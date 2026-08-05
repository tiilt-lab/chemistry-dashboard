"""
Conversation Memory for BLINC Agent V7

Manages persistent state across conversation turns, including:
- Session and speaker focus
- Artifacts retrieved and shown to user
- Claims made (for consistency)
- User steering preferences
- Full message history
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set
from datetime import datetime

logger = logging.getLogger(__name__)


# =============================================================================
# Dynamic Data Loading (from database with caching)
# =============================================================================

# Cache TTL for all dynamic data
CACHE_TTL_SECONDS = 300  # 5 minutes

# Speaker cache — keyed by db_name to isolate study participants
_speakers_cache: Dict[str, Set[str]] = {}
_speakers_cache_time: Dict[str, datetime] = {}

# Session name cache — keyed by db_name to isolate study participants
_session_names_cache: Dict[str, List[tuple]] = {}
_session_names_cache_time: Dict[str, datetime] = {}


def _get_db_connection():
    """Get a database connection (study-aware via study_context)."""
    from study_context import get_db_connection
    return get_db_connection()


def _load_speakers_from_db() -> Set[str]:
    """
    Load all speaker names from the database.

    Caches results for 5 minutes per database context to isolate study participants.
    """
    from study_context import get_db_name
    db_key = get_db_name()

    # Check cache for this DB context
    if db_key in _speakers_cache and db_key in _speakers_cache_time:
        age = (datetime.now() - _speakers_cache_time[db_key]).total_seconds()
        if age < CACHE_TTL_SECONDS:
            return _speakers_cache[db_key]

    # Load from database
    try:
        connection = _get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT DISTINCT alias FROM speaker WHERE alias IS NOT NULL")
        speakers = {row[0] for row in cursor.fetchall() if row[0]}
        cursor.close()
        connection.close()

        _speakers_cache[db_key] = speakers
        _speakers_cache_time[db_key] = datetime.now()
        logger.info(f"[Memory] Loaded {len(speakers)} speakers from database ({db_key})")
        return speakers

    except Exception as e:
        logger.warning(f"[Memory] Failed to load speakers from DB: {e}")
        return set()


def get_known_speakers() -> Set[str]:
    """Get set of known speaker names (from database with caching)."""
    return _load_speakers_from_db()


def _load_session_names_from_db() -> List[tuple]:
    """
    Load session name → ID mappings from database.

    Returns a list of (name_pattern, session_id) tuples, ordered by specificity:
    - Full session names first (most specific)
    - Individual words from names second (for fuzzy matching)
    - Longer patterns before shorter ones

    Caches results for 5 minutes.
    """
    from study_context import get_db_name
    db_key = get_db_name()

    # Check cache for this DB context
    if db_key in _session_names_cache and db_key in _session_names_cache_time:
        age = (datetime.now() - _session_names_cache_time[db_key]).total_seconds()
        if age < CACHE_TTL_SECONDS:
            return _session_names_cache[db_key]

    # Load from database
    try:
        connection = _get_db_connection()
        cursor = connection.cursor()

        # Get session_device.id, session.name, and device name for all sessions
        cursor.execute("""
            SELECT sd.id as session_id, s.name as session_name, sd.name as device_name
            FROM session_device sd
            JOIN session s ON sd.session_id = s.id
            WHERE s.name IS NOT NULL AND s.name != ''
        """)

        rows = cursor.fetchall()
        cursor.close()
        connection.close()

        # Build mapping with full names, device names, and individual words
        name_to_id: Dict[str, int] = {}
        word_to_id: Dict[str, int] = {}

        for session_id, session_name, device_name in rows:
            if not session_name:
                continue

            name_lower = session_name.lower().strip()

            # Full name (highest priority) — for multi-device sessions, first wins
            if name_lower not in name_to_id:
                name_to_id[name_lower] = session_id

            # Device name mapping (e.g., "midnight" -> 43, "dev30" -> 47)
            if device_name:
                device_lower = device_name.lower().strip()
                name_to_id[device_lower] = session_id

            # Also extract individual words for fuzzy matching
            # Skip very short words, common stop words, and words that are commonly
            # used in natural language to refer to sessions/discussions generically
            stop_words = {
                'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'or', 'is', 'are',
                'discussion', 'session', 'conversation', 'debate', 'group', 'interview',
                'workshop', 'activity', 'part', 'parts', 'round', 'roundtable',
            }
            for word in name_lower.split():
                word = word.strip()
                if len(word) >= 2 and word not in stop_words:
                    if word not in word_to_id:
                        word_to_id[word] = session_id

        # Build ordered list: full names first (sorted by length desc), then words (sorted by length desc)
        # This ensures longer/more specific patterns are checked first
        result = []

        # Full names, longest first
        for name in sorted(name_to_id.keys(), key=len, reverse=True):
            result.append((name, name_to_id[name]))

        # Individual words, longest first
        for word in sorted(word_to_id.keys(), key=len, reverse=True):
            # Skip if this word is already in as a full name
            if word not in name_to_id:
                result.append((word, word_to_id[word]))

        _session_names_cache[db_key] = result
        _session_names_cache_time[db_key] = datetime.now()
        logger.info(f"[Memory] Loaded {len(result)} session name patterns from database ({len(name_to_id)} full names, {len(word_to_id)} words) [{db_key}]")
        return result

    except Exception as e:
        logger.warning(f"[Memory] Failed to load session names from DB: {e}")
        return []


def get_session_name_mapping() -> List[tuple]:
    """
    Get session name → ID mapping (from database with caching).

    Returns list of (pattern, session_id) tuples ordered by specificity.
    """
    return _load_session_names_from_db()


def get_session_name_by_id(session_id: int) -> Optional[str]:
    """
    Get the session name for a given session ID.

    Returns the full session name or None if not found.
    """
    mapping = get_session_name_mapping()

    # Find the first (longest) name that maps to this session_id
    for name, sid in mapping:
        if sid == session_id and ' ' in name:  # Prefer multi-word names
            return name.title()

    # Fallback to any name
    for name, sid in mapping:
        if sid == session_id:
            return name.title()

    return None


def clear_caches():
    """Clear all cached data (useful for testing or after data changes)."""
    _speakers_cache.clear()
    _speakers_cache_time.clear()
    _session_names_cache.clear()
    _session_names_cache_time.clear()
    logger.info("[Memory] Cleared all caches")


@dataclass
class ArtifactReference:
    """Reference to an artifact shown to user."""
    artifact_type: str  # 'transcript', 'concept_map', '7c', 'overview'
    session_id: int
    turn_number: int
    key_content: str = ""  # Brief summary of what was shown


@dataclass
class ClaimMade:
    """A claim made by the agent, with evidence reference."""
    claim: str
    evidence_type: str
    evidence_ref: str  # e.g., "7c:24:communication" or "transcript:24:42"
    turn_number: int


@dataclass
class ConversationMemory:
    """
    Persistent memory for a conversation.

    Tracks context across turns to enable:
    - Follow-up questions about artifacts
    - Consistent session/speaker focus
    - Avoiding redundant artifact retrieval
    - Maintaining claim consistency
    """
    conversation_id: str

    # Current focus (persists across turns)
    session_focus: Optional[int] = None
    session_focus_from_query: bool = False  # True if user explicitly named a session
    session_name: Optional[str] = None
    speaker_focus: Optional[str] = None

    # Artifacts and claims (accumulate across turns)
    artifacts_retrieved: List[ArtifactReference] = field(default_factory=list)
    claims_made: List[ClaimMade] = field(default_factory=list)

    # Message history
    messages: List[Dict[str, Any]] = field(default_factory=list)

    # User steering preferences (can persist or be per-turn)
    user_steering: Dict[str, Any] = field(default_factory=dict)

    # Turn counter
    turn_count: int = 0

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)

    def get_context_for_llm(self) -> str:
        """
        Format memory as context string for LLM.

        Returns a concise summary of:
        - Current session/speaker focus
        - Recent artifacts discussed
        - Key claims established
        - User preferences
        """
        parts = []

        # Session focus
        if self.session_focus:
            session_desc = f"Session {self.session_focus}"
            if self.session_name:
                session_desc += f" ({self.session_name})"
            parts.append(f"Current session focus: {session_desc}")

        # Speaker focus
        if self.speaker_focus:
            parts.append(f"Current speaker focus: {self.speaker_focus}")

        # Recent artifacts (last 5)
        if self.artifacts_retrieved:
            recent = self.artifacts_retrieved[-5:]
            artifact_strs = []
            for art in recent:
                desc = f"{art.artifact_type} for session {art.session_id}"
                if art.key_content:
                    desc += f" ({art.key_content[:50]}...)"
                artifact_strs.append(desc)
            parts.append("Artifacts already discussed:\n  - " + "\n  - ".join(artifact_strs))

        # Recent claims (last 3)
        if self.claims_made:
            recent_claims = self.claims_made[-3:]
            claim_strs = [f"\"{c.claim}\" (from {c.evidence_type})" for c in recent_claims]
            parts.append("Key points established:\n  - " + "\n  - ".join(claim_strs))

        # User preferences
        if self.user_steering:
            pref_parts = []
            if self.user_steering.get('preferred_artifacts'):
                pref_parts.append(f"Prefer: {', '.join(self.user_steering['preferred_artifacts'])}")
            if self.user_steering.get('excluded_artifacts'):
                pref_parts.append(f"Exclude: {', '.join(self.user_steering['excluded_artifacts'])}")
            if pref_parts:
                parts.append("User preferences: " + "; ".join(pref_parts))

        if not parts:
            return "No prior context (new conversation)"

        return "\n".join(parts)

    def get_message_history_for_llm(self, max_messages: int = 10) -> List[Dict[str, str]]:
        """
        Get recent message history formatted for LLM.

        Args:
            max_messages: Maximum number of messages to include

        Returns:
            List of message dicts with 'role' and 'content'
        """
        recent = self.messages[-max_messages:] if len(self.messages) > max_messages else self.messages
        return [{"role": m["role"], "content": m["content"]} for m in recent]

    def add_user_message(self, content: str):
        """Add a user message to history."""
        self.messages.append({
            "role": "user",
            "content": content,
            "turn": self.turn_count,
            "timestamp": datetime.now().isoformat()
        })

    def add_assistant_message(self, content: str):
        """Add an assistant message to history."""
        self.messages.append({
            "role": "assistant",
            "content": content,
            "turn": self.turn_count,
            "timestamp": datetime.now().isoformat()
        })

    def record_artifact(self, artifact_type: str, session_id: int, key_content: str = ""):
        """Record that an artifact was retrieved and shown."""
        self.artifacts_retrieved.append(ArtifactReference(
            artifact_type=artifact_type,
            session_id=session_id,
            turn_number=self.turn_count,
            key_content=key_content
        ))
        logger.debug(f"[Memory] Recorded artifact: {artifact_type} for session {session_id}")

    def record_claim(self, claim: str, evidence_type: str, evidence_ref: str):
        """Record a claim made by the agent."""
        self.claims_made.append(ClaimMade(
            claim=claim,
            evidence_type=evidence_type,
            evidence_ref=evidence_ref,
            turn_number=self.turn_count
        ))
        logger.debug(f"[Memory] Recorded claim: {claim[:50]}...")

    def has_artifact(self, artifact_type: str, session_id: int) -> bool:
        """Check if an artifact has already been retrieved."""
        return any(
            a.artifact_type == artifact_type and a.session_id == session_id
            for a in self.artifacts_retrieved
        )

    def update_session_focus(self, session_id: int, session_name: str = None):
        """Update the current session focus."""
        if self.session_focus != session_id:
            logger.info(f"[Memory] Session focus changed: {self.session_focus} -> {session_id}")
            self.session_focus = session_id
            if session_name:
                self.session_name = session_name
            else:
                # Try to find name from dynamic mapping
                self.session_name = get_session_name_by_id(session_id)

    def update_speaker_focus(self, speaker: str):
        """Update the current speaker focus."""
        if self.speaker_focus != speaker:
            logger.info(f"[Memory] Speaker focus changed: {self.speaker_focus} -> {speaker}")
            self.speaker_focus = speaker

    def update_steering(self, preferred: List[str] = None, excluded: List[str] = None):
        """Update user steering preferences."""
        if preferred:
            self.user_steering['preferred_artifacts'] = preferred
        if excluded:
            self.user_steering['excluded_artifacts'] = excluded
        logger.debug(f"[Memory] Updated steering: {self.user_steering}")

    def start_new_turn(self):
        """Increment turn counter and update timestamp."""
        self.turn_count += 1
        self.last_active = datetime.now()
        logger.debug(f"[Memory] Starting turn {self.turn_count}")

    def extract_session_from_text(self, text: str) -> Optional[int]:
        """
        Extract session reference from text (query or response).

        Handles:
        - Explicit: "session 24", "Session 19"
        - Named: "the Country Music session", "Nuclear Fusion discussion"
        - Pronouns: "it", "this session", "that discussion"

        Dynamically loads session names from database.

        Returns session ID or None
        """
        text_lower = text.lower()

        # Check for explicit session ID
        session_match = re.search(r'session\s*(\d+)', text_lower)
        if session_match:
            return int(session_match.group(1))

        # Check for session names using dynamic mapping from database
        # Mapping is ordered by specificity (longer/multi-word patterns first)
        session_mapping = get_session_name_mapping()
        for name, sid in session_mapping:
            if ' ' in name:
                # Multi-word phrases: exact substring match is fine
                # e.g., "nuclear fusion" clearly refers to that session
                if name in text_lower:
                    return sid
            else:
                # Single words: ONLY match when in session-referencing context
                # e.g., "the AI session", "AI discussion", "about the dinosaurs session"
                # NOT: "about AI" or "hypotheses about AI" (too ambiguous - could be topic)
                #
                # This prevents auto-focusing on sessions from mere topic mentions.
                # "What hypotheses were raised about AI?" should search, not auto-target session 19.
                session_context_pattern = (
                    r'\b' + re.escape(name) + r'\b\s*'
                    r'(?:session|discussion|conversation|debate)'  # word followed by session indicator
                    r'|'
                    r'(?:the|this|that)\s+' + re.escape(name) + r'\b'  # "the AI", "this AI"
                    r'|'
                    r'(?:in|from|about)\s+(?:the\s+)?' + re.escape(name) +
                    r'\s+(?:session|discussion)'  # "in the AI session", "about the fusion discussion"
                )
                if re.search(session_context_pattern, text_lower):
                    return sid

        # Pronouns refer to current focus
        pronoun_patterns = [
            r'\b(it|this|that)\b.*\b(session|discussion)\b',
            r'\bthe\s+(session|discussion)\b',
            r'\bthis\s+one\b',
        ]
        for pattern in pronoun_patterns:
            if re.search(pattern, text_lower):
                return self.session_focus

        return None

    def extract_speaker_from_text(self, text: str) -> Optional[str]:
        """
        Extract speaker reference from text.

        Dynamically loads speaker names from database instead of hardcoded list.
        Uses word boundary matching to avoid false positives.

        Returns speaker name or None
        """
        # Get known speakers from database (cached)
        known_speakers = get_known_speakers()

        if not known_speakers:
            return None

        text_lower = text.lower()

        # Check each known speaker with word boundary matching
        for speaker in known_speakers:
            speaker_lower = speaker.lower()
            # Use word boundary to avoid false matches (e.g., "said" matching "ai")
            pattern = r'\b' + re.escape(speaker_lower) + r'\b'
            if re.search(pattern, text_lower):
                return speaker

        return None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize memory to dict for storage."""
        return {
            "conversation_id": self.conversation_id,
            "session_focus": self.session_focus,
            "session_name": self.session_name,
            "speaker_focus": self.speaker_focus,
            "artifacts_retrieved": [
                {
                    "artifact_type": a.artifact_type,
                    "session_id": a.session_id,
                    "turn_number": a.turn_number,
                    "key_content": a.key_content
                }
                for a in self.artifacts_retrieved
            ],
            "claims_made": [
                {
                    "claim": c.claim,
                    "evidence_type": c.evidence_type,
                    "evidence_ref": c.evidence_ref,
                    "turn_number": c.turn_number
                }
                for c in self.claims_made
            ],
            "messages": self.messages,
            "user_steering": self.user_steering,
            "turn_count": self.turn_count,
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationMemory":
        """Deserialize memory from dict."""
        memory = cls(conversation_id=data["conversation_id"])
        memory.session_focus = data.get("session_focus")
        memory.session_name = data.get("session_name")
        memory.speaker_focus = data.get("speaker_focus")
        memory.artifacts_retrieved = [
            ArtifactReference(**a) for a in data.get("artifacts_retrieved", [])
        ]
        memory.claims_made = [
            ClaimMade(**c) for c in data.get("claims_made", [])
        ]
        memory.messages = data.get("messages", [])
        memory.user_steering = data.get("user_steering", {})
        memory.turn_count = data.get("turn_count", 0)
        if data.get("created_at"):
            memory.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("last_active"):
            memory.last_active = datetime.fromisoformat(data["last_active"])
        return memory


# =============================================================================
# Edit Log Context (for agent awareness of user edits)
# =============================================================================

def get_edit_log_context() -> Optional[str]:
    """
    Build context string about user edits to collaboration assessments
    and the dimension pool, for injection into agent context.

    Computes score diffs by comparing analysis_summary vs ai_baseline
    for each session's analysis. No dependency on dimension_score_edit table.
    """
    try:
        import json as _json
        connection = _get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Get dimension pool info (default schema)
        cursor.execute("""
            SELECT schema_name, dimensions
            FROM dimension_schema
            WHERE is_default = TRUE
            LIMIT 1
        """)
        schema_row = cursor.fetchone()

        # Get all analyses with their session names, comparing summary vs baseline
        cursor.execute("""
            SELECT
                sca.analysis_summary,
                sca.ai_baseline,
                s.name as session_name,
                sd.name as device_name
            FROM seven_cs_analysis sca
            JOIN session_device sd ON sca.session_device_id = sd.id
            JOIN session s ON sd.session_id = s.id
            WHERE sca.analysis_status = 'completed'
              AND sca.analysis_summary IS NOT NULL
              AND sca.ai_baseline IS NOT NULL
        """)
        analyses = cursor.fetchall()

        cursor.close()
        connection.close()

        parts = []

        # Pool info
        if schema_row:
            dims = schema_row['dimensions']
            if isinstance(dims, str):
                dims = _json.loads(dims)
            dim_names = [d.get('name', d.get('key', '')) for d in dims]
            parts.append(f"[Dimension Pool: \"{schema_row['schema_name']}\" — {', '.join(dim_names)}]")

        # Compute edit diffs across all sessions
        edit_lines = []
        for row in analyses:
            summary = row['analysis_summary']
            baseline = row['ai_baseline']
            if isinstance(summary, str):
                summary = _json.loads(summary)
            if isinstance(baseline, str):
                baseline = _json.loads(baseline)
            if not summary or not baseline:
                continue

            session_label = row['session_name'] or row['device_name'] or 'Unknown'

            for dim_key, current_data in summary.items():
                if not current_data or not isinstance(current_data, dict):
                    continue
                baseline_data = baseline.get(dim_key)
                if not baseline_data or not isinstance(baseline_data, dict):
                    continue

                current_score = current_data.get('score')
                baseline_score = baseline_data.get('score')
                if current_score is not None and baseline_score is not None and current_score != baseline_score:
                    edit_lines.append(f"{session_label}: {dim_key.title()} score {baseline_score} -> {current_score}")

        if edit_lines:
            parts.append("[User Edits]\n" + "\n".join(edit_lines))

        if not parts:
            return None

        return "\n\n".join(parts)

    except Exception as e:
        logger.warning(f"[Memory] Failed to get edit log context: {e}")
        return None


# In-memory storage for conversation memories (use Redis in production)
# Keyed by "{db_name}:{conversation_id}" to isolate study participants
_memory_store: Dict[str, ConversationMemory] = {}


def _memory_key(conversation_id: str) -> str:
    """Build a memory store key scoped by the current database context."""
    from study_context import get_db_name
    return f"{get_db_name()}:{conversation_id}"


def get_memory(conversation_id: str) -> ConversationMemory:
    """Get or create memory for a conversation (scoped by study user)."""
    key = _memory_key(conversation_id)
    if key not in _memory_store:
        _memory_store[key] = ConversationMemory(conversation_id)
        logger.info(f"[Memory] Created new memory for conversation {conversation_id} (key={key})")
    return _memory_store[key]


def clear_memory(conversation_id: str):
    """Clear memory for a conversation (scoped by study user)."""
    key = _memory_key(conversation_id)
    if key in _memory_store:
        del _memory_store[key]
        logger.info(f"[Memory] Cleared memory for conversation {conversation_id} (key={key})")


def clear_all_memories():
    """Clear all conversation memories."""
    global _memory_store
    count = len(_memory_store)
    _memory_store = {}
    logger.info(f"[Memory] Cleared all {count} conversation memories")
