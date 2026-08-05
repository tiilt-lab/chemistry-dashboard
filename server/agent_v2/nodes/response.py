"""
Response Formatter Node

Formats the final response for frontend visualization.
Ensures response structure matches legacy RAG UI expectations.
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def response_formatter(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format response for frontend visualization.

    Ensures the response metadata matches what the frontend expects
    for proper visualization rendering (chunks, sessions, speakers, etc.)

    Args:
        state: Current agent state with final answer

    Returns:
        Updated state with formatted response_metadata
    """
    query = state.get('original_query', '')
    query_type = state.get('query_type', 'topic_search')
    visualization = state.get('visualization_type', 'chunks')
    tool_results = state.get('tool_results', [])
    plan_results = state.get('plan_results', [])
    final_answer = state.get('final_answer', '')
    citations = state.get('citations', [])
    confidence = state.get('confidence', 0.5)

    # Combine all results
    all_results = tool_results + plan_results

    # Initialize response structure matching legacy RAG UI
    response_metadata = {
        "query": query,
        "query_type": query_type,
        "search_level": visualization,
        "results": None,
        "session_results": None,
        "speaker_results": None,
        "comparison": None,
        "timeline": None,
        "similar": None,
        "insights": None,
        "total_found": 0,
        "tools_used": [],
        "confidence": confidence
    }

    # Route tool results to appropriate response fields
    for result in all_results:
        tool_name = result.get('tool_name') or result.get('tool', 'unknown')
        data = result.get('data') or result.get('result', {})

        response_metadata["tools_used"].append(tool_name)

        if not isinstance(data, dict):
            continue

        # Chunk-level search results
        if tool_name in ["search_transcript_chunks", "search_concept_nodes",
                        "search_chunks", "search_concept_clusters"]:
            if response_metadata["results"] is None:
                response_metadata["results"] = []
            results_list = data.get('results', [])
            response_metadata["results"].extend(results_list)
            response_metadata["search_level"] = "chunks"

        # Session-level search results
        elif tool_name in ["search_sessions_multi", "hybrid_session_search",
                          "get_sessions_by_metrics"]:
            if response_metadata["session_results"] is None:
                response_metadata["session_results"] = []

            # Handle different result structures
            sessions = data.get('fused_results') or data.get('results', [])
            if sessions:
                # Enrich session results with argumentation data
                enriched = _enrich_session_results(sessions)
                response_metadata["session_results"].extend(enriched)
                response_metadata["search_level"] = "sessions"

        # Speaker results
        elif tool_name in ["search_speakers", "compare_speakers"]:
            if response_metadata["speaker_results"] is None:
                response_metadata["speaker_results"] = []
            results_list = data.get('results', [])
            if isinstance(results_list, dict):
                # compare_speakers returns dict of speakers
                results_list = list(results_list.values())
            response_metadata["speaker_results"].extend(results_list)
            response_metadata["search_level"] = "speakers"

        # Comparison results
        elif tool_name == "compare_sessions":
            response_metadata["comparison"] = data
            response_metadata["search_level"] = "comparison"

        # Similar sessions
        elif tool_name == "find_similar_sessions":
            response_metadata["similar"] = data.get('similar_sessions', [])

        # Generated insights
        elif tool_name == "generate_ultra_insights":
            if isinstance(data, str):
                response_metadata["insights"] = data
            elif isinstance(data, dict):
                response_metadata["insights"] = data.get('insights', str(data))

    # Add insights for analytical queries
    is_analytical = state.get('is_analytical', False)
    if is_analytical and not response_metadata.get("insights"):
        response_metadata["insights"] = final_answer

    # Calculate total found
    response_metadata["total_found"] = (
        len(response_metadata.get("results") or []) +
        len(response_metadata.get("session_results") or []) +
        len(response_metadata.get("speaker_results") or [])
    )

    # Preserve session context for multi-turn conversations
    return {
        "response_metadata": response_metadata,
        "final_answer": final_answer,
        "citations": citations,
        "confidence": confidence,
        # Pass through session context for storage in conversation context
        "current_session_focus": state.get("current_session_focus"),
        "previous_session_focus": state.get("previous_session_focus"),
        "current_speaker_focus": state.get("current_speaker_focus"),
        "session_history": state.get("session_history", []),
        "compared_sessions": state.get("compared_sessions", [])
    }


