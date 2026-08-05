"""
Reasoning Prompts for BLINC Agent V3

The core reasoning prompt that enables intelligent tool selection
without keyword matching.

Progressive context loading: Load session list dynamically,
only include minimal info upfront.
"""

import logging
from functools import lru_cache

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_session_context() -> str:
    """
    Dynamically fetch session context from database.

    Progressive disclosure: Only include ID and name,
    agent can use get_session_overview for details.

    Cached to avoid repeated DB calls within same process.
    """
    try:
        import mysql.connector
        connection = mysql.connector.connect(
            host='localhost',
            user='vagrant',
            password='vagrant',
            database='discussion_capture'
        )
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                sd.id as session_id,
                COALESCE(s.name, sd.name) as session_name
            FROM session_device sd
            JOIN session s ON s.id = sd.session_id
            ORDER BY sd.id
        """)

        sessions = cursor.fetchall()
        cursor.close()
        connection.close()

        if not sessions:
            return "No sessions available."

        # Minimal context: just ID and name
        lines = ["| ID | Session Name |", "|----|--------------| "]
        for s in sessions:
            lines.append(f"| {s['session_id']} | {s['session_name']} |")

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"Failed to load session context: {e}")
        return "Session data unavailable. Use list_sessions tool to discover available sessions."


def get_reasoning_system_prompt() -> str:
    """Get the system prompt with dynamically loaded session context."""
    session_table = _get_session_context()

    return f"""You are an intelligent assistant for analyzing collaborative discussions.

## Available Sessions

{session_table}

**Note**: Use `get_session_overview(session_id)` or `list_sessions()` to get detailed information about speakers, themes, and discourse type.

Each session has:
- Transcripts (what was said, by whom, when)
- Concept map (ideas, questions, connections)
- 7C collaboration scores (measured teamwork quality)
- Theme clusters

## Tool Selection: SEARCH vs MEASUREMENT

**SEARCH tools** find content that MENTIONS something:
- "What did they discuss about X?" → search_transcripts
- "Which sessions talked about Y?" → search_sessions
- These return TEXT that contains your query terms

**MEASUREMENT tools** return SCORES and STRUCTURED DATA:
- "How well did they collaborate?" → get_collaboration_analysis(session_id) returns 7C scores for one session
- "Which session had the BEST collaboration?" → compare_sessions(session_ids=[list of all IDs]) returns all scores
- "Tell me about session X" → get_session_overview
- "What sessions are available?" → list_sessions
- These return NUMBERS and STRUCTURED INFO, not text content

**Key insight**: Words like "best", "highest", "most", "compare", "how well" indicate you need MEASUREMENT tools, not SEARCH tools. Searching for "collaboration" finds text mentioning it; get_collaboration_analysis returns actual scores.

**CRITICAL for comparisons**: To find "best" or "highest" across sessions, use compare_sessions with session IDs from the table above. This returns collaboration scores for all sessions at once.

## Core Principles

1. **Transcripts are the foundation**: For almost ALL content queries, search_transcripts should be your FIRST tool. Raw transcripts provide primary evidence of what was actually said. Other representations (concepts, 7C scores) ENHANCE your reasoning but don't replace transcript evidence.

2. **Search, don't ask**: When in doubt, search and show results.

3. **Match query intent to tool type**:
   - Looking for CONTENT about something? → SEARCH tools (start with transcripts!)
   - Measuring or comparing QUALITY? → MEASUREMENT tools + transcripts for context

4. **Be thorough for comprehensive answers**:
   - For SPEAKER queries ("How does X engage/participate/discuss?"):
     * Call analyze_speaker to get METRICS (participation patterns, speaking style)
     * ALSO call search_transcripts with speaker filter to get ACTUAL QUOTES
     * Both perspectives give a complete picture
   - For TIMELINE/PROGRESSION queries ("How did the discussion unfold?"):
     * Call get_session_overview for structure
     * Call search_transcripts for specific moments
   - For "WHY" questions:
     * Search for relevant content first
     * Get metrics if applicable (collaboration scores, speaker data)
     * Then synthesize an explanation from the evidence

4. **Don't synthesize too early**: If you only have metrics but no quotes, or only quotes but no context, get more data.

5. **Cite evidence**: Ground answers in specific data (session, speaker, timestamp).

## Session Context

- Use the session table above to resolve names to IDs
- Use get_session_overview to get speaker and theme details when needed
- Maintain context: "it" or "that session" refers to current focus
- Build on previous queries in conversation
"""

# Keep legacy constant for backwards compatibility
REASONING_SYSTEM_PROMPT = get_reasoning_system_prompt()


REASONING_USER_TEMPLATE = """## Current Query
{query}

## Conversation Context
{context}

## Previous Results in This Turn
{previous_results}

## Your Task
Decide your next action. You can:
1. Use `think` to reason about the query
2. Use a search/analysis tool to get information
3. Use `synthesize` if you have enough information to answer
4. Use `clarify` only if the query is genuinely ambiguous (prefer searching)

Respond with a JSON object:
{{
    "thought": "Brief reasoning about what to do next",
    "action": "tool_name OR synthesize",
    "action_input": {{...tool parameters...}} OR null for synthesize
}}

Remember: The tool descriptions explain WHEN to use each tool. Trust those descriptions.
"""


def format_reasoning_prompt(
    query: str,
    context: dict,
    previous_results: list
) -> str:
    """
    Format the reasoning prompt with current context.

    Args:
        query: The user's query
        context: Conversation context (session focus, history)
        previous_results: Results from tools already called

    Returns:
        Formatted prompt string
    """
    # Format context
    context_lines = []
    if context.get('current_session_focus'):
        context_lines.append(f"- Current session focus: Session {context['current_session_focus']}")
    if context.get('previous_session_focus'):
        context_lines.append(f"- Previous session: Session {context['previous_session_focus']}")
    if context.get('session_history'):
        context_lines.append(f"- Sessions discussed: {context['session_history'][-5:]}")
    if context.get('current_speaker_focus'):
        context_lines.append(f"- Current speaker focus: {context['current_speaker_focus']}")

    context_str = "\n".join(context_lines) if context_lines else "No prior context"

    # Format previous results
    if previous_results:
        results_lines = []
        for result in previous_results[-3:]:  # Last 3 results
            tool = result.get('tool_name', 'unknown')
            count = result.get('result_count', 0)
            relevant = "relevant" if result.get('is_relevant', True) else "not relevant"
            results_lines.append(f"- {tool}: {count} results ({relevant})")
        results_str = "\n".join(results_lines)
    else:
        results_str = "No results yet"

    return REASONING_USER_TEMPLATE.format(
        query=query,
        context=context_str,
        previous_results=results_str
    )
