"""
Cross-Representational Tools for BLINC Agent V3

These tools operate ACROSS representations, enabling:
1. Provenance tracing (artifact → source transcript)
2. Multi-representation evidence gathering
3. Unified speaker views
4. Evidence convergence checking
5. Gap identification

These support the PRAS architecture's cross-representation reasoning.
"""

import logging
from typing import Dict, Any, List, Optional

from .search_tools import search_transcripts, search_concepts
from .analysis_tools import get_collaboration_analysis, analyze_speaker, get_session_overview

logger = logging.getLogger(__name__)


def trace_to_transcript(
    artifact_type: str,
    artifact_id: str,
    session_id: int,
    artifact_text: str = None
) -> Dict[str, Any]:
    """
    Trace any artifact back to source transcript segments.

    Since we don't have explicit provenance links stored, use:
    - Semantic similarity (concept text → transcript search)
    - Speaker + timestamp proximity
    - Keyword overlap

    Args:
        artifact_type: "concept" | "7c_segment" | "cluster"
        artifact_id: The artifact identifier
        session_id: Session to search within
        artifact_text: Text content of the artifact (for semantic matching)

    Returns:
        {
            "artifact_type": str,
            "artifact_id": str,
            "source_segments": [transcript segments],
            "provenance_type": "inferred",  # vs "explicit" if we had stored links
            "confidence": float
        }
    """
    if not artifact_text:
        logger.warning(f"No artifact text provided for {artifact_type}:{artifact_id}")
        return {
            "artifact_type": artifact_type,
            "artifact_id": artifact_id,
            "source_segments": [],
            "provenance_type": "inferred",
            "confidence": 0.0,
            "error": "No artifact text provided"
        }

    # Search transcripts using artifact text
    try:
        transcript_results = search_transcripts(
            query=artifact_text,
            session_ids=[session_id],
            limit=5
        )

        source_segments = []
        for result in transcript_results.get('results', []):
            source_segments.append({
                "text": result.get('text', ''),
                "speaker": result.get('speaker', ''),
                "timestamp": result.get('timestamp', ''),
                "session_id": session_id,
                "match_type": "semantic"
            })

        # Calculate confidence based on result quality
        confidence = 0.0
        if source_segments:
            # Higher confidence if first result matches well
            confidence = min(0.8, len(source_segments) * 0.2)

        return {
            "artifact_type": artifact_type,
            "artifact_id": artifact_id,
            "source_segments": source_segments,
            "provenance_type": "inferred",
            "confidence": confidence
        }

    except Exception as e:
        logger.error(f"Error tracing artifact: {e}")
        return {
            "artifact_type": artifact_type,
            "artifact_id": artifact_id,
            "source_segments": [],
            "provenance_type": "inferred",
            "confidence": 0.0,
            "error": str(e)
        }


def get_multi_rep_evidence(
    query: str,
    session_id: int,
    representations: List[str] = None
) -> Dict[str, Any]:
    """
    Gather evidence from all representations in one call.

    This is a convenience tool that queries multiple representations
    in parallel and returns combined results.

    Args:
        query: Search query
        session_id: Session to search
        representations: List of reps to query (None = all)

    Returns:
        {
            "query": str,
            "session_id": int,
            "evidence_by_rep": {
                "transcript": [...],
                "concept_map": [...],
                "collaboration": {...},
                "speaker_profile": {...}
            },
            "quick_convergence_check": str
        }
    """
    all_reps = ["transcript", "concept_map", "collaboration", "session_overview"]
    reps_to_query = representations or all_reps

    evidence = {}
    errors = []

    # Query each representation
    if "transcript" in reps_to_query:
        try:
            result = search_transcripts(query=query, session_ids=[session_id], limit=5)
            evidence["transcript"] = result.get('results', [])
        except Exception as e:
            errors.append(f"transcript: {e}")
            evidence["transcript"] = []

    if "concept_map" in reps_to_query:
        try:
            result = search_concepts(query=query, session_ids=[session_id], limit=5)
            evidence["concept_map"] = result.get('results', [])
        except Exception as e:
            errors.append(f"concept_map: {e}")
            evidence["concept_map"] = []

    if "collaboration" in reps_to_query:
        try:
            result = get_collaboration_analysis(session_id=session_id)
            evidence["collaboration"] = result
        except Exception as e:
            errors.append(f"collaboration: {e}")
            evidence["collaboration"] = {}

    if "session_overview" in reps_to_query:
        try:
            result = get_session_overview(session_id=session_id)
            evidence["session_overview"] = result
        except Exception as e:
            errors.append(f"session_overview: {e}")
            evidence["session_overview"] = {}

    # Quick convergence check
    convergence = _quick_convergence_check(query, evidence)

    return {
        "query": query,
        "session_id": session_id,
        "evidence_by_rep": evidence,
        "representations_queried": reps_to_query,
        "quick_convergence_check": convergence,
        "errors": errors if errors else None
    }


