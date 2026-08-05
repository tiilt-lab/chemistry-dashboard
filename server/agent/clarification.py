"""
Clarification Engine

Handles ambiguous queries by asking smart clarifying questions.
Detects when clarification is needed and generates appropriate questions.
"""

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


class ClarificationType(str, Enum):
    """Types of clarification needed."""
    MULTIPLE_SESSIONS = "multiple_sessions"
    MULTIPLE_SPEAKERS = "multiple_speakers"
    AMBIGUOUS_REFERENCE = "ambiguous_reference"
    MISSING_CONTEXT = "missing_context"
    LOW_CONFIDENCE = "low_confidence"
    VAGUE_QUERY = "vague_query"
    NO_RESULTS = "no_results"


@dataclass
class ClarificationRequest:
    """A request for user clarification."""
    clarification_type: ClarificationType
    question: str
    options: Optional[List[str]] = None  # For quick-reply buttons
    context: Optional[Dict] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "clarification_type": self.clarification_type.value,
            "question": self.question,
            "options": self.options,
            "context": self.context
        }


@dataclass
class PendingClarification:
    """Stored state for pending clarification."""
    original_query: str
    clarification_type: ClarificationType
    options_map: Dict[str, Any] = field(default_factory=dict)  # Maps option text to resolved value
    expires_at: float = 0.0  # Timestamp
    context: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage."""
        return {
            "original_query": self.original_query,
            "clarification_type": self.clarification_type.value,
            "options_map": self.options_map,
            "expires_at": self.expires_at,
            "context": self.context
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'PendingClarification':
        """Create from dictionary."""
        return cls(
            original_query=data.get("original_query", ""),
            clarification_type=ClarificationType(data.get("clarification_type", "vague_query")),
            options_map=data.get("options_map", {}),
            expires_at=data.get("expires_at", 0.0),
            context=data.get("context", {})
        )

    def is_expired(self) -> bool:
        """Check if this clarification has expired."""
        return time.time() > self.expires_at


class ClarificationEngine:
    """
    Detects when clarification is needed and generates appropriate questions.

    Handles:
    - Multiple session matches (which session?)
    - Multiple speaker matches (which speaker?)
    - Ambiguous references ("that session", "they")
    - Low confidence retrieval results
    - Missing required context
    """

    # References that need context to resolve
    AMBIGUOUS_REFERENCES = {
        'session': ['that session', 'this session', 'the session', 'that discussion',
                   'this discussion', 'the discussion', 'it', 'that one'],
        'speaker': ['that student', 'the student', 'they', 'the speaker',
                   'that speaker', 'he', 'she', 'the participant', 'that person'],
        'concept': ['that concept', 'the concept', 'that idea', 'the idea',
                   'that topic', 'the topic', 'it', 'that'],
    }

    # Default clarification expiry (5 minutes)
    DEFAULT_EXPIRY_SECONDS = 300

    def __init__(self, entity_resolver=None):
        """
        Args:
            entity_resolver: EntityResolver instance for session/speaker lookup
        """
        self.entity_resolver = entity_resolver

    def check_needs_clarification(
        self,
        query: str,
        classification: Any = None,  # Classification from classifier.py
        conversation_state: Optional[Dict] = None
    ) -> Optional[ClarificationRequest]:
        """
        Check if a query needs clarification before processing.

        Args:
            query: User's query
            classification: Classification result from classifier.py
            conversation_state: Current conversation state

        Returns:
            ClarificationRequest if needed, None otherwise
        """
        query_lower = query.lower()

        # Check for ambiguous references without conversation context
        if not conversation_state or not conversation_state.get('current_session_focus'):
            for ref_type, refs in self.AMBIGUOUS_REFERENCES.items():
                for ref in refs:
                    # Use word boundary matching to avoid false positives like "the" matching "he"
                    pattern = r'\b' + re.escape(ref) + r'\b'
                    if re.search(pattern, query_lower):
                        # Check if we have context to resolve this
                        if ref_type == 'session' and not self._has_session_context(conversation_state):
                            return ClarificationRequest(
                                clarification_type=ClarificationType.AMBIGUOUS_REFERENCE,
                                question=f"I'm not sure which session you're referring to. Could you specify which session you mean?",
                                options=self._get_recent_session_options(),
                                context={"reference_type": ref_type, "reference": ref}
                            )
                        elif ref_type == 'speaker' and not self._has_speaker_context(conversation_state):
                            return ClarificationRequest(
                                clarification_type=ClarificationType.AMBIGUOUS_REFERENCE,
                                question=f"Which speaker are you asking about?",
                                options=None,  # Speakers need session context first
                                context={"reference_type": ref_type, "reference": ref}
                            )

        # Check classification for multiple entity matches
        if classification and hasattr(classification, 'entities'):
            entities = classification.entities

            # First check if we have resolved session IDs - if so, no clarification needed
            session_ids = getattr(entities, 'session_device_ids', [])
            if session_ids:
                # Session IDs are already resolved (either explicit or via name resolution)
                # No need for clarification
                logger.debug(f"Session IDs already resolved: {session_ids}, skipping clarification")
                return None

            # Multiple session NAMES mentioned but no resolved IDs
            if hasattr(entities, 'sessions') and len(getattr(entities, 'sessions', [])) > 1:
                return self._create_session_clarification(entities.sessions, query)

            # Multiple speakers but query needs specific one
            if hasattr(entities, 'speakers') and len(getattr(entities, 'speakers', [])) > 1:
                # Check if query is asking about a specific speaker
                singular_indicators = ['who', 'which speaker', 'that speaker', 'the speaker']
                if any(ind in query_lower for ind in singular_indicators):
                    return self._create_speaker_clarification(entities.speakers, query)

        return None

    def check_post_retrieval_clarification(
        self,
        query: str,
        results: List[Dict],
        confidence: float = 1.0
    ) -> Optional[ClarificationRequest]:
        """
        Check if clarification is needed based on retrieval results.

        Args:
            query: Original query
            results: Search results
            confidence: Overall retrieval confidence

        Returns:
            ClarificationRequest if needed
        """
        # No results found
        if not results:
            return ClarificationRequest(
                clarification_type=ClarificationType.NO_RESULTS,
                question="I couldn't find any relevant information for that query. Would you like to try something different?",
                options=[
                    "Try a different search term",
                    "See what topics are in my sessions",
                    "Show me recent sessions"
                ]
            )

        # Very low confidence
        if confidence < 0.3:
            return ClarificationRequest(
                clarification_type=ClarificationType.LOW_CONFIDENCE,
                question="I found some results, but I'm not confident they match what you're looking for. Could you be more specific?",
                options=[
                    "Show me what you found anyway",
                    "Let me rephrase my question",
                    "What topics do my sessions cover?"
                ]
            )

        # Results span many sessions - offer to narrow down
        unique_sessions = set(r.get('session_device_id') for r in results if r.get('session_device_id'))
        if len(unique_sessions) > 5:
            session_names = self._get_session_names(list(unique_sessions)[:4])
            return ClarificationRequest(
                clarification_type=ClarificationType.MULTIPLE_SESSIONS,
                question=f"I found results across {len(unique_sessions)} different sessions. Would you like me to focus on a specific one?",
                options=session_names + ["Show results from all sessions"],
                context={"session_ids": list(unique_sessions)}
            )

        return None

    def _has_session_context(self, conversation_state: Optional[Dict]) -> bool:
        """Check if conversation has session context."""
        if not conversation_state:
            return False
        return bool(conversation_state.get('current_session_focus'))

    def _has_speaker_context(self, conversation_state: Optional[Dict]) -> bool:
        """Check if conversation has speaker context."""
        if not conversation_state:
            return False
        return bool(conversation_state.get('current_speaker_focus'))

    def _create_session_clarification(self, sessions: List[str], query: str) -> ClarificationRequest:
        """Create clarification for multiple session matches."""
        if len(sessions) <= 5:
            options = list(sessions)
            if len(sessions) > 1:
                options.append("Compare all of them")
        else:
            options = sessions[:4] + [f"Show all {len(sessions)} sessions"]

        return ClarificationRequest(
            clarification_type=ClarificationType.MULTIPLE_SESSIONS,
            question="I found several sessions that might match. Which one are you asking about?",
            options=options,
            context={"matched_sessions": sessions}
        )

    def _create_speaker_clarification(self, speakers: List[str], query: str) -> ClarificationRequest:
        """Create clarification for multiple speaker matches."""
        options = list(speakers[:5])
        if len(speakers) > 1:
            options.append("Compare all speakers")

        return ClarificationRequest(
            clarification_type=ClarificationType.MULTIPLE_SPEAKERS,
            question="Which speaker are you asking about?",
            options=options,
            context={"matched_speakers": speakers}
        )

    def _get_recent_session_options(self) -> Optional[List[str]]:
        """Get recent session options for clarification."""
        # This would ideally query recent sessions from database
        # For now, return generic options
        return [
            "The most recent session",
            "Today's session",
            "Let me specify the session name"
        ]

    def _get_session_names(self, session_ids: List[int]) -> List[str]:
        """Get session names from IDs."""
        if self.entity_resolver:
            try:
                names = []
                for sid in session_ids:
                    # Try to get session name from resolver
                    name = f"Session {sid}"  # Fallback
                    names.append(name)
                return names
            except Exception as e:
                logger.warning(f"Error getting session names: {e}")

        return [f"Session {sid}" for sid in session_ids]

    def create_pending_clarification(
        self,
        original_query: str,
        clarification_request: ClarificationRequest
    ) -> PendingClarification:
        """
        Create a pending clarification to store in conversation state.

        Args:
            original_query: The user's original query
            clarification_request: The clarification we're asking for

        Returns:
            PendingClarification object to store
        """
        # Build options map
        options_map = {}
        if clarification_request.options:
            for i, option in enumerate(clarification_request.options):
                options_map[option.lower()] = {
                    "index": i,
                    "value": option,
                    "context": clarification_request.context
                }

        return PendingClarification(
            original_query=original_query,
            clarification_type=clarification_request.clarification_type,
            options_map=options_map,
            expires_at=time.time() + self.DEFAULT_EXPIRY_SECONDS,
            context=clarification_request.context or {}
        )

    def resolve_clarification_response(
        self,
        response: str,
        pending: PendingClarification
    ) -> Dict[str, Any]:
        """
        Resolve a user's response to a clarification question.

        Args:
            response: User's response
            pending: The pending clarification state

        Returns:
            Dict with resolution status and modified query
        """
        if pending.is_expired():
            logger.debug("Pending clarification has expired")
            return {
                "resolved": False,
                "expired": True,
                "original_query": pending.original_query
            }

        response_lower = response.lower().strip()

        # Check for "show anyway" type responses
        show_anyway_phrases = ["show me what you found", "show anyway", "show results", "show all"]
        if any(phrase in response_lower for phrase in show_anyway_phrases):
            return {
                "resolved": True,
                "action": "proceed_anyway",
                "original_query": pending.original_query
            }

        # Check for "rephrase" type responses
        rephrase_phrases = ["rephrase", "let me rephrase", "different", "try again"]
        if any(phrase in response_lower for phrase in rephrase_phrases):
            return {
                "resolved": True,
                "action": "await_rephrase",
                "message": "No problem! Please ask your question in a different way."
            }

        # Check if response matches an option
        for option_key, option_data in pending.options_map.items():
            if option_key in response_lower or response_lower in option_key:
                logger.debug(f"Matched clarification option: {option_key}")
                return {
                    "resolved": True,
                    "action": "use_selection",
                    "selected_option": option_data["value"],
                    "modified_query": self._inject_resolution(
                        pending.original_query,
                        option_data["value"],
                        pending.clarification_type
                    ),
                    "context": option_data.get("context", {})
                }

        # Check if response contains a number (selecting by index)
        import re
        number_match = re.search(r'\b(\d+)\b', response_lower)
        if number_match:
            index = int(number_match.group(1)) - 1  # Convert to 0-indexed
            if 0 <= index < len(pending.options_map):
                option_key = list(pending.options_map.keys())[index]
                option_data = pending.options_map[option_key]
                return {
                    "resolved": True,
                    "action": "use_selection",
                    "selected_option": option_data["value"],
                    "modified_query": self._inject_resolution(
                        pending.original_query,
                        option_data["value"],
                        pending.clarification_type
                    )
                }

        # Response doesn't match known options - treat as new query with context
        logger.debug(f"Clarification response doesn't match options, treating as contextual query")
        return {
            "resolved": True,
            "action": "new_query_with_context",
            "new_query": response,
            "original_context": pending.context
        }

    def _inject_resolution(
        self,
        original_query: str,
        resolved_value: str,
        clarification_type: ClarificationType
    ) -> str:
        """Modify query to include resolved entity."""
        # Clean up the resolved value
        resolved_clean = resolved_value.strip()

        if clarification_type == ClarificationType.MULTIPLE_SESSIONS:
            # Replace ambiguous session references
            for ref in self.AMBIGUOUS_REFERENCES['session']:
                if ref in original_query.lower():
                    return original_query.lower().replace(ref, f'session "{resolved_clean}"')
            # If no reference found, append
            return f"{original_query} (in {resolved_clean})"

        elif clarification_type == ClarificationType.MULTIPLE_SPEAKERS:
            # Replace ambiguous speaker references
            for ref in self.AMBIGUOUS_REFERENCES['speaker']:
                if ref in original_query.lower():
                    return original_query.lower().replace(ref, resolved_clean)
            return f"{original_query} (speaker: {resolved_clean})"

        elif clarification_type == ClarificationType.AMBIGUOUS_REFERENCE:
            # Generic reference resolution
            return f"{original_query} ({resolved_clean})"

        return f"{original_query} - {resolved_clean}"
