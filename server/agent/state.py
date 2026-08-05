"""
Conversation State Management

Manages runtime state for agent conversations using Redis.
Tracks context across turns for coherent multi-turn dialogue.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
import redis

logger = logging.getLogger(__name__)

# Redis key prefix
REDIS_STATE_PREFIX = "agent:state:"
REDIS_STATE_TTL = 86400  # 24 hours


@dataclass
class ArtifactRef:
    """Reference to an artifact mentioned in conversation."""
    artifact_type: str  # transcript, concept_map, seven_c, liwc, cluster, node
    artifact_id: str  # session_device_id, node_id, cluster_id, etc.
    excerpt: Optional[str] = None
    timestamp: Optional[float] = None


@dataclass
class ConversationState:
    """
    Tracks context across turns for coherent dialogue.

    Stored in Redis with 24-hour TTL for persistence across
    browser sessions while allowing cleanup of stale data.
    """

    conversation_id: str
    current_session_focus: Optional[int] = None  # Active session_device_id
    current_speaker_focus: Optional[int] = None  # Active speaker_id
    referenced_artifacts: List[Dict] = field(default_factory=list)  # Recent artifacts
    established_findings: Dict[str, Any] = field(default_factory=dict)  # Key facts
    turn_count: int = 0
    last_query: Optional[str] = None
    last_tools_used: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    # Conversational UX: pending clarification from the agent
    pending_clarification: Optional[Dict] = None  # Stores pending clarification request
    failure_count: int = 0  # Tracks consecutive failures for tiered fallback
    # Session history for ordinal references ("first session", "previous session")
    session_history: List[int] = field(default_factory=list)  # Sessions mentioned in order
    compared_sessions: List[int] = field(default_factory=list)  # Sessions from last comparison
    previous_session_focus: Optional[int] = None  # For "go back" references

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'ConversationState':
        """Create from dictionary."""
        return cls(**data)

    def add_artifact_reference(self, artifact_type: str, artifact_id: str,
                                excerpt: str = None):
        """Add a referenced artifact."""
        ref = {
            "artifact_type": artifact_type,
            "artifact_id": str(artifact_id),
            "excerpt": excerpt,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.referenced_artifacts.append(ref)

        # Keep only last 20 references
        if len(self.referenced_artifacts) > 20:
            self.referenced_artifacts = self.referenced_artifacts[-20:]

    def set_session_focus(self, session_device_id: int):
        """Set the current session focus and track history."""
        # Save previous focus for "go back" references
        if self.current_session_focus and self.current_session_focus != session_device_id:
            self.previous_session_focus = self.current_session_focus

        self.current_session_focus = session_device_id

        # Add to session history if not already the most recent
        if not self.session_history or self.session_history[-1] != session_device_id:
            self.session_history.append(session_device_id)
            # Keep only last 10 sessions in history
            if len(self.session_history) > 10:
                self.session_history = self.session_history[-10:]

    def set_compared_sessions(self, session_ids: List[int]):
        """Set the list of sessions from a comparison operation."""
        self.compared_sessions = session_ids[:10]  # Limit to 10

    def set_speaker_focus(self, speaker_id: int):
        """Set the current speaker focus."""
        self.current_speaker_focus = speaker_id

    def add_finding(self, key: str, value: Any):
        """Add an established finding."""
        self.established_findings[key] = value

    def update_from_turn(self, query: str, tools_used: List[str]):
        """Update state after a conversation turn."""
        self.turn_count += 1
        self.last_query = query
        self.last_tools_used = tools_used
        self.updated_at = datetime.utcnow().isoformat()

    def get_context_summary(self) -> str:
        """Get a text summary of the current context for LLM prompts."""
        parts = []

        if self.current_session_focus:
            parts.append(f"Current session focus: session_device_id={self.current_session_focus}")

        if self.previous_session_focus:
            parts.append(f"Previous session: session_device_id={self.previous_session_focus}")

        if self.session_history:
            parts.append(f"Session history (in order): {self.session_history}")

        if self.compared_sessions:
            parts.append(f"Last compared sessions: {self.compared_sessions}")

        if self.current_speaker_focus:
            parts.append(f"Current speaker focus: speaker_id={self.current_speaker_focus}")

        if self.referenced_artifacts:
            recent = self.referenced_artifacts[-5:]
            refs = [f"{r['artifact_type']}:{r['artifact_id']}" for r in recent]
            parts.append(f"Recent artifacts: {', '.join(refs)}")

        if self.established_findings:
            findings = list(self.established_findings.items())[:5]
            parts.append("Established findings: " +
                        "; ".join([f"{k}={v}" for k, v in findings]))

        return "\n".join(parts) if parts else "No prior context established."

    def set_pending_clarification(self, clarification_data: Dict) -> None:
        """Set a pending clarification request."""
        self.pending_clarification = clarification_data
        self.updated_at = datetime.utcnow().isoformat()

    def clear_pending_clarification(self) -> None:
        """Clear the pending clarification."""
        self.pending_clarification = None
        self.updated_at = datetime.utcnow().isoformat()

    def has_pending_clarification(self) -> bool:
        """Check if there's a pending clarification."""
        if not self.pending_clarification:
            return False
        # Check expiry if present
        expires_at = self.pending_clarification.get('expires_at', 0)
        if expires_at and datetime.utcnow().timestamp() > expires_at:
            self.pending_clarification = None
            return False
        return True

    def increment_failure(self) -> int:
        """Increment failure count and return new value."""
        self.failure_count += 1
        self.updated_at = datetime.utcnow().isoformat()
        return self.failure_count

    def reset_failures(self) -> None:
        """Reset failure count after successful interaction."""
        self.failure_count = 0
        self.updated_at = datetime.utcnow().isoformat()


