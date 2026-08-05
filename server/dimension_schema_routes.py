import json
import logging
from flask import Blueprint, request, jsonify
from app import db
from tables.dimension_schema import DimensionSchema

dimension_schema_bp = Blueprint('dimension_schemas', __name__)


@dimension_schema_bp.route('/api/v1/dimension-schemas', methods=['GET'])
def list_schemas():
    """List all dimension schemas."""
    try:
        schemas = DimensionSchema.query.order_by(
            DimensionSchema.is_default.desc(),
            DimensionSchema.created_at.desc()
        ).all()
        return jsonify([s.json() for s in schemas])
    except Exception as e:
        logging.error(f"Error listing schemas: {e}")
        return jsonify({'error': str(e)}), 500


@dimension_schema_bp.route('/api/v1/dimension-schemas/<int:schema_id>', methods=['GET'])
def get_schema(schema_id):
    """Get a single dimension schema."""
    try:
        schema = DimensionSchema.query.get(schema_id)
        if not schema:
            return jsonify({'error': 'Schema not found'}), 404
        return jsonify(schema.json())
    except Exception as e:
        logging.error(f"Error getting schema: {e}")
        return jsonify({'error': str(e)}), 500


@dimension_schema_bp.route('/api/v1/dimension-schemas', methods=['POST'])
def create_schema():
    """Create a new dimension schema."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body required'}), 400

        schema_name = data.get('schema_name')
        dimensions = data.get('dimensions')

        if not schema_name or not dimensions:
            return jsonify({'error': 'schema_name and dimensions are required'}), 400

        if not isinstance(dimensions, list) or len(dimensions) == 0:
            return jsonify({'error': 'dimensions must be a non-empty array'}), 400

        # Validate each dimension has required fields
        for dim in dimensions:
            if not dim.get('key') or not dim.get('name'):
                return jsonify({'error': 'Each dimension must have key and name'}), 400

        schema = DimensionSchema(
            schema_name=schema_name,
            dimensions=dimensions,
            is_default=False
        )
        db.session.add(schema)
        db.session.commit()

        return jsonify(schema.json()), 201

    except Exception as e:
        logging.error(f"Error creating schema: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@dimension_schema_bp.route('/api/v1/dimension-schemas/<int:schema_id>', methods=['PUT'])
def update_schema(schema_id):
    """Update a dimension schema."""
    try:
        schema = DimensionSchema.query.get(schema_id)
        if not schema:
            return jsonify({'error': 'Schema not found'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body required'}), 400

        if 'schema_name' in data:
            schema.schema_name = data['schema_name']

        if 'dimensions' in data:
            dimensions = data['dimensions']
            if not isinstance(dimensions, list) or len(dimensions) == 0:
                return jsonify({'error': 'dimensions must be a non-empty array'}), 400
            for dim in dimensions:
                if not dim.get('key') or not dim.get('name'):
                    return jsonify({'error': 'Each dimension must have key and name'}), 400
            schema.dimensions = dimensions
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(schema, 'dimensions')

        db.session.commit()
        return jsonify(schema.json())

    except Exception as e:
        logging.error(f"Error updating schema: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@dimension_schema_bp.route('/api/v1/dimension-schemas/<int:schema_id>', methods=['DELETE'])
def delete_schema(schema_id):
    """Delete a dimension schema (cannot delete default)."""
    try:
        schema = DimensionSchema.query.get(schema_id)
        if not schema:
            return jsonify({'error': 'Schema not found'}), 404

        if schema.is_default:
            return jsonify({'error': 'Cannot delete the default schema'}), 400

        db.session.delete(schema)
        db.session.commit()
        return jsonify({'status': 'deleted', 'id': schema_id})

    except Exception as e:
        logging.error(f"Error deleting schema: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@dimension_schema_bp.route('/api/v1/dimension-schemas/default', methods=['GET'])
def get_default_schema():
    """Get the default dimension schema (the pool)."""
    try:
        schema = DimensionSchema.query.filter_by(is_default=True).first()
        if not schema:
            return jsonify({'error': 'No default schema found'}), 404
        return jsonify(schema.json())
    except Exception as e:
        logging.error(f"Error getting default schema: {e}")
        return jsonify({'error': str(e)}), 500


# =============================================================================
# Pool-level dimension management
# =============================================================================

@dimension_schema_bp.route('/api/v1/dimension-pool/add', methods=['POST'])
def add_dimension_to_pool():
    """
    Add a new dimension to the pool (default schema).

    Body: { "key": "creativity", "name": "Creativity",
            "description": "...", "indicators": [...], "scoring_criteria": "..." }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body required'}), 400

        key = data.get('key')
        name = data.get('name')
        description = data.get('description', '')

        if not key or not name:
            return jsonify({'error': 'key and name are required'}), 400

        schema = DimensionSchema.query.filter_by(is_default=True).first()
        if not schema:
            return jsonify({'error': 'No default schema found'}), 404

        dims = schema.dimensions or []

        # Check for duplicate key
        if any(d.get('key') == key for d in dims):
            return jsonify({'error': f'Dimension with key "{key}" already exists in pool'}), 400

        # Add new dimension
        new_dim = {
            'key': key,
            'name': name,
            'description': description,
            'indicators': data.get('indicators', []),
            'scoring_criteria': data.get('scoring_criteria', ''),
            'color': data.get('color', 'rgba(150, 150, 150, 0.35)')
        }
        dims.append(new_dim)

        schema.dimensions = dims
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(schema, 'dimensions')
        db.session.commit()

        return jsonify({
            'status': 'added',
            'dimension': new_dim,
            'pool': schema.json()
        }), 201

    except Exception as e:
        logging.error(f"Error adding dimension to pool: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@dimension_schema_bp.route('/api/v1/dimension-pool/remove', methods=['POST'])
def remove_dimension_from_pool():
    """
    Permanently remove a dimension from the pool.
    Also removes that dimension's data from analysis_summary and ai_baseline
    in ALL sessions that have it, then re-indexes affected sessions.

    Body: { "key": "creativity" }
    """
    try:
        data = request.get_json()
        dim_key = data.get('key') if data else None
        if not dim_key:
            return jsonify({'error': 'key is required'}), 400

        schema = DimensionSchema.query.filter_by(is_default=True).first()
        if not schema:
            return jsonify({'error': 'No default schema found'}), 404

        dims = schema.dimensions or []

        # Find and remove from pool
        original_len = len(dims)
        dims = [d for d in dims if d.get('key') != dim_key]
        if len(dims) == original_len:
            return jsonify({'error': f'Dimension "{dim_key}" not found in pool'}), 404

        schema.dimensions = dims
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(schema, 'dimensions')

        # Clean from all analyses
        from tables.seven_cs_analysis import SevenCsAnalysis
        affected_ids = []
        analyses = SevenCsAnalysis.query.filter(
            SevenCsAnalysis.analysis_status == 'completed'
        ).all()

        for analysis in analyses:
            changed = False
            summary = analysis.analysis_summary or {}
            baseline = analysis.ai_baseline or {}

            if dim_key in summary:
                del summary[dim_key]
                analysis.analysis_summary = summary
                flag_modified(analysis, 'analysis_summary')
                changed = True

            if dim_key in baseline:
                del baseline[dim_key]
                analysis.ai_baseline = baseline
                flag_modified(analysis, 'ai_baseline')
                changed = True

            if changed:
                affected_ids.append(analysis.session_device_id)

        db.session.commit()

        # Re-index affected sessions
        from indexing_service import reindex_session
        from study_context import get_chroma_path
        for sd_id in set(affected_ids):
            reindex_session(sd_id, reason="dimension_pool_delete", chroma_path=get_chroma_path())

        return jsonify({
            'status': 'removed',
            'dimension': dim_key,
            'sessions_affected': len(set(affected_ids)),
            'pool': schema.json()
        })

    except Exception as e:
        logging.error(f"Error removing dimension from pool: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
