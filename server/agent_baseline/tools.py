"""
Simplified Tool Registry for BLINC Agent Baseline (Transcript-Only)

4 core tools with restricted access (NO concept map, NO collaboration assessment):
1. list_sessions      - List all available sessions (no collaboration scores)
2. search_sessions    - Find sessions by topic (transcript collection only)
3. get_transcript     - Get session transcript
4. get_speaker_profile - Get speaker metrics (psycholinguistic only, no concepts)

This baseline agent has NO access to:
- Concept maps (ideas, relationships, speaker contributions)
- Collaboration assessment (scores, dimensions, supporting segments)

Design principle: Same ReAct architecture as V7, but restricted data access
for fair comparison testing.
"""

import logging
from typing import Dict, Any, List, Optional, Callable
from functools import wraps

logger = logging.getLogger(__name__)


def tool_wrapper(tool_name: str):
    """Decorator to standardize tool output and logging."""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger.info(f"[Baseline Tool] {tool_name} called with args={args}, kwargs={kwargs}")
            try:
                result = func(*args, **kwargs)
                result["tool_name"] = tool_name
                logger.info(f"[Baseline Tool] {tool_name} completed successfully")
                return result
            except Exception as e:
                logger.error(f"[Baseline Tool] {tool_name} error: {e}")
                return {
                    "tool_name": tool_name,
                    "display": f"Error: {str(e)}",
                    "error": str(e),
                }
        return wrapper
    return decorator


def _get_db_connection():
    """Get database connection."""
    import mysql.connector
    return mysql.connector.connect(
        host='localhost',
        user='vagrant',
        password='vagrant',
        database='discussion_capture'
    )


def _get_rag_service():
    """Get RAG service for semantic search."""
    from rag_service import RAGService
    return RAGService()


# =============================================================================
# Tool 1: list_sessions (NO collaboration scores)
# =============================================================================

@tool_wrapper("list_sessions")
def list_sessions() -> Dict[str, Any]:
    """
    List all available discussion sessions.

    NOTE: This baseline version does NOT show collaboration scores.
    Sessions are listed without collaboration assessment data.

    Returns:
        Dict with 'display' containing LLM-ready text of all sessions
    """
    try:
        conn = _get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get sessions with speakers
        cursor.execute("""
            SELECT
                sd.id as session_device_id,
                s.id as session_id,
                COALESCE(s.name, sd.name) as session_name,
                sd.name as device_name,
                (SELECT COUNT(DISTINCT speaker_id) FROM transcript WHERE session_device_id = sd.id) as speaker_count,
                (SELECT GROUP_CONCAT(DISTINCT sp.alias SEPARATOR ', ')
                 FROM transcript t
                 JOIN speaker sp ON t.speaker_id = sp.id
                 WHERE t.session_device_id = sd.id) as speakers
            FROM session_device sd
            JOIN session s ON sd.session_id = s.id
            ORDER BY sd.id DESC
        """)
        sessions = cursor.fetchall()
        cursor.close()
        conn.close()

        # Build LLM-ready text
        lines = [f"=== Available Sessions ({len(sessions)} total) ===\n"]

        for s in sessions:
            sid = s.get('session_device_id', '?')
            name = s.get('session_name', 'Unnamed')
            device_name = s.get('device_name', '')
            speaker_count = s.get('speaker_count', 0)
            speakers = s.get('speakers', '') or 'Unknown'

            # Format: Discussion ID: Session Name (Device Name)
            if device_name:
                lines.append(f"Discussion {sid}: {name} ({device_name})")
            else:
                lines.append(f"Discussion {sid}: {name}")
            lines.append(f"  Speakers ({speaker_count}): {speakers}")
            lines.append("")

        # Add guidance for LLM (baseline-specific - no collaboration assessment tips)
        lines.append("---")
        lines.append("TIP: Use get_transcript(discussion_id=N) to see what was discussed")
        lines.append("TIP: Use get_speaker_profile(speaker_name='Name') for speaker metrics")

        return {
            "display": "\n".join(lines),
            "session_count": len(sessions),
            "sessions": sessions,
        }

    except Exception as e:
        logger.error(f"list_sessions error: {e}")
        return {
            "display": f"Error listing sessions: {str(e)}",
            "error": str(e),
        }


