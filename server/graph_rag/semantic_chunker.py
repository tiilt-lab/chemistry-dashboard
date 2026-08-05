"""
Semantic Chunker for Transcripts

Replaces fixed 30-second windows with topic-based semantic chunking.
Detects topic shifts using embedding similarity and groups consecutive
turns on the same topic while respecting speaker boundaries.
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from openai import OpenAI
import os

logger = logging.getLogger(__name__)


@dataclass
class SemanticChunk:
    """A semantically coherent transcript chunk."""
    text: str
    start_time: float
    end_time: float
    speakers: List[str]
    speaker_ids: List[int]
    transcript_ids: List[int]
    session_device_id: int
    chunk_index: int
    topic_keywords: List[str]  # Extracted topic hints

    # Aggregated LIWC metrics
    avg_emotional_tone: float = 0.0
    avg_analytic_thinking: float = 0.0
    avg_clout: float = 0.0
    avg_authenticity: float = 0.0
    avg_certainty: float = 0.0


class SemanticChunker:
    """
    Creates semantically coherent transcript chunks based on topic shifts.

    Unlike fixed 30-second windows, this chunker:
    1. Detects topic shifts using embedding similarity
    2. Groups consecutive turns on the same topic
    3. Respects speaker turn boundaries
    4. Targets 100-300 words per chunk (flexible)
    5. Preserves discourse markers
    """

    # Minimum/maximum words per chunk
    MIN_WORDS = 50
    MAX_WORDS = 400
    TARGET_WORDS = 200

    # Similarity threshold for topic shift detection
    TOPIC_SHIFT_THRESHOLD = 0.65  # Below this = new topic

    # Discourse markers that indicate continuation
    CONTINUATION_MARKERS = [
        'and', 'also', 'furthermore', 'moreover', 'additionally',
        'building on', 'to add to', 'continuing', 'as I was saying',
        'similarly', 'likewise', 'in addition'
    ]

    # Discourse markers that indicate topic shift
    SHIFT_MARKERS = [
        'however', 'but', 'on the other hand', 'actually',
        'changing topic', 'moving on', 'let me ask', 'new question',
        'what about', 'speaking of', 'anyway'
    ]

    def __init__(self, openai_api_key: str = None):
        """Initialize with OpenAI for embedding similarity."""
        self.api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key)
        self._embedding_cache = {}

    def chunk_transcripts(self, transcripts: List, session_device_id: int) -> List[SemanticChunk]:
        """
        Chunk transcripts into semantically coherent segments.

        Args:
            transcripts: List of Transcript objects from database
            session_device_id: The session device ID

        Returns:
            List of SemanticChunk objects
        """
        if not transcripts:
            return []

        # Sort by time
        sorted_transcripts = sorted(transcripts, key=lambda t: t.start_time)

        # Build speaker alias lookup
        speaker_aliases = self._build_speaker_aliases(sorted_transcripts)

        # Group into initial segments by detecting topic shifts
        segments = self._segment_by_topic(sorted_transcripts)

        # Merge small segments, split large ones
        balanced_segments = self._balance_segments(segments)

        # Convert to SemanticChunk objects
        chunks = []
        for idx, segment in enumerate(balanced_segments):
            chunk = self._create_chunk(
                segment,
                session_device_id,
                idx,
                speaker_aliases
            )
            chunks.append(chunk)

        logger.info(f"Created {len(chunks)} semantic chunks from {len(transcripts)} transcripts")
        return chunks

    def _segment_by_topic(self, transcripts: List) -> List[List]:
        """
        Segment transcripts by detecting topic shifts.
        Uses a sliding window approach with embedding similarity.
        """
        if len(transcripts) <= 3:
            return [transcripts]

        segments = []
        current_segment = [transcripts[0]]

        # Get embeddings for sliding windows
        window_size = 3  # Compare groups of 3 utterances

        for i in range(1, len(transcripts)):
            # Check for topic shift
            should_split = self._detect_topic_shift(
                current_segment[-min(window_size, len(current_segment)):],
                transcripts[i]
            )

            # Also check discourse markers
            if self._has_shift_marker(transcripts[i].transcript):
                should_split = True
            elif self._has_continuation_marker(transcripts[i].transcript):
                should_split = False

            if should_split and len(current_segment) >= 2:
                segments.append(current_segment)
                current_segment = [transcripts[i]]
            else:
                current_segment.append(transcripts[i])

        # Don't forget the last segment
        if current_segment:
            segments.append(current_segment)

        return segments

    def _detect_topic_shift(self, recent_transcripts: List, new_transcript) -> bool:
        """
        Detect if new_transcript represents a topic shift from recent_transcripts.
        Uses embedding similarity comparison.
        """
        if not recent_transcripts:
            return False

        # Combine recent transcripts into context
        recent_text = " ".join([t.transcript for t in recent_transcripts])
        new_text = new_transcript.transcript

        # Skip very short utterances
        if len(new_text.split()) < 5:
            return False

        try:
            # Get embeddings
            recent_embedding = self._get_embedding(recent_text)
            new_embedding = self._get_embedding(new_text)

            # Calculate cosine similarity
            similarity = self._cosine_similarity(recent_embedding, new_embedding)

            return similarity < self.TOPIC_SHIFT_THRESHOLD

        except Exception as e:
            logger.warning(f"Error computing topic shift: {e}")
            return False

    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for text, with caching."""
        # Use a hash of the text as cache key
        cache_key = hash(text[:500])  # Limit for caching

        if cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]

        response = self.client.embeddings.create(
            model="text-embedding-3-small",  # Use smaller model for chunking (faster)
            input=text[:8000]  # Limit input length
        )

        embedding = response.data[0].embedding
        self._embedding_cache[cache_key] = embedding

        return embedding

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        a = np.array(a)
        b = np.array(b)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    def _has_shift_marker(self, text: str) -> bool:
        """Check if text starts with a topic shift marker."""
        text_lower = text.lower().strip()
        for marker in self.SHIFT_MARKERS:
            if text_lower.startswith(marker):
                return True
        return False

    def _has_continuation_marker(self, text: str) -> bool:
        """Check if text starts with a continuation marker."""
        text_lower = text.lower().strip()
        for marker in self.CONTINUATION_MARKERS:
            if text_lower.startswith(marker):
                return True
        return False

    def _balance_segments(self, segments: List[List]) -> List[List]:
        """
        Balance segment sizes - merge small ones, split large ones.
        Target: MIN_WORDS to MAX_WORDS per segment.
        """
        balanced = []
        pending = []
        pending_words = 0

        for segment in segments:
            segment_words = sum(len(t.transcript.split()) for t in segment)

            if segment_words < self.MIN_WORDS:
                # Too small - try to merge with pending
                pending.extend(segment)
                pending_words += segment_words

                if pending_words >= self.TARGET_WORDS:
                    balanced.append(pending)
                    pending = []
                    pending_words = 0

            elif segment_words > self.MAX_WORDS:
                # Too large - split it
                # First, flush pending
                if pending:
                    pending.extend(segment[:len(segment)//4])  # Add some overlap
                    balanced.append(pending)
                    pending = []
                    pending_words = 0

                # Split large segment
                split_segments = self._split_large_segment(segment)
                balanced.extend(split_segments)

            else:
                # Good size
                if pending:
                    # Merge pending with this segment if combined size is OK
                    combined_words = pending_words + segment_words
                    if combined_words <= self.MAX_WORDS:
                        pending.extend(segment)
                        balanced.append(pending)
                        pending = []
                        pending_words = 0
                    else:
                        balanced.append(pending)
                        balanced.append(segment)
                        pending = []
                        pending_words = 0
                else:
                    balanced.append(segment)

        # Flush any remaining pending
        if pending:
            if balanced and sum(len(t.transcript.split()) for t in balanced[-1]) < self.TARGET_WORDS:
                balanced[-1].extend(pending)
            else:
                balanced.append(pending)

        return balanced

    def _split_large_segment(self, segment: List) -> List[List]:
        """Split a large segment into smaller chunks."""
        result = []
        current = []
        current_words = 0

        for t in segment:
            t_words = len(t.transcript.split())

            if current_words + t_words > self.TARGET_WORDS and current:
                result.append(current)
                current = [t]
                current_words = t_words
            else:
                current.append(t)
                current_words += t_words

        if current:
            result.append(current)

        return result

    def _build_speaker_aliases(self, transcripts: List) -> Dict[int, str]:
        """Build speaker_id to alias mapping."""
        import database as db_helper

        speaker_ids = set(t.speaker_id for t in transcripts if t.speaker_id)
        speaker_map = {}

        for speaker_id in speaker_ids:
            try:
                speaker = db_helper.get_speakers(id=speaker_id)
                if speaker:
                    speaker_map[speaker_id] = speaker.alias or speaker.get_alias()
                else:
                    speaker_map[speaker_id] = f"Speaker {speaker_id}"
            except Exception:
                speaker_map[speaker_id] = f"Speaker {speaker_id}"

        return speaker_map

    def _create_chunk(self, transcripts: List, session_device_id: int,
                      chunk_index: int, speaker_aliases: Dict[int, str]) -> SemanticChunk:
        """Create a SemanticChunk from a list of transcripts."""

        # Build text with speaker labels
        texts = []
        speakers = set()
        speaker_ids = set()
        transcript_ids = []

        # Aggregate LIWC metrics
        total_emotional = 0
        total_analytic = 0
        total_clout = 0
        total_authenticity = 0
        total_certainty = 0
        count = 0

        for t in transcripts:
            # Get speaker label
            if t.speaker_id and t.speaker_id in speaker_aliases:
                speaker = speaker_aliases[t.speaker_id]
                speaker_ids.add(t.speaker_id)
            elif t.speaker_tag:
                speaker = t.speaker_tag
            else:
                speaker = "Unknown"

            speakers.add(speaker)
            transcript_ids.append(t.id)
            texts.append(f"{speaker}: {t.transcript}")

            # Aggregate metrics
            if hasattr(t, 'emotional_tone_value') and t.emotional_tone_value is not None:
                total_emotional += t.emotional_tone_value
                total_analytic += t.analytic_thinking_value or 0
                total_clout += t.clout_value or 0
                total_authenticity += t.authenticity_value or 0
                total_certainty += t.certainty_value or 0
                count += 1

        # Calculate averages
        if count > 0:
            avg_emotional = round(total_emotional / count, 2)
            avg_analytic = round(total_analytic / count, 2)
            avg_clout = round(total_clout / count, 2)
            avg_authenticity = round(total_authenticity / count, 2)
            avg_certainty = round(total_certainty / count, 2)
        else:
            avg_emotional = avg_analytic = avg_clout = avg_authenticity = avg_certainty = 0

        # Extract simple topic keywords from the chunk
        topic_keywords = self._extract_topic_keywords(" ".join([t.transcript for t in transcripts]))

        return SemanticChunk(
            text="\n".join(texts),
            start_time=transcripts[0].start_time,
            end_time=transcripts[-1].end_time if hasattr(transcripts[-1], 'end_time') else transcripts[-1].start_time,
            speakers=list(speakers),
            speaker_ids=list(speaker_ids),
            transcript_ids=transcript_ids,
            session_device_id=session_device_id,
            chunk_index=chunk_index,
            topic_keywords=topic_keywords,
            avg_emotional_tone=avg_emotional,
            avg_analytic_thinking=avg_analytic,
            avg_clout=avg_clout,
            avg_authenticity=avg_authenticity,
            avg_certainty=avg_certainty
        )

    def _extract_topic_keywords(self, text: str, max_keywords: int = 5) -> List[str]:
        """
        Extract topic keywords from text using simple frequency analysis.
        For more sophisticated extraction, could use TF-IDF or KeyBERT.
        """
        import re
        from collections import Counter

        # Simple stopwords
        stopwords = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare',
            'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as',
            'into', 'through', 'during', 'before', 'after', 'above', 'below',
            'between', 'under', 'again', 'further', 'then', 'once', 'here',
            'there', 'when', 'where', 'why', 'how', 'all', 'each', 'few', 'more',
            'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own',
            'same', 'so', 'than', 'too', 'very', 'just', 'and', 'but', 'if', 'or',
            'because', 'until', 'while', 'although', 'though', 'whether', 'this',
            'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
            'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'its', 'our',
            'their', 'what', 'which', 'who', 'whom', 'think', 'know', 'like',
            'yeah', 'okay', 'right', 'um', 'uh', 'well', 'so', 'like', 'just',
            'really', 'actually', 'basically', 'literally', 'something', 'thing',
            'say', 'said', 'says', 'going', 'get', 'got', 'make', 'made'
        }

        # Tokenize and filter
        words = re.findall(r'\b[a-z]{3,}\b', text.lower())
        filtered = [w for w in words if w not in stopwords]

        # Get most common
        counter = Counter(filtered)
        return [word for word, _ in counter.most_common(max_keywords)]

    def clear_cache(self):
        """Clear the embedding cache to free memory."""
        self._embedding_cache.clear()
