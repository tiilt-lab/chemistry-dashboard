import json
import logging
import threading
from flask import Blueprint, request, jsonify, current_app, g
from app import db
from tables.seven_cs_analysis import SevenCsAnalysis
from tables.seven_cs_coded_segment import SevenCsCodedSegment
import database as db_helper
from seven_cs_service import analyze_session_seven_cs, update_seven_cs_analysis

seven_cs_bp = Blueprint('seven_cs', __name__)


def _reindex_background(app, session_device_id: int, reason: str,
                        study_db: str = None, chroma_path: str = None):
    """Fire-and-forget re-indexing — runs in a daemon thread with Flask app context."""
    def _run():
        with app.app_context():
            if study_db:
                from sqlalchemy import text
                db.session.execute(text(f'USE {study_db}'))
            from indexing_service import reindex_session
            reindex_session(session_device_id, reason=reason, chroma_path=chroma_path)
    threading.Thread(target=_run, daemon=True).start()


@seven_cs_bp.route('/api/v1/seven-cs/analyze/<int:session_device_id>', methods=['POST'])
def trigger_analysis(session_device_id):
    """
    Manually trigger collaboration assessment for a session device.
    Regenerates for all active dimensions (keys in analysis_summary).
    Full reset — wipes all user edits. Stores results as the new AI baseline.
    """
    try:
        # Check if session device exists
        session_device = db_helper.get_session_devices(id=session_device_id)
        if not session_device:
            return jsonify({'error': 'Session device not found'}), 404

        # Check if analysis is already in progress
        existing = db.session.query(SevenCsAnalysis).filter_by(
            session_device_id=session_device_id,
            analysis_status='processing'
        ).first()

        if existing:
            return jsonify({
                'status': 'processing',
                'message': 'Analysis already in progress',
                'analysis_id': existing.id
            }), 202

        # Trigger new analysis (optionally with custom schema)
        data = request.get_json(silent=True) or {}
        schema_id = data.get('schema_id')
        analysis = update_seven_cs_analysis(session_device_id, schema_id=schema_id)

        if analysis:
            return jsonify({
                'status': 'triggered',
                'message': 'Analysis started successfully',
                'analysis_id': analysis.id
            }), 202
        else:
            return jsonify({
                'error': 'Failed to start analysis'
            }), 500

    except Exception as e:
        logging.error(f"Error triggering analysis: {str(e)}")
        return jsonify({'error': str(e)}), 500

@seven_cs_bp.route('/api/v1/seven-cs/results/<int:session_device_id>', methods=['GET'])
def get_results(session_device_id):
    """
    Get the latest analysis results for a session device.
    Returns overall scores, coded segments, and aggregated counts.
    """
    try:
        # Get the latest analysis
        analysis = db.session.query(SevenCsAnalysis).filter_by(
            session_device_id=session_device_id
        ).order_by(SevenCsAnalysis.created_at.desc()).first()

        if not analysis:
            return jsonify({
                'status': 'not_analyzed',
                'message': 'No analysis found for this session'
            }), 200

        # Get coded segments
        segments = db.session.query(SevenCsCodedSegment).filter_by(
            analysis_id=analysis.id
        ).all()

        # Calculate dimension counts
        dimension_counts = {}
        for segment in segments:
            if segment.dimension not in dimension_counts:
                dimension_counts[segment.dimension] = 0
            dimension_counts[segment.dimension] += 1

        # Prepare segments data
        segments_data = []
        for segment in segments:
            segments_data.append({
                'id': segment.id,
                'dimension': segment.dimension,
                'start_time': segment.start_time,
                'end_time': segment.end_time,
                'text_snippet': segment.text_snippet,
                'speaker_tag': segment.speaker_tag,
                'coding_reason': segment.coding_reason,
                'confidence': segment.confidence
            })

        # Load dimension schema for frontend rendering
        schema_data = None
        if analysis.schema_id:
            from tables.dimension_schema import DimensionSchema
            schema = DimensionSchema.query.get(analysis.schema_id)
            if schema:
                schema_data = schema.json()

        # Compute edit diffs: compare analysis_summary vs ai_baseline
        edited_dimensions = _compute_edit_diffs(analysis)

        # Return comprehensive results
        return jsonify({
            'status': analysis.analysis_status,
            'summary': analysis.analysis_summary,
            'ai_baseline': analysis.ai_baseline,
            'edited_dimensions': edited_dimensions,
            'counts': dimension_counts,
            'segments': segments_data,
            'schema': schema_data,
            'metadata': {
                'total_segments_analyzed': analysis.total_segments_analyzed,
                'processing_time_seconds': analysis.processing_time_seconds,
                'tokens_used': analysis.tokens_used,
                'created_at': analysis.created_at.isoformat() if analysis.created_at else None,
                'updated_at': analysis.updated_at.isoformat() if analysis.updated_at else None,
                'schema_id': analysis.schema_id
            }
        })

    except Exception as e:
        logging.error(f"Error getting results: {str(e)}")
        return jsonify({'error': str(e)}), 500

