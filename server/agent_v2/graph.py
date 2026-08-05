"""
LangGraph Agent Workflow for BLINC V2

Defines the main agent workflow using LangGraph StateGraph.
"""

import logging
import os
from typing import Dict, Any, Literal

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from .state import AgentState
from .nodes import (
    input_processor,
    reference_resolver,
    query_classifier,
    react_think,
    plan_generator,
    plan_executor,
    synthesizer,
    response_formatter
)
from .nodes.response import handle_direct_response

logger = logging.getLogger(__name__)


def route_after_classifier(state: Dict[str, Any]) -> Literal["react_think", "plan_gen", "direct_response", "clarification"]:
    """Route based on classification results."""
    next_node = state.get("next_node", "react_think")

    if next_node == "direct_response":
        return "direct_response"
    elif next_node == "clarification":
        return "clarification"
    elif next_node == "plan_gen":
        return "plan_gen"
    else:
        return "react_think"


def route_after_react_think(state: Dict[str, Any]) -> Literal["react_tools", "synthesize"]:
    """Route after ReAct thinking step."""
    if state.get("current_action") == "synthesize":
        return "synthesize"
    return "react_tools"


def route_after_plan_exec(state: Dict[str, Any]) -> Literal["plan_exec", "synthesize"]:
    """Route after plan execution step."""
    plan_steps = state.get("plan_steps", [])
    current_index = state.get("current_step_index", 0)

    if current_index >= len(plan_steps):
        return "synthesize"
    return "plan_exec"


# Tools that expect singular session_device_id (int) not session_device_ids (list)
SINGLE_SESSION_TOOLS = {
    "get_7c_analysis",
    "get_session_summary",
    "get_full_concept_map",
    "get_liwc_metrics",
    "compare_speakers",
    "find_similar_sessions",
    "get_speaker_contribution_graph"
}

# Search tools that need a query parameter
SEARCH_TOOLS = {
    "search_sessions_multi",
    "search_chunks",
    "search_transcript_chunks",
    "search_concept_nodes",
    "search_concept_clusters",
    "search_speakers"
}


