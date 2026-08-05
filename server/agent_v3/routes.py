"""
API Routes for BLINC Agent V3

Clean API endpoints for the Ultra Agent.
"""

import logging
import uuid
from flask import Blueprint, request, jsonify, session

from .graph import run_agent
from .nodes.input_processor import should_reset_context

logger = logging.getLogger(__name__)

AGENT_VERSION = 'v3'

# Create blueprint
agent_v3_bp = Blueprint('agent_v3', __name__, url_prefix='/api/v3/agent')

# In-memory conversation context storage (for multi-turn within session)
# Database storage is used for persistence across sessions
_conversation_contexts = {}

# Default user ID for unauthenticated requests (user id 1 = llmblinc)
DEFAULT_USER_ID = 1


def _get_user_id():
    """Get user ID from session or use default."""
    user_dict = session.get('user')
    if user_dict and user_dict.get('id'):
        return user_dict['id']
    return DEFAULT_USER_ID


def _save_conversation_to_db(conversation_id: str, query: str, result: dict,
                              user_id: int, session_device_id: int = None):
    """Save conversation and messages to database."""
    try:
        import database as db_helper

        # Check if conversation exists
        existing = db_helper.get_agent_conversations(conversation_id=conversation_id)

        if not existing:
            # Create new conversation with the specific ID
            # NOTE: We create directly with the conversation_id to avoid duplicates
            # (create_agent_conversation() generates a new ID, which would cause duplication)
            from tables.agent_conversation import AgentConversation
            from app import db
            title = query[:50] + "..." if len(query) > 50 else query
            conv = AgentConversation(
                user_id=user_id,
                session_device_id=session_device_id,
                title=title,
                agent_version=AGENT_VERSION
            )
            conv.id = conversation_id  # Use the specific ID from the response
            db.session.add(conv)
            db.session.commit()
            logger.debug(f"Created new conversation {conversation_id[:8]}")
        else:
            # Update last_active timestamp
            existing.touch()
            from app import db
            db.session.commit()

        # Save user message
        db_helper.add_agent_message(
            conversation_id=conversation_id,
            role='user',
            content=query
        )

        # Save assistant message
        db_helper.add_agent_message(
            conversation_id=conversation_id,
            role='assistant',
            content=result.get('final_answer', ''),
            citations=result.get('citations', []),
            tools_used=result.get('tools_used', []),
            reasoning_trace=result.get('thought_history', []),
            confidence=result.get('confidence', 0.0)
        )

        logger.debug(f"Saved conversation {conversation_id[:8]} to database")

    except Exception as e:
        logger.error(f"Error saving conversation to database: {e}")
        # Don't fail the request if DB save fails


@agent_v3_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'agent_version': 'v3',
        'features': [
            'intelligent_reasoning',
            'self_reflective_rag',
            'query_rewriting',
            'multi_turn_context'
        ]
    })


