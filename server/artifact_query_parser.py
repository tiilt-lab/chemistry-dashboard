"""
Artifact-Aware Query Parser for Artifact-Grounded RAG

Uses LLM to parse queries into structured intents that reference
the artifact schema (7C scores, concept map metrics, LIWC metrics).

This enables queries like:
- "Find sessions with high conflict" → metric_filter on conflict_score
- "Compare Carlson Show and Vanessa" → entity_lookup with resolved IDs
- "Show me moments of analytical thinking" → metric_filter_chunks on avg_analytic_thinking
"""

import json
import logging
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict

from artifact_schema import (
    build_schema_prompt,
    get_all_metric_fields,
    get_metric_vocabulary,
    SEVEN_C_DIMENSIONS,
    CONCEPT_MAP_METRICS,
    LIWC_METRICS,
    QUERY_INTENTS,
    RETRIEVAL_STRATEGIES
)
from entity_resolver import EntityResolver

logger = logging.getLogger(__name__)


@dataclass
class MetricFilter:
    """A filter condition on a metric."""
    field: str
    operator: str  # >=, <=, >, <, ==, top_k
    value: Any
    source: str = ""  # "7c", "concept_map", "liwc"


@dataclass
class ResolvedEntity:
    """A resolved entity reference."""
    entity_type: str  # "session" or "speaker"
    original_reference: str
    resolved_id: Optional[int] = None
    resolved_name: Optional[str] = None
    confidence: float = 0.0
    match_type: str = ""


@dataclass
class StructuredQuery:
    """Structured representation of a parsed query."""
    original_query: str
    intent: str = "find_sessions"
    retrieval_strategy: str = "semantic_search"
    entities: List[ResolvedEntity] = field(default_factory=list)
    metric_filters: List[MetricFilter] = field(default_factory=list)
    semantic_query: Optional[str] = None
    sort_by: Optional[str] = None
    sort_descending: bool = True
    limit: int = 10
    artifacts_referenced: List[str] = field(default_factory=list)
    confidence: float = 0.0
    parse_error: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'original_query': self.original_query,
            'intent': self.intent,
            'retrieval_strategy': self.retrieval_strategy,
            'entities': [
                {
                    'entity_type': e.entity_type,
                    'original_reference': e.original_reference,
                    'resolved_id': e.resolved_id,
                    'resolved_name': e.resolved_name,
                    'confidence': e.confidence
                } for e in self.entities
            ],
            'metric_filters': [
                {
                    'field': m.field,
                    'operator': m.operator,
                    'value': m.value,
                    'source': m.source
                } for m in self.metric_filters
            ],
            'semantic_query': self.semantic_query,
            'sort_by': self.sort_by,
            'limit': self.limit,
            'artifacts_referenced': self.artifacts_referenced,
            'confidence': self.confidence
        }