def _enrich_session_results(sessions: List[Dict]) -> List[Dict]:
    """
    Enrich session results with argumentation and 7C metrics for visualization.

    This adds the data needed for the frontend to render session cards properly.
    """
    try:
        from tables.concept_session import ConceptSession
        from tables.concept_edge import ConceptEdge
        from tables.seven_cs_analysis import SevenCsAnalysis
    except ImportError:
        logger.warning("Could not import tables for enrichment")
        return sessions

    enriched = []
    for session in sessions:
        sd_id = session.get("session_device_id")
        if not sd_id:
            enriched.append(session)
            continue

        # Clone session dict
        enriched_session = dict(session)

        try:
            # Get argumentation metrics
            concept_session = ConceptSession.query.filter_by(
                session_device_id=sd_id
            ).first()

            if concept_session:
                edges = ConceptEdge.query.filter_by(
                    concept_session_id=concept_session.id
                ).all()

                edge_counts = {}
                for edge in edges:
                    edge_counts[edge.edge_type] = edge_counts.get(edge.edge_type, 0) + 1

                enriched_session["argumentation"] = {
                    "has_concept_map": True,
                    "debate_score": edge_counts.get("challenges", 0) + edge_counts.get("contrasts_with", 0),
                    "reasoning_depth": edge_counts.get("builds_on", 0) + edge_counts.get("elaborates", 0),
                    "challenge_count": edge_counts.get("challenges", 0),
                    "support_count": edge_counts.get("supports", 0)
                }

            # Get 7C scores
            seven_cs = SevenCsAnalysis.query.filter_by(session_device_id=sd_id).first()
            if seven_cs and seven_cs.analysis_summary:
                summary = seven_cs.analysis_summary
                enriched_session["seven_cs"] = {
                    "communication_score": summary.get("communication", {}).get("score", 0),
                    "climate_score": summary.get("climate", {}).get("score", 0),
                    "contribution_score": summary.get("contribution", {}).get("score", 0)
                }

        except Exception as e:
            logger.warning(f"Could not enrich session {sd_id}: {e}")

        enriched.append(enriched_session)

    return enriched


# Handle small talk and help responses
SMALL_TALK_RESPONSES = {
    "greeting": "Hello! I'm here to help you analyze discussion sessions. "
               "Ask me about specific sessions, compare discussions, or explore patterns in your data.",
    "thanks": "You're welcome! Let me know if you have any other questions about your discussions.",
    "help": "I can help you with:\n"
           "- Searching discussion content (\"What was said about X?\")\n"
           "- Analyzing sessions (\"Show me the concept map for session 23\")\n"
           "- Comparing sessions (\"Compare collaboration in sessions 20 and 21\")\n"
           "- Finding patterns (\"Sessions with high debate\")\n"
           "- Speaker analysis (\"Who contributed most?\")\n\n"
           "Just ask naturally and I'll find the relevant information!",
    "out_of_scope": "I'm specialized in analyzing discussion sessions and can't help with that topic. "
                   "Try asking about session content, speaker patterns, or collaboration quality."
}


def handle_direct_response(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle direct responses for small talk, help, and out-of-scope queries.

    Args:
        state: Current agent state

    Returns:
        Updated state with direct response
    """
    query_type = state.get('query_type', '')
    query_lower = (state.get('original_query') or '').lower()

    # Determine response type
    if query_type == "help" or "what can you do" in query_lower or "help" in query_lower:
        response = SMALL_TALK_RESPONSES["help"]
    elif query_type == "out_of_scope":
        response = SMALL_TALK_RESPONSES["out_of_scope"]
    elif any(g in query_lower for g in ["hello", "hi ", "hey", "good morning", "good afternoon"]):
        response = SMALL_TALK_RESPONSES["greeting"]
    elif any(t in query_lower for t in ["thank", "thanks", "appreciate"]):
        response = SMALL_TALK_RESPONSES["thanks"]
    else:
        response = SMALL_TALK_RESPONSES["greeting"]

    return {
        "final_answer": response,
        "confidence": 1.0,
        "next_node": "format",
        # Preserve session context for multi-turn conversations
        "current_session_focus": state.get("current_session_focus"),
        "previous_session_focus": state.get("previous_session_focus"),
        "session_history": state.get("session_history", []),
        "compared_sessions": state.get("compared_sessions", [])
    }
