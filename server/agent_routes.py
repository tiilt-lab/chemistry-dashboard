"""
Agent API Routes

Flask blueprint for the agentic RAG system API endpoints.
"""

import logging
from functools import wraps
from flask import Blueprint, request, jsonify, g, Response
import json

logger = logging.getLogger(__name__)

# Create blueprint
agent_bp = Blueprint('agent', __name__, url_prefix='/api/v1/agent')


def verify_login(f):
    """Decorator to verify user is logged in."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import session
        from tables.user import User

        # Use 'user' key (dict) - same as wrappers.py
        user_dict = session.get('user')
        if not user_dict:
            return jsonify({'error': 'Not authenticated'}), 401

        user_id = user_dict.get('id')
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 401

        g.user = user
        g.user_id = user_id
        return f(*args, **kwargs)

    return decorated_function


@agent_bp.route('/query', methods=['POST'])
@verify_login
def query():
    """
    Process a user query through the agent system.

    Request body:
    {
        "query": "What did students say about X?",
        "conversation_id": "optional-uuid",
        "session_device_id": optional_int
    }

    Response:
    {
        "answer": "Based on the discussion...",
        "citations": [...],
        "confidence": 0.85,
        "reasoning_trace": [...],
        "tools_used": [...],
        "follow_up_suggestions": [...],
        "conversation_id": "uuid",
        "message_id": 123,
        "success": true
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        query_text = data.get('query')
        if not query_text:
            return jsonify({'error': 'Query is required'}), 400

        conversation_id = data.get('conversation_id')
        session_device_id = data.get('session_device_id')

        # Validate session_device_id belongs to user if provided
        if session_device_id:
            if not _verify_session_access(g.user_id, session_device_id):
                return jsonify({'error': 'Access denied to session'}), 403

        # Process query through orchestrator
        from agent import get_orchestrator
        orchestrator = get_orchestrator()

        response = orchestrator.process_query(
            query=query_text,
            user_id=g.user_id,
            conversation_id=conversation_id,
            session_device_id=session_device_id
        )

        return jsonify(response.to_dict())

    except Exception as e:
        logger.error(f"Agent query error: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'success': False
        }), 500


