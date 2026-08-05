"""
Plan-Execute Nodes

Handles complex queries by generating a plan and executing it step-by-step.
Used for comparative queries, multi-session analysis, and analytical questions.
"""

import json
import logging
import os
from typing import Dict, Any, List

from openai import OpenAI

logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

PLAN_PROMPT = """Create a plan to answer this complex query about discussion analysis.

Query: {query}
Query type: {query_type}
Current session focus: {session_focus}
Compared sessions: {compared_sessions}
Session history: {session_history}

Available tool categories:
- SEARCH: search_sessions_multi, search_chunks, search_concept_nodes
- METRICS: get_sessions_by_metrics, hybrid_session_search, get_contrastive_sessions
- ARTIFACTS: get_7c_analysis, get_session_summary, get_full_concept_map
- COMPARISON: compare_sessions, compare_speakers
- INSIGHTS: generate_ultra_insights, find_similar_sessions

Create a step-by-step plan. Each step should be ONE tool call.
Respond with JSON:
{{
    "plan_steps": [
        {{"step": 1, "tool": "<tool_name>", "purpose": "<why>", "params": {{<params>}}}},
        {{"step": 2, "tool": "<tool_name>", "purpose": "<why>", "params": {{<params>}}}},
        ...
    ],
    "final_synthesis": "<how to combine results>"
}}

Rules:
1. Keep plans to 3-5 steps maximum
2. For comparisons, gather data for ALL sessions before comparing
3. Use session_device_ids filters to scope searches
4. End with synthesis that combines all gathered data
5. For "why" questions, use get_contrastive_sessions

Example for "Compare collaboration quality between sessions 20 and 21":
{{
    "plan_steps": [
        {{"step": 1, "tool": "get_7c_analysis", "purpose": "Get 7C scores for session 20", "params": {{"session_device_id": 20}}}},
        {{"step": 2, "tool": "get_7c_analysis", "purpose": "Get 7C scores for session 21", "params": {{"session_device_id": 21}}}},
        {{"step": 3, "tool": "compare_sessions", "purpose": "Structured comparison", "params": {{"session_device_ids": [20, 21], "comparison_type": "metrics"}}}}
    ],
    "final_synthesis": "Compare 7C dimension scores, highlight biggest differences, identify which session had better collaboration"
}}
"""


def plan_generator(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a multi-step plan for complex queries.

    Args:
        state: Current agent state

    Returns:
        Updated state with plan steps
    """
    query = state.get('resolved_query') or state.get('original_query', '')
    query_type = state.get('query_type', 'comparative')
    session_focus = state.get('current_session_focus')
    compared_sessions = state.get('compared_sessions', [])
    session_history = state.get('session_history', [])

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": PLAN_PROMPT.format(
                    query=query,
                    query_type=query_type,
                    session_focus=session_focus,
                    compared_sessions=compared_sessions,
                    session_history=session_history[-5:]
                )
            }],
            response_format={"type": "json_object"},
            temperature=0
        )

        plan = json.loads(response.choices[0].message.content)
        plan_steps = plan.get('plan_steps', [])
        logger.info(f"Generated plan with {len(plan_steps)} steps")

    except Exception as e:
        logger.error(f"Plan generation failed: {e}")
        # Fallback plan
        plan_steps = [{
            "step": 1,
            "tool": "search_sessions_multi",
            "purpose": "Search for relevant content",
            "params": {"query": query, "n_results": 5}
        }]
        plan = {"final_synthesis": "Summarize findings"}

    return {
        "plan_steps": plan_steps,
        "current_step_index": 0,
        "plan_results": [],
        "final_synthesis_strategy": plan.get('final_synthesis', ''),
        "next_node": "plan_exec"
    }


def plan_executor(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute plan steps one at a time.

    This node is called repeatedly until all steps are complete.

    Args:
        state: Current agent state with plan

    Returns:
        Updated state with step results
    """
    plan_steps = state.get('plan_steps', [])
    current_index = state.get('current_step_index', 0)
    plan_results = state.get('plan_results', [])

    if current_index >= len(plan_steps):
        # All steps complete
        logger.info("Plan execution complete, moving to synthesis")
        return {"next_node": "synthesize"}

    # Get current step
    step = plan_steps[current_index]
    tool_name = step.get('tool')
    params = step.get('params', {})

    logger.info(f"Executing plan step {current_index + 1}: {tool_name}")

    # Execute the tool
    try:
        result = _execute_tool(tool_name, params)
        plan_results.append({
            "step": current_index + 1,
            "tool": tool_name,
            "purpose": step.get('purpose', ''),
            "result": result
        })
    except Exception as e:
        logger.error(f"Plan step {current_index + 1} failed: {e}")
        plan_results.append({
            "step": current_index + 1,
            "tool": tool_name,
            "purpose": step.get('purpose', ''),
            "error": str(e)
        })

    # Move to next step
    new_index = current_index + 1

    if new_index >= len(plan_steps):
        # Last step completed
        return {
            "plan_results": plan_results,
            "current_step_index": new_index,
            "tool_results": plan_results,  # Also copy to tool_results for synthesis
            "next_node": "synthesize"
        }

    return {
        "plan_results": plan_results,
        "current_step_index": new_index,
        "next_node": "plan_exec"  # Continue with next step
    }


def _execute_tool(tool_name: str, params: Dict) -> Dict[str, Any]:
    """
    Execute a tool by name with parameters.

    Args:
        tool_name: Name of the tool to execute
        params: Tool parameters

    Returns:
        Tool result
    """
    # Import tools lazily
    from agent_v2.tools import (
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
    from agent_v2.tools.rag_tools import search_chunks

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
        raise ValueError(f"Unknown tool: {tool_name}")

    tool = tools[tool_name]

    # Call the tool - LangChain tools are callable
    return tool.invoke(params)