# =============================================================================
# Tool 2: search_sessions (transcript collection ONLY)
# =============================================================================

@tool_wrapper("search_sessions")
def search_sessions(query: str, top_k: int = 5) -> Dict[str, Any]:
    """
    Find sessions relevant to a query using semantic search on TRANSCRIPT ONLY.

    NOTE: This baseline version searches ONLY the transcript collection.
    It does NOT search collaboration assessment or concept collections.

    Args:
        query: Topic or keyword to search for
        top_k: Maximum number of results

    Returns:
        Dict with 'display' containing LLM-ready text of matching sessions
    """
    top_k = max(top_k, 5)  # Never return fewer than 5 results
    logger.info(f"[Baseline Search] Query: '{query}' (transcript-only)")

    try:
        rag = _get_rag_service()
        conn = _get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Check for exact session name match first
        exact_match_sessions = []
        try:
            cursor.execute("""
                SELECT DISTINCT
                    sd.id as session_device_id,
                    s.id as session_id,
                    COALESCE(s.name, sd.name) as session_name,
                    sd.name as device_name
                FROM session_device sd
                JOIN session s ON sd.session_id = s.id
                WHERE LOWER(s.name) = LOWER(%s)
                   OR LOWER(s.name) LIKE LOWER(%s)
                   OR LOWER(sd.name) LIKE LOWER(%s)
            """, (query, f"%{query}%", f"%{query}%"))
            exact_match_sessions = cursor.fetchall()
            if exact_match_sessions:
                logger.info(f"  [exact_match] Found {len(exact_match_sessions)} sessions matching name '{query}'")
        except Exception as e:
            logger.warning(f"  [exact_match] Name lookup failed: {e}")

        # Search ONLY transcript collection (baseline restriction)
        try:
            transcript_results = rag.transcript_collection.query(
                query_texts=[query],
                n_results=top_k * 3
            )
            logger.info(f"  [transcript] Found {len(transcript_results.get('documents', [[]])[0])} results")
        except Exception as e:
            logger.warning(f"  [transcript] Search failed: {e}")
            transcript_results = {'documents': [[]], 'metadatas': [[]], 'distances': [[]]}

        # Process transcript results - aggregate by session
        session_scores = {}
        session_previews = {}

        docs = transcript_results.get('documents', [[]])[0]
        metas = transcript_results.get('metadatas', [[]])[0]
        distances = transcript_results.get('distances', [[]])[0]

        for doc, meta, dist in zip(docs, metas, distances):
            sid = meta.get('session_device_id')
            if sid is None:
                continue

            # Convert distance to similarity
            similarity = 1.0 - dist

            if sid not in session_scores:
                session_scores[sid] = similarity
                session_previews[sid] = doc[:200] + "..." if len(doc) > 200 else doc
            else:
                # Keep best score for the session
                session_scores[sid] = max(session_scores[sid], similarity)

        # Add exact matches with high score
        for exact in exact_match_sessions:
            sid = exact['session_device_id']
            if sid not in session_scores:
                session_scores[sid] = 1.0
                session_previews[sid] = f"Exact name match: {exact['session_name']}"

        # Sort by score and apply thresholds
        sorted_sessions = sorted(session_scores.items(), key=lambda x: x[1], reverse=True)

        # Apply minimum score threshold
        min_score = 0.20
        min_relative_score = 0.65

        if sorted_sessions:
            best_score = sorted_sessions[0][1]
            threshold = max(min_score, best_score * min_relative_score)
            sorted_sessions = [(sid, score) for sid, score in sorted_sessions if score >= threshold]

        # Limit to top_k
        sorted_sessions = sorted_sessions[:top_k]

        # Get session metadata
        result_sessions = []
        for sid, score in sorted_sessions:
            cursor.execute("""
                SELECT
                    sd.id as session_device_id,
                    COALESCE(s.name, sd.name) as session_name,
                    sd.name as device_name,
                    (SELECT GROUP_CONCAT(DISTINCT sp.alias SEPARATOR ', ')
                     FROM transcript t
                     JOIN speaker sp ON t.speaker_id = sp.id
                     WHERE t.session_device_id = sd.id) as speakers
                FROM session_device sd
                JOIN session s ON sd.session_id = s.id
                WHERE sd.id = %s
            """, (sid,))
            session_meta = cursor.fetchone()

            if session_meta:
                result_sessions.append({
                    'session_device_id': sid,
                    'session_name': session_meta['session_name'],
                    'device_name': session_meta['device_name'],
                    'speakers': session_meta['speakers'],
                    'match_preview': session_previews.get(sid, ''),
                    'relevance_score': score,
                })

        cursor.close()
        conn.close()

        # Build LLM-ready text
        lines = [f"=== Search Results for \"{query}\" ({len(result_sessions)} found) ===\n"]

        if not result_sessions:
            lines.append("No matching discussions found.")
        else:
            for i, s in enumerate(result_sessions, 1):
                sid = s.get('session_device_id', '?')
                name = s.get('session_name', 'Unnamed')
                device_name = s.get('device_name', '')
                speakers = s.get('speakers', 'Unknown')
                preview = s.get('match_preview', '')

                if device_name:
                    lines.append(f"{i}. Discussion {sid}: {name} ({device_name})")
                else:
                    lines.append(f"{i}. Discussion {sid}: {name}")
                lines.append(f"   Speakers: {speakers}")
                if preview:
                    lines.append(f"   Preview: {preview}")
                lines.append("")

        return {
            "display": "\n".join(lines),
            "session_count": len(result_sessions),
            "query": query,
            "sessions": result_sessions,
        }

    except Exception as e:
        logger.error(f"search_sessions error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "display": f"Error searching sessions: {str(e)}",
            "error": str(e),
        }


