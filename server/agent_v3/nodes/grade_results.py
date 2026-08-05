"""
Grade Results Node for BLINC Agent V3

Implements Self-RAG / CRAG style document grading.
Evaluates relevance of retrieved documents and decides
whether to proceed or rewrite the query.
"""

import json
import logging
from typing import Dict, Any

from openai import OpenAI

logger = logging.getLogger(__name__)


def grade_results(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Grade the relevance of retrieved documents.

    This node:
    1. Evaluates each document's relevance to the query
    2. Assigns relevance scores
    3. Decides whether to proceed or rewrite the query

    Implements CRAG (Corrective RAG) pattern.

    Args:
        state: Current agent state with retrieval_results

    Returns:
        Updated state with grading decision
    """
    query = state.get('current_query', state.get('original_query', ''))
    results = state.get('retrieval_results', [])

    if not results:
        logger.info("No results to grade")
        return {
            'next_action': 'continue',
            'grading_result': {
                'overall_relevant': False,
                'should_rewrite': True,
                'reason': 'No results retrieved'
            }
        }

    # Get the latest result
    latest_result = results[-1] if results else {}
    documents = latest_result.get('results', [])
    tool_name = latest_result.get('tool_name', '')

    # If tool already marked results as relevant, trust it
    # This is especially important for structured results like compare_sessions
    if latest_result.get('is_relevant', False):
        logger.info(f"Results from {tool_name} marked as relevant by tool, skipping grading")
        return {
            'next_action': 'continue',
            'grading_result': {
                'overall_relevant': True,
                'should_rewrite': False,
                'method': 'tool_marking',
                'reason': f'{tool_name} marked results as relevant'
            }
        }

    if not documents:
        logger.info("Empty results, should rewrite")
        return {
            'next_action': 'rewrite',
            'grading_result': {
                'overall_relevant': False,
                'should_rewrite': True,
                'reason': 'No documents in results'
            }
        }

    # Quick check based on distance scores if available
    distances = [d.get('distance', 0.5) for d in documents if 'distance' in d]
    if distances:
        avg_distance = sum(distances) / len(distances)
        best_distance = min(distances)

        # If best result is very close, likely relevant
        if best_distance < 0.4:
            logger.info(f"Results look relevant based on distance: {best_distance:.2f}")
            return {
                'next_action': 'continue',
                'grading_result': {
                    'overall_relevant': True,
                    'relevance_score': 1 - best_distance,
                    'should_rewrite': False,
                    'method': 'distance_check'
                }
            }

        # If all results are far, likely irrelevant
        if best_distance > 0.75:
            rewrite_count = state.get('rewrite_count', 0)
            max_rewrites = state.get('max_rewrites', 2)

            if rewrite_count < max_rewrites:
                logger.info(f"Results look irrelevant (distance: {best_distance:.2f}), suggesting rewrite")
                return {
                    'next_action': 'rewrite',
                    'grading_result': {
                        'overall_relevant': False,
                        'relevance_score': 1 - best_distance,
                        'should_rewrite': True,
                        'method': 'distance_check',
                        'reason': 'High distance scores suggest irrelevant results'
                    }
                }

    # For borderline cases, use LLM grading
    try:
        grading = _llm_grade_results(query, documents)
        logger.info(f"LLM grading result: relevant={grading.get('overall_relevant')}, score={grading.get('relevance_score', 0):.2f}")

        if grading.get('should_rewrite', False):
            rewrite_count = state.get('rewrite_count', 0)
            max_rewrites = state.get('max_rewrites', 2)

            if rewrite_count < max_rewrites:
                return {
                    'next_action': 'rewrite',
                    'grading_result': grading
                }

        return {
            'next_action': 'continue',
            'grading_result': grading
        }

    except Exception as e:
        logger.error(f"LLM grading error: {e}")
        # On error, proceed with what we have
        return {
            'next_action': 'continue',
            'grading_result': {
                'overall_relevant': True,  # Assume relevant on error
                'error': str(e)
            }
        }


def _llm_grade_results(query: str, documents: list) -> Dict[str, Any]:
    """Use LLM to grade document relevance."""
    from ..prompts.grading import format_grading_prompt

    client = OpenAI()

    prompt = format_grading_prompt(query, documents)

    response = client.chat.completions.create(
        model="gpt-4o-mini",  # Use mini for grading (cost efficiency)
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=300,
        response_format={"type": "json_object"}
    )

    result = json.loads(response.choices[0].message.content)
    result['method'] = 'llm_grading'

    return result
