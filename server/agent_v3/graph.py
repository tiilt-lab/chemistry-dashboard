"""
LangGraph Workflow for BLINC Agent V3

A clean, intelligent agent workflow with query-adaptive reasoning
and source verification for AIED 2026.

Architecture: Simplified PRAS (4 stages instead of 5, no ReAct fallback)

    START
      ↓
    process_input (resolve references)
      ↓
    query_decomposer (Stage 1: identify constructs, generate sub-goals)
      ↓
    ┌──────────────────┬────────────────────────────────────────────┐
    ↓                                                               ↓
  fast_path                                                    PRAS PATH
    │                                                               ↓
    │                                                   targeted_retriever (Stage 2) ←┐
    │                                                               ↓                  │
    │                                                         [reflection loop] ───────┘
    │                                                               ↓
    │                                                   cross_rep_reasoner (Stage 3)
    │                                                               ↓
    │                                                   grounded_synthesizer (Stage 4)
    │                                                               ↓
    └───────────────────────────────────────→ synthesize ←──────────┘
                                                  ↓
                                               verify
                                                  ↓
                                               reflect
                                                  ↓
                                            format_response
                                                  ↓
                                                 END

Key Paths:
- Fast Path: Simple direct queries → direct tool execution (~2-3s)
- PRAS Path: Complex queries → cross-rep reasoning (~15-30s)

Simplifications from original V3:
- Removed ReAct fallback path (was unreliable)
- Removed pras_plan node (retrieval is now deterministic)
- 4 stages instead of 5: decompose → retrieve → reason → synthesize

AIED 2026 Theme: "Artifact-Grounded Analytics: Agentic Reasoning Across
Heterogeneous Representations"
"""

import logging
from typing import Dict, Any, Literal

from langgraph.graph import StateGraph, END

from .state import AgentState, create_initial_state
from .nodes import (
    process_input,
    synthesize,
    reflect,
    format_response,
    # PRAS nodes (simplified 4-stage)
    decompose_query,
    targeted_retrieve,
    reason_across_representations,
    synthesize_grounded_response
)
from .nodes.query_router import execute_fast_path
from .nodes.verify_claims import verify_claims

# NOTE: ReAct path removed (was unreliable), pras_plan node removed (deterministic retrieval)

logger = logging.getLogger(__name__)


def create_agent_graph() -> StateGraph:
    """
    Create the simplified PRAS Agent workflow graph.

    Simplified from 5 stages to 4:
    - Removed pras_plan node (retrieval is now deterministic)
    - Removed ReAct path (was unreliable fallback)

    Returns:
        Configured StateGraph ready for compilation
    """
    # Create the graph with our state type
    graph = StateGraph(AgentState)

    # === Add nodes ===

    # Input processing
    graph.add_node("process_input", process_input)

    # Query decomposition (Stage 1)
    graph.add_node("decompose", decompose_query)

    # Fast path for simple queries
    graph.add_node("fast_path", execute_fast_path)

    # === PRAS Path (Stages 2-4, simplified) ===

    # Stage 2: Targeted Retrieval with Reflection (deterministic planning)
    graph.add_node("pras_retrieve", targeted_retrieve)

    # Stage 3: Cross-Representation Reasoning
    graph.add_node("pras_reason", reason_across_representations)

    # Stage 4: Grounded Synthesis
    graph.add_node("pras_synthesize", synthesize_grounded_response)

    # Synthesis and reflection (shared by both paths)
    graph.add_node("synthesize", synthesize)
    graph.add_node("verify", verify_claims)
    graph.add_node("reflect", reflect)

    # Final formatting
    graph.add_node("format", format_response)

    # === Add edges ===

    # Start -> process input -> decompose
    graph.set_entry_point("process_input")
    graph.add_edge("process_input", "decompose")

    # Decompose -> conditional routing (fast_path or pras only)
    graph.add_conditional_edges(
        "decompose",
        _route_after_decompose,
        {
            "fast_path": "fast_path",
            "pras": "pras_retrieve"  # Direct to retrieve, skip planning
        }
    )

    # Fast path -> synthesize
    graph.add_edge("fast_path", "synthesize")

    # === PRAS Path edges ===

    # Stage 2 -> conditional (continue retrieval or move to reasoning)
    graph.add_conditional_edges(
        "pras_retrieve",
        _route_pras_retrieval,
        {
            "continue": "pras_retrieve",  # Reflection loop
            "reason": "pras_reason"
        }
    )

    # Stage 3 -> Stage 4
    graph.add_edge("pras_reason", "pras_synthesize")

    # Stage 4 -> verify
    graph.add_edge("pras_synthesize", "verify")

    # Shared ending: synthesize -> verify -> reflect -> format
    graph.add_edge("synthesize", "verify")
    graph.add_edge("verify", "reflect")
    graph.add_edge("reflect", "format")

    # Format -> END
    graph.add_edge("format", END)

    return graph


