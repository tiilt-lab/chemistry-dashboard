"""
Artifact Retrieval Tools for BLINC Agent V2

Tools for directly accessing discussion artifacts (concept maps, 7C analysis, etc.)
Adapted from existing tools with LangChain @tool decorator.
"""

import sys
import os
import logging
from typing import List, Dict, Optional, Any, Tuple

from langchain_core.tools import tool

# Add server directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logger = logging.getLogger(__name__)


@tool
def get_7c_analysis(session_device_id: int) -> Dict[str, Any]:
    """
    Get the 7C collaborative quality analysis for a session.

    Returns scores and evidence for all 7 dimensions of collaboration quality:
    - Climate: Emotional atmosphere and psychological safety
    - Communication: Quality of dialogue and information exchange
    - Compatibility: How well team members work together
    - Conflict: Level and nature of disagreements
    - Context: Shared understanding and background
    - Contribution: Balance of participation
    - Constructive: Productive problem-solving behaviors

    Args:
        session_device_id: The session device ID to get 7C analysis for

    Returns:
        Dict with 'dimensions' containing scores (0-100) and evidence for each dimension
    """
    try:
        from tables.seven_cs_analysis import SevenCsAnalysis

        analysis = SevenCsAnalysis.query.filter_by(
            session_device_id=session_device_id,
            analysis_status='completed'
        ).order_by(SevenCsAnalysis.created_at.desc()).first()

        if not analysis:
            return {
                "error": f"No 7C analysis found for session {session_device_id}",
                "dimensions": {}
            }

        # Format the analysis
        result = {
            "session_device_id": session_device_id,
            "analysis_status": analysis.analysis_status,
            "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
            "dimensions": {}
        }

        # Extract scores and details for each dimension
        dimensions = ['climate', 'communication', 'compatibility', 'conflict',
                     'context', 'contribution', 'constructive']

        if analysis.analysis_summary:
            for dim in dimensions:
                dim_data = analysis.analysis_summary.get(dim, {})
                result["dimensions"][dim] = {
                    "score": dim_data.get('score', 0),
                    "explanation": dim_data.get('explanation', ''),
                    "evidence": dim_data.get('evidence', [])[:3],  # Top 3 evidence
                    "keywords": dim_data.get('keywords_found', [])
                }

        return result

    except Exception as e:
        logger.error(f"Error getting 7C analysis: {e}")
        return {"error": str(e), "dimensions": {}}


@tool
def get_liwc_metrics(
    session_device_id: int,
    speaker_id: Optional[int] = None,
    time_range: Optional[Tuple[float, float]] = None
) -> Dict[str, Any]:
    """
    Get aggregated LIWC linguistic metrics for a session or speaker.

    LIWC metrics include:
    - Emotional tone: Positive vs negative emotional expression (0-100)
    - Analytical thinking: Formal, logical, hierarchical thinking (0-100)
    - Clout: Social status, confidence, leadership (0-100)
    - Authenticity: Honest, personal, disclosing (0-100)
    - Certainty: Confidence and definitiveness in language (0-100)

    Args:
        session_device_id: The session device ID to analyze
        speaker_id: Optional speaker ID to filter by
        time_range: Optional (start_time, end_time) tuple to filter

    Returns:
        Dict with aggregated LIWC metrics and optional speaker breakdown
    """
    try:
        from sqlalchemy import func
        from app import db
        from tables.transcript import Transcript

        query = db.session.query(
            func.avg(Transcript.emotional_tone_value).label('avg_emotional'),
            func.avg(Transcript.analytic_thinking_value).label('avg_analytic'),
            func.avg(Transcript.clout_value).label('avg_clout'),
            func.avg(Transcript.authenticity_value).label('avg_authenticity'),
            func.avg(Transcript.certainty_value).label('avg_certainty'),
            func.count(Transcript.id).label('transcript_count')
        ).filter(Transcript.session_device_id == session_device_id)

        if speaker_id:
            query = query.filter(Transcript.speaker_id == speaker_id)

        if time_range:
            start_time, end_time = time_range
            query = query.filter(
                Transcript.start_time >= start_time,
                (Transcript.start_time + Transcript.length) <= end_time
            )

        result = query.first()

        if not result or result.transcript_count == 0:
            return {
                "error": f"No transcripts found for session {session_device_id}",
                "metrics": {}
            }

        return {
            "session_device_id": session_device_id,
            "speaker_id": speaker_id,
            "time_range": time_range,
            "transcript_count": result.transcript_count,
            "metrics": {
                "emotional_tone": round(float(result.avg_emotional or 0), 2),
                "analytic_thinking": round(float(result.avg_analytic or 0), 2),
                "clout": round(float(result.avg_clout or 0), 2),
                "authenticity": round(float(result.avg_authenticity or 0), 2),
                "certainty": round(float(result.avg_certainty or 0), 2)
            }
        }

    except Exception as e:
        logger.error(f"Error getting LIWC metrics: {e}")
        return {"error": str(e), "metrics": {}}


