"""
Representation Planner Node for BLINC Agent V3

PRAS Stage 2: Representation Planning

For each sub-goal, determines which representations to query and in what order.
Maps sub-goal indicators to specific tools and parameters.
"""

import logging
from typing import Dict, Any, List

from ..llm import get_reasoning_client
from ..state import SubGoal, RetrievalStep, RetrievalPlan

logger = logging.getLogger(__name__)

# Representation capabilities and tool mappings
# SPECIFIC TOOLS DESIGN: Each representation has its own dedicated tool
# This provides cleaner responses and better traceability
REPRESENTATION_CONFIG = {
    "transcript": {
        "provides": ["direct quotes", "temporal sequence", "speaker attribution", "language patterns"],
        "good_for": ["evidence of what was said", "discourse patterns", "specific claims"],
        "epistemic_value": "high",
        "tools": {
            "get_transcript": {
                "purpose": "Get complete transcript with LIWC metrics for a session",
                "params": ["session_id"],
                "requires_session": True
            },
            "search_for_sessions": {
                "purpose": "Find sessions discussing a topic (use when no session specified)",
                "params": ["query", "top_k"],
                "requires_session": False
            },
            "search_transcripts": {
                "purpose": "Find specific content, quotes, or moments (fragment search)",
                "params": ["query", "session_ids", "speaker", "limit"],
                "requires_session": False
            }
        }
    },
    "concept_map": {
        "provides": ["ideas", "relationships", "clusters", "speaker attribution"],
        "good_for": ["semantic structure", "causal relationships", "thematic organization"],
        "epistemic_value": "medium",
        "tools": {
            "get_concept_map": {
                "purpose": "Get complete concept map with nodes, edges, clusters",
                "params": ["session_id"],
                "requires_session": True
            },
            "search_for_sessions": {
                "purpose": "Find sessions with relevant concepts (use when no session specified)",
                "params": ["query", "top_k"],
                "requires_session": False
            },
            "search_concepts": {
                "purpose": "Find specific concepts or ideas (fragment search)",
                "params": ["query", "session_ids", "concept_types", "limit"],
                "requires_session": False
            }
        }
    },
    "collaboration": {
        "provides": ["7C dimension scores", "explanations", "overall quality"],
        "good_for": ["interaction quality", "participation balance", "collaborative behaviors"],
        "epistemic_value": "medium",
        "tools": {
            "get_7c_analysis": {
                "purpose": "Get 7C collaboration analysis for a session",
                "params": ["session_id"],
                "requires_session": True
            },
            "search_for_sessions": {
                "purpose": "Find sessions to analyze collaboration (use when no session specified)",
                "params": ["query", "top_k"],
                "requires_session": False
            }
        }
    },
    "speaker_profile": {
        "provides": ["aggregated metrics", "cross-session patterns", "contribution types"],
        "good_for": ["individual patterns", "comparative analysis"],
        "epistemic_value": "medium",
        "tools": {
            "get_speaker_profile": {
                "purpose": "Get complete speaker data across transcript and concept map",
                "params": ["speaker_name", "session_id"],
                "requires_session": False  # session_id is optional
            }
        }
    },
    "session_overview": {
        "provides": ["summary", "participants", "themes", "duration"],
        "good_for": ["context", "high-level understanding"],
        "epistemic_value": "low",
        "tools": {
            "list_sessions": {
                "purpose": "List all available sessions with metadata",
                "params": [],
                "requires_session": False
            }
        }
    },
    "discovery": {
        "provides": ["relevant sessions", "session rankings", "topic matches"],
        "good_for": ["finding sessions about a topic", "exploratory queries"],
        "epistemic_value": "high",
        "tools": {
            "search_for_sessions": {
                "purpose": "Semantic search across all sessions",
                "params": ["query", "top_k"],
                "requires_session": False
            }
        }
    }
}

# Indicator patterns to tool mappings
INDICATOR_TO_TOOL = {
    # Causal relationships
    "causal": {"rep": "concept_map", "tool": "search_concepts", "type_filter": ["hypothesis", "idea"]},
    "causes": {"rep": "concept_map", "tool": "explore_concepts", "direction": "outgoing"},
    "leads to": {"rep": "concept_map", "tool": "explore_concepts", "direction": "outgoing"},

    # Language patterns
    "language patterns": {"rep": "transcript", "tool": "search_transcripts"},
    "quotes": {"rep": "transcript", "tool": "search_transcripts"},
    "said": {"rep": "transcript", "tool": "search_transcripts"},
    "statements": {"rep": "transcript", "tool": "search_transcripts"},

    # Collaboration indicators
    "participation": {"rep": "collaboration", "tool": "get_collaboration_analysis"},
    "communication": {"rep": "collaboration", "tool": "get_collaboration_analysis"},
    "7C": {"rep": "collaboration", "tool": "get_collaboration_analysis"},
    "building on": {"rep": "collaboration", "tool": "get_collaboration_analysis"},
    "constructive": {"rep": "collaboration", "tool": "get_collaboration_analysis"},

    # Concept structure
    "concepts": {"rep": "concept_map", "tool": "search_concepts"},
    "ideas": {"rep": "concept_map", "tool": "search_concepts"},
    "relationships": {"rep": "concept_map", "tool": "explore_concepts"},
    "connections": {"rep": "concept_map", "tool": "explore_concepts"},
    "clusters": {"rep": "concept_map", "tool": "get_concept_map"},

    # Speaker analysis
    "speaker": {"rep": "speaker_profile", "tool": "analyze_speaker"},
    "contribution": {"rep": "speaker_profile", "tool": "analyze_speaker"},
    "participation style": {"rep": "speaker_profile", "tool": "analyze_speaker"},
}