@seven_cs_bp.route('/api/v1/seven-cs/status/<int:session_device_id>', methods=['GET'])
def check_status(session_device_id):
    """Check the status of analysis for a session device."""
    try:
        analysis = db.session.query(SevenCsAnalysis).filter_by(
            session_device_id=session_device_id
        ).order_by(SevenCsAnalysis.created_at.desc()).first()

        if not analysis:
            return jsonify({
                'status': 'not_analyzed',
                'message': 'No analysis found'
            })

        return jsonify({
            'status': analysis.analysis_status,
            'analysis_id': analysis.id,
            'created_at': analysis.created_at.isoformat() if analysis.created_at else None,
            'updated_at': analysis.updated_at.isoformat() if analysis.updated_at else None
        })

    except Exception as e:
        logging.error(f"Error checking status: {str(e)}")
        return jsonify({'error': str(e)}), 500

@seven_cs_bp.route('/api/v1/seven-cs/segments/<int:session_device_id>/<dimension>', methods=['GET'])
def get_dimension_segments(session_device_id, dimension):
    """Get all coded segments for a specific dimension."""
    try:
        analysis = db.session.query(SevenCsAnalysis).filter_by(
            session_device_id=session_device_id,
            analysis_status='completed'
        ).order_by(SevenCsAnalysis.created_at.desc()).first()

        if not analysis:
            return jsonify({
                'status': 'not_analyzed',
                'message': 'No completed analysis found'
            }), 404

        # Validate dimension exists in this analysis
        if dimension.lower() not in (analysis.analysis_summary or {}):
            return jsonify({'error': f'Dimension {dimension} not active in this analysis'}), 400

        segments = db.session.query(SevenCsCodedSegment).filter_by(
            analysis_id=analysis.id,
            dimension=dimension.lower()
        ).order_by(SevenCsCodedSegment.start_time).all()

        segments_data = []
        for segment in segments:
            segments_data.append({
                'id': segment.id,
                'start_time': segment.start_time,
                'end_time': segment.end_time,
                'text_snippet': segment.text_snippet,
                'speaker_tag': segment.speaker_tag,
                'coding_reason': segment.coding_reason,
                'confidence': segment.confidence,
                'transcript_id': segment.transcript_id
            })

        return jsonify({
            'dimension': dimension,
            'count': len(segments_data),
            'segments': segments_data
        })

    except Exception as e:
        logging.error(f"Error getting dimension segments: {str(e)}")
        return jsonify({'error': str(e)}), 500

@seven_cs_bp.route('/api/v1/seven-cs/export/<int:session_device_id>', methods=['GET'])
def export_analysis(session_device_id):
    """Export analysis results in a format suitable for external analysis tools."""
    try:
        analysis = db.session.query(SevenCsAnalysis).filter_by(
            session_device_id=session_device_id,
            analysis_status='completed'
        ).order_by(SevenCsAnalysis.created_at.desc()).first()

        if not analysis:
            return jsonify({
                'status': 'not_analyzed',
                'message': 'No completed analysis found'
            }), 404

        segments = db.session.query(SevenCsCodedSegment).filter_by(
            analysis_id=analysis.id
        ).order_by(SevenCsCodedSegment.start_time).all()

        session_device = db_helper.get_session_devices(id=session_device_id)
        session = db_helper.get_sessions(id=session_device.session_id) if session_device else None

        export_data = {
            'metadata': {
                'session_id': session.id if session else None,
                'session_name': session.name if session else None,
                'device_id': session_device_id,
                'device_name': session_device.name if session_device else None,
                'analysis_date': analysis.created_at.isoformat() if analysis.created_at else None,
                'total_segments_coded': len(segments)
            },
            'overall_scores': analysis.analysis_summary,
            'ai_baseline': analysis.ai_baseline,
            'coded_segments': []
        }

        for segment in segments:
            export_data['coded_segments'].append({
                'dimension': segment.dimension,
                'start_time': segment.start_time,
                'end_time': segment.end_time,
                'duration': segment.end_time - segment.start_time,
                'text': segment.text_snippet,
                'speaker': segment.speaker_tag,
                'coding_reason': segment.coding_reason,
                'confidence': segment.confidence
            })

        # Dynamic dimension statistics from analysis_summary
        dimension_stats = {}
        for dim in (analysis.analysis_summary or {}):
            dim_segments = [s for s in segments if s.dimension == dim]
            dimension_stats[dim] = {
                'count': len(dim_segments),
                'percentage': round((len(dim_segments) / len(segments) * 100), 2) if segments else 0,
                'avg_confidence': round(sum(s.confidence for s in dim_segments) / len(dim_segments), 2) if dim_segments else 0
            }

        export_data['dimension_statistics'] = dimension_stats
        return jsonify(export_data)

    except Exception as e:
        logging.error(f"Error exporting analysis: {str(e)}")
        return jsonify({'error': str(e)}), 500


