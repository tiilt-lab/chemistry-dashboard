"""
Query Router Node for BLINC Agent V3

Lightweight classification to route queries based on complexity:
- Simple queries → Direct tool execution (fast path)
- Moderate queries → ReAct reasoning loop
- Analytical queries → Plan-then-execute (parallel sub-queries)

Inspired by Agent Skills progressive disclosure - only invoke full
reasoning when complexity warrants it.
"""

import logging
import re
from typing import Dict, Any, Optional, Tuple

from openai import OpenAI

logger = logging.getLogger(__name__)

# NOTE: plan_and_execute and diagnostic_reasoning imports removed (paths disabled)

# Pattern-based fast routing (no LLM call needed)
DIRECT_PATTERNS = {
    'session_overview': [
        r'(?:what|tell me|describe).+(?:session|discussion)\s*(\d+)',
        r'(?:about|overview of)\s*(?:session|discussion)\s*(\d+)',
        r'session\s*(\d+)\s*(?:about|overview|summary)',
    ],
    'list_sessions': [
        r'(?:what|which|list|show).*sessions?\s*(?:are|do|available|exist)',
        r'(?:list|show)\s+(?:all\s+)?(?:the\s+)?sessions?$',  # "List sessions", "List all sessions", "List all the sessions"
        r'(?:how many|all)\s*sessions?',
        r'(?:available|existing)\s*sessions?',
        r'^sessions?\s*(?:list|available)',  # "Sessions list", "Sessions available"
        r'(?:what|tell me).*(?:discussed|happened)\s*recently',  # "What was discussed recently?"
        r'recent\s+(?:discussions?|sessions?)',  # "Recent discussions"
        r'(?:what|show|list).*recent',  # "What's recent", "Show recent"
    ],
    'collaboration_score': [
        r'(?:collaboration|7c)\s*(?:score|analysis).+session\s*(\d+)',
        r'session\s*(\d+).+(?:collaboration|7c)\s*(?:score|analysis)',
        r'(?:how well|quality).+(?:collaborat).+session\s*(\d+)',
    ],
}

# Complexity indicators that require full reasoning
COMPLEXITY_INDICATORS = [
    r'\b(?:compare|comparison|versus|vs\.?|difference|between)\b',
    r'\b(?:best|worst|highest|lowest|most|least)\b',
    r'\b(?:all|every|each)\s+sessions?\b',
    r'\b(?:across|throughout|multiple)\b',
    r'\b(?:why|how come|reason|explain why)\b',
    r'\b(?:trend|pattern|change|evolution)\b',
    r'\b(?:relationship|connection|link|related)\b',
]


