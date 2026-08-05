"""
Expert Agent Rating Routes

API endpoints for blind expert evaluation of agent responses.
"""

from flask import Blueprint, request, jsonify
from app import db
from tables.agent_response import AgentResponse
from tables.expert_agent_rating import ExpertAgentRating
import random
import hashlib
import logging

logger = logging.getLogger(__name__)

expert_agent_rating_bp = Blueprint('expert_agent_rating', __name__, url_prefix='/api/expert-agent-rating')


@expert_agent_rating_bp.route('/responses', methods=['GET'])
def get_responses():
    """
    Get all responses for expert evaluation.
    Responses are randomized and agent_version is hidden.
    Includes info on which ones this expert has already rated.
    """
    expert_id = request.args.get('expert_id')
    if not expert_id:
        return jsonify({'error': 'expert_id is required'}), 400

    try:
        # Get all responses
        responses = AgentResponse.query.all()

        # Get IDs this expert has already rated
        rated_ids = set(
            r.response_id for r in
            ExpertAgentRating.query.filter_by(expert_id=expert_id).all()
        )

        # Group responses by pair_id
        pairs = {}  # pair_id -> list of responses
        singles = []  # responses without pair or with unique pair_id
        for r in responses:
            if r.pair_id:
                pairs.setdefault(r.pair_id, []).append(r)
            else:
                singles.append(r)

        # Separate actual pairs (2 responses) from singles
        actual_pairs = {}
        for pid, resps in pairs.items():
            if len(resps) == 2:
                actual_pairs[pid] = resps
            else:
                singles.extend(resps)

        # Shuffle pair order using expert_id seed
        pair_ids = list(actual_pairs.keys())
        random.seed(int(hashlib.md5(expert_id.encode()).hexdigest(), 16))
        random.shuffle(pair_ids)

        # Build ordered response list with pair labels
        response_list = []
        for pid in pair_ids:
            resps = actual_pairs[pid]
            # Randomize A/B within this pair using hash(expert_id + pair_id)
            pair_seed = int(hashlib.md5((expert_id + pid).encode()).hexdigest(), 16)
            if pair_seed % 2 == 1:
                resps = [resps[1], resps[0]]

            for idx, r in enumerate(resps):
                item = r.to_dict()
                item['rated'] = r.id in rated_ids
                item['pair_label'] = 'Response A' if idx == 0 else 'Response B'
                item['pair_size'] = 2
                response_list.append(item)

        # Append singles at the end
        random.seed(int(hashlib.md5(expert_id.encode()).hexdigest(), 16) + 1)
        random.shuffle(singles)
        for r in singles:
            item = r.to_dict()
            item['rated'] = r.id in rated_ids
            item['pair_label'] = ''
            item['pair_size'] = 1
            response_list.append(item)

        return jsonify({
            'responses': response_list,
            'total': len(response_list),
            'rated_count': len(rated_ids),
            'pair_count': len(actual_pairs),
            'single_count': len(singles)
        })

    except Exception as e:
        logger.error(f"Error getting responses: {e}")
        return jsonify({'error': str(e)}), 500


@expert_agent_rating_bp.route('/ratings', methods=['POST'])
def submit_rating():
    """Submit a rating for a response."""
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    required_fields = ['expert_id', 'response_id', 'accuracy', 'relevance',
                       'groundedness', 'analytical_depth', 'helpfulness']

    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400

    # Validate ratings are 1-5
    rating_fields = ['accuracy', 'relevance', 'groundedness',
                     'analytical_depth', 'helpfulness']
    for field in rating_fields:
        val = data.get(field)
        if not isinstance(val, int) or val < 1 or val > 5:
            return jsonify({'error': f'{field} must be an integer between 1 and 5'}), 400

    try:
        # Check if response exists
        response = AgentResponse.query.get(data['response_id'])
        if not response:
            return jsonify({'error': 'Response not found'}), 404

        # Check if already rated by this expert
        existing = ExpertAgentRating.query.filter_by(
            expert_id=data['expert_id'],
            response_id=data['response_id']
        ).first()

        if existing:
            # Update existing rating
            existing.accuracy = data['accuracy']
            existing.relevance = data['relevance']
            existing.groundedness = data['groundedness']
            existing.analytical_depth = data['analytical_depth']
            existing.helpfulness = data['helpfulness']
            existing.comment = data.get('comment', '')
            db.session.commit()
            return jsonify({'success': True, 'message': 'Rating updated', 'id': existing.id})

        # Create new rating
        rating = ExpertAgentRating(
            expert_id=data['expert_id'],
            response_id=data['response_id'],
            accuracy=data['accuracy'],
            relevance=data['relevance'],
            groundedness=data['groundedness'],
            analytical_depth=data['analytical_depth'],
            helpfulness=data['helpfulness'],
            comment=data.get('comment', '')
        )
        db.session.add(rating)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Rating submitted', 'id': rating.id})

    except Exception as e:
        logger.error(f"Error submitting rating: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@expert_agent_rating_bp.route('/rating/<int:response_id>', methods=['GET'])
def get_rating(response_id):
    """Get an expert's rating for a specific response."""
    expert_id = request.args.get('expert_id')
    if not expert_id:
        return jsonify({'error': 'expert_id is required'}), 400

    try:
        rating = ExpertAgentRating.query.filter_by(
            expert_id=expert_id,
            response_id=response_id
        ).first()

        if rating:
            return jsonify({'rating': rating.to_dict()})
        else:
            return jsonify({'rating': None})

    except Exception as e:
        logger.error(f"Error getting rating: {e}")
        return jsonify({'error': str(e)}), 500


@expert_agent_rating_bp.route('/progress/<expert_id>', methods=['GET'])
def get_progress(expert_id):
    """Get expert's rating progress."""
    try:
        total_responses = AgentResponse.query.count()
        rated_count = ExpertAgentRating.query.filter_by(expert_id=expert_id).count()

        return jsonify({
            'expert_id': expert_id,
            'total_responses': total_responses,
            'rated_count': rated_count,
            'remaining': total_responses - rated_count,
            'progress_pct': round(100 * rated_count / total_responses, 1) if total_responses > 0 else 0
        })

    except Exception as e:
        logger.error(f"Error getting progress: {e}")
        return jsonify({'error': str(e)}), 500


@expert_agent_rating_bp.route('/stats', methods=['GET'])
def get_stats():
    """Get overall rating statistics (for admin/research view)."""
    try:
        total_responses = AgentResponse.query.count()
        total_ratings = ExpertAgentRating.query.count()

        # Get unique experts
        experts = db.session.query(ExpertAgentRating.expert_id).distinct().all()
        expert_list = [e[0] for e in experts]

        return jsonify({
            'total_responses': total_responses,
            'total_ratings': total_ratings,
            'unique_experts': len(expert_list),
            'experts': expert_list
        })

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'error': str(e)}), 500


# Helper function to add a response to the rating pool (called from agent routes)
def add_response_to_pool(agent_version: str, query: str, response: str, conversation_id: str = None):
    """Add an agent response to the rating pool."""
    try:
        agent_response = AgentResponse(
            agent_version=agent_version,
            query_text=query,
            response_text=response,
            conversation_id=conversation_id
        )
        db.session.add(agent_response)
        db.session.commit()
        logger.info(f"Added response to rating pool: {agent_response.id}")
        return agent_response.id
    except Exception as e:
        logger.error(f"Error adding response to pool: {e}")
        db.session.rollback()
        return None
