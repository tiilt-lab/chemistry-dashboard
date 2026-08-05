"""
Input Processor Node for BLINC Agent V3

Preprocesses the query and resolves references from conversation context.
"""

import logging
import re
import time
from typing import Dict, Any, Optional
import mysql.connector

logger = logging.getLogger(__name__)

# Patterns that indicate user is switching away from current context
CONTEXT_SWITCH_PATTERNS = [
    r'\bno\b[,.]?\s*(i\s+)?mean\b',    # "No, I mean..."
    r'\binstead\b',                     # "instead, show me"
    r'\bactually\b.*\bwant\b',          # "actually I want"
    r'\bforget\b.*\b(that|about)\b',    # "forget about that"
    r'\bswitch\b.*\bto\b',              # "switch to"
    r'\bdifferent\s+session\b',         # "different session"
    r'\banother\s+session\b',           # "another session"
]

# Patterns that indicate cross-session exploratory queries
# These should NOT have session_focus applied - they search across ALL sessions
EXPLORATORY_PATTERNS = [
    r'\bfind\s+sessions?\b',            # "Find sessions showing..."
    r'\bfind\s+when\b',                 # "Find when people discussed..." (NEW)
    r'\bwhen\s+(?:did|was|were)\s+(?:people|someone|they)\b',  # "When did people discuss..." (NEW)
    r'\bwhich\s+sessions?\b',           # "Which sessions have..."
    r'\bsessions?\s+(?:with|showing|that|where)\b',  # "Sessions showing X"
    r'\bacross\s+(?:all\s+)?sessions?\b',  # "Across all sessions"
    r'\ball\s+sessions?\b',             # "All sessions"
    r'\blist\s+sessions?\b',            # "List sessions"
    r'\bany\s+sessions?\b',             # "Any sessions with..."
    r'\bevery\s+session\b',             # "Every session"
    r'\bwhat\s+sessions?\b',            # "What sessions..."
    r'\bhow\s+many\s+sessions?\b',      # "How many sessions..."
    r'\btop\s+\d+\s+(?:most\s+)?',      # "Top 3 most collaborative"
    r'\bbest\s+(?:collaboration|communication)\b',  # "Best collaboration"
    r'\bmost\s+(?:collaborative|communicative)\b',  # "Most collaborative sessions"
    r'\bhigh(?:est)?\s+(?:communication|collaboration)\b',  # "High communication quality"
    r'\brecently\b',                    # "What was discussed recently?" (NEW)
    r'\brecent\s+discussion',           # "Recent discussions" (NEW)
    r'\bwhat\s+was\s+discussed\b',      # "What was discussed" without specific session (NEW)
]

# Cache for session patterns (refreshed periodically)
_session_patterns_cache: Dict[str, int] = {}
_session_patterns_cache_time: float = 0
_SESSION_CACHE_TTL = 300  # Refresh every 5 minutes


def _get_db_connection():
    """Get MySQL database connection."""
    return mysql.connector.connect(
        host='localhost',
        user='vagrant',
        password='vagrant',
        database='discussion_capture'
    )


def _load_session_patterns() -> Dict[str, int]:
    """Load session name patterns from database dynamically."""
    global _session_patterns_cache, _session_patterns_cache_time

    # Return cached version if still valid
    if _session_patterns_cache and (time.time() - _session_patterns_cache_time) < _SESSION_CACHE_TTL:
        return _session_patterns_cache

    patterns = {}
    try:
        conn = _get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get all sessions with their names
        cursor.execute("""
            SELECT s.id, s.name, sd.id as session_device_id
            FROM session s
            JOIN session_device sd ON sd.session_id = s.id
            ORDER BY s.id
        """)

        for row in cursor.fetchall():
            session_id = row['session_device_id']  # Use session_device_id for queries
            name = row['name'].lower() if row['name'] else ''

            if name:
                # Add full name
                patterns[name] = session_id

                # Add individual significant words (skip common words)
                skip_words = {'the', 'a', 'an', 'in', 'on', 'at', 'is', 'are', 'was', 'were', 'and', 'or', 'of', 'to', 'for', 'with', 'session', 'interview', 'discussion'}
                words = name.split()
                for word in words:
                    word = word.strip('.,!?')
                    if len(word) > 2 and word not in skip_words:
                        # Only add if not ambiguous (not already mapped to different session)
                        if word not in patterns:
                            patterns[word] = session_id

        cursor.close()
        conn.close()

        # Update cache
        _session_patterns_cache = patterns
        _session_patterns_cache_time = time.time()

        logger.debug(f"Loaded {len(patterns)} session patterns from database")

    except Exception as e:
        logger.error(f"Error loading session patterns: {e}")
        # Return existing cache on error
        if _session_patterns_cache:
            return _session_patterns_cache

    return patterns


