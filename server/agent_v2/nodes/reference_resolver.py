"""
Reference Resolver Node

Resolves session/speaker references using conversation context.
Handles pronouns ("it", "they"), ordinals ("first session"), and name-based references.
"""

import re
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


def reference_resolver(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resolve session and speaker references in the query.

    This node handles:
    1. Explicit session IDs ("session 23")
    2. Session names ("Dinosaurs session", "NYC discussion")
    3. Ordinal references ("first session", "second one")
    4. Pronoun references ("it", "that session")
    5. "Go back" references ("previous session")
    6. "Both sessions" references

    Args:
        state: Current agent state with query and context

    Returns:
        Updated state with resolved session focus
    """
    query = state.get('resolved_query') or state.get('original_query', '')
    query_lower = query.lower()

    # Get current context
    current_focus = state.get('current_session_focus')
    previous_focus = state.get('previous_session_focus')
    session_history = state.get('session_history', [])
    compared_sessions = state.get('compared_sessions', [])

    updates = {}

    # 1. Check for explicit session ID
    session_id_match = re.search(r'\bsession\s*(\d+)\b', query_lower)
    if session_id_match:
        session_id = int(session_id_match.group(1))
        logger.info(f"Resolved explicit session ID: {session_id}")
        updates['current_session_focus'] = session_id
        if current_focus and current_focus != session_id:
            updates['previous_session_focus'] = current_focus
        # Add to history if not already there
        if session_id not in session_history:
            updates['session_history'] = session_history + [session_id]
        return {**updates, "next_node": "classifier"}

    # 2. Check for session name references (like "Dinosaurs session", "NYC discussion")
    session_name = _extract_session_name(query)
    if session_name:
        resolved_id = _resolve_session_name(session_name)
        if resolved_id:
            logger.info(f"Resolved session name '{session_name}' to ID: {resolved_id}")
            updates['current_session_focus'] = resolved_id
            if current_focus and current_focus != resolved_id:
                updates['previous_session_focus'] = current_focus
            if resolved_id not in session_history:
                updates['session_history'] = session_history + [resolved_id]
            return {**updates, "next_node": "classifier"}

    # 3. Check for ordinal references
    ordinal_match = re.search(r'\b(first|second|third|fourth|fifth|1st|2nd|3rd|4th|5th)\s+(session|one)\b', query_lower)
    if ordinal_match and session_history:
        ordinal_map = {
            'first': 0, '1st': 0,
            'second': 1, '2nd': 1,
            'third': 2, '3rd': 2,
            'fourth': 3, '4th': 3,
            'fifth': 4, '5th': 4
        }
        ordinal = ordinal_match.group(1)
        index = ordinal_map.get(ordinal, 0)
        if index < len(session_history):
            resolved_id = session_history[index]
            logger.info(f"Resolved ordinal '{ordinal}' to session: {resolved_id}")
            updates['current_session_focus'] = resolved_id
            if current_focus and current_focus != resolved_id:
                updates['previous_session_focus'] = current_focus
            return {**updates, "next_node": "classifier"}

    # 4. Check for "go back" / "previous" references
    go_back_patterns = [
        r'\bgo\s*back\b',
        r'\bprevious\s+(session|one)\b',
        r'\bback\s+to\s+what\b',
        r'\breturn\s+to\b',
        r'\bbefore\s+that\b'
    ]
    for pattern in go_back_patterns:
        if re.search(pattern, query_lower):
            if previous_focus:
                logger.info(f"Resolved 'go back' to previous session: {previous_focus}")
                updates['current_session_focus'] = previous_focus
                updates['previous_session_focus'] = current_focus
                return {**updates, "next_node": "classifier"}
            break

    # 5. Check for "both sessions" references
    if re.search(r'\bboth\s+(sessions?|of\s+them)\b', query_lower):
        if compared_sessions and len(compared_sessions) >= 2:
            logger.info(f"Using compared sessions from context: {compared_sessions}")
            # Keep compared_sessions as is, they'll be used in comparison
            return {"next_node": "classifier"}
        elif previous_focus and current_focus:
            updates['compared_sessions'] = [previous_focus, current_focus]
            logger.info(f"Set compared_sessions to: {[previous_focus, current_focus]}")
            return {**updates, "next_node": "classifier"}

    # 6. Check for pronoun references that need context
    pronoun_patterns = [
        r'\b(it|that|this|the)\s+(session|discussion|one)\b',
        r'\bthat\s+session\b',
        r'\bthe\s+session\b'
    ]
    needs_context = False
    for pattern in pronoun_patterns:
        if re.search(pattern, query_lower):
            needs_context = True
            break

    if needs_context and not current_focus:
        # We might need clarification, but let the classifier handle it
        logger.info("Query has pronoun reference but no session context - classifier will handle")

    # No explicit resolution needed, pass through
    return {"next_node": "classifier"}


def _extract_session_name(query: str) -> Optional[str]:
    """
    Extract potential session name from query.

    Looks for patterns like:
    - "Dinosaurs session"
    - "the NYC discussion"
    - "interview about psychology"
    - "The Shaw Interview" (standalone session name)
    - "Nuclear Fusion" (standalone topic name)
    """
    query_lower = query.lower()

    # Pattern: "<Name> session" or "<Name> discussion"
    name_pattern = re.search(
        r'(?:the\s+)?(\w+(?:\s+\w+)?)\s+(?:session|discussion)\b',
        query_lower
    )
    if name_pattern:
        name = name_pattern.group(1)
        # Filter out generic words
        generic = {'that', 'this', 'the', 'a', 'an', 'first', 'second', 'third',
                  'last', 'previous', 'next', 'same', 'other', 'another'}
        if name.split()[0] not in generic:
            return name

    # Pattern: "session about <topic>"
    about_pattern = re.search(r'session\s+about\s+(\w+(?:\s+\w+)?)', query_lower)
    if about_pattern:
        return about_pattern.group(1)

    # Pattern: Standalone session name (for clarification responses)
    # If query is short (<=5 words) and starts with "The" or is a proper name,
    # treat it as a potential session name
    words = query.strip().split()
    if len(words) <= 5:
        # Remove leading "The" for matching
        clean_query = query.strip()
        if clean_query.lower().startswith('the '):
            clean_query = clean_query[4:]
        # If it's a short query, try it as a session name
        if len(clean_query) > 2:
            return clean_query

    return None


def _resolve_session_name(name: str) -> Optional[int]:
    """
    Resolve a session name to session_device_id.

    Searches session names and device names for matches.
    Uses mysql.connector for direct database access.
    """
    try:
        import mysql.connector

        name_lower = name.lower()

        # Connect directly to MySQL
        connection = mysql.connector.connect(
            host='localhost',
            user='vagrant',
            password='vagrant',
            database='discussion_capture'
        )

        try:
            cursor = connection.cursor()

            # Search session names
            cursor.execute("""
                SELECT sd.id, s.name
                FROM session_device sd
                JOIN session s ON s.id = sd.session_id
                WHERE s.name IS NOT NULL
            """)
            sessions = cursor.fetchall()

            for sd_id, session_name in sessions:
                if session_name and name_lower in session_name.lower():
                    logger.info(f"Matched '{name}' to session '{session_name}' (ID: {sd_id})")
                    cursor.close()
                    return sd_id

            # Search device names as fallback
            cursor.execute("""
                SELECT id, name
                FROM session_device
                WHERE name IS NOT NULL
            """)
            devices = cursor.fetchall()

            for device_id, device_name in devices:
                if device_name and name_lower in device_name.lower():
                    logger.info(f"Matched '{name}' to device '{device_name}' (ID: {device_id})")
                    cursor.close()
                    return device_id

            cursor.close()

        finally:
            connection.close()

        return None

    except Exception as e:
        logger.error(f"Error resolving session name '{name}': {e}")
        return None
