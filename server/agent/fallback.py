"""
Tiered Fallback Handler

Handles failures gracefully with escalating responses.
Provides a 3-tier escalation system:
  Tier 1: Ask for rephrasing
  Tier 2: Show capability menu
  Tier 3: Offer example questions
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import IntEnum

logger = logging.getLogger(__name__)


class FallbackTier(IntEnum):
    """Escalation tiers for fallback."""
    TIER_1_REPHRASE = 1      # Ask user to rephrase
    TIER_2_CAPABILITIES = 2   # Show what bot can do
    TIER_3_EXAMPLES = 3       # Offer example questions


@dataclass
class FallbackResponse:
    """A fallback response."""
    tier: FallbackTier
    message: str
    suggestions: List[str]
    is_terminal: bool = False  # If true, don't escalate further

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "tier": self.tier.value,
            "message": self.message,
            "suggestions": self.suggestions,
            "is_terminal": self.is_terminal
        }


class TieredFallbackHandler:
    """
    Handles failures with escalating fallback tiers.

    Tier 1: Ask for rephrasing (first failure)
    Tier 2: Show capability menu (second failure)
    Tier 3: Offer clickable example questions (third+ failure)

    Failure counts are tracked per conversation and reset on successful queries.
    """

    # Maximum failures before terminal state
    MAX_FAILURES = 3

    # Error types that map to specific tier 1 messages
    ERROR_MESSAGES = {
        "no_results": "I couldn't find any relevant information for that query. Could you try rephrasing or being more specific?",
        "ambiguous": "I'm not sure I understood your question correctly. Could you rephrase it?",
        "low_confidence": "I found some results, but I'm not confident they match what you're looking for. Could you be more specific?",
        "tool_error": "I encountered an issue while searching. Could you try asking in a different way?",
        "timeout": "The search took too long. Could you try a simpler or more specific query?",
        "general": "I had trouble understanding that. Could you try asking in a different way?",
    }

    def __init__(self):
        """Initialize the handler with failure tracking."""
        self.failure_counts: Dict[str, int] = {}  # conversation_id -> count
        self.last_error_types: Dict[str, str] = {}  # conversation_id -> last error type

    def get_fallback(
        self,
        conversation_id: str,
        error_type: str = "general",
        original_query: str = "",
        context: Optional[Dict] = None
    ) -> FallbackResponse:
        """
        Get appropriate fallback response based on failure count.

        Args:
            conversation_id: Conversation ID for tracking
            error_type: Type of error that occurred
            original_query: The query that failed
            context: Optional additional context

        Returns:
            FallbackResponse with appropriate tier
        """
        # Increment failure count
        count = self.failure_counts.get(conversation_id, 0) + 1
        self.failure_counts[conversation_id] = count
        self.last_error_types[conversation_id] = error_type

        logger.debug(f"Fallback triggered for conversation {conversation_id}: "
                    f"count={count}, error_type={error_type}")

        if count == 1:
            return self._tier_1_rephrase(error_type, original_query)
        elif count == 2:
            return self._tier_2_capabilities()
        else:
            return self._tier_3_examples()

    def get_failure_count(self, conversation_id: str) -> int:
        """Get current failure count for a conversation."""
        return self.failure_counts.get(conversation_id, 0)

    def reset_failures(self, conversation_id: str) -> None:
        """Reset failure count after successful interaction."""
        if conversation_id in self.failure_counts:
            logger.debug(f"Resetting failure count for conversation {conversation_id}")
            del self.failure_counts[conversation_id]
        if conversation_id in self.last_error_types:
            del self.last_error_types[conversation_id]

    def should_show_examples(self, conversation_id: str) -> bool:
        """Check if we should proactively show examples."""
        return self.failure_counts.get(conversation_id, 0) >= 2

    def _tier_1_rephrase(self, error_type: str, query: str) -> FallbackResponse:
        """Tier 1: Ask user to rephrase."""
        message = self.ERROR_MESSAGES.get(error_type, self.ERROR_MESSAGES["general"])

        # Customize suggestions based on error type
        if error_type == "no_results":
            suggestions = [
                "Try using different keywords",
                "Ask about a specific session",
                "What topics are in my sessions?"
            ]
        elif error_type == "ambiguous":
            suggestions = [
                "Specify a session or speaker name",
                "Ask about a specific topic",
                "What can you help me with?"
            ]
        elif error_type == "low_confidence":
            suggestions = [
                "Show me what you found anyway",
                "Let me try different keywords",
                "What sessions do I have?"
            ]
        else:
            suggestions = [
                "Try a different question",
                "Ask about a specific session",
                "What can you help me with?"
            ]

        return FallbackResponse(
            tier=FallbackTier.TIER_1_REPHRASE,
            message=message,
            suggestions=suggestions
        )

    def _tier_2_capabilities(self) -> FallbackResponse:
        """Tier 2: Show capability menu."""
        message = """I'm still having trouble understanding. Here's what I can help with:

