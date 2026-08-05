"""
ReAct Loop Nodes

Implements the ReAct (Reasoning + Acting) pattern for simple queries.
Uses LLM to decide which tool to call and synthesizes results.
"""

import json
import logging
import os
from typing import Dict, Any, List

from openai import OpenAI
from langchain_core.messages import AIMessage, HumanMessage

logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Tool descriptions for the LLM with EXACT parameter names
TOOL_DESCRIPTIONS = """Available tools with EXACT parameter names:

SEARCH TOOLS (use session_device_ids as LIST):
- search_sessions_multi(query: str, session_device_ids: list = None, n_results: int = 5)
  Search across sessions with RRF fusion. Best for broad queries.

- search_chunks(query: str, session_device_ids: list = None, n_results: int = 5)
  Search 30-second transcript chunks for specific content/quotes.

- search_transcript_chunks(query: str, session_device_ids: list = None, n_results: int = 5)
  Search semantic transcript segments by topic.

- search_concept_nodes(query: str, session_device_ids: list = None, n_results: int = 10)
  Search individual concepts (ideas, questions, hypotheses).

- search_concept_clusters(query: str, session_device_ids: list = None, n_results: int = 5)
  Search thematic clusters for high-level topics.

ARTIFACT TOOLS (use session_device_id as SINGLE INT, not list):
- get_7c_analysis(session_device_id: int)
  Get 7C collaboration scores for ONE session.

- get_session_summary(session_device_id: int)
  Get overview of ONE session including SPEAKER NAMES, themes, key metrics.

- get_full_concept_map(session_device_id: int)
  Get complete concept map structure for ONE session.

- get_liwc_metrics(session_device_id: int)
  Get linguistic metrics for ONE session.

GRAPH TRAVERSAL TOOLS (USE for connection/structure/path queries):
- get_node_neighbors(node_id: str, edge_types: list = None, direction: str = "both")
  USE WHEN: "what is connected to X", "concepts related to X", "what builds on X"
  Returns concepts linked to a node with relationship types.

- get_concept_path(source_node_id: str, target_node_id: str, max_depth: int = 4)
  USE WHEN: "how does X connect to Y", "path between X and Y", "link between concepts"
  Finds the reasoning path from one concept to another.

- get_causal_chain(node_id: str, direction: str = "forward", max_depth: int = 5)
  USE WHEN: "what led to X", "causes of X", "effects of X", "what follows from X"
  Traces cause-effect chains in the concept map.

- get_cluster_subgraph(cluster_id: int, include_edges: bool = True)
  USE WHEN: "concepts in theme X", "structure of theme", "what's in the cluster"
  Returns all nodes and edges within a thematic cluster.

- get_speaker_contribution_graph(session_device_id: int, speaker_id: int = None)
  USE WHEN: "what did speaker contribute", "concepts from speaker X"
  Shows which concepts each speaker contributed.

IMPORTANT: Prefer GRAPH tools when query contains:
"connected", "connection", "path", "chain", "led to", "causes", "effects",
"structure", "how ideas link", "reasoning flow", "contributions by"

SPEAKER TOOLS (CRITICAL for speaker/person queries):
- search_speakers(query: str, n_results: int = 5)
  USE WHEN: Query mentions a PERSON'S NAME (Lex, Dave, Julia, Tucker, Ezra, Derek, etc.)
  AND asks about their style, contributions, engagement, participation, or role.

  TRIGGER KEYWORDS: "speaker", "how does X engage", "X's style", "X's role",
  "how did X contribute", "about X" (where X is a person's name)

  This searches speaker profiles ACROSS ALL SESSIONS - perfect for cross-session analysis.

  Example: "How does Lex engage in discussions?" → search_speakers(query="Lex engagement style")
  Example: "What is Lex's speaker style?" → search_speakers(query="Lex speaking style patterns")
  Example: "How did Dave contribute?" → search_speakers(query="Dave contributions")

  NOTE: For within-session speaker analysis, use compare_speakers() instead.

- compare_speakers(session_device_id: int, aspects: list = ["all"])
  Compare speakers WITHIN ONE SESSION on participation, LIWC metrics, concept contributions.
  Use when query asks to compare speakers in a specific session.

IMPORTANT: When query contains a person's name + "style/engage/contribute/role/how does",
ALWAYS prefer search_speakers over search_sessions_multi or get_session_summary.

COMPARISON TOOLS:
- compare_sessions(session_device_ids: list)
  Compare multiple sessions on metrics, concepts, participation. Requires LIST of IDs.

INSIGHT TOOLS:
- find_similar_sessions(session_device_id: int, n_results: int = 5)
  Find structurally similar sessions.

- hybrid_session_search(query: str, metric_filters: dict, n_results: int = 5)
  Combine semantic search with metric filters. For queries like "sessions with high debate about X".

- get_sessions_by_metrics(metric_filters: dict, n_results: int = 10, sort_by: str = None)
  Get sessions filtered by metrics. For "most collaborative sessions" or "highest debate scores".

- generate_ultra_insights(query: str, focus_area: str, session_contexts: str)
  Generate analytical insights. Use for "why" and "analyze" questions.

CRITICAL RULES:
- For single-session tools: use session_device_id (int), e.g., {"session_device_id": 23}
- For multi-session search: use session_device_ids (list), e.g., {"session_device_ids": [23]}
- Search tools always need "query" parameter
- For speaker questions across sessions: use search_speakers NOT get_session_summary
- When a person's name appears in query + engagement/style/role → use search_speakers
"""

