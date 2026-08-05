"""
Comparison Tools for BLINC Agent V2

Tools for comparing sessions and speakers.
Adapted from existing tools with LangChain @tool decorator.
"""

import sys
import os
import logging
from typing import List, Dict, Optional, Any
from collections import Counter

from langchain_core.tools import tool

# Add server directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logger = logging.getLogger(__name__)


@tool
def compare_sessions(
    session_device_ids: List[int],
    comparison_type: str = "all"
) -> Dict[str, Any]:
    """
    Compare metrics, concepts, or participation patterns across multiple sessions.

    Returns structured comparison highlighting differences and similarities.
    Use this to understand how discussions differ across sessions.

    Args:
        session_device_ids: List of session device IDs to compare (2-5 sessions)
        comparison_type: Type of comparison:
            - 'metrics': Compare 7C collaboration scores
            - 'concepts': Compare concept map structures
            - 'participation': Compare speaker participation patterns
            - 'themes': Compare discussion themes
            - 'all': All of the above (default)

    Returns:
        Dict with comparison data for each dimension requested
    """
    try:
        if len(session_device_ids) < 2:
            return {
                "error": "Need at least 2 sessions to compare",
                "sessions": {}
            }

        if len(session_device_ids) > 5:
            session_device_ids = session_device_ids[:5]

        from tables.concept_session import ConceptSession
        from tables.seven_cs_analysis import SevenCsAnalysis
        from tables.transcript import Transcript

        result = {
            "session_device_ids": session_device_ids,
            "comparison_type": comparison_type,
            "sessions": {}
        }

        # Gather data for each session
        for sid in session_device_ids:
            session_data = {"session_device_id": sid}

            # Get concept session
            concept_session = ConceptSession.query.filter_by(
                session_device_id=sid
            ).first()

            if concept_session and comparison_type in ["all", "concepts", "themes"]:
                nodes = concept_session.nodes or []
                session_data["concept_data"] = {
                    "node_count": len(nodes),
                    "edge_count": len(concept_session.edges or []),
                    "discourse_type": concept_session.discourse_type,
                    "node_types": dict(Counter(n.node_type for n in nodes if n.node_type)),
                    "cluster_count": len(concept_session.clusters or []),
                    "cluster_names": [c.cluster_name for c in (concept_session.clusters or [])[:5]]
                }

            # Get 7C analysis
            if comparison_type in ["all", "metrics"]:
                seven_cs = SevenCsAnalysis.query.filter_by(
                    session_device_id=sid,
                    analysis_status='completed'
                ).first()

                if seven_cs and seven_cs.analysis_summary:
                    session_data["seven_c_scores"] = {
                        dim: seven_cs.analysis_summary.get(dim, {}).get('score', 0)
                        for dim in ['climate', 'communication', 'compatibility',
                                   'conflict', 'context', 'contribution', 'constructive']
                    }

            # Get participation data
            if comparison_type in ["all", "participation"]:
                transcripts = Transcript.query.filter_by(
                    session_device_id=sid
                ).all()

                speaker_counts = Counter(t.speaker_id for t in transcripts if t.speaker_id)
                session_data["participation"] = {
                    "transcript_count": len(transcripts),
                    "speaker_count": len(speaker_counts),
                    "speaker_distribution": dict(speaker_counts)
                }

            result["sessions"][sid] = session_data

        # Generate comparison insights
        if comparison_type in ["all", "metrics"]:
            result["metrics_comparison"] = _compare_metrics(result["sessions"])

        if comparison_type in ["all", "concepts"]:
            result["concepts_comparison"] = _compare_concepts(result["sessions"])

        if comparison_type in ["all", "participation"]:
            result["participation_comparison"] = _compare_participation(result["sessions"])

        return result

    except Exception as e:
        logger.error(f"Error comparing sessions: {e}")
        return {"error": str(e), "sessions": {}}


def _compare_metrics(sessions: Dict) -> Dict:
    """Compare 7C metrics across sessions."""
    comparisons = {}
    dimensions = ['climate', 'communication', 'compatibility',
                 'conflict', 'context', 'contribution', 'constructive']

    for dim in dimensions:
        scores = []
        for sid, data in sessions.items():
            if "seven_c_scores" in data:
                scores.append({
                    "session": sid,
                    "score": data["seven_c_scores"].get(dim, 0)
                })

        if scores:
            avg = sum(s["score"] for s in scores) / len(scores)
            comparisons[dim] = {
                "scores": scores,
                "average": round(avg, 1),
                "highest": max(scores, key=lambda x: x["score"]),
                "lowest": min(scores, key=lambda x: x["score"])
            }

    return comparisons


def _compare_concepts(sessions: Dict) -> Dict:
    """Compare concept map structures."""
    comparisons = {}

    node_counts = []
    discourse_types = {}

    for sid, data in sessions.items():
        if "concept_data" in data:
            cd = data["concept_data"]
            node_counts.append({
                "session": sid,
                "count": cd.get("node_count", 0)
            })
            dt = cd.get("discourse_type")
            if dt:
                discourse_types[sid] = dt

    if node_counts:
        comparisons["node_counts"] = {
            "values": node_counts,
            "max": max(node_counts, key=lambda x: x["count"]),
            "min": min(node_counts, key=lambda x: x["count"])
        }

    comparisons["discourse_types"] = discourse_types

    return comparisons


