# server/rag_query_parser.py - With Ultra RAG Architecture + Artifact-Grounded RAG

import re
import json
import logging
from typing import Dict, List, Optional
from rag_service import RAGService
from session_serializer import SessionSerializer
from query_understanding import QueryUnderstanding, QueryPlan
from context_builder import ContextBuilder
from artifact_query_parser import ArtifactQueryParser, StructuredQuery
from entity_resolver import EntityResolver
# Note: 'database' imported lazily inside functions to avoid circular import

logger = logging.getLogger(__name__)

class QueryParser:
    # Relevance threshold - ChromaDB cosine distance where results become unreliable
    # Based on testing: relevant queries get 0.45-0.60, irrelevant get 0.75+
    RELEVANCE_THRESHOLD = 0.70

    def __init__(self):
        self.rag = RAGService()
        self.session_serializer = SessionSerializer()
        self.query_understanding = QueryUnderstanding()
        self.context_builder = ContextBuilder()
        # Artifact-Grounded RAG components
        self.artifact_parser = ArtifactQueryParser(self.rag)
        self.entity_resolver = EntityResolver(self.rag)

    def _check_relevance(self, results: Dict, threshold: float = None) -> Dict:
        """
        Check if search results are actually relevant to the query.
        Returns modified results with relevance info, or no_results response.

        Args:
            results: Search results dict with 'results' list containing 'distance' scores
            threshold: Distance threshold (lower = more similar). Default: RELEVANCE_THRESHOLD

        Returns:
            Original results if relevant, or no_results dict if irrelevant
        """
        if threshold is None:
            threshold = self.RELEVANCE_THRESHOLD

        result_list = results.get('results', [])
        if not result_list:
            return {
                'no_results': True,
                'message': 'No content found in the database matching your query.',
                'original_results': results
            }

        # Check best result's distance
        best_distance = result_list[0].get('distance', 1.0)

        if best_distance > threshold:
            logger.info(f"Results below relevance threshold: best_distance={best_distance:.3f} > {threshold}")
            return {
                'no_results': True,
                'message': f'No relevant content found for this query. The closest matches (distance: {best_distance:.2f}) are not sufficiently related to your search.',
                'suggestion': 'Try searching for topics actually discussed in your sessions, such as personal experiences, opinions, or specific discussion themes.',
                'original_results': results
            }

        # Filter out results below threshold
        relevant_results = [r for r in result_list if r.get('distance', 1.0) <= threshold]
        results['results'] = relevant_results
        results['total_found'] = len(relevant_results)
        results['relevance_filtered'] = True

        return results

    def parse_and_execute(self, query: str, user_session_devices: Optional[List[int]] = None,
                          granularity: str = 'auto') -> Dict:
        """
        Parse natural language query and execute appropriate search.

        Uses Artifact-Grounded RAG for intelligent query understanding:
        1. First tries artifact-aware parsing (entity resolution, metric detection)
        2. Falls back to legacy keyword routing if artifact parsing doesn't match

        Args:
            query: Natural language query
            user_session_devices: Optional filter to user's sessions
            granularity: 'chunks' (30-sec), 'sessions' (concept map level), 'both', or 'auto'

        Returns:
            Search results with type indicator
        """
        query_lower = query.lower()

        # =====================================================================
        # ARTIFACT-GROUNDED RAG: Try artifact-aware parsing first
        # =====================================================================
        try:
            parsed = self.artifact_parser.parse(query)
            logger.info(f"Artifact parser result: intent={parsed.intent}, strategy={parsed.retrieval_strategy}, confidence={parsed.confidence}")

            # Skip artifact handling for speaker queries - let legacy routing handle them
            # (Artifact parser handles sessions and chunks, not speaker profiles)
            if parsed.intent in ['find_speakers', 'analyze_speaker']:
                logger.info("Speaker query detected - deferring to legacy speaker search")
            # If artifact parser has high confidence and a specific strategy, use it
            elif parsed.confidence >= 0.8 and parsed.retrieval_strategy in ['metric_filter_chunks', 'comparison']:
                result = self._handle_artifact_parsed_query(parsed, user_session_devices)
                if result:
                    logger.info(f"Artifact-grounded RAG handled query with type: {result.get('type')}")
                    return result

            # For comparison queries with entities, try entity resolution even with lower confidence
            if parsed.intent in ['compare_sessions', 'compare_speakers'] and parsed.entities:
                result = self._handle_artifact_parsed_query(parsed, user_session_devices)
                if result:
                    logger.info(f"Entity-resolved comparison handled query")
                    return result

        except Exception as e:
            logger.warning(f"Artifact parser failed, falling back to legacy routing: {e}")

        # =====================================================================
        # LEGACY ROUTING: Fall back to existing keyword-based routing
        # =====================================================================

        # Route granularity if auto
        if granularity == 'auto':
            granularity = self._route_query(query_lower)
            logger.info(f"Auto-routed query to granularity: {granularity}")

        # Check for specific query types first
        if self._is_comparative(query_lower):
            return self._handle_comparative(query, user_session_devices)
        elif self._is_similarity(query_lower):
            return self._handle_similarity_search(query, user_session_devices, granularity)
        elif self._is_temporal(query_lower):
            return self._handle_temporal_analysis(query, user_session_devices)

        # Route based on granularity
        if granularity == 'speakers':
            return self._handle_speaker_search(query)
        elif granularity == 'sessions':
            return self._handle_session_search(query, user_session_devices)
        elif granularity == 'both':
            return self._handle_hybrid_search(query, user_session_devices)
        else:  # 'chunks' or default
            return self._handle_intelligent_search(query, user_session_devices)
    
    def _is_comparative(self, query: str) -> bool:
        """Check if query is asking for comparison"""
        return any(word in query for word in ['compare', 'versus', 'vs', 'difference between', 'contrast'])
    
    def _is_similarity(self, query: str) -> bool:
        """Check if query is asking for similar sessions"""
        return any(phrase in query for phrase in ['similar to', 'like session', 'resembles', 'same as'])
    
    def _is_temporal(self, query: str) -> bool:
        """Check if query is asking for single-session temporal analysis (timeline).

        Only matches queries that:
        1. Contain timeline keywords AND
        2. Reference a specific session/device

        Cross-session evolution queries (e.g., "find discussions that evolved")
        should go through session search, not timeline analysis.
        """
        timeline_keywords = ['timeline', 'progression', 'throughout']
        has_timeline_keyword = any(word in query for word in timeline_keywords)
        has_session_reference = re.search(r'(session|device)\s*\d+', query.lower())

        return has_timeline_keyword and has_session_reference
    
    def _is_analytical_query(self, query: str) -> bool:
        """Check if query is asking for analysis (auto-trigger insights)"""
        query_lower = query.lower()
        analytical_keywords = ['why', 'how', 'what patterns', 'what makes', 'analyze', 'explain',
                               'insights', 'understand', 'reason', 'cause', 'leads to', 'results in']
        return any(keyword in query_lower for keyword in analytical_keywords)

    def _route_query(self, query: str) -> str:
        """
        Route query to appropriate granularity level using heuristics.
        Falls back to LLM classification for ambiguous queries.

        Returns:
            'chunks' for content/moment queries, 'sessions' for pattern/structure queries
        """
        query_lower = query.lower()

        # === Layer 1: Fast heuristics for clear cases ===

        # Chunk-level indicators (specific moments, content search)
        chunk_indicators = [
            'what was said', 'when did', 'who mentioned', 'quote',
            'specific moment', 'transcript', 'said about', 'discussed about',
            'talked about', 'find when', 'show me when', 'at what point',
            'exact words', 'what did they say'
        ]
        if any(phrase in query_lower for phrase in chunk_indicators):
            return 'chunks'

        # Speaker-level indicators - check BEFORE session indicators
        # to avoid "speakers who ask many questions" matching "many questions"
        speaker_early_indicators = [
            'speakers who', 'speaker who', 'who asks', 'who asked',
            'speakers that', 'speaker that'
        ]
        if any(phrase in query_lower for phrase in speaker_early_indicators):
            return 'speakers'

        # Session-level indicators (patterns, structure, quality)
        session_indicators = [
            'find sessions', 'discussions with', 'similar to session',
            'sessions where', 'pattern of', 'sessions that have',
            'sessions showing', 'discussions that', 'find groups',
            # Pedagogical/structural terms
            'argumentation', 'reasoning pattern', 'participation',
            'collaboration quality', 'problem solving', 'knowledge building',
            'hypothesis testing', 'inquiry-based', 'productive disagreement',
            'deep elaboration', 'cross-theme', 'discourse type',
            # 7C collaborative quality terms
            'communication quality', 'conflict resolution', 'contribution balance',
            'climate', 'high communication', 'effective collaboration',
            'good teamwork', 'balanced participation', 'constructive discussion',
            # Structural queries
            'strong argumentation', 'many questions', 'high challenge',
            'lots of questions', 'deep reasoning', 'well-connected concepts'
        ]
        if any(phrase in query_lower for phrase in session_indicators):
            return 'sessions'

        # Speaker-level indicators (cross-session speaker patterns)
        speaker_indicators = [
            r'how did .* engage', r'how does .* engage', r'speaker style',
            r'interviewer style', r'who asks', r'.* typically', r'engagement style',
            r'speaking style', r'compare .* style', r'.* engagement pattern'
        ]
        if any(re.search(pattern, query_lower) for pattern in speaker_indicators):
            return 'speakers'

        # Direct speaker name mentions with engagement context
        # Use word boundary to avoid "engagement" matching "engage"
        engagement_words = ['engage', 'style', 'behavior', 'typically', 'usually', 'tend to', 'characteristically']
        if any(re.search(rf'\b{word}\b', query_lower) for word in engagement_words):
            return 'speakers'

        # === Layer 2: LLM classification for ambiguous queries ===
        # Only call LLM for genuinely ambiguous queries
        return self._llm_classify_granularity(query)

    def _llm_classify_granularity(self, query: str) -> str:
        """
        Use LLM to classify ambiguous queries.
        ~100ms latency, acceptable for reflection-oriented tool.
        """
        try:
            from openai import OpenAI
            client = OpenAI()

            prompt = f"""Classify this discussion analytics query by what it's looking for:

Query: "{query}"

Options:
- "chunks": Looking for specific moments, quotes, or what was said about a topic
- "sessions": Looking for discussion patterns, structural qualities, or session characteristics
- "speakers": Looking for speaker behavior, engagement style, or cross-session speaker patterns

Return ONLY one word: chunks, sessions, or speakers."""

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=10
            )

            result = response.choices[0].message.content.strip().lower()
            if result in ['chunks', 'sessions', 'speakers']:
                return result
            return 'chunks'  # Default to chunks if unclear

        except Exception as e:
            logger.warning(f"LLM granularity classification failed: {e}")
            return 'chunks'  # Default to existing behavior
    
    def _handle_intelligent_search(self, query: str, user_devices: Optional[List[int]] = None) -> Dict:
        """Use GPT to understand query intent and extract parameters"""
        
        # Check if this is an analytical query that needs auto-insights
        auto_generate_insights = self._is_analytical_query(query)
        
        # First try GPT parsing
        try:
            from openai import OpenAI
            client = OpenAI()
            
            prompt = f"""Parse this discussion analytics query: "{query}"
            
            Extract:
            1. search_terms: Key terms to search for (remove filler words)
            2. intent: One of [topic_search, pattern_analysis, insight_generation]
            3. temporal: Any time references
            
            Return as JSON. Example:
            {{"search_terms": "collaboration", "intent": "pattern_analysis", "temporal": null}}
            """
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                response_format={"type": "json_object"}
            )
            
            parsed = json.loads(response.choices[0].message.content)
            logger.info(f"GPT parsed query: {parsed}")
            
            # Build filters (no metric filtering - only session filtering)
            filters = {}
            if user_devices:
                filters['session_device_ids'] = user_devices
            
            # Execute search
            search_results = self.rag.search(
                query=parsed.get('search_terms', query),
                n_results=5,
                **filters
            )

            logger.info(f"Search returned {search_results.get('total_found', 0)} results")

            # Check relevance - don't generate garbage from irrelevant results
            relevance_check = self._check_relevance(search_results)
            if relevance_check.get('no_results'):
                return {
                    'type': 'no_results',
                    'query': query,
                    'message': relevance_check['message'],
                    'suggestion': relevance_check.get('suggestion'),
                    'results': {'results': [], 'total_found': 0}
                }

            # Auto-generate insights if analytical query OR if GPT detected insight intent
            if auto_generate_insights or parsed.get('intent') == 'insight_generation':
                logger.info(f"Auto-generating insights for analytical query")
                insights = self.rag.generate_insights(query, relevance_check)
                return {
                    'type': 'insights',
                    'query': query,
                    'parsed': parsed,
                    'insights': insights,
                    'evidence': relevance_check
                }

            # Otherwise return as simple retrieval
            return {
                'type': parsed.get('intent', 'topic_search'),
                'query': query,
                'parsed': parsed,
                'results': relevance_check
            }
            
        except Exception as e:
            logger.warning(f"GPT parsing failed, using fallback: {e}")
            return self._fallback_search(query, user_devices, auto_generate_insights)
    
    def _fallback_search(self, query: str, user_devices: Optional[List[int]] = None, 
                         auto_generate_insights: bool = False) -> Dict:
        """Fallback without GPT - use simple heuristics"""
        
        logger.info(f"Using fallback search for: {query}")
        
        # Remove common filler words
        stop_words = {'show', 'me', 'find', 'search', 'for', 'the', 'a', 'an', 'about', 'what', 'when', 'where'}
        words = query.lower().split()
        clean_query = ' '.join([w for w in words if w not in stop_words])
        
        # Build filters (no metric filtering - only session filtering)
        filters = {}
        if user_devices:
            filters['session_device_ids'] = user_devices
        
        results = self.rag.search(
            query=clean_query if clean_query else query,
            n_results=5,
            **filters
        )

        logger.info(f"Fallback search returned {results.get('total_found', 0)} results")

        # Check relevance - don't return garbage
        relevance_check = self._check_relevance(results)
        if relevance_check.get('no_results'):
            return {
                'type': 'no_results',
                'query': query,
                'message': relevance_check['message'],
                'suggestion': relevance_check.get('suggestion'),
                'results': {'results': [], 'total_found': 0}
            }

        # Auto-generate insights if needed
        if auto_generate_insights:
            logger.info(f"Auto-generating insights in fallback")
            insights = self.rag.generate_insights(query, relevance_check)
            return {
                'type': 'insights',
                'query': query,
                'interpreted_as': clean_query,
                'insights': insights,
                'evidence': relevance_check
            }

        return {
            'type': 'topic_search',
            'query': query,
            'interpreted_as': clean_query,
            'results': relevance_check
        }

    # =========================================================================
    # ARTIFACT-GROUNDED RAG: METRIC-BASED CHUNK RETRIEVAL
    # =========================================================================

    def _handle_metric_chunk_search(self, parsed: StructuredQuery, user_devices: Optional[List[int]] = None) -> Dict:
        """
        Handle metric-based chunk retrieval for queries like:
        "Show me moments of analytical thinking"

        Uses LIWC metrics stored in chunk metadata to filter/sort chunks.
        """
        logger.info(f"Handling metric-based chunk search: {parsed.original_query}")

        # Get the metric filter
        if not parsed.metric_filters:
            return {
                'type': 'error',
                'message': 'No metric filter specified for chunk search'
            }

        metric_filter = parsed.metric_filters[0]
        metric_field = metric_filter.field
        operator = metric_filter.operator
        value = metric_filter.value

        logger.info(f"Searching chunks by metric: {metric_field} {operator} {value}")

        try:
            # Get all chunks (we'll filter in Python since ChromaDB doesn't support sorting by metadata)
            where_filter = {}
            if user_devices:
                # ChromaDB doesn't support IN for multiple values easily, so we'll filter in Python
                pass

            # Retrieve chunks with the metric field
            all_chunks = self.rag.collection.get(
                include=['documents', 'metadatas'],
                limit=1000  # Get a reasonable number to filter
            )

            if not all_chunks['metadatas']:
                return {
                    'type': 'no_results',
                    'message': 'No chunks found in the database',
                    'results': {'results': [], 'total_found': 0}
                }

            # Filter and sort by metric
            chunks_with_metric = []
            for i, meta in enumerate(all_chunks['metadatas']):
                metric_value = meta.get(metric_field, 0)
                if metric_value is None:
                    metric_value = 0

                # Apply user device filter if specified
                if user_devices and meta.get('session_device_id') not in user_devices:
                    continue

                chunks_with_metric.append({
                    'text': all_chunks['documents'][i] if all_chunks['documents'] else '',
                    'metadata': meta,
                    'metric_value': float(metric_value),
                    'session_device_id': meta.get('session_device_id'),
                    'start_time': meta.get('start_time', 0),
                    'end_time': meta.get('end_time', 0),
                    'speakers': meta.get('speakers', [])
                })

            # Sort by metric value (descending for "high" queries)
            chunks_with_metric.sort(key=lambda x: x['metric_value'], reverse=True)

            # Apply top_k or threshold filter
            if operator == 'top_k':
                result_chunks = chunks_with_metric[:int(value)]
            elif operator == '>=':
                result_chunks = [c for c in chunks_with_metric if c['metric_value'] >= float(value)]
            elif operator == '<=':
                result_chunks = [c for c in chunks_with_metric if c['metric_value'] <= float(value)]
            elif operator == '>':
                result_chunks = [c for c in chunks_with_metric if c['metric_value'] > float(value)]
            elif operator == '<':
                result_chunks = [c for c in chunks_with_metric if c['metric_value'] < float(value)]
            else:
                result_chunks = chunks_with_metric[:10]

            # Format results
            formatted_results = []
            for chunk in result_chunks[:20]:  # Limit to top 20
                formatted_results.append({
                    'text': chunk['text'][:500] if chunk['text'] else '',
                    'metadata': chunk['metadata'],
                    'session_device_id': chunk['session_device_id'],
                    'session_name': self._get_session_name(chunk['session_device_id']),
                    metric_field: chunk['metric_value'],
                    'start_time': chunk['start_time'],
                    'end_time': chunk['end_time'],
                    'speakers': chunk['speakers']
                })

            logger.info(f"Found {len(formatted_results)} chunks matching metric criteria")

            return {
                'type': 'metric_chunks',
                'query': parsed.original_query,
                'metric_field': metric_field,
                'operator': operator,
                'value': value,
                'artifacts_referenced': parsed.artifacts_referenced,
                'results': formatted_results,
                'total_found': len(formatted_results)
            }

        except Exception as e:
            logger.error(f"Error in metric chunk search: {e}")
            return {
                'type': 'error',
                'message': f'Error searching chunks by metric: {str(e)}'
            }

    def _handle_artifact_parsed_query(self, parsed: StructuredQuery, user_devices: Optional[List[int]] = None) -> Optional[Dict]:
        """
        Handle queries that were parsed by the artifact parser.

        Returns None if the parsed query should fall through to legacy handlers.
        """
        logger.info(f"Handling artifact-parsed query: intent={parsed.intent}, strategy={parsed.retrieval_strategy}")

        # Route based on retrieval strategy
        if parsed.retrieval_strategy == 'metric_filter_chunks':
            return self._handle_metric_chunk_search(parsed, user_devices)

        elif parsed.retrieval_strategy == 'metric_filter':
            # Session-level metric filtering - use existing get_sessions_by_metrics
            if parsed.metric_filters:
                metric_filters = {}
                for mf in parsed.metric_filters:
                    metric_filters[mf.field] = (mf.operator, mf.value)

                sort_by = parsed.sort_by or (parsed.metric_filters[0].field if parsed.metric_filters else None)

                results = self.rag.get_sessions_by_metrics(
                    metric_filters=metric_filters,
                    n_results=parsed.limit,
                    sort_by=sort_by
                )

                return {
                    'type': 'session_search',
                    'query': parsed.original_query,
                    'search_level': 'sessions',
                    'metric_filters': [mf.__dict__ if hasattr(mf, '__dict__') else mf for mf in parsed.metric_filters],
                    'artifacts_referenced': parsed.artifacts_referenced,
                    'session_results': results,
                    'total_found': len(results)
                }

        elif parsed.retrieval_strategy == 'comparison' and parsed.entities:
            # Entity-resolved comparison - pass to _handle_comparative with resolved IDs
            # Extract resolved session device IDs
            resolved_devices = []
            for entity in parsed.entities:
                if entity.entity_type == 'session' and entity.resolved_id:
                    resolved_devices.append((entity.resolved_id, entity.resolved_name or entity.original_reference))

            if len(resolved_devices) >= 2:
                # Inject resolved devices into comparison handler
                return self._handle_comparative_with_resolved(parsed.original_query, resolved_devices)

        # For other strategies, return None to fall through to legacy handling
        return None

    def _handle_comparative_with_resolved(self, query: str, resolved_devices: list) -> Dict:
        """Handle comparison with pre-resolved device IDs from entity resolver."""
        logger.info(f"Handling comparison with resolved devices: {resolved_devices}")

        comparisons = {}
        for device_id, label in resolved_devices[:2]:
            # First try transcript collection (has session-level summaries)
            transcripts = self.rag.transcript_collection.get(
                where={'session_device_id': device_id},
                limit=1
            )

            # Fallback to chunk collection if transcript not found
            if not transcripts['metadatas']:
                transcripts = self.rag.collection.get(
                    where={'session_device_id': device_id},
                    limit=100
                )

            # Get argumentation metrics
            arg_metrics = self._get_argumentation_metrics(device_id)

            # Get temporal evolution
            evolution = self._get_temporal_evolution(device_id)

            if transcripts['metadatas']:
                meta = transcripts['metadatas'][0]
                comparisons[label] = {
                    'device_id': device_id,
                    'metrics': {
                        'communication_score': meta.get('communication_score', 0),
                        'conflict_score': meta.get('conflict_score', 0),
                        'contribution_score': meta.get('contribution_score', 0),
                        'constructive_score': meta.get('constructive_score', 0),
                        'climate_score': meta.get('climate_score', 0),
                        'context_score': meta.get('context_score', 0),
                        'compatibility_score': meta.get('compatibility_score', 0),
                    },
                    'argumentation': arg_metrics,
                    'evolution': evolution,
                    'total_chunks': meta.get('transcript_count', 1),
                    'unique_speakers': meta.get('speaker_count', 0),
                    'discourse_type': meta.get('discourse_type', 'unknown'),
                    'cluster_count': meta.get('cluster_count', 0),
                    'text_preview': transcripts['documents'][0][:300] if transcripts['documents'] else ''
                }

        logger.info(f"Comparison completed for {len(comparisons)} sessions")

        return {
            'type': 'comparative',
            'query': query,
            'comparisons': comparisons,
            'entity_resolved': True
        }

    def _handle_comparative(self, query: str, user_devices: Optional[List[int]] = None) -> Dict:
        """Handle comparative queries - supports both IDs and natural language topics."""
        import database  # Lazy import to avoid circular dependency

        logger.info(f"Handling comparative query: {query}")

        # NEW: Check if this is a speaker comparison first
        if self._is_speaker_comparison_query(query):
            speaker_names = self._extract_speakers_to_compare(query)
            if len(speaker_names) >= 2:
                logger.info(f"Detected speaker comparison: {speaker_names}")
                return self._handle_speaker_comparison(query, speaker_names, user_devices)

        # Extract session/device IDs
        session_pattern = r'session\s*(\d+)'
        device_pattern = r'device\s*(\d+)'

        session_ids = re.findall(session_pattern, query.lower())
        device_ids = re.findall(device_pattern, query.lower())

        # Collect devices to compare
        devices_to_compare = []

        for sid in session_ids:
            session_devices = database.get_session_devices(session_id=int(sid))
            devices_to_compare.extend([(sd.id, f"Session {sid} - {sd.name}") for sd in session_devices])

        for did in device_ids:
            devices_to_compare.append((int(did), f"Device {did}"))

        # If not enough numeric IDs, try natural language topic extraction
        if len(devices_to_compare) < 2:
            logger.info("Not enough numeric IDs, trying natural language topic extraction")
            topics = self._extract_comparison_topics(query)
            logger.info(f"Extracted topics: {topics}")

            for topic in topics:
                if topic:  # Skip empty topics
                    resolved = self._resolve_topic_to_session(topic)
                    if resolved:
                        # Avoid duplicates
                        if resolved[0] not in [d[0] for d in devices_to_compare]:
                            devices_to_compare.append(resolved)

        if len(devices_to_compare) < 2:
            return {
                'type': 'error',
                'message': 'Could not identify two sessions to compare. Try being more specific about the topics.',
                'example': 'Compare the dinosaur discussion and the nuclear fusion discussion'
            }

        # Get metrics for each (limit to first 2)
        comparisons = {}
        for device_id, label in devices_to_compare[:2]:
            # First try transcript collection (has session-level summaries)
            transcripts = self.rag.transcript_collection.get(
                where={'session_device_id': device_id},
                limit=1
            )

            # Fallback to chunk collection if transcript not found
            if not transcripts['metadatas']:
                transcripts = self.rag.collection.get(
                    where={'session_device_id': device_id},
                    limit=100
                )

            # Get argumentation metrics
            arg_metrics = self._get_argumentation_metrics(device_id)

            # Get temporal evolution
            evolution = self._get_temporal_evolution(device_id)

            if transcripts['metadatas']:
                meta = transcripts['metadatas'][0]  # Use first (session-level) metadata
                comparisons[label] = {
                    'device_id': device_id,
                    'metrics': {
                        # 7C collaborative quality scores (available in transcript collection)
                        'communication_score': meta.get('communication_score', 0),
                        'conflict_score': meta.get('conflict_score', 0),
                        'contribution_score': meta.get('contribution_score', 0),
                        'constructive_score': meta.get('constructive_score', 0),
                        'climate_score': meta.get('climate_score', 0),
                        'context_score': meta.get('context_score', 0),
                        'compatibility_score': meta.get('compatibility_score', 0),
                    },
                    'argumentation': arg_metrics,
                    'evolution': evolution,
                    'total_chunks': meta.get('transcript_count', 1),
                    'unique_speakers': meta.get('speaker_count', 0),
                    'discourse_type': meta.get('discourse_type', 'unknown'),
                    'cluster_count': meta.get('cluster_count', 0),
                    'text_preview': transcripts['documents'][0][:300] if transcripts['documents'] else ''
                }

        logger.info(f"Comparison completed for {len(comparisons)} sessions")

        return {
            'type': 'comparative',
            'query': query,
            'comparisons': comparisons
        }
    
    def _handle_similarity_search(self, query: str, user_devices: Optional[List[int]] = None,
                                   granularity: str = 'sessions') -> Dict:
        """Find sessions similar to a reference - supports both chunk and session level"""
        import database  # Lazy import to avoid circular dependency

        logger.info(f"Handling similarity query: {query} (granularity: {granularity})")

        # Extract reference ID
        device_match = re.search(r'device\s*(\d+)', query.lower())
        session_match = re.search(r'session\s*(\d+)', query.lower())

        reference_id = None
        if device_match:
            reference_id = int(device_match.group(1))
        elif session_match:
            sid = int(session_match.group(1))
            devices = database.get_session_devices(session_id=sid)
            if devices:
                reference_id = devices[0].id

        if not reference_id:
            if user_devices and len(user_devices) > 0:
                reference_id = user_devices[0]
            else:
                return {
                    'type': 'error',
                    'message': 'Please specify a session or device to find similar discussions'
                }

        # Use session-level similarity (concept map based) when available
        if granularity == 'sessions':
            results = self.rag.find_similar_sessions(reference_id, n_results=5)
            return {
                'type': 'similar_sessions',
                'query': query,
                'reference_device': reference_id,
                'search_level': 'sessions',
                'results': results
            }
        else:
            # Fallback to chunk-level similarity
            results = self.rag.find_similar_discussions(reference_id, n_results=5)
            return {
                'type': 'similar',
                'query': query,
                'reference_device': reference_id,
                'search_level': 'chunks',
                'results': results
            }

    def _handle_speaker_search(self, query: str) -> Dict:
        """
        Handle speaker-level searches - finds speakers by engagement patterns.
        Uses cross-session speaker profiles.
        """
        logger.info(f"Handling speaker-level search: {query}")

        # Extract mentioned speaker names from query
        mentioned_speakers = self._extract_speaker_names(query)
        is_specific_speaker_query = len(mentioned_speakers) > 0

        # Search speakers
        results = self.rag.search_speakers(
            query=query,
            n_results=10 if is_specific_speaker_query else 5  # Get more to filter
        )

        # Check if we got any results
        speaker_results = results.get('results', [])
        if not speaker_results or len(speaker_results) == 0:
            return {
                'type': 'speaker_search',
                'query': query,
                'search_level': 'speakers',
                'speaker_results': [],
                'total_found': 0,
                'message': 'No speaker profiles found. Try running speaker indexing if speakers exist in the database.'
            }

        # Filter to mentioned speakers if specific names were found
        if is_specific_speaker_query:
            filtered_results = []
            for result in speaker_results:
                metadata = result.get('metadata', {})
                speaker_alias = metadata.get('alias', metadata.get('speaker_alias', ''))
                if speaker_alias and speaker_alias.lower() in [s.lower() for s in mentioned_speakers]:
                    filtered_results.append(result)
            # Use filtered results if we found matches, otherwise fall back to semantic results
            if filtered_results:
                speaker_results = filtered_results
                results['results'] = filtered_results

        # Auto-generate insights for:
        # 1. Analytical queries (why, how, analyze, etc.)
        # 2. Specific speaker queries (asking about a named speaker's style/engagement)
        should_generate_insights = (
            self._is_analytical_query(query) or
            (is_specific_speaker_query and self._is_speaker_profile_query(query))
        )

        if should_generate_insights:
            insights = self._generate_speaker_insights(query, results)
            return {
                'type': 'speaker_insights',
                'query': query,
                'search_level': 'speakers',
                'insights': insights,
                'speaker_results': speaker_results,
                'total_found': len(speaker_results),
                'mentioned_speakers': mentioned_speakers,
                'evidence': results
            }

        return {
            'type': 'speaker_search',
            'query': query,
            'search_level': 'speakers',
            'speaker_results': speaker_results,
            'total_found': len(speaker_results),
            'mentioned_speakers': mentioned_speakers
        }

    def _extract_speaker_names(self, query: str) -> List[str]:
        """Extract speaker names mentioned in the query."""
        # Get known speaker aliases from the speaker collection
        try:
            all_speakers = self.rag.speaker_collection.get(include=['metadatas'])
            known_aliases = set()
            if all_speakers and all_speakers.get('metadatas'):
                for meta in all_speakers['metadatas']:
                    alias = meta.get('alias', meta.get('speaker_alias', ''))
                    if alias:
                        known_aliases.add(alias.lower())
        except Exception as e:
            logger.warning(f"Could not get speaker aliases: {e}")
            known_aliases = set()

        # Find which known speakers are mentioned in the query
        query_lower = query.lower()
        mentioned = []
        for alias in known_aliases:
            if alias in query_lower:
                mentioned.append(alias.capitalize())
        return mentioned

    def _is_speaker_profile_query(self, query: str) -> bool:
        """Check if query is asking about a specific speaker's profile/style."""
        query_lower = query.lower()
        profile_keywords = [
            'style', 'engage', 'engagement', 'communicate', 'communication',
            'participate', 'participation', 'speak', 'speaking', 'talk',
            'contribute', 'contribution', 'behave', 'behavior', 'profile',
            'typically', 'usually', 'tend to', 'characteristic'
        ]
        return any(keyword in query_lower for keyword in profile_keywords)

    def _is_speaker_comparison_query(self, query: str) -> bool:
        """Check if query is asking to compare two or more speakers."""
        query_lower = query.lower()
        # Check for comparison keywords
        comparison_keywords = ['compare', 'versus', ' vs ', 'difference', 'differently', 'differ']
        has_comparison = any(kw in query_lower for kw in comparison_keywords)

        if not has_comparison:
            return False

        # Check if at least two speaker names are mentioned
        mentioned_speakers = self._extract_speaker_names(query)
        return len(mentioned_speakers) >= 2

    def _extract_speakers_to_compare(self, query: str) -> List[str]:
        """Extract speaker names from a comparison query."""
        return self._extract_speaker_names(query)

    def _handle_speaker_comparison(self, query: str, speaker_names: List[str], user_devices: Optional[List[int]] = None) -> Dict:
        """Handle speaker comparison queries - compare engagement patterns between speakers."""
        logger.info(f"Handling speaker comparison: {speaker_names}")

        # Get data for each speaker from speaker_collection
        speaker_profiles = {}

        for speaker_name in speaker_names[:2]:  # Limit to 2 speakers
            try:
                # Search for this speaker in speaker_collection
                results = self.rag.speaker_collection.query(
                    query_texts=[f"{speaker_name} engagement style"],
                    n_results=5,
                    where={'alias': speaker_name} if speaker_name else None
                )

                # Also try with partial match if exact match fails
                if not results['documents'] or not results['documents'][0]:
                    results = self.rag.speaker_collection.get(include=['documents', 'metadatas'])
                    # Filter by speaker name
                    filtered_docs = []
                    filtered_metas = []
                    for i, meta in enumerate(results.get('metadatas', [])):
                        alias = meta.get('alias', meta.get('speaker_alias', '')).lower()
                        if speaker_name.lower() in alias:
                            filtered_docs.append(results['documents'][i] if results.get('documents') else '')
                            filtered_metas.append(meta)
                    results = {'documents': [filtered_docs], 'metadatas': [filtered_metas]}

                if results['documents'] and results['documents'][0]:
                    meta = results['metadatas'][0][0] if results['metadatas'][0] else {}
                    profile_text = results['documents'][0][0] if isinstance(results['documents'][0], list) else results['documents'][0]

                    speaker_profiles[speaker_name] = {
                        'alias': meta.get('alias', meta.get('speaker_alias', speaker_name)),
                        'session_count': meta.get('session_count', 0),
                        'total_turns': meta.get('total_turns', 0),
                        'question_count': meta.get('question_count', 0),
                        'question_ratio': meta.get('question_ratio', 0),
                        'avg_turn_length': meta.get('avg_turn_length', 0),
                        'avg_clout': meta.get('avg_clout', 0),
                        'avg_analytic': meta.get('avg_analytic', 0),
                        'avg_tone': meta.get('avg_tone', 0),
                        'avg_authenticity': meta.get('avg_authenticity', 0),
                        'profile_text': profile_text[:500] if profile_text else ''
                    }
            except Exception as e:
                logger.warning(f"Error getting speaker profile for {speaker_name}: {e}")
                continue

        if len(speaker_profiles) < 2:
            return {
                'type': 'error',
                'message': f'Could not find profiles for both speakers: {speaker_names}. Found: {list(speaker_profiles.keys())}',
                'suggestion': 'Try using exact speaker names as they appear in the transcripts.'
            }

        # Generate comparison insights using three-layer framework
        comparison_context = self._build_speaker_comparison_context(speaker_profiles, query)
        insights = self._generate_speaker_comparison_insights(query, speaker_profiles, comparison_context)

        return {
            'type': 'speaker_comparison',
            'query': query,
            'speakers': speaker_profiles,
            'insights': insights
        }

    def _build_speaker_comparison_context(self, speaker_profiles: Dict, query: str) -> str:
        """Build context for speaker comparison insights."""
        context_parts = []

        for name, profile in speaker_profiles.items():
            context_parts.append(f"""
### Speaker: {profile.get('alias', name)}
- Sessions participated: {profile.get('session_count', 0)}
- Total speaking turns: {profile.get('total_turns', 0)}
- Questions asked: {profile.get('question_count', 0)} ({profile.get('question_ratio', 0)*100:.1f}% question ratio)
- Avg turn length: {profile.get('avg_turn_length', 0):.1f} words
- LIWC Metrics:
  - Clout (confidence): {profile.get('avg_clout', 0):.1f}
  - Analytic thinking: {profile.get('avg_analytic', 0):.1f}
  - Emotional tone: {profile.get('avg_tone', 0):.1f}
  - Authenticity: {profile.get('avg_authenticity', 0):.1f}

Profile excerpt:
{profile.get('profile_text', 'No profile available')}
""")

        return "\n".join(context_parts)

    def _generate_speaker_comparison_insights(self, query: str, speaker_profiles: Dict, context: str) -> str:
        """Generate three-layer insights comparing speakers."""
        from insight_prompts import get_smart_assistant_system_prompt

        try:
            from openai import OpenAI
            client = OpenAI()

            speaker_names = list(speaker_profiles.keys())

            prompt = f"""Compare these two speakers based on the query: "{query}"

## Speaker Profiles
{context}

## Instructions
Use the three-layer response framework:

**GROUND**: Start by referencing what the speaker profiles show in terms of concrete metrics.
Example: "{speaker_names[0]}'s profile shows X speaking turns with Y% question ratio, while {speaker_names[1]} has..."

**ENRICH**: Interpret what these metrics mean for their engagement style.
Example: "This suggests {speaker_names[0]} tends to take a more questioning approach, while {speaker_names[1]}..."

**EXTEND**: Provide original insight about how they complement or contrast.
Example: "The pairing creates a dynamic where..."

Weave these three layers naturally without using section headers."""

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": get_smart_assistant_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=800
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error generating speaker comparison insights: {e}")
            return f"Error generating insights: {str(e)}"

    def _generate_speaker_insights(self, query: str, speaker_results: Dict) -> str:
        """Generate insights from speaker-level search results."""
        if not speaker_results.get('results'):
            return "No speakers found to generate insights from."

        # Build context from speaker metadata
        context_parts = []
        for i, result in enumerate(speaker_results['results'][:5], 1):
            metadata = result.get('metadata', {})
            preview = result.get('text_preview', '')[:400]

            context_parts.append(
                f"Speaker {i}: {metadata.get('speaker_alias', 'Unknown')}\n"
                f"  Sessions: {metadata.get('session_count', 0)}\n"
                f"  Questions asked: {metadata.get('question_count', 0)}\n"
                f"  Avg clout: {metadata.get('avg_clout', 0)}\n"
                f"  Profile: {preview}\n"
            )

        context = "\n".join(context_parts)

        try:
            from openai import OpenAI
            client = OpenAI()

            prompt = f"""Based on these speaker profiles related to "{query}", provide insights about:
1. Common engagement patterns across speakers
2. Notable differences in speaking styles
3. Recommendations for understanding speaker dynamics

Speakers:
{context}

Provide specific, evidence-based insights with references to speaker characteristics."""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": """You are an expert at analyzing speaker engagement patterns in discussions.

