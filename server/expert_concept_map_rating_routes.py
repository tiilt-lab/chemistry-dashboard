"""
API routes for expert concept map ratings.

Allows human experts to rate AI-generated concept maps across
quality dimensions (Likert 1-5) for research evaluation.
"""

import logging
from flask import Blueprint, request, jsonify
from app import db
from tables.expert_concept_map_rating import ExpertConceptMapRating
import database as db_helper

expert_concept_map_rating_bp = Blueprint('expert_concept_map_rating', __name__)

RATING_DIMENSIONS = {
    'node_accuracy': {
        'name': 'Node Accuracy',
        'description': 'The concepts accurately reflect ideas from the discussion',
    },
    'relationship_validity': {
        'name': 'Relationship Validity',
        'description': 'The connections between concepts are meaningful and supported',
    },
    'completeness': {
        'name': 'Completeness',
        'description': 'Important ideas from the discussion are captured',
    },
    'granularity': {
        'name': 'Granularity',
        'description': 'The level of detail is appropriate—not too broad, not too fragmented',
    },
    'usefulness': {
        'name': 'Usefulness',
        'description': 'This map would help a teacher understand the discussion',
    },
}


@expert_concept_map_rating_bp.route('/api/v1/expert-concept-map-ratings/dimensions', methods=['GET'])
def get_dimensions():
    """Get rating dimension definitions."""
    return jsonify(RATING_DIMENSIONS)


@expert_concept_map_rating_bp.route('/api/v1/expert-concept-map-ratings/<int:session_device_id>', methods=['GET'])
def get_rating(session_device_id):
    """
    Get expert rating for a session device's concept map.

    Query params:
    - expert_id: Required.
    """
    expert_id = request.args.get('expert_id')
    if not expert_id:
        return jsonify({'error': 'expert_id is required'}), 400

    try:
        session_device = db_helper.get_session_devices(id=session_device_id)
        if not session_device:
            return jsonify({'error': 'Session device not found'}), 404

        rating = db.session.query(ExpertConceptMapRating).filter_by(
            expert_id=expert_id,
            session_device_id=session_device_id
        ).first()

        if rating:
            return jsonify({'exists': True, 'rating': rating.json()})
        else:
            empty = ExpertConceptMapRating._empty_ratings()
            return jsonify({
                'exists': False,
                'rating': {
                    'expert_id': expert_id,
                    'session_device_id': session_device_id,
                    'status': 'draft',
                    'ratings': empty,
                    'comment': '',
                    'created_at': None,
                    'updated_at': None,
                }
            })

    except Exception as e:
        logging.error(f"Error getting concept map rating: {str(e)}")
        return jsonify({'error': str(e)}), 500


@expert_concept_map_rating_bp.route('/api/v1/expert-concept-map-ratings/<int:session_device_id>', methods=['POST'])
def create_or_update_rating(session_device_id):
    """
    Create or update an expert concept map rating.

    Body:
    {
        "expert_id": "expert_jane",
        "ratings": {"node_accuracy": 4, ...},
        "comment": "...",
        "status": "draft" | "submitted"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body is required'}), 400

    expert_id = data.get('expert_id')
    ratings = data.get('ratings')
    comment = data.get('comment', '')
    status = data.get('status', 'draft')

    if not expert_id:
        return jsonify({'error': 'expert_id is required'}), 400
    if status not in ['draft', 'submitted']:
        return jsonify({'error': 'status must be draft or submitted'}), 400

    try:
        session_device = db_helper.get_session_devices(id=session_device_id)
        if not session_device:
            return jsonify({'error': 'Session device not found'}), 404

        rating = db.session.query(ExpertConceptMapRating).filter_by(
            expert_id=expert_id,
            session_device_id=session_device_id
        ).first()

        if rating:
            rating.update_rating(ratings, comment, status)
            db.session.commit()
            return jsonify({'message': 'Rating updated', 'rating': rating.json()})
        else:
            rating = ExpertConceptMapRating(
                expert_id=expert_id,
                session_device_id=session_device_id,
                ratings=ratings,
                comment=comment,
                status=status,
            )
            db.session.add(rating)
            db.session.commit()
            return jsonify({'message': 'Rating created', 'rating': rating.json()}), 201

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error saving concept map rating: {str(e)}")
        return jsonify({'error': str(e)}), 500


@expert_concept_map_rating_bp.route('/api/v1/expert-concept-map-ratings/list/<int:session_device_id>', methods=['GET'])
def list_ratings_for_device(session_device_id):
    """List all expert ratings for a session device's concept map."""
    try:
        ratings = db.session.query(ExpertConceptMapRating).filter_by(
            session_device_id=session_device_id
        ).all()
        return jsonify({'count': len(ratings), 'ratings': [r.json() for r in ratings]})
    except Exception as e:
        logging.error(f"Error listing concept map ratings: {str(e)}")
        return jsonify({'error': str(e)}), 500


@expert_concept_map_rating_bp.route('/api/v1/expert-concept-map-ratings/by-expert/<expert_id>', methods=['GET'])
def list_ratings_by_expert(expert_id):
    """List all concept map ratings by a specific expert."""
    try:
        ratings = db.session.query(ExpertConceptMapRating).filter_by(
            expert_id=expert_id
        ).all()
        return jsonify({
            'expert_id': expert_id,
            'count': len(ratings),
            'ratings': [r.json() for r in ratings],
        })
    except Exception as e:
        logging.error(f"Error listing expert's concept map ratings: {str(e)}")
        return jsonify({'error': str(e)}), 500