class ConversationStateManager:
    """
    Manages conversation state storage in Redis.

    Provides:
    - State persistence with TTL
    - State loading and saving
    - Reference resolution using state
    """

    def __init__(self, redis_client: redis.Redis = None):
        """
        Initialize the state manager.

        Args:
            redis_client: Optional Redis client. If not provided,
                         will use the global Redis connection.
        """
        if redis_client:
            self.redis = redis_client
        else:
            from redis_helper import r as redis_connection
            self.redis = redis_connection

    def _key(self, conversation_id: str) -> str:
        """Get Redis key for a conversation."""
        return f"{REDIS_STATE_PREFIX}{conversation_id}"

    def get_state(self, conversation_id: str) -> Optional[ConversationState]:
        """
        Load conversation state from Redis.

        Returns None if no state exists.
        """
        try:
            data = self.redis.get(self._key(conversation_id))
            if data:
                return ConversationState.from_dict(json.loads(data))
            return None
        except Exception as e:
            logger.warning(f"Error loading state for {conversation_id}: {e}")
            return None

    def save_state(self, conversation_id_or_state, state: ConversationState = None):
        """
        Save conversation state to Redis.

        State expires after 24 hours of inactivity.

        Args:
            conversation_id_or_state: Either a conversation_id string or a ConversationState
            state: Optional ConversationState if first arg is conversation_id
        """
        try:
            # Handle both calling patterns: save_state(state) and save_state(id, state)
            if isinstance(conversation_id_or_state, ConversationState):
                actual_state = conversation_id_or_state
            elif state is not None:
                actual_state = state
            else:
                raise ValueError("Must provide a ConversationState")

            actual_state.updated_at = datetime.utcnow().isoformat()
            self.redis.setex(
                self._key(actual_state.conversation_id),
                REDIS_STATE_TTL,
                json.dumps(actual_state.to_dict())
            )
        except Exception as e:
            conv_id = conversation_id_or_state if isinstance(conversation_id_or_state, str) else getattr(conversation_id_or_state, 'conversation_id', 'unknown')
            logger.error(f"Error saving state for {conv_id}: {e}")

    def get_or_create_state(self, conversation_id: str) -> ConversationState:
        """
        Get existing state or create new one.

        Always returns a valid ConversationState.
        """
        state = self.get_state(conversation_id)
        if not state:
            state = ConversationState(conversation_id=conversation_id)
            self.save_state(state)
        return state

    def delete_state(self, conversation_id: str):
        """Delete conversation state."""
        try:
            self.redis.delete(self._key(conversation_id))
        except Exception as e:
            logger.warning(f"Error deleting state for {conversation_id}: {e}")

    def clear_state(self, conversation_id: str):
        """Alias for delete_state for semantic clarity."""
        self.delete_state(conversation_id)

    def update_state_from_response(self, conversation_id: str,
                                    query: str,
                                    tools_used: List[str],
                                    session_device_id: int = None,
                                    speaker_id: int = None,
                                    artifacts: List[Dict] = None):
        """
        Update state after processing a query.

        Args:
            conversation_id: The conversation ID
            query: The user's query
            tools_used: List of tools that were used
            session_device_id: Optional session to focus on
            speaker_id: Optional speaker to focus on
            artifacts: Optional list of artifacts to reference
        """
        state = self.get_or_create_state(conversation_id)

        # Update basic info
        state.update_from_turn(query, tools_used)

        # Update focus if provided
        if session_device_id:
            state.set_session_focus(session_device_id)
        if speaker_id:
            state.set_speaker_focus(speaker_id)

        # Add artifact references
        if artifacts:
            for artifact in artifacts:
                state.add_artifact_reference(
                    artifact_type=artifact.get('type'),
                    artifact_id=artifact.get('id'),
                    excerpt=artifact.get('excerpt')
                )

        self.save_state(state)
        return state

    def resolve_reference(self, conversation_id: str,
                          reference: str) -> Optional[Dict]:
        """
        Resolve a reference like "that session" or "the student".

        Uses conversation state to map references to concrete entities.

        Args:
            conversation_id: The conversation ID
            reference: The reference text to resolve

        Returns:
            Dict with resolved entity info or None
        """
        state = self.get_state(conversation_id)
        if not state:
            return None

        reference_lower = reference.lower()

        # Multi-session references (for comparisons)
        multi_session_refs = ['those sessions', 'these sessions', 'those four',
                              'those three', 'those two', 'all of them',
                              'both sessions', 'both of them', 'all four',
                              'all three', 'the sessions']
        if any(ref in reference_lower for ref in multi_session_refs):
            if state.compared_sessions:
                return {
                    "type": "sessions",
                    "session_device_ids": state.compared_sessions
                }

        # Ordinal session references
        ordinal_first = ['first session', 'the first one', 'first one i mentioned',
                         'first session i asked', 'first session i mentioned']
        if any(ref in reference_lower for ref in ordinal_first):
            if state.session_history:
                return {
                    "type": "session",
                    "session_device_id": state.session_history[0]
                }

        ordinal_second = ['second session', 'the second one', 'second one i mentioned']
        if any(ref in reference_lower for ref in ordinal_second):
            if len(state.session_history) >= 2:
                return {
                    "type": "session",
                    "session_device_id": state.session_history[1]
                }

        ordinal_prev = ['previous session', 'go back', 'the other session',
                        'the earlier session', 'back to the first']
        if any(ref in reference_lower for ref in ordinal_prev):
            if state.previous_session_focus:
                return {
                    "type": "session",
                    "session_device_id": state.previous_session_focus
                }

        # Session references
        session_refs = ['that session', 'this session', 'the session',
                       'that discussion', 'this discussion', 'the discussion',
                       'it', 'that']
        if any(ref in reference_lower for ref in session_refs):
            if state.current_session_focus:
                return {
                    "type": "session",
                    "session_device_id": state.current_session_focus
                }

        # Speaker references
        speaker_refs = ['that student', 'the student', 'they', 'the speaker',
                       'that speaker', 'he', 'she', 'the participant']
        if any(ref in reference_lower for ref in speaker_refs):
            if state.current_speaker_focus:
                return {
                    "type": "speaker",
                    "speaker_id": state.current_speaker_focus
                }

        # Artifact references
        artifact_refs = ['that concept', 'the concept', 'that idea', 'the idea',
                        'that question', 'the question', 'that cluster',
                        'the cluster', 'that theme', 'the theme']
        if any(ref in reference_lower for ref in artifact_refs):
            if state.referenced_artifacts:
                # Return most recent matching artifact
                recent = state.referenced_artifacts[-1]
                return {
                    "type": "artifact",
                    "artifact_type": recent.get('artifact_type'),
                    "artifact_id": recent.get('artifact_id')
                }

        return None

    def set_pending_clarification(
        self,
        conversation_id: str,
        clarification_data: Dict
    ) -> None:
        """
        Set a pending clarification for a conversation.

        Args:
            conversation_id: The conversation ID
            clarification_data: Clarification data to store
        """
        state = self.get_or_create_state(conversation_id)
        state.set_pending_clarification(clarification_data)
        self.save_state(state)

    def get_pending_clarification(
        self,
        conversation_id: str
    ) -> Optional[Dict]:
        """
        Get pending clarification for a conversation.

        Args:
            conversation_id: The conversation ID

        Returns:
            Pending clarification data or None
        """
        state = self.get_state(conversation_id)
        if state and state.has_pending_clarification():
            return state.pending_clarification
        return None

    def clear_pending_clarification(self, conversation_id: str) -> None:
        """
        Clear pending clarification for a conversation.

        Args:
            conversation_id: The conversation ID
        """
        state = self.get_state(conversation_id)
        if state:
            state.clear_pending_clarification()
            self.save_state(state)

    def increment_failure(self, conversation_id: str) -> int:
        """
        Increment failure count for a conversation.

        Args:
            conversation_id: The conversation ID

        Returns:
            New failure count
        """
        state = self.get_or_create_state(conversation_id)
        count = state.increment_failure()
        self.save_state(state)
        return count

    def reset_failures(self, conversation_id: str) -> None:
        """
        Reset failure count for a conversation.

        Args:
            conversation_id: The conversation ID
        """
        state = self.get_state(conversation_id)
        if state:
            state.reset_failures()
            self.save_state(state)

    def get_state_as_dict(self, conversation_id: str) -> Optional[Dict]:
        """
        Get conversation state as a dictionary.

        Useful for passing to meta-intent classifier.

        Args:
            conversation_id: The conversation ID

        Returns:
            State dictionary or None
        """
        state = self.get_state(conversation_id)
        if state:
            return state.to_dict()
        return None


# Global state manager instance
_state_manager = None


def get_state_manager() -> ConversationStateManager:
    """Get the global state manager instance."""
    global _state_manager
    if _state_manager is None:
        _state_manager = ConversationStateManager()
    return _state_manager