def _normalize_tool_params(tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize tool parameters to handle common LLM mistakes.

    Fixes:
    - session_device_ids -> session_device_id for single-session tools
    - Adds default query for search tools
    - Handles list vs int confusion
    """
    if not params:
        params = {}

    params = dict(params)  # Copy to avoid mutation

    # Handle single-session tools that got list instead of int
    if tool_name in SINGLE_SESSION_TOOLS:
        if "session_device_ids" in params and "session_device_id" not in params:
            ids = params.pop("session_device_ids")
            if isinstance(ids, list) and len(ids) > 0:
                params["session_device_id"] = ids[0]
            elif isinstance(ids, int):
                params["session_device_id"] = ids

    # Handle search tools missing query
    if tool_name in SEARCH_TOOLS:
        if "query" not in params or not params.get("query"):
            params["query"] = "main topics discussed"  # Default query

    # Handle metric_filters format for get_sessions_by_metrics
    if tool_name == "get_sessions_by_metrics":
        if "metric_filters" not in params:
            # Try to construct from other params
            filters = {}
            if "metric" in params and "threshold" in params:
                metric = params.pop("metric")
                threshold = params.pop("threshold")
                filters[metric] = (">=", threshold)
            params["metric_filters"] = filters if filters else {}

    return params


def execute_react_tool(state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute the tool selected by ReAct reasoning."""
    tool_name = state.get("current_action", "")
    tool_input = state.get("current_action_input", {})

    if not tool_name or tool_name == "synthesize":
        return {"next_node": "synthesize"}

    logger.info(f"Executing ReAct tool: {tool_name}")

    try:
        # Import tools
        from .tools import (
            search_sessions_multi,
            hybrid_session_search,
            get_sessions_by_metrics,
            get_contrastive_sessions,
            generate_ultra_insights,
            search_speakers,
            find_similar_sessions,
            search_transcript_chunks,
            search_concept_nodes,
            search_concept_clusters,
            get_7c_analysis,
            get_liwc_metrics,
            get_session_summary,
            get_full_concept_map,
            compare_sessions,
            compare_speakers,
            # Graph traversal tools
            get_node_neighbors,
            get_concept_path,
            get_causal_chain,
            get_cluster_subgraph,
            get_speaker_contribution_graph
        )
        from .tools.rag_tools import search_chunks

        # Tool mapping
        tools = {
            "search_sessions_multi": search_sessions_multi,
            "hybrid_session_search": hybrid_session_search,
            "get_sessions_by_metrics": get_sessions_by_metrics,
            "get_contrastive_sessions": get_contrastive_sessions,
            "generate_ultra_insights": generate_ultra_insights,
            "search_speakers": search_speakers,
            "find_similar_sessions": find_similar_sessions,
            "search_transcript_chunks": search_transcript_chunks,
            "search_concept_nodes": search_concept_nodes,
            "search_concept_clusters": search_concept_clusters,
            "search_chunks": search_chunks,
            "get_7c_analysis": get_7c_analysis,
            "get_liwc_metrics": get_liwc_metrics,
            "get_session_summary": get_session_summary,
            "get_full_concept_map": get_full_concept_map,
            "compare_sessions": compare_sessions,
            "compare_speakers": compare_speakers,
            # Graph traversal tools
            "get_node_neighbors": get_node_neighbors,
            "get_concept_path": get_concept_path,
            "get_causal_chain": get_causal_chain,
            "get_cluster_subgraph": get_cluster_subgraph,
            "get_speaker_contribution_graph": get_speaker_contribution_graph
        }

        if tool_name not in tools:
            logger.error(f"Unknown tool: {tool_name}")
            return {
                "tool_results": [{
                    "tool_name": tool_name,
                    "data": {"error": f"Unknown tool: {tool_name}"},
                    "success": False
                }],
                "next_node": "react_think"
            }

        # Normalize parameters to handle common LLM mistakes
        tool_input = _normalize_tool_params(tool_name, tool_input)

        tool = tools[tool_name]
        result = tool.invoke(tool_input)

        return {
            "tool_results": [{
                "tool_name": tool_name,
                "data": result,
                "success": True
            }],
            "next_node": "react_think"
        }

    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        return {
            "tool_results": [{
                "tool_name": tool_name,
                "data": {"error": str(e)},
                "success": False
            }],
            "next_node": "react_think"
        }


def handle_clarification(state: Dict[str, Any]) -> Dict[str, Any]:
    """Handle clarification requests."""
    question = state.get("clarification_question", "Could you please provide more details?")
    options = state.get("clarification_options", [])

    response = question
    if options:
        response += "\n\nOptions:\n" + "\n".join(f"- {opt}" for opt in options)

    return {
        "final_answer": response,
        "needs_clarification": True,
        "confidence": 0.5,
        "next_node": "format",
        # Preserve session context even during clarification
        "current_session_focus": state.get("current_session_focus"),
        "previous_session_focus": state.get("previous_session_focus"),
        "session_history": state.get("session_history", []),
        "compared_sessions": state.get("compared_sessions", [])
    }


def create_agent_graph() -> StateGraph:
    """Create the LangGraph agent workflow."""

    # Create workflow with AgentState
    workflow = StateGraph(AgentState)

    # === ADD NODES ===
    workflow.add_node("input", input_processor)
    workflow.add_node("resolver", reference_resolver)
    workflow.add_node("classifier", query_classifier)
    workflow.add_node("direct_response", handle_direct_response)
    workflow.add_node("clarification", handle_clarification)
    workflow.add_node("react_think", react_think)
    workflow.add_node("react_tools", execute_react_tool)
    workflow.add_node("plan_gen", plan_generator)
    workflow.add_node("plan_exec", plan_executor)
    workflow.add_node("synthesize", synthesizer)
    workflow.add_node("format", response_formatter)

    # === ADD EDGES ===

    # Start -> Input -> Resolver -> Classifier
    workflow.add_edge(START, "input")
    workflow.add_edge("input", "resolver")
    workflow.add_edge("resolver", "classifier")

    # Classifier routing
    workflow.add_conditional_edges(
        "classifier",
        route_after_classifier,
        {
            "react_think": "react_think",
            "plan_gen": "plan_gen",
            "direct_response": "direct_response",
            "clarification": "clarification"
        }
    )

    # Direct response and clarification -> format
    workflow.add_edge("direct_response", "format")
    workflow.add_edge("clarification", "format")

    # ReAct loop
    workflow.add_conditional_edges(
        "react_think",
        route_after_react_think,
        {
            "react_tools": "react_tools",
            "synthesize": "synthesize"
        }
    )
    workflow.add_edge("react_tools", "react_think")

    # Plan-Execute flow
    workflow.add_edge("plan_gen", "plan_exec")
    workflow.add_conditional_edges(
        "plan_exec",
        route_after_plan_exec,
        {
            "plan_exec": "plan_exec",
            "synthesize": "synthesize"
        }
    )

    # Synthesis -> Format -> END
    workflow.add_edge("synthesize", "format")
    workflow.add_edge("format", END)

    return workflow


def get_compiled_graph(use_memory: bool = True):
    """
    Get compiled graph with optional checkpointing.

    Args:
        use_memory: Whether to use memory checkpointing for conversation continuity

    Returns:
        Compiled LangGraph
    """
    workflow = create_agent_graph()

    if use_memory:
        checkpointer = MemorySaver()
        return workflow.compile(checkpointer=checkpointer)

    return workflow.compile()


# Create a default instance
_default_graph = None


def get_default_graph():
    """Get or create the default graph instance."""
    global _default_graph
    if _default_graph is None:
        _default_graph = get_compiled_graph()
    return _default_graph
