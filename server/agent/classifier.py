"""
Query Classifier

Determines query intent, complexity, and routing for the agent system.
"""

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum

import openai

logger = logging.getLogger(__name__)


class QueryIntent(str, Enum):
    """Types of user query intents."""
    FACTUAL = "factual"
    COMPARATIVE = "comparative"
    DIAGNOSTIC = "diagnostic"
    GENERATIVE = "generative"
    GRAPH_TRAVERSAL = "graph_traversal"


class QueryComplexity(str, Enum):
    """Query complexity levels."""
    SIMPLE = "simple"
    COMPLEX = "complex"


@dataclass
class ExtractedEntities:
    """Entities extracted from the query."""
    sessions: List[str] = field(default_factory=list)
    speakers: List[str] = field(default_factory=list)
    concepts: List[str] = field(default_factory=list)
    time_references: List[str] = field(default_factory=list)
    session_device_ids: List[int] = field(default_factory=list)  # Resolved IDs


@dataclass
class Classification:
    """Complete query classification result."""
    intent: QueryIntent
    complexity: QueryComplexity
    required_artifacts: List[str]
    suggested_tools: List[str]
    entities: ExtractedEntities
    reasoning: str
    confidence: float = 1.0

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "intent": self.intent.value,
            "complexity": self.complexity.value,
            "required_artifacts": self.required_artifacts,
            "suggested_tools": self.suggested_tools,
            "entities": {
                "sessions": self.entities.sessions,
                "speakers": self.entities.speakers,
                "concepts": self.entities.concepts,
                "time_references": self.entities.time_references,
                "session_device_ids": self.entities.session_device_ids
            },
            "reasoning": self.reasoning,
            "confidence": self.confidence
        }


