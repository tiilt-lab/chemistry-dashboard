"""
Grounding and Citation Validation

Ensures agent responses are grounded in retrieved evidence.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)


@dataclass
class Citation:
    """A citation linking a claim to its source."""
    claim: str
    artifact_type: str  # transcript, concept_map, seven_c, liwc, speaker
    artifact_id: str  # session_device_id or other identifier
    excerpt: str  # Supporting evidence text
    source_timestamps: Optional[List[float]] = None
    confidence: float = 1.0

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "claim": self.claim,
            "artifact_type": self.artifact_type,
            "artifact_id": self.artifact_id,
            "excerpt": self.excerpt,
            "source_timestamps": self.source_timestamps,
            "confidence": self.confidence
        }


@dataclass
class GroundedResponse:
    """A response with grounding validation."""
    answer: str
    citations: List[Citation]
    confidence: float  # Overall confidence 0-1
    reasoning_trace: List[str]
    follow_up_suggestions: List[str]
    ungrounded_claims: List[str] = field(default_factory=list)
    is_grounded: bool = True

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "answer": self.answer,
            "citations": [c.to_dict() for c in self.citations],
            "confidence": self.confidence,
            "reasoning_trace": self.reasoning_trace,
            "follow_up_suggestions": self.follow_up_suggestions,
            "ungrounded_claims": self.ungrounded_claims,
            "is_grounded": self.is_grounded
        }


class GroundingValidator:
    """
    Validates that agent responses are grounded in retrieved evidence.

    Features:
    - Citation extraction from tool results
    - Claim verification against evidence
    - Confidence calculation
    - Follow-up suggestion generation
    """

    # Patterns that indicate quantitative claims needing verification
    QUANTITATIVE_PATTERNS = [
        r'\b(\d+(?:\.\d+)?)\s*%',  # Percentages
        r'\b(\d+)\s+(?:students?|speakers?|participants?)',  # Counts
        r'\bscored?\s+(\d+(?:\.\d+)?)',  # Scores
        r'\b(\d+)\s+(?:concepts?|ideas?|questions?)',  # Concept counts
    ]

    # Patterns indicating temporal claims
    TEMPORAL_PATTERNS = [
        r'at\s+(\d+:\d+|\d+\s*(?:min|sec|minutes?|seconds?))',
        r'(?:first|last|early|late|beginning|end)\s+(?:part|half|portion)',
        r'(?:before|after|during|throughout)',
    ]

    def __init__(self):
        """Initialize the validator."""
        pass

    def validate_response(
        self,
        answer: str,
        tool_results: List[Dict],
        reasoning_trace: List[str]
    ) -> GroundedResponse:
        """
        Validate that a response is grounded in evidence.

        Args:
            answer: The generated answer
            tool_results: Results from tool executions
            reasoning_trace: The agent's reasoning steps

        Returns:
            GroundedResponse with validation results
        """
        # Extract citations from tool results
        citations = self._extract_citations(tool_results)

        # Check for ungrounded claims
        ungrounded = self._find_ungrounded_claims(answer, citations, tool_results)

        # Calculate confidence
        confidence = self._calculate_confidence(citations, ungrounded, tool_results)

        # Generate follow-up suggestions
        suggestions = self._generate_suggestions(answer, tool_results)

        return GroundedResponse(
            answer=answer,
            citations=citations,
            confidence=confidence,
            reasoning_trace=reasoning_trace,
            follow_up_suggestions=suggestions,
            ungrounded_claims=ungrounded,
            is_grounded=len(ungrounded) == 0 and confidence >= 0.5
        )

    def _extract_citations(self, tool_results: List[Dict]) -> List[Citation]:
        """Extract citations from tool results."""
        citations = []

        for result in tool_results:
            if not result.get('success'):
                continue

            data = result.get('data') or {}  # Handle None values
            if not isinstance(data, dict):
                continue
            tool_name = result.get('tool_name', '')

            # Handle different result types
            if 'transcripts' in data:
                citations.extend(self._extract_transcript_citations(data))
            elif 'nodes' in data:
                citations.extend(self._extract_concept_citations(data))
            elif 'dimensions' in data:
                citations.extend(self._extract_7c_citations(data))
            elif 'results' in data:
                citations.extend(self._extract_search_citations(data, tool_name))
            elif 'neighbors' in data:
                citations.extend(self._extract_graph_citations(data))

        return citations

    def _extract_transcript_citations(self, data: Dict) -> List[Citation]:
        """Extract citations from transcript data."""
        citations = []

        for transcript in data.get('transcripts', [])[:10]:
            if isinstance(transcript, dict) and transcript.get('text'):
                citations.append(Citation(
                    claim="",  # Will be matched later
                    artifact_type="transcript",
                    artifact_id=str(data.get('session_device_id', '')),
                    excerpt=transcript['text'][:300],
                    source_timestamps=[transcript.get('start_time')] if transcript.get('start_time') else None
                ))

        return citations

    def _extract_concept_citations(self, data: Dict) -> List[Citation]:
        """Extract citations from concept map data."""
        citations = []

        for node in data.get('nodes', [])[:20]:
            if isinstance(node, dict) and node.get('text'):
                citations.append(Citation(
                    claim="",
                    artifact_type="concept_map",
                    artifact_id=str(data.get('session_device_id', '')),
                    excerpt=f"{node.get('node_type', 'concept')}: {node['text'][:200]}"
                ))

        return citations

    def _extract_7c_citations(self, data: Dict) -> List[Citation]:
        """Extract citations from 7C analysis data."""
        citations = []

        for dim, dim_data in data.get('dimensions', {}).items():
            if isinstance(dim_data, dict):
                score = dim_data.get('score', 0)
                evidence = dim_data.get('evidence', [])
                excerpt = f"{dim}: score {score}"
                if evidence:
                    excerpt += f" - {evidence[0][:200]}" if evidence[0] else ""

                citations.append(Citation(
                    claim="",
                    artifact_type="seven_c",
                    artifact_id=str(data.get('session_device_id', '')),
                    excerpt=excerpt,
                    confidence=0.9  # 7C data is reliable
                ))

        return citations

    def _extract_search_citations(self, data: Dict, tool_name: str) -> List[Citation]:
        """Extract citations from search results."""
        citations = []

        # Ensure we have a proper list to iterate
        results = data.get('results', []) if isinstance(data, dict) else []
        if not isinstance(results, list):
            results = list(results) if hasattr(results, '__iter__') else []

        for result in results[:10]:
            if not isinstance(result, dict):
                continue

            excerpt = (
                result.get('text') or
                result.get('chunk_text') or
                result.get('node_text') or
                result.get('content', '')
            )[:300]

            # Determine artifact type from tool name
            if 'transcript' in tool_name or 'chunk' in tool_name:
                artifact_type = "transcript"
            elif 'concept' in tool_name or 'node' in tool_name:
                artifact_type = "concept_map"
            elif 'cluster' in tool_name:
                artifact_type = "concept_cluster"
            else:
                artifact_type = "search_result"

            citations.append(Citation(
                claim="",
                artifact_type=artifact_type,
                artifact_id=str(result.get('session_device_id', '')),
                excerpt=excerpt,
                confidence=1.0 - result.get('distance', 0)  # Convert distance to confidence
            ))

        return citations

    def _extract_graph_citations(self, data: Dict) -> List[Citation]:
        """Extract citations from graph traversal results."""
        citations = []

        # Ensure we have a proper list to iterate
        neighbors = data.get('neighbors', []) if isinstance(data, dict) else []
        if not isinstance(neighbors, list):
            neighbors = list(neighbors) if hasattr(neighbors, '__iter__') else []

        for node in neighbors[:10]:
            if isinstance(node, dict) and node.get('text'):
                citations.append(Citation(
                    claim="",
                    artifact_type="concept_graph",
                    artifact_id=str(node.get('id', '')),
                    excerpt=f"{node.get('node_type', 'node')}: {node['text'][:200]}"
                ))

        return citations

    def _find_ungrounded_claims(
        self,
        answer: str,
        citations: List[Citation],
        tool_results: List[Dict]
    ) -> List[str]:
        """Find claims in the answer that aren't supported by evidence."""
        ungrounded = []

        # Check quantitative claims
        for pattern in self.QUANTITATIVE_PATTERNS:
            matches = re.findall(pattern, answer, re.IGNORECASE)
            for match in matches:
                if not self._verify_quantitative_claim(match, tool_results):
                    claim = self._extract_surrounding_text(answer, match)
                    if claim not in ungrounded:
                        ungrounded.append(claim)

        # Check for fabricated session references
        session_refs = re.findall(r'session\s+(\d+)', answer, re.IGNORECASE)
        known_sessions = self._get_known_sessions(tool_results)
        for ref in session_refs:
            if ref not in known_sessions:
                ungrounded.append(f"Reference to session {ref}")

        return ungrounded

    def _verify_quantitative_claim(
        self,
        value: str,
        tool_results: List[Dict]
    ) -> bool:
        """Verify a quantitative claim against tool results."""
        # Search for the value in any tool result
        for result in tool_results:
            data = result.get('data') or {}  # Handle None values
            if self._contains_value(data, value):
                return True
        return False

    def _contains_value(self, data: Any, value: str) -> bool:
        """Check if data contains the given value."""
        if isinstance(data, dict):
            for v in data.values():
                if self._contains_value(v, value):
                    return True
        elif isinstance(data, list):
            for item in data:
                if self._contains_value(item, value):
                    return True
        elif str(data) == str(value):
            return True
        return False

    def _extract_surrounding_text(self, text: str, match: str) -> str:
        """Extract text surrounding a match for context."""
        idx = text.find(match)
        if idx == -1:
            return match
        start = max(0, idx - 30)
        end = min(len(text), idx + len(match) + 30)
        return text[start:end].strip()

    def _get_known_sessions(self, tool_results: List[Dict]) -> set:
        """Get all session IDs mentioned in tool results."""
        sessions = set()
        for result in tool_results:
            data = result.get('data') or {}  # Handle None values
            if not isinstance(data, dict):
                continue
            if 'session_device_id' in data:
                sessions.add(str(data['session_device_id']))
            if 'results' in data:
                for item in data.get('results') or []:
                    if isinstance(item, dict) and 'session_device_id' in item:
                        sessions.add(str(item['session_device_id']))
        return sessions

    def _calculate_confidence(
        self,
        citations: List[Citation],
        ungrounded: List[str],
        tool_results: List[Dict]
    ) -> float:
        """Calculate overall response confidence."""
        if not citations and not tool_results:
            return 0.3  # Low confidence if no evidence

        # Base confidence on citations
        if citations:
            avg_citation_confidence = sum(c.confidence for c in citations) / len(citations)
        else:
            avg_citation_confidence = 0.5

        # Penalize for ungrounded claims
        ungrounded_penalty = min(0.3, len(ungrounded) * 0.1)

        # Boost for successful tool calls
        successful_tools = sum(1 for r in tool_results if r.get('success'))
        tool_boost = min(0.2, successful_tools * 0.05)

        confidence = avg_citation_confidence - ungrounded_penalty + tool_boost
        return max(0.0, min(1.0, confidence))

    def _generate_suggestions(
        self,
        answer: str,
        tool_results: List[Dict]
    ) -> List[str]:
        """Generate follow-up question suggestions."""
        suggestions = []

        # Analyze what was retrieved (handle None data values)
        has_transcripts = any('transcripts' in (r.get('data') or {}) for r in tool_results)
        has_concepts = any('nodes' in (r.get('data') or {}) for r in tool_results)
        has_7c = any('dimensions' in (r.get('data') or {}) for r in tool_results)
        has_comparison = any('comparison' in r.get('tool_name', '') for r in tool_results)

        # Suggest based on what wasn't explored
        if not has_concepts and has_transcripts:
            suggestions.append("What concepts or ideas emerged from this discussion?")

        if not has_7c and has_transcripts:
            suggestions.append("How was the collaboration quality in this session?")

        if has_concepts and not has_transcripts:
            suggestions.append("What did students actually say about these concepts?")

        if not has_comparison:
            suggestions.append("How does this compare to other sessions?")

        # Suggest deeper exploration
        if 'speaker' in answer.lower() or 'student' in answer.lower():
            suggestions.append("Who were the most active contributors?")

        if 'concept' in answer.lower() or 'idea' in answer.lower():
            suggestions.append("What concepts are related to this?")

        return suggestions[:3]  # Return top 3


