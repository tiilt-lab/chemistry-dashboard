"""
Query Classifier Node

Single LLM call to classify query type, complexity, and routing.
Replaces 1,500+ lines of regex patterns from the legacy system.
"""

import json
import logging
import os
from typing import Dict, Any

from openai import OpenAI

logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

CLASSIFICATION_PROMPT = """Analyze this query and classify it for a discussion analysis system.

Query: {query}

Conversation Context:
- Current session focus: {current_session}
- Previous session: {previous_session}
- Session history: {session_history}
- Compared sessions: {compared_sessions}

Respond with JSON:
{{
    "query_type": "<type>",
    "complexity": "simple|complex",
    "needs_clarification": true/false,
    "clarification_reason": "<reason or null>",
    "clarification_question": "<question to ask or null>",
    "clarification_options": ["option1", "option2"] or null,
    "visualization": "chunks|sessions|speakers|timeline|comparison|both",
    "rag_collections": ["transcripts", "concepts", "seven_c"],
    "is_analytical": true/false,
    "entities": {{
        "session_ids": [<extracted IDs>],
        "session_names": ["<extracted names>"],
        "speaker_names": ["<extracted names>"],
        "topics": ["<extracted topics>"]
    }}
}}

Query types (choose ONE):
- topic_search: Looking for specific content/quotes ("what was said about X")
- session_search: Looking for sessions with patterns ("sessions where they debated")
- session_insights: Session search + analytical keywords (why, how, analyze)
- comparative: Comparing 2+ sessions or speakers
- speaker_search: Looking for speaker patterns
- speaker_insights: Deep speaker analysis
- temporal: Evolution/timeline within a session
- similar: Finding similar sessions
- hybrid_search: Needs both chunk and session level
- artifact_lookup: Direct request for concept map, 7C, etc.
- out_of_scope: Weather, stocks, recipes (not discussion analysis)
- small_talk: Greetings, thanks, acknowledgments
- help: "What can you do?"

Complexity rules:
- simple: Single session, single artifact, factual retrieval
- complex: Multiple sessions, comparisons, analytical synthesis

Clarification needed when:
- Query uses TYPE REFERENCES like "the interview", "the podcast", "the discussion", "the session about X"
  WITHOUT specifying which one AND no current_session focus is set AND multiple sessions match
  Example: "What was discussed in the interview?" → NEEDS CLARIFICATION (multiple interview sessions exist)
- Query uses pronouns "they/that session/the last one" without clear context
- Query is too vague to determine user intent

IMPORTANT: Set needs_clarification=true when:
- current_session is null AND query mentions a generic type ("interview", "discussion", "session")
- The type reference could match multiple sessions in the system
- User says "the [type]" but hasn't established which specific one they mean

Do NOT need clarification when:
- current_session is set (user already has a session focus)
- Query mentions a SPECIFIC session name like "Dinosaurs session" or "Nuclear Fusion"
- Query mentions a session ID like "session 23" or "sessions 20 and 21"
- Query is a GENERAL search like "What was discussed recently?" - search ALL sessions
- Query doesn't mention "the [type]" at all - just search broadly
- Query asks about recent/latest/all discussions - use search tools across all sessions
- Query contains UNIQUE topic terms (T-Rex, fusion, dinosaurs) - just search, these are specific
- Query asks about a speaker ACROSS sessions ("how did Lex contribute") - use cross-session speaker search
- Query is a comparison with EXPLICIT session IDs or names - use compare_sessions directly
- Query asks for 7C analysis or concept map of a named session - use artifact tools directly
- Query asks about concepts, clusters, or themes - use search tools directly

Examples that do NOT need clarification (NEVER ask for clarification on these):
- "What was discussed recently?" → topic_search across all sessions
- "What topics have been covered?" → session_search across all sessions
- "Show me discussions about science" → topic_search with science filter
- "What sessions are available?" → session_search across all sessions
- "Find discussions about AI" → topic_search for AI topic
- "What have people talked about?" → topic_search across all sessions
- "The Shaw Interview" → session_search (user is specifying which session)
- "Nuclear Fusion" → session_search (user is specifying a session by name)
- "Dinosaurs" → session_search (user is specifying a session by topic)

CLARIFICATION RESPONSE DETECTION:
If the query is SHORT (1-5 words) and looks like a session name or topic, the user is likely
RESPONDING to a previous clarification request. In this case:
- NEVER ask for further clarification
- Treat it as a session_search with the given name
- Example: After "Which interview?", user says "Shaw Interview" → search for Shaw Interview session

CRITICAL: Default to NOT needing clarification. Only set needs_clarification=true when:
1. Query says "the interview" / "the session" / "the discussion" WITHOUT any name/ID
2. AND current_session is null
3. AND there's no specific topic term that could narrow the search

If in doubt, do NOT ask for clarification - just search and let the user see results.
"""


