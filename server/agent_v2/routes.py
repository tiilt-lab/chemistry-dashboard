"""
API Routes for BLINC Agent V2

New /api/v2/agent/* endpoints that coexist with legacy v1 endpoints.
"""

import uuid
import logging
from flask import Blueprint, request, jsonify

from .graph import get_default_graph
from .state import create_initial_state

logger = logging.getLogger(__name__)

agent_v2_bp = Blueprint('agent_v2', __name__)

# Store conversation contexts (in production, use Redis)
_conversation_contexts = {}


@agent_v2_bp.route('/api/v2/agent/query', methods=['POST'])
def query_v2():
    """
    Process query through LangGraph agent.

    Request body:
    {
        "query": "What was discussed in the Dinosaurs session?",
        "conversation_id": "optional-uuid",
        "session_device_id": null  // Optional pre-focus
    }

    Response:
    {
        "success": true,
        "answer": "...",
        "conversation_id": "uuid",
        "confidence": 0.85,
        "citations": [...],
        "tools_used": [...],
        "metadata": {...}
    }
    """
    data = request.get_json()

    query_text = data.get('query', '')
    conversation_id = data.get('conversation_id') or str(uuid.uuid4())
    session_device_id = data.get('session_device_id')

    if not query_text:
        return jsonify({
            "success": False,
            "error": "Query is required"
        }), 400

    logger.info(f"V2 Agent query: '{query_text[:100]}...' (conv: {conversation_id[:8]})")

    # Get or create conversation context
    conversation_context = _conversation_contexts.get(conversation_id, {})

    try:
        # Get compiled graph
        graph = get_default_graph()

        # Create initial state
        initial_state = create_initial_state(
            query=query_text,
            session_device_id=session_device_id,
            conversation_context=conversation_context
        )

        # Add messages for LangGraph
        initial_state["messages"] = [{"role": "user", "content": query_text}]

        # Run graph with checkpointing
        output = graph.invoke(
            initial_state,
            config={"configurable": {"thread_id": conversation_id}}
        )

        # Update conversation context for multi-turn persistence
        _conversation_contexts[conversation_id] = {
            "current_session_focus": output.get("current_session_focus"),
            "previous_session_focus": output.get("previous_session_focus"),
            "current_speaker_focus": output.get("current_speaker_focus"),
            "session_history": output.get("session_history", []),
            "compared_sessions": output.get("compared_sessions", [])
        }

        # Build response
        metadata = output.get("response_metadata", {})

        response = {
            "success": True,
            "answer": output.get("final_answer", ""),
            "conversation_id": conversation_id,
            "confidence": output.get("confidence", 0.5),
            "citations": output.get("citations", []),
            "tools_used": metadata.get("tools_used", []),
            "metadata": metadata,
            # Legacy RAG UI fields for frontend compatibility
            "query_type": metadata.get("query_type"),
            "search_level": metadata.get("search_level"),
            "results": metadata.get("results"),
            "session_results": metadata.get("session_results"),
            "speaker_results": metadata.get("speaker_results"),
            "comparison": metadata.get("comparison"),
            "timeline": metadata.get("timeline"),
            "insights": metadata.get("insights"),
            "total_found": metadata.get("total_found", 0)
        }

        # Add clarification info if needed
        if output.get("needs_clarification"):
            response["needs_clarification"] = True
            response["clarification_options"] = output.get("clarification_options", [])

        logger.info(f"V2 Agent response: {len(response['answer'])} chars, "
                   f"confidence={response['confidence']:.2f}")

        return jsonify(response)

    except Exception as e:
        logger.exception("V2 Agent error")
        return jsonify({
            "success": False,
            "error": str(e),
            "conversation_id": conversation_id
        }), 500


@agent_v2_bp.route('/api/v2/agent/context', methods=['GET'])
def get_context():
    """Get current conversation context."""
    conversation_id = request.args.get('conversation_id')

    if not conversation_id:
        return jsonify({"error": "conversation_id required"}), 400

    context = _conversation_contexts.get(conversation_id, {})

    return jsonify({
        "conversation_id": conversation_id,
        "context": context
    })


@agent_v2_bp.route('/api/v2/agent/context', methods=['DELETE'])
def clear_context():
    """Clear conversation context."""
    conversation_id = request.args.get('conversation_id')

    if not conversation_id:
        return jsonify({"error": "conversation_id required"}), 400

    if conversation_id in _conversation_contexts:
        del _conversation_contexts[conversation_id]

    return jsonify({
        "success": True,
        "conversation_id": conversation_id
    })


@agent_v2_bp.route('/api/v2/agent/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        # Quick check that graph can be created
        graph = get_default_graph()
        return jsonify({
            "status": "healthy",
            "version": "v2",
            "graph_initialized": graph is not None
        })
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500