def get_speaker_unified_view(
    speaker: str,
    session_id: int
) -> Dict[str, Any]:
    """
    Unified view of one speaker across all representations.

    Combines data from transcripts, concept maps, and collaboration
    to give a complete picture of a speaker's participation.

    Args:
        speaker: Speaker name
        session_id: Session ID

    Returns:
        {
            "speaker": str,
            "session_id": int,
            "transcript_summary": {...},
            "concept_summary": {...},
            "collaboration_summary": {...},
            "cross_rep_insights": [str]
        }
    """
    result = {
        "speaker": speaker,
        "session_id": session_id,
        "transcript_summary": {},
        "concept_summary": {},
        "collaboration_summary": {},
        "cross_rep_insights": []
    }

    # Get transcript data
    try:
        transcript_result = search_transcripts(
            query="",  # Get all for this speaker
            session_ids=[session_id],
            speaker=speaker,
            limit=20
        )
        quotes = transcript_result.get('results', [])
        result["transcript_summary"] = {
            "quote_count": len(quotes),
            "key_quotes": [q.get('text', '')[:100] for q in quotes[:3]],
            "word_count": sum(len(q.get('text', '').split()) for q in quotes)
        }
    except Exception as e:
        logger.error(f"Error getting transcript for {speaker}: {e}")

    # Get concept data
    try:
        concept_result = search_concepts(
            query=speaker,  # Search for speaker's concepts
            session_ids=[session_id],
            limit=20
        )
        concepts = concept_result.get('results', [])
        # Count concept types
        type_counts = {}
        for c in concepts:
            ctype = c.get('type', 'unknown')
            type_counts[ctype] = type_counts.get(ctype, 0) + 1

        result["concept_summary"] = {
            "concepts_count": len(concepts),
            "concept_types": type_counts,
            "key_concepts": [c.get('text', '')[:50] for c in concepts[:3]]
        }
    except Exception as e:
        logger.error(f"Error getting concepts for {speaker}: {e}")

    # Get collaboration data
    try:
        collab_result = get_collaboration_analysis(session_id=session_id)
        # Extract speaker-relevant info from 7C
        result["collaboration_summary"] = {
            "communication_score": collab_result.get('dimensions', {}).get('Communication', {}).get('score', 0),
            "contribution_score": collab_result.get('dimensions', {}).get('Contribution', {}).get('score', 0),
            "constructive_score": collab_result.get('dimensions', {}).get('Constructive', {}).get('score', 0)
        }
    except Exception as e:
        logger.error(f"Error getting collaboration for {speaker}: {e}")

    # Generate cross-rep insights
    result["cross_rep_insights"] = _generate_speaker_insights(result)

    return result