class ArtifactQueryParser:
    """
    LLM-based query parser that understands queries in terms of artifacts.
    """

    def __init__(self, rag_service=None):
        """
        Initialize the parser.

        Args:
            rag_service: Optional RAG service for entity resolution
        """
        self.entity_resolver = EntityResolver(rag_service)
        self.metric_fields = get_all_metric_fields()
        self.metric_vocabulary = get_metric_vocabulary()
        self.schema_prompt = build_schema_prompt()

    def parse(self, query: str) -> StructuredQuery:
        """
        Parse a natural language query into structured intent.

        Args:
            query: Natural language query

        Returns:
            StructuredQuery with intent, entities, metrics, and retrieval strategy
        """
        logger.info(f"Artifact parser processing: '{query}'")

        # Initialize result
        result = StructuredQuery(original_query=query)

        try:
            # Step 1: Quick heuristic pre-check for common patterns
            heuristic_result = self._apply_heuristics(query)
            if heuristic_result:
                logger.info(f"Heuristic match: {heuristic_result.intent}")
                # Always resolve entities for comparison queries
                if heuristic_result.intent in ['compare_sessions', 'compare_speakers']:
                    heuristic_result = self._resolve_entities(heuristic_result)
                return heuristic_result

            # Step 2: Use LLM for complex queries
            llm_result = self._llm_parse(query)
            if llm_result:
                # Step 3: Resolve entities
                llm_result = self._resolve_entities(llm_result)
                return llm_result

            # Fallback to semantic search
            result.retrieval_strategy = "semantic_search"
            result.semantic_query = query
            result.confidence = 0.5
            return result

        except Exception as e:
            logger.error(f"Error parsing query: {e}")
            result.parse_error = str(e)
            result.retrieval_strategy = "semantic_search"
            result.semantic_query = query
            return result

    def _apply_heuristics(self, query: str) -> Optional[StructuredQuery]:
        """
        Apply fast heuristics for common query patterns.
        Returns None if no clear heuristic match.
        """
        query_lower = query.lower()

        # Pattern 0: Speaker queries should fall through to legacy routing
        # Don't intercept with metric heuristics if query is about speakers
        speaker_indicators = ['speaker', 'speakers', 'who asks', 'who speaks', 'who said', 'who mentioned']
        if any(ind in query_lower for ind in speaker_indicators):
            logger.info("Detected speaker query - deferring to legacy routing")
            return None  # Let legacy routing handle speaker queries

        # Pattern 1: Comparison queries
        if self._is_comparison_query(query_lower):
            return self._parse_comparison_heuristic(query)

        # Pattern 2: LIWC metric queries (chunk-level)
        liwc_match = self._match_liwc_metric(query_lower)
        if liwc_match and ('moment' in query_lower or 'instance' in query_lower or 'chunk' in query_lower):
            result = StructuredQuery(
                original_query=query,
                intent="find_chunks",
                retrieval_strategy="metric_filter_chunks",
                metric_filters=[MetricFilter(
                    field=liwc_match,
                    operator="top_k",
                    value=10,
                    source="liwc"
                )],
                sort_by=liwc_match,
                artifacts_referenced=["liwc_metrics"],
                confidence=0.9
            )
            return result

        # Pattern 3: 7C metric queries (session-level)
        for dim_name, dim_info in SEVEN_C_DIMENSIONS.items():
            for vocab in dim_info['user_vocabulary']:
                if vocab in query_lower:
                    # Check for "high" or "low" modifiers
                    is_high = any(w in query_lower for w in ['high', 'strong', 'good', 'great', 'excellent'])
                    is_low = any(w in query_lower for w in ['low', 'weak', 'poor', 'bad', 'lacking'])

                    if is_high or is_low:
                        result = StructuredQuery(
                            original_query=query,
                            intent="find_sessions",
                            retrieval_strategy="metric_filter",
                            metric_filters=[MetricFilter(
                                field=dim_info['field'],
                                operator=">=" if is_high else "<=",
                                value=70 if is_high else 30,
                                source="7c"
                            )],
                            sort_by=dim_info['field'],
                            sort_descending=is_high,
                            artifacts_referenced=["7c_scores"],
                            confidence=0.85
                        )
                        return result

        # Pattern 4: Concept map metric queries
        for metric_name, metric_info in CONCEPT_MAP_METRICS.items():
            for vocab in metric_info['user_vocabulary']:
                if vocab in query_lower:
                    is_high = any(w in query_lower for w in ['high', 'strong', 'many', 'lots', 'much'])
                    if is_high:
                        result = StructuredQuery(
                            original_query=query,
                            intent="find_sessions",
                            retrieval_strategy="metric_filter",
                            metric_filters=[MetricFilter(
                                field=metric_info['field'],
                                operator=">=",
                                value=3 if 'count' in metric_info['field'] else 5,
                                source="concept_map"
                            )],
                            sort_by=metric_info['field'],
                            artifacts_referenced=["concept_map"],
                            confidence=0.85
                        )
                        return result

        return None

    def _is_comparison_query(self, query_lower: str) -> bool:
        """Check if query is asking for comparison."""
        comparison_words = ['compare', 'versus', ' vs ', 'vs.', 'difference between', 'contrast']
        return any(w in query_lower for w in comparison_words)

    def _parse_comparison_heuristic(self, query: str) -> StructuredQuery:
        """Parse comparison query using entity resolution."""
        result = StructuredQuery(
            original_query=query,
            intent="compare_sessions",
            retrieval_strategy="comparison",
            confidence=0.9
        )

        # Check if comparing speakers
        query_lower = query.lower()
        if 'speaker' in query_lower or self._mentions_known_speakers(query):
            result.intent = "compare_speakers"

        # Entity resolution happens in _resolve_entities
        return result

    def _mentions_known_speakers(self, query: str) -> bool:
        """Check if query mentions known speaker names."""
        speakers = self.entity_resolver.get_available_speakers()
        query_lower = query.lower()
        count = sum(1 for s in speakers if s.lower() in query_lower)
        return count >= 2

    def _match_liwc_metric(self, query_lower: str) -> Optional[str]:
        """Check if query references a LIWC metric."""
        for metric_name, metric_info in LIWC_METRICS.items():
            for vocab in metric_info['user_vocabulary']:
                if vocab in query_lower:
                    return metric_info['field']
        return None

    def _llm_parse(self, query: str) -> Optional[StructuredQuery]:
        """
        Use LLM to parse complex queries.
        """
        try:
            from openai import OpenAI
            client = OpenAI()

            prompt = f"""Parse this discussion analytics query into structured form.

{self.schema_prompt}

## Query
"{query}"

## Instructions
Analyze the query and return JSON with:
1. "intent": One of {QUERY_INTENTS}
2. "retrieval_strategy": One of {list(RETRIEVAL_STRATEGIES.keys())}
3. "entities": List of {{type: "session"|"speaker", reference: "name/reference"}}
4. "metric_filters": List of {{field: "field_name", operator: ">=|<=|>|<|==|top_k", value: number}}
5. "semantic_query": Text to search for (if semantic search needed)
6. "sort_by": Field to sort results by (optional)
7. "artifacts_referenced": Which artifacts are relevant (e.g., ["7c_scores", "concept_map"])

Example for "Find sessions with high conflict but good communication":
{{
  "intent": "find_sessions",
  "retrieval_strategy": "metric_filter",
  "entities": [],
  "metric_filters": [
    {{"field": "conflict_score", "operator": ">=", "value": 70}},
    {{"field": "communication_score", "operator": ">=", "value": 70}}
  ],
  "semantic_query": null,
  "sort_by": "conflict_score",
  "artifacts_referenced": ["7c_scores"]
}}

Example for "Compare Carlson Show and Vanessa Podcast":
{{
  "intent": "compare_sessions",
  "retrieval_strategy": "comparison",
  "entities": [
    {{"type": "session", "reference": "Carlson Show"}},
    {{"type": "session", "reference": "Vanessa Podcast"}}
  ],
  "metric_filters": [],
  "semantic_query": null,
  "sort_by": null,
  "artifacts_referenced": ["7c_scores", "concept_map"]
}}

Example for "Show me moments of analytical thinking":
{{
  "intent": "find_chunks",
  "retrieval_strategy": "metric_filter_chunks",
  "entities": [],
  "metric_filters": [
    {{"field": "avg_analytic_thinking", "operator": "top_k", "value": 10}}
  ],
  "semantic_query": null,
  "sort_by": "avg_analytic_thinking",
  "artifacts_referenced": ["liwc_metrics"]
}}

Return ONLY valid JSON."""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                response_format={"type": "json_object"}
            )

            parsed = json.loads(response.choices[0].message.content)
            logger.info(f"LLM parsed query: {parsed}")

            # Convert to StructuredQuery
            result = StructuredQuery(
                original_query=query,
                intent=parsed.get('intent', 'find_sessions'),
                retrieval_strategy=parsed.get('retrieval_strategy', 'semantic_search'),
                semantic_query=parsed.get('semantic_query'),
                sort_by=parsed.get('sort_by'),
                artifacts_referenced=parsed.get('artifacts_referenced', []),
                confidence=0.8
            )

            # Parse entities
            for entity in parsed.get('entities', []):
                result.entities.append(ResolvedEntity(
                    entity_type=entity.get('type', 'session'),
                    original_reference=entity.get('reference', '')
                ))

            # Parse metric filters
            for mf in parsed.get('metric_filters', []):
                field_name = mf.get('field', '')
                source = self.metric_fields.get(field_name, 'unknown')
                result.metric_filters.append(MetricFilter(
                    field=field_name,
                    operator=mf.get('operator', '>='),
                    value=mf.get('value', 0),
                    source=source
                ))

            return result

        except Exception as e:
            logger.error(f"LLM parsing failed: {e}")
            return None

    def _resolve_entities(self, result: StructuredQuery) -> StructuredQuery:
        """
        Resolve all entity references in the structured query.
        """
        resolved_entities = []

        for entity in result.entities:
            if entity.entity_type == 'session':
                resolved = self.entity_resolver.resolve_session(entity.original_reference)
                if resolved:
                    entity.resolved_id = resolved['session_device_id']
                    entity.resolved_name = resolved['name']
                    entity.confidence = resolved['confidence']
                    entity.match_type = resolved['match_type']
                    logger.info(f"Resolved session '{entity.original_reference}' → {entity.resolved_id} ({entity.resolved_name})")
            elif entity.entity_type == 'speaker':
                resolved = self.entity_resolver.resolve_speaker(entity.original_reference)
                if resolved:
                    entity.resolved_id = resolved['speaker_ids'][0] if resolved['speaker_ids'] else None
                    entity.resolved_name = resolved['alias']
                    entity.confidence = resolved['confidence']
                    entity.match_type = resolved['match_type']
                    logger.info(f"Resolved speaker '{entity.original_reference}' → {entity.resolved_name}")

            resolved_entities.append(entity)

        result.entities = resolved_entities

        # Also try to find entities mentioned in query that weren't explicitly extracted
        if not result.entities and result.intent in ['compare_sessions', 'compare_speakers']:
            auto_resolved = self.entity_resolver.resolve_entities_in_query(result.original_query)

            for session in auto_resolved.get('sessions', []):
                result.entities.append(ResolvedEntity(
                    entity_type='session',
                    original_reference=session['name'],
                    resolved_id=session['session_device_id'],
                    resolved_name=session['name'],
                    confidence=session['confidence'],
                    match_type=session['match_type']
                ))

            for speaker in auto_resolved.get('speakers', []):
                result.entities.append(ResolvedEntity(
                    entity_type='speaker',
                    original_reference=speaker['alias'],
                    resolved_id=speaker['speaker_ids'][0] if speaker.get('speaker_ids') else None,
                    resolved_name=speaker['alias'],
                    confidence=speaker['confidence'],
                    match_type=speaker['match_type']
                ))

        return result

    def get_available_entities(self) -> Dict[str, List[str]]:
        """Return available entities for UI autocomplete."""
        return {
            'sessions': self.entity_resolver.get_available_sessions(),
            'speakers': self.entity_resolver.get_available_speakers()
        }
