"""
Meta-Intent Classifier

Classifies queries before they reach the main agent system.
Detects small talk, out-of-scope, help requests, and ambiguous queries.
"""

import logging
import re
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


class MetaIntent(str, Enum):
    """High-level intent categories."""
    IN_SCOPE_CLEAR = "in_scope_clear"           # Normal agent query
    IN_SCOPE_AMBIGUOUS = "in_scope_ambiguous"   # Needs clarification
    SMALL_TALK = "small_talk"                   # Greetings, thanks, etc.
    OUT_OF_SCOPE = "out_of_scope"               # Not about discussions
    HELP_REQUEST = "help_request"               # User wants to know capabilities
    CLARIFICATION_RESPONSE = "clarification_response"  # Response to our question


@dataclass
class MetaClassification:
    """Result of meta-intent classification."""
    intent: MetaIntent
    confidence: float
    suggested_response: Optional[str] = None
    clarification_needed: Optional[str] = None
    original_query: str = ""
    detected_patterns: List[str] = None

    def __post_init__(self):
        if self.detected_patterns is None:
            self.detected_patterns = []

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "intent": self.intent.value,
            "confidence": self.confidence,
            "suggested_response": self.suggested_response,
            "clarification_needed": self.clarification_needed,
            "original_query": self.original_query,
            "detected_patterns": self.detected_patterns
        }