PLANNING_SYSTEM_PROMPT = """You are planning retrieval steps for a sub-goal in a collaborative learning analysis.

For each sub-goal, create a retrieval plan that specifies:
1. Which tools to use and in what order
2. What parameters to pass to each tool
3. The priority of each step (primary, secondary, verification)

Available tools and their parameters:

TRANSCRIPT TOOLS:
- search_transcripts(query, session_ids?, speaker?, limit?): Find specific content or quotes

CONCEPT MAP TOOLS:
- search_concepts(query, session_ids?, concept_types?, limit?): Find specific concepts
- explore_concepts(concept_id, direction, depth?): Explore concept connections
- get_concept_map(session_id): Get full concept map structure

COLLABORATION TOOLS:
- get_collaboration_analysis(session_id): Get 7C collaboration scores

SPEAKER TOOLS:
- analyze_speaker(speaker_name, session_ids?): Analyze speaker patterns

SESSION TOOLS:
- get_session_overview(session_id): Get session summary
- list_sessions(): List all sessions

COMPARISON TOOLS:
- compare_sessions(session_ids): Compare multiple sessions

Return JSON:
{
    "steps": [
        {
            "representation": "representation_type",
            "purpose": "what this step finds",
            "tool": "tool_name",
            "parameters": {"param": "value"},
            "priority": "primary|secondary|verification"
        }
    ]
}

Guidelines:
1. Primary steps get direct evidence for the sub-goal
2. Secondary steps get supporting or alternative evidence
3. Verification steps confirm findings from other representations
4. Keep plans focused: 2-4 steps per sub-goal
5. Order by priority and logical sequence"""