def check_evidence_convergence(
    claim: str,
    evidence_items: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Analyze whether evidence items converge or conflict.

    Args:
        claim: The claim being evaluated
        evidence_items: List of evidence with 'rep' and 'finding' keys

    Returns:
        {
            "claim": str,
            "convergence_score": float (0-1),
            "analysis": {
                "supporting": [...],
                "neutral": [...],
                "conflicting": [...]
            },
            "interpretation": str
        }
    """
    # Simple heuristic-based convergence check
    supporting = []
    neutral = []
    conflicting = []

    claim_words = set(claim.lower().split())

    for item in evidence_items:
        rep = item.get('rep', 'unknown')
        finding = item.get('finding', '')
        finding_lower = finding.lower()

        # Check for supporting indicators
        if any(word in finding_lower for word in ['supports', 'confirms', 'shows', 'demonstrates']):
            supporting.append(item)
        # Check for conflicting indicators
        elif any(word in finding_lower for word in ['contradicts', 'conflicts', 'however', 'but']):
            conflicting.append(item)
        else:
            # Check word overlap
            finding_words = set(finding_lower.split())
            overlap = len(claim_words & finding_words) / max(len(claim_words), 1)
            if overlap > 0.3:
                supporting.append(item)
            else:
                neutral.append(item)

    # Calculate convergence score
    total = len(evidence_items)
    if total == 0:
        convergence_score = 0.0
    else:
        support_weight = len(supporting) * 1.0
        conflict_weight = len(conflicting) * -1.0
        convergence_score = max(0.0, min(1.0, (support_weight + conflict_weight + total) / (total * 2)))

    # Generate interpretation
    if len(conflicting) > 0:
        interpretation = f"Mixed evidence: {len(supporting)} supporting, {len(conflicting)} conflicting findings."
    elif len(supporting) > 1:
        interpretation = f"Converging evidence from {len(supporting)} sources."
    elif len(supporting) == 1:
        interpretation = "Single source of evidence."
    else:
        interpretation = "No clear supporting evidence found."

    return {
        "claim": claim,
        "convergence_score": convergence_score,
        "analysis": {
            "supporting": supporting,
            "neutral": neutral,
            "conflicting": conflicting
        },
        "interpretation": interpretation
    }


def find_representation_gaps(
    query: str,
    retrieved_evidence: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Identify what representations might answer aspects of the query
    that aren't covered by current evidence.

    Args:
        query: The user's query
        retrieved_evidence: Evidence already retrieved, keyed by rep type

    Returns:
        {
            "query_aspects": [str],
            "covered_by": {aspect: [reps]},
            "gaps": [
                {
                    "aspect": str,
                    "could_use": "representation",
                    "suggested_tool": "tool_name",
                    "suggested_params": {...}
                }
            ]
        }
    """
    # Identify query aspects using simple keyword analysis
    query_lower = query.lower()

    aspects = []
    aspect_to_rep = {
        "said": ["transcript"],
        "quote": ["transcript"],
        "discuss": ["transcript", "concept_map"],
        "concept": ["concept_map"],
        "idea": ["concept_map"],
        "collaborate": ["collaboration"],
        "participation": ["collaboration", "speaker_profile"],
        "communication": ["collaboration"],
        "speaker": ["speaker_profile", "transcript"],
        "session": ["session_overview"],
        "compare": ["comparison"],
        "theme": ["community", "concept_map"]
    }

    # Find which aspects are in the query
    for aspect, reps in aspect_to_rep.items():
        if aspect in query_lower:
            aspects.append({"aspect": aspect, "relevant_reps": reps})

    # Check which are covered
    covered_by = {}
    gaps = []
    retrieved_reps = set(retrieved_evidence.keys())

    for aspect_info in aspects:
        aspect = aspect_info["aspect"]
        relevant_reps = aspect_info["relevant_reps"]
        covered = [r for r in relevant_reps if r in retrieved_reps]

        if covered:
            covered_by[aspect] = covered
        else:
            # This is a gap
            suggested_rep = relevant_reps[0]
            gaps.append({
                "aspect": aspect,
                "could_use": suggested_rep,
                "suggested_tool": _rep_to_tool(suggested_rep),
                "reason": f"Query mentions '{aspect}' but no {suggested_rep} evidence retrieved"
            })

    return {
        "query_aspects": [a["aspect"] for a in aspects],
        "covered_by": covered_by,
        "gaps": gaps,
        "uncovered_aspects": [g["aspect"] for g in gaps]
    }


def _quick_convergence_check(query: str, evidence: Dict[str, List]) -> str:
    """Generate a quick convergence assessment."""
    reps_with_results = []

    if evidence.get("transcript"):
        reps_with_results.append("transcript")
    if evidence.get("concept_map"):
        reps_with_results.append("concept_map")
    if evidence.get("collaboration"):
        reps_with_results.append("collaboration")

    if len(reps_with_results) == 0:
        return "No evidence found across representations."
    elif len(reps_with_results) == 1:
        return f"Evidence found in {reps_with_results[0]} only."
    else:
        return f"Evidence found across {len(reps_with_results)} representations: {', '.join(reps_with_results)}."


def _generate_speaker_insights(speaker_data: Dict) -> List[str]:
    """Generate cross-representation insights about a speaker."""
    insights = []

    transcript = speaker_data.get("transcript_summary", {})
    concepts = speaker_data.get("concept_summary", {})
    collab = speaker_data.get("collaboration_summary", {})

    # Check for quality vs quantity patterns
    quote_count = transcript.get("quote_count", 0)
    concept_count = concepts.get("concepts_count", 0)
    comm_score = collab.get("communication_score", 0)

    if quote_count > 10 and comm_score < 50:
        insights.append("High verbosity but lower communication quality score - may indicate one-way communication.")

    if concept_count > 5 and quote_count < 5:
        insights.append("Fewer direct quotes but multiple concepts attributed - contributions may be synthesized from discussion.")

    if collab.get("constructive_score", 0) > 70 and concept_count > 3:
        insights.append("High constructive score with multiple concepts - actively building on discussion.")

    if not insights:
        insights.append(f"Speaker contributed {quote_count} quotes and {concept_count} concepts.")

    return insights


def _rep_to_tool(rep: str) -> str:
    """Map representation to primary tool."""
    mapping = {
        "transcript": "search_transcripts",
        "concept_map": "search_concepts",
        "collaboration": "get_collaboration_analysis",
        "speaker_profile": "analyze_speaker",
        "session_overview": "get_session_overview",
        "community": "search_communities",
        "comparison": "compare_sessions"
    }
    return mapping.get(rep, "search_transcripts")
