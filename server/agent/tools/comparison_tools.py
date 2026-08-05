"""
Comparison Tools

Tools for comparing sessions and speakers.
"""

import logging
from typing import Dict, List, Optional
from collections import Counter

from .base import BaseTool, ToolResult, ParameterSpec, ToolCategory

logger = logging.getLogger(__name__)


class CompareSessionsTool(BaseTool):
    """Compare metrics and patterns across sessions."""

    name = "compare_sessions"
    description = (
        "Compare metrics, concepts, or participation patterns across multiple sessions. "
        "Returns structured comparison highlighting differences. "
        "Use this to understand how discussions differ across sessions."
    )
    category = ToolCategory.COMPARISON
    parameters = {
        "session_device_ids": ParameterSpec(
            name="session_device_ids",
            type="list",
            description="List of session device IDs to compare (2-5)",
            required=True
        ),
        "comparison_type": ParameterSpec(
            name="comparison_type",
            type="str",
            description="Type of comparison: 'metrics', 'concepts', 'participation', 'themes', 'all'",
            required=False,
            default="all",
            enum=["metrics", "concepts", "participation", "themes", "all"]
        )
    }

    def execute(self, session_device_ids: List[int],
                comparison_type: str = "all") -> ToolResult:
        """Execute session comparison."""
        try:
            if len(session_device_ids) < 2:
                return ToolResult(
                    success=False,
                    data=None,
                    error="Need at least 2 sessions to compare"
                )

            if len(session_device_ids) > 5:
                session_device_ids = session_device_ids[:5]

            result = {
                "session_device_ids": session_device_ids,
                "comparison_type": comparison_type,
                "sessions": {}
            }

            # Gather data for each session
            for sid in session_device_ids:
                session_data = self._get_session_data(sid, comparison_type)
                result["sessions"][sid] = session_data

            # Generate comparison insights
            if comparison_type in ["all", "metrics"]:
                result["metrics_comparison"] = self._compare_metrics(result["sessions"])

            if comparison_type in ["all", "concepts"]:
                result["concepts_comparison"] = self._compare_concepts(result["sessions"])

            if comparison_type in ["all", "participation"]:
                result["participation_comparison"] = self._compare_participation(result["sessions"])

            return ToolResult(
                success=True,
                data=result,
                metadata={
                    "session_count": len(session_device_ids),
                    "comparison_type": comparison_type
                }
            )

        except Exception as e:
            logger.error(f"Error comparing sessions: {e}")
            return ToolResult(success=False, data=None, error=str(e))

    def _get_session_data(self, session_device_id: int, comparison_type: str) -> Dict:
        """Get data for a single session."""
        from tables.concept_session import ConceptSession
        from tables.seven_cs_analysis import SevenCsAnalysis
        from tables.transcript import Transcript
        import database as db_helper

        data = {"session_device_id": session_device_id}

        # Get concept session
        concept_session = ConceptSession.query.filter_by(
            session_device_id=session_device_id
        ).first()

        if concept_session and comparison_type in ["all", "concepts", "themes"]:
            nodes = concept_session.nodes or []
            data["concept_data"] = {
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
                session_device_id=session_device_id,
                analysis_status='completed'
            ).first()

            if seven_cs and seven_cs.analysis_summary:
                data["seven_c_scores"] = {
                    dim: seven_cs.analysis_summary.get(dim, {}).get('score', 0)
                    for dim in ['climate', 'communication', 'compatibility',
                               'conflict', 'context', 'contribution', 'constructive']
                }

        # Get participation data
        if comparison_type in ["all", "participation"]:
            transcripts = Transcript.query.filter_by(
                session_device_id=session_device_id
            ).all()

            speaker_counts = Counter(t.speaker_id for t in transcripts if t.speaker_id)
            data["participation"] = {
                "transcript_count": len(transcripts),
                "speaker_count": len(speaker_counts),
                "speaker_distribution": dict(speaker_counts)
            }

        return data

    def _compare_metrics(self, sessions: Dict) -> Dict:
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

    def _compare_concepts(self, sessions: Dict) -> Dict:
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

    def _compare_participation(self, sessions: Dict) -> Dict:
        """Compare participation patterns."""
        comparisons = {}

        speaker_counts = []
        transcript_counts = []

        for sid, data in sessions.items():
            if "participation" in data:
                p = data["participation"]
                speaker_counts.append({
                    "session": sid,
                    "count": p.get("speaker_count", 0)
                })
                transcript_counts.append({
                    "session": sid,
                    "count": p.get("transcript_count", 0)
                })

        if speaker_counts:
            comparisons["speaker_counts"] = speaker_counts
            comparisons["transcript_counts"] = transcript_counts

        return comparisons


