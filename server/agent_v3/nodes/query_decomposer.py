"""
Query Decomposer Node for BLINC Agent V3

PRAS Stage 1: Query Understanding & Decomposition

Decomposes complex queries into operational sub-goals by:
1. Identifying abstract constructs (e.g., "systems thinking", "critical thinking")
2. Operationalizing constructs into observable indicators
3. Generating sub-goals targeting specific representations
"""

import logging
import json
from typing import Dict, Any, List

from ..llm import get_reasoning_client
from ..state import SubGoal

logger = logging.getLogger(__name__)

# Comparison query patterns - these bypass PRAS and go to reasoning
COMPARISON_PATTERNS = [
    r'\bcompare\b',
    r'\bcomparison\b',
    r'\bvs\.?\b',
    r'\bversus\b',
    r'\bdifference\s+between\b',
    r'\bcontrast\b',
    r'\bbetter\b.*\bor\b',
    r'\bwhich\s+(session|one)\b.*\b(better|more|higher|best|worst|lowest)\b',
    r'\bhow\s+do(?:es)?\b.+\bdiffer\b',
    r'\bsimilar(?:ities)?\s+between\b',
    # Superlative patterns that require comparing ALL sessions
    r'\b(best|worst|highest|lowest|top|bottom)\s+(collaboration|quality|score|session)\b',
    r'\bthe\s+(best|worst|highest|lowest)\b',
    r'\bwhat\s+is\s+the\s+(best|worst|highest|lowest)\b',
    r'\bwhich\s+.*(best|worst|highest|lowest|most|least)\b',
]


def _is_comparison_query(query: str) -> bool:
    """Detect if query is a comparison between sessions/speakers."""
    import re
    query_lower = query.lower()
    for pattern in COMPARISON_PATTERNS:
        if re.search(pattern, query_lower):
            return True
    return False


# Hypothesis query patterns - detect when user is proposing something to test
HYPOTHESIS_PATTERNS = [
    r'\b(i\s+(?:think|believe|hypothesize|suspect))\b',
    r'\b(my\s+hypothesis\s+is)\b',
    r'\b(could\s+it\s+be\s+that)\b',
    r'\b(i\s+wonder\s+if)\b',
    r'\b(what\s+if)\b',
    r'\btest\s+(?:the\s+)?(?:hypothesis|idea|theory)\b',
    r'\b(is\s+it\s+(?:true|the\s+case)\s+that)\b',
    r'\b(?:prove|disprove|verify|confirm)\s+(?:that|whether)\b',
]


def _is_hypothesis_query(query: str) -> bool:
    """Detect if query contains a hypothesis to test."""
    import re
    query_lower = query.lower()
    return any(re.search(p, query_lower) for p in HYPOTHESIS_PATTERNS)


def _extract_hypothesis(query: str) -> str:
    """
    Extract the hypothesis claim from query, if present.

    Returns the extracted hypothesis or the original query if extraction fails.
    """
    import re
    query_lower = query.lower()

    # Patterns for extracting hypothesis claims
    extraction_patterns = [
        (r'i\s+(?:think|believe|hypothesize|suspect)\s+(?:that\s+)?(.+?)(?:\.|$)', 1),
        (r'could\s+it\s+be\s+(?:that\s+)?(.+?)(?:\?|$)', 1),
        (r'what\s+if\s+(.+?)(?:\?|$)', 1),
        (r'i\s+wonder\s+if\s+(.+?)(?:\.|$)', 1),
        (r'is\s+it\s+(?:true|the\s+case)\s+that\s+(.+?)(?:\?|$)', 1),
        (r'(?:prove|disprove|verify|confirm)\s+(?:that|whether)\s+(.+?)(?:\.|$)', 1),
    ]

    for pattern, group in extraction_patterns:
        match = re.search(pattern, query_lower)
        if match:
            return match.group(group).strip()

    # If no pattern matches, return original query (cleaned up)
    return query.strip()


# =============================================================================
# User Steering Directives (Co-Discovery)
# =============================================================================

# Patterns for detecting user steering preferences
STEERING_PATTERNS = {
    # Representation preferences
    'transcript_focus': [
        r'\b(?:use|using|focus on|based on|from)\s+(?:the\s+)?transcript',
        r'\b(?:just|only)\s+(?:the\s+)?transcript',
        r'\bquotes?\s+(?:from|only)',
        r'\bwhat\s+(?:was|did)\s+(?:\w+\s+)?(?:actually\s+)?(?:say|said)\b',
    ],
    'concept_map_focus': [
        r'\b(?:use|using|focus on|based on|from)\s+(?:the\s+)?concept\s*map',
        r'\bhow\s+(?:are\s+)?(?:ideas?|concepts?)\s+connected',
        r'\b(?:show|trace|find)\s+(?:the\s+)?(?:path|connection|relationship)',
        r'\bidea\s+(?:connections?|relationships?|structure)',
        # Graph structure queries
        r'\bquestion\s+density\b',
        r'\bidea\s+distribution\b',
        r'\b(?:how\s+many|count\s+of)\s+(?:questions?|ideas?|problems?|solutions?)',
        r'\b(?:node|concept)\s+types?\b',
        r'\bgraph\s+(?:structure|statistics|metrics)\b',
        r'\bby\s+speaker\b.*(?:ideas?|contributions?|questions?)',
        r'\bwho\s+contributed\s+(?:the\s+)?(?:most|more)\s+(?:ideas?|questions?)',
    ],
    'collaboration_focus': [
        r'\b(?:use|using|focus on|based on)\s+(?:the\s+)?(?:7c|collaboration)',
        r'\bcollaboration\s+(?:scores?|metrics?|analysis)',
        r'\b7c\s+(?:scores?|analysis|dimensions?)',
        r'\bhow\s+well\s+did\s+(?:they\s+)?collaborat',
    ],
    'speaker_focus': [
        r'\b(?:focus on|analyze)\s+(?:speaker|participant)',
        r'\bspeaker\s+(?:profile|analysis|patterns?)',
        r'\b(?:who|which\s+speaker)\s+(?:contributed|said|participated)',
    ],
    # Analysis mode preferences
    'explore_mode': [
        r'\bexplore\b',
        r'\bwhat\s+(?:patterns?|themes?)\s+(?:are|emerge)',
        r'\bdiscover\b',
        r'\bfind\s+(?:patterns?|insights?)',
    ],
    'compare_mode': [
        r'\bcompare\b',
        r'\bdifference\s+between\b',
        r'\bwhich\s+(?:session|one)\s+(?:is\s+)?(?:better|worse)',
        r'\bvs\.?\b',
    ],
    'trace_mode': [
        r'\btrace\b',
        r'\bpath\s+(?:from|between)',
        r'\bhow\s+did\s+(?:\w+\s+)?(?:lead|connect)\s+to',
        r'\bconnection\s+between',
    ],
}


