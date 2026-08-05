"""
ReAct Agent for BLINC Agent V7 (Pure ReAct Architecture)

A simple, flexible agent that:
1. Uses LLM to decide what tools to call (not hardcoded patterns)
2. Maintains conversation memory across turns
3. Produces scaffolded responses with specific evidence
4. Respects user steering preferences
5. Supports artifact steering (user controls which tools to use)

V7.2: Pure ReAct - All queries go through the ReAct loop.
The LLM decides what tools to call based on:
- Query understanding
- Tool guidance in system prompt
- User steering constraints
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple, Callable, Set

from .llm import get_reasoning_client, LLMResponse
from .memory import ConversationMemory, get_memory
from .steering import extract_steering, validate_tool_call, SteeringDirectives
from .tools_v2 import CORE_TOOLS, TOOL_SCHEMAS, execute_tool, get_tool_names
from .prompts_v2 import format_system_prompt
# Note: classifier.py and exploratory.py are deprecated in V7.2
# All queries now go through pure ReAct loop

logger = logging.getLogger(__name__)

# Maximum iterations to prevent infinite loops
MAX_ITERATIONS = 8

# Maximum evidence items to include in context
MAX_EVIDENCE_ITEMS = 20

# Dynamic session name to ID mapping (loaded from DB)
# Keyed by db_name to isolate study participants
_session_name_cache: dict = {}
_session_name_cache_time: dict = {}
SESSION_NAME_CACHE_TTL = 300  # 5 minutes

def get_session_name_mapping() -> dict:
    """Load session name → ID mapping dynamically from the database (study-aware)."""
    import time
    from study_context import get_db_name, get_db_connection

    db_key = get_db_name()

    if db_key in _session_name_cache and (time.time() - _session_name_cache_time.get(db_key, 0)) < SESSION_NAME_CACHE_TTL:
        return _session_name_cache[db_key]

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT sd.id, s.name, sd.name as device_name
            FROM session_device sd
            JOIN session s ON sd.session_id = s.id
            WHERE s.name IS NOT NULL
        """)
        mapping = {}
        for sd_id, session_name, device_name in cursor.fetchall():
            # Map session name to session_device id
            name_lower = session_name.lower()
            # For multi-device sessions, each device gets its own entry
            # Later matches overwrite earlier ones, but device_name is more specific
            if name_lower not in mapping:
                mapping[name_lower] = sd_id
            # Map device name (e.g., "midnight", "kha4", "dev30")
            if device_name:
                mapping[device_name.lower()] = sd_id
            # Add abbreviated session name forms
            words = name_lower.split()
            if len(words) > 1:
                if len(words[0]) >= 4 and words[0] not in mapping:
                    mapping[words[0]] = sd_id
        cursor.close()
        conn.close()

        _session_name_cache[db_key] = mapping
        _session_name_cache_time[db_key] = time.time()
        logger.debug(f"[Sessions] Loaded {len(mapping)} session name mappings from database [{db_key}]")
        return mapping

    except Exception as e:
        logger.warning(f"[Sessions] Failed to load from database: {e}")
        return _session_name_cache.get(db_key, {})

# =============================================================================
# Query Classification Patterns
# =============================================================================

# Patterns that indicate comparison/multi-session queries
COMPARISON_PATTERNS = [
    r'compare\s+(.+?)\s+(?:and|vs\.?|versus|with|to)\s+(.+)',
    r'(.+?)\s+vs\.?\s+(.+)',
    r'difference(?:s)?\s+between\s+(.+?)\s+and\s+(.+)',
    r'how\s+(?:does|do|did)\s+(.+?)\s+(?:differ|compare)\s+(?:from|to|with)\s+(.+)',
]

# Patterns that indicate superlative/ranking queries needing multiple sessions
SUPERLATIVE_PATTERNS = [
    r'which\s+sessions?\s+(?:had|has|was|is|showed|demonstrated)\s+(?:the\s+)?(?:most|best|highest|greatest|lowest|worst|least)',
    r'(?:best|worst|highest|lowest|most|least)\s+(?:collaboration|engagement|participation|communication|constructive|conflict)',
    r'rank\s+(?:the\s+)?sessions',
    r'(?:more|most)\s+(?:constructive|balanced|engaging)',
    r'which\s+(?:session|discussion)\s+had\s+more',  # "Which session had more X" - comparative
    r'which\s+(?:session|discussion)\s+had\s+(?:better|worse)',  # "Which session had better/worse X"
    r'across\s+(?:all\s+)?sessions',  # "7C scores across sessions" - needs multiple sessions
]

# Patterns that indicate hypothesis testing queries
HYPOTHESIS_PATTERNS = [
    r'test\s+(?:whether|if|that)',
    r'verify\s+(?:whether|if|that)',
    r'is\s+it\s+true\s+that',
    r'(?:does|do|did)\s+.+\s+(?:have|show|demonstrate)\s+(?:more|less|better|worse|higher|lower)',
    r'(?:hypothesis|claim|theory|proposition)[\s:]+',
    r'evidence\s+(?:for|against|that)',
    # "X more/less than Y" patterns
    r'(.+?)\s+(?:more|less|higher|lower|better|worse)\s+(?:\w+\s+)?than\s+(.+)',
]

# Patterns that indicate thematic/topic-based queries (should use search_sessions)
THEMATIC_PATTERNS = [
    r'(?:what\s+was\s+)?(?:said|discussed|mentioned|talked)\s+about\s+(.+?)(?:\?|$|across|in\s+the)',
    r'(?:sessions?|discussions?)\s+(?:about|on|regarding|involving|related\s+to)\s+(.+?)(?:\?|$)',
    r'(?:find|search|look\s+for)\s+(?:sessions?|discussions?)\s+(?:about|on|regarding)\s+(.+?)(?:\?|$)',
    r'(?:where|when)\s+(?:was|were|did)\s+(.+?)\s+(?:discussed|mentioned|brought\s+up)',
    r'(?:any\s+)?(?:sessions?|discussions?)\s+(?:that\s+)?(?:mention|discuss|cover|address)\s+(.+?)(?:\?|$)',
    # Note: "across sessions" moved to SUPERLATIVE_PATTERNS - it indicates need for multi-session data
    r'(?:all|every|each)\s+session.*(?:about|discuss|mention)',
]

# Patterns that indicate structural queries (metadata only, use list_sessions)
STRUCTURAL_PATTERNS = [
    r'how\s+many\s+sessions',
    r'(?:list|show|display)\s+(?:all\s+)?sessions',
    r'sessions?\s+with\s+\d+\s+(?:speakers?|participants?)',
    r'what\s+sessions\s+(?:are\s+)?(?:available|exist)',
    r'(?:all|available)\s+sessions',
    r'session\s+(?:names?|ids?|list)',
]

# Patterns for speaker-focused queries
SPEAKER_PATTERNS = [
    r'how\s+(?:did|does)\s+(\w+)\s+(?:engage|participate|contribute)',
    r'(\w+)(?:\'s|s)\s+(?:style|pattern|behavior|contribution)',
    r'(?:most|least)\s+active\s+speaker',
    r'speaker\s+(?:comparison|analysis|profile)',
    r'who\s+(?:spoke|talked|contributed)\s+(?:the\s+)?(?:most|least)',
]

# Patterns for speaker comparison queries (need profiles for BOTH speakers)
SPEAKER_COMPARISON_PATTERNS = [
    r'compare\s+(\w+)\s+(?:and|vs\.?|versus|with|to)\s+(\w+)',
    r'(\w+)\s+(?:and|vs\.?)\s+(\w+)(?:\'s)?\s+(?:participation|contribution|style|pattern|engagement)',
    r'difference(?:s)?\s+between\s+(\w+)\s+and\s+(\w+)',
    r'how\s+(?:do|did)\s+(\w+)\s+and\s+(\w+)\s+(?:differ|compare)',
]

# Cache for dynamically loaded speaker names
# Keyed by db_name to isolate study participants
_speaker_cache: dict = {}
_speaker_cache_time: dict = {}
SPEAKER_CACHE_TTL = 300  # 5 minutes

