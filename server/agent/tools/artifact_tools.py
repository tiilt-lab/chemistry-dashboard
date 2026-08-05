"""
Artifact Retrieval Tools

Tools for directly accessing discussion artifacts (concept maps, 7C analysis, etc.)
"""

import logging
from typing import Dict, List, Optional, Tuple

from .base import BaseTool, ToolResult, ParameterSpec, ToolCategory
from .search_tools import get_session_display_names

logger = logging.getLogger(__name__)


class GetFullConceptMapTool(BaseTool):
    """Get complete concept map for a session."""

    name = "get_full_concept_map"
    description = (
        "Get the complete concept map structure for a session including all "
        "nodes, edges, and clusters. Use this when you need the full picture "
        "of how ideas connect in a discussion."
    )
    category = ToolCategory.ARTIFACT
    parameters = {
        "session_device_id": ParameterSpec(
            name="session_device_id",
            type="int",
            description="The session device ID to get concept map for",
            required=True
        ),
        "include_clusters": ParameterSpec(
            name="include_clusters",
            type="bool",
            description="Whether to include cluster assignments",
            required=False,
            default=True
        )
    }

    def execute(self, session_device_id: int,
                include_clusters: bool = True) -> ToolResult:
        """Get the full concept map."""
        try:
            from tables.concept_session import ConceptSession
            import database as db_helper

            # Get concept session
            concept_session = ConceptSession.query.filter_by(
                session_device_id=session_device_id
            ).first()

            if not concept_session:
                return ToolResult(
                    success=False,
                    data=None,
                    error=f"No concept map found for session {session_device_id}"
                )

            # Get all nodes and edges
            nodes = db_helper.get_concept_nodes(
                concept_session_id=concept_session.id
            )
            edges = db_helper.get_concept_edges(
                concept_session_id=concept_session.id
            )

            # Get session and device display names
            names = get_session_display_names([session_device_id]).get(session_device_id, {})

            result = {
                "session_device_id": session_device_id,
                "session_name": names.get('session_name', f"Session {session_device_id}"),
                "device_name": names.get('device_name', ''),
                "display_name": names.get('display_name', f"Session {session_device_id}"),
                "discourse_type": concept_session.discourse_type,
                "generation_status": concept_session.generation_status,
                "node_count": len(nodes),
                "edge_count": len(edges),
                "nodes": [n.json() for n in nodes],
                "edges": [e.json() for e in edges]
            }

            # Add clusters if requested
            if include_clusters and concept_session.clusters:
                result["clusters"] = [c.json() for c in concept_session.clusters]
                result["cluster_count"] = len(concept_session.clusters)

            return ToolResult(
                success=True,
                data=result,
                metadata={"session_device_id": session_device_id}
            )

        except Exception as e:
            logger.error(f"Error getting concept map: {e}")
            return ToolResult(success=False, data=None, error=str(e))