def _extract_steering_directives(query: str) -> dict:
    """
    Extract user steering preferences from query.

    Returns dict with:
    - preferred_representations: list of reps user wants to focus on
    - analysis_mode: 'explore', 'compare', 'trace', or None
    - exclude_representations: list of reps to skip (if user says "without X")
    """
    import re
    query_lower = query.lower()

    directives = {
        'preferred_representations': [],
        'analysis_mode': None,
        'exclude_representations': [],
    }

    # Check representation preferences
    rep_mapping = {
        'transcript_focus': 'transcript',
        'concept_map_focus': 'concept_map',
        'collaboration_focus': 'collaboration',
        'speaker_focus': 'speaker_profile',
    }

    for pattern_key, rep_name in rep_mapping.items():
        patterns = STEERING_PATTERNS.get(pattern_key, [])
        for pattern in patterns:
            if re.search(pattern, query_lower):
                if rep_name not in directives['preferred_representations']:
                    directives['preferred_representations'].append(rep_name)
                break

    # Check analysis mode
    mode_mapping = {
        'explore_mode': 'explore',
        'compare_mode': 'compare',
        'trace_mode': 'trace',
    }

    for pattern_key, mode_name in mode_mapping.items():
        patterns = STEERING_PATTERNS.get(pattern_key, [])
        for pattern in patterns:
            if re.search(pattern, query_lower):
                directives['analysis_mode'] = mode_name
                break
        if directives['analysis_mode']:
            break

    # Check for exclusions ("without", "don't use", "skip")
    exclusion_patterns = [
        (r'\b(?:without|skip|don\'t use|no)\s+(?:the\s+)?transcript', 'transcript'),
        (r'\b(?:without|skip|don\'t use|no)\s+(?:the\s+)?concept\s*map', 'concept_map'),
        (r'\b(?:without|skip|don\'t use|no)\s+(?:the\s+)?(?:7c|collaboration)', 'collaboration'),
    ]

    for pattern, rep_name in exclusion_patterns:
        if re.search(pattern, query_lower):
            directives['exclude_representations'].append(rep_name)

    return directives


# Representation types and what they can provide
REPRESENTATION_CAPABILITIES = {
    "transcript": {
        "provides": ["direct quotes", "temporal sequence", "speaker attribution", "language patterns"],
        "good_for": ["evidence of what was said", "discourse patterns", "specific claims"],
        "epistemic_value": "high (primary source)"
    },
    "concept_map": {
        "provides": ["ideas", "relationships", "clusters", "speaker attribution"],
        "good_for": ["semantic structure", "causal relationships", "thematic organization"],
        "epistemic_value": "medium (derived artifact)"
    },
    "collaboration": {
        "provides": ["7C dimension scores", "explanations", "overall quality"],
        "good_for": ["interaction quality", "participation balance", "collaborative behaviors"],
        "epistemic_value": "medium (interpreted)"
    },
    "speaker_profile": {
        "provides": ["aggregated metrics", "cross-session patterns", "contribution types"],
        "good_for": ["individual patterns", "comparative analysis"],
        "epistemic_value": "medium (aggregated)"
    },
    "session_overview": {
        "provides": ["summary", "participants", "themes", "duration"],
        "good_for": ["context", "high-level understanding"],
        "epistemic_value": "low (summary)"
    }
}

# Common abstract constructs and their operationalizations
CONSTRUCT_OPERATIONALIZATIONS = {
    "systems thinking": [
        "identifying causal relationships between concepts",
        "seeing interconnections across ideas",
        "understanding feedback loops",
        "considering multiple perspectives",
        "recognizing emergent patterns"
    ],
    "critical thinking": [
        "questioning assumptions",
        "evaluating evidence",
        "considering alternative viewpoints",
        "identifying logical flaws",
        "distinguishing fact from opinion"
    ],
    "collaboration": [
        "building on others' ideas",
        "active listening indicators",
        "turn-taking balance",
        "supportive communication",
        "constructive disagreement"
    ],
    "engagement": [
        "question asking frequency",
        "contribution length and depth",
        "topic initiation",
        "response to others",
        "sustained participation"
    ],
    "creativity": [
        "novel idea generation",
        "unexpected connections",
        "hypothetical exploration",
        "analogy usage",
        "divergent thinking"
    ]
}