def get_known_speakers() -> Set[str]:
    """
    Get known speaker names from database (cached, study-aware).

    This allows the agent to recognize speaker names in queries
    even for new sessions added after deployment.
    """
    import time
    from study_context import get_db_name, get_db_connection

    db_key = get_db_name()

    # Return cached result if still valid for this DB context
    if db_key in _speaker_cache and (time.time() - _speaker_cache_time.get(db_key, 0)) < SPEAKER_CACHE_TTL:
        return _speaker_cache[db_key]

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT LOWER(alias) FROM speaker WHERE alias IS NOT NULL AND alias != ''")
        speakers = {row[0] for row in cursor.fetchall()}
        cursor.close()
        conn.close()

        # Add common patterns that might not be in DB
        speakers.update({'speaker_00', 'speaker_01', 'speaker_02', 'speaker_03', 'speaker_04'})

        _speaker_cache[db_key] = speakers
        _speaker_cache_time[db_key] = time.time()
        logger.debug(f"[Speakers] Loaded {len(speakers)} speaker names from database [{db_key}]")
        return speakers

    except Exception as e:
        logger.warning(f"[Speakers] Failed to load from database: {e}, using fallback")
        # Fallback to hardcoded list if DB fails
        return {
            'tucker', 'sam', 'david', 'lex', 'noah', 'john', 'jane',
            'alice', 'bob', 'vanessa', 'julia', 'oliver', 'ezra', 'derek', 'dave',
            'speaker_00', 'speaker_01', 'speaker_02', 'speaker_03'
        }

# Patterns for correlation hypotheses (need data from multiple sessions)
CORRELATION_PATTERNS = [
    r'sessions?\s+with\s+(?:more|fewer|less|higher|lower)\s+\w+\s+have\s+(?:higher|lower|better|worse)',
    r'(?:more|fewer|less)\s+\w+\s+(?:correlate|lead|result)s?\s+(?:with|in)\s+(?:higher|lower)',
    r'(?:do|does|is|are)\s+\w+\s+(?:correlate|related)\s+(?:with|to)',
    r'test\s+whether\s+sessions?\s+with',
    r'(?:longer|shorter)\s+sessions?\s+have\s+(?:more|fewer|less|higher|lower)',
]


@dataclass
class QueryClassification:
    """Classification of query with data requirements."""
    query_type: str  # single_session, comparison, thematic, superlative, hypothesis, structural, speaker, speaker_comparison, correlation
    required_sessions: Set[int]  # Explicit sessions mentioned
    requires_search: bool  # Needs semantic search first
    requires_counter_evidence: bool  # For hypothesis testing
    topic: Optional[str]  # Extracted topic for thematic queries
    min_sessions_needed: int = 1  # Minimum sessions needed for complete answer
    required_speakers: Set[str] = field(default_factory=set)  # Speakers needed for comparison


@dataclass
class QueryConstraints:
    """
    Explicit tool constraints extracted from query.

    This is extracted BEFORE query classification to handle constraint queries
    like "only transcript", "not transcripts", "focus on concept map".
    """
    allowed_tools: Optional[Set[str]] = None  # "only X" -> ONLY these tools allowed
    blocked_tools: Set[str] = field(default_factory=set)  # "not X" -> these tools blocked
    focus_tools: Set[str] = field(default_factory=set)  # "focus on X" -> prioritize these
    mentioned_tools: Set[str] = field(default_factory=set)  # artifacts explicitly mentioned in query -> should be retrieved


# Tool name normalization for constraint extraction
TOOL_ALIASES = {
    'transcript': 'get_transcript',
    'transcripts': 'get_transcript',
    'concept map': 'get_concept_map',
    'concept_map': 'get_concept_map',
    'conceptmap': 'get_concept_map',
    'map': 'get_concept_map',
    '7c': 'get_collaboration_assessment',
    '7c scores': 'get_collaboration_assessment',
    '7c analysis': 'get_collaboration_assessment',
    'collaboration metrics': 'get_collaboration_assessment',
    'collab metrics': 'get_collaboration_assessment',
    'collaboration assessment': 'get_collaboration_assessment',
    'collab assessment': 'get_collaboration_assessment',
    'get_7c_analysis': 'get_collaboration_assessment',
    'speaker profile': 'get_speaker_profile',
    'speaker profiles': 'get_speaker_profile',
}


@dataclass
class ToolCall:
    """Represents a tool call decision."""
    name: str
    params: Dict[str, Any]
    reason: str = ""


@dataclass
class AgentAction:
    """Represents an action decision by the agent."""
    action_type: str  # "tool_call" or "respond"
    tool_call: Optional[ToolCall] = None
    response: Optional[str] = None


@dataclass
class AgentResponse:
    """Final response from the agent."""
    answer: str
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    tool_calls_made: List[ToolCall] = field(default_factory=list)
    session_focus: Optional[int] = None
    speaker_focus: Optional[str] = None
    suggested_explorations: List[str] = field(default_factory=list)