REACT_PROMPT = """You are a ReAct agent for analyzing discussion sessions.

{tool_descriptions}

Current Context:
- Query: {query}
- Session focus: {session_focus}
- Query type: {query_type}
- Tools already called: {tools_called}
- Results so far: {results_summary}

Based on the query and context, decide your next action.

Respond with JSON:
{{
    "thought": "<your reasoning about what to do next>",
    "action": "<tool_name or 'synthesize'>",
    "action_input": {{<tool parameters>}},
    "should_continue": true/false
}}

Rules:
1. If you have enough information to answer, set action="synthesize" and should_continue=false
2. Call the MINIMUM tools needed - don't over-fetch
3. For simple factual queries, 1-2 tool calls should suffice
4. Use session_focus as session_device_ids filter when appropriate
5. Don't call the same tool twice with identical parameters
6. For "synthesize", leave action_input empty

Example for "What was discussed in the Dinosaurs session?":
{{
    "thought": "Need to search for content in the Dinosaurs session (ID 23)",
    "action": "search_transcript_chunks",
    "action_input": {{"query": "main topics discussed", "session_device_ids": [23], "n_results": 5}},
    "should_continue": true
}}
"""


def react_think(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    ReAct thinking step - decide next action.

    Args:
        state: Current agent state

    Returns:
        Updated state with action decision
    """
    query = state.get('resolved_query') or state.get('original_query', '')
    session_focus = state.get('current_session_focus')
    query_type = state.get('query_type', 'topic_search')
    iteration = state.get('iteration_count', 0)
    max_iterations = state.get('max_iterations', 3)
    tool_results = state.get('tool_results', [])

    # =================================================================
    # DETERMINISTIC: Skip to synthesis if flag is set and we have results
    # =================================================================
    skip_to_synthesis = state.get('skip_to_synthesis', False)
    if skip_to_synthesis and tool_results:
        logger.info("DETERMINISTIC: Skipping to synthesis (skip_to_synthesis=True)")
        return {
            "current_thought": "Have results from deterministic tool, synthesizing directly",
            "current_action": "synthesize",
            "current_action_input": {},
            "next_node": "synthesize"
        }

    # =================================================================
    # DETERMINISTIC: If classifier forced a specific tool, use it
    # =================================================================
    forced_tool = state.get('force_tool')
    if forced_tool and not tool_results:
        # Use force_tool_params if provided, otherwise use defaults
        forced_params = state.get('force_tool_params', {})

        # Build tool input - merge forced params with defaults
        tool_input = {}

        # For search tools, add query if not provided
        if 'query' not in forced_params and forced_tool.startswith('search'):
            tool_input['query'] = query

        # Add session focus if applicable and not already specified
        if session_focus and 'session_device_id' not in forced_params and 'session_device_ids' not in forced_params:
            # Single-session tools use session_device_id
            single_session_tools = ['get_7c_analysis', 'get_session_summary', 'get_full_concept_map',
                                    'get_liwc_metrics', 'get_cluster_subgraph', 'get_speaker_contribution_graph']
            if forced_tool in single_session_tools:
                tool_input['session_device_id'] = session_focus
            elif forced_tool.startswith('search'):
                tool_input['session_device_ids'] = [session_focus]

        # Override with forced_params (these take precedence)
        tool_input.update(forced_params)

        logger.info(f"DETERMINISTIC: Using forced tool '{forced_tool}' with params: {tool_input}")
        return {
            "current_thought": f"Using {forced_tool} as directed by deterministic routing",
            "current_action": forced_tool,
            "current_action_input": tool_input,
            "iteration_count": iteration + 1,
            "next_node": "react_tools"
        }

    # Check iteration limit
    if iteration >= max_iterations:
        logger.info(f"Reached max iterations ({max_iterations}), synthesizing")
        return {
            "current_thought": "Reached iteration limit, time to synthesize",
            "current_action": "synthesize",
            "current_action_input": {},
            "next_node": "synthesize"
        }

    # Build results summary
    results_summary = ""
    tools_called = []
    for result in tool_results[-3:]:  # Last 3 results
        tool_name = result.get('tool_name', 'unknown')
        tools_called.append(tool_name)
        data = result.get('data', {})
        if isinstance(data, list):
            # Handle tools that return lists directly (like get_sessions_by_metrics)
            count = len(data)
            if count > 0:
                # Show first result for context
                first = data[0]
                if isinstance(first, dict):
                    session_name = first.get('session_name', f"Session {first.get('session_device_id', '?')}")
                    results_summary += f"\n- {tool_name}: {count} sessions found. Top: {session_name}"
                else:
                    results_summary += f"\n- {tool_name}: {count} results"
            else:
                results_summary += f"\n- {tool_name}: 0 results"
        elif isinstance(data, dict):
            count = data.get('result_count', data.get('total_found', len(data.get('results', []))))
            results_summary += f"\n- {tool_name}: {count} results"

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": REACT_PROMPT.format(
                    tool_descriptions=TOOL_DESCRIPTIONS,
                    query=query,
                    session_focus=session_focus,
                    query_type=query_type,
                    tools_called=tools_called,
                    results_summary=results_summary or "None yet"
                )
            }],
            response_format={"type": "json_object"},
            temperature=0
        )

        decision = json.loads(response.choices[0].message.content)
        logger.info(f"ReAct decision: action={decision.get('action')}")

    except Exception as e:
        logger.error(f"ReAct thinking failed: {e}")
        # Default to synthesize on error
        decision = {
            "thought": f"Error in reasoning: {e}",
            "action": "synthesize",
            "action_input": {},
            "should_continue": False
        }

    # Route based on decision
    action = decision.get('action', 'synthesize')

    if action == 'synthesize' or not decision.get('should_continue', True):
        return {
            "current_thought": decision.get('thought', ''),
            "current_action": "synthesize",
            "current_action_input": {},
            "iteration_count": iteration + 1,
            "next_node": "synthesize"
        }

    return {
        "current_thought": decision.get('thought', ''),
        "current_action": action,
        "current_action_input": decision.get('action_input', {}),
        "iteration_count": iteration + 1,
        "next_node": "react_tools"
    }


def should_continue_react(state: Dict[str, Any]) -> str:
    """
    Determine if ReAct loop should continue.

    Args:
        state: Current agent state

    Returns:
        Next node name
    """
    return state.get('next_node', 'synthesize')