def _route_after_decompose(state: Dict[str, Any]) -> str:
    """
    Route after query decomposition (Stage 1).

    Simplified routing: only fast_path or pras (no ReAct fallback).
    """
    route = state.get('route', 'pras')

    if route == 'fast_path':
        return 'fast_path'

    # Default to PRAS for all other cases (no ReAct fallback)
    return 'pras'


def _route_pras_retrieval(state: Dict[str, Any]) -> str:
    """
    Route within PRAS retrieval loop.

    Returns 'reason' when retrieval is complete, 'continue' to keep retrieving.
    """
    next_action = state.get('next_action', 'continue')

    if next_action == 'reason':
        return 'reason'

    # Check if all subgoals are done
    sub_goals = state.get('sub_goals', [])
    current_idx = state.get('current_subgoal_index', 0)

    if current_idx >= len(sub_goals):
        # Check if there are discovered sessions that need artifact fetching
        discovered_sessions = state.get('_discovered_sessions', [])
        if discovered_sessions:
            logger.info(f"[Router] {len(discovered_sessions)} discovered sessions need artifacts - continuing")
            return 'continue'
        return 'reason'

    # Check iteration limits
    iteration = state.get('iteration_count', 0) + 1
    max_iter = state.get('max_iterations', 8)

    if iteration >= max_iter:
        logger.warning(f"PRAS retrieval hit max iterations ({max_iter})")
        return 'reason'

    return 'continue'


# Compiled graph (singleton)
_compiled_graph = None


def get_compiled_graph():
    """Get the compiled graph (singleton)."""
    global _compiled_graph

    if _compiled_graph is None:
        graph = create_agent_graph()
        _compiled_graph = graph.compile()
        logger.info("Agent V3 graph compiled successfully with PRAS architecture")

    return _compiled_graph


def reset_graph():
    """Reset the compiled graph (for testing)."""
    global _compiled_graph
    _compiled_graph = None


def run_agent(
    query: str,
    conversation_id: str,
    conversation_context: Dict[str, Any] = None,
    steering_options: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Run the agent on a query.

    Args:
        query: User's query
        conversation_id: Unique conversation identifier
        conversation_context: Optional context from previous turns
        steering_options: Optional user steering preferences (Co-Discovery)
            - preferred_representations: List of representations to focus on
            - exclude_representations: List of representations to exclude
            - analysis_mode: 'explore', 'compare', 'trace', or None

    Returns:
        Agent response with answer, citations, etc.
    """
    logger.info(f"Running agent V3 on query: '{query}'")

    # Create initial state
    initial_state = create_initial_state(
        query=query,
        conversation_id=conversation_id,
        conversation_context=conversation_context
    )

    # Apply user steering options if provided (Co-Discovery feature)
    if steering_options:
        if steering_options.get('preferred_representations'):
            initial_state['preferred_representations'] = steering_options['preferred_representations']
            logger.info(f"User steering: prefer {steering_options['preferred_representations']}")
        if steering_options.get('exclude_representations'):
            initial_state['exclude_representations'] = steering_options['exclude_representations']
            logger.info(f"User steering: exclude {steering_options['exclude_representations']}")
        if steering_options.get('analysis_mode'):
            initial_state['analysis_mode'] = steering_options['analysis_mode']
            logger.info(f"User steering: mode = {steering_options['analysis_mode']}")

    # Get compiled graph
    graph = get_compiled_graph()

    # Run the graph
    try:
        final_state = graph.invoke(initial_state)

        logger.info(f"Agent completed: confidence={final_state.get('confidence', 0):.2f}, "
                   f"iterations={final_state.get('iteration_count', 0)}, "
                   f"pras_stage={final_state.get('pras_stage', 'n/a')}")

        return final_state

    except Exception as e:
        logger.error(f"Agent error: {e}", exc_info=True)

        return {
            'final_answer': f"I encountered an error processing your request: {str(e)}",
            'confidence': 0.0,
            'citations': [],
            'tools_used': [],
            'follow_ups': ['Try rephrasing your question'],
            'success': False,
            'error': str(e),
            'current_session_focus': conversation_context.get('current_session_focus') if conversation_context else None,
            'session_history': conversation_context.get('session_history', []) if conversation_context else []
        }