@tool
def get_session_summary(session_device_id: int) -> Dict[str, Any]:
    """
    Get a comprehensive summary of a session including metadata, speakers, and key metrics.

    This is a quick overview tool that combines basic info from multiple sources.

    Args:
        session_device_id: The session device ID to summarize

    Returns:
        Dict with session name, speakers, duration, key metrics, and theme overview
    """
    try:
        from tables.session_device import SessionDevice
        from tables.session import Session
        from tables.transcript import Transcript
        from tables.concept_session import ConceptSession
        from tables.seven_cs_analysis import SevenCsAnalysis
        from sqlalchemy import func
        from app import db

        # Get session info
        sd = SessionDevice.query.get(session_device_id)
        if not sd:
            return {"error": f"Session {session_device_id} not found"}

        session = Session.query.get(sd.session_id)

        result = {
            "session_device_id": session_device_id,
            "session_id": sd.session_id,
            "session_name": session.name if session else f"Session {session_device_id}",
            "device_name": sd.name or ""
        }

        # Get speaker info with names
        from tables.speaker import Speaker

        speaker_data = db.session.query(
            func.count(func.distinct(Transcript.speaker_id)).label('speaker_count'),
            func.count(Transcript.id).label('transcript_count'),
            func.max(Transcript.start_time + Transcript.length).label('duration')
        ).filter(
            Transcript.session_device_id == session_device_id
        ).first()

        if speaker_data:
            result["speaker_count"] = speaker_data.speaker_count
            result["transcript_count"] = speaker_data.transcript_count
            result["duration_seconds"] = float(speaker_data.duration or 0)

        # Get actual speaker names
        speakers = db.session.query(
            Speaker.alias,
            func.count(Transcript.id).label('utterance_count'),
            func.sum(Transcript.word_count).label('word_count')
        ).join(
            Transcript, Transcript.speaker_id == Speaker.id
        ).filter(
            Transcript.session_device_id == session_device_id
        ).group_by(Speaker.id).all()

        if speakers:
            result["speakers"] = [
                {
                    "name": s.alias,
                    "utterance_count": s.utterance_count,
                    "word_count": int(s.word_count or 0)
                }
                for s in speakers
            ]

        # Get concept map info
        concept_session = ConceptSession.query.filter_by(
            session_device_id=session_device_id
        ).first()

        if concept_session:
            result["has_concept_map"] = True
            result["discourse_type"] = concept_session.discourse_type
            result["node_count"] = len(concept_session.nodes or [])
            result["cluster_count"] = len(concept_session.clusters or [])
            if concept_session.clusters:
                result["themes"] = [c.cluster_name for c in concept_session.clusters[:5]]
        else:
            result["has_concept_map"] = False

        # Get 7C highlights
        seven_cs = SevenCsAnalysis.query.filter_by(
            session_device_id=session_device_id,
            analysis_status='completed'
        ).first()

        if seven_cs and seven_cs.analysis_summary:
            summary = seven_cs.analysis_summary
            result["seven_c_highlights"] = {
                "communication": summary.get('communication', {}).get('score', 0),
                "climate": summary.get('climate', {}).get('score', 0),
                "contribution": summary.get('contribution', {}).get('score', 0)
            }

        return result

    except Exception as e:
        logger.error(f"Error getting session summary: {e}")
        return {"error": str(e)}