class QueryClassifier:
    """
    Classifies user queries for routing and tool selection.

    Uses a combination of:
    1. Rule-based heuristics for common patterns
    2. LLM-based classification for complex cases
    """

    # Patterns for rule-based classification
    GRAPH_PATTERNS = [
        r'\brelat(ed|es|ion)',
        r'\bconnect(ed|s|ion)',
        r'\blink(ed|s)',
        r'\bpath\s+(between|from|to)',
        r'\bleads?\s+to',
        r'\bcause[sd]?',
        r'\bbuild(s|ing)?\s+on',
        r'\bneighbor',
        r'\badjacent',
    ]

    # Strong indicators - single match is enough
    GRAPH_STRONG_INDICATORS = [
        r'\bpath\s+between',
        r'\bconnected\s+to',
        r'\brelates?\s+to',
        r'\bleads?\s+to',
    ]

    COMPARATIVE_PATTERNS = [
        r'\bcompar(e|ing|ison)',
        r'\bdiff(er|erence)',
        r'\bvs\.?\b',
        r'\bversus\b',
        r'\bbetter\b',
        r'\bworse\b',
        r'\bmore\s+than',
        r'\bless\s+than',
        r'\bbetween\s+\w+\s+and\b',
        r'\b(group|session|team)\s+\w+\s+and\s+(group|session|team)\s+\w+',  # "Group A and Group B"
    ]

    # Strong comparative indicators - single match is enough
    COMPARATIVE_STRONG_INDICATORS = [
        r'\bcompare\s+.+\s+(with|to|and)\b',  # "compare X with Y"
        r'\b(how|what)\s+.*(differ|different)',  # "how did X differ"
    ]

    DIAGNOSTIC_PATTERNS = [
        r'\bwhy\b',
        r'\bwhat\s+went\s+wrong',
        r'\bproblem',
        r'\bissue',
        r'\bdiagnos',
        r'\banalyze\s+why',
        r'\bexplain\s+why',
    ]

    GENERATIVE_PATTERNS = [
        r'\bsuggest',
        r'\brecommend',
        r'\bimprove',
        r'\bsummar',
        r'\btakeaway',
        r'\binsight',
        r'\bwhat\s+could',
        r'\bhow\s+could',
    ]

    def __init__(self):
        """Initialize the classifier."""
        self._client = None
        self._session_name_cache = None  # Cache for session names → device IDs
        self._session_info_cache = None  # Cache for device ID → (session_name, device_name)
        self._load_prompt_template()

    @property
    def client(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            self._client = openai.OpenAI()
        return self._client

    def _load_prompt_template(self):
        """Load the classification prompt template."""
        prompt_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'prompts',
            'classification.txt'
        )
        try:
            with open(prompt_path, 'r') as f:
                self.prompt_template = f.read()
        except FileNotFoundError:
            logger.warning(f"Prompt template not found at {prompt_path}, using default")
            self.prompt_template = self._get_default_prompt()

    def _get_default_prompt(self) -> str:
        """Return a default prompt if file not found."""
        return """Classify this query about classroom discussion data.

Return JSON with:
- intent: factual|comparative|diagnostic|generative|graph_traversal
- complexity: simple|complex
- required_artifacts: list of [transcripts, concept_maps, seven_c, liwc, speakers]
- suggested_tools: list of tool names
- entities: {sessions: [], speakers: [], concepts: [], time_references: []}
- reasoning: brief explanation

Query: {query}
Context: {context}"""

    def classify(self, query: str, context: Optional[Dict] = None) -> Classification:
        """
        Classify a user query.

        Args:
            query: The user's question
            context: Optional conversation context

        Returns:
            Classification result
        """
        context = context or {}

        # Try rule-based classification first
        rule_result = self._rule_based_classify(query)
        if rule_result and rule_result.confidence >= 0.8:
            logger.debug(f"Rule-based classification: {rule_result.intent.value}")
            return rule_result

        # Fall back to LLM classification
        try:
            llm_result = self._llm_classify(query, context)
            return llm_result
        except Exception as e:
            logger.error(f"LLM classification failed: {e}")
            # Return rule-based result or default
            if rule_result:
                return rule_result
            return self._default_classification(query)

    def _rule_based_classify(self, query: str) -> Optional[Classification]:
        """
        Attempt rule-based classification using patterns.

        Returns Classification if confident, None otherwise.
        """
        query_lower = query.lower()

        # Check for strong graph indicators first (single match is enough)
        for pattern in self.GRAPH_STRONG_INDICATORS:
            if re.search(pattern, query_lower):
                return self._build_classification(
                    intent=QueryIntent.GRAPH_TRAVERSAL,
                    query=query,
                    confidence=0.9
                )

        # Check for graph traversal patterns (need 2+ matches)
        graph_matches = sum(
            1 for p in self.GRAPH_PATTERNS
            if re.search(p, query_lower)
        )
        if graph_matches >= 2:
            return self._build_classification(
                intent=QueryIntent.GRAPH_TRAVERSAL,
                query=query,
                confidence=0.85
            )

        # Check for strong comparative indicators first
        for pattern in self.COMPARATIVE_STRONG_INDICATORS:
            if re.search(pattern, query_lower):
                return self._build_classification(
                    intent=QueryIntent.COMPARATIVE,
                    query=query,
                    confidence=0.9
                )

        # Check for comparative patterns (need 2+ matches)
        comp_matches = sum(
            1 for p in self.COMPARATIVE_PATTERNS
            if re.search(p, query_lower)
        )
        if comp_matches >= 2:
            return self._build_classification(
                intent=QueryIntent.COMPARATIVE,
                query=query,
                confidence=0.85
            )

        # Check for diagnostic patterns
        diag_matches = sum(
            1 for p in self.DIAGNOSTIC_PATTERNS
            if re.search(p, query_lower)
        )
        if diag_matches >= 1:
            return self._build_classification(
                intent=QueryIntent.DIAGNOSTIC,
                query=query,
                confidence=0.75
            )

        # Check for generative patterns
        gen_matches = sum(
            1 for p in self.GENERATIVE_PATTERNS
            if re.search(p, query_lower)
        )
        if gen_matches >= 1:
            return self._build_classification(
                intent=QueryIntent.GENERATIVE,
                query=query,
                confidence=0.75
            )

        # Default to factual with lower confidence
        return self._build_classification(
            intent=QueryIntent.FACTUAL,
            query=query,
            confidence=0.5  # Low confidence triggers LLM fallback
        )

    def _build_classification(
        self,
        intent: QueryIntent,
        query: str,
        confidence: float
    ) -> Classification:
        """Build a Classification from intent and query."""
        # Extract entities
        entities = self._extract_entities(query)

        # Determine artifacts and tools based on intent
        artifacts, tools = self._get_artifacts_and_tools(intent, query)

        # Determine complexity
        complexity = self._assess_complexity(intent, entities, tools)

        return Classification(
            intent=intent,
            complexity=complexity,
            required_artifacts=artifacts,
            suggested_tools=tools,
            entities=entities,
            reasoning=f"Rule-based: {intent.value} query",
            confidence=confidence
        )

    def _get_session_name_map(self) -> Dict[str, int]:
        """Get mapping of session names to device IDs (cached)."""
        if self._session_name_cache is not None:
            return self._session_name_cache

        try:
            from app import db
            from tables.session import Session
            from tables.session_device import SessionDevice

            # Get all sessions with their device IDs and device names
            results = db.session.query(
                Session.name.label('session_name'),
                SessionDevice.id.label('device_id'),
                SessionDevice.name.label('device_name')
            ).join(
                SessionDevice, SessionDevice.session_id == Session.id
            ).all()

            # Build name → device_id map (lowercase keys for matching)
            self._session_name_cache = {}
            # Also build device_id → (session_name, device_name) map
            self._session_info_cache = {}

            for session_name, device_id, device_name in results:
                # Store session info by device ID
                self._session_info_cache[device_id] = {
                    'session_name': session_name,
                    'device_name': device_name,
                    'display_name': f"{session_name} ({device_name})" if device_name and device_name != session_name else session_name
                }

                if session_name:
                    # Store both lowercase and original for matching
                    self._session_name_cache[session_name.lower()] = device_id
                    # Also store without common words
                    simplified = session_name.lower().replace(' session', '').replace('the ', '')
                    if simplified != session_name.lower():
                        self._session_name_cache[simplified] = device_id

                # Also allow matching by device name
                if device_name and device_name.lower() != session_name.lower():
                    self._session_name_cache[device_name.lower()] = device_id
                    simplified_device = device_name.lower().replace(' interview', '').replace('the ', '')
                    if simplified_device != device_name.lower():
                        self._session_name_cache[simplified_device] = device_id

            logger.debug(f"Cached {len(self._session_name_cache)} session names, {len(self._session_info_cache)} session info entries")
            return self._session_name_cache
        except Exception as e:
            logger.error(f"Failed to load session names: {e}")
            return {}

    def get_session_display_info(self, device_id: int) -> Dict[str, str]:
        """
        Get display information for a session device.

        Returns:
            Dict with session_name, device_name, and display_name
        """
        # Ensure cache is populated
        self._get_session_name_map()

        if self._session_info_cache and device_id in self._session_info_cache:
            return self._session_info_cache[device_id]

        return {
            'session_name': f"Session {device_id}",
            'device_name': f"Device {device_id}",
            'display_name': f"Session {device_id}"
        }

    def _resolve_session_names(self, query: str) -> List[int]:
        """
        Find session names mentioned in query and resolve to device IDs.

        This enables queries like "Dinosaurs session" to find session 23.
        """
        session_map = self._get_session_name_map()
        if not session_map:
            return []

        resolved_ids = []
        query_lower = query.lower()

        # Sort by name length (longest first) to match "Country Music" before "Music"
        sorted_names = sorted(session_map.keys(), key=len, reverse=True)

        for name in sorted_names:
            if name in query_lower:
                device_id = session_map[name]
                if device_id not in resolved_ids:
                    resolved_ids.append(device_id)
                    logger.debug(f"Resolved session name '{name}' to device ID {device_id}")

        return resolved_ids

    def _extract_entities(self, query: str) -> ExtractedEntities:
        """Extract entities from query using patterns."""
        entities = ExtractedEntities()

        # Extract explicit session ID references first
        session_patterns = [
            r"session\s+(?:device\s+)?(?:id\s+)?(\d+)",  # "session 23", "session id 23", "session device id 23"
            r"(?:device\s+)?id\s+(\d+)",  # "device id 23", "id 23"
            r"group\s+([A-Za-z]+)(?:'s)?",
            r"today'?s?\s+(?:session|discussion)",
            r"yesterday'?s?\s+(?:session|discussion)",
            r"last\s+(?:session|discussion)",
        ]
        for pattern in session_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            # Deduplicate while preserving order
            for m in matches:
                if m and m not in entities.sessions:
                    entities.sessions.append(m)
                    # If it's a numeric ID, also add to session_device_ids
                    if m.isdigit():
                        session_id = int(m)
                        if session_id not in entities.session_device_ids:
                            entities.session_device_ids.append(session_id)

        # NEW: Resolve session names to IDs (e.g., "Dinosaurs" → 23)
        name_resolved_ids = self._resolve_session_names(query)
        for device_id in name_resolved_ids:
            if device_id not in entities.session_device_ids:
                entities.session_device_ids.append(device_id)
                logger.debug(f"Added name-resolved session device ID: {device_id}")

        # Extract speaker references
        speaker_patterns = [
            r"speaker\s+([A-Za-z]+)",
            r"student\s+([A-Za-z]+)",
            r"([A-Za-z]+)\s+said",
            r"what\s+did\s+([A-Za-z]+)\s+say",
        ]
        for pattern in speaker_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            entities.speakers.extend(matches)

        # Extract time references
        time_patterns = [
            r"(today|yesterday|last week|last month|this week)",
            r"(recent|latest|newest|oldest)",
            r"(\d+)\s+(days?|weeks?|months?)\s+ago",
        ]
        for pattern in time_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            if matches:
                if isinstance(matches[0], tuple):
                    entities.time_references.extend([' '.join(m) for m in matches])
                else:
                    entities.time_references.extend(matches)

        # Extract concepts (quoted or after "about")
        concept_patterns = [
            r'"([^"]+)"',  # Quoted text
            r"'([^']+)'",  # Single quoted
            r"about\s+(?:the\s+)?(\w+(?:\s+\w+){0,3})",  # "about X"
            r"concept\s+(?:of\s+)?(\w+(?:\s+\w+){0,2})",  # "concept of X"
        ]
        for pattern in concept_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            entities.concepts.extend(matches)

        return entities

    def _get_artifacts_and_tools(
        self,
        intent: QueryIntent,
        query: str
    ) -> tuple[List[str], List[str]]:
        """Determine required artifacts and suggested tools for an intent."""

        query_lower = query.lower()

        if intent == QueryIntent.GRAPH_TRAVERSAL:
            # Start with appropriate tools based on query
            if "path" in query_lower:
                tools = ["search_concept_nodes", "get_concept_path"]
            elif "caus" in query_lower or "lead" in query_lower:
                tools = ["search_concept_nodes", "get_causal_chain"]
            else:
                tools = ["search_concept_nodes", "get_node_neighbors"]
            return ["concept_maps"], tools

        elif intent == QueryIntent.COMPARATIVE:
            tools = ["compare_sessions"]
            artifacts = ["transcripts", "concept_maps", "seven_c"]
            if "speaker" in query_lower or "student" in query_lower:
                tools = ["compare_speakers"]
                artifacts = ["transcripts", "speakers"]
            return artifacts, tools

        elif intent == QueryIntent.DIAGNOSTIC:
            tools = ["get_7c_analysis", "search_transcript_chunks"]
            if "concept" in query_lower or "idea" in query_lower:
                tools.append("get_full_concept_map")
            return ["transcripts", "seven_c", "concept_maps"], tools

        elif intent == QueryIntent.GENERATIVE:
            tools = ["search_transcript_chunks", "get_7c_analysis"]
            return ["transcripts", "seven_c"], tools

        else:  # FACTUAL
            # Determine based on what's being asked about
            if any(x in query_lower for x in ["concept", "map", "idea", "graph"]):
                return ["concept_maps"], ["get_full_concept_map", "search_concept_nodes"]
            elif any(x in query_lower for x in ["7c", "seven c", "collaboration", "score"]):
                return ["seven_c"], ["get_7c_analysis"]
            elif any(x in query_lower for x in ["liwc", "emotion", "tone", "analytic"]):
                return ["liwc"], ["get_liwc_metrics"]
            elif any(x in query_lower for x in ["speaker", "student", "participant"]):
                return ["speakers", "transcripts"], ["search_speakers", "compare_speakers"]
            else:
                return ["transcripts"], ["search_transcript_chunks"]

    def _assess_complexity(
        self,
        intent: QueryIntent,
        entities: ExtractedEntities,
        tools: List[str]
    ) -> QueryComplexity:
        """Assess whether the query is simple or complex."""

        # Complex if comparing multiple sessions
        if len(entities.sessions) > 1:
            return QueryComplexity.COMPLEX

        # Complex if multiple speakers to analyze
        if len(entities.speakers) > 1:
            return QueryComplexity.COMPLEX

        # Complex intents
        if intent in [QueryIntent.COMPARATIVE, QueryIntent.DIAGNOSTIC]:
            return QueryComplexity.COMPLEX

        # Complex if many tools needed
        if len(tools) >= 3:
            return QueryComplexity.COMPLEX

        return QueryComplexity.SIMPLE

    def _llm_classify(self, query: str, context: Dict) -> Classification:
        """Use LLM for classification when rule-based is uncertain."""
        prompt = self.prompt_template.format(
            query=query,
            context=json.dumps(context) if context else "No prior context"
        )

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a query classifier. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)

        # Parse the result
        try:
            intent = QueryIntent(result.get("intent", "factual"))
        except ValueError:
            intent = QueryIntent.FACTUAL

        try:
            complexity = QueryComplexity(result.get("complexity", "simple"))
        except ValueError:
            complexity = QueryComplexity.SIMPLE

        entities_data = result.get("entities", {})
        entities = ExtractedEntities(
            sessions=entities_data.get("sessions", []),
            speakers=entities_data.get("speakers", []),
            concepts=entities_data.get("concepts", []),
            time_references=entities_data.get("time_references", [])
        )

        return Classification(
            intent=intent,
            complexity=complexity,
            required_artifacts=result.get("required_artifacts", ["transcripts"]),
            suggested_tools=result.get("suggested_tools", ["search_transcript_chunks"]),
            entities=entities,
            reasoning=result.get("reasoning", "LLM classification"),
            confidence=0.9
        )

    def _default_classification(self, query: str) -> Classification:
        """Return a safe default classification."""
        return Classification(
            intent=QueryIntent.FACTUAL,
            complexity=QueryComplexity.SIMPLE,
            required_artifacts=["transcripts"],
            suggested_tools=["search_transcript_chunks"],
            entities=self._extract_entities(query),
            reasoning="Default fallback classification",
            confidence=0.5
        )