# =============================================================================
# Dimension editing (writes to analysis_summary only, ai_baseline untouched)
# =============================================================================

@seven_cs_bp.route('/api/v1/seven-cs/results/<int:session_device_id>/edit', methods=['PATCH'])
def edit_dimension(session_device_id):
    """
    Edit a dimension's score, explanation, or evidence in analysis_summary.
    ai_baseline is NOT modified — edit diffs are computed at read time.

    Body: { "dimension": "climate", "field": "score"|"explanation"|"evidence", "value": ... }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body required'}), 400

        dimension = data.get('dimension')
        field = data.get('field')
        value = data.get('value')

        if not dimension or not field or value is None:
            return jsonify({'error': 'dimension, field, and value are required'}), 400

        if field not in ('score', 'explanation', 'evidence'):
            return jsonify({'error': 'field must be score, explanation, or evidence'}), 400

        analysis = db.session.query(SevenCsAnalysis).filter_by(
            session_device_id=session_device_id
        ).order_by(SevenCsAnalysis.created_at.desc()).first()

        if not analysis:
            return jsonify({'error': 'No analysis found'}), 404

        summary = analysis.analysis_summary or {}
        dim_data = summary.get(dimension)
        if dim_data is None:
            return jsonify({'error': f'Dimension {dimension} not found in analysis'}), 404

        # Validate score range
        if field == 'score':
            try:
                value = int(value)
            except (ValueError, TypeError):
                return jsonify({'error': 'Score must be an integer'}), 400
            if value < 0 or value > 100:
                return jsonify({'error': 'Score must be between 0 and 100'}), 400

        # Capture old value before mutation (for study logging)
        old_value = dim_data.get(field)

        # Update analysis_summary only (ai_baseline stays untouched)
        dim_data[field] = value
        summary[dimension] = dim_data
        analysis.analysis_summary = summary
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(analysis, 'analysis_summary')

        db.session.commit()

        _reindex_background(current_app._get_current_object(), session_device_id, reason="dimension_edit",
                            study_db=getattr(g, 'study_db', None), chroma_path=getattr(g, 'chroma_path', None))

        # Log study interaction
        from study_context import get_study_user_id
        _study_uid = get_study_user_id()
        if _study_uid:
            from study_routes import log_study_action_server
            log_study_action_server(_study_uid, 'assessment_edit', session_device_id=session_device_id,
                                    action_data={'dimension': dimension, 'field': field, 'value': value, 'old_value': old_value})

        return jsonify({
            'status': 'updated',
            'dimension': dimension,
            'field': field,
            'value': value,
            'summary': analysis.analysis_summary
        })

    except Exception as e:
        logging.error(f"Error editing dimension: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@seven_cs_bp.route('/api/v1/seven-cs/results/<int:session_device_id>/edits', methods=['GET'])
def get_edit_diffs(session_device_id):
    """
    Get current edit diffs by comparing analysis_summary vs ai_baseline.
    No append-only log — computed at read time.
    """
    try:
        analysis = db.session.query(SevenCsAnalysis).filter_by(
            session_device_id=session_device_id
        ).order_by(SevenCsAnalysis.created_at.desc()).first()

        if not analysis:
            return jsonify({'edits': {}})

        return jsonify({
            'analysis_id': analysis.id,
            'edits': _compute_edit_diffs(analysis)
        })

    except Exception as e:
        logging.error(f"Error getting edit diffs: {str(e)}")
        return jsonify({'error': str(e)}), 500


@seven_cs_bp.route('/api/v1/seven-cs/results/<int:session_device_id>/reset/<dimension>', methods=['POST'])
def reset_dimension(session_device_id, dimension):
    """
    Reset a dimension to its AI-generated baseline values.
    Copies ai_baseline[dimension] back into analysis_summary[dimension].
    """
    try:
        analysis = db.session.query(SevenCsAnalysis).filter_by(
            session_device_id=session_device_id
        ).order_by(SevenCsAnalysis.created_at.desc()).first()

        if not analysis:
            return jsonify({'error': 'No analysis found'}), 404

        baseline = analysis.ai_baseline or {}
        if dimension not in baseline:
            return jsonify({'error': f'No baseline found for dimension {dimension}'}), 404

        summary = analysis.analysis_summary or {}
        summary[dimension] = json.loads(json.dumps(baseline[dimension]))  # deep copy
        analysis.analysis_summary = summary
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(analysis, 'analysis_summary')

        db.session.commit()

        _reindex_background(current_app._get_current_object(), session_device_id, reason="dimension_reset",
                            study_db=getattr(g, 'study_db', None), chroma_path=getattr(g, 'chroma_path', None))

        return jsonify({
            'status': 'reset',
            'dimension': dimension,
            'summary': analysis.analysis_summary
        })

    except Exception as e:
        logging.error(f"Error resetting dimension: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# =============================================================================
# Per-session dimension activate / deactivate
# =============================================================================

@seven_cs_bp.route('/api/v1/seven-cs/results/<int:session_device_id>/activate', methods=['POST'])
def activate_dimension(session_device_id):
    """
    Activate a dimension for this session.
    Adds the dimension key to analysis_summary with null data.
    User must regenerate to get assessment data.

    Body: { "dimension": "creativity" }
    """
    try:
        data = request.get_json()
        dimension = data.get('dimension') if data else None
        if not dimension:
            return jsonify({'error': 'dimension is required'}), 400

        analysis = db.session.query(SevenCsAnalysis).filter_by(
            session_device_id=session_device_id
        ).order_by(SevenCsAnalysis.created_at.desc()).first()

        if not analysis:
            return jsonify({'error': 'No analysis found'}), 404

        summary = analysis.analysis_summary or {}
        if dimension in summary:
            return jsonify({'status': 'already_active', 'dimension': dimension})

        # Add with null data — needs regeneration
        summary[dimension] = None
        analysis.analysis_summary = summary
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(analysis, 'analysis_summary')
        db.session.commit()

        return jsonify({
            'status': 'activated',
            'dimension': dimension,
            'message': 'Dimension activated. Regenerate to get assessment data.'
        })

    except Exception as e:
        logging.error(f"Error activating dimension: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@seven_cs_bp.route('/api/v1/seven-cs/results/<int:session_device_id>/deactivate', methods=['POST'])
def deactivate_dimension(session_device_id):
    """
    Deactivate a dimension for this session.
    Removes dimension from analysis_summary and ai_baseline. Data is gone.
    Triggers re-indexing.

    Body: { "dimension": "conflict" }
    """
    try:
        data = request.get_json()
        dimension = data.get('dimension') if data else None
        if not dimension:
            return jsonify({'error': 'dimension is required'}), 400

        analysis = db.session.query(SevenCsAnalysis).filter_by(
            session_device_id=session_device_id
        ).order_by(SevenCsAnalysis.created_at.desc()).first()

        if not analysis:
            return jsonify({'error': 'No analysis found'}), 404

        summary = analysis.analysis_summary or {}
        baseline = analysis.ai_baseline or {}

        if dimension not in summary and dimension not in baseline:
            return jsonify({'status': 'not_found', 'message': f'Dimension {dimension} not in this analysis'})

        # Remove from both
        summary.pop(dimension, None)
        baseline.pop(dimension, None)

        analysis.analysis_summary = summary
        analysis.ai_baseline = baseline
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(analysis, 'analysis_summary')
        flag_modified(analysis, 'ai_baseline')

        db.session.commit()

        _reindex_background(current_app._get_current_object(), session_device_id, reason="dimension_deactivate",
                            study_db=getattr(g, 'study_db', None), chroma_path=getattr(g, 'chroma_path', None))

        return jsonify({
            'status': 'deactivated',
            'dimension': dimension,
            'summary': analysis.analysis_summary
        })

    except Exception as e:
        logging.error(f"Error deactivating dimension: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# =============================================================================
# Helpers
# =============================================================================

def _compute_edit_diffs(analysis):
    """
    Compare analysis_summary vs ai_baseline for each dimension.
    Returns dict of {dimension: {field: {current, baseline}}} for dimensions that differ.
    """
    summary = analysis.analysis_summary or {}
    baseline = analysis.ai_baseline or {}
    diffs = {}

    for dim_key, current_data in summary.items():
        if not current_data or not isinstance(current_data, dict):
            continue
        baseline_data = baseline.get(dim_key)
        if not baseline_data or not isinstance(baseline_data, dict):
            continue

        dim_diffs = {}
        # Only track score diffs for the edit log
        current_score = current_data.get('score')
        baseline_score = baseline_data.get('score')
        if current_score is not None and baseline_score is not None and current_score != baseline_score:
            dim_diffs['score'] = {'current': current_score, 'baseline': baseline_score}

        if dim_diffs:
            diffs[dim_key] = dim_diffs

    return diffs