@agent_v3_bp.route('/query', methods=['POST'])
def query():
    """
    Main query endpoint for the Ultra Agent.

    Request body:
    {
        "query": "Your question here",
        "conversation_id": "optional-id",
        "session_device_id": optional_int
    }

    Response:
    {
        "answer": "The agent's response",
        "confidence": 0.0-1.0,
        "citations": [...],
        "tools_used": [...],
        "follow_up_suggestions": [...],
        "conversation_id": "uuid",
        "success": true/false,
        "needs_clarification": false,
        "error": null
    }
    """
    try:
        data = request.get_json()

        query_text = data.get('query', '').strip()
        if not query_text:
            return jsonify({'error': 'Query is required'}), 400

        # Get or create conversation ID
        conversation_id = data.get('conversation_id') or str(uuid.uuid4())

        # Get conversation context
        context = _conversation_contexts.get(conversation_id, {}).copy()

        # Check for context reset (comparison queries, topic switches)
        if should_reset_context(query_text):
            # Save previous focus for potential "go back" later
            if context.get('current_session_focus'):
                context['previous_session_focus'] = context['current_session_focus']
            context['current_session_focus'] = None
            logger.info(f"[{conversation_id[:8]}] Context reset due to topic switch/comparison")

        # Add session context if provided (explicit override from frontend)
        if data.get('session_device_id'):
            context['current_session_focus'] = data['session_device_id']

        # Extract user steering preferences (Co-Discovery feature)
        steering_options = {}
        if data.get('preferred_representations'):
            steering_options['preferred_representations'] = data['preferred_representations']
        if data.get('exclude_representations'):
            steering_options['exclude_representations'] = data['exclude_representations']
        if data.get('analysis_mode'):
            steering_options['analysis_mode'] = data['analysis_mode']

        if steering_options:
            logger.info(f"[{conversation_id[:8]}] User steering: {steering_options}")

        logger.info(f"Agent V3 query: '{query_text}' (conversation={conversation_id})")

        # Run the agent
        result = run_agent(
            query=query_text,
            conversation_id=conversation_id,
            conversation_context=context,
            steering_options=steering_options if steering_options else None
        )

        # Update conversation context (in-memory for multi-turn)
        _conversation_contexts[conversation_id] = {
            'current_session_focus': result.get('current_session_focus'),
            'previous_session_focus': result.get('previous_session_focus'),
            'session_history': result.get('session_history', []),
            'compared_sessions': result.get('compared_sessions', []),
            'current_speaker_focus': result.get('current_speaker_focus')
        }

        # Save to database for persistence
        user_id = _get_user_id()
        session_device_id = data.get('session_device_id')
        _save_conversation_to_db(
            conversation_id=conversation_id,
            query=query_text,
            result=result,
            user_id=user_id,
            session_device_id=session_device_id
        )

        # Format response
        response = {
            'answer': result.get('final_answer', ''),
            'confidence': result.get('confidence', 0.0),
            'citations': result.get('citations', []),
            'tools_used': result.get('tools_used', []),
            'follow_up_suggestions': result.get('follow_ups', []),
            'conversation_id': conversation_id,
            'success': result.get('success', True),
            'needs_clarification': result.get('needs_clarification', False),
            'error': result.get('error'),

            # Reasoning transparency (AIED 2026 enhancement)
            'reasoning_trace': result.get('reasoning_trace'),
            'verification': result.get('verification'),

            # Debug info (optional)
            'debug': {
                'iterations': result.get('iteration_count', 0),
                'rewrites': result.get('rewrite_count', 0),
                'thoughts': result.get('thought_history', [])
            } if data.get('include_debug') else None
        }

        return jsonify(response)

    except Exception as e:
        logger.error(f"Query error: {e}", exc_info=True)
        return jsonify({
            'answer': f"An error occurred: {str(e)}",
            'confidence': 0.0,
            'citations': [],
            'tools_used': [],
            'follow_up_suggestions': [],
            'success': False,
            'error': str(e)
        }), 500


@agent_v3_bp.route('/context', methods=['GET'])
def get_context():
    """Get stored conversation context."""
    conversation_id = request.args.get('conversation_id')

    if not conversation_id:
        return jsonify({'error': 'conversation_id required'}), 400

    context = _conversation_contexts.get(conversation_id, {})

    return jsonify({
        'conversation_id': conversation_id,
        'context': context
    })


@agent_v3_bp.route('/context', methods=['DELETE'])
def clear_context():
    """Clear conversation context."""
    conversation_id = request.args.get('conversation_id')

    if conversation_id:
        _conversation_contexts.pop(conversation_id, None)
        return jsonify({'success': True, 'message': f'Cleared context for {conversation_id}'})
    else:
        _conversation_contexts.clear()
        return jsonify({'success': True, 'message': 'Cleared all contexts'})


@agent_v3_bp.route('/tools', methods=['GET'])
def list_tools():
    """List available tools."""
    from .prompts.tool_descriptions import TOOL_DESCRIPTIONS

    tools = []
    for name, info in TOOL_DESCRIPTIONS.items():
        tools.append({
            'name': name,
            'description': info['description'].strip()[:200],
            'parameters': list(info.get('parameters', {}).keys())
        })

    return jsonify({
        'tools': tools,
        'count': len(tools)
    })


@agent_v3_bp.route('/metrics', methods=['GET'])
def get_metrics():
    """
    Get agent performance metrics.

    Useful for:
    - Paper claims about grounding rate
    - Performance monitoring (cache hit rate)
    - Debugging
    """
    from .nodes.execute_tool import get_cache_metrics
    from .nodes.synthesize import get_citation_metrics

    cache_metrics = get_cache_metrics()
    citation_metrics = get_citation_metrics()

    return jsonify({
        'cache': cache_metrics,
        'citations': citation_metrics,
        'summary': {
            'cache_hit_rate': f"{cache_metrics['hit_rate']:.1%}",
            'grounding_rate': f"{citation_metrics['grounding_rate']:.1%}",
            'total_citations': citation_metrics['total_citations_generated']
        }
    })