def _compare_participation(sessions: Dict) -> Dict:
    """Compare participation patterns across sessions."""
    comparisons = {}

    transcript_counts = []
    speaker_counts = []

    for sid, data in sessions.items():
        if "participation" in data:
            p = data["participation"]
            transcript_counts.append({
                "session": sid,
                "count": p.get("transcript_count", 0)
            })
            speaker_counts.append({
                "session": sid,
                "count": p.get("speaker_count", 0)
            })

    if transcript_counts:
        comparisons["transcript_counts"] = {
            "values": transcript_counts,
            "max": max(transcript_counts, key=lambda x: x["count"]),
            "min": min(transcript_counts, key=lambda x: x["count"])
        }

    if speaker_counts:
        comparisons["speaker_counts"] = {
            "values": speaker_counts,
            "max": max(speaker_counts, key=lambda x: x["count"]),
            "min": min(speaker_counts, key=lambda x: x["count"])
        }

    return comparisons


@tool
def compare_speakers(
    session_device_id: int,
    speaker_ids: Optional[List[int]] = None,
    comparison_aspects: List[str] = None
) -> Dict[str, Any]:
    """
    Compare speakers within a session or across sessions.

    Analyzes participation, linguistic patterns, and contribution types.

    Args:
        session_device_id: The session to analyze speakers in
        speaker_ids: Optional list of specific speaker IDs to compare.
                    If None, compares all speakers in the session.
        comparison_aspects: What to compare:
            - 'participation': Word counts, utterances
            - 'liwc': Emotional tone, analytic thinking, etc.
            - 'concepts': Concept contributions by type
            - 'all': All of the above (default)

    Returns:
        Dict with speaker comparison data
    """
    try:
        from tables.speaker import Speaker
        from tables.transcript import Transcript
        from tables.concept_node import ConceptNode
        from tables.concept_session import ConceptSession
        from sqlalchemy import func
        from app import db

        if comparison_aspects is None:
            comparison_aspects = ['all']

        result = {
            "session_device_id": session_device_id,
            "speakers": {}
        }

        # Get speakers for this session
        speaker_query = db.session.query(
            Speaker.id,
            Speaker.alias,
            func.count(Transcript.id).label('utterances'),
            func.sum(Transcript.word_count).label('total_words'),
            func.avg(Transcript.emotional_tone_value).label('avg_tone'),
            func.avg(Transcript.analytic_thinking_value).label('avg_analytic'),
            func.avg(Transcript.clout_value).label('avg_clout')
        ).join(
            Transcript, Transcript.speaker_id == Speaker.id
        ).filter(
            Transcript.session_device_id == session_device_id
        )

        if speaker_ids:
            speaker_query = speaker_query.filter(Speaker.id.in_(speaker_ids))

        speaker_query = speaker_query.group_by(Speaker.id, Speaker.alias)
        speakers = speaker_query.all()

        for speaker in speakers:
            speaker_data = {
                "speaker_id": speaker.id,
                "speaker_alias": speaker.alias
            }

            if 'all' in comparison_aspects or 'participation' in comparison_aspects:
                speaker_data["participation"] = {
                    "utterances": speaker.utterances,
                    "total_words": int(speaker.total_words or 0)
                }

            if 'all' in comparison_aspects or 'liwc' in comparison_aspects:
                speaker_data["liwc"] = {
                    "emotional_tone": round(float(speaker.avg_tone or 0), 2),
                    "analytic_thinking": round(float(speaker.avg_analytic or 0), 2),
                    "clout": round(float(speaker.avg_clout or 0), 2)
                }

            if 'all' in comparison_aspects or 'concepts' in comparison_aspects:
                # Get concept contributions
                concept_session = ConceptSession.query.filter_by(
                    session_device_id=session_device_id
                ).first()

                if concept_session:
                    nodes = ConceptNode.query.filter_by(
                        concept_session_id=concept_session.id,
                        speaker_id=speaker.id
                    ).all()

                    speaker_data["concepts"] = {
                        "total_contributions": len(nodes),
                        "by_type": dict(Counter(n.node_type for n in nodes if n.node_type))
                    }

            result["speakers"][speaker.id] = speaker_data

        # Add comparison summary
        if len(result["speakers"]) > 1:
            result["summary"] = _generate_speaker_comparison_summary(result["speakers"])

        return result

    except Exception as e:
        logger.error(f"Error comparing speakers: {e}")
        return {"error": str(e), "speakers": {}}


def _generate_speaker_comparison_summary(speakers: Dict) -> Dict:
    """Generate summary of speaker comparison."""
    summary = {}

    # Most active by words
    word_counts = [
        (sid, data.get("participation", {}).get("total_words", 0))
        for sid, data in speakers.items()
    ]
    if word_counts:
        most_active = max(word_counts, key=lambda x: x[1])
        least_active = min(word_counts, key=lambda x: x[1])
        summary["most_active_speaker"] = most_active[0]
        summary["least_active_speaker"] = least_active[0]

    # Highest emotional tone
    tone_scores = [
        (sid, data.get("liwc", {}).get("emotional_tone", 0))
        for sid, data in speakers.items()
    ]
    if tone_scores:
        highest_tone = max(tone_scores, key=lambda x: x[1])
        summary["highest_emotional_tone_speaker"] = highest_tone[0]

    # Most concepts contributed
    concept_counts = [
        (sid, data.get("concepts", {}).get("total_contributions", 0))
        for sid, data in speakers.items()
    ]
    if concept_counts:
        most_concepts = max(concept_counts, key=lambda x: x[1])
        summary["most_concepts_speaker"] = most_concepts[0]

    return summary
