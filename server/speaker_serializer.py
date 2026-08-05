# server/speaker_serializer.py
"""
Speaker Serializer for Cross-Session RAG

Aggregates speaker data across all sessions to create embeddable
text documents for speaker-level semantic search.
"""

import logging
from collections import Counter, defaultdict
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SpeakerSerializer:
    """
    Serializes speaker data across all sessions into embeddable text documents.

    The output captures:
    - Engagement metrics (LIWC averages, question counts)
    - Concept contributions by type
    - Sample utterances showing speaking style
    - Session participation history
    """

    def serialize_speaker(self, speaker_alias: str) -> Optional[Dict]:
        """
        Aggregate all data for a speaker across ALL sessions.

        Args:
            speaker_alias: The speaker's alias (e.g., "Lex")

        Returns:
            Dict with 'text' (document for embedding) and 'metadata' (for filtering)
            Returns None if speaker not found
        """
        import database as db_helper
        from tables.transcript import Transcript
        from tables.concept_node import ConceptNode
        from tables.speaker import Speaker

        # Find all speaker records with this alias
        all_speakers = Speaker.query.filter_by(alias=speaker_alias).all()

        if not all_speakers:
            logger.warning(f"No speaker records found for alias: {speaker_alias}")
            return None

        speaker_ids = [s.id for s in all_speakers]
        session_device_ids = [s.session_device_id for s in all_speakers]

        # Get all transcripts across all speaker_ids
        transcripts = Transcript.query.filter(
            Transcript.speaker_id.in_(speaker_ids)
        ).order_by(Transcript.start_time).all()

        if not transcripts:
            logger.warning(f"No transcripts found for speaker: {speaker_alias}")
            return None

        # Get all concept nodes across all speaker_ids
        concept_nodes = ConceptNode.query.filter(
            ConceptNode.speaker_id.in_(speaker_ids)
        ).all()

        # Get session names for context
        session_names = self._get_session_names(session_device_ids)

        # Build the document
        document_parts = []

        # 1. Speaker header with session info
        document_parts.append(self._serialize_header(
            speaker_alias, session_device_ids, session_names
        ))

        # 2. Engagement metrics from transcripts
        document_parts.append(self._serialize_engagement_metrics(transcripts))

        # 3. Concept contributions
        if concept_nodes:
            document_parts.append(self._serialize_concept_contributions(concept_nodes))

        # 4. Sample utterances
        document_parts.append(self._serialize_sample_utterances(transcripts))

        # Combine into embedding document
        document = "\n\n".join(filter(None, document_parts))

        # Compute metadata for filtering
        metadata = self._compute_metadata(
            speaker_alias, transcripts, concept_nodes, session_device_ids
        )

        return {
            "text": document,
            "metadata": metadata
        }

    def _get_session_names(self, session_device_ids: List[int]) -> Dict[int, str]:
        """Get session names for context."""
        import database as db_helper

        names = {}
        for sd_id in session_device_ids:
            sd = db_helper.get_session_devices(id=sd_id)
            if sd:
                names[sd_id] = sd.name or f"Session {sd_id}"
        return names

    def _serialize_header(self, speaker_alias: str,
                         session_device_ids: List[int],
                         session_names: Dict[int, str]) -> str:
        """Serialize speaker header with session participation."""
        lines = [f"SPEAKER: {speaker_alias}"]
        lines.append(f"SESSIONS ({len(session_device_ids)}):")

        for sd_id in session_device_ids:
            name = session_names.get(sd_id, f"Session {sd_id}")
            lines.append(f"  - {name}")

        return "\n".join(lines)

    def _serialize_engagement_metrics(self, transcripts: List) -> str:
        """Serialize aggregated LIWC metrics from transcripts."""
        if not transcripts:
            return ""

        # Aggregate metrics
        total_emotional = 0
        total_analytic = 0
        total_clout = 0
        total_authenticity = 0
        total_certainty = 0
        question_count = 0
        total_word_count = 0
        count = 0

        for t in transcripts:
            if t.emotional_tone_value is not None:
                total_emotional += t.emotional_tone_value
                total_analytic += t.analytic_thinking_value or 0
                total_clout += t.clout_value or 0
                total_authenticity += t.authenticity_value or 0
                total_certainty += t.certainty_value or 0
                count += 1
            if t.question:
                question_count += 1
            total_word_count += t.word_count or 0

        if count == 0:
            return ""

        avg_emotional = round(total_emotional / count, 2)
        avg_analytic = round(total_analytic / count, 2)
        avg_clout = round(total_clout / count, 2)
        avg_authenticity = round(total_authenticity / count, 2)
        avg_certainty = round(total_certainty / count, 2)

        lines = ["ENGAGEMENT METRICS:"]
        lines.append(f"  - Total utterances: {len(transcripts)}")
        lines.append(f"  - Total word count: {total_word_count}")
        lines.append(f"  - Questions asked: {question_count}")
        lines.append(f"  - Avg emotional tone: {avg_emotional}")
        lines.append(f"  - Avg analytic thinking: {avg_analytic}")
        lines.append(f"  - Avg clout: {avg_clout}")
        lines.append(f"  - Avg authenticity: {avg_authenticity}")
        lines.append(f"  - Avg certainty: {avg_certainty}")

        # Characterize engagement style
        style_notes = []
        if avg_clout < 10:
            style_notes.append("tends to defer to others")
        elif avg_clout > 50:
            style_notes.append("speaks with authority")

        if avg_analytic > 50:
            style_notes.append("highly analytical")

        if question_count > len(transcripts) * 0.3:
            style_notes.append("asks many questions")

        if style_notes:
            lines.append(f"  - Style: {', '.join(style_notes)}")

        return "\n".join(lines)

    def _serialize_concept_contributions(self, concept_nodes: List) -> str:
        """Serialize concept contributions by type."""
        if not concept_nodes:
            return ""

        # Group by type
        by_type = defaultdict(list)
        for node in concept_nodes:
            node_type = node.node_type or 'concept'
            by_type[node_type].append(node.text)

        lines = ["CONCEPT CONTRIBUTIONS:"]

        # Questions
        if by_type.get('question'):
            questions = by_type['question'][:3]
            lines.append(f"  - Questions ({len(by_type['question'])}):")
            for q in questions:
                lines.append(f'    "{q[:80]}"')

        # Ideas
        if by_type.get('idea'):
            ideas = by_type['idea'][:3]
            lines.append(f"  - Ideas ({len(by_type['idea'])}):")
            for i in ideas:
                lines.append(f'    "{i[:80]}"')

        # Other types
        for node_type in ['hypothesis', 'problem', 'solution', 'conclusion']:
            if by_type.get(node_type):
                items = by_type[node_type][:2]
                lines.append(f"  - {node_type.title()}s ({len(by_type[node_type])}):")
                for item in items:
                    lines.append(f'    "{item[:80]}"')

        return "\n".join(lines)

    def _serialize_sample_utterances(self, transcripts: List, max_samples: int = 5) -> str:
        """Serialize sample utterances showing speaking style."""
        if not transcripts:
            return ""

        # Select diverse samples (beginning, middle, end, longest)
        samples = []

        # First utterance
        if transcripts:
            samples.append(transcripts[0])

        # Middle utterance
        if len(transcripts) > 2:
            mid_idx = len(transcripts) // 2
            samples.append(transcripts[mid_idx])

        # Longest utterances (most substantive)
        sorted_by_length = sorted(transcripts, key=lambda t: len(t.transcript), reverse=True)
        for t in sorted_by_length[:2]:
            if t not in samples:
                samples.append(t)

        # Limit to max_samples
        samples = samples[:max_samples]

        lines = ["SAMPLE UTTERANCES:"]
        for t in samples:
            text = t.transcript[:150] + "..." if len(t.transcript) > 150 else t.transcript
            lines.append(f'  "{text}"')

        return "\n".join(lines)

    def _compute_metadata(self, speaker_alias: str, transcripts: List,
                         concept_nodes: List, session_device_ids: List[int]) -> Dict:
        """Compute metadata for ChromaDB filtering."""
        metadata = {
            "speaker_alias": speaker_alias,
            "indexed_at": datetime.utcnow().isoformat(),
            "session_count": len(session_device_ids),
            "session_device_ids": ",".join(str(sd) for sd in session_device_ids),
            "transcript_count": len(transcripts),
            "concept_count": len(concept_nodes) if concept_nodes else 0
        }

        # Aggregate transcript metrics
        if transcripts:
            question_count = sum(1 for t in transcripts if t.question)
            metadata["question_count"] = question_count

            total_words = sum(t.word_count or 0 for t in transcripts)
            metadata["total_word_count"] = total_words

            # LIWC averages
            count = 0
            total_emotional = 0
            total_analytic = 0
            total_clout = 0

            for t in transcripts:
                if t.emotional_tone_value is not None:
                    total_emotional += t.emotional_tone_value
                    total_analytic += t.analytic_thinking_value or 0
                    total_clout += t.clout_value or 0
                    count += 1

            if count > 0:
                metadata["avg_emotional_tone"] = round(total_emotional / count, 2)
                metadata["avg_analytic_thinking"] = round(total_analytic / count, 2)
                metadata["avg_clout"] = round(total_clout / count, 2)
            else:
                metadata["avg_emotional_tone"] = 0
                metadata["avg_analytic_thinking"] = 0
                metadata["avg_clout"] = 0
        else:
            metadata["question_count"] = 0
            metadata["total_word_count"] = 0
            metadata["avg_emotional_tone"] = 0
            metadata["avg_analytic_thinking"] = 0
            metadata["avg_clout"] = 0

        # Concept type counts
        if concept_nodes:
            node_types = Counter(n.node_type for n in concept_nodes)
            metadata["idea_count"] = node_types.get('idea', 0)
            metadata["question_concept_count"] = node_types.get('question', 0)
        else:
            metadata["idea_count"] = 0
            metadata["question_concept_count"] = 0

        return metadata


def get_all_speaker_aliases() -> List[str]:
    """Get all unique speaker aliases from the database."""
    from tables.speaker import Speaker

    speakers = Speaker.query.with_entities(Speaker.alias).distinct().all()
    return [s.alias for s in speakers if s.alias]
