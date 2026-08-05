"""
Verify Claims Node for BLINC Agent V3

Simplified heuristic-based verification:
- Counts validated vs unvalidated citations
- No LLM calls - fast and reliable
- Provides verification score for transparency

The grounded_synthesizer already validates citations against retrieval results.
This node aggregates those validation statuses into a summary.
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def verify_claims(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verify claims in the synthesized answer using citation validation.

    Heuristic approach (no LLM):
    - Check which citations are validated (have matching retrieval data)
    - Calculate verification score as % of validated citations

    Args:
        state: Current agent state with citations

    Returns:
        Updated state with verification results
    """
    citations = state.get('citations', [])
    route = state.get('route', '')

    # Skip for fast_path - simple queries don't need verification
    if route == 'fast_path':
        logger.info("Skipping verification: fast_path query")
        return _skip_result("fast_path query - verification not needed")

    # Skip if no citations to verify
    if not citations:
        logger.info("Skipping verification: no citations")
        return _skip_result("no citations to verify")

    # Count validated citations
    validated = []
    unvalidated = []

    for cite in citations:
        cite_info = {
            'claim': cite.get('referenceText', cite.get('reference_text', 'Unknown citation')),
            'source': cite.get('citationType', cite.get('citation_type', 'unknown')),
            'session_id': cite.get('artifactRef', cite.get('artifact_ref', {})).get('sessionId',
                          cite.get('artifactRef', cite.get('artifact_ref', {})).get('session_id'))
        }

        if cite.get('validated', False):
            cite_info['confidence'] = 0.9
            validated.append(cite_info)
        else:
            cite_info['reason'] = 'Citation not found in retrieval results'
            unvalidated.append(cite_info)

    total = len(citations)
    verified_count = len(validated)
    score = verified_count / total if total > 0 else 1.0

    logger.info(f"Verification complete: {verified_count}/{total} citations validated (score: {score:.2f})")

    return {
        'verification_result': {
            'verified_claims': validated,
            'unsupported_claims': unvalidated,
            'verification_score': score,
            'total_claims': total,
            'verified_count': verified_count,
            'skipped': False
        }
    }


def _skip_result(reason: str) -> Dict[str, Any]:
    """Return a skip result."""
    return {
        'verification_result': {
            'skipped': True,
            'skip_reason': reason,
            'verified_claims': [],
            'unsupported_claims': [],
            'verification_score': None,
            'total_claims': 0,
            'verified_count': 0
        }
    }


def format_verification_for_response(verification_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format verification results for inclusion in API response.

    Args:
        verification_result: Raw verification results

    Returns:
        Formatted verification summary
    """
    if verification_result.get('skipped'):
        return {
            'status': 'skipped',
            'reason': verification_result.get('skip_reason', 'verification skipped'),
            'score': None
        }

    verified = verification_result.get('verified_claims', [])
    unsupported = verification_result.get('unsupported_claims', [])

    return {
        'status': 'complete',
        'score': verification_result.get('verification_score', 0.0),
        'verified_count': len(verified),
        'total_claims': verification_result.get('total_claims', 0),
        'verified_claims': [
            {
                'claim': v['claim'][:100] + '...' if len(v.get('claim', '')) > 100 else v.get('claim', ''),
                'source': v.get('source', 'evidence'),
                'confidence': v.get('confidence', 0.8)
            }
            for v in verified[:5]
        ],
        'unsupported_claims': [
            {
                'claim': u['claim'][:100] + '...' if len(u.get('claim', '')) > 100 else u.get('claim', ''),
                'reason': u.get('reason', 'No evidence')[:50]
            }
            for u in unsupported[:3]
        ] if unsupported else []
    }
