"""
Reason and Act Node for BLINC Agent V3

The core reasoning loop that decides what action to take.
Uses GPT-4o with tool descriptions to naturally select tools.
NO keyword matching - trusts the model's understanding.
"""

import json
import logging
from typing import Dict, Any

from openai import OpenAI

logger = logging.getLogger(__name__)


def reason_and_act(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main reasoning node that decides what to do next.

    This node:
    1. Analyzes the query and context
    2. Considers previous retrieval results
    3. Decides whether to use a tool, synthesize, or clarify
    4. Returns the decision with tool parameters

    The key insight: We use GPT-4o (not mini) and trust its reasoning
    with well-written tool descriptions. No keyword matching.

    Args:
        state: Current agent state

    Returns:
        Updated state with action decision
    """
    query = state.get('current_query', state.get('original_query', ''))
    iteration = state.get('iteration_count', 0) + 1

    logger.info(f"Reasoning iteration {iteration}: '{query}'")

    # Check iteration limit
    if iteration > state.get('max_iterations', 8):
        logger.warning("Max iterations reached, forcing synthesis")
        return {
            'iteration_count': iteration,
            'next_action': 'synthesize'
        }

    # Build context for the model
    context = _build_context(state)
    previous_results = state.get('retrieval_results', [])

    # Check if we have enough information to synthesize
    if _should_synthesize(previous_results, iteration):
        logger.info("Have enough relevant results, proceeding to synthesis")
        return {
            'iteration_count': iteration,
            'next_action': 'synthesize'
        }

    # Call GPT-4o for reasoning
    try:
        client = OpenAI()

        system_prompt = _get_system_prompt()
        user_prompt = _get_user_prompt(query, context, previous_results)

        response = client.chat.completions.create(
            model="gpt-4o",  # Use the powerful model
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,  # Low temperature for consistent reasoning
            max_tokens=500,
            response_format={"type": "json_object"}
        )

        decision = json.loads(response.choices[0].message.content)
        logger.info(f"Reasoning decision: {decision.get('action')} - {decision.get('thought', '')[:100]}")

        # Record thought if present
        thought_history = state.get('thought_history', []).copy()
        if decision.get('thought'):
            thought_history.append(decision['thought'])

        # Handle the decision
        action = decision.get('action', 'think')

        if action == 'synthesize':
            return {
                'iteration_count': iteration,
                'next_action': 'synthesize',
                'thought_history': thought_history,
                'current_thought': decision.get('thought')
            }

        elif action == 'clarify':
            return {
                'iteration_count': iteration,
                'next_action': 'clarify',
                'current_tool': 'clarify',
                'current_tool_input': decision.get('action_input', {}),
                'thought_history': thought_history,
                'current_thought': decision.get('thought')
            }

        elif action == 'think':
            # Just thinking, continue the loop
            return {
                'iteration_count': iteration,
                'next_action': 'continue',
                'thought_history': thought_history,
                'current_thought': decision.get('thought') or decision.get('action_input', {}).get('reasoning', '')
            }

        else:
            # Tool call
            return {
                'iteration_count': iteration,
                'next_action': 'execute_tool',
                'current_tool': action,
                'current_tool_input': decision.get('action_input', {}),
                'thought_history': thought_history,
                'current_thought': decision.get('thought')
            }

    except Exception as e:
        logger.error(f"Reasoning error: {e}")

        # On error, try a simple search if we haven't tried anything
        if not previous_results:
            return {
                'iteration_count': iteration,
                'next_action': 'execute_tool',
                'current_tool': 'search_transcripts',
                'current_tool_input': {'query': query, 'limit': 10},
                'error': str(e)
            }
        else:
            # If we have some results, synthesize
            return {
                'iteration_count': iteration,
                'next_action': 'synthesize',
                'error': str(e)
            }


def _should_synthesize(results: list, iteration: int) -> bool:
    """Determine if we have enough information to synthesize.

    For compound queries, we want multiple representation types covered.
    """
    if not results:
        return False

    # Count relevant results and distinct representation types
    relevant_count = 0
    types_covered = set()

    TOOL_TO_TYPE = {
        'search_transcripts': 'transcripts',
        'get_collaboration_analysis': 'collaboration',
        'compare_sessions': 'comparison',
        'get_session_overview': 'overview',
        'analyze_speaker': 'speaker',
        'search_concepts': 'concepts',
        'explore_concepts': 'concepts',
        'get_concept_map': 'concepts',
    }

    for r in results:
        if r.get('is_relevant', False):
            relevant_count += 1
            tool = r.get('tool_name', '')
            if tool in TOOL_TO_TYPE:
                types_covered.add(TOOL_TO_TYPE[tool])

    # Synthesize if we have good coverage:
    # - 2+ different representation types (compound query satisfied)
    # - OR 3+ relevant results from any sources
    # - OR 1+ relevant after 5 iterations (fallback to prevent infinite loops)
    if len(types_covered) >= 2:
        return True
    if relevant_count >= 3:
        return True
    if relevant_count >= 1 and iteration >= 5:
        return True

    return False


def _build_context(state: Dict[str, Any]) -> Dict[str, Any]:
    """Build context object for the prompt."""
    return {
        'current_session_focus': state.get('current_session_focus'),
        'previous_session_focus': state.get('previous_session_focus'),
        'session_history': state.get('session_history', []),
        'compared_sessions': state.get('compared_sessions', []),
        'current_speaker_focus': state.get('current_speaker_focus')
    }


def _get_system_prompt() -> str:
    """Get the system prompt for reasoning."""
    from ..prompts.tool_descriptions import get_tools_prompt
    from ..prompts.reasoning import REASONING_SYSTEM_PROMPT

    tools_prompt = get_tools_prompt()

    return f"""{REASONING_SYSTEM_PROMPT}

{tools_prompt}

## Decision Making

Based on the query and context, decide your next action:

1. **Use a tool** - If you need information to answer the query
2. **synthesize** - If you have enough relevant information from previous results
3. **think** - If you need to reason through a complex problem
4. **clarify** - ONLY if the query is genuinely ambiguous (prefer searching)

## Response Format

Always respond with a JSON object:
{{
    "thought": "Brief reasoning about what to do",
    "action": "tool_name OR synthesize OR think OR clarify",
    "action_input": {{...parameters...}} OR null
}}

## Key Principles

- Trust the tool descriptions - they explain WHEN to use each tool
- For "best" or "compare" queries, use compare_sessions with session IDs [18,19,20,21,22,23,24,25]
- Consider the conversation context for references like "it" or "that session"
- Be efficient - don't call unnecessary tools

## CRITICAL: Compound Queries

When a query asks about MULTIPLE aspects (e.g., "collaborate AND concepts", "said AND patterns"),
you MUST retrieve ALL relevant representations before synthesizing:

- "How did they collaborate AND what was discussed?" → Need BOTH collaboration analysis AND transcripts
- "What concepts emerged AND how was participation?" → Need BOTH concepts AND collaboration analysis
- "What was said about X AND how do ideas connect?" → Need BOTH transcripts AND concept exploration

**DO NOT synthesize until you have results from ALL required representation types.**
Check your previous results - if the query has multiple parts, ensure each part is addressed.
"""


def _get_user_prompt(query: str, context: dict, previous_results: list) -> str:
    """Build the user prompt with current state."""

    # Format context
    context_lines = []
    if context.get('current_session_focus'):
        context_lines.append(f"- Currently focused on: Session {context['current_session_focus']}")
    if context.get('previous_session_focus'):
        context_lines.append(f"- Previous session: Session {context['previous_session_focus']}")
    if context.get('compared_sessions'):
        context_lines.append(f"- Comparing: Sessions {context['compared_sessions']}")
    if context.get('current_speaker_focus'):
        context_lines.append(f"- Speaker focus: {context['current_speaker_focus']}")

    context_str = "\n".join(context_lines) if context_lines else "No prior context"

    # Format previous results and track representation types covered
    results_lines = []
    types_covered = set()

    TOOL_TO_TYPE = {
        'search_transcripts': 'transcripts',
        'get_collaboration_analysis': 'collaboration',
        'compare_sessions': 'comparison',
        'get_session_overview': 'overview',
        'analyze_speaker': 'speaker',
        'search_concepts': 'concepts',
        'explore_concepts': 'concepts',
        'get_concept_map': 'concepts',
    }

    for result in previous_results[-5:]:  # Last 5
        tool = result.get('tool_name', 'unknown')
        count = result.get('result_count', 0)
        relevant = "relevant" if result.get('is_relevant', False) else "not relevant"
        query_used = result.get('query_used', '')[:50]
        results_lines.append(f"- {tool}('{query_used}'): {count} results ({relevant})")

        if result.get('is_relevant', False):
            rep_type = TOOL_TO_TYPE.get(tool)
            if rep_type:
                types_covered.add(rep_type)

    results_str = "\n".join(results_lines) if results_lines else "No results yet"

    # Add coverage summary for compound query awareness
    if types_covered:
        results_str += f"\n\n**Representations covered:** {', '.join(sorted(types_covered))}"
        results_str += "\n(For compound queries, check if ALL required types are covered before synthesizing)"

    # Add CRITICAL comparison guidance if we're comparing sessions
    comparison_guidance = ""
    if context.get('compared_sessions') and len(context.get('compared_sessions', [])) >= 2:
        sessions = context['compared_sessions']
        comparison_guidance = f"""

## CRITICAL: COMPARISON QUERY DETECTED

The user is comparing sessions: {sessions}

You MUST:
1. Use `compare_sessions` tool with `session_ids={sessions}`
2. Do NOT search for session names as if they were content (e.g., don't search for "country music" in transcripts)
3. The session IDs {sessions} are already resolved from session names
4. Do NOT use search_transcripts for comparison queries - use compare_sessions

The sessions to compare are ALREADY RESOLVED to IDs. Use them directly in compare_sessions.

**CORRECT**: compare_sessions(session_ids={sessions})
**WRONG**: search_transcripts(query="country music")
"""

    return f"""## User Query
{query}

## Conversation Context
{context_str}
{comparison_guidance}
## Previous Results This Turn
{results_str}

## Your Task
Decide what to do next. If you have enough relevant information, synthesize an answer.
Otherwise, call the appropriate tool to get more information.

Remember: Tool descriptions explain WHEN to use each tool. Trust them."""
