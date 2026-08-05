"""
Discussion Pulse Routes - API endpoints for real-time discussion summaries.
"""
import logging
from flask import Blueprint, request, jsonify
from app import db
from tables.discussion_pulse import DiscussionPulse
import database as db_helper
from discussion_pulse_service import (
    generate_next_pulse,
    get_all_pulses_for_session,
    generate_pulse_for_window
)

discussion_pulse_bp = Blueprint('discussion_pulse', __name__)


@discussion_pulse_bp.route('/api/v1/discussion-pulse/<int:session_device_id>', methods=['GET'])
def get_pulses(session_device_id):
    """
    Get all discussion pulses for a session device.
    Returns pulses in chronological order.
    """
    try:
        pulses = get_all_pulses_for_session(session_device_id)
        return jsonify({
            'pulses': pulses,
            'count': len(pulses)
        }), 200
    except Exception as e:
        logging.error(f"Error getting pulses: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@discussion_pulse_bp.route('/api/v1/discussion-pulse/<int:session_device_id>/latest', methods=['GET'])
def get_latest_pulse(session_device_id):
    """
    Get the most recent discussion pulse for a session device.
    Useful for real-time updates on the frontend.
    """
    try:
        pulse = DiscussionPulse.query.filter_by(
            session_device_id=session_device_id
        ).order_by(DiscussionPulse.end_time.desc()).first()

        if pulse:
            return jsonify(pulse.json()), 200
        else:
            return jsonify({'message': 'No pulses yet'}), 200

    except Exception as e:
        logging.error(f"Error getting latest pulse: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@discussion_pulse_bp.route('/api/v1/discussion-pulse/<int:session_device_id>/generate', methods=['POST'])
def trigger_pulse_generation(session_device_id):
    """
    Manually trigger pulse generation for a session device.
    Used to generate the next pulse based on recent transcripts.
    """
    try:
        # Check if session device exists
        session_device = db_helper.get_session_devices(id=session_device_id)
        if not session_device:
            return jsonify({'error': 'Session device not found'}), 404

        # Get optional window size from request
        data = request.get_json() or {}
        window_seconds = data.get('window_seconds', 60)

        # Generate next pulse
        pulse = generate_next_pulse(session_device_id, window_seconds)

        if pulse:
            return jsonify({
                'status': 'success',
                'pulse': pulse.json()
            }), 200
        else:
            return jsonify({
                'status': 'no_content',
                'message': 'Not enough new content to generate a pulse'
            }), 200

    except Exception as e:
        logging.error(f"Error triggering pulse: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@discussion_pulse_bp.route('/api/v1/discussion-pulse/<int:session_device_id>/poll', methods=['GET'])
def poll_for_new_pulses(session_device_id):
    """
    Poll for new pulses since a given timestamp.
    Returns only pulses created after the 'since' timestamp.

    Query params:
        since: Unix timestamp (float) to get pulses after
    """
    try:
        since = request.args.get('since', type=float, default=0)

        pulses = DiscussionPulse.query.filter(
            DiscussionPulse.session_device_id == session_device_id,
            DiscussionPulse.end_time > since
        ).order_by(DiscussionPulse.start_time).all()

        return jsonify({
            'pulses': [p.json() for p in pulses],
            'count': len(pulses),
            'latest_time': pulses[-1].end_time if pulses else since
        }), 200

    except Exception as e:
        logging.error(f"Error polling pulses: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@discussion_pulse_bp.route('/api/v1/discussion-pulse/<int:session_device_id>', methods=['DELETE'])
def delete_pulses(session_device_id):
    """
    Delete all pulses for a session device.
    Useful for re-generating from scratch.
    """
    try:
        deleted = DiscussionPulse.query.filter_by(
            session_device_id=session_device_id
        ).delete()

        db.session.commit()

        return jsonify({
            'status': 'success',
            'deleted_count': deleted
        }), 200

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error deleting pulses: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