@agent_v3_bp.route('/cache', methods=['DELETE'])
def clear_cache():
    """Clear the result cache for a conversation or all."""
    from .nodes.execute_tool import clear_conversation_cache

    conversation_id = request.args.get('conversation_id')

    if conversation_id:
        cleared = clear_conversation_cache(conversation_id)
        return jsonify({
            'success': True,
            'message': f'Cleared {cleared} cache entries for {conversation_id}'
        })
    else:
        # Clear all requires accessing the global cache
        from .nodes.execute_tool import _result_cache
        count = len(_result_cache)
        _result_cache.clear()
        return jsonify({
            'success': True,
            'message': f'Cleared all {count} cache entries'
        })


# =============================================================================
# CONVERSATION PERSISTENCE ENDPOINTS
# =============================================================================

@agent_v3_bp.route('/conversations', methods=['GET'])
def list_conversations():
    """
    List all conversations for the left panel.
    Uses database storage for persistence.
    """
    try:
        import database as db_helper
        user_id = _get_user_id()

        # Get conversations from database (filtered by agent version)
        conversations = db_helper.get_agent_conversations(user_id=user_id, agent_version='v3')

        # Format for frontend
        formatted = []
        for conv in conversations:
            formatted.append({
                'id': conv.id,
                'conversation_id': conv.id,
                'title': conv.title or 'Conversation',
                'created_at': conv.created_at.isoformat() if conv.created_at else None,
                'updated_at': conv.last_active.isoformat() if conv.last_active else None
            })

        return jsonify({
            'conversations': formatted,
            'count': len(formatted)
        })

    except Exception as e:
        logger.error(f"List conversations error: {e}")
        return jsonify({'conversations': [], 'count': 0, 'error': str(e)})


@agent_v3_bp.route('/conversations/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """
    Get a specific conversation with its messages.
    """
    try:
        import database as db_helper

        # Get conversation (returns single object when filtered by conversation_id)
        conv = db_helper.get_agent_conversations(conversation_id=conversation_id)
        if not conv:
            return jsonify({
                'conversation_id': conversation_id,
                'error': 'Conversation not found',
                'messages': []
            }), 404

        # Get messages
        messages = db_helper.get_agent_messages(conversation_id=conversation_id)

        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                'id': msg.id,
                'role': msg.role,
                'content': msg.content,
                'citations': msg.citations,
                'tools_used': msg.tools_used,
                'created_at': msg.created_at.isoformat() if msg.created_at else None
            })

        return jsonify({
            'conversation_id': conversation_id,
            'title': conv.title or 'Conversation',
            'messages': formatted_messages,
            'created_at': conv.created_at.isoformat() if conv.created_at else None,
            'updated_at': conv.last_active.isoformat() if conv.last_active else None
        })

    except Exception as e:
        logger.error(f"Get conversation error: {e}")
        return jsonify({'error': str(e)}), 500


@agent_v3_bp.route('/conversations/<conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    """Delete a conversation and its messages."""
    try:
        import database as db_helper

        # Delete from database
        db_helper.delete_agent_conversation(conversation_id)

        # Clear in-memory context
        _conversation_contexts.pop(conversation_id, None)

        return jsonify({'success': True, 'message': f'Deleted conversation {conversation_id}'})

    except Exception as e:
        logger.error(f"Delete conversation error: {e}")
        return jsonify({'error': str(e)}), 500


@agent_v3_bp.route('/conversations', methods=['POST'])
def create_conversation():
    """Create a new conversation explicitly."""
    try:
        import database as db_helper

        data = request.get_json() or {}
        title = data.get('title', 'New Conversation')
        user_id = _get_user_id()

        # Create in database (with agent version)
        conv = db_helper.create_agent_conversation(
            user_id=user_id,
            title=title,
            agent_version='v3'
        )

        return jsonify({
            'conversation_id': conv.id,
            'title': title,
            'created': True
        })

    except Exception as e:
        logger.error(f"Create conversation error: {e}")
        return jsonify({'error': str(e)}), 500