DECOMPOSITION_SYSTEM_PROMPT = """You are an expert at analyzing educational queries about collaborative learning discussions.

Your task is to decompose queries into targeted sub-goals for evidence retrieval.

## Available Data Representations

1. **TRANSCRIPT** - Raw discussion transcripts with speaker, timestamp, and text
   - Good for: Finding exact quotes, what someone said about a topic, discourse patterns
   - CRITICAL: This is the primary evidence source. Most queries need transcript evidence.

2. **CONCEPT_MAP** - Structured graph of ideas, questions, hypotheses and relationships
   - Good for: Semantic structure, idea connections, themes, who contributed what concepts
   - Enhances transcript evidence with structured representation

3. **COLLABORATION** - 7C analysis scores (0-100) for collaboration quality
   - Dimensions: Climate, Communication, Contribution, Conflict, Context, Constructive, Compatibility
   - Good for: Interaction quality, participation metrics, collaborative behaviors

4. **SPEAKER_PROFILE** - Aggregated metrics about individual speakers
   - Good for: Individual patterns, contribution types, cross-session speaker analysis

5. **SESSION_OVERVIEW** - High-level summary of a session
   - Good for: Context, participants, main themes, duration

## Response Format

Return a JSON object:
{
    "is_simple_query": boolean,
    "abstract_constructs": ["construct1", ...],
    "operationalization": {
        "construct1": ["indicator1", "indicator2", ...]
    },
    "sub_goals": [
        {
            "id": "sg1",
            "description": "What evidence to find",
            "indicators": ["specific things to look for"],
            "primary_representation": "transcript|concept_map|collaboration|speaker_profile",
            "secondary_representations": [],
            "session_filter": null,  // Session ID if query focuses on specific session
            "speaker_filter": null   // Speaker name if query focuses on specific person
        }
    ]
}

## Query Classification

**SIMPLE QUERIES (is_simple_query=true, empty sub_goals):**
- "What sessions are available?" - Just list sessions
- "Tell me about session 20" - Just get overview
- "How long was session 19?" - Just get metadata

**ALL OTHER QUERIES need sub_goals (is_simple_query=false):**
- "What did Tucker say about AI?" → Needs transcript search with speaker filter
- "Compare sessions 19 and 20" → Needs sub-goals for each session
- "Did Tucker demonstrate systems thinking?" → Needs operationalization + transcript search
- "Which session had better collaboration?" → Needs collaboration metrics for comparison

## Critical Rules

1. **TRANSCRIPT IS FOUNDATIONAL**
   - For ANY query about content, quotes, what was said, or speaker behavior:
     ALWAYS include at least one sub-goal with primary_representation="transcript"
   - Other representations (concept_map, collaboration) ENHANCE but don't replace transcripts

2. **7C IS MANDATORY FOR ENGAGEMENT/COLLABORATION QUERIES**
   - For ANY query about: engagement, collaboration, participation, quality, productive discourse, interaction
   - You MUST include a sub-goal with primary_representation="collaboration" to get 7C scores
   - The 7C analysis provides QUANTITATIVE metrics (0-100 scores) that are essential for:
     * Comparing sessions ("which had better collaboration?")
     * Assessing engagement levels ("why higher engagement?")
     * Evaluating participation balance ("contribution patterns")
   - Without 7C data, you cannot make claims about engagement or collaboration quality
   - Example: "Why did some discussions have higher engagement?" REQUIRES:
     * sg1: Get 7C scores for multiple sessions, primary_representation="collaboration"
     * sg2: Get transcript evidence, primary_representation="transcript"

3. **USE FILTERS EXPLICITLY**
   - If query mentions a session (e.g., "session 19", "Nuclear Fusion session"):
     Set session_filter to the session ID
   - If query mentions a speaker (e.g., "Tucker", "David"):
     Set speaker_filter to the speaker name
   - These filters help retrieval target the right data

3. **COMPARISON QUERIES**
   - Create one sub-goal per session being compared
   - Include indicators for what dimensions to compare (themes, collaboration, speakers)
   - Example: "Compare AI Alive and Nuclear Fusion" should generate:
     * sg1: Get transcript and themes for session 19, session_filter=19
     * sg2: Get transcript and themes for session 20, session_filter=20
     * sg3: Compare collaboration metrics between sessions (optional)

4. **ABSTRACT CONSTRUCTS**
   - For concepts like "systems thinking", "critical thinking", "engagement":
     * List in abstract_constructs
     * Operationalize into observable indicators
     * Map indicators to transcript evidence + supporting artifacts

## Examples

**Query: "What did Tucker say about AI in session 19?"**
```json
{
    "is_simple_query": false,
    "abstract_constructs": [],
    "operationalization": {},
    "sub_goals": [
        {
            "id": "sg1",
            "description": "Find Tucker's statements about AI",
            "indicators": ["AI", "artificial intelligence", "machine learning", "reasoning"],
            "primary_representation": "transcript",
            "secondary_representations": ["concept_map"],
            "session_filter": 19,
            "speaker_filter": "Tucker"
        }
    ]
}
```

**Query: "Compare collaboration in sessions 19 and 20"**
```json
{
    "is_simple_query": false,
    "abstract_constructs": ["collaboration"],
    "operationalization": {
        "collaboration": ["turn-taking", "building on ideas", "supportive responses"]
    },
    "sub_goals": [
        {
            "id": "sg1",
            "description": "Get collaboration evidence from session 19",
            "indicators": ["interaction patterns", "7C scores", "supportive language"],
            "primary_representation": "transcript",
            "secondary_representations": ["collaboration"],
            "session_filter": 19,
            "speaker_filter": null
        },
        {
            "id": "sg2",
            "description": "Get collaboration evidence from session 20",
            "indicators": ["interaction patterns", "7C scores", "supportive language"],
            "primary_representation": "transcript",
            "secondary_representations": ["collaboration"],
            "session_filter": 20,
            "speaker_filter": null
        }
    ]
}
```

**Query: "Did Tucker demonstrate systems thinking?"**
```json
{
    "is_simple_query": false,
    "abstract_constructs": ["systems thinking"],
    "operationalization": {
        "systems thinking": [
            "identifying causal relationships",
            "seeing interconnections",
            "considering multiple perspectives",
            "recognizing feedback loops"
        ]
    },
    "sub_goals": [
        {
            "id": "sg1",
            "description": "Find Tucker's statements showing systems thinking indicators",
            "indicators": ["causal language", "interconnections", "perspective-taking"],
            "primary_representation": "transcript",
            "secondary_representations": [],
            "session_filter": null,
            "speaker_filter": "Tucker"
        },
        {
            "id": "sg2",
            "description": "Find concepts Tucker contributed showing relational thinking",
            "indicators": ["causal edges", "multi-node connections", "synthesis nodes"],
            "primary_representation": "concept_map",
            "secondary_representations": [],
            "session_filter": null,
            "speaker_filter": "Tucker"
        },
        {
            "id": "sg3",
            "description": "Analyze Tucker's collaboration patterns for perspective integration",
            "indicators": ["building on others' ideas", "acknowledging different views"],
            "primary_representation": "collaboration",
            "secondary_representations": [],
            "session_filter": null,
            "speaker_filter": "Tucker"
        },
        {
            "id": "sg4",
            "description": "Trace reasoning paths in Tucker's concept contributions",
            "indicators": ["causal chains", "feedback loops", "multi-step reasoning"],
            "primary_representation": "concept_map",
            "secondary_representations": [],
            "session_filter": null,
            "speaker_filter": "Tucker"
        }
    ]
}
```

## IMPORTANT: Generating Efficient Sub-Goals

Generate **2-3 focused sub-goals** for most queries. Only generate 4+ sub-goals for queries with **multiple abstract constructs** that require extensive operationalization.

**Standard queries (2-3 sub-goals):**
1. **Primary sub-goal** - Transcript evidence (always first - primary source)
2. **Secondary sub-goal** - Most relevant supporting representation (concept_map OR collaboration)
3. **Optional** - Only if query explicitly requires another perspective

Example for "How well did participants collaborate in session 20?":
```json
{
    "sub_goals": [
        {"id": "sg1", "description": "Find transcript evidence of collaborative behaviors", "primary_representation": "transcript", "indicators": ["building on ideas", "supportive responses", "turn-taking"], "secondary_representations": ["collaboration"]},
        {"id": "sg2", "description": "Get 7C collaboration scores", "primary_representation": "collaboration", "indicators": ["all 7 dimensions", "overall score"]}
    ]
}
```

**Complex abstract queries (4+ sub-goals)** - Only when query contains multiple constructs like "systems thinking" AND "critical thinking" that each need separate operationalization.

Key principle: Prefer DEPTH over BREADTH. A thorough transcript search with one supporting representation beats superficial coverage of many representations."""