def get_session_patterns() -> Dict[str, int]:
    """Get session name to ID mapping (cached, refreshes from DB periodically)."""
    return _load_session_patterns()


def process_input(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process the input query and resolve references.

    This node:
    1. Normalizes the query
    2. Resolves session references ("Dinosaurs session" -> session 23)
    3. Resolves conversational references ("it", "that session", "go back")

    Args:
        state: Current agent state

    Returns:
        Updated state with resolved references
    """
    query = state.get('current_query', state.get('original_query', ''))
    query_lower = query.lower()

    logger.info(f"Processing input: '{query}'")

    updates = {
        'iteration_count': 0
    }

    # === Check for exploratory queries FIRST ===
    # These queries should search across ALL sessions, not be constrained by previous focus
    is_exploratory = is_exploratory_query(query)
    if is_exploratory:
        # Save previous focus for potential "go back" later
        if state.get('current_session_focus'):
            updates['previous_session_focus'] = state['current_session_focus']
        updates['current_session_focus'] = None
        updates['is_exploratory_query'] = True
        logger.info("Exploratory query detected: clearing session focus to search all sessions")

    # === Check for context reset (comparison, topic switch) ===
    elif _should_reset_context(query):
        # Save previous focus for potential "go back" later
        if state.get('current_session_focus'):
            updates['previous_session_focus'] = state['current_session_focus']
        updates['current_session_focus'] = None
        logger.info("Context reset: user switching topics or comparing sessions")

    # === Resolve conversational references ===

    # "Go back" or "previous" -> switch to previous session
    if any(phrase in query_lower for phrase in ['go back', 'previous session', 'earlier session']):
        if state.get('previous_session_focus'):
            updates['current_session_focus'] = state['previous_session_focus']
            updates['previous_session_focus'] = state.get('current_session_focus')
            logger.info(f"Switched to previous session: {updates['current_session_focus']}")

    # "This session" or "it" with no session mentioned -> use current focus
    if any(phrase in query_lower for phrase in ['this session', 'that session', 'the session']):
        if state.get('current_session_focus') and not _mentions_specific_session(query_lower):
            # Keep the current focus, query will use it
            pass

    # === Resolve session name references ===
    # NOTE: Skip single session focus for comparison queries (handled later)

    is_comparison_query = _should_reset_context(query)
    session_id = _resolve_session_name(query_lower)

    if session_id and not is_comparison_query:
        # Update session focus (only for non-comparison queries)
        if state.get('current_session_focus') != session_id:
            updates['previous_session_focus'] = state.get('current_session_focus')
            updates['current_session_focus'] = session_id

        # Add to session history
        history = state.get('session_history', []).copy()
        if session_id not in history:
            history.append(session_id)
        updates['session_history'] = history[-10:]  # Keep last 10

        logger.info(f"Resolved session reference: {session_id}")
    elif session_id and is_comparison_query:
        # For comparison queries, add to history but don't set single focus
        history = state.get('session_history', []).copy()
        if session_id not in history:
            history.append(session_id)
        updates['session_history'] = history[-10:]
        logger.info(f"Session {session_id} found but comparison mode - no single focus")

    # === Resolve speaker references ===

    speaker = _resolve_speaker_name(query_lower)
    if speaker:
        updates['current_speaker_focus'] = speaker
        logger.info(f"Resolved speaker reference: {speaker}")

    # === Detect comparison queries ===

    is_comparison = _should_reset_context(query)  # Comparison is part of context reset
    if is_comparison:
        # Try to find multiple session references
        sessions = _find_all_session_references(query_lower)
        if len(sessions) >= 2:
            updates['compared_sessions'] = sessions[:5]
            # IMPORTANT: Do NOT set single session focus for comparisons
            # The context reset already cleared it - don't restore it
            updates['current_session_focus'] = None
            logger.info(f"Detected comparison: {sessions}, keeping multi-session focus")
        elif len(sessions) == 1:
            # Only one session found but comparison query - find sessions to compare
            # Could be "compare session 20 with the previous one"
            if state.get('previous_session_focus'):
                sessions.append(state['previous_session_focus'])
                updates['compared_sessions'] = sessions
                updates['current_session_focus'] = None
                logger.info(f"Detected comparison with previous: {sessions}")

    return updates


def _mentions_specific_session(query: str) -> bool:
    """Check if query mentions a specific session by name or ID."""
    # Check for session ID pattern
    if re.search(r'session\s*\d+', query):
        return True

    # Check for session names (dynamically loaded from DB)
    session_patterns = get_session_patterns()
    for pattern in session_patterns:
        if pattern in query:
            return True

    return False


def _resolve_session_name(query: str) -> int | None:
    """Resolve session name to session ID."""
    query = query.lower()

    # Check for explicit session ID
    match = re.search(r'session\s*(\d+)', query)
    if match:
        return int(match.group(1))

    # Check for session names (dynamically loaded from DB)
    session_patterns = get_session_patterns()
    for pattern, session_id in session_patterns.items():
        if pattern in query:
            return session_id

    return None


def _find_all_session_references(query: str) -> list:
    """Find all session references in a query (for comparisons)."""
    sessions = []
    query = query.lower()

    # Find explicit IDs
    for match in re.finditer(r'session\s*(\d+)', query):
        sessions.append(int(match.group(1)))

    # Find named sessions (dynamically loaded from DB)
    session_patterns = get_session_patterns()
    for pattern, session_id in session_patterns.items():
        if pattern in query and session_id not in sessions:
            sessions.append(session_id)

    return sessions


def _resolve_speaker_name(query: str) -> str | None:
    """Extract speaker name from query if mentioned."""
    query = query.lower()

    # Common patterns for speaker mentions
    patterns = [
        r"how did (\w+) ",
        r"what did (\w+) say",
        r"(\w+)'s (contribution|participation|style)",
        r"speaker (\w+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, query)
        if match:
            name = match.group(1)
            # Filter out common words that aren't names
            if name not in ['the', 'a', 'this', 'that', 'each', 'every', 'some']:
                return name.title()

    return None


def _should_reset_context(query: str) -> bool:
    """
    Detect if user is explicitly switching away from previous focus.

    Returns True if query contains indicators that user wants to:
    - Switch to a different topic
    - Compare multiple sessions (no single focus)
    - Explicitly redirect the conversation
    """
    query_lower = query.lower()

    # Check explicit switch patterns
    for pattern in CONTEXT_SWITCH_PATTERNS:
        if re.search(pattern, query_lower):
            return True

    # Comparison queries indicate multi-focus (no single session focus)
    comparison_indicators = [
        r'\bcompare\b',
        r'\bcomparison\b',
        r'\bvs\.?\b',
        r'\bversus\b',
        r'\bdifference\s+between\b',
        r'\bcontrast\b',
        r'\bbetween\b.+\band\b',
    ]
    for pattern in comparison_indicators:
        if re.search(pattern, query_lower):
            return True

    return False


def should_reset_context(query: str) -> bool:
    """Public wrapper for context reset detection (used by routes.py)."""
    return _should_reset_context(query) or is_exploratory_query(query)


def is_exploratory_query(query: str) -> bool:
    """
    Detect if query is an exploratory cross-session query.

    These queries should NOT have session_focus applied because they
    explicitly ask to search across multiple/all sessions.

    Examples:
    - "Find sessions showing hypothesis testing" → True
    - "Which sessions have high communication quality?" → True
    - "What did David say about fusion?" → False (specific content)
    """
    query_lower = query.lower()

    for pattern in EXPLORATORY_PATTERNS:
        if re.search(pattern, query_lower):
            logger.info(f"Detected exploratory query (pattern: {pattern})")
            return True

    return False