@agent_bp.route('/conversations', methods=['GET'])
@verify_login
def list_conversations():
    """
    List user's agent conversations.

    Query params:
    - limit: Max number of conversations (default 20)

    Response:
    {
        "conversations": [
            {
                "id": "uuid",
                "title": "What did students...",
                "session_device_id": 42,
                "created_at": "2024-01-01T00:00:00",
                "last_active": "2024-01-01T01:00:00"
            }
        ]
    }
    """
    try:
        limit = request.args.get('limit', 1000, type=int)  # Show all conversations by default

        from agent import get_orchestrator
        orchestrator = get_orchestrator()

        conversations = orchestrator.list_conversations(
            user_id=g.user_id,
            limit=limit
        )

        return jsonify({'conversations': conversations})

    except Exception as e:
        logger.error(f"List conversations error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@agent_bp.route('/conversations/<conversation_id>', methods=['GET'])
@verify_login
def get_conversation(conversation_id):
    """
    Get a specific conversation with full history.

    Response:
    {
        "conversation": {
            "id": "uuid",
            "title": "...",
            "session_device_id": 42,
            "created_at": "...",
            "last_active": "..."
        },
        "messages": [
            {
                "id": 1,
                "role": "user",
                "content": "...",
                "created_at": "..."
            },
            {
                "id": 2,
                "role": "assistant",
                "content": "...",
                "citations": [...],
                "confidence": 0.85,
                "created_at": "..."
            }
        ]
    }
    """
    try:
        from agent import get_orchestrator
        orchestrator = get_orchestrator()

        # Get conversation history (verifies ownership)
        messages = orchestrator.get_conversation_history(
            conversation_id=conversation_id,
            user_id=g.user_id
        )

        if messages is None:
            return jsonify({'error': 'Conversation not found or access denied'}), 404

        # Get conversation metadata
        import database as db_helper
        conversation = db_helper.get_agent_conversations(conversation_id=conversation_id)

        return jsonify({
            'conversation': {
                'id': conversation.id,
                'title': conversation.title,
                'session_device_id': conversation.session_device_id,
                'created_at': conversation.created_at.isoformat() if conversation.created_at else None,
                'last_active': conversation.last_active.isoformat() if conversation.last_active else None
            },
            'messages': messages
        })

    except Exception as e:
        logger.error(f"Get conversation error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@agent_bp.route('/conversations/<conversation_id>', methods=['PATCH'])
@verify_login
def rename_conversation(conversation_id):
    """
    Rename a conversation.

    Request body:
    {
        "title": "New conversation title"
    }

    Response:
    {
        "success": true,
        "conversation": {
            "id": "uuid",
            "title": "New conversation title"
        }
    }
    """
    try:
        data = request.get_json()
        new_title = data.get('title', '').strip()

        if not new_title:
            return jsonify({'error': 'Title is required'}), 400

        if len(new_title) > 200:
            return jsonify({'error': 'Title too long (max 200 characters)'}), 400

        import database as db_helper

        # Verify ownership
        conversation = db_helper.get_agent_conversations(conversation_id=conversation_id)
        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404

        if conversation.user_id != g.user_id:
            return jsonify({'error': 'Access denied'}), 403

        # Update title
        db_helper.update_agent_conversation(conversation_id, title=new_title)

        return jsonify({
            'success': True,
            'conversation': {
                'id': conversation_id,
                'title': new_title
            }
        })

    except Exception as e:
        logger.error(f"Rename conversation error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@agent_bp.route('/conversations/<conversation_id>/messages', methods=['GET'])
@verify_login
def get_messages(conversation_id):
    """
    Get messages for a conversation.

    Query params:
    - limit: Max messages (default all)
    - offset: Starting offset (default 0)

    Response:
    {
        "messages": [...]
    }
    """
    try:
        from agent import get_orchestrator
        orchestrator = get_orchestrator()

        messages = orchestrator.get_conversation_history(
            conversation_id=conversation_id,
            user_id=g.user_id
        )

        if messages is None:
            return jsonify({'error': 'Conversation not found or access denied'}), 404

        # Apply pagination
        offset = request.args.get('offset', 0, type=int)
        limit = request.args.get('limit', type=int)

        if offset > 0:
            messages = messages[offset:]
        if limit:
            messages = messages[:limit]

        return jsonify({'messages': messages})

    except Exception as e:
        logger.error(f"Get messages error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@agent_bp.route('/conversations/<conversation_id>', methods=['DELETE'])
@verify_login
def delete_conversation(conversation_id):
    """
    Delete a conversation and all its messages.

    Response:
    {
        "success": true,
        "message": "Conversation deleted"
    }
    """
    try:
        from agent import get_orchestrator
        orchestrator = get_orchestrator()

        success = orchestrator.delete_conversation(
            conversation_id=conversation_id,
            user_id=g.user_id
        )

        if not success:
            return jsonify({'error': 'Conversation not found or access denied'}), 404

        return jsonify({
            'success': True,
            'message': 'Conversation deleted'
        })

    except Exception as e:
        logger.error(f"Delete conversation error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@agent_bp.route('/tools', methods=['GET'])
@verify_login
def list_tools():
    """
    List available agent tools.

    Response:
    {
        "tools": [
            {
                "name": "search_transcript_chunks",
                "description": "...",
                "parameters": {...}
            }
        ]
    }
    """
    try:
        from agent.tools import get_tool_registry

        registry = get_tool_registry()
        tools = registry.get_tool_schemas()

        return jsonify({'tools': tools})

    except Exception as e:
        logger.error(f"List tools error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@agent_bp.route('/classify', methods=['POST'])
@verify_login
def classify_query():
    """
    Classify a query without executing it.
    Useful for debugging and understanding query routing.

    Request body:
    {
        "query": "What did students say about X?"
    }

    Response:
    {
        "intent": "factual",
        "complexity": "simple",
        "required_artifacts": ["transcripts"],
        "suggested_tools": ["search_transcript_chunks"],
        "entities": {...},
        "reasoning": "..."
    }
    """
    try:
        data = request.get_json()
        if not data or not data.get('query'):
            return jsonify({'error': 'Query is required'}), 400

        from agent import QueryClassifier
        classifier = QueryClassifier()

        classification = classifier.classify(data['query'])

        return jsonify(classification.to_dict())

    except Exception as e:
        logger.error(f"Classify query error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


def _verify_session_access(user_id: int, session_device_id: int) -> bool:
    """Verify user has access to a session."""
    try:
        from tables.session_device import SessionDevice

        session_device = SessionDevice.query.get(session_device_id)
        if not session_device:
            return False

        # Check if user owns the session
        return session_device.session.user_id == user_id

    except Exception as e:
        logger.error(f"Session access check error: {e}")
        return False


def register_agent_routes(app):
    """Register the agent blueprint with the Flask app."""
    app.register_blueprint(agent_bp)
    logger.info("Agent routes registered at /api/v1/agent/")