class CitationFormatter:
    """Formats citations for display."""

    @staticmethod
    def format_inline(citation: Citation) -> str:
        """Format citation for inline display."""
        if citation.artifact_type == "transcript":
            if citation.source_timestamps:
                ts = citation.source_timestamps[0]
                return f"[Session {citation.artifact_id}, {int(ts//60)}:{int(ts%60):02d}]"
            return f"[Session {citation.artifact_id}]"
        elif citation.artifact_type == "seven_c":
            return f"[7C Analysis]"
        elif citation.artifact_type == "concept_map":
            return f"[Concept Map, Session {citation.artifact_id}]"
        else:
            return f"[{citation.artifact_type}]"

    @staticmethod
    def format_footnote(citations: List[Citation]) -> str:
        """Format citations as footnotes."""
        footnotes = []
        for i, citation in enumerate(citations, 1):
            source = CitationFormatter.format_inline(citation)
            footnotes.append(f"[{i}] {source}: {citation.excerpt[:100]}...")
        return "\n".join(footnotes)


class ResponseFormatter:
    """
    Formats agent responses with confidence indicators and source transparency.

    Provides user-friendly confidence communication when results are uncertain.
    """

    # Confidence thresholds
    HIGH_CONFIDENCE_THRESHOLD = 0.7
    MEDIUM_CONFIDENCE_THRESHOLD = 0.4

    @classmethod
    def format_response_with_confidence(
        cls,
        grounded_response: GroundedResponse
    ) -> GroundedResponse:
        """
        Enhance response with confidence indicator if needed.

        Args:
            grounded_response: The grounded response to format

        Returns:
            GroundedResponse with potentially modified answer
        """
        answer = grounded_response.answer

        # Add confidence indicator if low
        if grounded_response.confidence < cls.HIGH_CONFIDENCE_THRESHOLD:
            confidence_note = cls._get_confidence_note(grounded_response.confidence)
            if confidence_note:
                answer = f"{answer}\n\n{confidence_note}"

        # Add source transparency
        if grounded_response.citations:
            source_note = cls._get_source_note(grounded_response.citations)
            answer = f"{answer}\n\n{source_note}"

        # Return updated response
        return GroundedResponse(
            answer=answer,
            citations=grounded_response.citations,
            confidence=grounded_response.confidence,
            reasoning_trace=grounded_response.reasoning_trace,
            follow_up_suggestions=grounded_response.follow_up_suggestions,
            ungrounded_claims=grounded_response.ungrounded_claims,
            is_grounded=grounded_response.is_grounded
        )

    @classmethod
    def _get_confidence_note(cls, confidence: float) -> str:
        """Generate appropriate confidence note based on score."""
        if confidence < cls.MEDIUM_CONFIDENCE_THRESHOLD:
            return ("*Note: I'm not very confident about this answer. "
                   "The search results weren't strongly related to your query. "
                   "You might want to rephrase or ask about a different aspect.*")
        elif confidence < cls.HIGH_CONFIDENCE_THRESHOLD:
            return ("*Note: This answer is based on partially matching results. "
                   "Let me know if you'd like me to clarify or search differently.*")
        return ""

    @classmethod
    def _get_source_note(cls, citations: List[Citation]) -> str:
        """Generate source transparency note."""
        if not citations:
            return ""

        # Count unique sources
        unique_sources = set()
        source_types = set()

        for citation in citations:
            unique_sources.add(citation.artifact_id)
            source_types.add(citation.artifact_type)

        # Format source summary
        source_count = len(unique_sources)
        type_names = {
            'transcript': 'transcript',
            'concept_map': 'concept map',
            'seven_c': '7C analysis',
            'liwc': 'LIWC metrics',
            'search_result': 'search result',
            'concept_graph': 'concept graph',
            'concept_cluster': 'concept cluster'
        }

        type_list = [type_names.get(t, t) for t in source_types]
        type_str = ', '.join(type_list[:3])

        if source_count == 1:
            return f"*Based on 1 source ({type_str})*"
        else:
            return f"*Based on {source_count} sources ({type_str})*"

    @classmethod
    def get_confidence_level(cls, confidence: float) -> str:
        """Get human-readable confidence level."""
        if confidence >= cls.HIGH_CONFIDENCE_THRESHOLD:
            return "high"
        elif confidence >= cls.MEDIUM_CONFIDENCE_THRESHOLD:
            return "medium"
        else:
            return "low"

    @classmethod
    def should_warn_user(cls, confidence: float) -> bool:
        """Check if we should warn the user about low confidence."""
        return confidence < cls.HIGH_CONFIDENCE_THRESHOLD

    @classmethod
    def format_error_response(cls, error_message: str, suggestions: List[str] = None) -> Dict:
        """
        Format an error response with helpful suggestions.

        Args:
            error_message: The error message to display
            suggestions: Optional list of helpful suggestions

        Returns:
            Formatted response dictionary
        """
        response = {
            "answer": error_message,
            "citations": [],
            "confidence": 0.0,
            "is_error": True
        }

        if suggestions:
            response["follow_up_suggestions"] = suggestions

        return response