class Get7CAnalysisTool(BaseTool):
    """Get 7C collaboration analysis for a session."""

    name = "get_7c_analysis"
    description = (
        "Get the 7C collaborative quality analysis for a session. "
        "Returns scores and evidence for all 7 dimensions: Climate, Communication, "
        "Compatibility, Conflict, Context, Contribution, Constructive."
    )
    category = ToolCategory.ARTIFACT
    parameters = {
        "session_device_id": ParameterSpec(
            name="session_device_id",
            type="int",
            description="The session device ID to get 7C analysis for",
            required=True
        )
    }

    def execute(self, session_device_id: int) -> ToolResult:
        """Get the 7C analysis."""
        try:
            from tables.seven_cs_analysis import SevenCsAnalysis

            analysis = SevenCsAnalysis.query.filter_by(
                session_device_id=session_device_id,
                analysis_status='completed'
            ).order_by(SevenCsAnalysis.created_at.desc()).first()

            if not analysis:
                return ToolResult(
                    success=False,
                    data=None,
                    error=f"No 7C analysis found for session {session_device_id}"
                )

            # Get session and device display names
            names = get_session_display_names([session_device_id]).get(session_device_id, {})

            # Format the analysis
            result = {
                "session_device_id": session_device_id,
                "session_name": names.get('session_name', f"Session {session_device_id}"),
                "device_name": names.get('device_name', ''),
                "display_name": names.get('display_name', f"Session {session_device_id}"),
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

            return ToolResult(
                success=True,
                data=result,
                metadata={"session_device_id": session_device_id}
            )

        except Exception as e:
            logger.error(f"Error getting 7C analysis: {e}")
            return ToolResult(success=False, data=None, error=str(e))


class GetLIWCMetricsTool(BaseTool):
    """Get LIWC metrics for a session."""

    name = "get_liwc_metrics"
    description = (
        "Get aggregated LIWC linguistic metrics for a session or speaker. "
        "Includes emotional tone, analytical thinking, clout, authenticity. "
        "Use this to understand the emotional and cognitive patterns in discussion."
    )
    category = ToolCategory.ARTIFACT
    parameters = {
        "session_device_id": ParameterSpec(
            name="session_device_id",
            type="int",
            description="The session device ID to analyze",
            required=True
        ),
        "speaker_id": ParameterSpec(
            name="speaker_id",
            type="int",
            description="Optional speaker ID to filter by",
            required=False,
            default=None
        ),
        "time_range": ParameterSpec(
            name="time_range",
            type="list",
            description="Optional time range as [start_sec, end_sec]",
            required=False,
            default=None
        ),
        "aggregation": ParameterSpec(
            name="aggregation",
            type="str",
            description="Aggregation type: 'raw', 'mean', 'trend', 'by_speaker'",
            required=False,
            default="mean",
            enum=["raw", "mean", "trend", "by_speaker"]
        )
    }

    def execute(self, session_device_id: int, speaker_id: int = None,
                time_range: List[float] = None,
                aggregation: str = "mean") -> ToolResult:
        """Get LIWC metrics."""
        try:
            from tables.transcript import Transcript
            from sqlalchemy import func
            from app import db

            # Build query
            query = db.session.query(Transcript).filter(
                Transcript.session_device_id == session_device_id
            )

            if speaker_id:
                query = query.filter(Transcript.speaker_id == speaker_id)

            if time_range and len(time_range) == 2:
                query = query.filter(
                    Transcript.start_time >= time_range[0],
                    Transcript.start_time <= time_range[1]
                )

            transcripts = query.order_by(Transcript.start_time).all()

            if not transcripts:
                return ToolResult(
                    success=False,
                    data=None,
                    error=f"No transcripts found for session {session_device_id}"
                )

            # Process based on aggregation type
            if aggregation == "raw":
                result = self._get_raw_metrics(transcripts)
            elif aggregation == "mean":
                result = self._get_mean_metrics(transcripts)
            elif aggregation == "trend":
                result = self._get_trend_metrics(transcripts)
            elif aggregation == "by_speaker":
                result = self._get_by_speaker_metrics(transcripts)
            else:
                result = self._get_mean_metrics(transcripts)

            result["session_device_id"] = session_device_id
            result["transcript_count"] = len(transcripts)

            return ToolResult(
                success=True,
                data=result,
                metadata={
                    "session_device_id": session_device_id,
                    "speaker_id": speaker_id,
                    "aggregation": aggregation
                }
            )

        except Exception as e:
            logger.error(f"Error getting LIWC metrics: {e}")
            return ToolResult(success=False, data=None, error=str(e))

    def _get_raw_metrics(self, transcripts):
        """Return raw metrics for each transcript."""
        return {
            "aggregation": "raw",
            "metrics": [{
                "id": t.id,
                "start_time": t.start_time,
                "emotional_tone": t.emotional_tone_value,
                "analytic_thinking": t.analytic_thinking_value,
                "clout": t.clout_value,
                "authenticity": t.authenticity_value,
                "certainty": t.certainty_value
            } for t in transcripts if t.emotional_tone_value is not None]
        }

    def _get_mean_metrics(self, transcripts):
        """Return mean metrics across all transcripts."""
        valid = [t for t in transcripts if t.emotional_tone_value is not None]
        if not valid:
            return {"aggregation": "mean", "metrics": None}

        n = len(valid)
        return {
            "aggregation": "mean",
            "metrics": {
                "emotional_tone": round(sum(t.emotional_tone_value or 0 for t in valid) / n, 2),
                "analytic_thinking": round(sum(t.analytic_thinking_value or 0 for t in valid) / n, 2),
                "clout": round(sum(t.clout_value or 0 for t in valid) / n, 2),
                "authenticity": round(sum(t.authenticity_value or 0 for t in valid) / n, 2),
                "certainty": round(sum(t.certainty_value or 0 for t in valid) / n, 2)
            }
        }

    def _get_trend_metrics(self, transcripts):
        """Return metrics showing trend over time."""
        valid = [t for t in transcripts if t.emotional_tone_value is not None]
        if len(valid) < 4:
            return {"aggregation": "trend", "metrics": None}

        # Split into quarters
        quarter_size = len(valid) // 4
        quarters = []
        for i in range(4):
            start = i * quarter_size
            end = start + quarter_size if i < 3 else len(valid)
            q = valid[start:end]
            if q:
                quarters.append({
                    "quarter": i + 1,
                    "emotional_tone": round(sum(t.emotional_tone_value or 0 for t in q) / len(q), 2),
                    "analytic_thinking": round(sum(t.analytic_thinking_value or 0 for t in q) / len(q), 2)
                })

        return {"aggregation": "trend", "metrics": quarters}

    def _get_by_speaker_metrics(self, transcripts):
        """Return metrics grouped by speaker."""
        from collections import defaultdict

        by_speaker = defaultdict(list)
        for t in transcripts:
            if t.speaker_id and t.emotional_tone_value is not None:
                by_speaker[t.speaker_id].append(t)

        result = {}
        for speaker_id, speaker_transcripts in by_speaker.items():
            n = len(speaker_transcripts)
            result[speaker_id] = {
                "count": n,
                "emotional_tone": round(sum(t.emotional_tone_value or 0 for t in speaker_transcripts) / n, 2),
                "analytic_thinking": round(sum(t.analytic_thinking_value or 0 for t in speaker_transcripts) / n, 2),
                "clout": round(sum(t.clout_value or 0 for t in speaker_transcripts) / n, 2)
            }

        return {"aggregation": "by_speaker", "metrics": result}


class GetTranscriptContextTool(BaseTool):
    """Get transcript context around a timestamp."""

    name = "get_transcript_context"
    description = (
        "Get transcript turns around a specific timestamp. "
        "Returns the discussion context for a particular moment. "
        "Use this to understand what was being said at a specific time."
    )
    category = ToolCategory.ARTIFACT
    parameters = {
        "session_device_id": ParameterSpec(
            name="session_device_id",
            type="int",
            description="The session device ID",
            required=True
        ),
        "timestamp": ParameterSpec(
            name="timestamp",
            type="float",
            description="Center timestamp in seconds",
            required=True
        ),
        "window_seconds": ParameterSpec(
            name="window_seconds",
            type="int",
            description="Context window size in seconds",
            required=False,
            default=60
        )
    }

    def execute(self, session_device_id: int, timestamp: float,
                window_seconds: int = 60) -> ToolResult:
        """Get transcript context."""
        try:
            from tables.transcript import Transcript
            import database as db_helper

            # Get transcripts in time window
            transcripts = Transcript.query.filter(
                Transcript.session_device_id == session_device_id,
                Transcript.start_time >= timestamp - window_seconds / 2,
                Transcript.start_time <= timestamp + window_seconds / 2
            ).order_by(Transcript.start_time).all()

            if not transcripts:
                return ToolResult(
                    success=False,
                    data=None,
                    error=f"No transcripts found around timestamp {timestamp}"
                )

            # Build speaker alias lookup
            speaker_ids = set(t.speaker_id for t in transcripts if t.speaker_id)
            speaker_map = {}
            for speaker_id in speaker_ids:
                speaker = db_helper.get_speakers(id=speaker_id)
                if speaker:
                    speaker_map[speaker_id] = speaker.alias or speaker.get_alias()

            result = {
                "session_device_id": session_device_id,
                "center_timestamp": timestamp,
                "window_seconds": window_seconds,
                "transcript_count": len(transcripts),
                "transcripts": [{
                    "id": t.id,
                    "text": t.transcript,
                    "speaker_id": t.speaker_id,
                    "speaker_alias": speaker_map.get(t.speaker_id, t.speaker_tag),
                    "start_time": t.start_time,
                    "emotional_tone": t.emotional_tone_value
                } for t in transcripts]
            }

            return ToolResult(
                success=True,
                data=result,
                metadata={
                    "session_device_id": session_device_id,
                    "timestamp": timestamp
                }
            )

        except Exception as e:
            logger.error(f"Error getting transcript context: {e}")
            return ToolResult(success=False, data=None, error=str(e))
