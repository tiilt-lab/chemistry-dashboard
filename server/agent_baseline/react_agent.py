"""
ReAct Agent for BLINC Agent Baseline (Transcript-Only)

A simplified agent with transcript-only access for fair comparison with V7.
Uses the same ReAct architecture but with restricted tools:
- list_sessions (no collaboration scores)
- search_sessions (transcript collection only)
- get_transcript
- get_speaker_profile (psycholinguistic metrics only)

NO access to: concept maps, collaboration assessment
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple, Callable, Set

from .llm import get_reasoning_client, LLMResponse
from .memory import ConversationMemory, get_memory
from .steering import extract_steering, validate_tool_call, SteeringDirectives
from .tools import CORE_TOOLS, TOOL_SCHEMAS, execute_tool, get_tool_names
from .prompts import (
    format_system_prompt,
    format_tool_descriptions_for_llm,
    TOOL_DESCRIPTIONS
)

logger = logging.getLogger(__name__)

# Maximum iterations to prevent infinite loops
MAX_ITERATIONS = 8

# Maximum evidence items to include in context
MAX_EVIDENCE_ITEMS = 20

# Session name mapping is loaded dynamically from DB via memory.py

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

# Patterns that indicate thematic/topic-based queries (should use search_sessions)
THEMATIC_PATTERNS = [
    r'(?:what\s+was\s+)?(?:said|discussed|mentioned|talked)\s+about\s+(.+?)(?:\?|$|across|in\s+the)',
    r'(?:sessions?|discussions?)\s+(?:about|on|regarding|involving|related\s+to)\s+(.+?)(?:\?|$)',
    r'(?:find|search|look\s+for)\s+(?:sessions?|discussions?)\s+(?:about|on|regarding)\s+(.+?)(?:\?|$)',
    r'(?:where|when)\s+(?:was|were|did)\s+(.+?)\s+(?:discussed|mentioned|brought\s+up)',
    r'(?:any\s+)?(?:sessions?|discussions?)\s+(?:that\s+)?(?:mention|discuss|cover|address)\s+(.+?)(?:\?|$)',
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
_speaker_cache = None
_speaker_cache_time = 0
SPEAKER_CACHE_TTL = 300  # 5 minutes

def get_known_speakers() -> Set[str]:
    """Get known speaker names from database (cached)."""
    global _speaker_cache, _speaker_cache_time
    import time

    if _speaker_cache is not None and (time.time() - _speaker_cache_time) < SPEAKER_CACHE_TTL:
        return _speaker_cache

    try:
        import mysql.connector
        conn = mysql.connector.connect(
            host='localhost',
            user='vagrant',
            password='vagrant',
            database='discussion_capture'
        )
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT LOWER(alias) FROM speaker WHERE alias IS NOT NULL AND alias != ''")
        speakers = {row[0] for row in cursor.fetchall()}
        cursor.close()
        conn.close()

        speakers.update({'speaker_00', 'speaker_01', 'speaker_02', 'speaker_03', 'speaker_04'})
        _speaker_cache = speakers
        _speaker_cache_time = time.time()
        return speakers

    except Exception as e:
        logger.warning(f"[Speakers] Failed to load from database: {e}, using fallback")
        return {
            'tucker', 'sam', 'david', 'lex', 'noah', 'john', 'jane',
            'alice', 'bob', 'vanessa', 'julia', 'oliver', 'ezra', 'derek', 'dave',
            'speaker_00', 'speaker_01', 'speaker_02', 'speaker_03'
        }

# Tool name normalization for constraint extraction (BASELINE: transcript-only)
TOOL_ALIASES = {
    'transcript': 'get_transcript',
    'transcripts': 'get_transcript',
    'speaker profile': 'get_speaker_profile',
    'speaker profiles': 'get_speaker_profile',
    # Note: Concept map and collaboration assessment aliases are NOT included in baseline
}


@dataclass
class QueryConstraints:
    """Explicit tool constraints extracted from query."""
    allowed_tools: Optional[Set[str]] = None
    blocked_tools: Set[str] = field(default_factory=set)
    focus_tools: Set[str] = field(default_factory=set)
    mentioned_tools: Set[str] = field(default_factory=set)


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
    Baseline ReAct agent with transcript-only access.

    Same architecture as V7, but restricted to 4 tools:
    - list_sessions (no collaboration scores)
    - search_sessions (transcript collection only)
    - get_transcript
    - get_speaker_profile (psycholinguistic only)
    """

    def __init__(self, conversation_id: str):
        """Initialize agent with conversation memory."""
        self.conversation_id = conversation_id
        self.memory = get_memory(conversation_id)
        self.llm = get_reasoning_client()
        self._tools_dict = self._create_tools_dict()

    def _create_tools_dict(self) -> Dict[str, Callable]:
        """Create a dictionary of callable tools."""
        def make_tool_fn(tool_name: str) -> Callable:
            def tool_fn(**kwargs):
                return execute_tool(tool_name, kwargs)
            return tool_fn

        return {
            'list_sessions': make_tool_fn('list_sessions'),
            'search_sessions': make_tool_fn('search_sessions'),
            'get_transcript': make_tool_fn('get_transcript'),
            'get_speaker_profile': make_tool_fn('get_speaker_profile'),
        }

    def respond(self, query: str) -> AgentResponse:
        """
        Process a user query and return a scaffolded response.

        V7 Baseline Flow (Pure ReAct with transcript-only access):
        1. Extract context (session/speaker focus, steering)
        2. Run ReAct loop - LLM decides what tools to call
        3. Synthesize and return response
        """
        logger.info(f"[Baseline Agent] Processing query: {query[:100]}...")

        # Start new turn
        self.memory.start_new_turn()
        self.memory.add_user_message(query)

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

        speaker = self.memory.extract_speaker_from_text(query)
        if speaker and speaker != self.memory.speaker_focus:
            self.memory.update_speaker_focus(speaker)

        # Run pure ReAct loop
        return self._run_react_loop(query, steering)

    def _run_react_loop(
        self,
        query: str,
        steering: SteeringDirectives
    ) -> AgentResponse:
        """Run the ReAct loop to process a query."""
        logger.info(f"[Baseline Agent] Running ReAct loop")

        # Extract constraints
        constraints = self._extract_constraints(query)

        # Build context
        memory_context = self.memory.get_context_for_llm()

        # ReAct loop
        evidence = []
        tool_calls_made = []
        tools_called_with_params = set()

        for iteration in range(MAX_ITERATIONS):
            logger.info(f"[Baseline Agent] Iteration {iteration + 1}/{MAX_ITERATIONS}")

            # Decide next action
            action = self._decide_action(
                query=query,
                memory_context=memory_context,
                evidence=evidence,
                steering=steering
            )

            if action.action_type == "respond":
                logger.info("[Baseline Agent] Decided to respond")
                break

            elif action.action_type == "tool_call" and action.tool_call:
                tool_call = action.tool_call

                # Skip invalid tool names
                valid_tool_names = get_tool_names()
                if tool_call.name not in valid_tool_names:
                    logger.debug(f"[Baseline Agent] Skipping invalid tool: {tool_call.name}")
                    continue

                logger.info(f"[Baseline Agent] Calling tool: {tool_call.name}")

                # Check for duplicates
                params_str = json.dumps(tool_call.params, sort_keys=True)
                call_key = f"{tool_call.name}:{params_str}"

                if call_key in tools_called_with_params:
                    logger.info(f"[Baseline Agent] Skipping duplicate tool call: {tool_call.name}")
                    if evidence:
                        break
                    else:
                        continue

                tools_called_with_params.add(call_key)

                # Validate against steering
                is_valid, reason = validate_tool_call(tool_call.name, steering)
                if not is_valid:
                    logger.warning(f"[Baseline Agent] Tool blocked by steering: {reason}")
                    evidence.append({
                        "type": "steering_block",
                        "tool": tool_call.name,
                        "reason": reason
                    })
                    continue

                # Validate against query constraints
                if not self._should_auto_fetch(tool_call.name, constraints):
                    logger.warning(f"[Baseline Agent] Tool blocked by query constraints: {tool_call.name}")
                    evidence.append({
                        "type": "constraint_block",
                        "tool": tool_call.name,
                        "reason": f"Tool {tool_call.name} blocked by query constraints"
                    })
                    continue

                # Execute tool
                result = execute_tool(tool_call.name, tool_call.params)
                evidence.append({
                    "tool": tool_call.name,
                    "params": tool_call.params,
                    "result": result
                })
                tool_calls_made.append(tool_call)

                # Record in memory
                if tool_call.name == 'get_transcript':
                    session_id = tool_call.params.get('discussion_id')
                    if session_id:
                        self.memory.record_artifact('transcript', session_id)
                        if not self.memory.session_focus:
                            self.memory.update_session_focus(session_id)

        # Synthesize response
        answer = self._synthesize_response(
            query=query,
            memory_context=memory_context,
            evidence=evidence,
            steering=steering
        )

        # Extract suggestions
        suggestions = self._extract_suggestions(answer, evidence)

        # Update memory
        self.memory.add_assistant_message(answer)

        return AgentResponse(
            answer=answer,
            evidence=evidence,
            tool_calls_made=tool_calls_made,
            session_focus=self.memory.session_focus,
            speaker_focus=self.memory.speaker_focus,
            suggested_explorations=suggestions
        )

    def _extract_constraints(self, query: str) -> QueryConstraints:
        """Extract tool constraints from query."""
        query_lower = query.lower()

        allowed_tools = None
        blocked_tools = set()
        focus_tools = set()

        # Patterns for "only X" (exclusive)
        only_patterns = [
            r'(?:use\s+)?only\s+(?:the\s+)?(.+?)(?:\s+to|\s+for|\s+when|\s*[,\.\?]|$)',
            r'using\s+only\s+(?:the\s+)?(.+?)(?:\s+to|\s+for|\s*[,\.\?]|$)',
        ]

        # Patterns for "not X" / "don't use X" (blocked)
        not_patterns = [
            r'(?:don\'t|do\s+not|without)\s+(?:use\s+)?(?:the\s+)?(.+?)(?:\s*[,\.\?]|$)',
            r'not\s+(?:the\s+)?(.+?)(?:\s*[,\.\?]|$)',
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

        # Extract "not" constraints
        for pattern in not_patterns:
            match = re.search(pattern, query_lower)
            if match:
                artifact_phrase = match.group(1).strip()
                tool_name = self._resolve_tool_name(artifact_phrase)
                if tool_name:
                    blocked_tools.add(tool_name)

        return QueryConstraints(
            allowed_tools=allowed_tools,
            blocked_tools=blocked_tools,
            focus_tools=focus_tools,
            mentioned_tools=set()
        )

    def _resolve_tool_name(self, phrase: str) -> Optional[str]:
        """Resolve a natural language phrase to a tool name."""
        phrase_lower = phrase.lower().strip()

        if phrase_lower in TOOL_ALIASES:
            return TOOL_ALIASES[phrase_lower]

        for alias, tool_name in TOOL_ALIASES.items():
            if alias in phrase_lower or phrase_lower in alias:
                return tool_name

        tool_names = get_tool_names()
        if phrase_lower in tool_names:
            return phrase_lower
        if f"get_{phrase_lower}" in tool_names:
            return f"get_{phrase_lower}"

        return None

    def _should_auto_fetch(self, tool_name: str, constraints: QueryConstraints) -> bool:
        """Check if a tool should be allowed given the query constraints."""
        discovery_tools = {'list_sessions', 'search_sessions'}
        if tool_name in discovery_tools:
            return True

        if tool_name in constraints.blocked_tools:
            return False

        if constraints.allowed_tools is not None and tool_name not in constraints.allowed_tools:
            return False

        return True

    def _decide_action(
        self,
        query: str,
        memory_context: str,
        evidence: List[Dict],
        steering: SteeringDirectives
    ) -> AgentAction:
        """Use LLM to decide next action: call a tool or respond."""
        system_prompt = format_system_prompt(
            memory_context=memory_context,
            steering_instructions=steering.raw_instructions
        )

        evidence_str = self._format_evidence_for_context(evidence)

        user_message = f"""Query: {query}

Evidence gathered so far:
{evidence_str if evidence_str else "None yet"}

Before deciding your action, reason about:
1. What evidence do I have?
2. What evidence do I still need for a complete answer?
3. What should I do next?

Use this format:

THOUGHT: [Your reasoning about evidence, gaps, and next step]
ACTION: respond
RESPONSE: [Your complete answer with citations]

OR

THOUGHT: [Your reasoning about evidence, gaps, and next step]
ACTION: tool_call
TOOL: [tool_name]
PARAMS: {{"param": "value"}}

IMPORTANT: Make ONE tool call at a time. If you need data from multiple sessions,
call the tool once, then in the next turn call it again for the next session.

Remember: You have access to ONLY transcript and speaker profile tools.
You do NOT have concept map or collaboration assessment access.
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        try:
            response = self.llm.complete_with_tools(
                messages=messages,
                tools=TOOL_SCHEMAS,
                temperature=0.3,
                max_tokens=2000
            )

            # Check if LLM made a tool call
            if response.finish_reason == "tool_calls" and response.raw_response:
                tool_calls = response.raw_response.get("tool_calls", [])
                valid_tool_names = get_tool_names()

                for tc in tool_calls:
                    func = tc.get("function", {})
                    tool_name = func.get("name", "")

                    if tool_name not in valid_tool_names:
                        continue

                    try:
                        params = json.loads(func.get("arguments", "{}"))
                    except json.JSONDecodeError:
                        params = {}

                    return AgentAction(
                        action_type="tool_call",
                        tool_call=ToolCall(
                            name=tool_name,
                            params=params,
                            reason="LLM tool call"
                        )
                    )

            # Parse LLM's text response
            content = response.content
            thought, action_type, action_content = self._parse_react_format(content)

            if thought:
                logger.info(f"[Baseline Agent] THOUGHT: {thought[:300]}...")

            if action_type == "respond":
                return AgentAction(
                    action_type="respond",
                    response=action_content or ""
                )

            elif action_type == "tool_call":
                tool_call = self._parse_tool_call_from_text(action_content)
                if tool_call:
                    valid_tool_names = get_tool_names()
                    if tool_call.name in valid_tool_names:
                        return AgentAction(
                            action_type="tool_call",
                            tool_call=tool_call
                        )

            # Fallback
            if content.strip().upper().startswith("RESPOND:"):
                return AgentAction(
                    action_type="respond",
                    response=content[8:].strip()
                )
            elif "TOOL:" in content.upper():
                tool_call = self._parse_tool_call_from_text(content)
                if tool_call:
                    return AgentAction(
                        action_type="tool_call",
                        tool_call=tool_call
                    )

            if evidence:
                return AgentAction(action_type="respond")
            else:
                default_tool = self._get_default_tool_call(query)
                if default_tool:
                    return AgentAction(
                        action_type="tool_call",
                        tool_call=default_tool
                    )
                return AgentAction(action_type="respond")

        except Exception as e:
            logger.error(f"[Baseline Agent] Decision error: {e}")
            return AgentAction(action_type="respond")

    def _parse_react_format(self, content: str) -> Tuple[str, str, str]:
        """Parse THOUGHT → ACTION format from LLM response."""
        thought = ""
        action_type = ""
        action_content = ""

        # Extract THOUGHT
        thought_match = re.search(r'THOUGHT:\s*(.+?)(?=ACTION:|$)', content, re.DOTALL | re.IGNORECASE)
        if thought_match:
            thought = thought_match.group(1).strip()

        # Extract ACTION
        action_match = re.search(r'ACTION:\s*(\w+)', content, re.IGNORECASE)
        if action_match:
            action_type = action_match.group(1).lower()

        # Extract content based on action type
        if action_type == "respond":
            response_match = re.search(r'RESPONSE:\s*(.+?)$', content, re.DOTALL | re.IGNORECASE)
            if response_match:
                action_content = response_match.group(1).strip()
        elif action_type == "tool_call":
            # Everything after ACTION: tool_call
            action_idx = content.upper().find("ACTION:")
            if action_idx >= 0:
                action_content = content[action_idx:]

        return thought, action_type, action_content

    def _parse_tool_call_from_text(self, text: str) -> Optional[ToolCall]:
        """Parse tool call from text format."""
        if not text:
            return None

        # Try to find TOOL: and PARAMS:
        # Handle formats like "TOOL: list_sessions" or "TOOL: functions.list_sessions"
        tool_match = re.search(r'TOOL:\s*([\w.]+)', text, re.IGNORECASE)
        if not tool_match:
            return None

        tool_name = tool_match.group(1)
        # Strip "functions." prefix if present (common with OpenAI function calling format)
        if tool_name.startswith('functions.'):
            tool_name = tool_name[10:]  # len('functions.') = 10

        # Parse params
        params = {}
        params_match = re.search(r'PARAMS:\s*(\{[^}]*\})', text, re.IGNORECASE | re.DOTALL)
        if params_match:
            try:
                params = json.loads(params_match.group(1))
            except json.JSONDecodeError:
                pass

        return ToolCall(name=tool_name, params=params)

    def _get_default_tool_call(self, query: str) -> Optional[ToolCall]:
        """Get a default tool call based on query patterns."""
        query_lower = query.lower()

        # Thematic queries - use search
        for pattern in THEMATIC_PATTERNS:
            match = re.search(pattern, query_lower, re.IGNORECASE)
            if match:
                topic = match.group(1).strip() if match.lastindex else self._extract_likely_topic(query)
                return ToolCall(
                    name="search_sessions",
                    params={"query": topic},
                    reason="Thematic query"
                )

        # Structural queries - use list_sessions
        for pattern in STRUCTURAL_PATTERNS:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return ToolCall(
                    name="list_sessions",
                    params={},
                    reason="Structural query"
                )

        # Default: search with extracted topic
        topic = self._extract_likely_topic(query)
        return ToolCall(
            name="search_sessions",
            params={"query": topic},
            reason="Default search"
        )

    def _extract_likely_topic(self, query: str) -> str:
        """Extract the likely topic from a query for semantic search."""
        query_lower = query.lower()
        remove_phrases = [
            r'^what\s+(was|were|is|are)\s+',
            r'^how\s+(did|does|do|was|were)\s+',
            r'^which\s+',
            r'^tell\s+me\s+about\s+',
            r'^show\s+me\s+',
            r'^find\s+',
        ]

        topic = query_lower
        for pattern in remove_phrases:
            topic = re.sub(pattern, '', topic, flags=re.IGNORECASE)

        topic = re.sub(r'[?.!]+$', '', topic).strip()

        if len(topic) > 100:
            topic = topic[:100]

        return topic if topic else query[:50]

    def _synthesize_response(
        self,
        query: str,
        memory_context: str,
        evidence: List[Dict],
        steering: SteeringDirectives
    ) -> str:
        """Synthesize a scaffolded response from gathered evidence."""
        system_prompt = format_system_prompt(
            memory_context=memory_context,
            steering_instructions=steering.raw_instructions
        )

        evidence_str = self._format_evidence_for_synthesis(evidence)

        user_message = f"""Based on the evidence gathered, provide a scaffolded response to this query:

Query: {query}

Evidence:
{evidence_str}

Instructions:
1. Point to SPECIFIC evidence (exact quotes, speaker metrics)
2. Explain WHY the evidence is relevant
3. Use natural language ("You can see this in...", "Notice how...")
4. If evidence is incomplete, acknowledge what couldn't be determined
5. Suggest what the user might want to explore further

When interpreting speaker participation patterns:
- Low participation % + high question rate often indicates a facilitator/interviewer role
- Compare actual participation to equal share to assess dominance vs deference
- Consistent patterns across sessions suggest a stable role (host, facilitator, etc.)

Write a conversational response that guides the user through the evidence."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        try:
            response = self.llm.complete(
                messages=messages,
                temperature=0.4,
                max_tokens=3000
            )
            return response.content

        except Exception as e:
            logger.error(f"[Baseline Agent] Synthesis error: {e}")
            return self._fallback_response(query, evidence)

    def _format_evidence_for_context(self, evidence: List[Dict]) -> str:
        """Format evidence for decision-making context."""
        if not evidence:
            return ""

        DISCOVERY_TOOLS = {'list_sessions', 'search_sessions', 'get_speaker_profile'}

        lines = []
        for e in evidence[-MAX_EVIDENCE_ITEMS:]:
            if e.get("type") == "steering_block":
                lines.append(f"[BLOCKED] {e.get('tool')}: {e.get('reason')}")
            elif e.get("type") == "constraint_block":
                lines.append(f"[BLOCKED] {e.get('tool')}: {e.get('reason')}")
            else:
                tool = e.get("tool", "unknown")
                result = e.get("result", {})

                if result.get("error"):
                    lines.append(f"[{tool}] Error: {result.get('error')}")
                elif tool in DISCOVERY_TOOLS:
                    display = result.get("display", "")
                    if display:
                        display_lines = display.split("\n")
                        summary = " | ".join(line.strip() for line in display_lines if line.strip())
                        lines.append(f"[{tool}] {summary}")
                    else:
                        lines.append(f"[{tool}] Completed")
                else:
                    summary = self._build_detail_summary(tool, result)
                    lines.append(f"[{tool}] {summary}")

        return "\n".join(lines)

    def _build_detail_summary(self, tool: str, result: Dict) -> str:
        """Build a structured summary for detail tools."""
        discussion_id = result.get("discussion_id", "?")
        session_name = result.get("session_name", "")

        if session_name:
            title = f'Discussion {discussion_id} "{session_name}"'
        else:
            title = f'Discussion {discussion_id}'

        if tool == "get_transcript":
            utterance_count = result.get("utterance_count", 0)
            return f"{title}: {utterance_count} utterances"

        return f"{title}: Retrieved"

    def _format_evidence_for_synthesis(self, evidence: List[Dict]) -> str:
        """Format evidence for synthesis (detailed)."""
        if not evidence:
            return "No evidence gathered."

        sections = []

        for e in evidence:
            if e.get("type") == "steering_block":
                continue

            tool = e.get("tool", "unknown")
            result = e.get("result", {})

            if result.get("error"):
                sections.append(f"## {tool}\nError: {result.get('error')}")
                continue

            display = result.get("display", "")
            if display:
                sections.append(display)
            else:
                sections.append(f"## {tool}\n(No display content available)")

        return "\n\n".join(sections)

    def _extract_suggestions(self, answer: str, evidence: List[Dict]) -> List[str]:
        """Extract exploration suggestions from the answer."""
        suggestions = []

        # Look for suggestion patterns in the answer
        patterns = [
            r'you might (?:want to|also) (?:explore|check|look at|see)\s+(.+?)(?:\.|$)',
            r'consider (?:exploring|checking|looking at)\s+(.+?)(?:\.|$)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, answer, re.IGNORECASE)
            suggestions.extend(matches)

        return suggestions[:3]

    def _fallback_response(self, query: str, evidence: List[Dict]) -> str:
        """Generate a fallback response when synthesis fails."""
        if not evidence:
            return "I couldn't find relevant information for your query. Please try rephrasing or specifying a session."

        return f"I gathered evidence for your query but encountered an issue synthesizing it. Here's a summary of what I found:\n\n{self._format_evidence_for_synthesis(evidence)}"


# =============================================================================
# Module-level entry points
# =============================================================================

def run_agent(conversation_id: str, query: str) -> AgentResponse:
    """
    Run the agent for a single query.

    This is the main entry point for the routes.

    Args:
        conversation_id: Unique conversation identifier
        query: User's query

    Returns:
        AgentResponse with answer and metadata
    """
    agent = ScaffoldingAgent(conversation_id)
    return agent.respond(query)


def clear_conversation(conversation_id: str):
    """Clear conversation memory."""
    from .memory import clear_memory
    clear_memory(conversation_id)