def plan_retrieval(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Plan retrieval steps for each sub-goal.

    PRAS Stage 2: Representation Planning

    Args:
        state: Current agent state with sub-goals

    Returns:
        State updates with retrieval plans
    """
    sub_goals = state.get('sub_goals', [])

    # === USER STEERING PREFERENCES (Co-Discovery) ===
    preferred_representations = state.get('preferred_representations', [])
    exclude_representations = state.get('exclude_representations', [])
    analysis_mode = state.get('analysis_mode')

    # DEBUG: Log all steering fields
    logger.debug(f"[PRAS Stage 2] State keys: {list(state.keys())[:20]}")
    logger.debug(f"[PRAS Stage 2] preferred_representations in state: {preferred_representations}")
    logger.debug(f"[PRAS Stage 2] exclude_representations in state: {exclude_representations}")
    logger.debug(f"[PRAS Stage 2] analysis_mode in state: {analysis_mode}")

    if preferred_representations:
        logger.info(f"[PRAS Stage 2] User steering: prefer {preferred_representations}")
    if exclude_representations:
        logger.info(f"[PRAS Stage 2] User steering: exclude {exclude_representations}")
    if analysis_mode:
        logger.info(f"[PRAS Stage 2] User steering: analysis_mode = {analysis_mode}")

    # Check for "best/highest" comparison queries that need compare_sessions
    is_comparison = state.get('is_comparison', False)
    compared_sessions = state.get('compared_sessions', [])
    original_query = state.get('original_query', '').lower()

    # Detect "best/highest/most" patterns that require compare_sessions with ALL sessions
    import re
    superlative_pattern = r'\b(best|highest|most|lowest|worst|top|bottom)\b'
    target_pattern = r'\b(session|collaboration|quality|score)\b'
    has_superlative = re.search(superlative_pattern, original_query)
    has_target = re.search(target_pattern, original_query)

    logger.info(f"[PRAS Stage 2] Global comparison check:")
    logger.info(f"  - is_comparison: {is_comparison}")
    logger.info(f"  - compared_sessions: {compared_sessions}")
    logger.info(f"  - original_query: '{original_query}'")
    logger.info(f"  - has_superlative: {bool(has_superlative)}")
    logger.info(f"  - has_target: {bool(has_target)}")

    needs_global_comparison = is_comparison and not compared_sessions and has_superlative and has_target

    if needs_global_comparison:
        logger.info("[PRAS Stage 2] GLOBAL COMPARISON detected - using compare_sessions for ALL sessions")
        # Create a single retrieval plan that uses compare_sessions
        return _plan_global_comparison(state, original_query)

    if not sub_goals:
        logger.warning("[PRAS Stage 2] No sub-goals to plan for")
        return {'pras_stage': 'plan', 'retrieval_plans': {}}

    # FIX: Check if original query is a path query - if so, ensure find_concept_path is used
    # This handles cases where the decomposer generates sub-goals that don't preserve
    # "connection between X and Y" phrasing from the original query
    if _is_path_query(original_query):
        logger.info(f"[PRAS Stage 2] Original query is a path query: '{original_query[:50]}...'")
        # Pass original query to sub-goals so _plan_for_subgoal can use it
        for sg in sub_goals:
            sg['_original_query'] = original_query

    logger.info(f"[PRAS Stage 2] Planning retrieval for {len(sub_goals)} sub-goals")

    # Context for planning
    # CRITICAL: For exploratory queries, do NOT apply session focus
    # This allows queries like "Find sessions showing hypothesis testing" to search ALL sessions
    is_exploratory = state.get('is_exploratory_query', False)

    if is_exploratory:
        session_focus = None  # Don't constrain exploratory queries to a single session
        logger.info("[PRAS Stage 2] Exploratory query - searching across ALL sessions")
    else:
        session_focus = state.get('current_session_focus')

    speaker_focus = state.get('current_speaker_focus')

    # Build retrieval plans
    retrieval_plans: Dict[str, RetrievalPlan] = {}

    for subgoal in sub_goals:
        try:
            plan = _plan_for_subgoal(
                subgoal, session_focus, speaker_focus,
                preferred_representations=preferred_representations,
                exclude_representations=exclude_representations,
                analysis_mode=analysis_mode
            )
            retrieval_plans[subgoal['id']] = plan
            logger.info(f"  - {subgoal['id']}: {len(plan['steps'])} steps planned")
        except Exception as e:
            logger.error(f"Error planning for {subgoal['id']}: {e}")
            # Fallback plan
            retrieval_plans[subgoal['id']] = _fallback_plan(subgoal, session_focus, speaker_focus)

    return {
        'pras_stage': 'plan',
        'retrieval_plans': retrieval_plans,
        'current_subgoal_index': 0,
        'current_retrieval_step': 0,
        'thought_history': state.get('thought_history', []) + [
            f"Planned retrieval for {len(sub_goals)} sub-goals with "
            f"{sum(len(p['steps']) for p in retrieval_plans.values())} total steps"
        ]
    }


def _plan_global_comparison(state: Dict[str, Any], query: str) -> Dict[str, Any]:
    """
    Create a special retrieval plan for global comparison queries.

    These are queries like "Which session has the best collaboration?"
    that require comparing ALL sessions, not just searching.

    Args:
        state: Current agent state
        query: The original query (lowercased)

    Returns:
        State updates with retrieval plan using compare_sessions
    """
    # Create a synthetic sub-goal for comparison
    sub_goal = SubGoal(
        id='sg_compare_all',
        description=f'Compare all sessions: {query}',
        indicators=['collaboration quality', '7C scores', 'ranking'],
        primary_representation='collaboration',
        secondary_representations=['transcript', 'concept_map'],
        session_filter=None,  # No filter - compare ALL
        speaker_filter=None,
        satisfied=False,
        evidence=[]
    )

    # Create retrieval steps:
    # 1. compare_sessions with empty session_ids (compares ALL)
    # 2. get_transcript for top result (for evidence/quotes)
    steps = [
        RetrievalStep(
            representation='collaboration',
            purpose='Compare ALL sessions across collaboration and quality metrics',
            tool='compare_sessions',
            parameters={},  # Empty = compare ALL sessions
            priority='primary'
        ),
        RetrievalStep(
            representation='transcript',
            purpose='Get transcript evidence from top-ranked session',
            tool='search_transcripts',
            parameters={
                'query': _extract_search_terms(query),
                'limit': 5
            },
            priority='secondary'
        )
    ]

    retrieval_plan = RetrievalPlan(
        subgoal_id=sub_goal['id'],
        steps=steps
    )

    return {
        'pras_stage': 'plan',
        'sub_goals': [sub_goal],
        'retrieval_plans': {sub_goal['id']: retrieval_plan},
        'current_subgoal_index': 0,
        'current_retrieval_step': 0,
        'use_pras': True,
        'thought_history': state.get('thought_history', []) + [
            f"Created global comparison plan with {len(steps)} steps for comparing ALL sessions"
        ]
    }


def _is_path_query(text: str) -> bool:
    """Detect if text is asking about paths/connections between concepts.

    Examples:
    - "How did they get from fusion to energy?"
    - "What's the connection between X and Y?"
    - "Trace the reasoning from X to Y"
    """
    import re

    path_patterns = [
        r'\bfrom\b.+\bto\b',                    # "from X to Y"
        r'\bpath\b|\bchain\b|\btrace\b',        # path-related words
        r'\bconnection\b.*\bbetween\b',         # "connection between"
        r'\bhow\s+did\b.*\b(get|evolve|lead)\b.*\bto\b',  # "how did X get to Y"
        r'\breasoning\b.*\bfrom\b',             # "reasoning from"
        r'\blink\b.*\bbetween\b',               # "link between"
        r'\bled\s+to\b',                        # "led to"
    ]

    text_lower = text.lower()
    for pattern in path_patterns:
        if re.search(pattern, text_lower):
            return True
    return False


def _plan_for_subgoal(
    subgoal: SubGoal,
    session_focus: int | None,
    speaker_focus: str | None,
    preferred_representations: List[str] = None,
    exclude_representations: List[str] = None,
    analysis_mode: str = None
) -> RetrievalPlan:
    """
    Create retrieval plan for a single sub-goal.

    Uses heuristics first, falls back to LLM for complex cases.
    Respects user steering preferences for representations and analysis mode.
    """
    steps: List[RetrievalStep] = []
    preferred_representations = preferred_representations or []
    exclude_representations = exclude_representations or []

    primary_rep = subgoal.get('primary_representation', 'transcript')
    secondary_reps = subgoal.get('secondary_representations', [])
    indicators = subgoal.get('indicators', [])
    description = subgoal.get('description', '')

    # === HYPOTHESIS TESTING (Co-Discovery) ===
    # If this is a hypothesis sub-goal, use test_hypothesis tool directly
    if primary_rep == 'hypothesis' or subgoal.get('_hypothesis'):
        hypothesis_claim = subgoal.get('_hypothesis', description.replace('Test hypothesis: ', ''))
        sessions_to_test = subgoal.get('_sessions_to_test')

        logger.info(f"  Hypothesis sub-goal: using test_hypothesis tool")
        logger.info(f"    Claim: {hypothesis_claim[:80]}...")

        # Build test_hypothesis step
        params = {'hypothesis': hypothesis_claim}
        if sessions_to_test:
            params['session_ids'] = sessions_to_test

        # Build steps list (hypothesis test first, then supporting evidence)
        hypothesis_steps = [
            RetrievalStep(
                representation='hypothesis',
                purpose='Test user hypothesis with systematic evidence gathering',
                tool='test_hypothesis',
                parameters=params,
                priority='primary'
            )
        ]

        # Add supporting evidence steps if we have a session focus
        if sessions_to_test:
            hypothesis_steps.append(RetrievalStep(
                representation='transcript',
                purpose='Get transcript evidence for hypothesis verification',
                tool='get_transcript',
                parameters={'session_id': sessions_to_test[0]},
                priority='secondary'
            ))
            hypothesis_steps.append(RetrievalStep(
                representation='concept_map',
                purpose='Get concept map for reasoning pattern analysis',
                tool='get_concept_map',
                parameters={'session_id': sessions_to_test[0]},
                priority='secondary'
            ))

        return RetrievalPlan(
            subgoal_id=subgoal.get('id', 'sg_hypothesis'),
            primary_representation='hypothesis',
            steps=hypothesis_steps
        )

    # === APPLY USER STEERING ===
    # If user specified preferred representations, override sub-goal's choices
    if preferred_representations:
        # Use first preferred as primary, rest as secondary
        primary_rep = preferred_representations[0]
        secondary_reps = preferred_representations[1:] if len(preferred_representations) > 1 else []
        logger.info(f"  User steering: primary={primary_rep}, secondary={secondary_reps}")

    # Filter out excluded representations
    if exclude_representations:
        if primary_rep in exclude_representations:
            # Find alternative primary from secondary
            for alt in secondary_reps:
                if alt not in exclude_representations:
                    primary_rep = alt
                    break
            else:
                # Fall back to transcript if nothing else available
                primary_rep = 'transcript' if 'transcript' not in exclude_representations else 'concept_map'
        secondary_reps = [r for r in secondary_reps if r not in exclude_representations]
        logger.info(f"  After exclusions: primary={primary_rep}, secondary={secondary_reps}")

    # === ANALYSIS MODE HANDLING ===
    # Different modes affect tool selection strategy
    if analysis_mode == 'trace':
        # Trace mode: prioritize graph tools for path finding
        logger.info("  Analysis mode 'trace': prioritizing path-finding tools")
        # Force path query detection to use find_concept_path
        if not _is_path_query(description):
            # Add path-like context to description for tool selection
            description = f"trace the path of {description}"

    elif analysis_mode == 'compare':
        # Compare mode: use compare_sessions tool
        logger.info("  Analysis mode 'compare': will use compare_sessions")
        steps.append(RetrievalStep(
            representation='collaboration',
            purpose='Compare sessions as requested by user',
            tool='compare_sessions',
            parameters={},  # Will compare all or focused sessions
            priority='primary'
        ))

    elif analysis_mode == 'explore':
        # Explore mode: prioritize discovery/search tools
        logger.info("  Analysis mode 'explore': prioritizing discovery tools")
        steps.append(RetrievalStep(
            representation='discovery',
            purpose='Explore sessions matching query',
            tool='search_for_sessions',
            parameters={
                'query': _extract_search_terms(description),
                'top_k': 5  # More results for exploration
            },
            priority='primary'
        ))

    # FIX: Check both sub-goal description AND original query for path patterns
    # The original query might contain "connection between X and Y" but the
    # decomposed sub-goal description might not preserve this phrasing
    original_query = subgoal.get('_original_query', '')  # Pass from state if available

    # Check for path-tracing queries - use find_concept_path
    is_path = _is_path_query(description)
    if not is_path and original_query:
        is_path = _is_path_query(original_query)

    if is_path:
        logger.info(f"Detected path query in sub-goal: {description[:50]}...")
        # Try to extract path params from description first, then original query
        path_params = _build_concept_path_params(description, session_focus)
        if not (path_params.get('from_concept') and path_params.get('to_concept')) and original_query:
            path_params = _build_concept_path_params(original_query, session_focus)
            logger.info(f"Extracted path params from original query: {path_params}")
        if path_params.get('from_concept') and path_params.get('to_concept'):
            steps.append(RetrievalStep(
                representation='graph',
                purpose='Trace reasoning path between concepts',
                tool='find_concept_path',
                parameters=path_params,
                priority='primary'
            ))
            # Also get concept map for context
            if session_focus:
                steps.append(RetrievalStep(
                    representation='concept_map',
                    purpose='Get full concept context',
                    tool='get_concept_map',
                    parameters={'session_id': session_focus},
                    priority='secondary'
                ))
                # CRITICAL: Always include transcript for evolution/path queries
                # Transcripts show HOW the discussion actually progressed
                if 'transcript' not in exclude_representations:
                    steps.append(RetrievalStep(
                        representation='transcript',
                        purpose='Get actual discussion flow to trace concept evolution',
                        tool='get_transcript',
                        parameters={'session_id': session_focus},
                        priority='secondary'
                    ))
            return RetrievalPlan(subgoal_id=subgoal['id'], steps=steps)

    # Use explicit filters from sub-goal (set by decomposer), fall back to state context
    # This replaces the old regex extraction hack
    effective_session = subgoal.get('session_filter') or session_focus
    effective_speaker = subgoal.get('speaker_filter') or speaker_focus

    if effective_session != session_focus or effective_speaker != speaker_focus:
        logger.info(f"  Using sub-goal filters: session={effective_session}, speaker={effective_speaker}")

    # Override the passed-in values with sub-goal-specific values
    session_focus = effective_session
    speaker_focus = effective_speaker

    # Step 1: Primary representation
    primary_step = _create_step_for_representation(
        representation=primary_rep,
        indicators=indicators,
        description=description,
        session_focus=session_focus,
        speaker_focus=speaker_focus,
        priority='primary'
    )
    if primary_step:
        steps.append(primary_step)

    # Step 2: Secondary representations
    for rep in secondary_reps[:2]:  # Limit to 2 secondary
        secondary_step = _create_step_for_representation(
            representation=rep,
            indicators=indicators,
            description=description,
            session_focus=session_focus,
            speaker_focus=speaker_focus,
            priority='secondary'
        )
        if secondary_step:
            steps.append(secondary_step)

    # Step 3: Add verification step if we have transcript as secondary
    if 'transcript' in secondary_reps and primary_rep != 'transcript':
        verification_step = RetrievalStep(
            representation='transcript',
            purpose='Verify findings with direct quotes',
            tool='search_transcripts',
            parameters=_build_transcript_params(description, session_focus, speaker_focus),
            priority='verification'
        )
        steps.append(verification_step)

    # Step 4: BASELINE TRANSCRIPT INCLUSION
    # If we have a session focus and transcript isn't already included,
    # add it as a baseline source. Transcripts are fundamental evidence
    # that should almost always be consulted.
    existing_tools = {s.get('tool') if isinstance(s, dict) else s.tool for s in steps}
    transcript_tools = {'get_transcript', 'search_transcripts'}
    has_transcript = bool(existing_tools & transcript_tools)

    if (session_focus
        and not has_transcript
        and 'transcript' not in exclude_representations
        and primary_rep != 'transcript'):
        logger.info(f"  Adding baseline transcript for session {session_focus}")
        steps.append(RetrievalStep(
            representation='transcript',
            purpose='Baseline evidence from actual discussion',
            tool='get_transcript',
            parameters={'session_id': session_focus},
            priority='baseline'
        ))

    return RetrievalPlan(
        subgoal_id=subgoal['id'],
        steps=steps
    )


def _create_step_for_representation(
    representation: str,
    indicators: List[str],
    description: str,
    session_focus: int | None,
    speaker_focus: str | None,
    priority: str
) -> RetrievalStep | None:
    """Create a retrieval step for a given representation.

    CRITICAL: When no session_focus is provided, we MUST use discovery tools
    (search_for_sessions, search_transcripts) instead of returning None.
    """
    # Normalize representation name
    rep_normalized = representation.lower().replace(' ', '_').replace('-', '_')

    # Map common variations
    REP_ALIASES = {
        'concept': 'concept_map',
        'concepts': 'concept_map',
        'concept_maps': 'concept_map',
        'transcripts': 'transcript',
        '7c': 'collaboration',
        '7c_analysis': 'collaboration',
        'collaboration_analysis': 'collaboration',
        'speaker': 'speaker_profile',
        'speakers': 'speaker_profile',
        'session': 'session_overview',
        'sessions': 'session_overview',
        'overview': 'session_overview'
    }

    rep_normalized = REP_ALIASES.get(rep_normalized, rep_normalized)

    rep_config = REPRESENTATION_CONFIG.get(rep_normalized)
    if not rep_config:
        logger.warning(f"Unknown representation: '{representation}' (normalized: '{rep_normalized}')")
        # FALLBACK: Use discovery when representation is unknown
        return _create_discovery_step(description, priority)

    # Choose best tool for this representation
    tools = rep_config.get('tools', {})
    if not tools:
        return _create_discovery_step(description, priority)

    # === CRITICAL: Choose tool based on whether we have session context ===
    # If we have session_focus, prefer tools that require session
    # If no session_focus, MUST use discovery tools

    tool_name = None
    tool_info = None

    if session_focus:
        # We have session context - prefer get_artifacts for complete data
        for name, info in tools.items():
            if info.get('requires_session', True):
                tool_name = name
                tool_info = info
                break

    if not tool_name:
        # No session context OR no session-requiring tool found
        # Use discovery/search tools
        for name, info in tools.items():
            if not info.get('requires_session', True):
                tool_name = name
                tool_info = info
                break

    if not tool_name:
        # Last resort: use first available tool
        tool_name = list(tools.keys())[0]
        tool_info = tools[tool_name]

    # Build parameters
    params = {}

    # === SPECIFIC ARTIFACT TOOLS ===
    if tool_name == 'get_transcript':
        if session_focus:
            params = {'session_id': session_focus}
        else:
            logger.info("No session_focus for get_transcript, using search_for_sessions instead")
            return _create_discovery_step(description, priority)

    elif tool_name == 'get_concept_map':
        if session_focus:
            params = {'session_id': session_focus}
        else:
            logger.info("No session_focus for get_concept_map, using search_for_sessions instead")
            return _create_discovery_step(description, priority)

    elif tool_name == 'get_7c_analysis':
        if session_focus:
            params = {'session_id': session_focus}
        else:
            logger.info("No session_focus for get_7c_analysis, using search_for_sessions instead")
            return _create_discovery_step(description, priority)

    elif tool_name == 'search_for_sessions':
        # Extract meaningful search terms from the description
        search_query = _extract_search_terms(description)
        params = {
            'query': search_query,
            'top_k': 3
        }

    elif tool_name == 'get_speaker_profile':
        if speaker_focus:
            params = {'speaker_name': speaker_focus}
            if session_focus:
                params['session_id'] = session_focus
        else:
            logger.warning("get_speaker_profile requires speaker_name, using discovery")
            return _create_discovery_step(description, priority)

    elif tool_name == 'list_sessions':
        params = {}  # No parameters needed

    elif tool_name == 'synthesize':
        # Cross-session synthesis - needs session_ids
        params = {
            'questions': [description]
        }
        if session_focus:
            params['session_ids'] = [session_focus]

    elif tool_name == 'find_concept_path':
        # Graph reasoning - extract concepts from query
        params = _build_concept_path_params(description, session_focus)

    # === LEGACY TOOLS (fallback) ===
    elif tool_name == 'search_transcripts':
        params = _build_transcript_params(description, session_focus, speaker_focus)
    elif tool_name == 'search_concepts':
        params = _build_concept_params(description, indicators, session_focus)
    elif tool_name == 'explore_concepts':
        params = {'direction': 'both', 'depth': 2}
    elif tool_name == 'get_concept_map':
        if session_focus:
            params = {'session_id': session_focus}
        else:
            return _create_discovery_step(description, priority)
    elif tool_name == 'get_collaboration_analysis':
        if session_focus:
            params = {'session_id': session_focus}
        else:
            return _create_discovery_step(description, priority)
    elif tool_name == 'analyze_speaker':
        if speaker_focus:
            params = {'speaker_name': speaker_focus}
            if session_focus:
                params['session_ids'] = [session_focus]
        else:
            return _create_discovery_step(description, priority)
    elif tool_name == 'get_session_overview':
        if session_focus:
            params = {'session_id': session_focus}
        else:
            return _create_discovery_step(description, priority)
    elif tool_name == 'compare_sessions':
        params = {}  # Requires session_ids from state

    return RetrievalStep(
        representation=representation,
        purpose=tool_info.get('purpose', f'Retrieve from {representation}'),
        tool=tool_name,
        parameters=params,
        priority=priority
    )


def _create_discovery_step(description: str, priority: str) -> RetrievalStep:
    """Create a discovery step using search_for_sessions.

    This is the CRITICAL fallback when no session context is available.
    We use semantic search to find relevant sessions.
    """
    search_query = _extract_search_terms(description)
    logger.info(f"Creating discovery step with query: '{search_query}'")

    return RetrievalStep(
        representation='discovery',
        purpose=f'Find sessions relevant to: {search_query}',
        tool='search_for_sessions',
        parameters={
            'query': search_query,
            'top_k': 3
        },
        priority=priority
    )


def _build_transcript_params(
    description: str,
    session_focus: int | None,
    speaker_focus: str | None
) -> Dict[str, Any]:
    """Build parameters for search_transcripts."""
    params = {
        'query': _extract_search_terms(description),
        'limit': 10
    }
    if session_focus:
        params['session_ids'] = [session_focus]
    if speaker_focus:
        params['speaker'] = speaker_focus
    return params


def _build_concept_params(
    description: str,
    indicators: List[str],
    session_focus: int | None
) -> Dict[str, Any]:
    """Build parameters for search_concepts."""
    params = {
        'query': _extract_search_terms(description),
        'limit': 10
    }
    if session_focus:
        params['session_ids'] = [session_focus]

    # Check indicators for concept type hints
    indicator_text = ' '.join(indicators).lower()
    if 'causal' in indicator_text or 'hypothesis' in indicator_text:
        params['concept_types'] = ['hypothesis', 'idea']
    elif 'question' in indicator_text:
        params['concept_types'] = ['question']

    return params


def _build_concept_path_params(
    description: str,
    session_focus: int | None
) -> Dict[str, Any]:
    """Build parameters for find_concept_path.

    Extracts from_concept and to_concept from path-style queries like:
    - "How did they get from X to Y?"
    - "What's the connection between X and Y?"
    - "Trace the path from fusion to energy"
    """
    import re

    params = {}

    if session_focus:
        params['session_id'] = session_focus

    # Try common path patterns
    patterns = [
        # "from X to Y" pattern
        r'from\s+["\']?([^"\']+?)["\']?\s+to\s+["\']?([^"\']+?)["\']?(?:\s|$|\?)',
        # "between X and Y" pattern
        r'between\s+["\']?([^"\']+?)["\']?\s+and\s+["\']?([^"\']+?)["\']?(?:\s|$|\?)',
        # "X to Y" pattern (simpler)
        r'([a-zA-Z\s]+?)\s+to\s+([a-zA-Z\s]+?)(?:\s+in\s+session|\?|$)',
        # "connection between X and Y"
        r'connection.*?["\']?([^"\']+?)["\']?\s+and\s+["\']?([^"\']+?)["\']?(?:\s|$|\?)',
    ]

    for pattern in patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            from_concept = match.group(1).strip()
            to_concept = match.group(2).strip()

            # Clean up extracted concepts
            stop_words = {'how', 'did', 'the', 'they', 'get', 'discussion', 'ideas'}
            from_concept = ' '.join(w for w in from_concept.split() if w.lower() not in stop_words)
            to_concept = ' '.join(w for w in to_concept.split() if w.lower() not in stop_words)

            if from_concept and to_concept:
                params['from_concept'] = from_concept
                params['to_concept'] = to_concept
                logger.info(f"Extracted path concepts: '{from_concept}' -> '{to_concept}'")
                break

    # If no pattern matched, try to extract any noun phrases as concepts
    if 'from_concept' not in params:
        # Extract meaningful terms and use first two as from/to
        terms = _extract_search_terms(description).split()
        if len(terms) >= 2:
            params['from_concept'] = terms[0]
            params['to_concept'] = terms[-1]
            logger.info(f"Fallback path concepts: '{terms[0]}' -> '{terms[-1]}'")

    return params


def _extract_search_terms(description: str) -> str:
    """Extract key search terms from description.

    CRITICAL: Must extract meaningful terms for semantic search.
    For "What was said about AI?", should extract "AI".
    """
    # Expanded stop words list
    stop_words = {
        # Common query words
        'find', 'the', 'a', 'an', 'in', 'of', 'to', 'for', 'and', 'or',
        'evidence', 'look', 'search', 'get', 'analyze', 'assess', 'evaluate',
        'what', 'was', 'were', 'is', 'are', 'about', 'how', 'why', 'when',
        'who', 'which', 'that', 'this', 'these', 'those', 'said', 'say',
        'tell', 'me', 'show', 'describe', 'discuss', 'discussed', 'talking',
        'talk', 'any', 'some', 'all', 'each', 'both', 'more', 'most', 'less',
        'relevant', 'related', 'content', 'specific', 'statements', 'quotes',
        'key', 'important', 'main', 'primary', 'secondary', 'does', 'did',
        'has', 'have', 'had', 'been', 'being', 'with', 'from', 'into', 'through',
        'during', 'before', 'after', 'above', 'below', 'between', 'under', 'over',
        'can', 'could', 'would', 'should', 'may', 'might', 'must', 'will',
        'session', 'sessions', 'discussion', 'discussions', 'transcript', 'transcripts'
    }

    # First, try to preserve important short terms like "AI", "7C", etc.
    # These are often acronyms or important keywords
    words = description.split()
    meaningful = []

    for word in words:
        # Remove punctuation from word
        clean_word = word.strip('.,?!:;()[]{}"\'-')
        word_lower = clean_word.lower()

        # Keep if:
        # 1. Not a stop word AND either:
        #    a. Length > 2, OR
        #    b. Is all uppercase (acronym like "AI", "7C"), OR
        #    c. Contains numbers (like "7C")
        if word_lower not in stop_words:
            is_acronym = clean_word.isupper() and len(clean_word) >= 2
            has_number = any(c.isdigit() for c in clean_word)
            is_long_enough = len(clean_word) > 2

            if is_acronym or has_number or is_long_enough:
                meaningful.append(clean_word)

    # Take top 5 terms
    result = ' '.join(meaningful[:5])

    # If we got nothing, fallback to original text minus obvious stop words
    if not result.strip():
        basic_stops = {'what', 'was', 'is', 'the', 'a', 'an', 'in', 'of', 'to', 'for'}
        words = [w for w in description.lower().split() if w not in basic_stops]
        result = ' '.join(words[:5])

    logger.debug(f"Extracted search terms: '{result}' from '{description}'")
    return result


def _fallback_plan(
    subgoal: SubGoal,
    session_focus: int | None,
    speaker_focus: str | None
) -> RetrievalPlan:
    """Create a basic fallback plan using optimal tools.

    CRITICAL: Always ensure at least one retrieval step, even without session context.
    """
    steps = []
    description = subgoal.get('description', '')
    search_query = _extract_search_terms(description)

    if session_focus:
        # We have session context - use specific tools
        # Step 1: Get transcript (primary evidence)
        transcript_step = RetrievalStep(
            representation='transcript',
            purpose='Get complete transcript for session',
            tool='get_transcript',
            parameters={'session_id': session_focus},
            priority='primary'
        )
        steps.append(transcript_step)
        # Step 2: Get concept map (secondary evidence)
        concept_step = RetrievalStep(
            representation='concept_map',
            purpose='Get concept map for session',
            tool='get_concept_map',
            parameters={'session_id': session_focus},
            priority='secondary'
        )
        steps.append(concept_step)
    else:
        # NO session context - MUST use discovery first
        # Step 1: Search for relevant sessions
        discovery_step = RetrievalStep(
            representation='discovery',
            purpose=f'Find sessions relevant to: {search_query}',
            tool='search_for_sessions',
            parameters={
                'query': search_query,
                'top_k': 3
            },
            priority='primary'
        )
        steps.append(discovery_step)

        # Step 2: Also search transcripts directly (cross-session)
        transcript_step = RetrievalStep(
            representation='transcript',
            purpose='Find relevant transcript content',
            tool='search_transcripts',
            parameters={
                'query': search_query,
                'limit': 10
            },
            priority='secondary'
        )
        steps.append(transcript_step)

    return RetrievalPlan(
        subgoal_id=subgoal['id'],
        steps=steps
    )


def get_next_retrieval_step(state: Dict[str, Any]) -> Dict[str, Any] | None:
    """
    Get the next retrieval step to execute.

    Used by the targeted retriever to get what to execute next.

    Returns:
        Dict with subgoal_id, step_index, and step details, or None if done
    """
    sub_goals = state.get('sub_goals', [])
    retrieval_plans = state.get('retrieval_plans', {})
    current_subgoal_idx = state.get('current_subgoal_index', 0)
    current_step_idx = state.get('current_retrieval_step', 0)

    if current_subgoal_idx >= len(sub_goals):
        return None

    current_subgoal = sub_goals[current_subgoal_idx]
    plan = retrieval_plans.get(current_subgoal['id'])

    if not plan:
        return None

    steps = plan.get('steps', [])
    if current_step_idx >= len(steps):
        return None

    return {
        'subgoal_id': current_subgoal['id'],
        'subgoal_index': current_subgoal_idx,
        'step_index': current_step_idx,
        'step': steps[current_step_idx],
        'subgoal': current_subgoal,
        'total_steps': len(steps),
        'total_subgoals': len(sub_goals)
    }
