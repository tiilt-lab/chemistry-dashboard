"""
Format Response Node for BLINC Agent V3

Formats the final response for the API.

Enhancement: Reasoning Transparency
- Includes reasoning_trace showing how the system arrived at the answer
- Includes verification results for source attribution
- Includes diagnostic reasoning for causal queries

Enhancement: Clickable Citations
- Converts Citation objects to frontend-friendly format (camelCase)
- Enriches citations with preview data from retrieval results
"""

import logging
from typing import Dict, Any, List, Optional

from .verify_claims import format_verification_for_response

logger = logging.getLogger(__name__)


def format_response(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format the final response for the API.

    This node:
    1. Packages the answer with metadata
    2. Includes citations and follow-ups
    3. Preserves session context for multi-turn
    4. Handles clarification requests

    Args:
        state: Current agent state

    Returns:
        Final state with formatted response
    """
    logger.info("Formatting final response")

    # Check if this is a clarification request
    if state.get('next_action') == 'clarify':
        return _format_clarification(state)

    # === FIX: Extract session focus from retrieval results if not in state ===
    # This ensures multi-turn context is preserved even if earlier nodes didn't propagate it
    current_session_focus = state.get('current_session_focus')
    if current_session_focus is None:
        current_session_focus = _extract_session_focus_from_results(state)

    # Build reasoning trace for transparency
    reasoning_trace = _build_reasoning_trace(state)

    # Format verification results
    verification = None
    verification_result = state.get('verification_result')
    if verification_result:
        try:
            verification = format_verification_for_response(verification_result)
        except Exception as e:
            logger.error(f"Error formatting verification: {e}")
            verification = {'status': 'error', 'error': str(e)}

    # Process and enrich citations for frontend
    raw_citations = state.get('citations', [])
    enriched_citations = _enrich_and_format_citations(raw_citations, state)
    logger.info(f"Formatted {len(enriched_citations)} citations for response")

    # Format normal response
    return {
        # The answer
        'final_answer': state.get('final_answer', ''),

        # Metadata
        'confidence': state.get('confidence', 0.0),
        'reflection': state.get('reflection', ''),

        # Evidence - using enriched citations
        'citations': enriched_citations,
        'tools_used': state.get('tools_used', []),

        # Reasoning transparency (AIED 2026 enhancement)
        'reasoning_trace': reasoning_trace,
        'verification': verification,

        # Follow-ups
        'follow_ups': state.get('follow_ups', []),

        # Context to preserve for multi-turn (use extracted session focus)
        'current_session_focus': current_session_focus,
        'previous_session_focus': state.get('previous_session_focus'),
        'session_history': state.get('session_history', []),
        'compared_sessions': state.get('compared_sessions', []),
        'current_speaker_focus': state.get('current_speaker_focus'),

        # Debug info
        'thought_history': state.get('thought_history', []),
        'iteration_count': state.get('iteration_count', 0),
        'rewrite_count': state.get('rewrite_count', 0),

        # Status
        'success': True,
        'needs_clarification': False,
        'error': state.get('error')
    }


def _format_clarification(state: Dict[str, Any]) -> Dict[str, Any]:
    """Format a clarification request response."""
    question = state.get('clarification_question', 'Could you please clarify your question?')
    options = state.get('clarification_options', [])

    # Build clarification answer
    answer = question
    if options:
        answer += "\n\nOptions:\n"
        for i, opt in enumerate(options, 1):
            answer += f"{i}. {opt}\n"

    return {
        'final_answer': answer,
        'confidence': 0.0,
        'citations': [],
        'tools_used': state.get('tools_used', []),
        'reasoning_trace': None,
        'verification': None,
        'follow_ups': options,  # Options as follow-ups for easy selection

        # Context preserved
        'current_session_focus': state.get('current_session_focus'),
        'previous_session_focus': state.get('previous_session_focus'),
        'session_history': state.get('session_history', []),
        'compared_sessions': state.get('compared_sessions', []),
        'current_speaker_focus': state.get('current_speaker_focus'),

        # Status
        'success': True,
        'needs_clarification': True,
        'error': None
    }


def _build_reasoning_trace(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build reasoning trace for transparency.

    This shows users HOW the system arrived at the answer,
    aligned with AIED theme "From tools to teammates".

    Args:
        state: Current agent state

    Returns:
        Reasoning trace with approach, evidence sources, hypotheses (if diagnostic)
    """
    trace = {
        'approach': _determine_approach(state),
        'query_understanding': state.get('original_query', ''),
    }

    # Add evidence sources
    evidence_sources = []
    for result in state.get('retrieval_results', []):
        if isinstance(result, dict) and result.get('is_relevant', True):
            tool_name = result.get('tool_name', 'unknown')
            # Extract a brief finding summary
            finding = _summarize_finding(result)
            if finding:
                evidence_sources.append({
                    'tool': tool_name,
                    'finding': finding
                })

    trace['evidence_sources'] = evidence_sources[:5]  # Limit to top 5

    # Add diagnostic reasoning if present
    diagnostic_reasoning = state.get('diagnostic_reasoning')
    if diagnostic_reasoning:
        trace['diagnostic'] = {
            'hypotheses_considered': _format_hypotheses_for_trace(state),
            'primary_conclusion': state.get('primary_hypothesis'),
            'contributing_factors': state.get('contributing_factors', [])
        }

    # Add verification summary
    verification = state.get('verification_result')
    if verification and not verification.get('skipped'):
        trace['verification'] = {
            'claims_verified': verification.get('verified_count', 0),
            'claims_total': verification.get('total_claims', 0),
            'score': verification.get('verification_score', 0.0)
        }

    return trace


def _determine_approach(state: Dict[str, Any]) -> str:
    """Determine which reasoning approach was used."""
    if state.get('diagnostic_reasoning'):
        return 'diagnostic'
    elif state.get('query_plan'):
        return 'analytical'
    elif state.get('fast_path_tool'):
        return 'fast_path'
    else:
        return 'reasoning'


def _summarize_finding(result: Dict[str, Any]) -> Optional[str]:
    """Extract a brief finding summary from a tool result."""
    # For different result types, extract key info
    if 'summary' in result:
        return result['summary'][:100] if len(result.get('summary', '')) > 100 else result.get('summary')

    if 'results' in result and result['results']:
        first_result = result['results'][0]
        if isinstance(first_result, dict):
            # Try different keys
            for key in ['text', 'content', 'summary', 'finding']:
                if key in first_result:
                    text = str(first_result[key])
                    return text[:100] + '...' if len(text) > 100 else text

    return None


def _format_hypotheses_for_trace(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Format hypotheses for the reasoning trace."""
    hypotheses = state.get('hypotheses', [])
    scores = state.get('hypothesis_scores', {})

    formatted = []
    for h in hypotheses:
        # Get hypothesis ID - try 'id' first, then generate from hypothesis text
        h_id = h.get('id', h.get('hypothesis', '')[:20])
        score_info = scores.get(h_id, {})
        formatted.append({
            'hypothesis': h.get('hypothesis', ''),  # Changed from 'description'
            'confidence': score_info.get('score', 0.0),  # Changed from 'confidence'
            'support_level': score_info.get('verdict', 'unknown')  # Changed from 'support_level'
        })

    return formatted[:4]  # Limit to top 4


# =============================================================================
# Citation Enrichment Functions
# =============================================================================

def _enrich_and_format_citations(
    citations: List[Dict[str, Any]],
    state: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Enrich citations with additional data and convert to frontend format.

    This function:
    1. Enriches citations with preview data from retrieval results
    2. Converts snake_case keys to camelCase for frontend
    3. Ensures all required fields are present

    Args:
        citations: Raw citation objects from grounded_synthesizer
        state: Agent state with retrieval results

    Returns:
        List of formatted citations ready for frontend
    """
    if not citations:
        return []

    # Build lookup map from retrieval results for enrichment
    retrieval_lookup = _build_retrieval_lookup(state.get('retrieval_results', []))

    formatted_citations = []
    for citation in citations:
        try:
            # Handle both dict and TypedDict citations
            if hasattr(citation, 'get'):
                formatted = _format_single_citation(citation, retrieval_lookup)
            else:
                # It's already a dict-like object
                formatted = _format_single_citation(dict(citation), retrieval_lookup)

            if formatted:
                formatted_citations.append(formatted)
        except Exception as e:
            logger.warning(f"Error formatting citation: {e}")
            continue

    return formatted_citations


def _build_retrieval_lookup(retrieval_results: List[Dict]) -> Dict[str, Dict]:
    """
    Build a lookup map from retrieval results for citation enrichment.

    Maps session_id + speaker combinations to their retrieved data.
    """
    lookup = {}

    for result in retrieval_results:
        if not isinstance(result, dict):
            continue

        results_list = result.get('results', [])
        for item in results_list:
            if not isinstance(item, dict):
                continue

            # Build lookup keys
            session_id = item.get('session_id') or item.get('session')
            speaker = item.get('speaker')

            if session_id and speaker:
                key = f"transcript:{session_id}:{speaker}"
                if key not in lookup:
                    lookup[key] = item

            # Concept lookup
            concept_text = item.get('text', '')[:50] if item.get('type') in ['idea', 'hypothesis', 'question'] else None
            if concept_text:
                key = f"concept:{concept_text}"
                if key not in lookup:
                    lookup[key] = item

    return lookup


def _format_single_citation(
    citation: Dict[str, Any],
    retrieval_lookup: Dict[str, Dict]
) -> Optional[Dict[str, Any]]:
    """
    Format a single citation to frontend-friendly format.

    Converts snake_case to camelCase and ensures all required fields exist.
    """
    if not citation:
        return None

    # Get basic fields
    citation_id = citation.get('id', '')
    citation_type = citation.get('citation_type', 'transcript')
    inline_text = citation.get('inline_text', '')
    reference_text = citation.get('reference_text', inline_text)

    # Get artifact reference
    artifact_ref = citation.get('artifact_ref', {})
    if not isinstance(artifact_ref, dict):
        artifact_ref = {}

    # Get preview
    preview = citation.get('preview', {})
    if not isinstance(preview, dict):
        preview = {}

    # Try to enrich from retrieval lookup if preview is sparse
    if not preview.get('content'):
        enriched = _enrich_from_lookup(citation_type, artifact_ref, retrieval_lookup)
        if enriched:
            preview = {**preview, **enriched}

    # Format to camelCase for frontend
    formatted = {
        'id': citation_id,
        'citationType': citation_type,
        'inlineText': inline_text,
        'referenceText': reference_text,
        'artifactRef': {
            'sessionId': artifact_ref.get('session_id'),
            'speaker': artifact_ref.get('speaker'),
            'conceptId': artifact_ref.get('concept_id'),
            'dimension': artifact_ref.get('dimension'),
            'clusterId': artifact_ref.get('cluster_id'),
            'timestamp': artifact_ref.get('timestamp'),
            # Also include sessions array for comparison citations
            'sessions': artifact_ref.get('sessions')
        },
        'preview': {
            'title': preview.get('title', ''),
            'content': preview.get('content', ''),
            'metadata': preview.get('metadata', {})
        },
        # Grounding fields - these make the paper claim defensible
        'sourceChunkId': citation.get('source_chunk_id'),
        'validated': citation.get('validated', False)
    }

    # Clean up None values in artifactRef
    formatted['artifactRef'] = {
        k: v for k, v in formatted['artifactRef'].items() if v is not None
    }

    return formatted


def _extract_session_focus_from_results(state: Dict[str, Any]) -> Optional[int]:
    """
    Extract session focus from retrieval results when not in state.

    This ensures multi-turn context is preserved even if earlier nodes
    didn't propagate the session focus properly.

    Returns:
        Session ID if a single session is evident, None otherwise
    """
    retrieval_results = state.get('retrieval_results', [])
    fast_path_args = state.get('fast_path_args', {})

    # First check fast_path_args - most direct source
    if fast_path_args and fast_path_args.get('session_id'):
        session_id = fast_path_args['session_id']
        logger.info(f"Extracted session focus from fast_path_args: {session_id}")
        return session_id

    # Extract session IDs from retrieval results
    session_ids = set()
    for result in retrieval_results:
        if not isinstance(result, dict):
            continue

        # Check tool_name for session-specific tools
        tool_name = result.get('tool_name', '')
        if tool_name in ('get_session_overview', 'get_collaboration_analysis', 'get_7c_analysis'):
            # These tools have session_id in their direct results
            for item in result.get('results', []):
                if isinstance(item, dict):
                    sid = item.get('session_device_id') or item.get('session_id')
                    if sid:
                        session_ids.add(sid)

        # Check all results for session references
        for item in result.get('results', []):
            if isinstance(item, dict):
                sid = item.get('session_device_id') or item.get('session_id')
                if sid:
                    session_ids.add(sid)

    # Only set focus if there's exactly one session
    if len(session_ids) == 1:
        session_id = list(session_ids)[0]
        logger.info(f"Extracted session focus from retrieval results: {session_id}")
        return session_id

    # Check grounded_claims for session references
    grounded_claims = state.get('grounded_claims', [])
    for claim in grounded_claims:
        if isinstance(claim, dict):
            for grounding in claim.get('grounding', []):
                if isinstance(grounding, dict):
                    sid = grounding.get('session_id')
                    if sid:
                        session_ids.add(sid)

    if len(session_ids) == 1:
        session_id = list(session_ids)[0]
        logger.info(f"Extracted session focus from grounded_claims: {session_id}")
        return session_id

    if session_ids:
        logger.info(f"Multiple sessions in results ({session_ids}), not setting single focus")

    return None


def _enrich_from_lookup(
    citation_type: str,
    artifact_ref: Dict[str, Any],
    retrieval_lookup: Dict[str, Dict]
) -> Optional[Dict[str, Any]]:
    """
    Try to enrich citation preview from retrieval results.

    Args:
        citation_type: Type of citation
        artifact_ref: Artifact reference data
        retrieval_lookup: Lookup map from retrieval results

    Returns:
        Enriched preview data or None
    """
    session_id = artifact_ref.get('session_id')
    speaker = artifact_ref.get('speaker')
    concept_id = artifact_ref.get('concept_id')

    lookup_key = None

    if citation_type == 'transcript' and session_id and speaker:
        lookup_key = f"transcript:{session_id}:{speaker}"
    elif citation_type == 'concept' and concept_id:
        lookup_key = f"concept:{concept_id[:50]}"

    if lookup_key and lookup_key in retrieval_lookup:
        item = retrieval_lookup[lookup_key]
        return {
            'content': item.get('text', item.get('content', ''))[:300],
            'title': f"{speaker} - Session {session_id}" if speaker else 'Reference'
        }

    return None