**I can analyze:**
- **Transcripts** - What students said about topics
- **Concept Maps** - Ideas and how they connect
- **7C Scores** - Collaboration quality metrics
- **Speakers** - Participation and engagement patterns

**I can answer questions like:**
- "What was discussed in today's session?"
- "How did the collaboration quality compare?"
- "Who contributed the most ideas?"

Which area would you like to explore?"""

        return FallbackResponse(
            tier=FallbackTier.TIER_2_CAPABILITIES,
            message=message,
            suggestions=[
                "Analyze transcripts",
                "Explore concept maps",
                "Check collaboration scores",
                "Look at speaker patterns"
            ]
        )

    def _tier_3_examples(self) -> FallbackResponse:
        """Tier 3: Offer specific example questions."""
        message = "Let me suggest some specific questions you can try:"

        examples = [
            "What did students discuss in the most recent session?",
            "Show me the collaboration scores for my sessions",
            "What concepts emerged from today's discussion?",
            "Compare the two most recent sessions",
            "Who were the most active participants?"
        ]

        return FallbackResponse(
            tier=FallbackTier.TIER_3_EXAMPLES,
            message=message,
            suggestions=examples,
            is_terminal=True  # Don't escalate further
        )

    def get_contextual_suggestions(
        self,
        conversation_id: str,
        context: Optional[Dict] = None
    ) -> List[str]:
        """
        Get contextual suggestions based on conversation state.

        Args:
            conversation_id: Conversation ID
            context: Optional context with session/speaker info

        Returns:
            List of relevant suggestions
        """
        suggestions = []

        if context:
            session_id = context.get('current_session_focus')
            speaker_id = context.get('current_speaker_focus')

            if session_id:
                suggestions.extend([
                    f"What was discussed in this session?",
                    f"Show me the concept map",
                    f"How was the collaboration?",
                ])
            elif speaker_id:
                suggestions.extend([
                    f"What did this speaker contribute?",
                    f"Show their participation metrics",
                ])

        # Add general suggestions if we don't have enough
        if len(suggestions) < 3:
            suggestions.extend([
                "Show me recent sessions",
                "What topics were discussed?",
                "Compare sessions",
            ])

        return suggestions[:5]  # Return max 5 suggestions


class ErrorClassifier:
    """
    Classifies errors into types for appropriate fallback handling.
    """

    @staticmethod
    def classify_error(error: Exception, context: Optional[Dict] = None) -> str:
        """
        Classify an error into a fallback error type.

        Args:
            error: The exception that occurred
            context: Optional context about the error

        Returns:
            Error type string for fallback handler
        """
        error_str = str(error).lower()
        error_type = type(error).__name__

        # Timeout errors
        if 'timeout' in error_str or error_type == 'TimeoutError':
            return "timeout"

        # No results
        if 'no results' in error_str or 'not found' in error_str or 'empty' in error_str:
            return "no_results"

        # Ambiguity errors
        if 'ambiguous' in error_str or 'unclear' in error_str or 'multiple' in error_str:
            return "ambiguous"

        # Low confidence
        if 'confidence' in error_str or 'uncertain' in error_str:
            return "low_confidence"

        # Tool/API errors
        if 'api' in error_str or 'connection' in error_str or 'tool' in error_str:
            return "tool_error"

        return "general"

    @staticmethod
    def classify_response(
        response: Dict,
        results: Optional[List] = None,
        confidence: float = 1.0
    ) -> Optional[str]:
        """
        Classify a response to determine if fallback is needed.

        Args:
            response: The response dictionary
            results: Optional list of results
            confidence: Confidence score

        Returns:
            Error type if fallback needed, None otherwise
        """
        # No results
        if results is not None and len(results) == 0:
            return "no_results"

        # Low confidence
        if confidence < 0.3:
            return "low_confidence"

        # Check response for error indicators
        if response.get('error'):
            return "general"

        if not response.get('success', True):
            return "tool_error"

        return None  # No fallback needed
