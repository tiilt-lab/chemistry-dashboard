"""
Reflect Node for BLINC Agent V3

Self-reflection on the generated answer before returning.
"""

import json
import logging
from typing import Dict, Any

from openai import OpenAI

logger = logging.getLogger(__name__)


def reflect(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Reflect on the generated answer quality.

    This node:
    1. Evaluates if the answer fully addresses the query
    2. Checks for accuracy and completeness
    3. Generates follow-up suggestions
    4. Assigns a confidence score

    OPTIMIZATION: If PRAS path already set confidence/follow_ups via grounded_synthesizer,
    skip the LLM call (saves ~5s per query).

    Args:
        state: Current agent state with final_answer

    Returns:
        Updated state with reflection, confidence, and follow_ups
    """
    query = state.get('original_query', '')
    answer = state.get('final_answer', '')
    tools_used = state.get('tools_used', [])

    logger.info(f"Reflecting on answer for: '{query}'")

    if not answer:
        return {
            'confidence': 0.0,
            'reflection': 'No answer was generated',
            'follow_ups': ['Try asking a different question'],
            'next_action': 'format'
        }

    # OPTIMIZATION: Skip LLM reflection if PRAS path already set confidence
    # grounded_synthesizer sets confidence and follow_ups, no need to redo
    existing_confidence = state.get('confidence')
    existing_followups = state.get('follow_ups', [])

    if existing_confidence is not None and existing_confidence > 0:
        logger.info(f"Skipping LLM reflection - PRAS already set confidence={existing_confidence:.2f}")
        # Generate default follow-ups if not already set
        if not existing_followups:
            existing_followups = _generate_default_followups(query, tools_used)
        return {
            'confidence': existing_confidence,
            'reflection': 'Confidence set by grounded synthesis',
            'follow_ups': existing_followups[:3],
            'next_action': 'format'
        }

    # For non-PRAS paths (legacy ReAct), use LLM reflection
    try:
        client = OpenAI()

        prompt = _format_reflection_prompt(query, answer, tools_used)

        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Use mini for reflection (cost)
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=300,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)

        logger.info(f"Reflection: confidence={result.get('confidence', 0):.2f}, complete={result.get('is_complete')}")

        return {
            'confidence': result.get('confidence', 0.7),
            'reflection': result.get('assessment', ''),
            'follow_ups': result.get('suggested_followups', [])[:3],
            'next_action': 'format'
        }

    except Exception as e:
        logger.error(f"Reflection error: {e}")

        # Default reflection on error
        return {
            'confidence': 0.6,
            'reflection': 'Unable to evaluate answer quality',
            'follow_ups': _generate_default_followups(query, tools_used),
            'next_action': 'format'
        }


def _format_reflection_prompt(query: str, answer: str, tools_used: list) -> str:
    """Format the reflection prompt."""

    tools_str = ", ".join(tools_used) if tools_used else "No tools used"

    return f"""Evaluate this answer before sending it to the user. Return your response as JSON.

## Original Query
{query}

## Generated Answer
{answer}

## Tools Used
{tools_str}

## Evaluation Criteria
1. **Completeness**: Does it fully address the query?
2. **Accuracy**: Is it grounded in the retrieved information?
3. **Clarity**: Is it easy to understand?
4. **Helpfulness**: Does it actually help the user?

## Response Format (JSON)
{{
    "confidence": 0.0-1.0,
    "is_complete": true/false,
    "is_accurate": true/false,
    "assessment": "Brief evaluation of the answer",
    "issues": ["Any issues found"],
    "suggested_followups": ["2-3 follow-up questions the user might find helpful"]
}}

Be honest but not overly critical. A score of 0.7+ is acceptable for most answers."""


def _generate_default_followups(query: str, tools_used: list) -> list:
    """Generate default follow-up suggestions."""
    followups = []

    query_lower = query.lower()

    # Session-related followups
    if 'session' in query_lower:
        followups.append("How did the collaboration quality compare to other sessions?")
        followups.append("What were the main themes discussed?")

    # Speaker-related followups
    elif any(word in query_lower for word in ['speaker', 'participant', 'who']):
        followups.append("How did other speakers contribute?")
        followups.append("What concepts did this speaker introduce?")

    # Topic-related followups
    elif any(word in query_lower for word in ['about', 'discuss', 'topic']):
        followups.append("Which sessions discussed similar topics?")
        followups.append("What conclusions were reached?")

    # Default followups
    else:
        followups.append("What other sessions might be relevant?")
        followups.append("Can you show me the concept map?")
        followups.append("How well did the group collaborate?")

    return followups[:3]