class ReferenceResolver:
    """
    Resolves references in queries using conversation context.

    Handles:
    - "that session" → session from previous turn
    - "they" → speaker(s) mentioned previously
    - "those results" → artifacts from previous turn
    """

    def __init__(self, state_manager=None):
        """Initialize resolver with optional state manager."""
        self.state_manager = state_manager

    def resolve(self, query: str, conversation_id: str = None) -> tuple[str, Dict]:
        """
        Resolve references in query.

        Returns:
            Tuple of (resolved_query, resolution_info)
        """
        if not conversation_id or not self.state_manager:
            return query, {}

        state = self.state_manager.get_state(conversation_id)
        if not state:
            return query, {}

        resolved_query = query
        resolutions = {}
        query_lower = query.lower()

        # Multi-session references (for comparisons) - check first
        multi_session_refs = ['those sessions', 'these sessions', 'those four',
                              'those three', 'those two', 'all of them',
                              'both sessions', 'both of them', 'all four',
                              'all three', 'the sessions']
        for ref in multi_session_refs:
            compared = getattr(state, 'compared_sessions', [])
            if ref in query_lower and compared:
                session_list = ', '.join([f"session {s}" for s in compared])
                resolved_query = re.sub(
                    re.escape(ref),
                    session_list,
                    resolved_query,
                    flags=re.IGNORECASE
                )
                resolutions["sessions"] = compared
                break

        # Ordinal session references - "first session", "previous session"
        session_history = getattr(state, 'session_history', [])
        previous_session = getattr(state, 'previous_session_focus', None)

        ordinal_first = ['first session i asked', 'first session i mentioned',
                         'the first session', 'first one i mentioned']
        for ref in ordinal_first:
            if ref in query_lower and session_history:
                resolved_query = re.sub(
                    re.escape(ref),
                    f"session {session_history[0]}",
                    resolved_query,
                    flags=re.IGNORECASE
                )
                resolutions["session"] = session_history[0]
                break

        ordinal_prev = ['previous session', 'go back', 'the earlier session',
                        'back to the first', 'the other session']
        for ref in ordinal_prev:
            if ref in query_lower and previous_session:
                resolved_query = re.sub(
                    re.escape(ref),
                    f"session {previous_session}",
                    resolved_query,
                    flags=re.IGNORECASE
                )
                resolutions["session"] = previous_session
                break

        # Standard session references
        session_refs = [
            "that session", "the session", "this session",
            "the discussion", "that discussion"
        ]
        for ref in session_refs:
            if ref in query_lower and state.current_session_focus and "session" not in resolutions:
                resolved_query = re.sub(
                    re.escape(ref),
                    f"session {state.current_session_focus}",
                    resolved_query,
                    flags=re.IGNORECASE
                )
                resolutions["session"] = state.current_session_focus

        # Resolve speaker references
        speaker_refs = ["they", "the speaker", "that student", "the student", "that speaker"]
        for ref in speaker_refs:
            if ref in query_lower and state.current_speaker_focus:
                resolved_query = re.sub(
                    re.escape(ref),
                    f"speaker {state.current_speaker_focus}",
                    resolved_query,
                    flags=re.IGNORECASE
                )
                resolutions["speaker"] = state.current_speaker_focus

        return resolved_query, resolutions