# =============================================================================
# Tool 3: get_transcript (unchanged from V7)
# =============================================================================

@tool_wrapper("get_transcript")
def get_transcript(
    discussion_id: int,
    speaker_filter: str = None,
    keyword_filter: str = None
) -> Dict[str, Any]:
    """
    Get transcript for a discussion in human-readable format.

    Args:
        discussion_id: Discussion to get transcript for
        speaker_filter: Optional - only get utterances from this speaker
        keyword_filter: Optional - only get utterances containing this keyword

    Returns:
        Dict with 'display' containing LLM-ready formatted transcript
    """
    try:
        conn = _get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get session info
        cursor.execute("""
            SELECT
                sd.id as session_device_id,
                COALESCE(s.name, sd.name) as session_name,
                sd.name as device_name
            FROM session_device sd
            JOIN session s ON sd.session_id = s.id
            WHERE sd.id = %s
        """, (discussion_id,))
        session_info = cursor.fetchone()

        if not session_info:
            cursor.close()
            conn.close()
            return {
                "display": f"Discussion {discussion_id} not found.",
                "error": "Session not found",
            }

        session_name = session_info['session_name']
        device_name = session_info['device_name']

        # Build query with optional filters
        query = """
            SELECT
                t.transcript as text,
                sp.alias as speaker,
                t.start_time
            FROM transcript t
            JOIN speaker sp ON t.speaker_id = sp.id
            WHERE t.session_device_id = %s
        """
        params = [discussion_id]

        if speaker_filter:
            query += " AND LOWER(sp.alias) LIKE LOWER(%s)"
            params.append(f"%{speaker_filter}%")

        if keyword_filter:
            query += " AND LOWER(t.transcript) LIKE LOWER(%s)"
            params.append(f"%{keyword_filter}%")

        query += " ORDER BY t.start_time"

        cursor.execute(query, params)
        utterances = cursor.fetchall()

        cursor.close()
        conn.close()

        # Build LLM-ready text
        title = f"{session_name} ({device_name})" if device_name else session_name
        lines = [
            f"=== Transcript: {title} ===",
            f"Discussion ID: {discussion_id}",
        ]

        if speaker_filter:
            lines.append(f"Filtered by speaker: {speaker_filter}")
        if keyword_filter:
            lines.append(f"Filtered by keyword: {keyword_filter}")

        lines.append(f"Utterances: {len(utterances)}")
        lines.append("")
        lines.append("--- Begin Transcript ---")
        lines.append("")

        for u in utterances:
            speaker = u.get('speaker', 'Unknown') or 'Unknown'
            text = (u.get('text', '') or '').strip()

            # Format timestamp as [MM:SS]
            start_time = u.get('start_time', 0) or 0
            minutes = int(start_time // 60)
            seconds = int(start_time % 60)
            timestamp = f"[{minutes:02d}:{seconds:02d}]"

            lines.append(f"{timestamp} {speaker}: {text}")

        lines.append("")
        lines.append("--- End Transcript ---")

        return {
            "display": "\n".join(lines),
            "discussion_id": discussion_id,
            "session_name": session_name,
            "utterance_count": len(utterances),
            "utterances": utterances,
        }

    except Exception as e:
        logger.error(f"get_transcript error: {e}")
        return {
            "display": f"Error getting transcript: {str(e)}",
            "error": str(e),
        }


# =============================================================================
# Tool 4: get_speaker_profile (psycholinguistic ONLY - no concept data)
# =============================================================================

@tool_wrapper("get_speaker_profile")
def get_speaker_profile(speaker_name: str, discussion_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Get a speaker's engagement profile (psycholinguistic metrics ONLY).

    NOTE: This baseline version does NOT include:
    - Concept node contributions
    - Speaker connections via concept edges
    - Concept-level interaction data

    Returns:
    - Discussions participated
    - Per-discussion metrics (utterances, words, questions, analytic/certainty scores)
    - Sample quotes (diverse selection)

    For full transcript, use get_transcript(discussion_id, speaker_filter=name).

    Args:
        speaker_name: Name of the speaker (partial match supported)
        discussion_id: Optional - limit to specific discussion (None = all discussions)

    Returns:
        Dict with 'display' containing LLM-ready speaker profile
    """
    try:
        connection = _get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Find ALL speaker IDs with this alias (same person has different ID per session)
        cursor.execute("""
            SELECT id, alias, session_device_id FROM speaker WHERE alias LIKE %s
        """, (f"%{speaker_name}%",))
        speakers = cursor.fetchall()

        if not speakers:
            cursor.close()
            connection.close()
            return {
                "display": f"Speaker '{speaker_name}' not found. Use list_sessions to see available speakers.",
                "found": False,
            }

        speaker_ids = [s['id'] for s in speakers]
        speaker_alias = speakers[0]['alias']
        speaker_id_list = ', '.join(str(sid) for sid in speaker_ids)

        # Discussion filters (discussion_id maps to session_device_id internally)
        session_filter = f"AND t.session_device_id = {discussion_id}" if discussion_id else ""
        session_filter_unaliased = f"AND session_device_id = {discussion_id}" if discussion_id else ""

        # Get participation by session (across ALL speaker IDs)
        cursor.execute(f"""
            SELECT
                t.session_device_id,
                COALESCE(s.name, sd.name) as session_name,
                COUNT(*) as utterance_count,
                SUM(t.word_count) as word_count,
                SUM(CASE WHEN t.question = 1 THEN 1 ELSE 0 END) as questions,
                AVG(t.analytic_thinking_value) as avg_analytic,
                AVG(t.certainty_value) as avg_certainty,
                AVG(t.clout_value) as avg_clout,
                AVG(t.emotional_tone_value) as avg_emotional,
                (SELECT COUNT(*) FROM transcript t2 WHERE t2.session_device_id = t.session_device_id) as session_total_utterances,
                (SELECT COUNT(DISTINCT t2.speaker_id) FROM transcript t2 WHERE t2.session_device_id = t.session_device_id) as session_speaker_count
            FROM transcript t
            JOIN session_device sd ON t.session_device_id = sd.id
            JOIN session s ON sd.session_id = s.id
            WHERE t.speaker_id IN ({speaker_id_list}) {session_filter}
            GROUP BY t.session_device_id, s.name, sd.name
        """)
        session_data = cursor.fetchall()

        # Add comparative metrics for LLM to reason about
        for row in session_data:
            utterances = int(row.get('utterance_count') or 0)
            questions = int(row.get('questions') or 0)
            session_total = int(row.get('session_total_utterances') or 1)
            speaker_count = int(row.get('session_speaker_count') or 1)

            row['participation_share_pct'] = round(utterances * 100.0 / session_total, 1) if session_total > 0 else 0
            row['question_rate_pct'] = round(questions * 100.0 / utterances, 1) if utterances > 0 else 0
            row['expected_equal_share_pct'] = round(100.0 / speaker_count, 1) if speaker_count > 0 else 100

        # Get sample quotes - diverse selection showing speaker style
        sample_quotes = []

        # Get questions (across ALL speaker IDs)
        cursor.execute(f"""
            SELECT transcript as text, session_device_id, certainty_value, analytic_thinking_value,
                   'question' as quote_type
            FROM transcript
            WHERE speaker_id IN ({speaker_id_list}) AND question = 1 AND word_count > 10 {session_filter_unaliased}
            ORDER BY word_count DESC LIMIT 2
        """)
        sample_quotes.extend(cursor.fetchall())

        # Get high-certainty statements (across ALL speaker IDs)
        cursor.execute(f"""
            SELECT transcript as text, session_device_id, certainty_value, analytic_thinking_value,
                   'high_certainty' as quote_type
            FROM transcript
            WHERE speaker_id IN ({speaker_id_list}) AND question = 0 AND certainty_value > 70 AND word_count > 15 {session_filter_unaliased}
            ORDER BY certainty_value DESC LIMIT 2
        """)
        sample_quotes.extend(cursor.fetchall())

        # Get high-analytic statements (across ALL speaker IDs)
        cursor.execute(f"""
            SELECT transcript as text, session_device_id, certainty_value, analytic_thinking_value,
                   'high_analytic' as quote_type
            FROM transcript
            WHERE speaker_id IN ({speaker_id_list}) AND question = 0 AND analytic_thinking_value > 70 AND word_count > 15 {session_filter_unaliased}
            ORDER BY analytic_thinking_value DESC LIMIT 2
        """)
        sample_quotes.extend(cursor.fetchall())

        cursor.close()
        connection.close()

        # Build LLM-ready display
        lines = [
            f"=== Speaker Profile: {speaker_alias} ===",
            f"Scope: {'Discussion ' + str(discussion_id) if discussion_id else 'All discussions'}",
            "",
        ]

        # Discussions participated
        total_utterances = sum(d['utterance_count'] for d in session_data)
        total_words = sum(d['word_count'] or 0 for d in session_data)
        total_questions = sum(d['questions'] or 0 for d in session_data)

        lines.append(f"--- Participation Summary ---")
        lines.append(f"Discussions: {len(session_data)}")
        lines.append(f"Total utterances: {total_utterances}")
        lines.append(f"Total words: {total_words}")
        lines.append(f"Questions asked: {total_questions}")
        lines.append("")

        lines.append(f"--- By Discussion (with comparative metrics) ---")
        for sd in session_data:
            lines.append(f"Discussion {sd['session_device_id']}: {sd['session_name']}")
            lines.append(f"  Utterances: {sd['utterance_count']}, Questions: {sd['questions'] or 0}")
            # Comparative metrics for LLM to interpret
            lines.append(f"  Participation: {sd.get('participation_share_pct', 0)}% of session (equal share would be {sd.get('expected_equal_share_pct', 0)}%)")
            lines.append(f"  Question rate: {sd.get('question_rate_pct', 0)}% of their utterances are questions")
            lines.append(f"  Avg metrics: analytic={(sd['avg_analytic'] or 0):.1f}, certainty={(sd['avg_certainty'] or 0):.1f}, clout={(sd['avg_clout'] or 0):.1f}")
        lines.append("")

        # Sample quotes (diverse selection)
        if sample_quotes:
            lines.append(f"--- Sample Quotes ({len(sample_quotes)}) ---")
            for q in sample_quotes:
                quote_type = q.get('quote_type', 'statement')
                text = q['text'] if q['text'] else ''
                cert = q.get('certainty_value') or 0
                anal = q.get('analytic_thinking_value') or 0
                label = {'question': '[Question]', 'high_certainty': '[Certain]', 'high_analytic': '[Analytic]'}.get(quote_type, '')
                lines.append(f"{label} \"{text}\"")
                lines.append(f"  (certainty={cert:.0f}, analytic={anal:.0f})")
            lines.append("")

        # NOTE: Baseline does NOT include concept contributions or speaker connections
        lines.append("--- Note ---")
        lines.append("This profile includes psycholinguistic metrics only.")
        lines.append("For utterance details, use get_transcript(discussion_id=N, speaker_filter='" + speaker_alias + "')")
        lines.append("")
        lines.append("=== End Speaker Profile ===")

        return {
            "display": "\n".join(lines),
            "speaker_alias": speaker_alias,
            "speaker_ids": speaker_ids,
            "discussions": [{"discussion_id": d['session_device_id'], "session_name": d['session_name']} for d in session_data],
            "found": True,
        }

    except Exception as e:
        logger.error(f"Speaker profile error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "display": f"Error getting speaker profile: {str(e)}",
            "error": str(e),
        }


# =============================================================================
# Tool Registry (4 tools ONLY - no concept map, no collaboration assessment)
# =============================================================================

CORE_TOOLS = {
    "list_sessions": list_sessions,
    "search_sessions": search_sessions,
    "get_transcript": get_transcript,
    "get_speaker_profile": get_speaker_profile,
}


def get_tool(name: str) -> Optional[Callable]:
    """Get a tool by name."""
    return CORE_TOOLS.get(name)


def execute_tool(name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tool by name with parameters."""
    tool = get_tool(name)
    if not tool:
        return {
            "tool_name": name,
            "display": f"Error: Unknown tool '{name}'",
            "error": f"Unknown tool: {name}",
        }
    return tool(**params)


def get_tool_names() -> List[str]:
    """Get list of all tool names."""
    return list(CORE_TOOLS.keys())


# =============================================================================
# Tool Schema for OpenAI Function Calling (4 tools ONLY)
# =============================================================================

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "list_sessions",
            "description": "List all available discussion sessions with speaker information. Use this to discover what sessions exist.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_sessions",
            "description": "Search sessions by topic using semantic similarity on transcript content. Returns sessions where the topic was discussed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Topic or keyword to search"},
                    "top_k": {"type": "integer", "description": "Max results", "default": 5}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_transcript",
            "description": "Get discussion transcript with speaker names and timestamps. Use for quotes, content analysis, and verifying claims.",
            "parameters": {
                "type": "object",
                "properties": {
                    "discussion_id": {"type": "integer", "description": "Discussion ID"},
                    "speaker_filter": {"type": "string", "description": "Filter by speaker"},
                    "keyword_filter": {"type": "string", "description": "Filter by keyword"}
                },
                "required": ["discussion_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_speaker_profile",
            "description": "Get speaker's participation metrics: discussions, utterance counts, psycholinguistic scores (analytic, certainty, clout), sample quotes. Chain with get_transcript for specific utterances.",
            "parameters": {
                "type": "object",
                "properties": {
                    "speaker_name": {"type": "string", "description": "Speaker name (partial match supported)"},
                    "discussion_id": {"type": "integer", "description": "Optional: limit to specific discussion"}
                },
                "required": ["speaker_name"]
            }
        }
    },
]
