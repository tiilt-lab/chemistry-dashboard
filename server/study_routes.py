"""
Study routes — interaction logging and phase control for CUI 2026 user study.

All logs are written to the MAIN database (discussion_capture.study_interaction_log),
not to per-participant databases.
"""
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, session as flask_session
import mysql.connector

logger = logging.getLogger(__name__)

study_bp = Blueprint('study', __name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_main_db_connection():
    """Always connect to the main discussion_capture database for logging."""
    return mysql.connector.connect(
        host='localhost', user='vagrant', password='vagrant',
        database='discussion_capture'
    )


def _get_study_user_id():
    """Return the study participant ID or None."""
    user = flask_session.get('user') or {}
    if user.get('role') == 'study':
        return user.get('email')
    return None


def _get_current_phase():
    """Return the current study phase from the session."""
    return flask_session.get('study_phase', 'unknown')


# ---------------------------------------------------------------------------
# Interaction Logging
# ---------------------------------------------------------------------------

@study_bp.route('/api/v1/study/log', methods=['POST'])
def log_action():
    """
    Log a study interaction event.

    Request body:
    {
        "action_type": "session_navigate",
        "session_device_id": 26,          // optional
        "action_data": { ... }            // optional extra data
    }
    """
    study_user_id = _get_study_user_id()
    if not study_user_id:
        # Non-study users — silently accept but don't log
        return jsonify({'logged': False, 'reason': 'not_study_user'}), 200

    data = request.get_json() or {}
    action_type = data.get('action_type')
    if not action_type:
        return jsonify({'error': 'action_type required'}), 400

    session_device_id = data.get('session_device_id')
    action_data = data.get('action_data')

    try:
        import json
        conn = _get_main_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO study_interaction_log
                (study_user_id, phase, action_type, session_device_id, action_data)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            study_user_id,
            _get_current_phase(),
            action_type,
            session_device_id,
            json.dumps(action_data) if action_data else None,
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'logged': True}), 200

    except Exception as e:
        logger.error(f"[Study] Error logging action: {e}")
        return jsonify({'logged': False, 'error': str(e)}), 200  # Don't fail the client


def log_study_action_server(study_user_id: str, action_type: str,
                            session_device_id: int = None,
                            action_data: dict = None, phase: str = None):
    """
    Server-side logging helper — call from other route handlers.

    Args:
        study_user_id: Participant ID (e.g. 'P01')
        action_type: Event type string
        session_device_id: Optional device context
        action_data: Optional extra data dict
        phase: Override phase (defaults to session phase)
    """
    if not study_user_id:
        return
    try:
        import json
        conn = _get_main_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO study_interaction_log
                (study_user_id, phase, action_type, session_device_id, action_data)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            study_user_id,
            phase or _get_current_phase(),
            action_type,
            session_device_id,
            json.dumps(action_data) if action_data else None,
        ))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(f"[Study] Server-side log error: {e}")


# ---------------------------------------------------------------------------
# Phase Control
# ---------------------------------------------------------------------------

@study_bp.route('/api/v1/study/phase', methods=['POST'])
def set_phase():
    """
    Set the current study phase for the logged-in participant.

    Request body:
    {
        "phase": "tutorial" | "guided" | "open" | "interview"
    }

    This is called by the researcher to advance the study phase.
    The phase is stored in the Flask session and automatically
    included in all subsequent interaction logs.
    """
    study_user_id = _get_study_user_id()
    if not study_user_id:
        return jsonify({'error': 'Not a study participant'}), 403

    data = request.get_json() or {}
    phase = data.get('phase')

    valid_phases = ['tutorial', 'guided', 'open', 'interview']
    if phase not in valid_phases:
        return jsonify({'error': f'Invalid phase. Must be one of: {valid_phases}'}), 400

    old_phase = flask_session.get('study_phase', 'unknown')
    flask_session['study_phase'] = phase

    # Log the phase change itself
    log_study_action_server(
        study_user_id=study_user_id,
        action_type='phase_change',
        action_data={'old_phase': old_phase, 'new_phase': phase},
        phase=phase,
    )

    return jsonify({
        'study_user_id': study_user_id,
        'phase': phase,
        'previous_phase': old_phase,
    })


@study_bp.route('/api/v1/study/phase', methods=['GET'])
def get_phase():
    """Get the current study phase."""
    return jsonify({
        'study_user_id': _get_study_user_id(),
        'phase': _get_current_phase(),
    })


# ---------------------------------------------------------------------------
# Study Status (researcher view)
# ---------------------------------------------------------------------------

@study_bp.route('/api/v1/study/status', methods=['GET'])
def study_status():
    """
    Get study status overview — interaction counts per participant.
    For researcher monitoring during the study.
    """
    try:
        conn = _get_main_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT study_user_id,
                   COUNT(*) as total_actions,
                   MAX(timestamp) as last_action,
                   GROUP_CONCAT(DISTINCT phase) as phases
            FROM study_interaction_log
            GROUP BY study_user_id
            ORDER BY study_user_id
        """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        for row in rows:
            if row.get('last_action'):
                row['last_action'] = row['last_action'].isoformat()

        return jsonify({'participants': rows})

    except Exception as e:
        logger.error(f"[Study] Status error: {e}")
        return jsonify({'error': str(e)}), 500