class ScaffoldingAgent:
    """
    Pure ReAct agent for scaffolded artifact exploration.

    Key features:
    - LLM decides what tools to call (no hardcoded routing)
    - Tool guidance in system prompt for different query types
    - Artifact steering support (user controls data sources)
    - Conversation memory for context persistence
    - Steering compliance with validation
    - Scaffolded response generation

    V7.2: Removed classifier and exploratory path. LLM reasoning replaces
    hardcoded query routing.
    """

    def __init__(self, conversation_id: str):
        """Initialize agent with conversation memory."""
        self.conversation_id = conversation_id
        self.memory = get_memory(conversation_id)
        self.llm = get_reasoning_client()
        self._tools_dict = self._create_tools_dict()

    def _create_tools_dict(self) -> Dict[str, Callable]:
        """
        Create a dictionary of callable tools for the exploratory retriever.

        This wraps execute_tool into individual callable functions.
        """
        def make_tool_fn(tool_name: str) -> Callable:
            def tool_fn(**kwargs):
                return execute_tool(tool_name, kwargs)
            return tool_fn

        return {
            'list_sessions': make_tool_fn('list_sessions'),
            'search_sessions': make_tool_fn('search_sessions'),
            'get_transcript': make_tool_fn('get_transcript'),
            'get_concept_map': make_tool_fn('get_concept_map'),
            'get_collaboration_assessment': make_tool_fn('get_collaboration_assessment'),
            'get_speaker_profile': make_tool_fn('get_speaker_profile'),
        }

    def _get_truncated_history(self, max_turns: int, max_words: int = 350) -> List[Dict[str, str]]:
        """
        Get truncated conversation history for LLM context.

        Returns prior exchanges with assistant messages truncated to max_words.
        Excludes the current turn's user message (already in the active prompt).

        Args:
            max_turns: Number of prior turns to include (each turn = user + assistant)
            max_words: Max words to keep per assistant message (first N words)

        Returns:
            List of {"role": ..., "content": ...} dicts in chronological order
        """
        # All messages except the current user message (added at top of respond())
        all_msgs = self.memory.messages[:-1] if self.memory.messages else []
        if not all_msgs:
            return []

        # Take last N turns (each turn = user + assistant = 2 messages)
        max_messages = max_turns * 2
        recent = all_msgs[-max_messages:]

        result = []
        for msg in recent:
            role = msg["role"]
            content = msg["content"]

            if role == "assistant":
                words = content.split()
                if len(words) > max_words:
                    content = " ".join(words[:max_words]) + " [...]"

            result.append({"role": role, "content": content})

        return result

    def respond(self, query: str) -> AgentResponse:
        """
        Process a user query and return a scaffolded response.

        This is the main entry point for the agent.

        V7.2 Flow (Pure ReAct):
        1. Extract context (session/speaker focus, steering)
        2. Run ReAct loop - LLM decides what tools to call
        3. Synthesize and return response

        The LLM uses tool guidance in system prompt to decide:
        - list_sessions for structural/superlative/hypothesis queries
        - search_sessions for topic-based discovery
        - Appropriate artifact tools based on query needs

        Args:
            query: User's query

        Returns:
            AgentResponse with answer, evidence, and suggestions
        """
        logger.info(f"[Agent] Processing query: {query[:100]}...")

        # Start new turn
        self.memory.start_new_turn()
        self.memory.add_user_message(query)

        # =========================================================
        # CONVERSATIONAL SHORT-CIRCUIT
        # Greetings, acknowledgments, and meta-questions don't need
        # any tool calls. Respond directly and return immediately.
        # =========================================================
        if self._is_conversational(query):
            logger.info("[Agent] Conversational query detected — short-circuit, no tools")
            answer = self._respond_conversationally(query)
            self.memory.add_assistant_message(answer)
            return AgentResponse(
                answer=answer,
                evidence=[],
                tool_calls_made=[],
                session_focus=self.memory.session_focus,
                speaker_focus=self.memory.speaker_focus,
                suggested_explorations=[]
            )

        # Get steering preferences
        steering = extract_steering(
            query,
            self.memory.messages,
            self.memory.user_steering
        )

        # Extract session/speaker focus from query
        session_id = self.memory.extract_session_from_text(query)
        if session_id and session_id != self.memory.session_focus:
            self.memory.update_session_focus(session_id)
            self.memory.session_focus_from_query = True

        speaker = self.memory.extract_speaker_from_text(query)
        if speaker and speaker != self.memory.speaker_focus:
            self.memory.update_speaker_focus(speaker)

        return self._run_react_loop(query, steering)

    # Patterns that mark a query as purely conversational (no data needed)
    _CONVERSATIONAL_RE = re.compile(
        r'^\s*('
        r'hi+|hello+|hey+|howdy|greetings|good\s+(morning|afternoon|evening|day)'
        r'|thanks?|thank\s+you|thx|ty|cheers'
        r'|ok(ay)?|got\s+it|i\s+see|understood|makes?\s+sense|that\'?s?\s+(clear|helpful|great|good|interesting|useful)'
        r'|sure|alright|sounds?\s+good|perfect|great|awesome|nice|cool'
        r'|bye|goodbye|see\s+ya?|cya|take\s+care'
        r'|yes|no|yep|nope|yeah|nah|correct|right|wrong|exactly'
        r'|who\s+are\s+you|what\s+(are|can)\s+you|what\s+do\s+you\s+do|how\s+(do\s+you\s+work|can\s+you\s+help)'
        r'|help\s*$|help\s+me\s*$'
        r')\s*[!?.,]*\s*$',
        re.IGNORECASE
    )

    def _is_conversational(self, query: str) -> bool:
        """Return True if the query is a greeting/ack/meta-question needing no tool calls."""
        return bool(self._CONVERSATIONAL_RE.match(query.strip()))

    def _respond_conversationally(self, query: str) -> str:
        """
        Respond to a conversational message without any tool calls.

        Uses a lightweight LLM call with conversation history for context,
        but no tool schemas — the model responds as a conversational partner.
        """
        history = self._get_truncated_history(max_turns=3, max_words=200)
        context_note = ""
        if self.memory.session_focus and self.memory.session_name:
            context_note = (
                f" You are currently helping the user explore the "
                f"'{self.memory.session_name}' discussion session."
            )
        system = (
            "You are an intelligent guide helping users explore collaborative learning "
            "discussions through transcripts, concept maps, and collaboration assessments."
            + context_note +
            " Respond warmly and concisely to the user's message."
        )
        try:
            response = self.llm.complete_with_tools(
                messages=[
                    {"role": "system", "content": system},
                    *history,
                    {"role": "user", "content": query},
                ],
                tools=[],
                temperature=0.5,
                max_tokens=200,
            )
            return (response.content or "").strip() or "Hello! How can I help you explore your discussion sessions?"
        except Exception as e:
            logger.warning(f"[Agent] Conversational response failed: {e}")
            return "Hello! How can I help you explore your discussion sessions?"

    def _run_react_loop(
        self,
        query: str,
        steering: SteeringDirectives
    ) -> AgentResponse:
        """
        Path A: Message-accumulating ReAct loop.

        Tool results are injected as native OpenAI role="tool" messages.
        The LLM's final text response IS the answer — no separate synthesis call.
        A completeness gate (MAX_GATE_REJECTIONS=2) ensures the agent retrieves
        enough evidence before committing to a response.
        """
        MAX_GATE_REJECTIONS = 2
        logger.info("[Agent] Running Path A ReAct loop")

        # Extract constraints BEFORE classification (handles "only X" / "not Y" queries)
        constraints = self._extract_constraints(query)

        # Build context
        memory_context = self.memory.get_context_for_llm()

        # Inject edit log context (user edits to assessments)
        from agent_v7.memory import get_edit_log_context
        edit_context = get_edit_log_context()
        if edit_context:
            memory_context += "\n\n" + edit_context

        # Inject session_device_id into initial user message if a session context is set
        # (either inferred from query text or explicitly passed by the frontend)
        session_hint = ""
        if self.memory.session_focus:
            session_hint = (
                f"\n\nNote: The user is currently viewing discussion_id={self.memory.session_focus}."
                " Focus your response on this session unless the query clearly asks for cross-session comparison."
                " Use this ID for tool calls."
            )
        initial_user_content = f"Query: {query}{session_hint}"

        # =========================================================
        # CROSS-SESSION GUARDRAIL
        # If no session focus after all resolution attempts, the query
        # doesn't name a specific session. Pre-fetch the session list
        # and inject it into the query context so the LLM has all
        # sessions available before choosing what to retrieve.
        # This prevents defaulting to a stale or arbitrary session
        # for cross-session, hypothesis, or pattern queries.
        #
        # False positives (e.g. topic searches) are harmless —
        # the extra context doesn't mislead, just adds overhead.
        #
        # Fires are logged with [GUARDRAIL-FIRED] for post-study
        # intent classification analysis.
        # =========================================================
        if not self.memory.session_focus:
            logger.info(
                f"[GUARDRAIL-FIRED] query={query[:80]!r} — "
                "no session focus, injecting list_sessions context"
            )
            try:
                list_result = execute_tool("list_sessions", {})
                session_summary = json.dumps(list_result, default=str)
                initial_user_content += (
                    "\n\n[Session overview — no specific session was identified "
                    "in this query. Use this to determine which sessions are "
                    "relevant, then call artifact tools (get_collaboration_assessment, "
                    "get_transcript, get_concept_map) on relevant sessions before "
                    "responding. This overview alone is NOT sufficient for content "
                    "questions]:\n" + session_summary
                )
            except Exception as e:
                logger.warning(f"[Guardrail] list_sessions prefetch failed: {e}")

        # Path A state
        evidence: List[Dict] = []
        tool_calls_made: List[ToolCall] = []
        tools_called_with_params: set = set()
        gate_rejections = 0
        loop_messages: List[Dict] = []  # Native tool role messages accumulated per turn

        valid_tool_names = get_tool_names()

        for iteration in range(MAX_ITERATIONS):
            logger.info(f"[Agent] Iteration {iteration + 1}/{MAX_ITERATIONS}")

            system_prompt = format_system_prompt(
                memory_context=memory_context,
                steering_instructions=steering.raw_instructions
            )
            history = self._get_truncated_history(max_turns=5, max_words=350)
            messages = [
                {"role": "system", "content": system_prompt},
                *history,
                {"role": "user", "content": initial_user_content},
                *loop_messages,
            ]

            try:
                response = self.llm.complete_with_tools(
                    messages=messages,
                    tools=TOOL_SCHEMAS,
                    temperature=0.3,
                    max_tokens=2000
                )
            except Exception as e:
                logger.error(f"[Agent] LLM error at iteration {iteration + 1}: {e}")
                break

            if response.finish_reason == "tool_calls" and response.raw_response:
                # ── TOOL CALL branch ─────────────────────────────────────────
                thought = response.content.strip() if response.content else ""
                if thought:
                    logger.info(f"[Agent] THOUGHT: {thought[:500]}")

                raw_tool_calls = response.raw_response.get("tool_calls", [])
                assistant_payload_calls: List[Dict] = []
                tool_result_messages: List[Dict] = []

                for tc in raw_tool_calls:
                    func = tc.get("function", {})
                    tool_name = func.get("name", "")
                    tc_id = tc.get("id", f"call_{iteration}_{len(assistant_payload_calls)}")

                    if tool_name not in valid_tool_names:
                        logger.debug(f"[Agent] Skipping invalid tool: {tool_name}")
                        continue

                    try:
                        params = json.loads(func.get("arguments", "{}"))
                    except json.JSONDecodeError:
                        params = {}

                    # Add to assistant tool_calls payload (OpenAI requires a response for each)
                    assistant_payload_calls.append({
                        "id": tc_id,
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "arguments": func.get("arguments", "{}")
                        }
                    })

                    # Deduplication
                    params_str = json.dumps(params, sort_keys=True)
                    call_key = f"{tool_name}:{params_str}"
                    if call_key in tools_called_with_params:
                        logger.info(f"[Agent] Duplicate tool call skipped: {tool_name}")
                        tool_result_messages.append({
                            "role": "tool",
                            "tool_call_id": tc_id,
                            "content": "Already retrieved — duplicate skipped."
                        })
                        continue
                    tools_called_with_params.add(call_key)

                    # Steering validation
                    is_valid, block_reason = validate_tool_call(tool_name, steering)
                    if not is_valid:
                        logger.warning(f"[Agent] Tool blocked by steering: {block_reason}")
                        evidence.append({
                            "type": "steering_block",
                            "tool": tool_name,
                            "reason": block_reason
                        })
                        tool_result_messages.append({
                            "role": "tool",
                            "tool_call_id": tc_id,
                            "content": f"Tool blocked: {block_reason}"
                        })
                        continue

                    # Constraint validation
                    if not self._should_auto_fetch(tool_name, constraints):
                        logger.warning(f"[Agent] Tool blocked by query constraints: {tool_name}")
                        block_msg = (
                            f"Tool {tool_name} blocked by query constraints "
                            f"(allowed={constraints.allowed_tools}, "
                            f"blocked={constraints.blocked_tools})"
                        )
                        evidence.append({
                            "type": "constraint_block",
                            "tool": tool_name,
                            "reason": block_msg
                        })
                        tool_result_messages.append({
                            "role": "tool",
                            "tool_call_id": tc_id,
                            "content": "Tool blocked by query constraints."
                        })
                        continue

                    # Execute tool
                    logger.info(f"[Agent] Calling tool: {tool_name}")
                    result = execute_tool(tool_name, params)
                    evidence.append({
                        "tool": tool_name,
                        "params": params,
                        "result": result
                    })
                    tool_calls_made.append(ToolCall(
                        name=tool_name,
                        params=params,
                        reason=thought or "LLM tool call"
                    ))

                    # Record artifact retrieval in memory
                    if tool_name in [
                        'get_transcript', 'get_concept_map', 'get_collaboration_assessment'
                    ]:
                        session_id = params.get('discussion_id')
                        if session_id:
                            artifact_type = tool_name.replace('get_', '').replace('_analysis', '')
                            self.memory.record_artifact(artifact_type, session_id)
                            if not self.memory.session_focus:
                                self.memory.update_session_focus(session_id)

                    # Build display content for tool result message
                    if isinstance(result, dict) and result.get("error"):
                        content = f"Error: {result['error']}"
                    elif isinstance(result, dict):
                        content = result.get("display", "(no display content)")
                    else:
                        content = str(result)

                    tool_result_messages.append({
                        "role": "tool",
                        "tool_call_id": tc_id,
                        "content": content or "(no content)"
                    })

                # Append assistant message + tool results to loop_messages
                if assistant_payload_calls:
                    loop_messages.append({
                        "role": "assistant",
                        "content": thought if thought else None,
                        "tool_calls": assistant_payload_calls
                    })
                    loop_messages.extend(tool_result_messages)
                # else: no valid tool names found; loop continues to next iteration

            else:
                # ── TEXT RESPONSE branch ──────────────────────────────────────
                text_response = (response.content or "").strip()
                logger.info(f"[Agent] LLM text response (gate_rejections={gate_rejections})")

                # Completeness gate
                analysis = self._analyze_query_completeness(query, evidence)
                if analysis['complete'] or gate_rejections >= MAX_GATE_REJECTIONS:
                    logger.info(
                        f"[Agent] Accepting response "
                        f"(complete={analysis['complete']}, rejections={gate_rejections})"
                    )
                    suggestions = self._extract_suggestions(text_response, evidence)
                    self.memory.add_assistant_message(text_response)
                    return AgentResponse(
                        answer=text_response,
                        evidence=evidence,
                        tool_calls_made=tool_calls_made,
                        session_focus=self.memory.session_focus,
                        speaker_focus=self.memory.speaker_focus,
                        suggested_explorations=suggestions
                    )
                else:
                    # Reject — inject gate feedback and continue
                    missing_reason = analysis.get('reason', 'More evidence needed')
                    gate_rejections += 1
                    logger.info(f"[Agent] Gate rejection {gate_rejections}: {missing_reason}")
                    loop_messages.append({
                        "role": "assistant",
                        "content": text_response
                    })
                    loop_messages.append({
                        "role": "user",
                        "content": (
                            f"[Completeness check: {missing_reason}. "
                            "Please retrieve more evidence before responding.]"
                        )
                    })

        # MAX_ITERATIONS exhausted — use fallback synthesizer
        logger.warning("[Agent] MAX_ITERATIONS exhausted, using fallback")
        fallback = self._fallback_response(query, evidence)
        suggestions = self._extract_suggestions(fallback, evidence)
        self.memory.add_assistant_message(fallback)
        return AgentResponse(
            answer=fallback,
            evidence=evidence,
            tool_calls_made=tool_calls_made,
            session_focus=self.memory.session_focus,
            speaker_focus=self.memory.speaker_focus,
            suggested_explorations=suggestions
        )

    def _extract_constraints(self, query: str) -> QueryConstraints:
        """
        Extract tool constraints from query BEFORE classification.

        This handles constraint queries like:
        - "only transcript" -> allowed_tools = {get_transcript}
        - "not transcripts" -> blocked_tools = {get_transcript}
        - "focus on concept map" -> focus_tools = {get_concept_map}
        - "only collaboration metrics, not transcripts" -> allowed_tools = {get_collaboration_assessment}, blocked_tools = {get_transcript}

        Returns:
            QueryConstraints with allowed/blocked/focus tools
        """
        query_lower = query.lower()

        allowed_tools = None  # None means all allowed
        blocked_tools = set()
        focus_tools = set()

        # Patterns for "only X" (exclusive)
        only_patterns = [
            r'(?:use\s+)?only\s+(?:the\s+)?(.+?)(?:\s+to|\s+for|\s+when|\s*[,\.\?]|$)',
            r'using\s+only\s+(?:the\s+)?(.+?)(?:\s+to|\s+for|\s*[,\.\?]|$)',
            r'(?:just|exclusively)\s+(?:use\s+)?(?:the\s+)?(.+?)(?:\s+to|\s+for|\s*[,\.\?]|$)',
        ]

        # Patterns for "not X" / "don't use X" (blocked)
        not_patterns = [
            r'(?:don\'t|do\s+not|without)\s+(?:use\s+)?(?:the\s+)?(.+?)(?:\s*[,\.\?]|$)',
            r'not\s+(?:the\s+)?(.+?)(?:\s*[,\.\?]|$)',
            r'(?:no|avoid)\s+(.+?)(?:\s*[,\.\?]|$)',
        ]

        # Patterns for "focus on X" / "emphasize X" (priority)
        focus_patterns = [
            r'(?:focus(?:ing)?\s+on|emphasiz(?:e|ing)|prioritiz(?:e|ing))\s+(?:the\s+)?(.+?)(?:\s+when|\s+to|\s*[,\.\?]|$)',
            r'(?:using|with)\s+(?:primarily\s+)?(?:the\s+)?(.+?)\s+(?:as\s+)?(?:primary|main|focus)',
            r'primarily\s+(?:the\s+)?(.+?)(?:\s*[,\.\?]|$)',
        ]

        # Extract "only" constraints
        for pattern in only_patterns:
            match = re.search(pattern, query_lower)
            if match:
                artifact_phrase = match.group(1).strip()
                tool_name = self._resolve_tool_name(artifact_phrase)
                if tool_name:
                    if allowed_tools is None:
                        allowed_tools = set()
                    allowed_tools.add(tool_name)
                    logger.debug(f"[Constraints] 'only' constraint: {artifact_phrase} -> {tool_name}")

        # Extract "not" constraints
        for pattern in not_patterns:
            match = re.search(pattern, query_lower)
            if match:
                artifact_phrase = match.group(1).strip()
                tool_name = self._resolve_tool_name(artifact_phrase)
                if tool_name:
                    blocked_tools.add(tool_name)
                    logger.debug(f"[Constraints] 'not' constraint: {artifact_phrase} -> {tool_name}")

        # Extract "focus" constraints
        for pattern in focus_patterns:
            match = re.search(pattern, query_lower)
            if match:
                artifact_phrase = match.group(1).strip()
                tool_name = self._resolve_tool_name(artifact_phrase)
                if tool_name:
                    focus_tools.add(tool_name)
                    logger.debug(f"[Constraints] 'focus' constraint: {artifact_phrase} -> {tool_name}")

        # =================================================================
        # ARTIFACT MENTION DETECTION
        # If user explicitly mentions an artifact in query, ensure it's retrieved
        # e.g., "The collaboration assessment shows X" → should retrieve to verify
        # =================================================================
        mentioned_tools = set()

        # Patterns for artifact mentions (not steering commands, just mentions)
        artifact_group = r'(7c|7c\s+scores?|7c\s+analysis|collaboration\s+(?:assessment|scores?|analysis)|transcript|concept\s*map)'
        mention_patterns = [
            # "The collaboration assessment shows/indicates/reveals..."
            r'(?:the\s+)?' + artifact_group + r'\s+(?:shows?|indicates?|reveals?|suggests?)',
            # "...according to the collaboration assessment/transcript/concept map"
            r'according\s+to\s+(?:the\s+)?' + artifact_group,
            # "...based on the collaboration assessment/transcript/concept map"
            r'based\s+on\s+(?:the\s+)?' + artifact_group,
            # "...from the collaboration assessment/transcript/concept map"
            r'from\s+(?:the\s+)?' + artifact_group,
            # "...in the collaboration assessment/transcript/concept map"
            r'in\s+(?:the\s+)?' + artifact_group,
            # "what does the transcript/collaboration assessment/concept map reveal/show"
            r'what\s+does\s+(?:the\s+)?' + artifact_group + r'\s+(?:reveal|show|indicate)',
        ]

        for pattern in mention_patterns:
            matches = re.findall(pattern, query_lower)
            for match in matches:
                artifact_phrase = match if isinstance(match, str) else match[0]
                tool_name = self._resolve_tool_name(artifact_phrase)
                if tool_name:
                    mentioned_tools.add(tool_name)
                    logger.debug(f"[Constraints] Artifact mention detected: '{artifact_phrase}' -> {tool_name}")

        constraints = QueryConstraints(
            allowed_tools=allowed_tools,
            blocked_tools=blocked_tools,
            focus_tools=focus_tools,
            mentioned_tools=mentioned_tools
        )

        if allowed_tools or blocked_tools or focus_tools or mentioned_tools:
            logger.info(f"[Constraints] Extracted: allowed={allowed_tools}, blocked={blocked_tools}, focus={focus_tools}, mentioned={mentioned_tools}")

        return constraints

    def _resolve_tool_name(self, phrase: str) -> Optional[str]:
        """
        Resolve a natural language phrase to a tool name.

        Examples:
            "transcript" -> "get_transcript"
            "concept map" -> "get_concept_map"
            "7C scores" -> "get_collaboration_assessment"
            "collaboration metrics" -> "get_collaboration_assessment"
        """
        phrase_lower = phrase.lower().strip()

        # Direct lookup in TOOL_ALIASES
        if phrase_lower in TOOL_ALIASES:
            return TOOL_ALIASES[phrase_lower]

        # Check for partial matches
        for alias, tool_name in TOOL_ALIASES.items():
            if alias in phrase_lower or phrase_lower in alias:
                return tool_name

        # Check if already a tool name
        tool_names = get_tool_names()
        if phrase_lower in tool_names:
            return phrase_lower
        if f"get_{phrase_lower}" in tool_names:
            return f"get_{phrase_lower}"

        return None

    def _should_auto_fetch(self, tool_name: str, constraints: QueryConstraints) -> bool:
        """
        Check if a tool should be allowed given the query constraints.

        Returns False if the tool is blocked or not in allowed_tools (when specified).

        Note: Discovery tools (list_sessions, search_sessions) are always allowed
        since they're needed for finding which sessions to query. The constraints
        only apply to artifact tools (get_transcript, get_concept_map, get_collaboration_assessment).
        """
        # Discovery tools are always allowed - they help find sessions
        discovery_tools = {'list_sessions', 'search_sessions'}
        if tool_name in discovery_tools:
            return True

        # If this tool is explicitly blocked, don't allow it
        if tool_name in constraints.blocked_tools:
            logger.info(f"[Constraints] Blocking {tool_name}: in blocked_tools")
            return False

        # If allowed_tools is specified (for artifact tools) and this tool isn't in it, block it
        if constraints.allowed_tools is not None and tool_name not in constraints.allowed_tools:
            logger.info(f"[Constraints] Blocking {tool_name}: not in allowed_tools {constraints.allowed_tools}")
            return False

        return True


    # Common English words that should NOT be matched as session names
    # unless they appear in an explicit session-referencing context.
    # Expand this list when a new session name causes false-positive matches.
    _COMMON_WORDS = {
        # Structural / meta
        'collaboration', 'discussion', 'interview', 'session', 'table',
        'group', 'device', 'part', 'module', 'unit', 'phase', 'round',
        # Time
        'morning', 'afternoon', 'evening', 'night', 'midnight',
        'week', 'day',
        # Action / process
        'analysis', 'review', 'design', 'test', 'demo', 'show',
        'study', 'project', 'workshop', 'meeting', 'lab', 'grind',
        # Generic descriptors
        'data', 'innovation', 'class', 'course',
    }

    def _extract_sessions_from_query(self, query: str) -> Set[int]:
        """
        Extract session IDs mentioned in query by name or number.

        Returns set of session IDs that should be retrieved for this query.
        Multi-word names are matched as phrases. Single-word names that are
        common English words are only matched when preceded/followed by
        session-referencing context (e.g., "the Collaboration session").
        """
        query_lower = query.lower()
        sessions = set()

        # Check for session names (dynamically loaded from DB)
        for name, session_id in get_session_name_mapping().items():
            # Multi-word names: match as phrase with word boundaries
            if ' ' in name:
                if re.search(r'\b' + re.escape(name) + r'\b', query_lower):
                    sessions.add(session_id)
            else:
                # Single-word: skip common English words unless in session context
                if name in self._COMMON_WORDS:
                    # Only match if preceded by "the X session" or "X discussion" patterns
                    pattern = (
                        r'(?:the\s+)?' + re.escape(name) +
                        r'\s+(?:session|discussion|group)'
                        r'|'
                        r'(?:session|discussion)\s+' + re.escape(name)
                    )
                    if re.search(pattern, query_lower):
                        sessions.add(session_id)
                else:
                    if re.search(r'\b' + re.escape(name) + r'\b', query_lower):
                        sessions.add(session_id)

        # Check for explicit session numbers
        session_num_matches = re.findall(r'session\s*(\d+)', query_lower)
        for match in session_num_matches:
            sessions.add(int(match))

        return sessions

    def _extract_speakers_from_query(self, query: str) -> Set[str]:
        """
        Extract speaker names mentioned in query.

        Returns set of speaker names that should have profiles retrieved.

        Key design decisions:
        - Word-boundary matching only (no substring matches like 'ai' inside 'said')
        - Only accepts names that appear in get_known_speakers() — no length heuristic
        - For comparison patterns, BOTH extracted names must be confirmed speakers
        - Session name words are filtered out to prevent e.g. "Nuclear" (from a
          session name "Nuclear Fusion") being misidentified as a speaker
        """
        query_lower = query.lower()
        speakers = set()
        known_speakers = get_known_speakers()

        # Build set of all words in known session names — topic words, not speaker names
        session_name_words: Set[str] = set()
        for name in get_session_name_mapping().keys():
            for word in name.split():
                session_name_words.add(word.lower())

        def _is_confirmed_speaker(candidate: str) -> bool:
            """Return True only if candidate is a known speaker, not a session name word."""
            c = candidate.lower()
            # Must appear in the known speakers list
            if c not in known_speakers:
                return False
            # Reject if it's a direct single-word session name match
            if c in get_session_name_mapping():
                return False
            return True

        # 1. Speaker comparison patterns: extract both names and require both are confirmed
        for pattern in SPEAKER_COMPARISON_PATTERNS:
            match = re.search(pattern, query_lower, re.IGNORECASE)
            if match and match.lastindex and match.lastindex >= 2:
                candidate1 = match.group(1).lower()
                candidate2 = match.group(2).lower()
                # Only add if BOTH are confirmed speakers (avoids "compare Session A and Session B")
                if _is_confirmed_speaker(candidate1) and _is_confirmed_speaker(candidate2):
                    speakers.add(candidate1.title())
                    speakers.add(candidate2.title())

        # 2. Scan query for any known speaker name (word-boundary match)
        for speaker in known_speakers:
            if re.search(r'\b' + re.escape(speaker) + r'\b', query_lower):
                if _is_confirmed_speaker(speaker):
                    speakers.add(speaker.title())

        return speakers

    def _classify_query(self, query: str) -> QueryClassification:
        """
        Classify query and determine data requirements.

        This is the core of the principled query understanding system.
        Each query type has specific data requirements that must be satisfied
        before the agent can respond.

        Returns:
            QueryClassification with query_type and data requirements
        """
        query_lower = query.lower()
        required_sessions = self._extract_sessions_from_query(query)
        required_speakers = self._extract_speakers_from_query(query)

        # 0. Check for SPEAKER COMPARISON patterns FIRST
        # These need profiles for ALL mentioned speakers.
        # Guard: pattern match alone is insufficient — "Compare Dinosaurs to Nuclear Fusion"
        # matches SPEAKER_COMPARISON_PATTERNS but both are session names, not speakers.
        # Require _extract_speakers_from_query to have found >= 2 confirmed speakers.
        for pattern in SPEAKER_COMPARISON_PATTERNS:
            if re.search(pattern, query_lower, re.IGNORECASE):
                if len(required_speakers) >= 2:
                    return QueryClassification(
                        query_type='speaker_comparison',
                        required_sessions=required_sessions,
                        requires_search=len(required_sessions) == 0,
                        requires_counter_evidence=False,
                        topic=None,
                        min_sessions_needed=0,
                        required_speakers=required_speakers
                    )
                else:
                    # Pattern matched but < 2 confirmed speakers — fall through
                    logger.debug(
                        f"[Classify] Speaker comparison pattern matched but only "
                        f"{len(required_speakers)} confirmed speaker(s) found, falling through"
                    )

        # 1. Check for THEMATIC patterns (should use search_sessions)
        # These are topic-based queries without explicit session references
        for pattern in THEMATIC_PATTERNS:
            match = re.search(pattern, query_lower, re.IGNORECASE)
            if match:
                # Try to extract topic from capture group
                topic = None
                try:
                    topic = match.group(1).strip() if match.lastindex else None
                except IndexError:
                    pass

                # If no topic extracted, try to find key terms
                if not topic:
                    topic = self._extract_likely_topic(query)

                return QueryClassification(
                    query_type='thematic',
                    required_sessions=required_sessions,
                    requires_search=True,
                    requires_counter_evidence=False,
                    topic=topic,
                    min_sessions_needed=1
                )

        # 2. Check for CORRELATION patterns (specific type of hypothesis)
        # These need collaboration data from multiple sessions to test patterns
        for pattern in CORRELATION_PATTERNS:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return QueryClassification(
                    query_type='correlation',
                    required_sessions=set(),  # Need to discover via list_sessions
                    requires_search=False,
                    requires_counter_evidence=False,
                    topic=None,
                    min_sessions_needed=3  # Need at least 3 sessions for correlation
                )

        # 3. Check for HYPOTHESIS patterns
        # These need evidence from all mentioned entities + counter-evidence
        for pattern in HYPOTHESIS_PATTERNS:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return QueryClassification(
                    query_type='hypothesis',
                    required_sessions=required_sessions,
                    requires_search=len(required_sessions) == 0,  # Search if no explicit sessions
                    requires_counter_evidence=True,
                    topic=self._extract_likely_topic(query) if len(required_sessions) == 0 else None,
                    min_sessions_needed=max(2, len(required_sessions))  # Need at least 2 for comparison
                )

        # 3. Check for COMPARISON patterns
        # These need data from ALL mentioned sessions
        for pattern in COMPARISON_PATTERNS:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return QueryClassification(
                    query_type='comparison',
                    required_sessions=required_sessions,
                    requires_search=len(required_sessions) < 2,
                    requires_counter_evidence=False,
                    topic=None,
                    min_sessions_needed=max(2, len(required_sessions))
                )

        # 4. Check for SUPERLATIVE patterns
        # These need list_sessions + detailed data for top N
        for pattern in SUPERLATIVE_PATTERNS:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return QueryClassification(
                    query_type='superlative',
                    required_sessions=set(),  # Need to discover via list_sessions
                    requires_search=False,
                    requires_counter_evidence=False,
                    topic=None,
                    min_sessions_needed=2  # Need at least top 2 for comparison
                )

        # 5. Check for STRUCTURAL patterns (metadata only)
        for pattern in STRUCTURAL_PATTERNS:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return QueryClassification(
                    query_type='structural',
                    required_sessions=set(),
                    requires_search=False,
                    requires_counter_evidence=False,
                    topic=None,
                    min_sessions_needed=0  # list_sessions is sufficient
                )

        # 6. Check for SPEAKER patterns
        for pattern in SPEAKER_PATTERNS:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return QueryClassification(
                    query_type='speaker',
                    required_sessions=required_sessions,
                    requires_search=len(required_sessions) == 0,  # Search if no explicit sessions
                    requires_counter_evidence=False,
                    topic=None,
                    min_sessions_needed=1
                )

        # 7. If explicit sessions mentioned, it's a SINGLE_SESSION query
        if required_sessions:
            return QueryClassification(
                query_type='single_session',
                required_sessions=required_sessions,
                requires_search=False,
                requires_counter_evidence=False,
                topic=None,
                min_sessions_needed=len(required_sessions)
            )

        # 8. Default: Treat as THEMATIC (use search to find relevant sessions)
        # This ensures we use semantic search for ambiguous queries
        return QueryClassification(
            query_type='unknown',
            required_sessions=set(),
            requires_search=True,
            requires_counter_evidence=False,
            topic=self._extract_likely_topic(query),
            min_sessions_needed=1
        )

    def _extract_likely_topic(self, query: str) -> str:
        """
        Extract the likely topic from a query for semantic search.

        Removes common question words and returns key content words.
        """
        # Remove common question starters
        query_lower = query.lower()
        remove_phrases = [
            r'^what\s+(was|were|is|are)\s+',
            r'^how\s+(did|does|do|was|were)\s+',
            r'^which\s+',
            r'^where\s+(did|does|was|were)\s+',
            r'^when\s+(did|does|was|were)\s+',
            r'^can\s+you\s+',
            r'^tell\s+me\s+about\s+',
            r'^show\s+me\s+',
            r'^find\s+',
            r'^search\s+for\s+',
        ]

        topic = query_lower
        for pattern in remove_phrases:
            topic = re.sub(pattern, '', topic, flags=re.IGNORECASE)

        # Remove trailing punctuation
        topic = re.sub(r'[?.!]+$', '', topic).strip()

        # If topic is too long, take first 100 chars
        if len(topic) > 100:
            topic = topic[:100]

        return topic if topic else query[:50]

    def _is_comparison_query(self, query: str) -> bool:
        """Check if query requires comparing multiple sessions."""
        query_lower = query.lower()

        # Check comparison patterns
        for pattern in COMPARISON_PATTERNS:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return True

        return False

    def _is_superlative_query(self, query: str) -> bool:
        """Check if query asks for best/worst/ranking across sessions."""
        query_lower = query.lower()

        for pattern in SUPERLATIVE_PATTERNS:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return True

        return False

    def _get_sessions_retrieved(self, evidence: List[Dict]) -> Set[int]:
        """Extract session IDs from successfully retrieved evidence.

        Error-aware: skips entries where the tool call returned an error.
        Batch-aware: handles discussion_ids list params from batch tool calls.
        """
        sessions = set()

        for e in evidence:
            # Skip blocked entries (never executed)
            if e.get("type") in ("steering_block", "constraint_block"):
                continue

            result = e.get("result", {})
            params = e.get("params", {})

            # Error-aware: don't count failed retrievals
            if result.get("error"):
                continue

            # Single-mode: discussion_id in params or result
            session_id = params.get("discussion_id") or result.get("discussion_id")
            if session_id:
                sessions.add(int(session_id))

            # Batch-mode: discussion_ids list
            batch_ids = params.get("discussion_ids") or result.get("discussion_ids")
            if batch_ids and isinstance(batch_ids, list):
                sessions.update(int(sid) for sid in batch_ids if sid)

        return sessions

    def _get_speakers_retrieved(self, evidence: List[Dict]) -> Set[str]:
        """Extract speaker names from successfully retrieved evidence.

        Error-aware: skips entries where the tool call returned an error.
        Batch-aware: handles speaker_names list params from batch tool calls.
        """
        speakers = set()

        for e in evidence:
            if e.get("type") in ("steering_block", "constraint_block"):
                continue

            result = e.get("result", {})
            params = e.get("params", {})

            # Error-aware
            if result.get("error"):
                continue

            if e.get("tool") == "get_speaker_profile":
                # Single-mode
                speaker_name = params.get("speaker_name", "")
                if speaker_name:
                    speakers.add(speaker_name.title())
                # Batch-mode
                speaker_names = params.get("speaker_names")
                if speaker_names and isinstance(speaker_names, list):
                    speakers.update(n.title() for n in speaker_names if n)

        return speakers

    def _get_sessions_with_7c(self, evidence: List[Dict]) -> Set[int]:
        """Extract session IDs that have collaboration assessment successfully retrieved.

        Error-aware: skips entries where the tool call returned an error.
        Batch-aware: handles discussion_ids list params from batch tool calls.
        """
        sessions = set()

        for e in evidence:
            if e.get("type") in ("steering_block", "constraint_block"):
                continue

            result = e.get("result", {})
            params = e.get("params", {})

            # Error-aware
            if result.get("error"):
                continue

            if e.get("tool") == "get_collaboration_assessment":
                session_id = params.get("discussion_id") or result.get("discussion_id")
                if session_id:
                    sessions.add(int(session_id))
                # Batch-mode
                batch_ids = params.get("discussion_ids") or result.get("discussion_ids")
                if batch_ids and isinstance(batch_ids, list):
                    sessions.update(int(sid) for sid in batch_ids if sid)

        return sessions

    def _analyze_query_completeness(self, query: str, evidence: List[Dict]) -> dict:
        """
        Analyze whether we have sufficient evidence for the query.

        This is the key gating function that prevents premature responses.
        Uses query classification to determine data requirements.

        Returns:
            {
                'query_type': str,
                'classification': QueryClassification,
                'required_sessions': Set[int],
                'retrieved_sessions': Set[int],
                'missing_sessions': Set[int],
                'has_search_results': bool,
                'has_detailed_data': bool,
                'complete': bool,
                'reason': Optional[str]  # Why incomplete
            }
        """
        classification = self._classify_query(query)
        retrieved_sessions = self._get_sessions_retrieved(evidence)
        retrieved_speakers = self._get_speakers_retrieved(evidence)

        # Check what types of evidence we have
        has_search_results = any(
            e.get("tool") == "search_sessions"
            for e in evidence if e.get("type") != "steering_block"
        )
        has_list_overview = any(
            e.get("tool") == "list_sessions"
            for e in evidence if e.get("type") != "steering_block"
        )
        has_detailed_data = any(
            e.get("tool") in ["get_collaboration_assessment", "get_concept_map", "get_transcript"]
            for e in evidence if e.get("type") != "steering_block"
        )
        has_speaker_data = any(
            e.get("tool") == "get_speaker_profile"
            for e in evidence if e.get("type") != "steering_block"
        )

        base_result = {
            'query_type': classification.query_type,
            'classification': classification,
            'required_sessions': classification.required_sessions,
            'retrieved_sessions': retrieved_sessions,
            'required_speakers': classification.required_speakers,
            'retrieved_speakers': retrieved_speakers,
            'has_search_results': has_search_results,
            'has_detailed_data': has_detailed_data,
            'has_speaker_data': has_speaker_data,
            # Legacy fields for backwards compatibility
            'is_comparison': classification.query_type in ['comparison', 'hypothesis', 'speaker_comparison'],
            'is_superlative': classification.query_type == 'superlative',
            'is_speaker_comparison': classification.query_type == 'speaker_comparison',
        }

        # =================================================================
        # CONSTRAINT-DRIVEN COMPLETENESS: Check if constrained tools used
        # This ensures "only collaboration metrics" actually calls get_collaboration_assessment
        # =================================================================
        constraints = self._extract_constraints(query)
        if constraints.allowed_tools:
            # User explicitly requested specific tools (e.g., "only collaboration metrics")
            # Check if ANY of those tools have been called
            tools_used = {
                e.get('tool') for e in evidence
                if e.get('type') not in ('steering_block', 'constraint_block')
            }
            constrained_tools_used = constraints.allowed_tools & tools_used

            if not constrained_tools_used:
                # We have NOT called the required tools yet
                # Discovery tools are fine, but we need the actual data tools
                missing_tool = list(constraints.allowed_tools)[0]

                # Get a session ID to query (from list_sessions or search_sessions results)
                session_id = None
                for e in evidence:
                    if e.get('tool') in ('list_sessions', 'search_sessions'):
                        result = e.get('result', {})
                        sessions = result.get('sessions', [])
                        if sessions:
                            session_id = sessions[0].get('session_id')
                            break

                logger.info(f"[Constraints] Constrained tools {constraints.allowed_tools} not yet used. "
                           f"Forcing {missing_tool} for session {session_id}")

                return {
                    **base_result,
                    'missing_sessions': set(),
                    'missing_speakers': set(),
                    'complete': False,
                    'reason': f'Query requires {constraints.allowed_tools} but none have been called yet',
                    'next_action': missing_tool,
                    'next_action_session': session_id,  # Pass session ID for the forced tool
                    'constraint_driven': True
                }

        # SPEAKER_COMPARISON: Need profiles for ALL mentioned speakers
        if classification.query_type == 'speaker_comparison':
            missing_speakers = classification.required_speakers - retrieved_speakers
            if missing_speakers:
                return {
                    **base_result,
                    'missing_sessions': set(),
                    'missing_speakers': missing_speakers,
                    'complete': False,
                    'reason': f'Missing speaker profiles for: {missing_speakers}',
                    'next_action': 'get_speaker_profile'
                }
            # Need profiles for at least 2 speakers for comparison
            if len(retrieved_speakers) < 2:
                return {
                    **base_result,
                    'missing_sessions': set(),
                    'missing_speakers': classification.required_speakers,
                    'complete': False,
                    'reason': 'Need speaker profiles for both speakers to compare',
                    'next_action': 'get_speaker_profile'
                }
            return {**base_result, 'missing_sessions': set(), 'missing_speakers': set(), 'complete': True, 'reason': None}

        # CORRELATION: Need collaboration data from at least 3 sessions to test pattern
        if classification.query_type == 'correlation':
            sessions_with_7c = self._get_sessions_with_7c(evidence)
            if not has_list_overview:
                return {
                    **base_result,
                    'missing_sessions': set(),
                    'sessions_with_7c': sessions_with_7c,
                    'complete': False,
                    'reason': 'Need list_sessions to find sessions for correlation analysis',
                    'next_action': 'list_sessions'
                }
            if len(sessions_with_7c) < 3:
                return {
                    **base_result,
                    'missing_sessions': set(),
                    'sessions_with_7c': sessions_with_7c,
                    'complete': False,
                    'reason': f'Need collaboration data from at least 3 sessions to test correlation (have {len(sessions_with_7c)})',
                    'next_action': 'get_collaboration_assessment'
                }
            return {**base_result, 'missing_sessions': set(), 'sessions_with_7c': sessions_with_7c, 'complete': True, 'reason': None}

        # THEMATIC: Need search + retrieval from at least one match
        if classification.query_type == 'thematic':
            if not has_search_results:
                return {
                    **base_result,
                    'missing_sessions': set(),
                    'complete': False,
                    'reason': 'Need to search for relevant sessions first',
                    'next_action': 'search_sessions'
                }
            if not has_detailed_data:
                return {
                    **base_result,
                    'missing_sessions': set(),
                    'complete': False,
                    'reason': 'Need to retrieve data from search results',
                    'next_action': 'get_artifact'
                }
            return {**base_result, 'missing_sessions': set(), 'complete': True, 'reason': None}

        # COMPARISON: Need data for ALL mentioned sessions
        if classification.query_type == 'comparison':
            missing = classification.required_sessions - retrieved_sessions
            if missing:
                return {
                    **base_result,
                    'missing_sessions': missing,
                    'complete': False,
                    'reason': f'Missing data for sessions: {missing}'
                }
            return {**base_result, 'missing_sessions': set(), 'complete': True, 'reason': None}

        # HYPOTHESIS: Need data for all entities + detailed artifact data
        if classification.query_type == 'hypothesis':
            missing = classification.required_sessions - retrieved_sessions
            # For hypothesis, we need data from at least 2 sessions for comparison
            needs_more = len(retrieved_sessions) < classification.min_sessions_needed

            if missing:
                return {
                    **base_result,
                    'missing_sessions': missing,
                    'complete': False,
                    'reason': f'Missing data for sessions: {missing}'
                }
            if needs_more and not has_search_results:
                return {
                    **base_result,
                    'missing_sessions': set(),
                    'complete': False,
                    'reason': f'Need data from at least {classification.min_sessions_needed} sessions for hypothesis testing',
                    'next_action': 'search_sessions' if not classification.required_sessions else 'get_artifact'
                }
            if classification.requires_search and not has_search_results:
                return {
                    **base_result,
                    'missing_sessions': set(),
                    'complete': False,
                    'reason': 'Need to search for relevant sessions for hypothesis',
                    'next_action': 'search_sessions'
                }
            # Even with search results, hypothesis testing requires detailed
            # artifact data (assessments, transcripts) — not just discovery
            if not has_detailed_data:
                return {
                    **base_result,
                    'missing_sessions': set(),
                    'complete': False,
                    'reason': 'Hypothesis testing requires detailed artifact data (collaboration assessments, transcripts, or concept maps) — not just search results',
                    'next_action': 'get_collaboration_assessment'
                }
            return {**base_result, 'missing_sessions': set(), 'complete': True, 'reason': None}

        # SUPERLATIVE: Need list_sessions + detailed data for top candidates
        if classification.query_type == 'superlative':
            if not has_list_overview:
                return {
                    **base_result,
                    'missing_sessions': set(),
                    'complete': False,
                    'reason': 'Need list_sessions to see all scores',
                    'next_action': 'list_sessions'
                }
            if not has_detailed_data:
                return {
                    **base_result,
                    'missing_sessions': set(),
                    'complete': False,
                    'reason': 'Need detailed data for top candidates',
                    'next_action': 'get_collaboration_assessment'
                }
            if len(retrieved_sessions) < classification.min_sessions_needed:
                return {
                    **base_result,
                    'missing_sessions': set(),
                    'complete': False,
                    'reason': f'Need detailed data for at least {classification.min_sessions_needed} sessions',
                    'next_action': 'get_collaboration_assessment'
                }
            return {**base_result, 'missing_sessions': set(), 'complete': True, 'reason': None}

        # STRUCTURAL: list_sessions is sufficient
        if classification.query_type == 'structural':
            if not has_list_overview:
                return {
                    **base_result,
                    'missing_sessions': set(),
                    'complete': False,
                    'reason': 'Need list_sessions for structural query',
                    'next_action': 'list_sessions'
                }
            return {**base_result, 'missing_sessions': set(), 'complete': True, 'reason': None}

        # SPEAKER: Need speaker profile or search
        if classification.query_type == 'speaker':
            has_speaker_data = any(
                e.get("tool") == "get_speaker_profile"
                for e in evidence if e.get("type") != "steering_block"
            )
            if not has_speaker_data and not has_detailed_data:
                return {
                    **base_result,
                    'missing_sessions': set(),
                    'complete': False,
                    'reason': 'Need speaker profile or session data',
                    'next_action': 'get_speaker_profile' if not classification.requires_search else 'search_sessions'
                }
            return {**base_result, 'missing_sessions': set(), 'complete': True, 'reason': None}

        # SINGLE_SESSION: Need data for the specified session(s)
        if classification.query_type == 'single_session':
            missing = classification.required_sessions - retrieved_sessions
            if missing:
                return {
                    **base_result,
                    'missing_sessions': missing,
                    'complete': False,
                    'reason': f'Need data for session(s): {missing}'
                }
            return {**base_result, 'missing_sessions': set(), 'complete': True, 'reason': None}

        # UNKNOWN: Query doesn't match any known pattern.
        # If the LLM called discovery tools (search/list), it found sessions —
        # require artifact-level data before accepting the response.
        # If no tools were called at all (conversational), accept as-is.
        if classification.query_type == 'unknown':
            has_discovery = has_search_results or has_list_overview
            if has_discovery and not has_detailed_data:
                return {
                    **base_result,
                    'missing_sessions': set(),
                    'complete': False,
                    'reason': 'Discovery tools were called but no detailed artifact data retrieved — call get_collaboration_assessment, get_transcript, or get_concept_map on relevant sessions',
                    'next_action': 'get_artifact'
                }
            return {**base_result, 'missing_sessions': set(), 'complete': True, 'reason': None}

        # Default: Any evidence is sufficient
        return {
            **base_result,
            'missing_sessions': set(),
            'complete': len(evidence) > 0,
            'reason': 'No evidence gathered' if len(evidence) == 0 else None
        }


    def _extract_suggestions(self, answer: str, evidence: List[Dict]) -> List[str]:
        """Extract or generate suggestions for further exploration."""
        suggestions = []

        # Check what artifacts were NOT retrieved
        retrieved_types = set()
        retrieved_sessions = set()

        for e in evidence:
            tool = e.get("tool", "")
            result = e.get("result", {})

            if tool == "get_transcript":
                retrieved_types.add("transcript")
                # session_id is still available in result metadata
                if result.get("discussion_id"):
                    retrieved_sessions.add(result.get("discussion_id"))
            elif tool == "get_concept_map":
                retrieved_types.add("concept_map")
                if result.get("discussion_id"):
                    retrieved_sessions.add(result.get("discussion_id"))
            elif tool == "get_collaboration_assessment":
                retrieved_types.add("7c")
                if result.get("discussion_id"):
                    retrieved_sessions.add(result.get("discussion_id"))

        # Suggest unexplored artifacts for retrieved sessions
        if retrieved_sessions:
            session_id = list(retrieved_sessions)[0]
            if "concept_map" not in retrieved_types:
                suggestions.append(f"You might want to explore the concept map for session {session_id} to see how ideas connect.")
            if "7c" not in retrieved_types:
                suggestions.append(f"The collaboration assessment for session {session_id} could show interaction quality.")

        return suggestions[:2]  # Limit suggestions

    def _fallback_response(self, query: str, evidence: List[Dict]) -> str:
        """
        Generate a fallback response when MAX_ITERATIONS is exhausted.

        Instead of listing tool names, uses the LLM to synthesize from
        gathered evidence. This fires for complex cross-session queries
        that exhaust the tool budget.
        """
        if not evidence:
            return "I wasn't able to find relevant information for your query. Could you provide more details or specify a session?"

        # Build a condensed evidence summary for the synthesis call
        evidence_parts = []
        for e in evidence:
            tool = e.get("tool")
            result = e.get("result", {})
            if not tool or not isinstance(result, dict):
                continue
            display = result.get("display", "")
            if not display:
                continue
            # Truncate very long displays to stay within token budget
            if len(display) > 2000:
                display = display[:2000] + "\n[... truncated]"
            evidence_parts.append(f"=== {tool} ===\n{display}")

        if not evidence_parts:
            return "I retrieved data for your query but wasn't able to produce a complete synthesis. Could you try a more specific question?"

        evidence_text = "\n\n".join(evidence_parts)

        # Use the LLM to synthesize — one focused call, no tools
        try:
            synthesis_response = self.llm.complete(
                messages=[
                    {"role": "system", "content": (
                        "You are a learning analytics assistant. The user asked a question and "
                        "several data retrievals were performed but ran out of processing budget "
                        "before a response was generated. Synthesize the gathered evidence into "
                        "a direct, analytical answer. Cite specific scores, quotes, and session "
                        "names. Do NOT mention tools, iterations, or technical issues — just "
                        "answer the question naturally using the data below."
                    )},
                    {"role": "user", "content": f"Question: {query}\n\nGathered evidence:\n{evidence_text}"}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            answer = synthesis_response.content.strip()
            if answer:
                logger.info(f"[Agent] Fallback synthesis produced {len(answer.split())}w response")
                return answer
        except Exception as e:
            logger.error(f"[Agent] Fallback synthesis LLM call failed: {e}")

        # Last resort: summarize what we found without LLM
        sessions_found = set()
        for e in evidence:
            result = e.get("result", {})
            if isinstance(result, dict):
                sid = result.get("discussion_id") or e.get("params", {}).get("discussion_id")
                name = result.get("session_name", "")
                if sid:
                    sessions_found.add(name or f"Session {sid}")
        if sessions_found:
            return f"I found data for {', '.join(sessions_found)} but wasn't able to fully synthesize a response. Could you try a more focused question about a specific session or dimension?"
        return "I retrieved data for your query but wasn't able to produce a complete synthesis. Could you try a more specific question?"


# =============================================================================
# Convenience Functions
# =============================================================================

def run_agent(conversation_id: str, query: str, session_focus: int = None) -> AgentResponse:
    """
    Run the agent for a single query.

    This is the main entry point for the routes.

    Args:
        conversation_id: Unique conversation identifier
        query: User's query
        session_focus: Optional session_device_id the user is currently viewing

    Returns:
        AgentResponse with answer and metadata
    """
    agent = ScaffoldingAgent(conversation_id)
    if session_focus is not None:
        agent.memory.session_focus = session_focus
        # Populate session_name so memory context is concrete, not just "Session 34"
        from agent_v7.memory import get_session_name_by_id
        name = get_session_name_by_id(session_focus)
        if name:
            agent.memory.session_name = name
    return agent.respond(query)


def clear_conversation(conversation_id: str):
    """Clear conversation memory."""
    from .memory import clear_memory
    clear_memory(conversation_id)