def route_query(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Route query based on complexity.

    Simple queries → direct tool execution (fast path)
    Analytical queries → plan-then-execute (parallel sub-queries)
    Complex queries → full reasoning loop (slow path)

    Args:
        state: Current agent state with original_query

    Returns:
        Updated state with routing decision
    """
    query = state.get('original_query', '').strip()
    query_lower = query.lower()

    logger.info(f"Routing query: '{query}'")

    # =========================================================================
    # CONSERVATIVE ROUTING - Let the flexible reasoning path handle most queries
    #
    # The original V3 was faster and smarter because it used GPT-4o to reason
    # about ALL queries and pick the right tools. The specialized paths
    # (diagnostic, plan) add overhead and often fail.
    #
    # Only use fast_path for truly trivial queries like "list sessions".
    # Everything else goes to the flexible reasoning path.
    # =========================================================================

    # Try pattern-based fast routing for TRULY SIMPLE queries only
    fast_route = _try_pattern_routing(query_lower)
    if fast_route:
        tool_name, tool_args = fast_route
        logger.info(f"Query classified as SIMPLE - fast path to {tool_name}")
        return {
            'route': 'fast_path',
            'fast_path_tool': tool_name,
            'fast_path_args': tool_args
        }

    # DISABLED: Diagnostic path - hypothesis generation often fails to gather evidence
    # Let the flexible reasoning path handle "why" questions instead
    # if is_diagnostic_query(query):
    #     logger.info("Query classified as DIAGNOSTIC - using hypothesis-evidence path")
    #     return {'route': 'diagnostic', ...}

    # DISABLED: Analytical/plan path - adds overhead without clear benefit
    # The reasoning path with GPT-4o handles these well
    # if is_analytical_query(query):
    #     logger.info("Query classified as ANALYTICAL - using plan-execute path")
    #     return {'route': 'plan', ...}

    # Default: Use flexible reasoning path - GPT-4o picks the right tools
    # This is the original V3 behavior that worked well
    logger.info("Using flexible reasoning path (GPT-4o will select tools)")
    return {
        'route': 'reasoning',
        'fast_path_tool': None,
        'fast_path_args': None
    }


def _is_complex_query(query: str) -> bool:
    """Check if query has complexity indicators."""
    for pattern in COMPLEXITY_INDICATORS:
        if re.search(pattern, query, re.IGNORECASE):
            return True
    return False


def _try_pattern_routing(query: str) -> Optional[Tuple[str, Dict]]:
    """
    Try to route query using patterns.

    Priority order matters! More specific patterns checked first.

    Returns:
        Tuple of (tool_name, tool_args) if matched, None otherwise
    """
    # CRITICAL: Keywords that should NEVER use fast path
    # These require full reasoning with 7C analysis
    reasoning_required_keywords = [
        'collaboration', 'collaborate', 'collaborative',
        'engagement', 'engaged', 'engaging',
        'participation', 'interact', 'interaction',
        '7c', 'seven c', 'communication quality',
        'contribution', 'climate', 'conflict',
        'constructive', 'context', 'compatibility'
    ]

    query_lower = query.lower()
    for keyword in reasoning_required_keywords:
        if keyword in query_lower:
            logger.info(f"Query contains '{keyword}' - routing to reasoning path (not fast path)")
            return None  # Force reasoning path

    # Check collaboration score FIRST (more specific than session overview)
    for pattern in DIRECT_PATTERNS['collaboration_score']:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            session_id = int(match.group(1))
            return ('get_collaboration_analysis', {'session_id': session_id})

    # Check list sessions patterns
    for pattern in DIRECT_PATTERNS['list_sessions']:
        if re.search(pattern, query, re.IGNORECASE):
            return ('list_sessions', {})

    # Check session overview patterns LAST (most generic)
    for pattern in DIRECT_PATTERNS['session_overview']:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            session_id = int(match.group(1))
            return ('get_session_overview', {'session_id': session_id})

    return None


def execute_fast_path(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the fast path tool directly.

    This bypasses the reasoning loop for simple queries.
    """
    tool_name = state.get('fast_path_tool')
    tool_args = state.get('fast_path_args', {})

    logger.info(f"Executing fast path: {tool_name}({tool_args})")

    try:
        # Import and execute the tool
        if tool_name == 'get_session_overview':
            from ..tools.analysis_tools import get_session_overview
            result = get_session_overview(**tool_args)

            # ENHANCEMENT: Add transcript grounding for depth
            # Fetch 3-5 key transcript quotes to enrich the overview
            session_id = tool_args.get('session_id')
            if session_id:
                transcript_quotes = _get_key_transcript_quotes(session_id, limit=5)
                if transcript_quotes:
                    result['key_quotes'] = transcript_quotes
                    logger.info(f"Added {len(transcript_quotes)} transcript quotes to fast path")

            return {
                'retrieval_results': [result],
                'tools_used': [tool_name, 'transcript_quotes'],
                'next_action': 'synthesize'
            }

        elif tool_name == 'get_collaboration_analysis':
            from ..tools.analysis_tools import get_collaboration_analysis
            result = get_collaboration_analysis(**tool_args)
        elif tool_name == 'list_sessions':
            result = _list_all_sessions()
        else:
            logger.warning(f"Unknown fast path tool: {tool_name}")
            return {'route': 'reasoning'}  # Fallback to reasoning

        # Store result for synthesis
        return {
            'retrieval_results': [result],
            'tools_used': [tool_name],
            'next_action': 'synthesize'
        }

    except Exception as e:
        logger.error(f"Fast path error: {e}")
        # Fallback to reasoning on error
        return {'route': 'reasoning'}


def _list_all_sessions() -> Dict[str, Any]:
    """List all available sessions from the database."""
    import mysql.connector

    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='vagrant',
            password='vagrant',
            database='discussion_capture'
        )
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                sd.id as session_device_id,
                COALESCE(s.name, sd.name) as session_name,
                cs.discourse_type,
                (SELECT COUNT(DISTINCT speaker_id) FROM transcript WHERE session_device_id = sd.id) as speaker_count,
                (SELECT COUNT(*) FROM transcript WHERE session_device_id = sd.id) as transcript_count
            FROM session_device sd
            JOIN session s ON s.id = sd.session_id
            LEFT JOIN concept_session cs ON cs.session_device_id = sd.id
            ORDER BY sd.id
        """)

        sessions = cursor.fetchall()
        cursor.close()
        connection.close()

        return {
            'tool_name': 'list_sessions',
            'result_count': len(sessions),
            'results': sessions,
            'is_relevant': True
        }

    except Exception as e:
        logger.error(f"List sessions error: {e}")
        return {
            'tool_name': 'list_sessions',
            'error': str(e),
            'result_count': 0,
            'results': [],
            'is_relevant': False
        }


def _get_key_transcript_quotes(session_id: int, limit: int = 5) -> list:
    """
    Get key transcript quotes for a session to add depth to overview.

    Selects quotes that are:
    - Substantive (longer than 50 chars)
    - Varied across speakers
    - Spread across the discussion

    Returns:
        List of quote dicts with speaker, text, timestamp
    """
    import mysql.connector

    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='vagrant',
            password='vagrant',
            database='discussion_capture'
        )
        cursor = connection.cursor(dictionary=True)

        # Get substantive quotes spread across the session
        # Using a subquery to get varied quotes (not just the first N)
        cursor.execute("""
            SELECT
                t.transcript as text,
                s.alias as speaker,
                t.start_time as timestamp,
                CHAR_LENGTH(t.transcript) as length
            FROM transcript t
            JOIN speaker s ON s.id = t.speaker_id
            WHERE t.session_device_id = %s
                AND CHAR_LENGTH(t.transcript) > 50
            ORDER BY RAND()
            LIMIT %s
        """, (session_id, limit * 2))  # Fetch extra, then select best

        all_quotes = cursor.fetchall()
        cursor.close()
        connection.close()

        if not all_quotes:
            return []

        # Sort by timestamp and select spread across session
        all_quotes.sort(key=lambda x: x.get('timestamp', 0))

        # Select quotes spread across the session
        selected = []
        seen_speakers = set()
        step = max(1, len(all_quotes) // limit)

        for i in range(0, len(all_quotes), step):
            if len(selected) >= limit:
                break
            quote = all_quotes[i]
            # Prefer variety in speakers
            if quote['speaker'] not in seen_speakers or len(selected) < limit // 2:
                selected.append({
                    'speaker': quote['speaker'],
                    'text': quote['text'][:200] + '...' if len(quote['text']) > 200 else quote['text'],
                    'timestamp': quote.get('timestamp')
                })
                seen_speakers.add(quote['speaker'])

        logger.info(f"Selected {len(selected)} key quotes from {len(all_quotes)} candidates")
        return selected

    except Exception as e:
        logger.error(f"Error getting transcript quotes: {e}")
        return []