DECOMPOSITION_USER_TEMPLATE = """Query: {query}

{context_section}

Analyze this query and decompose it into targeted sub-goals. Consider:
1. What abstract constructs need operationalization?
2. What specific indicators would provide evidence?
3. Which representations are most relevant for each indicator?

Return the JSON decomposition."""


def decompose_query(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Decompose a query into operational sub-goals.

    PRAS Stage 1: Query Understanding & Decomposition

    Args:
        state: Current agent state with query

    Returns:
        State updates with decomposition results
    """
    query = state.get('current_query', state.get('original_query', ''))

    logger.info(f"[PRAS Stage 1] Decomposing query: '{query}'")

    # === CHECK FOR USER STEERING (must happen before fast path check) ===
    # Check BOTH API parameters AND natural language patterns

    # API steering (from request parameters)
    api_preferred = state.get('preferred_representations', [])
    api_exclude = state.get('exclude_representations', [])
    api_mode = state.get('analysis_mode')
    has_api_steering = bool(api_preferred or api_exclude or api_mode)

    # Natural language steering (from query text)
    nl_steering = _extract_steering_directives(query)
    nl_preferred = nl_steering.get('preferred_representations', [])
    nl_exclude = nl_steering.get('exclude_representations', [])
    nl_mode = nl_steering.get('analysis_mode')
    has_nl_steering = bool(nl_preferred or nl_exclude or nl_mode)

    # Combined check - either source triggers steering
    has_user_steering = has_api_steering or has_nl_steering

    if has_user_steering:
        logger.info(f"[PRAS Stage 1] USER STEERING detected")
        if has_api_steering:
            logger.info(f"  - API: prefer={api_preferred}, exclude={api_exclude}, mode={api_mode}")
        if has_nl_steering:
            logger.info(f"  - NL:  prefer={nl_preferred}, exclude={nl_exclude}, mode={nl_mode}")

    # === PRE-LLM SHORT-CIRCUIT for truly simple queries ===
    # This avoids the expensive LLM call for simple listing/overview queries
    # BUT: Skip fast path if user provided ANY steering - they want control over representations
    fast_tool, fast_args = _determine_fast_path_tool(query, state)
    if fast_tool and not has_user_steering:
        logger.info(f"[PRAS Stage 1] FAST PATH detected: {fast_tool} - skipping LLM decomposition")
        return {
            'route': 'fast_path',
            'fast_path_tool': fast_tool,
            'fast_path_args': fast_args,
            'abstract_constructs': [],
            'sub_goals': [],
            'reasoning_trace': [f"Query classified as simple: fast_path to {fast_tool}"]
        }
    elif fast_tool and has_user_steering:
        logger.info(f"[PRAS Stage 1] Fast path would be {fast_tool}, but using PRAS due to user steering")

    # Detect comparison queries (for context, but let LLM handle decomposition)
    is_comparison = _is_comparison_query(query)
    compared_sessions = state.get('compared_sessions', [])

    if is_comparison:
        logger.info(f"[PRAS Stage 1] COMPARISON QUERY detected")
        logger.info(f"  - Compared sessions: {compared_sessions}")

    # Detect hypothesis queries for co-discovery
    is_hypothesis = _is_hypothesis_query(query)
    extracted_hypothesis = None

    if is_hypothesis:
        extracted_hypothesis = _extract_hypothesis(query)
        logger.info(f"[PRAS Stage 1] HYPOTHESIS QUERY detected")
        logger.info(f"  - Extracted hypothesis: '{extracted_hypothesis[:80]}...'" if len(extracted_hypothesis) > 80 else f"  - Extracted hypothesis: '{extracted_hypothesis}'")

    # Merge steering: API takes precedence over NL (already extracted above)
    preferred_reps = api_preferred if api_preferred else nl_preferred
    exclude_reps = api_exclude if api_exclude else nl_exclude
    analysis_mode = api_mode if api_mode else nl_mode

    # Build context section for LLM
    context_parts = []
    if state.get('current_session_focus'):
        context_parts.append(f"Current session focus: Session {state['current_session_focus']}")
    if state.get('current_speaker_focus'):
        context_parts.append(f"Current speaker focus: {state['current_speaker_focus']}")
    if state.get('compared_sessions'):
        context_parts.append(f"Sessions being compared: {state['compared_sessions']}")

    context_section = ""
    if context_parts:
        context_section = "Context:\n" + "\n".join(f"- {c}" for c in context_parts)

    # Get LLM client - use reasoning model (GPT-4o) for decomposition
    # Quality of decomposition determines overall answer quality
    llm = get_reasoning_client()

    # Call LLM for decomposition
    user_prompt = DECOMPOSITION_USER_TEMPLATE.format(
        query=query,
        context_section=context_section
    )

    try:
        result = llm.json_chat(
            system=DECOMPOSITION_SYSTEM_PROMPT,
            user=user_prompt,
            temperature=0.3,  # Higher temp for more thoughtful decomposition
            max_tokens=2000   # More tokens for complex decompositions
        )

        if not result:
            logger.warning("LLM returned invalid JSON, using fallback decomposition")
            result = _fallback_decomposition(query)

    except Exception as e:
        logger.error(f"Error in query decomposition: {e}")
        result = _fallback_decomposition(query)

    # Process result
    is_simple = result.get('is_simple_query', False)
    abstract_constructs = result.get('abstract_constructs', [])
    operationalization = result.get('operationalization', {})
    raw_sub_goals = result.get('sub_goals', [])

    # Convert to SubGoal typed dicts with explicit filters
    sub_goals: List[SubGoal] = []
    for i, sg in enumerate(raw_sub_goals):
        sub_goals.append(SubGoal(
            id=sg.get('id', f'sg{i+1}'),
            description=sg.get('description', ''),
            indicators=sg.get('indicators', []),
            primary_representation=sg.get('primary_representation', 'transcript'),
            secondary_representations=sg.get('secondary_representations', []),
            # Use explicit filters from LLM, fall back to state context
            session_filter=sg.get('session_filter') or state.get('current_session_focus'),
            speaker_filter=sg.get('speaker_filter') or state.get('current_speaker_focus'),
            satisfied=False,
            evidence=[]
        ))

    # === HYPOTHESIS QUERY HANDLING (Co-Discovery) ===
    # If this is a hypothesis query, add a special sub-goal for hypothesis testing
    # This ensures the test_hypothesis tool is used for systematic verification
    if is_hypothesis and extracted_hypothesis:
        # Determine which sessions to test (from context or all)
        session_filter = state.get('current_session_focus')
        sessions_to_test = [session_filter] if session_filter else None

        hypothesis_subgoal = SubGoal(
            id="sg_hypothesis",
            description=f"Test hypothesis: {extracted_hypothesis}",
            indicators=["supporting evidence", "contradicting evidence", "confidence level"],
            primary_representation="hypothesis",  # Special marker for hypothesis testing
            secondary_representations=["transcript", "concept_map", "collaboration"],
            session_filter=session_filter,
            speaker_filter=state.get('current_speaker_focus'),
            satisfied=False,
            evidence=[],
            # Special field to mark this as a hypothesis sub-goal
            _hypothesis=extracted_hypothesis,
            _sessions_to_test=sessions_to_test
        )

        # Insert hypothesis sub-goal at the beginning
        sub_goals.insert(0, hypothesis_subgoal)
        logger.info(f"[PRAS Stage 1] Added hypothesis testing sub-goal: sg_hypothesis")

    # Determine whether to use PRAS (complex) or fast path (simple)
    use_pras = not is_simple and len(sub_goals) > 0

    logger.info(f"[PRAS Stage 1] Decomposition complete:")
    logger.info(f"  - Simple query: {is_simple}")
    logger.info(f"  - Abstract constructs: {abstract_constructs}")
    logger.info(f"  - Sub-goals: {len(sub_goals)}")
    logger.info(f"  - Using PRAS: {use_pras}")

    # Build state updates
    updates = {
        'abstract_constructs': abstract_constructs,
        'operationalization': operationalization,
        'sub_goals': sub_goals,
        'current_subgoal_index': 0,
        'use_pras': use_pras,
        'is_comparison': is_comparison,
        'compared_sessions': compared_sessions,
        'pras_stage': 'decompose' if use_pras else None,
        # Hypothesis-driven inquiry support
        'is_hypothesis': is_hypothesis,
        'extracted_hypothesis': extracted_hypothesis,
        # User steering preferences (Co-Discovery)
        'preferred_representations': preferred_reps,
        'analysis_mode': analysis_mode,
        'exclude_representations': exclude_reps,
        'thought_history': state.get('thought_history', []) + [
            f"Query decomposition: identified {len(abstract_constructs)} abstract constructs, "
            f"generated {len(sub_goals)} sub-goals" +
            (f", comparison query with sessions {compared_sessions}" if is_comparison else "") +
            (f", hypothesis query: '{extracted_hypothesis[:50]}...'" if is_hypothesis and extracted_hypothesis else "") +
            (f", user steering: prefer {preferred_reps}" if preferred_reps else "") +
            (f", mode: {analysis_mode}" if analysis_mode else "")
        ]
    }

    # Determine route based on query type
    # IMPORTANT: If user provided ANY steering (API or NL), always use PRAS to respect their preferences
    if is_simple and not has_user_steering:
        # Try fast path for truly simple queries (only if no user steering)
        fast_tool, fast_args = _determine_fast_path_tool(query, state)
        if fast_tool:
            updates['route'] = 'fast_path'
            updates['fast_path_tool'] = fast_tool
            updates['fast_path_args'] = fast_args
        else:
            # No fast path match - route to PRAS
            # The LLM should have generated sub-goals if needed
            updates['route'] = 'pras'
            updates['use_pras'] = True
            if not sub_goals:
                logger.warning(f"Simple query with no fast_path and no sub-goals: '{query}'")
    else:
        # Complex query OR user provided steering - use PRAS
        updates['route'] = 'pras'
        updates['use_pras'] = True
        if has_user_steering:
            logger.info(f"[PRAS Stage 1] Using PRAS route due to user steering")

        # === FALLBACK SUB-GOAL FOR STEERING WITHOUT SUB-GOALS ===
        # When user provides steering but LLM generated no sub-goals (simple query),
        # create a fallback sub-goal using the user's preferred representations
        if has_user_steering and not sub_goals:
            logger.info(f"[PRAS Stage 1] Creating fallback sub-goal for user steering")

            # Use user's preferred representation or default to transcript
            primary_rep = preferred_reps[0] if preferred_reps else 'transcript'
            fallback_secondary = preferred_reps[1:] if len(preferred_reps) > 1 else []

            # Add transcript as secondary if not already primary or excluded
            if primary_rep != 'transcript' and 'transcript' not in exclude_reps:
                if 'transcript' not in fallback_secondary:
                    fallback_secondary.append('transcript')

            session_filter = state.get('current_session_focus')

            fallback_subgoal = SubGoal(
                id="sg_fallback_steering",
                description=f"Analyze using {primary_rep}: {query}",
                indicators=["relevant content", "key insights"],
                primary_representation=primary_rep,
                secondary_representations=fallback_secondary,
                session_filter=session_filter,
                speaker_filter=state.get('current_speaker_focus'),
                satisfied=False,
                evidence=[]
            )
            sub_goals.append(fallback_subgoal)
            updates['sub_goals'] = sub_goals
            logger.info(f"[PRAS Stage 1] Created fallback sub-goal with primary={primary_rep}, secondary={fallback_secondary}")

    # Validate transcript-first principle for content queries
    updates['sub_goals'] = _ensure_transcript_subgoal(
        updates.get('sub_goals', []),
        query,
        state
    )

    # Ensure 7C analysis for engagement/collaboration queries
    updates['sub_goals'] = _ensure_collaboration_subgoal(
        updates.get('sub_goals', []),
        query,
        state
    )

    return updates


def _ensure_transcript_subgoal(
    sub_goals: List[SubGoal],
    query: str,
    state: Dict[str, Any]
) -> List[SubGoal]:
    """
    Ensure at least one sub-goal has transcript as primary representation.

    This enforces the principle that transcripts are foundational evidence
    and other representations enhance but don't replace them.
    """
    if not sub_goals:
        return sub_goals

    # Check if any sub-goal already has transcript as primary
    has_transcript_primary = any(
        sg.get('primary_representation') == 'transcript'
        for sg in sub_goals
    )

    if has_transcript_primary:
        return sub_goals

    # For content queries, add transcript to the first sub-goal's secondary
    # or create a new transcript sub-goal
    content_indicators = [
        r'\bsaid\b', r'\bsay\b', r'\bquote', r'\bspeak',
        r'\bmentioned\b', r'\bstated\b', r'\bdiscussed\b',
        r'\btalked\b', r'\bexpress', r'\bcomment',
        r'\bwhat did\b', r'\bhow did\b', r'\bdid \w+ demonstrate',
        r'\bcompare\b', r'\banalyze\b', r'\bevaluate\b'
    ]

    import re
    query_lower = query.lower()
    is_content_query = any(
        re.search(pattern, query_lower) for pattern in content_indicators
    )

    if not is_content_query:
        return sub_goals

    # Upgrade first sub-goal to use transcript as primary
    # Move current primary to secondary
    logger.info("[PRAS Stage 1] Enforcing transcript-first: upgrading first sub-goal")
    first_sg = sub_goals[0]
    current_primary = first_sg.get('primary_representation', '')

    if current_primary and current_primary != 'transcript':
        current_secondary = first_sg.get('secondary_representations', [])
        if current_primary not in current_secondary:
            current_secondary = [current_primary] + current_secondary
        first_sg['secondary_representations'] = current_secondary

    first_sg['primary_representation'] = 'transcript'
    sub_goals[0] = first_sg

    return sub_goals


def _ensure_collaboration_subgoal(
    sub_goals: List[SubGoal],
    query: str,
    state: Dict[str, Any]
) -> List[SubGoal]:
    """
    Ensure 7C collaboration analysis is included for engagement/quality queries.

    For queries about engagement, collaboration, participation, or quality,
    we MUST include 7C analysis to provide quantitative metrics.
    Without 7C scores, claims about "higher engagement" are unsubstantiated.
    """
    import re

    if not sub_goals:
        return sub_goals

    # Check if query requires 7C analysis
    collaboration_indicators = [
        r'\bengagement\b',
        r'\bcollaboration\b',
        r'\bparticipation\b',
        r'\bproductive\b',
        r'\bquality\b',
        r'\binteraction\b',
        r'\bcontribution\b',
        r'\b7c\b',
        r'\bbetter\s+(?:discussion|session|discourse)\b',
        r'\bhigher\s+engagement\b',
        r'\bmore\s+productive\b',
        r'\bcompare.*(?:session|collaboration)\b',
        r'\bwhich\s+session\b.*\b(?:better|best|worse|worst)\b',
    ]

    query_lower = query.lower()
    needs_collaboration = any(
        re.search(pattern, query_lower) for pattern in collaboration_indicators
    )

    if not needs_collaboration:
        return sub_goals

    # Check if any sub-goal already has collaboration as primary or secondary
    has_collaboration = any(
        sg.get('primary_representation') == 'collaboration' or
        'collaboration' in sg.get('secondary_representations', [])
        for sg in sub_goals
    )

    if has_collaboration:
        logger.info("[PRAS Stage 1] Collaboration already included in sub-goals")
        return sub_goals

    # Add collaboration sub-goal for 7C analysis
    logger.info("[PRAS Stage 1] ENFORCING 7C: Adding collaboration sub-goal for engagement query")

    collaboration_subgoal = SubGoal(
        id="sg_7c_analysis",
        description="Get 7C collaboration scores to assess engagement and quality",
        indicators=["7C scores", "overall collaboration score", "strengths", "weaknesses"],
        primary_representation="collaboration",
        secondary_representations=[],
        session_filter=state.get('current_session_focus'),
        speaker_filter=None,
        satisfied=False,
        evidence=[]
    )

    # Insert at the beginning so 7C analysis comes first
    sub_goals.insert(0, collaboration_subgoal)

    return sub_goals


def _determine_fast_path_tool(query: str, state: Dict[str, Any]) -> tuple:
    """
    Determine which tool to use for fast path execution.

    Returns:
        Tuple of (tool_name, tool_args) or (None, None) if no match
    """
    import re

    query_lower = query.lower()

    # Pattern-based tool selection
    # Check collaboration analysis first (more specific)
    collab_patterns = [
        r'(?:collaboration|7c)\s*(?:score|analysis).+session\s*(\d+)',
        r'session\s*(\d+).+(?:collaboration|7c)\s*(?:score|analysis)',
        r'(?:how well|quality).+(?:collaborat).+session\s*(\d+)',
    ]
    for pattern in collab_patterns:
        match = re.search(pattern, query_lower, re.IGNORECASE)
        if match:
            session_id = int(match.group(1))
            return ('get_collaboration_analysis', {'session_id': session_id})

    # Check list sessions (including "recently" patterns)
    list_patterns = [
        r'(?:what|which|list|show).*sessions?\s*(?:are|do|available|exist)',
        r'(?:list|show)\s+(?:all\s+)?(?:the\s+)?sessions?$',  # "List sessions", "List all sessions", "List all the sessions"
        r'(?:how many|all)\s*sessions?',
        r'(?:available|existing)\s*sessions?',
        r'(?:what|tell me).*(?:discussed|happened)\s*recently',  # "What was discussed recently?"
        r'recent\s+(?:discussions?|sessions?)',  # "Recent discussions"
        r'(?:what|show|list).*recent',  # "What's recent", "Show recent"
    ]
    for pattern in list_patterns:
        if re.search(pattern, query_lower, re.IGNORECASE):
            return ('list_sessions', {})

    # Check session overview (most generic - last)
    # BUT exclude queries that ask about what was SAID (those need transcript search)

    # First, check if query is asking about PARTICIPANTS (speakers/who participated)
    # These are metadata queries, NOT transcript queries
    participant_patterns = [
        r'\bwho\s+(?:were|are|was)\s+(?:the\s+)?speakers?\b',
        r'\bwho\s+(?:participated|spoke|was\s+in)\b',
        r'\blist\s+(?:the\s+)?(?:speakers|participants)\b',
        r'\b(?:speakers|participants)\s+(?:in|of)\b',
    ]
    session_id = state.get('current_session_focus')
    for pattern in participant_patterns:
        if re.search(pattern, query_lower, re.IGNORECASE) and session_id:
            return ('get_session_overview', {'session_id': session_id})

    # EXCLUSIONS: Complex queries that need PRAS reasoning, not fast path

    # 1. Hypothesis patterns - need test_hypothesis tool and PRAS path
    for pattern in HYPOTHESIS_PATTERNS:
        if re.search(pattern, query_lower, re.IGNORECASE):
            logger.debug(f"Fast path excluded: hypothesis pattern detected")
            return (None, None)  # Let PRAS handle hypothesis testing

    # 2. Comparison patterns - need compare_sessions and multi-session analysis
    for pattern in COMPARISON_PATTERNS:
        if re.search(pattern, query_lower, re.IGNORECASE):
            logger.debug(f"Fast path excluded: comparison pattern detected")
            return (None, None)  # Let PRAS handle comparisons

    # 3. Complex analytical constructs - need multi-representation analysis
    complex_construct_patterns = [
        r'\bsystems?\s*thinking\b',
        r'\bcritical\s*thinking\b',
        r'\bcreativity\b',
        r'\binnovation\b',
        r'\breasoning\b',
        r'\bargument(?:ation)?\b',
        r'\bdemonstrate(?:s|d)?\b',
        r'\banalyz(?:e|ing)\b',
        r'\beverify\b',
        r'\beveridence\b',
        r'\bpatterns?\b',
        r'\bhow\s+(?:are|do)\s+(?:ideas?|concepts?)\s+connect',
        r'\bconnected\b',
    ]
    for pattern in complex_construct_patterns:
        if re.search(pattern, query_lower, re.IGNORECASE):
            logger.debug(f"Fast path excluded: complex construct detected")
            return (None, None)  # Let PRAS handle complex analysis

    # 4. Transcript indicators - need search, not overview
    transcript_indicators = [
        r'\bsaid\b',
        r'\bsay\b',
        r'\bquote',
        r'\bspeak(?:s|ing)\b',  # "speaks", "speaking" but NOT "speakers"
        r'\bstatement',
        r'\bmentioned\b',
        r'\bword(?:s|ed|ing)',
        r'\btold\b',
        r'\bexpress(?:ed|ing)',
        r'\bcomment(?:s|ed)',
    ]

    # If query has transcript indicators, don't use fast path - use reasoning
    for pattern in transcript_indicators:
        if re.search(pattern, query_lower, re.IGNORECASE):
            return (None, None)  # Let reasoning handle it

    # 5. Collaboration/engagement keywords - need 7C analysis via PRAS
    # These require full reasoning with get_7c_analysis, not just session overview
    collaboration_keywords = [
        'collaboration', 'collaborate', 'collaborative',
        'engagement', 'engaged', 'engaging',
        'participation', 'interact', 'interaction',
        '7c', 'seven c', 'communication quality',
        'contribution', 'climate', 'conflict',
        'constructive', 'context', 'compatibility'
    ]
    for keyword in collaboration_keywords:
        if keyword in query_lower:
            logger.info(f"Fast path excluded: collaboration keyword '{keyword}' detected")
            return (None, None)  # Let PRAS handle with 7C analysis

    overview_patterns = [
        r'(?:what|tell me|describe).+(?:session|discussion)\s*(\d+)',
        r'(?:about|overview of)\s*(?:session|discussion)\s*(\d+)',
        r'session\s*(\d+)\s*(?:about|overview|summary)',
        r'(?:what was|what were).+(?:discussed|talked about).+(?:session|discussion)\s*(\d+)',
        r'(?:session|discussion)\s*(\d+).+(?:discuss|talk|about)',
    ]
    for pattern in overview_patterns:
        match = re.search(pattern, query_lower, re.IGNORECASE)
        if match:
            session_id = int(match.group(1))
            return ('get_session_overview', {'session_id': session_id})

    # Check for session context from state
    if state.get('current_session_focus'):
        session_id = state['current_session_focus']
        # If query is asking about "it" or "the session" without a number
        if re.search(r'\b(it|this|the session|that session)\b', query_lower):
            return ('get_session_overview', {'session_id': session_id})

        # If query is a general "tell me about" / "what is" with a session name resolved
        # This handles cases like "Tell me about the Nuclear Fusion session"
        # where input_processor already resolved the session name to an ID
        general_overview_patterns = [
            r'^tell me about\b',
            r'^what (is|was|happened|were)',
            r'^describe\b',
            r'^explain\b',
            r'^give me (an )?overview',
            r'\b(about|overview of)\b.*session\b',
        ]
        for pattern in general_overview_patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return ('get_session_overview', {'session_id': session_id})

    return (None, None)


def _fallback_decomposition(query: str) -> Dict[str, Any]:
    """
    Fallback decomposition when LLM fails.

    Uses heuristics to determine if query is simple or complex.
    """
    query_lower = query.lower()

    # Check for known abstract constructs
    found_constructs = []
    for construct in CONSTRUCT_OPERATIONALIZATIONS:
        if construct in query_lower:
            found_constructs.append(construct)

    # Simple query patterns
    simple_patterns = [
        'what sessions',
        'list sessions',
        'show sessions',
        'tell me about session',
        'what happened in',
        'what did .* say about',
        'how many',
        'who participated'
    ]

    import re
    is_simple = any(re.search(pattern, query_lower) for pattern in simple_patterns)
    is_simple = is_simple and len(found_constructs) == 0

    if is_simple:
        return {
            'is_simple_query': True,
            'abstract_constructs': [],
            'operationalization': {},
            'sub_goals': []
        }

    # Build operationalization from known constructs
    operationalization = {}
    for construct in found_constructs:
        if construct in CONSTRUCT_OPERATIONALIZATIONS:
            operationalization[construct] = CONSTRUCT_OPERATIONALIZATIONS[construct]

    # Generate comprehensive sub-goals (4-6 for analytical queries)
    sub_goals = []

    # If we have constructs, create sub-goals covering multiple representations
    if found_constructs:
        # Always start with transcript evidence
        sub_goals.append({
            'id': 'sg1',
            'description': f'Find transcript evidence of {", ".join(found_constructs)}',
            'indicators': ['key statements', 'relevant quotes', 'language patterns'],
            'primary_representation': 'transcript',
            'secondary_representations': []
        })

        # Add concept map sub-goal
        sub_goals.append({
            'id': 'sg2',
            'description': f'Find concept structure related to {found_constructs[0]}',
            'indicators': ['related concepts', 'causal relationships', 'idea connections'],
            'primary_representation': 'concept_map',
            'secondary_representations': []
        })

        # Add collaboration sub-goal if relevant
        collab_constructs = ['collaboration', 'engagement', 'participation', 'interaction']
        if any(c in query_lower for c in collab_constructs):
            sub_goals.append({
                'id': 'sg3',
                'description': 'Get 7C collaboration metrics',
                'indicators': ['dimension scores', 'collaboration quality'],
                'primary_representation': 'collaboration',
                'secondary_representations': []
            })

        # Add construct-specific sub-goals
        for i, construct in enumerate(found_constructs):
            indicators = operationalization.get(construct, [])[:3]
            sub_goals.append({
                'id': f'sg{len(sub_goals)+1}',
                'description': f'Find specific evidence of {construct}',
                'indicators': indicators,
                'primary_representation': 'concept_map' if 'thinking' in construct else 'transcript',
                'secondary_representations': ['transcript'] if 'thinking' in construct else []
            })
    else:
        # Comprehensive sub-goals for unrecognized complex queries
        sub_goals = [
            {
                'id': 'sg1',
                'description': 'Find relevant transcript evidence',
                'indicators': ['key statements', 'relevant quotes'],
                'primary_representation': 'transcript',
                'secondary_representations': []
            },
            {
                'id': 'sg2',
                'description': 'Find conceptual structure',
                'indicators': ['related concepts', 'relationships'],
                'primary_representation': 'concept_map',
                'secondary_representations': []
            },
            {
                'id': 'sg3',
                'description': 'Get collaboration context',
                'indicators': ['interaction patterns', '7C scores'],
                'primary_representation': 'collaboration',
                'secondary_representations': []
            },
            {
                'id': 'sg4',
                'description': 'Check speaker contributions',
                'indicators': ['participation', 'key contributors'],
                'primary_representation': 'speaker_profile',
                'secondary_representations': ['transcript']
            }
        ]

    return {
        'is_simple_query': False,
        'abstract_constructs': found_constructs,
        'operationalization': operationalization,
        'sub_goals': sub_goals
    }


def should_use_pras(state: Dict[str, Any]) -> str:
    """
    Conditional edge function: determine next node based on query complexity.

    Returns:
        "pras" for complex queries needing full PRAS flow
        "fast" for simple queries that can use legacy ReAct
    """
    if state.get('use_pras', False):
        return "pras"
    return "fast"