When providing insights:
- Include 2-3 specific quotes that illustrate the speaker's communication style
- Make direct observations about patterns (avoid filler like "It's worth noting")
- Reference specific metrics when relevant (e.g., "asked questions in 40% of turns")
- Focus on what's distinctive or interesting about this speaker's engagement"""},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error generating speaker insights: {e}")
            return f"Error generating insights: {str(e)}"

    def _route_to_collections(self, query: str) -> List[str]:
        """
        Determine which session collection(s) to search based on query.

        Returns:
            List of collection names: ['transcripts', 'concepts', 'seven_c']
        """
        query_lower = query.lower()

        # Topic/content queries → transcripts (full session text)
        topic_indicators = [
            'about', 'discuss', 'mention', 'talk about', 'topic', 'said about',
            'talked about', 'regarding', 'concerning', 'related to', 'sessions on',
            'discussions about', 'conversations about'
        ]
        if any(phrase in query_lower for phrase in topic_indicators):
            return ['transcripts']

        # Structure/argumentation queries → concepts (graph-as-text)
        structure_indicators = [
            'argumentation', 'hypothesis', 'questions', 'reasoning', 'structure',
            'argument flow', 'concept chain', 'builds on', 'challenges', 'supports',
            'problem solving', 'knowledge building', 'discourse type', 'inquiry',
            'evidence', 'conclusion', 'synthesis', 'elaboration'
        ]
        if any(phrase in query_lower for phrase in structure_indicators):
            return ['concepts']

        # Quality/collaboration queries → 7c
        quality_indicators = [
            'communication', 'collaboration', 'quality', 'productive', 'teamwork',
            'climate', 'conflict', 'contribution', 'constructive', 'compatibility',
            '7c', 'balanced participation', 'effective', 'good teamwork',
            'collaborative quality'
        ]
        if any(phrase in query_lower for phrase in quality_indicators):
            return ['seven_c']

        # Ambiguous → search all three and fuse with RRF
        return ['transcripts', 'concepts', 'seven_c']

    def _handle_session_search(self, query: str, user_devices: Optional[List[int]] = None) -> Dict:
        """
        Handle session-level searches - finds discussions by structure, patterns, and quality.

        ULTRA RAG ENHANCEMENT:
        - Uses query understanding to detect focus area
        - For argumentation/collaboration queries: metric-first retrieval
        - For topic queries: semantic-first with metric re-ranking
        - Hybrid ranking combines metric and semantic scores
        """
        logger.info(f"Handling session-level search: {query}")

        # ULTRA RAG: Analyze query to determine best retrieval strategy
        plan = self.query_understanding.analyze(query)
        logger.info(f"Query plan: focus={plan.focus_area}, strategy={plan.retrieval_strategy}, filters={plan.metric_filters}")

        # Route to appropriate collection(s)
        collections = self._route_to_collections(query)
        logger.info(f"Routing to collections: {collections}")

        # Extract any structural filters from query
        filters = self._extract_session_filters(query)

        # ULTRA RAG: Use metric-first or hybrid retrieval for quality-focused queries
        use_metric_first = plan.retrieval_strategy == 'metric_first' and plan.metric_filters

        if use_metric_first:
            # Get sessions sorted by metric FIRST, then add semantic relevance
            logger.info(f"Using METRIC-FIRST retrieval with filters: {plan.metric_filters}")

            sort_metric = plan.metrics_needed[0] if plan.metrics_needed else 'debate_score'
            hybrid_results = self.rag.hybrid_session_search(
                query=query,
                metric_filters=plan.metric_filters,
                sort_metric=sort_metric,
                n_results=5,
                metric_weight=0.5,  # Balance metric and semantic
                semantic_weight=0.5
            )

            # Convert hybrid results to standard format with metrics included
            result_list = []
            for hr in hybrid_results:
                result_list.append({
                    'session_device_id': hr['session_device_id'],
                    'metadata': hr.get('metrics', {}),
                    'hybrid_score': hr.get('hybrid_score', 0),
                    'metric_score': hr.get('metric_score', 0),
                    'semantic_score': hr.get('semantic_score', 0),
                    'text_preview': hr.get('metrics', {}).get('session_name', f"Session {hr['session_device_id']}")
                })

            # Format for downstream processing
            formatted_results = {
                "query": query,
                "search_level": "sessions",
                "collections_searched": collections,
                "fused_results": result_list,
                "retrieval_strategy": "metric_first",
                "total_found": len(result_list)
            }

        # Standard semantic search for topic queries
        elif len(collections) > 1:
            # Multi-collection search with RRF
            results = self.rag.search_sessions_multi(
                query=query,
                collections=collections,
                n_results=5,
                session_device_ids=user_devices,
                filters=filters
            )

            # Format results for response
            formatted_results = {
                "query": query,
                "search_level": "sessions",
                "collections_searched": collections,
                "fused_results": results.get('fused_results', []),
                "results_by_collection": results.get('results_by_collection', {}),
                "total_found": len(results.get('fused_results', []))
            }
            result_list = formatted_results.get('fused_results', [])
        else:
            # Single collection search
            collection = collections[0]
            if collection == 'transcripts':
                results = self.rag.search_transcripts(query, 5, user_devices, filters)
            elif collection == 'concepts':
                results = self.rag.search_concepts(query, 5, user_devices, filters)
            else:  # seven_c
                results = self.rag.search_7c(query, 5, user_devices, filters)

            formatted_results = results
            result_list = results.get('results', [])

        # =====================================================================
        # ENRICH with argumentation and temporal evolution metrics
        # =====================================================================
        for result in result_list:
            session_id = result.get('session_device_id') or result.get('metadata', {}).get('session_device_id')
            if session_id:
                # Add argumentation metrics
                result['argumentation'] = self._get_argumentation_metrics(session_id)
                # Add temporal evolution
                result['evolution'] = self._get_temporal_evolution(session_id)

        # =====================================================================
        # RE-RANK based on query type
        # =====================================================================
        is_arg_query = self._is_argumentation_query(query)
        is_temporal_query = self._is_temporal_evolution_query(query)

        if is_arg_query:
            sort_key = self._get_argumentation_sort_key(query)
            logger.info(f"Re-ranking by argumentation metric: {sort_key}")
            result_list = sorted(
                result_list,
                key=lambda r: r.get('argumentation', {}).get(sort_key, 0),
                reverse=True
            )

        if is_temporal_query:
            sort_key = self._get_temporal_sort_key(query)
            logger.info(f"Re-ranking by temporal metric: {sort_key}")

            # Filter to sessions with positive evolution if query implies improvement
            improvement_words = ['improved', 'better', 'grew', 'increased', 'more']
            if any(w in query.lower() for w in improvement_words):
                result_list = [r for r in result_list
                              if r.get('evolution', {}).get(sort_key, 0) > 0]

            # Sort by evolution magnitude
            result_list = sorted(
                result_list,
                key=lambda r: abs(r.get('evolution', {}).get(sort_key, 0)),
                reverse=True
            )

        # Update formatted_results with enriched/reranked list
        if len(collections) > 1:
            formatted_results['fused_results'] = result_list
        else:
            formatted_results['results'] = result_list

        formatted_results['total_found'] = len(result_list)

        # =====================================================================
        # Generate insights - ONLY for analytical queries (why, how, analyze, etc.)
        # Session searches, argumentation searches should NOT auto-trigger insights
        # =====================================================================
        insights = None
        response_type = 'session_search'  # Default: no auto-insights

        if self._is_analytical_query(query):
            if len(collections) > 1:
                insights = self._generate_multi_collection_insights(query, formatted_results)
            else:
                insights = self._generate_session_insights(query, formatted_results)
            response_type = 'session_insights'

        return {
            'type': response_type,
            'query': query,
            'search_level': 'sessions',
            'collections_searched': collections,
            'insights': insights,  # None if not analytical query
            'session_results': formatted_results.get('fused_results') or formatted_results.get('results', []),
            'evidence': formatted_results,
            'filters_applied': filters,
            'enrichments': {
                'argumentation_query': is_arg_query,
                'temporal_query': is_temporal_query
            }
        }

    def _generate_multi_collection_insights(self, query: str, multi_results: Dict) -> str:
        """Generate insights from multi-collection search results with FULL session data."""
        fused_results = multi_results.get('fused_results', [])

        if not fused_results:
            return "No sessions found to generate insights from."

        from session_serializer import SessionSerializer
        serializer = SessionSerializer()

        # ENRICHMENT: Fetch full data for top fused results
        enriched_contexts = []
        for result in fused_results[:3]:  # Top 3 sessions for token efficiency
            session_id = result.get('session_device_id')
            rrf_score = result.get('rrf_score', 0)
            if session_id:
                full_context = serializer.get_llm_context(session_id, max_chars=3000)
                if full_context:
                    enriched_contexts.append(
                        f"=== SESSION {session_id} (RRF Score: {rrf_score:.4f}) ===\n{full_context}"
                    )

        if not enriched_contexts:
            return "Unable to retrieve session data for analysis."

        context = "\n\n".join(enriched_contexts)

        try:
            from openai import OpenAI
            client = OpenAI()

            prompt = f"""Analyze these top-ranked discussion sessions for "{query}":

