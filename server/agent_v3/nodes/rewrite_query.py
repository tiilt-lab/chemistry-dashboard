"""
Rewrite Query Node for BLINC Agent V3

Implements query rewriting when retrieval fails.
Part of the CRAG (Corrective RAG) pattern.
"""

import json
import logging
from typing import Dict, Any

from openai import OpenAI

logger = logging.getLogger(__name__)


REWRITE_PROMPT = """You are helping improve a search query for a discussion analysis system. Return your response as JSON.

The original query didn't retrieve relevant results. Rewrite it to be more effective.

## Original Query
{query}

## Problem
{problem}

## Context
{context}

## Available Data
The system contains:
- Discussion transcripts (what people said)
- Concept maps (ideas, questions, hypotheses, and their connections)
- Collaboration metrics (7C scores for teamwork quality)
- Speaker profiles (participation patterns)

Sessions available: Living in NYC, Is AI Alive, Nuclear Fusion, Shaw Interview, Collaboration Literacy, Dinosaurs, Country Music, Abundance

## Instructions
Rewrite the query to be more likely to find relevant content.

Consider:
1. Using more specific or alternative terms
2. Focusing on the core intent
3. Breaking complex queries into simpler parts
4. Adding context that might help retrieval

## Response Format
{{
    "rewritten_query": "The improved search query",
    "reasoning": "Why this rewrite might work better",
    "alternative_approach": "Optional: A different tool or approach to try"
}}
"""


def rewrite_query(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Rewrite the query to improve retrieval.

    This node:
    1. Analyzes why retrieval failed
    2. Rewrites the query with better terms
    3. Increments rewrite counter

    Args:
        state: Current agent state

    Returns:
        Updated state with rewritten query
    """
    original_query = state.get('original_query', '')
    current_query = state.get('current_query', original_query)
    rewrite_count = state.get('rewrite_count', 0) + 1
    grading_result = state.get('grading_result', {})

    logger.info(f"Rewriting query (attempt {rewrite_count}): '{current_query}'")

    # Build context
    context_lines = []
    if state.get('current_session_focus'):
        context_lines.append(f"Session focus: {state['current_session_focus']}")
    if state.get('current_speaker_focus'):
        context_lines.append(f"Speaker focus: {state['current_speaker_focus']}")

    context_str = "\n".join(context_lines) if context_lines else "No specific context"

    # Get problem description from grading
    problem = grading_result.get('reason') or grading_result.get('assessment') or "Results were not relevant to the query"

    try:
        client = OpenAI()

        prompt = REWRITE_PROMPT.format(
            query=current_query,
            problem=problem,
            context=context_str
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Use mini for rewriting
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,  # Slight creativity for alternatives
            max_tokens=200,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)
        rewritten = result.get('rewritten_query', current_query)

        logger.info(f"Query rewritten to: '{rewritten}'")

        return {
            'current_query': rewritten,
            'rewrite_count': rewrite_count,
            'next_action': 'continue',
            'thought_history': state.get('thought_history', []) + [
                f"Rewrote query: '{current_query}' -> '{rewritten}' ({result.get('reasoning', '')})"
            ]
        }

    except Exception as e:
        logger.error(f"Query rewrite error: {e}")

        # On error, try simple modifications
        rewritten = _simple_rewrite(current_query)

        return {
            'current_query': rewritten,
            'rewrite_count': rewrite_count,
            'next_action': 'continue',
            'error': str(e)
        }


def _simple_rewrite(query: str) -> str:
    """Simple rule-based query rewriting as fallback."""
    # Remove question words
    for word in ['what', 'how', 'why', 'when', 'where', 'who', 'which']:
        if query.lower().startswith(word + ' '):
            query = query[len(word) + 1:]
            break

    # Remove filler phrases
    fillers = [
        'can you tell me about',
        'i want to know about',
        'tell me about',
        'show me',
        'find',
        'search for'
    ]
    query_lower = query.lower()
    for filler in fillers:
        if query_lower.startswith(filler):
            query = query[len(filler):].strip()
            break

    return query.strip()
