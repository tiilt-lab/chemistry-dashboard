# server/query_understanding.py - LLM-Powered Query Understanding for Ultra RAG
"""
Query Understanding Layer: Analyzes user queries BEFORE retrieval to determine:
1. Query intent (find, compare, analyze, explain)
2. Required metrics (debate_score, 7C scores, evolution)
3. Retrieval strategy (metric_filter, semantic, contrastive, hybrid)
4. Reasoning steps for complex queries
"""

import json
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Literal
from openai import OpenAI

logger = logging.getLogger(__name__)


@dataclass
class QueryPlan:
    """Structured plan for executing a query"""
    intent: Literal['find', 'compare', 'analyze', 'explain', 'describe']
    focus_area: Literal['argumentation', 'collaboration', 'speaker', 'evolution', 'topic', 'general']
    metrics_needed: List[str] = field(default_factory=list)
    metric_filters: Dict[str, tuple] = field(default_factory=dict)  # e.g., {'debate_score': ('>=', 3)}
    retrieval_strategy: Literal['metric_first', 'semantic', 'contrastive', 'hybrid'] = 'semantic'
    needs_contrastive: bool = False  # For "why" queries needing high/low comparison
    reasoning_steps: List[Dict] = field(default_factory=list)
    target_speaker: Optional[str] = None
    target_sessions: List[int] = field(default_factory=list)
    # New fields for artifact-grounded RAG
    primary_artifacts: List[str] = field(default_factory=list)  # ['concept_map', '7c', 'transcripts', 'speakers', 'evolution']
    needs_transcript: bool = True  # Whether to include raw transcript for ENRICH layer
    grounding_strategy: str = ""  # How to ground response in artifacts
    cross_session: bool = False  # Whether query needs cross-session analysis