class CompareSpeakersTool(BaseTool):
    """Compare speakers within a session."""

    name = "compare_speakers"
    description = (
        "Compare contribution patterns of speakers within a session. "
        "Returns per-speaker metrics, concept contributions, and interaction patterns. "
        "Use this to understand how different participants contributed."
    )
    category = ToolCategory.COMPARISON
    parameters = {
        "session_device_id": ParameterSpec(
            name="session_device_id",
            type="int",
            description="The session device ID to analyze",
            required=True
        ),
        "speaker_ids": ParameterSpec(
            name="speaker_ids",
            type="list",
            description="Optional specific speaker IDs to compare (default: all)",
            required=False,
            default=None
        )
    }

    def execute(self, session_device_id: int,
                speaker_ids: List[int] = None) -> ToolResult:
        """Execute speaker comparison."""
        try:
            from tables.transcript import Transcript
            from tables.speaker import Speaker
            import database as db_helper

            # Get all speakers in session
            speakers = Speaker.query.filter_by(
                session_device_id=session_device_id
            ).all()

            if not speakers:
                return ToolResult(
                    success=False,
                    data=None,
                    error=f"No speakers found for session {session_device_id}"
                )

            # Filter to specific speakers if provided
            if speaker_ids:
                speakers = [s for s in speakers if s.id in speaker_ids]

            result = {
                "session_device_id": session_device_id,
                "speaker_count": len(speakers),
                "speakers": {}
            }

            # Gather data for each speaker
            for speaker in speakers:
                speaker_data = self._get_speaker_data(
                    session_device_id, speaker
                )
                result["speakers"][speaker.id] = speaker_data

            # Generate comparison insights
            result["comparison"] = self._generate_comparison(result["speakers"])

            return ToolResult(
                success=True,
                data=result,
                metadata={
                    "session_device_id": session_device_id,
                    "speaker_count": len(speakers)
                }
            )

        except Exception as e:
            logger.error(f"Error comparing speakers: {e}")
            return ToolResult(success=False, data=None, error=str(e))

    def _get_speaker_data(self, session_device_id: int, speaker) -> Dict:
        """Get data for a single speaker."""
        from tables.transcript import Transcript
        import database as db_helper

        data = {
            "speaker_id": speaker.id,
            "alias": speaker.alias or speaker.get_alias()
        }

        # Get transcripts
        transcripts = Transcript.query.filter_by(
            session_device_id=session_device_id,
            speaker_id=speaker.id
        ).all()

        data["transcript_count"] = len(transcripts)
        data["word_count"] = sum(
            len(t.transcript.split()) for t in transcripts if t.transcript
        )

        # Get LIWC metrics
        valid_metrics = [t for t in transcripts if t.emotional_tone_value is not None]
        if valid_metrics:
            n = len(valid_metrics)
            data["avg_emotional_tone"] = round(
                sum(t.emotional_tone_value or 0 for t in valid_metrics) / n, 2
            )
            data["avg_analytic"] = round(
                sum(t.analytic_thinking_value or 0 for t in valid_metrics) / n, 2
            )
            data["avg_clout"] = round(
                sum(t.clout_value or 0 for t in valid_metrics) / n, 2
            )

        # Get concept contributions
        concept_graph = db_helper.get_speaker_contribution_graph(
            session_device_id, speaker.id
        )
        if concept_graph:
            data["concept_count"] = concept_graph.get("node_count", 0)
            data["concept_types"] = concept_graph.get("node_types", {})

        return data

    def _generate_comparison(self, speakers: Dict) -> Dict:
        """Generate comparison insights."""
        comparison = {}

        # Most active speaker
        by_transcripts = sorted(
            speakers.items(),
            key=lambda x: x[1].get("transcript_count", 0),
            reverse=True
        )
        if by_transcripts:
            comparison["most_active"] = {
                "speaker_id": by_transcripts[0][0],
                "alias": by_transcripts[0][1].get("alias"),
                "transcript_count": by_transcripts[0][1].get("transcript_count", 0)
            }

        # Most concepts contributed
        by_concepts = sorted(
            speakers.items(),
            key=lambda x: x[1].get("concept_count", 0),
            reverse=True
        )
        if by_concepts:
            comparison["most_concepts"] = {
                "speaker_id": by_concepts[0][0],
                "alias": by_concepts[0][1].get("alias"),
                "concept_count": by_concepts[0][1].get("concept_count", 0)
            }

        # Participation balance (Gini coefficient approximation)
        transcript_counts = [s.get("transcript_count", 0) for s in speakers.values()]
        if transcript_counts and sum(transcript_counts) > 0:
            total = sum(transcript_counts)
            shares = [c / total for c in transcript_counts]
            n = len(shares)
            if n > 1:
                gini = sum(abs(shares[i] - shares[j])
                          for i in range(n) for j in range(n)) / (2 * n * n * (sum(shares) / n))
                comparison["participation_balance"] = {
                    "gini_coefficient": round(gini, 3),
                    "interpretation": "balanced" if gini < 0.3 else "moderate" if gini < 0.5 else "uneven"
                }

        return comparison
