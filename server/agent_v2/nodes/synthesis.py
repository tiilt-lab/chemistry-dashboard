"""
Synthesis Node

Synthesizes final answer from tool results using LLM.
"""

import json
import logging
import os
from typing import Dict, Any, List

from openai import OpenAI

logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYNTHESIS_PROMPT = """Synthesize a clear, helpful answer based on retrieved information.

Query: {query}
Query type: {query_type}
Session focus: {session_focus}

Tool Results:
{tool_results}

Instructions:
1. Answer the user's question directly and concisely
2. Cite specific evidence (quotes, metrics, session names)
3. If results span multiple sessions, organize by session
4. For comparisons, highlight key differences
5. If data is incomplete or missing, acknowledge it
6. Don't include raw JSON or technical details
7. Use natural language, not bullet points unless comparing

For analytical queries, follow the THREE-LAYER pattern:
- GROUND: Reference artifacts the user can see (concept maps, 7C scores)
- ENRICH: Add specific quotes and timestamps
- EXTEND: Provide original insights beyond the data

Keep the response focused and under 500 words unless the query requires more detail.
"""


def synthesizer(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Synthesize final answer from tool results.

    Args:
        state: Current agent state with tool results

    Returns:
        Updated state with final answer
    """
    query = state.get('resolved_query') or state.get('original_query', '')
    query_type = state.get('query_type', 'topic_search')
    session_focus = state.get('current_session_focus')
    tool_results = state.get('tool_results', [])
    plan_results = state.get('plan_results', [])

    # Combine results from both ReAct and Plan-Execute
    all_results = tool_results + plan_results

    if not all_results:
        return {
            "final_answer": "I couldn't find relevant information to answer your question. "
                          "Could you try rephrasing or specifying a session?",
            "confidence": 0.2,
            "next_node": "format"
        }

    # Format results for LLM
    results_text = _format_results_for_synthesis(all_results)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": SYNTHESIS_PROMPT.format(
                    query=query,
                    query_type=query_type,
                    session_focus=session_focus,
                    tool_results=results_text
                )
            }],
            temperature=0.7,
            max_tokens=1500
        )

        answer = response.choices[0].message.content
        logger.info(f"Synthesized answer ({len(answer)} chars)")

    except Exception as e:
        logger.error(f"Synthesis failed: {e}")
        answer = _fallback_synthesis(all_results, query)

    # Calculate confidence based on result quality
    confidence = _calculate_confidence(all_results)

    # Extract citations for frontend
    citations = _extract_citations(all_results)

    # Extract session focus from results for multi-turn context
    session_focus_update = _extract_session_focus(all_results, session_focus)

    result = {
        "final_answer": answer,
        "confidence": confidence,
        "citations": citations,
        "next_node": "format",
        # Always preserve session context for multi-turn conversations
        "current_session_focus": session_focus_update or session_focus,
        "previous_session_focus": state.get("previous_session_focus"),
        "session_history": state.get("session_history", []),
        "compared_sessions": state.get("compared_sessions", [])
    }

    return result


def _format_results_for_synthesis(results: List[Dict]) -> str:
    """Format tool results for LLM consumption."""
    formatted = []

    for i, result in enumerate(results, 1):
        tool_name = result.get('tool_name') or result.get('tool', 'unknown')
        data = result.get('data') or result.get('result', {})

        if isinstance(data, str):
            # Already formatted (e.g., insights)
            formatted.append(f"[{tool_name}]: {data[:1000]}")
            continue

        # Handle list results (like from get_sessions_by_metrics)
        if isinstance(data, list):
            if data:
                items = []
                for session in data[:5]:  # Top 5
                    if isinstance(session, dict):
                        session_name = session.get('session_name', f"Session {session.get('session_device_id', '?')}")
                        # Include key metrics
                        metrics = []
                        if 'climate_score' in session:
                            metrics.append(f"climate: {session['climate_score']}")
                        if 'communication_score' in session:
                            metrics.append(f"communication: {session['communication_score']}")
                        if 'contribution_score' in session:
                            metrics.append(f"contribution: {session['contribution_score']}")
                        if 'debate_score' in session:
                            metrics.append(f"debate: {session['debate_score']}")
                        metrics_str = ", ".join(metrics) if metrics else "no metrics"
                        items.append(f"  - {session_name}: {metrics_str}")
                formatted.append(f"[{tool_name}] ({len(data)} sessions):\n" + "\n".join(items))
            else:
                formatted.append(f"[{tool_name}]: No sessions found")
            continue

        if not isinstance(data, dict):
            continue

        # Format based on tool type
        if 'results' in data:
            results_list = data['results'][:5]  # Top 5
            if results_list:
                items = []
                for r in results_list:
                    text = r.get('text', r.get('text_preview', ''))

                    # Check if this is a speaker profile result (has speaker_alias, no session_device_id)
                    if r.get('speaker_alias') and not r.get('session_device_id'):
                        # Speaker profile - include full text (contains valuable metrics)
                        speaker_name = r.get('speaker_alias')
                        items.append(f"  SPEAKER PROFILE - {speaker_name}:\n{text[:800]}")
                    else:
                        # Session-based result
                        session = r.get('session_device_id', r.get('session_name', 'unknown'))
                        speaker = r.get('speaker', r.get('speaker_alias', ''))
                        if speaker:
                            items.append(f"  - Session {session} ({speaker}): {text[:200]}...")
                        else:
                            items.append(f"  - Session {session}: {text[:200]}...")
                formatted.append(f"[{tool_name}] ({data.get('result_count', len(results_list))} results):\n" + "\n".join(items))

        elif 'dimensions' in data:
            # 7C analysis - include ALL dimensions with explanations
            dims = data['dimensions']
            scores = []
            for dim, info in dims.items():
                score = info.get('score', 0)
                explanation = info.get('explanation', '')[:150]
                if explanation:
                    scores.append(f"  {dim}: {score}/100 - {explanation}")
                else:
                    scores.append(f"  {dim}: {score}/100")
            formatted.append(f"[{tool_name}] 7C Analysis for Session {data.get('session_device_id')}:\n" + "\n".join(scores))

        elif 'sessions' in data:
            # Comparison
            sessions = data['sessions']
            formatted.append(f"[{tool_name}] Compared {len(sessions)} sessions")

        elif 'metrics' in data:
            # Metrics
            metrics = data['metrics']
            formatted.append(f"[{tool_name}]: " + ", ".join(f"{k}={v}" for k, v in metrics.items()))

        else:
            # Generic
            formatted.append(f"[{tool_name}]: {str(data)[:500]}")

    return "\n\n".join(formatted) or "No results found"


def _fallback_synthesis(results: List[Dict], query: str) -> str:
    """Generate fallback answer when LLM synthesis fails."""
    # Try to extract something useful
    for result in results:
        data = result.get('data') or result.get('result', {})
        if isinstance(data, dict) and 'results' in data:
            first_result = data['results'][0] if data['results'] else None
            if first_result:
                text = first_result.get('text', first_result.get('text_preview', ''))
                return f"Based on the available data: {text[:500]}..."

    return "I found some information but had trouble summarizing it. Please try a more specific question."


def _calculate_confidence(results: List[Dict]) -> float:
    """Calculate confidence score based on result quality and diversity."""
    if not results:
        return 0.2

    total_results = 0
    has_structured_data = False  # 7C analysis, speaker profiles, etc.
    num_tools = len(results)

    for result in results:
        data = result.get('data') or result.get('result', {})

        # Handle list results (from get_sessions_by_metrics, etc.)
        if isinstance(data, list):
            total_results += len(data)
            # Check for structured session data
            if data and isinstance(data[0], dict):
                first = data[0]
                if 'climate_score' in first or 'communication_score' in first:
                    has_structured_data = True  # Session metrics are structured

        elif isinstance(data, dict):
            count = data.get('result_count', data.get('total_found', 0))
            if 'results' in data:
                count = len(data['results'])
            total_results += count

            # Check for high-quality structured data
            if 'dimensions' in data:  # 7C analysis
                has_structured_data = True
            if 'speaker_alias' in str(data):  # Speaker profile
                has_structured_data = True
            if 'metrics' in data:  # Metrics data
                has_structured_data = True

    # Base confidence on result count
    if total_results == 0:
        base_confidence = 0.3
    elif total_results < 3:
        base_confidence = 0.6
    elif total_results < 10:
        base_confidence = 0.8
    else:
        base_confidence = 0.85

    # Boost for structured data (more reliable)
    if has_structured_data:
        base_confidence = min(0.9, base_confidence + 0.1)

    # Boost for multiple tools (more thorough search)
    if num_tools >= 3:
        base_confidence = min(0.9, base_confidence + 0.05)

    return base_confidence


def _extract_session_focus(results: List[Dict], current_focus: int) -> int:
    """
    Extract session focus from tool results for multi-turn context.

    If results come from a single session, set that as the current focus.
    This enables multi-turn context even when session wasn't resolved by name.
    """
    if current_focus:
        return None  # Already have a focus, don't override

    session_ids = set()

    for result in results:
        data = result.get('data') or result.get('result', {})
        if not isinstance(data, dict):
            continue

        # Check for session_device_id directly in result
        if 'session_device_id' in data:
            session_ids.add(data['session_device_id'])

        # Check in nested results
        if 'results' in data:
            for r in data['results']:
                if isinstance(r, dict):
                    sid = r.get('session_device_id') or r.get('metadata', {}).get('session_device_id')
                    if sid:
                        session_ids.add(sid)

        # Check in session_results
        if 'session_results' in data:
            for sr in data['session_results']:
                if isinstance(sr, dict) and 'session_device_id' in sr:
                    session_ids.add(sr['session_device_id'])

    # If all results are from a single session, set it as focus
    if len(session_ids) == 1:
        focus = session_ids.pop()
        logger.info(f"Extracted session focus from results: {focus}")
        return focus

    return None


def _extract_citations(results: List[Dict]) -> List[Dict]:
    """Extract citations for frontend display."""
    citations = []

    for result in results:
        data = result.get('data') or result.get('result', {})
        if isinstance(data, dict) and 'results' in data:
            for r in data['results'][:3]:  # Top 3 per tool
                citation = {
                    "session_device_id": r.get('session_device_id'),
                    "text": r.get('text', r.get('text_preview', ''))[:200],
                    "speaker": r.get('speaker', r.get('speaker_alias')),
                    "start_time": r.get('start_time', r.get('metadata', {}).get('start_time'))
                }
                if citation['session_device_id']:
                    citations.append(citation)

    return citations[:10]  # Max 10 citations