class MetaIntentClassifier:
    """
    Fast classifier for meta-intents.

    Filters queries before they reach the main agent system to handle:
    - Small talk (greetings, thanks, goodbyes)
    - Help requests (what can you do?)
    - Out-of-scope queries (weather, math, etc.)
    - Ambiguous queries that need clarification
    """

    # Small talk patterns (greetings, thanks, etc.)
    SMALL_TALK_PATTERNS = [
        (r'^(hi|hello|hey|greetings|good\s*(morning|afternoon|evening))[\s!.,?]*$', 'greeting'),
        (r'^(thanks|thank\s*you|thx|ty)[\s!.,]*', 'thanks'),
        (r'^(bye|goodbye|see\s*you|cya)[\s!.,]*$', 'goodbye'),
        (r'^how\s*are\s*you[\s?]*$', 'how_are_you'),
        (r'^what\'?s\s*up[\s?]*$', 'whats_up'),
        (r'^(ok|okay|sure|got\s*it|understood|i\s*see|alright)[\s!.,]*$', 'acknowledgment'),
        (r'^(yes|no|yeah|nope|yep|nah)[\s!.,]*$', 'yes_no'),
        (r'^(cool|nice|great|awesome|perfect)[\s!.,]*$', 'positive_feedback'),
    ]

    # Help request patterns
    HELP_PATTERNS = [
        (r'(what\s*can\s*you\s*do|what\s*are\s*your\s*capabilities)', 'capabilities'),
        (r'(how\s*do\s*i\s*use|how\s*does\s*this\s*work)', 'how_to_use'),
        (r'(what\s*kind\s*of\s*questions|what\s*should\s*i\s*ask)', 'what_to_ask'),
        (r'(show\s*me\s*(examples?|what\s*you\s*can\s*do))', 'show_examples'),
        (r'^help[\s!.,?]*$', 'help'),
        (r'(what\s*is\s*this|what\s*are\s*you)', 'what_is_this'),
    ]

    # Out-of-scope patterns (not about discussions)
    OUT_OF_SCOPE_PATTERNS = [
        (r'\b(weather|temperature|forecast|rain|sunny)\b', 'weather'),
        (r'\b(stock|market|price|crypto|bitcoin|invest)\b', 'finance'),
        (r'\b(recipe|cook|food|restaurant|eat)\b', 'food'),
        (r'\b(movie|film|tv\s*show|netflix|watch)\b', 'entertainment'),
        (r'\b(sports?|game|score|team|football|basketball)\b', 'sports'),
        (r'\b(news|politics|election|president|government)\b', 'news'),
        (r'^\s*\d+\s*[\+\-\*\/\^]\s*\d+', 'math_calculation'),
        (r'\b(calculate|solve|equation|formula)\b', 'math'),
        (r'\b(translate|translation|spanish|french|german)\b', 'translation'),
        (r'\b(joke|funny|humor|laugh)\b', 'humor'),
        (r'\b(capital\s*of|population\s*of|where\s*is\s+(?!session|discussion))', 'geography'),
        (r'\b(code|program|python|javascript|html|css)\b(?!.*\b(discuss|session|transcript)\b)', 'programming'),
        (r'\b(write\s*(me\s*)?(a|an|the)\s*(poem|story|essay|email))\b', 'creative_writing'),
    ]

    # In-scope indicators (discussion-related)
    IN_SCOPE_INDICATORS = [
        (r'\b(session|sessions?)\b', 'session'),
        (r'\b(discussion|discussions?|dialogue)\b', 'discussion'),
        (r'\b(transcript|transcripts?)\b', 'transcript'),
        (r'\b(conversation|conversations?)\b', 'conversation'),
        (r'\b(student|students?|learner)\b', 'student'),
        (r'\b(speaker|speakers?|participant)\b', 'speaker'),
        (r'\b(concept|concepts?|idea|ideas?)\b', 'concept'),
        (r'\b(question|questions?|hypothesis)\b', 'question'),
        (r'\b(7c|seven\s*c|collaboration|communication|conflict)\b', 'seven_c'),
        (r'\b(analysis|analyze|compare|comparison)\b', 'analysis'),
        (r'\b(said|mentioned|discussed|talked|spoke)\b', 'speech_verb'),
        (r'\b(topic|topics?|theme|themes?)\b', 'topic'),
        (r'\b(cluster|clusters?|group)\b', 'cluster'),
        (r'\b(engagement|participation|contribution)\b', 'participation'),
        (r'\b(liwc|metric|score)\b', 'metric'),
        (r'\b(today|yesterday|recent|last)\s*(session|discussion|class)\b', 'temporal_session'),
    ]

    # Very short/vague queries that need clarification
    VAGUE_QUERY_PATTERNS = [
        (r'^(tell\s*me|show\s*me|what)\s*$', 'incomplete'),
        (r'^(about|the|a|an)\s*$', 'incomplete'),
        (r'^[a-z]+\??$', 'single_word'),  # Single word queries
    ]

    def __init__(self):
        """Initialize the classifier with compiled patterns."""
        # Compile all patterns for efficiency
        self._small_talk = [(re.compile(p, re.IGNORECASE), name) for p, name in self.SMALL_TALK_PATTERNS]
        self._help = [(re.compile(p, re.IGNORECASE), name) for p, name in self.HELP_PATTERNS]
        self._out_of_scope = [(re.compile(p, re.IGNORECASE), name) for p, name in self.OUT_OF_SCOPE_PATTERNS]
        self._in_scope = [(re.compile(p, re.IGNORECASE), name) for p, name in self.IN_SCOPE_INDICATORS]
        self._vague = [(re.compile(p, re.IGNORECASE), name) for p, name in self.VAGUE_QUERY_PATTERNS]

    def classify(
        self,
        query: str,
        conversation_state: Optional[Dict] = None
    ) -> MetaClassification:
        """
        Classify a query's meta-intent.

        Args:
            query: User's input
            conversation_state: Optional state with pending_clarification

        Returns:
            MetaClassification with intent and suggested response
        """
        query_clean = query.strip()
        query_lower = query_clean.lower()

        logger.debug(f"Meta-classifying query: '{query_clean}'")

        # Check if this is a response to our clarification question
        if conversation_state and conversation_state.get('pending_clarification'):
            logger.debug("Detected clarification response")
            return MetaClassification(
                intent=MetaIntent.CLARIFICATION_RESPONSE,
                confidence=0.9,
                original_query=query_clean
            )

        # Check for empty or whitespace-only
        if not query_clean:
            return MetaClassification(
                intent=MetaIntent.IN_SCOPE_AMBIGUOUS,
                confidence=1.0,
                clarification_needed="I didn't receive a question. What would you like to know about your discussions?",
                original_query=query_clean
            )

        # Check small talk (exact/near-exact matches)
        for pattern, name in self._small_talk:
            if pattern.match(query_lower):
                logger.debug(f"Matched small talk pattern: {name}")
                return self._handle_small_talk(query_lower, name)

        # Check help requests
        for pattern, name in self._help:
            if pattern.search(query_lower):
                logger.debug(f"Matched help pattern: {name}")
                return MetaClassification(
                    intent=MetaIntent.HELP_REQUEST,
                    confidence=0.95,
                    suggested_response=self._get_help_response(),
                    original_query=query_clean,
                    detected_patterns=[name]
                )

        # Count in-scope and out-of-scope indicators
        out_of_scope_matches = []
        in_scope_matches = []

        for pattern, name in self._out_of_scope:
            if pattern.search(query_lower):
                out_of_scope_matches.append(name)

        for pattern, name in self._in_scope:
            if pattern.search(query_lower):
                in_scope_matches.append(name)

        logger.debug(f"In-scope matches: {in_scope_matches}, Out-of-scope matches: {out_of_scope_matches}")

        # If clearly out of scope and no in-scope indicators
        if out_of_scope_matches and not in_scope_matches:
            logger.debug(f"Query is out of scope: {out_of_scope_matches}")
            return MetaClassification(
                intent=MetaIntent.OUT_OF_SCOPE,
                confidence=0.85,
                suggested_response=self._get_out_of_scope_response(query_clean),
                original_query=query_clean,
                detected_patterns=out_of_scope_matches
            )

        # Check for very vague queries
        for pattern, name in self._vague:
            if pattern.match(query_lower):
                if not in_scope_matches:  # Only if no clear context
                    logger.debug(f"Query is too vague: {name}")
                    return MetaClassification(
                        intent=MetaIntent.IN_SCOPE_AMBIGUOUS,
                        confidence=0.7,
                        clarification_needed="Could you tell me more about what you'd like to know? "
                                            "For example, are you asking about a specific session, speaker, or topic?",
                        original_query=query_clean,
                        detected_patterns=[name]
                    )

        # Check if query is too short without context
        word_count = len(query_clean.split())
        if word_count <= 2 and not in_scope_matches:
            logger.debug(f"Query too short ({word_count} words) without context")
            return MetaClassification(
                intent=MetaIntent.IN_SCOPE_AMBIGUOUS,
                confidence=0.7,
                clarification_needed="Could you tell me more about what you'd like to know? "
                                    "For example, are you asking about a specific session, speaker, or topic?",
                original_query=query_clean,
                detected_patterns=['short_query']
            )

        # Default: in-scope and clear enough to process
        confidence = 0.9 if in_scope_matches else 0.75
        logger.debug(f"Query is in-scope (confidence: {confidence})")
        return MetaClassification(
            intent=MetaIntent.IN_SCOPE_CLEAR,
            confidence=confidence,
            original_query=query_clean,
            detected_patterns=in_scope_matches
        )

    def _handle_small_talk(self, query: str, pattern_name: str) -> MetaClassification:
        """Generate appropriate small talk response."""
        if pattern_name == 'greeting':
            response = ("Hello! I'm your Discussion Analysis Assistant. "
                       "I can help you explore classroom transcripts, concept maps, "
                       "collaboration metrics, and speaker patterns.\n\n"
                       "What would you like to know about your discussions?")
        elif pattern_name == 'thanks':
            response = ("You're welcome! Let me know if you have more questions "
                       "about your discussions.")
        elif pattern_name == 'goodbye':
            response = "Goodbye! Feel free to return anytime to explore your discussions."
        elif pattern_name == 'how_are_you':
            response = ("I'm ready to help you analyze your classroom discussions! "
                       "What would you like to explore?")
        elif pattern_name == 'whats_up':
            response = ("I'm here to help you explore your discussion data! "
                       "You can ask me about transcripts, concept maps, collaboration scores, or speakers.")
        elif pattern_name in ('acknowledgment', 'yes_no'):
            response = ("Got it! Is there anything specific about your discussions "
                       "you'd like to explore?")
        elif pattern_name == 'positive_feedback':
            response = ("Glad I could help! What else would you like to know "
                       "about your discussions?")
        else:
            response = ("I'm here to help you analyze classroom discussions. "
                       "What would you like to know?")

        return MetaClassification(
            intent=MetaIntent.SMALL_TALK,
            confidence=0.95,
            suggested_response=response,
            original_query=query,
            detected_patterns=[pattern_name]
        )

    def _get_help_response(self) -> str:
        """Generate capabilities overview."""
        return """I'm your Discussion Analysis Assistant. Here's what I can help with:

**Transcript Analysis**
- "What did students discuss about [topic]?"
- "Who mentioned [concept]?"
- "Find discussions about [subject]"

**Concept Maps**
- "What concepts are related to [idea]?"
- "Show me the main themes from today's session"
- "What questions did students raise?"

**Collaboration Quality (7C Analysis)**
- "How was the collaboration in session X?"
- "Which sessions had high communication quality?"
- "Compare conflict resolution between groups"

**Speaker Analysis**
- "How does [name] engage in discussions?"
- "Who contributed most to the ideas?"
- "Compare participation between speakers"

**Comparisons**
- "Compare session A and session B"
- "How did discussions evolve over time?"

Just ask a question to get started!"""

    def _get_out_of_scope_response(self, query: str) -> str:
        """Generate polite out-of-scope response."""
        return (f"I'm specialized in analyzing classroom discussions, so I can't help with that particular question. "
                f"However, I can help you:\n\n"
                f"- Analyze what students said about specific topics\n"
                f"- Explore concept maps and idea relationships\n"
                f"- Check collaboration quality (7C scores)\n"
                f"- Compare different discussion sessions\n"
                f"- Examine speaker participation patterns\n\n"
                f"What would you like to know about your discussions?")

    def get_starter_suggestions(self) -> List[str]:
        """Get starter suggestions for new conversations."""
        return [
            "What was discussed recently?",
            "Show me collaboration scores",
            "Who were the most active speakers?",
            "What concepts emerged from the discussions?"
        ]