def query_classifier(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Classify query type and complexity.

    Uses DETERMINISTIC routing for known patterns (speaker queries, etc.)
    and falls back to LLM classification for complex/novel queries.

    Args:
        state: Current agent state with query and context

    Returns:
        Updated state with classification results and routing decision
    """
    query = state.get('resolved_query') or state.get('original_query', '')
    query_lower = query.lower()

    # =================================================================
    # DETERMINISTIC ROUTING - Don't let LLM decide these cases
    # =================================================================

    # Known speaker names from the database
    KNOWN_SPEAKERS = {'lex', 'dave', 'julia', 'tucker', 'sam', 'vanessa',
                      'alice', 'bob', 'david', 'oliver', 'ezra', 'derek'}

    # Cross-session keywords that indicate searching across all sessions
    CROSS_SESSION_KEYWORDS = ['across', 'different sessions', 'all sessions',
                              'sessions', 'multiple', 'various']

    # Check if query mentions a known speaker (word boundary matching to avoid "alex" matching "lex")
    import re
    mentioned_speakers = [s for s in KNOWN_SPEAKERS if re.search(rf'\b{s}\b', query_lower)]

    # ANY query mentioning a speaker → FORCE search_speakers (don't let LLM decide)
    if mentioned_speakers:
        logger.info(f"DETERMINISTIC: Speaker query detected for {mentioned_speakers}, forcing search_speakers")
        return {
            "query_type": "speaker_search",
            "complexity": "simple",
            "is_analytical": False,
            "visualization_type": "speakers",
            "rag_collections": ["speakers"],
            "entities": {"speaker_names": mentioned_speakers},
            "needs_clarification": False,
            "clarification_question": "",
            "clarification_options": [],
            "max_iterations": 3,
            "force_tool": "search_speakers",  # Forces react_think to use this tool
            "next_node": "react_think"
        }

    # =================================================================
    # DETERMINISTIC: Debate/argumentation queries → force get_sessions_by_metrics
    # =================================================================
    DEBATE_KEYWORDS = ['debate', 'argumentation', 'argument', 'challenge',
                       'contrast', 'disagreement', 'contention']
    if any(k in query_lower for k in DEBATE_KEYWORDS) and not mentioned_speakers:
        logger.info("DETERMINISTIC: Debate/argumentation query detected")
        return {
            "query_type": "metric_analysis",
            "complexity": "moderate",
            "is_analytical": True,
            "visualization_type": "metrics",
            "rag_collections": ["concepts", "7c_analysis"],
            "entities": {},
            "needs_clarification": False,
            "clarification_question": "",
            "clarification_options": [],
            "max_iterations": 4,
            "force_tool": "get_sessions_by_metrics",
            "force_tool_params": {
                "metric_filters": {},  # No filters, get all sessions
                "sort_by": "debate_score",  # Sort by debate score
                "descending": True,
                "n_results": 5
            },
            "next_node": "react_think"
        }

    # =================================================================
    # DETERMINISTIC: Causal/chain queries → force get_causal_chain
    # =================================================================
    CAUSAL_KEYWORDS = ['cause', 'causes', 'caused', 'effect', 'effects',
                       'led to', 'leads to', 'chain', 'causal', 'result in',
                       'results in', 'consequence']
    if any(k in query_lower for k in CAUSAL_KEYWORDS) and not mentioned_speakers:
        logger.info("DETERMINISTIC: Causal query detected, forcing get_causal_chain")
        return {
            "query_type": "graph_traversal",
            "complexity": "moderate",
            "is_analytical": True,
            "visualization_type": "concept_map",
            "rag_collections": ["concepts"],
            "entities": {},
            "needs_clarification": False,
            "clarification_question": "",
            "clarification_options": [],
            "max_iterations": 4,
            "force_tool": "get_causal_chain",
            "next_node": "react_think"
        }

    # =================================================================
    # DETERMINISTIC: 7C dimension queries (best collaboration, highest communication)
    # =================================================================
    # Actual 7C dimensions in the system (from seven_cs_service.py)
    SEVEN_C_DIMENSIONS = {
        'climate': 'climate_score',       # Emotional safety, group interactions
        'communication': 'communication_score',
        'compatibility': 'compatibility_score',
        'conflict': 'conflict_score',
        'context': 'context_score',
        'contribution': 'contribution_score',  # Equal participation
        'constructive': 'constructive_score'
    }
    # User-friendly aliases that map to actual metrics
    DIMENSION_ALIASES = {
        'collaboration': 'climate_score',      # "collaboration" → climate (group interactions)
        'teamwork': 'climate_score',
        'participation': 'contribution_score',
        'engagement': 'contribution_score',
    }
    SUPERLATIVE_KEYWORDS = ['best', 'worst', 'most', 'least', 'highest', 'lowest',
                            'top', 'bottom']

    # Check if query asks for best/highest of a specific 7C dimension
    matched_metric = None
    matched_dimension_name = None

    # First check direct dimension names
    for dim, metric in SEVEN_C_DIMENSIONS.items():
        if dim in query_lower:
            matched_metric = metric
            matched_dimension_name = dim
            break

    # Then check aliases
    if not matched_metric:
        for alias, metric in DIMENSION_ALIASES.items():
            if alias in query_lower:
                matched_metric = metric
                matched_dimension_name = alias
                break

    if matched_metric and any(k in query_lower for k in SUPERLATIVE_KEYWORDS):
        # Determine sort order from query
        descending = not any(k in query_lower for k in ['worst', 'least', 'lowest', 'bottom'])
        logger.info(f"DETERMINISTIC: Best 7C dimension query for '{matched_dimension_name}' → {matched_metric}, forcing get_sessions_by_metrics")
        return {
            "query_type": "metric_ranking",
            "complexity": "simple",
            "is_analytical": True,
            "visualization_type": "comparison",
            "rag_collections": ["7c_analysis"],
            "entities": {"dimension": matched_dimension_name},
            "needs_clarification": False,
            "clarification_question": "",
            "clarification_options": [],
            "max_iterations": 1,  # Only one tool call needed
            "force_tool": "get_sessions_by_metrics",
            "force_tool_params": {
                "metric_filters": {},  # No filters, just sort
                "sort_by": matched_metric,
                "descending": descending,
                "n_results": 5
            },
            "skip_to_synthesis": True,  # Don't let LLM decide after forced tool
            "next_node": "react_think"
        }

    # =================================================================
    # DETERMINISTIC: Generic superlative queries (which session) → compare all
    # =================================================================
    GENERIC_SUPERLATIVES = ['which session', 'what session']
    if any(k in query_lower for k in SUPERLATIVE_KEYWORDS + GENERIC_SUPERLATIVES) and not mentioned_speakers:
        logger.info("DETERMINISTIC: Superlative query detected, searching all sessions")
        return {
            "query_type": "comparative",
            "complexity": "moderate",
            "is_analytical": True,
            "visualization_type": "comparison",
            "rag_collections": ["sessions", "7c_analysis"],
            "entities": {},
            "needs_clarification": False,
            "clarification_question": "",
            "clarification_options": [],
            "max_iterations": 4,
            "force_tool": "get_sessions_by_metrics",
            "next_node": "react_think"
        }

    # =================================================================
    # LLM-BASED CLASSIFICATION - For other cases
    # =================================================================

    # Build context
    context = {
        "current_session": state.get('current_session_focus'),
        "previous_session": state.get('previous_session_focus'),
        "session_history": state.get('session_history', [])[-5:],  # Last 5
        "compared_sessions": state.get('compared_sessions', [])
    }

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Fast and cheap for classification
            messages=[{
                "role": "user",
                "content": CLASSIFICATION_PROMPT.format(
                    query=query,
                    current_session=context['current_session'],
                    previous_session=context['previous_session'],
                    session_history=context['session_history'],
                    compared_sessions=context['compared_sessions']
                )
            }],
            response_format={"type": "json_object"},
            temperature=0
        )

        classification = json.loads(response.choices[0].message.content)
        logger.info(f"Classification: type={classification.get('query_type')}, "
                   f"complexity={classification.get('complexity')}")

    except Exception as e:
        logger.error(f"Classification failed: {e}")
        # Fallback to simple topic search
        classification = {
            "query_type": "topic_search",
            "complexity": "simple",
            "needs_clarification": False,
            "visualization": "chunks",
            "rag_collections": ["transcripts"],
            "is_analytical": False,
            "entities": {}
        }

    # Determine next node based on classification
    query_type = classification.get("query_type", "topic_search")
    complexity = classification.get("complexity", "simple")
    needs_clarification = classification.get("needs_clarification", False)

    # Routing logic
    if query_type in ["small_talk", "help"]:
        next_node = "direct_response"
    elif query_type == "out_of_scope":
        next_node = "direct_response"
    elif needs_clarification:
        next_node = "clarification"
    elif complexity == "simple":
        next_node = "react_think"
    else:
        next_node = "plan_gen"

    # Determine max iterations based on query type
    if query_type == "temporal":
        max_iterations = 5  # Timeline queries need more iterations
    elif query_type in ["comparative", "session_insights"]:
        max_iterations = 4
    else:
        max_iterations = 3

    return {
        "query_type": query_type,
        "complexity": complexity,
        "is_analytical": classification.get("is_analytical", False),
        "visualization_type": classification.get("visualization", "chunks"),
        "rag_collections": classification.get("rag_collections", ["transcripts"]),
        "entities": classification.get("entities", {}),
        "needs_clarification": needs_clarification,
        "clarification_question": classification.get("clarification_question", ""),
        "clarification_options": classification.get("clarification_options", []),
        "max_iterations": max_iterations,
        "next_node": next_node
    }