{context}

These sessions were ranked using Reciprocal Rank Fusion across transcript content, concept map structure, and 7C quality analysis.

Based on the FULL transcripts, concept maps, and 7C quality analysis above, provide:
1. Why these sessions are relevant to the query
2. Key themes and discussion patterns across sessions
3. Quality analysis based on 7C scores and evidence
4. Specific insights with quotes from the transcripts

Use specific evidence from the data to support your analysis."""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": """You are an expert at analyzing educational discussion patterns and collaborative learning.

When providing insights:
- Include 2-3 specific quotes from the transcript data that illustrate key patterns
- Make direct observations about what the data shows (avoid filler like "It's worth noting")
- Reference specific metrics when relevant (e.g., "Session X showed 85% communication score")
- Focus on what's interesting, surprising, or actionable in these specific discussions"""},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error generating multi-collection insights: {e}")
            return f"Error generating insights: {str(e)}"

    def _extract_session_filters(self, query: str) -> Dict:
        """Extract structural/quality filters from query text."""
        filters = {}
        query_lower = query.lower()

        # Discourse type detection - only filter if type exists in data
        # Available types: 'exploratory', 'analytical'
        # Note: 'problem_solving' doesn't exist as a separate type
        if 'exploratory' in query_lower or 'exploration' in query_lower:
            filters['discourse_type'] = 'exploratory'
        elif 'analytical' in query_lower:
            filters['discourse_type'] = 'analytical'
        # Don't filter for 'problem solving' - let semantic search find relevant sessions

        # Structural quality indicators
        if 'many questions' in query_lower or 'lots of questions' in query_lower:
            filters['min_question_ratio'] = 0.15
        if 'high challenge' in query_lower or 'productive disagreement' in query_lower:
            filters['min_challenge_ratio'] = 0.1

        # 7C quality indicators
        if 'high communication' in query_lower or 'good communication' in query_lower:
            filters['min_communication_score'] = 70
        if 'effective conflict' in query_lower or 'conflict resolution' in query_lower:
            filters['min_conflict_score'] = 70
        if 'balanced participation' in query_lower or 'good contribution' in query_lower:
            filters['min_contribution_score'] = 70

        return filters

    def _generate_session_insights(self, query: str, session_results: Dict) -> str:
        """
        Generate insights from session-level search results using Ultra RAG.
        Uses query understanding, rich context, and query-specific prompts.
        """
        if not session_results.get('results'):
            return "No sessions found to generate insights from."

        # Use Ultra RAG pipeline for intelligent insights
        return self._execute_ultra_rag(query, session_results)

    def _execute_ultra_rag(self, query: str, session_results: Dict = None) -> str:
        """
        Execute the Ultra RAG pipeline for intelligent insight generation.

        ENHANCED PIPELINE (Three-Layer Response):
        1. Query Understanding - LLM-powered artifact-aware analysis
        2. Retrieval - Get sessions based on LLM's artifact recommendations
        3. Artifact Description - Build GROUND layer (what user sees in UI)
        4. Transcript Context - Build ENRICH layer (raw dialogue)
        5. LLM Synthesis - Generate with three-layer response (GROUND → ENRICH → EXTEND)
        """
        try:
            # Step 1: LLM-powered artifact-aware query understanding
            plan = self.query_understanding.analyze_with_artifacts(query)
            logger.info(f"Ultra RAG plan: intent={plan.intent}, focus={plan.focus_area}, "
                       f"artifacts={plan.primary_artifacts}, grounding={plan.grounding_strategy[:50]}...")

            # Step 2: Get sessions based on strategy
            retrieved_sessions = []  # Track for rationale
            if plan.retrieval_strategy == 'metric_first' and plan.metric_filters:
                # Get sessions by metrics, sorted by primary metric
                sort_metric = plan.metrics_needed[0] if plan.metrics_needed else None
                retrieved_sessions = self.rag.get_sessions_by_metrics(
                    plan.metric_filters,
                    n_results=5,
                    sort_by=sort_metric
                )
                session_ids = [s['session_device_id'] for s in retrieved_sessions]
            elif plan.needs_contrastive and plan.metrics_needed:
                # Get high and low metric sessions for comparison
                primary_metric = plan.metrics_needed[0]
                high_ids, low_ids = self.rag.get_contrastive_sessions(primary_metric, n_high=3, n_low=3)

                # Build contrastive context
                high_context, low_context = self.context_builder.build_contrastive_context(
                    high_ids, low_ids, plan.focus_area
                )

                # Build retrieval rationale for contrastive analysis
                contrastive_sessions = [
                    {'session_device_id': sid, 'group': 'HIGH'} for sid in high_ids
                ] + [
                    {'session_device_id': sid, 'group': 'LOW'} for sid in low_ids
                ]
                retrieval_rationale = self._format_retrieval_rationale(
                    query=query,
                    plan=plan,
                    sessions=contrastive_sessions,
                    match_reasons={
                        sid: f"HIGH {primary_metric}" for sid in high_ids
                    } | {
                        sid: f"LOW {primary_metric}" for sid in low_ids
                    }
                )

                # Generate contrastive insights
                return self.rag.generate_ultra_insights(
                    query=query,
                    focus_area=plan.focus_area,
                    session_contexts="",
                    high_context=high_context,
                    low_context=low_context,
                    retrieval_rationale=retrieval_rationale
                )
            else:
                # Use provided session results or fall back to semantic search
                if session_results and session_results.get('results'):
                    retrieved_sessions = session_results['results'][:5]
                    session_ids = [
                        r.get('session_device_id') or r.get('metadata', {}).get('session_device_id')
                        for r in retrieved_sessions
                    ]
                    session_ids = [sid for sid in session_ids if sid]
                else:
                    # Fall back to semantic search
                    semantic_results = self.rag.search_sessions_multi(query, n_results=5)
                    retrieved_sessions = semantic_results.get('fused_results', [])
                    session_ids = [
                        r.get('session_device_id')
                        for r in retrieved_sessions
                    ]

            if not session_ids:
                return "No relevant sessions found for analysis."

            # Step 3: Build THREE-LAYER context

            # LAYER 1 (GROUND): Artifact descriptions - what user sees in UI
            artifact_descriptions = []
            for sid in session_ids[:3]:  # Limit to 3 for token efficiency
                artifact_desc = self.context_builder.build_artifact_description(sid)
                if artifact_desc:
                    artifact_descriptions.append(artifact_desc)

            artifact_context = "\n\n---\n\n".join(artifact_descriptions) if artifact_descriptions else ""

            # LAYER 2 (ENRICH): Transcript context - raw dialogue for deeper analysis
            transcript_contexts = []
            if plan.needs_transcript:
                for sid in session_ids[:3]:
                    ctx = self.context_builder.build_session_context(
                        sid,
                        focus_area=plan.focus_area,
                        max_transcript_chars=3000,
                        include_edges=False  # Edges already in artifact description
                    )
                    if ctx:
                        transcript_contexts.append(ctx.transcript_text)

            transcript_context = "\n\n---\n\n".join(transcript_contexts) if transcript_contexts else ""

            if not artifact_context and not transcript_context:
                return "Unable to build context for analysis."

            # Build retrieval rationale
            retrieval_rationale = self._format_retrieval_rationale(
                query=query,
                plan=plan,
                sessions=retrieved_sessions
            )

            # Step 4: Handle speaker-specific queries
            if plan.focus_area == 'speaker' and plan.target_speaker:
                speaker_context = self.context_builder.build_speaker_context(plan.target_speaker)
                return self.rag.generate_ultra_insights(
                    query=query,
                    focus_area='speaker',
                    session_contexts="",
                    speaker_context=speaker_context,
                    speaker_name=plan.target_speaker,
                    retrieval_rationale=retrieval_rationale,
                    grounding_strategy=plan.grounding_strategy
                )

            # Step 5: Generate THREE-LAYER insights
            # Pass both artifact descriptions (GROUND) and transcript context (ENRICH)
            return self.rag.generate_ultra_insights(
                query=query,
                focus_area=plan.focus_area,
                session_contexts=transcript_context,  # Transcript for ENRICH layer
                artifact_context=artifact_context,    # Artifacts for GROUND layer
                retrieval_rationale=retrieval_rationale,
                grounding_strategy=plan.grounding_strategy
            )

        except Exception as e:
            logger.error(f"Ultra RAG execution failed: {e}", exc_info=True)
            # Fall back to legacy method
            return self._generate_session_insights_legacy(query, session_results)

    def _format_retrieval_rationale(self, query: str, plan, sessions: List[Dict],
                                     match_reasons: Dict[int, str] = None) -> str:
        """
        Format WHY these sessions were retrieved for LLM context.

        Args:
            query: Original user query
            plan: QueryPlan with intent, focus_area, metrics, strategy
            sessions: Retrieved session results
            match_reasons: Optional dict of session_id -> specific match reason

        Returns:
            Formatted retrieval rationale string
        """
        lines = [
            "## RETRIEVAL CONTEXT",
            "",
            f"**Your Task:** Answer the query: \"{query}\"",
            "",
            "**Query Understanding:**",
            f"- Intent: {plan.intent} (user wants to {plan.intent})",
            f"- Focus Area: {plan.focus_area}",
            f"- Retrieval Strategy: {plan.retrieval_strategy}",
        ]

        if plan.metric_filters:
            filters_str = ", ".join(f"{k} {op} {v}" for k, (op, v) in plan.metric_filters.items())
            lines.append(f"- Filters Applied: {filters_str}")

        if plan.metrics_needed:
            lines.append(f"- Key Metrics: {', '.join(plan.metrics_needed)}")

        if plan.needs_contrastive:
            lines.append("- Analysis Type: Contrastive (comparing high vs low performers)")

        # Reasoning chain
        if plan.reasoning_steps:
            lines.append("")
            lines.append("**Reasoning Chain:**")
            for step in plan.reasoning_steps:
                lines.append(f"  {step['step']}. {step['description']}")

        # Session-specific match reasons
        if sessions:
            lines.append("")
            lines.append(f"**Sessions Retrieved ({len(sessions)}):**")

            for session in sessions[:5]:  # Top 5
                sid = session.get('session_device_id', session.get('id', 'unknown'))
                score = session.get('hybrid_score', session.get('rrf_score', session.get('score', 0)))

                # Get specific match reason if available
                if match_reasons and sid in match_reasons:
                    reason = match_reasons[sid]
                else:
                    # Infer reason from available data
                    reason = self._infer_match_reason(session, plan)

                if isinstance(score, (int, float)):
                    lines.append(f"  - Session {sid}: {reason} (relevance: {score:.2f})")
                else:
                    lines.append(f"  - Session {sid}: {reason}")

        lines.append("")
        lines.append("**Your Response Should:**")
        lines.append("- Ground insights in the specific sessions and metrics above")
        lines.append("- Explain findings in relation to WHY these sessions were selected")
        lines.append("- Cite specific evidence (quotes, metrics) from the session data below")

        return "\n".join(lines)

    def _infer_match_reason(self, session: Dict, plan) -> str:
        """Infer why a session matched based on its metadata and the query plan."""
        reasons = []

        # Check metrics based on focus area
        if plan.focus_area == 'argumentation':
            debate_score = session.get('debate_score', session.get('argumentation', {}).get('debate_score', 0))
            if debate_score and debate_score >= 3:
                reasons.append(f"high debate_score ({debate_score})")
            challenge_count = session.get('challenge_count', session.get('argumentation', {}).get('challenge_count', 0))
            if challenge_count and challenge_count >= 2:
                reasons.append(f"{challenge_count} challenges")

        elif plan.focus_area == 'collaboration':
            comm_score = session.get('communication_score', session.get('seven_c', {}).get('communication', 0))
            if comm_score and comm_score >= 70:
                reasons.append(f"high communication ({comm_score}%)")
            climate = session.get('climate_score', session.get('seven_c', {}).get('climate', 0))
            if climate and climate >= 70:
                reasons.append(f"positive climate ({climate}%)")

        elif plan.focus_area == 'questioning':
            q_count = session.get('question_count', session.get('argumentation', {}).get('question_count', 0))
            if q_count and q_count > 0:
                reasons.append(f"{q_count} questions asked")

        elif plan.focus_area == 'evolution':
            evolution = session.get('evolution', {})
            if evolution:
                if evolution.get('analytic_evolution', 0) > 0:
                    reasons.append("positive analytic evolution")
                if evolution.get('certainty_evolution', 0) != 0:
                    reasons.append(f"certainty change: {evolution.get('certainty_evolution', 0):+.1f}")

        # Check concept map nodes
        argumentation = session.get('argumentation', {})
        node_count = argumentation.get('node_count', session.get('node_count', 0))
        if node_count and node_count > 0:
            node_types = []
            q_nodes = argumentation.get('question_count', session.get('question_nodes', 0))
            if q_nodes and q_nodes > 0:
                node_types.append(f"{q_nodes} question nodes")
            p_nodes = argumentation.get('problem_count', session.get('problem_nodes', 0))
            if p_nodes and p_nodes > 0:
                node_types.append(f"{p_nodes} problem nodes")
            if node_types:
                reasons.append(f"concept map: {', '.join(node_types)}")

        # Fallback
        if not reasons:
            if plan.retrieval_strategy == 'semantic':
                reasons.append("semantic similarity to query")
            elif plan.retrieval_strategy == 'metric_first':
                reasons.append("matched metric criteria")
            else:
                reasons.append("matched retrieval criteria")

        return "; ".join(reasons)

    def _generate_session_insights_legacy(self, query: str, session_results: Dict) -> str:
        """Legacy fallback for session insights (original implementation)."""
        if not session_results or not session_results.get('results'):
            return "No sessions found to generate insights from."

        from session_serializer import SessionSerializer
        serializer = SessionSerializer()

        enriched_contexts = []
        for result in session_results['results'][:3]:
            session_id = result.get('session_device_id') or result.get('metadata', {}).get('session_device_id')
            if session_id:
                full_context = serializer.get_llm_context(session_id, max_chars=3000)
                if full_context:
                    enriched_contexts.append(f"=== SESSION {session_id} ===\n{full_context}")

        if not enriched_contexts:
            return "Unable to retrieve session data for analysis."

        context = "\n\n".join(enriched_contexts)

        try:
            from openai import OpenAI
            client = OpenAI()

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing educational discussions."},
                    {"role": "user", "content": f"Analyze these sessions for '{query}':\n\n{context}"}
                ],
                temperature=0.7,
                max_tokens=1500
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error generating legacy insights: {e}")
            return f"Error generating insights: {str(e)}"

    def _handle_hybrid_search(self, query: str, user_devices: Optional[List[int]] = None) -> Dict:
        """
        Search both chunk-level and session-level, combining results.
        Useful for queries that benefit from both specific moments and overall patterns.
        """
        logger.info(f"Handling hybrid search (chunks + sessions): {query}")

        # Search at both levels in parallel (conceptually)
        chunk_results = self.rag.search(
            query=query,
            n_results=5,
            session_device_ids=user_devices
        )

        session_results = self.rag.search_sessions(
            query=query,
            n_results=5,
            session_device_ids=user_devices
        )

        # Combine insights if analytical query
        combined_insights = None
        if self._is_analytical_query(query):
            combined_insights = self._generate_hybrid_insights(query, chunk_results, session_results)

        return {
            'type': 'hybrid_search',
            'query': query,
            'chunk_results': chunk_results,
            'session_results': session_results,
            'combined_insights': combined_insights
        }

    def _generate_hybrid_insights(self, query: str, chunk_results: Dict, session_results: Dict) -> str:
        """Generate combined insights from both chunk and session search results with FULL session data."""
        from session_serializer import SessionSerializer
        serializer = SessionSerializer()

        chunk_context = ""
        session_context = ""

        # Chunk context - specific moments with full text
        if chunk_results.get('results'):
            chunks = []
            for i, result in enumerate(chunk_results['results'][:3], 1):
                chunks.append(f"Moment {i} (Session {result.get('metadata', {}).get('session_device_id', '?')}):\n  {result['text'][:400]}")
            chunk_context = "=== SPECIFIC MOMENTS ===\n" + "\n\n".join(chunks)

        # Session context - ENRICHED with full data
        if session_results.get('results'):
            enriched_sessions = []
            for result in session_results['results'][:2]:  # Top 2 sessions (hybrid uses both levels)
                session_id = result.get('session_device_id') or result.get('metadata', {}).get('session_device_id')
                if session_id:
                    full_context = serializer.get_llm_context(session_id, max_chars=2000)  # Smaller for hybrid
                    if full_context:
                        enriched_sessions.append(f"=== SESSION {session_id} FULL DATA ===\n{full_context}")

            if enriched_sessions:
                session_context = "\n\n".join(enriched_sessions)

        try:
            from openai import OpenAI
            client = OpenAI()

            prompt = f"""Synthesize insights from both specific discussion moments AND overall session data for: "{query}"

{chunk_context}

{session_context}

Based on both the specific moments AND the full session data (transcripts, concept maps, 7C analysis):
1. How do the specific moments relate to broader session patterns?
2. What themes emerge across both levels?
3. Key quality insights from the 7C analysis
4. Specific recommendations with evidence

Use quotes and specific data to support your synthesis."""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": """You are an expert at analyzing educational discussions. Synthesize insights from both specific moments and overall session patterns.

