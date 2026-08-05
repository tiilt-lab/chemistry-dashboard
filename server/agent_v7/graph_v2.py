"""
Simplified Graph for BLINC Agent V7

A minimal LangGraph-based architecture:
1. process_input - Extract context, resolve references
2. agent_loop - ReAct loop with tool calling
3. format_response - Final formatting

This replaces the complex PRAS architecture with a simple, flexible flow.
"""

import logging
from typing import Dict, Any, TypedDict, List, Optional

from langgraph.graph import StateGraph, END

from .react_agent import run_agent, AgentResponse
from .memory import get_memory, ConversationMemory

logger = logging.getLogger(__name__)


# =============================================================================
# Simplified State
# =============================================================================

class AgentState(TypedDict, total=False):
    """
    Minimal state for the simplified agent.

    Most state management is now in ConversationMemory,
    so this just tracks per-request data.
    """
    # Input
    conversation_id: str
    original_query: str
    current_query: str

    # Context
    session_focus: Optional[int]
    speaker_focus: Optional[str]

    # Steering
    preferred_representations: List[str]
    exclude_representations: List[str]

    # Output
    final_answer: str
    evidence: List[Dict[str, Any]]
    tool_calls: List[Dict[str, Any]]
    suggestions: List[str]

    # Metadata
    error: Optional[str]
    processing_time_ms: float


# =============================================================================
# Node Functions
# =============================================================================

def process_input(state: AgentState) -> AgentState:
    """
    Process input and prepare for agent loop.

    Extracts session/speaker references and loads memory context.
    """
    logger.info(f"[Graph] Processing input: {state.get('original_query', '')[:50]}...")

    conversation_id = state.get('conversation_id', 'default')
    query = state.get('original_query', '')

    # Get memory
    memory = get_memory(conversation_id)

    # Extract any session reference from query
    session_id = memory.extract_session_from_text(query)
    speaker = memory.extract_speaker_from_text(query)

    # Priority: (1) session extracted from query text, (2) explicitly provided by frontend,
    # (3) memory's stored session_focus from prior turns
    explicit_focus = state.get('session_focus')
    resolved_session = session_id or explicit_focus or memory.session_focus

    return {
        **state,
        'current_query': query,
        'session_focus': resolved_session,
        'speaker_focus': speaker or memory.speaker_focus,
    }


def run_react_agent(state: AgentState) -> AgentState:
    """
    Run the ReAct agent loop.

    This is where the main work happens - the agent decides
    what tools to call and synthesizes the response.
    """
    import time
    start_time = time.time()

    logger.info("[Graph] Running ReAct agent")

    conversation_id = state.get('conversation_id', 'default')
    query = state.get('current_query', state.get('original_query', ''))

    try:
        # Run the agent (pass session_focus so the hint reaches the prompt)
        session_focus = state.get('session_focus')
        response: AgentResponse = run_agent(conversation_id, query, session_focus=session_focus)

        elapsed_ms = (time.time() - start_time) * 1000

        return {
            **state,
            'final_answer': response.answer,
            'evidence': response.evidence,
            'tool_calls': [
                {'name': tc.name, 'params': tc.params, 'reason': tc.reason}
                for tc in response.tool_calls_made
            ],
            'suggestions': response.suggested_explorations,
            'session_focus': response.session_focus,
            'speaker_focus': response.speaker_focus,
            'processing_time_ms': elapsed_ms,
            'error': None,
        }

    except Exception as e:
        logger.error(f"[Graph] Agent error: {e}")
        elapsed_ms = (time.time() - start_time) * 1000

        return {
            **state,
            'final_answer': f"I encountered an error processing your request: {str(e)}",
            'evidence': [],
            'tool_calls': [],
            'suggestions': [],
            'processing_time_ms': elapsed_ms,
            'error': str(e),
        }


def format_response(state: AgentState) -> AgentState:
    """
    Format final response for output.

    Adds suggestions and ensures consistent formatting.
    """
    logger.info("[Graph] Formatting response")

    answer = state.get('final_answer', '')
    suggestions = state.get('suggestions', [])

    return {
        **state,
        'final_answer': answer,
    }


# =============================================================================
# Graph Construction
# =============================================================================

def create_agent_graph() -> StateGraph:
    """
    Create the simplified agent graph.

    Flow: process_input -> agent_loop -> format_response -> END
    """
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("process_input", process_input)
    graph.add_node("agent_loop", run_react_agent)
    graph.add_node("format_response", format_response)

    # Add edges (simple linear flow)
    graph.set_entry_point("process_input")
    graph.add_edge("process_input", "agent_loop")
    graph.add_edge("agent_loop", "format_response")
    graph.add_edge("format_response", END)

    return graph.compile()


# =============================================================================
# Main Entry Point
# =============================================================================

# Compiled graph instance
_compiled_graph = None


def get_graph():
    """Get or create the compiled graph."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = create_agent_graph()
    return _compiled_graph


def invoke_agent(
    query: str,
    conversation_id: str = "default",
    session_focus: int = None,
    preferred_representations: List[str] = None,
    exclude_representations: List[str] = None,
) -> Dict[str, Any]:
    """
    Invoke the agent with a query.

    This is the main entry point for external callers.

    Args:
        query: User's query
        conversation_id: Unique conversation ID for memory
        session_focus: Optional session ID to focus on
        preferred_representations: Optional list of preferred artifacts
        exclude_representations: Optional list of artifacts to skip

    Returns:
        Dict with final_answer, evidence, tool_calls, etc.
    """
    graph = get_graph()

    initial_state: AgentState = {
        'conversation_id': conversation_id,
        'original_query': query,
        'current_query': query,
        'session_focus': session_focus,
        'speaker_focus': None,
        'preferred_representations': preferred_representations or [],
        'exclude_representations': exclude_representations or [],
        'final_answer': '',
        'evidence': [],
        'tool_calls': [],
        'suggestions': [],
        'error': None,
        'processing_time_ms': 0,
    }

    # Update memory with steering if provided
    if preferred_representations or exclude_representations:
        memory = get_memory(conversation_id)
        memory.update_steering(
            preferred=preferred_representations,
            excluded=exclude_representations
        )

    # Run the graph
    result = graph.invoke(initial_state)

    tool_calls = result.get('tool_calls', [])

    return {
        'answer': result.get('final_answer', ''),
        'evidence': result.get('evidence', []),
        'tool_calls': tool_calls,
        'tools_used': [tc.get('name') for tc in tool_calls],  # Convenience list
        'iterations': len(tool_calls),  # Approximate iterations
        'suggestions': result.get('suggestions', []),
        'session_focus': result.get('session_focus'),
        'speaker_focus': result.get('speaker_focus'),
        'processing_time_ms': result.get('processing_time_ms', 0),
        'error': result.get('error'),
    }


def reset_conversation(conversation_id: str):
    """Reset conversation memory."""
    from .memory import clear_memory
    clear_memory(conversation_id)
    logger.info(f"[Graph] Reset conversation: {conversation_id}")
