"""
API routes for expert 7C annotations.

These endpoints allow human experts to create and update 7C annotations
for research evaluation (measuring agreement with LLM-generated analysis).
"""

import logging
from flask import Blueprint, request, jsonify
from app import db
from tables.expert_7c_annotation import Expert7CAnnotation
import database as db_helper

expert_annotation_bp = Blueprint('expert_annotation', __name__)

# 7C dimension definitions for tooltips
DIMENSION_DEFINITIONS = {
    'climate': {
        'name': 'Climate',
        'description': 'The emotional and affective aspects of the collaboration',
        'indicators': ['respect', 'comfort', 'tone', 'welcome', 'safe', 'listening', 'being heard']
    },
    'communication': {
        'name': 'Communication',
        'description': 'The quantity and quality of information shared among group members',
        'indicators': ['verbal', 'nonverbal', 'discussion', 'listening', 'sharing', 'goals', 'expectations']
    },
    'compatibility': {
        'name': 'Compatibility',
        'description': 'How well group members\' working and interaction styles complement each other',
        'indicators': ['working style', 'active', 'equal distribution', 'friends', 'creative vision', 'complementary skills']
    },
    'conflict': {
        'name': 'Conflict',
        'description': 'Approaches to handling disagreements and contentious situations',
        'indicators': ['adapting', 'differences', 'confronting', 'mediator', 'resolution', 'external validation']
    },
    'context': {
        'name': 'Context',
        'description': 'Environmental factors and situational awareness: the who, why, and where',
        'indicators': ['privacy', 'out of school', 'in/out of context', 'interest', 'group members', 'setting']
    },
    'contribution': {
        'name': 'Contribution',
        'description': 'Individual participation and effort balance',
        'indicators': ['accountable', 'balance of work', 'tracking', 'engagement', 'effort', 'verbal contributions']
    },
    'constructive': {
        'name': 'Constructive',
        'description': 'Overall goals and the team\'s progress toward achieving them',
        'indicators': ['goal', 'product', 'efficiency', 'learning', 'mutual benefit', 'insights']
    }
}


@expert_annotation_bp.route('/api/v1/expert-annotations/dimensions', methods=['GET'])
def get_dimension_definitions():
    """Get the 7C dimension definitions for tooltips."""
    return jsonify(DIMENSION_DEFINITIONS)


@expert_annotation_bp.route('/api/v1/expert-annotations/<int:session_device_id>', methods=['GET'])
def get_annotation(session_device_id):
    """
    Get expert annotation for a session device.

    Query params:
    - expert_id: Required. The expert's identifier.

    Returns:
    - If annotation exists: the annotation data
    - If not exists: empty annotation structure with exists=False
    """
    expert_id = request.args.get('expert_id')

    if not expert_id:
        return jsonify({'error': 'expert_id is required'}), 400

    try:
        # Check if session device exists
        session_device = db_helper.get_session_devices(id=session_device_id)
        if not session_device:
            return jsonify({'error': 'Session device not found'}), 404

        # Look for existing annotation
        annotation = db.session.query(Expert7CAnnotation).filter_by(
            expert_id=expert_id,
            session_device_id=session_device_id
        ).first()

        if annotation:
            return jsonify({
                'exists': True,
                'annotation': annotation.json()
            })
        else:
            # Return empty structure
            empty = Expert7CAnnotation._empty_annotation()
            return jsonify({
                'exists': False,
                'annotation': {
                    'expert_id': expert_id,
                    'session_device_id': session_device_id,
                    'status': 'draft',
                    'annotation_data': empty,
                    'created_at': None,
                    'updated_at': None
                }
            })

    except Exception as e:
        logging.error(f"Error getting expert annotation: {str(e)}")
        return jsonify({'error': str(e)}), 500


@expert_annotation_bp.route('/api/v1/expert-annotations/<int:session_device_id>', methods=['POST'])
def create_or_update_annotation(session_device_id):
    """
    Create or update an expert annotation.

    Body:
    {
        "expert_id": "expert_jane",
        "annotation_data": {
            "climate": {"score": 75, "analysis": "...", "evidence": "..."},
            ...
        },
        "status": "draft" | "submitted"
    }
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body is required'}), 400

    expert_id = data.get('expert_id')
    annotation_data = data.get('annotation_data')
    status = data.get('status', 'draft')

    if not expert_id:
        return jsonify({'error': 'expert_id is required'}), 400

    if status not in ['draft', 'submitted']:
        return jsonify({'error': 'status must be draft or submitted'}), 400

    try:
        # Check if session device exists
        session_device = db_helper.get_session_devices(id=session_device_id)
        if not session_device:
            return jsonify({'error': 'Session device not found'}), 404

        # Look for existing annotation
        annotation = db.session.query(Expert7CAnnotation).filter_by(
            expert_id=expert_id,
            session_device_id=session_device_id
        ).first()

        if annotation:
            # Update existing
            annotation.update_annotation(annotation_data, status)
            db.session.commit()

            return jsonify({
                'message': 'Annotation updated',
                'annotation': annotation.json()
            })
        else:
            # Create new
            annotation = Expert7CAnnotation(
                expert_id=expert_id,
                session_device_id=session_device_id,
                annotation_data=annotation_data,
                status=status
            )
            db.session.add(annotation)
            db.session.commit()

            return jsonify({
                'message': 'Annotation created',
                'annotation': annotation.json()
            }), 201

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error saving expert annotation: {str(e)}")
        return jsonify({'error': str(e)}), 500


@expert_annotation_bp.route('/api/v1/expert-annotations/<int:session_device_id>/submit', methods=['POST'])
def submit_annotation(session_device_id):
    """
    Mark an annotation as submitted (final).

    Body:
    {
        "expert_id": "expert_jane"
    }
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body is required'}), 400

    expert_id = data.get('expert_id')

    if not expert_id:
        return jsonify({'error': 'expert_id is required'}), 400

    try:
        annotation = db.session.query(Expert7CAnnotation).filter_by(
            expert_id=expert_id,
            session_device_id=session_device_id
        ).first()

        if not annotation:
            return jsonify({'error': 'Annotation not found'}), 404

        annotation.status = 'submitted'
        db.session.commit()

        return jsonify({
            'message': 'Annotation submitted',
            'annotation': annotation.json()
        })

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error submitting annotation: {str(e)}")
        return jsonify({'error': str(e)}), 500


@expert_annotation_bp.route('/api/v1/expert-annotations/list/<int:session_device_id>', methods=['GET'])
def list_annotations_for_device(session_device_id):
    """
    List all expert annotations for a session device.
    Useful for comparing multiple experts' annotations.
    """
    try:
        annotations = db.session.query(Expert7CAnnotation).filter_by(
            session_device_id=session_device_id
        ).all()

        return jsonify({
            'count': len(annotations),
            'annotations': [a.json() for a in annotations]
        })

    except Exception as e:
        logging.error(f"Error listing annotations: {str(e)}")
        return jsonify({'error': str(e)}), 500


@expert_annotation_bp.route('/api/v1/expert-annotations/by-expert/<expert_id>', methods=['GET'])
def list_annotations_by_expert(expert_id):
    """
    List all annotations by a specific expert.
    Useful for an expert to see their work across sessions.
    """
    try:
        annotations = db.session.query(Expert7CAnnotation).filter_by(
            expert_id=expert_id
        ).all()

        return jsonify({
            'expert_id': expert_id,
            'count': len(annotations),
            'annotations': [a.json() for a in annotations]
        })

    except Exception as e:
        logging.error(f"Error listing expert's annotations: {str(e)}")
        return jsonify({'error': str(e)}), 500