class QueryUnderstanding:
    """
    Analyzes queries to create execution plans.
    Uses GPT for complex queries, fast heuristics for simple ones.
    """

    def __init__(self):
        self.client = OpenAI()

        # Metric keywords mapping
        self.metric_keywords = {
            'argumentation': {
                'keywords': ['argumentation', 'debate', 'argument', 'challenge', 'disagree', 'counter', 'reasoning'],
                'metrics': ['debate_score', 'challenge_count', 'reasoning_depth'],
                'filters': {'debate_score': ('>=', 2)}
            },
            'collaboration': {
                'keywords': ['collaboration', 'teamwork', 'communication', 'quality', '7c', 'productive'],
                'metrics': ['communication_score', 'climate_score', 'contribution_score'],
                'filters': {'communication_score': ('>=', 70)}
            },
            'evolution': {
                'keywords': ['evolution', 'evolved', 'changed', 'improved', 'grew', 'over time', 'progress'],
                'metrics': ['analytic_evolution', 'tone_evolution', 'certainty_evolution'],
                'filters': {}
            },
            'questioning': {
                'keywords': ['question', 'asking', 'inquiry', 'curious'],
                'metrics': ['question_count', 'question_ratio'],
                'filters': {'question_ratio': ('>=', 0.1)}
            },
            'speaker': {
                'keywords': ['speaker', 'engage', 'engagement', 'style', 'typically', 'usually'],
                'metrics': ['avg_clout', 'question_count', 'session_count'],
                'filters': {}
            }
        }

        # Intent patterns
        self.intent_patterns = {
            'compare': ['compare', 'versus', 'vs', 'difference', 'contrast', 'between'],
            'explain': ['why', 'how does', 'what causes', 'what leads', 'reason for', 'explain'],
            'analyze': ['analyze', 'what patterns', 'what makes', 'understand', 'insights'],
            'find': ['find', 'show', 'list', 'get', 'search', 'which', 'sessions with'],
            'describe': ['describe', 'tell me about', 'what is', 'how is']
        }

    def analyze(self, query: str) -> QueryPlan:
        """
        Analyze query and create execution plan.
        Uses fast heuristics first, LLM for complex cases.
        """
        query_lower = query.lower()

        # Step 1: Detect intent
        intent = self._detect_intent(query_lower)

        # Step 2: Detect focus area and metrics
        focus_area, metrics_needed, metric_filters = self._detect_focus(query_lower)

        # Step 3: Determine retrieval strategy
        retrieval_strategy = self._determine_strategy(intent, focus_area, query_lower)

        # Step 4: Check if contrastive retrieval needed
        needs_contrastive = self._needs_contrastive(intent, query_lower)

        # Step 5: Extract speaker if mentioned
        target_speaker = self._extract_speaker(query_lower)

        # Step 6: Build reasoning steps for complex queries
        reasoning_steps = self._build_reasoning_steps(intent, focus_area, needs_contrastive)

        plan = QueryPlan(
            intent=intent,
            focus_area=focus_area,
            metrics_needed=metrics_needed,
            metric_filters=metric_filters,
            retrieval_strategy=retrieval_strategy,
            needs_contrastive=needs_contrastive,
            reasoning_steps=reasoning_steps,
            target_speaker=target_speaker
        )

        logger.info(f"Query plan: intent={intent}, focus={focus_area}, strategy={retrieval_strategy}, contrastive={needs_contrastive}")

        return plan

    def _detect_intent(self, query: str) -> str:
        """Detect query intent from patterns"""
        for intent, patterns in self.intent_patterns.items():
            if any(p in query for p in patterns):
                return intent
        return 'find'  # Default

    def _detect_focus(self, query: str) -> tuple:
        """Detect focus area and required metrics"""
        for focus, config in self.metric_keywords.items():
            if any(kw in query for kw in config['keywords']):
                return focus, config['metrics'], config.get('filters', {})

        # Default to general topic search
        return 'topic', [], {}

    def _determine_strategy(self, intent: str, focus: str, query: str) -> str:
        """Determine optimal retrieval strategy"""
        # Metric-first for quality/structure queries
        if focus in ['argumentation', 'collaboration', 'questioning']:
            return 'metric_first'

        # Contrastive for explanatory queries
        if intent == 'explain':
            return 'contrastive'

        # Hybrid for complex analytical queries
        if intent == 'analyze':
            return 'hybrid'

        # Semantic for topic/content queries
        return 'semantic'

    def _needs_contrastive(self, intent: str, query: str) -> bool:
        """Check if query needs high/low comparison"""
        contrastive_indicators = [
            'why', 'what makes', 'difference', 'succeed', 'fail',
            'better', 'worse', 'effective', 'ineffective'
        ]
        return intent == 'explain' or any(ind in query for ind in contrastive_indicators)

    def _extract_speaker(self, query: str) -> Optional[str]:
        """Extract speaker name if mentioned"""
        # This would ideally check against known speakers
        # For now, look for common patterns
        import re
        patterns = [
            r"how does (\w+) engage",
            r"how did (\w+) engage",
            r"(\w+)'s? (?:speaker |engagement |speaking )?style",
            r"what is (\w+) speaker style",
            r"tell me about (\w+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return match.group(1).capitalize()
        return None

    def _build_reasoning_steps(self, intent: str, focus: str, needs_contrastive: bool) -> List[Dict]:
        """Build chain-of-thought reasoning steps for complex queries"""
        steps = []

        if intent == 'explain' and needs_contrastive:
            # Contrastive reasoning for "why" queries
            steps = [
                {'step': 1, 'type': 'retrieve', 'action': 'get_high_metric_sessions', 'description': f'Find sessions with HIGH {focus} metrics'},
                {'step': 2, 'type': 'retrieve', 'action': 'get_low_metric_sessions', 'description': f'Find sessions with LOW {focus} metrics'},
                {'step': 3, 'type': 'context', 'action': 'build_contrastive_context', 'description': 'Build rich context for both groups'},
                {'step': 4, 'type': 'compare', 'action': 'extract_differences', 'description': 'Identify differentiating patterns'},
                {'step': 5, 'type': 'synthesize', 'action': 'generate_explanation', 'description': 'Synthesize explanation with evidence'}
            ]
        elif intent == 'analyze':
            # Analytical reasoning
            steps = [
                {'step': 1, 'type': 'retrieve', 'action': 'get_relevant_sessions', 'description': 'Find sessions matching query'},
                {'step': 2, 'type': 'context', 'action': 'build_full_context', 'description': 'Build rich context with all relevant data'},
                {'step': 3, 'type': 'analyze', 'action': 'pattern_extraction', 'description': 'Extract patterns from data'},
                {'step': 4, 'type': 'synthesize', 'action': 'generate_insights', 'description': 'Generate evidence-based insights'}
            ]
        elif focus == 'speaker':
            # Speaker-focused reasoning
            steps = [
                {'step': 1, 'type': 'retrieve', 'action': 'get_speaker_profile', 'description': 'Get speaker cross-session profile'},
                {'step': 2, 'type': 'retrieve', 'action': 'get_speaker_moments', 'description': 'Get key moments/quotes from speaker'},
                {'step': 3, 'type': 'context', 'action': 'build_speaker_context', 'description': 'Build rich speaker context'},
                {'step': 4, 'type': 'synthesize', 'action': 'generate_speaker_analysis', 'description': 'Generate speaker characterization'}
            ]
        else:
            # Simple find/retrieve
            steps = [
                {'step': 1, 'type': 'retrieve', 'action': 'search_sessions', 'description': 'Search for matching sessions'},
                {'step': 2, 'type': 'context', 'action': 'build_context', 'description': 'Build context for results'},
                {'step': 3, 'type': 'synthesize', 'action': 'generate_summary', 'description': 'Generate summary'}
            ]

        return steps

    def analyze_with_llm(self, query: str) -> QueryPlan:
        """
        Use LLM for complex query understanding.
        Falls back to heuristics if LLM fails.
        """
        try:
            prompt = f"""Analyze this discussion analytics query and extract a structured plan.

Query: "{query}"

Available metrics:
- Argumentation: debate_score, challenge_count, reasoning_depth, builds_on_count
- Collaboration: communication_score, climate_score, contribution_score, conflict_score
- Evolution: analytic_evolution, tone_evolution, certainty_evolution
- Speaker: avg_clout, question_count, session_count

Return JSON with:
{{
    "intent": "find|compare|analyze|explain|describe",
    "focus_area": "argumentation|collaboration|speaker|evolution|topic|general",
    "metrics_needed": ["metric1", "metric2"],
    "metric_filters": {{"metric_name": ["operator", value]}},  // e.g., {{"debate_score": [">=", 3]}}
    "needs_contrastive": true/false,  // true if query needs high/low comparison
    "target_speaker": "SpeakerName" or null
}}"""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You analyze queries for a discussion analytics system. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)

            # Convert metric_filters format
            metric_filters = {}
            for metric, filter_val in result.get('metric_filters', {}).items():
                if isinstance(filter_val, list) and len(filter_val) == 2:
                    metric_filters[metric] = tuple(filter_val)

            # Build reasoning steps based on LLM analysis
            reasoning_steps = self._build_reasoning_steps(
                result.get('intent', 'find'),
                result.get('focus_area', 'general'),
                result.get('needs_contrastive', False)
            )

            return QueryPlan(
                intent=result.get('intent', 'find'),
                focus_area=result.get('focus_area', 'general'),
                metrics_needed=result.get('metrics_needed', []),
                metric_filters=metric_filters,
                retrieval_strategy=self._determine_strategy(
                    result.get('intent', 'find'),
                    result.get('focus_area', 'general'),
                    query.lower()
                ),
                needs_contrastive=result.get('needs_contrastive', False),
                reasoning_steps=reasoning_steps,
                target_speaker=result.get('target_speaker')
            )

        except Exception as e:
            logger.warning(f"LLM query analysis failed: {e}, falling back to heuristics")
            return self.analyze(query)

    def analyze_with_artifacts(self, query: str) -> QueryPlan:
        """
        Use LLM with artifact-awareness for smart query understanding.
        The LLM knows about our knowledge structure (concept maps, 7C, etc.)
        and can make intelligent decisions about what to retrieve.
        """
        ARTIFACT_AWARE_PROMPT = """You analyze queries about discussion sessions for an educational analytics system.

AVAILABLE KNOWLEDGE (what users see in the UI):

1. TRANSCRIPTS: Raw conversation with speaker attribution, timestamps
   - Users see: Scrollable transcript with speaker colors
   - Contains: Who said what, when, exact quotes

2. CONCEPT MAPS: Extracted discussion structure (LLM-generated)
   - Nodes: ideas, questions, problems, solutions, hypotheses, evidence, challenges
   - Edges: supports, challenges, builds_on, elaborates, synthesizes, contradicts
   - Users see: Interactive graph visualization showing how ideas connect
   - Metrics: challenge_count, support_count, debate_score, node_count, edge_count

3. 7C COLLABORATION ANALYSIS: Quality scores (0-100) with evidence quotes
   - communication: clarity, listening, information flow
   - climate: psychological safety, comfort sharing ideas
   - contribution: balanced participation equity
   - conflict: constructive disagreement handling
   - constructive: productive collaboration toward goals
   - Users see: Bar charts with scores, evidence quotes for each dimension

4. SPEAKER PROFILES: Cross-session aggregations per speaker
   - avg_clout, avg_analytic, question_ratio, total_contributions
   - Users see: Speaker cards with statistics and sample quotes

5. TEMPORAL EVOLUTION: How discussion changed over time
   - analytic_evolution, tone_evolution, certainty_evolution
   - Users see: First half vs second half comparison

User Query: "{query}"

Analyze this query and determine:
1. What is the user trying to understand? (intent)
2. Which artifacts are most relevant to answer this?
3. What specific data should be retrieved?
4. Does this need cross-session comparison?
5. How should the response reference these artifacts?

Return JSON:
{{
    "intent": "find|explain|compare|analyze|describe",
    "focus_area": "argumentation|collaboration|speaker|evolution|topic|general",
    "primary_artifacts": ["concept_map", "7c", "transcripts", "speakers", "evolution"],
    "metrics_needed": ["metric1", "metric2"],
    "metric_filters": {{}},
    "needs_transcript": true,
    "cross_session": false,
    "needs_contrastive": false,
    "target_speaker": null,
    "grounding_strategy": "Describe how the response should reference artifacts"
}}

Guidelines:
- For "why" questions: usually need concept_map (to see relationships) + transcripts (for quotes)
- For collaboration quality: need 7c scores + evidence quotes
- For speaker analysis: need speakers profile + transcripts for examples
- For comparisons: need multiple sessions' artifacts
- Almost always include transcripts for the ENRICH layer (adding depth with quotes)
- grounding_strategy should explain HOW to cite artifacts (e.g., "Reference specific challenge edges from concept map, cite 7C scores")"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert at understanding user queries for a discussion analytics system. Return only valid JSON."},
                    {"role": "user", "content": ARTIFACT_AWARE_PROMPT.format(query=query)}
                ],
                temperature=0,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)

            # Convert metric_filters format if present
            metric_filters = {}
            for metric, filter_val in result.get('metric_filters', {}).items():
                if isinstance(filter_val, list) and len(filter_val) == 2:
                    metric_filters[metric] = tuple(filter_val)

            # Build reasoning steps based on analysis
            reasoning_steps = self._build_reasoning_steps(
                result.get('intent', 'find'),
                result.get('focus_area', 'general'),
                result.get('needs_contrastive', False)
            )

            plan = QueryPlan(
                intent=result.get('intent', 'find'),
                focus_area=result.get('focus_area', 'general'),
                metrics_needed=result.get('metrics_needed', []),
                metric_filters=metric_filters,
                retrieval_strategy=self._determine_strategy(
                    result.get('intent', 'find'),
                    result.get('focus_area', 'general'),
                    query.lower()
                ),
                needs_contrastive=result.get('needs_contrastive', False),
                reasoning_steps=reasoning_steps,
                target_speaker=result.get('target_speaker'),
                # New artifact-aware fields
                primary_artifacts=result.get('primary_artifacts', ['transcripts']),
                needs_transcript=result.get('needs_transcript', True),
                grounding_strategy=result.get('grounding_strategy', ''),
                cross_session=result.get('cross_session', False)
            )

            logger.info(f"Artifact-aware plan: intent={plan.intent}, artifacts={plan.primary_artifacts}, grounding={plan.grounding_strategy[:50]}...")
            return plan

        except Exception as e:
            logger.warning(f"Artifact-aware analysis failed: {e}, falling back to heuristics")
            # Fall back to basic analysis and add default artifacts
            plan = self.analyze(query)
            plan.primary_artifacts = self._infer_artifacts(plan)
            plan.needs_transcript = True
            plan.grounding_strategy = self._default_grounding_strategy(plan)
            return plan

    def _infer_artifacts(self, plan: QueryPlan) -> List[str]:
        """Infer which artifacts are relevant based on focus area."""
        artifact_map = {
            'argumentation': ['concept_map', 'transcripts'],
            'collaboration': ['7c', 'transcripts'],
            'speaker': ['speakers', 'transcripts'],
            'evolution': ['evolution', 'transcripts'],
            'topic': ['transcripts'],
            'general': ['concept_map', '7c', 'transcripts']
        }
        return artifact_map.get(plan.focus_area, ['transcripts'])

    def _default_grounding_strategy(self, plan: QueryPlan) -> str:
        """Generate default grounding strategy based on focus area."""
        strategies = {
            'argumentation': "Reference specific edges from the concept map (challenges, builds_on). Cite debate_score and challenge_count.",
            'collaboration': "Cite specific 7C scores (communication, climate, etc.) and reference evidence quotes from the analysis.",
            'speaker': "Reference speaker profile statistics (avg_clout, question_ratio) and include example quotes.",
            'evolution': "Compare first-half vs second-half metrics. Note specific evolution values.",
            'topic': "Ground in transcript quotes that discuss the topic.",
            'general': "Reference both concept map structure and 7C scores as relevant."
        }
        return strategies.get(plan.focus_area, "Reference relevant artifacts and include transcript quotes.")