When providing insights:
- Include 2-3 specific quotes that illustrate key patterns
- Make direct observations (avoid filler like "It's worth noting")
- Reference specific metrics when relevant
- Focus on what's interesting, surprising, or actionable"""},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error generating hybrid insights: {e}")
            return None
    
    def _handle_temporal_analysis(self, query: str, user_devices: Optional[List[int]] = None) -> Dict:
        """Analyze patterns over time for a session"""
        import database  # Lazy import to avoid circular dependency

        logger.info(f"Handling temporal query: {query}")
        
        # Extract session/device ID
        device_match = re.search(r'device\s*(\d+)', query.lower())
        session_match = re.search(r'session\s*(\d+)', query.lower())
        
        device_id = None
        if device_match:
            device_id = int(device_match.group(1))
        elif session_match:
            sid = int(session_match.group(1))
            devices = database.get_session_devices(session_id=sid)
            if devices:
                device_id = devices[0].id
        elif user_devices and len(user_devices) > 0:
            device_id = user_devices[0]
        
        if not device_id:
            return {
                'type': 'error',
                'message': 'Please specify a session or device for temporal analysis'
            }
        
        # Get all chunks in order
        chunks = self.rag.collection.get(
            where={'session_device_id': device_id},
            limit=1000
        )
        
        if not chunks['metadatas']:
            return {
                'type': 'error',
                'message': f'No data found for device {device_id}'
            }
        
        # Create timeline
        timeline_data = []
        for i, meta in enumerate(chunks['metadatas']):
            timeline_data.append({
                'index': i,
                'time': meta.get('start_time', 0),
                'metrics': {
                    'emotional_tone': meta.get('avg_emotional_tone', 0),
                    'analytic_thinking': meta.get('avg_analytic_thinking', 0),
                    'clout': meta.get('avg_clout', 0),
                    'authenticity': meta.get('avg_authenticity', 0),
                    'certainty': meta.get('avg_certainty', 0)
                },
                'speakers': meta.get('speaker_count', 0)
            })
        
        # Sort by time
        timeline_data.sort(key=lambda x: x['time'])
        
        logger.info(f"Temporal analysis completed with {len(timeline_data)} data points")
        
        return {
            'type': 'temporal',
            'query': query,
            'device_id': device_id,
            'timeline': timeline_data,
            'summary': {
                'total_duration': timeline_data[-1]['time'] if timeline_data else 0,
                'total_chunks': len(timeline_data)
            }
        }
    
    # =========================================================================
    # HELPER METHODS FOR NATURAL LANGUAGE COMPARISONS
    # =========================================================================

    def _extract_comparison_topics(self, query: str) -> List[str]:
        """Extract topic phrases from natural language comparison query."""
        # Try simple heuristic first (fast, no API call)
        separators = [' and ', ' vs ', ' versus ', ' with ', ' to ']
        query_lower = query.lower()

        for sep in separators:
            if sep in query_lower:
                parts = query_lower.split(sep, 1)
                if len(parts) == 2:
                    topic1 = self._clean_topic(parts[0])
                    topic2 = self._clean_topic(parts[1])
                    if topic1 and topic2:
                        return [topic1, topic2]

        # Fallback: use LLM for complex queries
        return self._llm_extract_topics(query)

    def _clean_topic(self, text: str) -> str:
        """Remove comparison keywords, keep topic."""
        remove_words = ['compare', 'contrast', 'difference', 'between',
                        'the', 'discussion', 'session', 'about', 'what', 'is']
        result = text
        for word in remove_words:
            result = re.sub(rf'\b{word}\b', '', result, flags=re.IGNORECASE)
        return result.strip()

    def _llm_extract_topics(self, query: str) -> List[str]:
        """Use LLM to extract comparison topics from complex queries."""
        try:
            from openai import OpenAI
            client = OpenAI()

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{
                    "role": "user",
                    "content": f"""Extract the two topics being compared from this query:
"{query}"

Return as JSON: {{"topic1": "...", "topic2": "..."}}
Examples:
- "compare country music and nuclear" → {{"topic1": "country music", "topic2": "nuclear"}}
- "contrast the debate about politics with science" → {{"topic1": "politics", "topic2": "science"}}"""
                }],
                temperature=0,
                response_format={"type": "json_object"}
            )

            parsed = json.loads(response.choices[0].message.content)
            topics = [parsed.get('topic1', ''), parsed.get('topic2', '')]
            return [t for t in topics if t]  # Filter empty
        except Exception as e:
            logger.warning(f"LLM topic extraction failed: {e}")
            return []

    def _resolve_topic_to_session(self, topic: str) -> Optional[tuple]:
        """Search for best-matching session for a topic.

        Uses Artifact-Grounded RAG entity resolution first (session name matching),
        then falls back to semantic search if no name match found.
        """
        # Strategy 1: Try entity resolution first (session name matching)
        resolved = self.entity_resolver.resolve_session(topic)
        if resolved and resolved.get('confidence', 0) >= 0.6:
            session_device_id = resolved['session_device_id']
            session_name = resolved['name']
            logger.info(f"Entity resolver matched '{topic}' → {session_name} (confidence: {resolved['confidence']:.2f})")
            return (session_device_id, f"'{topic}' → {session_name}")

        # Strategy 2: Fall back to semantic search on transcript content
        results = self.rag.search_transcripts(topic, n_results=1)

        if results.get('results'):
            best = results['results'][0]
            session_id = best.get('session_device_id')
            # Get session name for display
            session_name = self._get_session_name(session_id)
            return (session_id, f"'{topic}' → {session_name}")
        return None

    def _get_session_name(self, session_device_id: int) -> str:
        """Get session name from session_device_id."""
        try:
            from tables.session_device import SessionDevice
            from tables.session import Session
            sd = SessionDevice.query.get(session_device_id)
            if sd:
                session = Session.query.get(sd.session_id)
                if session:
                    return session.name
            return f"Session {session_device_id}"
        except Exception:
            return f"Session {session_device_id}"

    # =========================================================================
    # ARGUMENTATION METRICS
    # =========================================================================

    def _get_argumentation_metrics(self, session_device_id: int) -> Dict:
        """Get argumentation structure metrics from concept map."""
        try:
            from tables.concept_session import ConceptSession
            from tables.concept_edge import ConceptEdge
            from tables.concept_node import ConceptNode

            # Get concept session
            concept_session = ConceptSession.query.filter_by(
                session_device_id=session_device_id
            ).first()

            if not concept_session:
                return {'has_concept_map': False}

            # Count edges by type
            edges = ConceptEdge.query.filter_by(
                concept_session_id=concept_session.id
            ).all()

            edge_counts = {}
            for edge in edges:
                edge_counts[edge.edge_type] = edge_counts.get(edge.edge_type, 0) + 1

            # Count nodes by type
            nodes = ConceptNode.query.filter_by(
                concept_session_id=concept_session.id
            ).all()

            node_counts = {}
            for node in nodes:
                node_counts[node.node_type] = node_counts.get(node.node_type, 0) + 1

            return {
                'has_concept_map': True,
                'node_count': len(nodes),
                'edge_count': len(edges),
                # Argumentation indicators
                'challenge_count': edge_counts.get('challenges', 0),
                'support_count': edge_counts.get('supports', 0),
                'builds_on_count': edge_counts.get('builds_on', 0),
                'elaboration_count': edge_counts.get('elaborates', 0),
                # Derived scores
                'debate_score': edge_counts.get('challenges', 0) + edge_counts.get('contrasts_with', 0),
                'reasoning_depth': edge_counts.get('builds_on', 0) + edge_counts.get('elaborates', 0),
                # Node type distribution
                'question_count': node_counts.get('question', 0),
                'problem_count': node_counts.get('problem', 0),
                'solution_count': node_counts.get('solution', 0),
                'idea_count': node_counts.get('idea', 0),
            }
        except Exception as e:
            logger.error(f"Error getting argumentation metrics: {e}")
            return {'has_concept_map': False, 'error': str(e)}

    def _is_argumentation_query(self, query: str) -> bool:
        """Check if query is about argumentation patterns."""
        indicators = [
            'debate', 'argument', 'challenge', 'disagree', 'counter',
            'support', 'evidence', 'reasoning', 'builds on', 'deep thinking',
            'problem solving', 'solutions', 'questions answered'
        ]
        query_lower = query.lower()
        return any(ind in query_lower for ind in indicators)

    def _get_argumentation_sort_key(self, query: str) -> str:
        """Determine which argumentation metric to sort by based on query."""
        query_lower = query.lower()

        if any(w in query_lower for w in ['debate', 'challenge', 'disagree', 'counter']):
            return 'debate_score'
        elif any(w in query_lower for w in ['deep', 'reasoning', 'builds']):
            return 'reasoning_depth'
        elif any(w in query_lower for w in ['problem', 'solution']):
            return 'solution_count'
        elif any(w in query_lower for w in ['question', 'answered']):
            return 'question_count'
        else:
            return 'edge_count'  # General argumentation strength

    # =========================================================================
    # TEMPORAL EVOLUTION METRICS
    # =========================================================================

    def _get_temporal_evolution(self, session_device_id: int) -> Dict:
        """Compute how discussion metrics evolved over time."""
        try:
            from tables.transcript import Transcript

            transcripts = Transcript.query.filter_by(
                session_device_id=session_device_id
            ).order_by(Transcript.start_time).all()

            n = len(transcripts)
            if n < 4:  # Need enough data points
                return {'has_evolution': False, 'reason': 'insufficient_data'}

            # Split into first and second half
            mid = n // 2
            first_half = transcripts[:mid]
            second_half = transcripts[mid:]

            def avg_metric(chunks, attr):
                values = [getattr(c, attr) for c in chunks if getattr(c, attr) is not None]
                return sum(values) / len(values) if values else 0

            # Compute evolution (positive = increased over time)
            return {
                'has_evolution': True,
                'analytic_evolution': round(
                    avg_metric(second_half, 'analytic_thinking_value') -
                    avg_metric(first_half, 'analytic_thinking_value'), 1
                ),
                'tone_evolution': round(
                    avg_metric(second_half, 'emotional_tone_value') -
                    avg_metric(first_half, 'emotional_tone_value'), 1
                ),
                'certainty_evolution': round(
                    avg_metric(second_half, 'certainty_value') -
                    avg_metric(first_half, 'certainty_value'), 1
                ),
                'clout_evolution': round(
                    avg_metric(second_half, 'clout_value') -
                    avg_metric(first_half, 'clout_value'), 1
                ),
                # Question ratio evolution
                'question_ratio_first': round(
                    sum(1 for t in first_half if t.question) / len(first_half), 2
                ) if first_half else 0,
                'question_ratio_second': round(
                    sum(1 for t in second_half if t.question) / len(second_half), 2
                ) if second_half else 0,
            }
        except Exception as e:
            logger.error(f"Error computing temporal evolution: {e}")
            return {'has_evolution': False, 'error': str(e)}

    def _is_temporal_evolution_query(self, query: str) -> bool:
        """Check if query is about temporal evolution."""
        indicators = [
            'evolved', 'evolution', 'over time', 'became', 'improved',
            'grew', 'increased', 'changed', 'progressed', 'developed',
            'started', 'ended', 'beginning', 'end'
        ]
        return any(ind in query.lower() for ind in indicators)

    def _get_temporal_sort_key(self, query: str) -> str:
        """Determine which evolution metric to sort by."""
        query_lower = query.lower()

        if any(w in query_lower for w in ['analytic', 'focused', 'thinking']):
            return 'analytic_evolution'
        elif any(w in query_lower for w in ['tone', 'positive', 'mood']):
            return 'tone_evolution'
        elif any(w in query_lower for w in ['certain', 'confident']):
            return 'certainty_evolution'
        else:
            return 'analytic_evolution'  # Default

    def get_suggested_queries(self, context: Optional[Dict] = None) -> List[Dict]:
        """Get contextual suggested queries - organized by granularity level"""

        base_suggestions = [
            {'category': 'Specific Moments (Chunks)', 'granularity': 'chunks', 'queries': [
                'What was said about pH levels?',
                'Find when students discussed catalysts',
                'Show me moments of analytical thinking'
            ]},
            {'category': 'Discussion Patterns (Sessions)', 'granularity': 'sessions', 'queries': [
                'Find sessions with strong argumentation',
                'Sessions with high communication quality',
                'Discussions showing hypothesis testing',
                'Find problem-solving discussions'
            ]},
            {'category': 'Collaborative Quality (7C)', 'granularity': 'sessions', 'queries': [
                'Sessions with productive disagreement',
                'Find groups with balanced participation',
                'Discussions with effective conflict resolution'
            ]},
            {'category': 'Speaker Engagement (Speakers)', 'granularity': 'speakers', 'queries': [
                'How did Lex typically engage in discussions?',
                'Which speakers ask the most questions?',
                'Compare speaker engagement styles',
                'Find speakers with high analytical thinking'
            ]},
            {'category': 'Analysis & Insights', 'granularity': 'auto', 'queries': [
                'What patterns lead to productive discussions?',
                'Why does engagement vary across sessions?',
                'How do successful collaborations differ?'
            ]},
            {'category': 'Comparison', 'granularity': 'chunks', 'queries': [
                'Compare device 448 and device 447',
                'Show differences between sessions'
            ]}
        ]
        
        if context and context.get('session_device_id'):
            device_id = context['session_device_id']
            base_suggestions.append({
                'category': 'Current Session',
                'granularity': 'sessions',
                'queries': [
                    f'Find sessions similar to device {device_id}',
                    f'Analyze device {device_id} progression over time',
                    f'What made device {device_id} unique?',
                    f'Sessions with similar argumentation to {device_id}'
                ]
            })

        return base_suggestions