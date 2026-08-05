# server/rag_routes.py - Unified Implementation

from flask import Blueprint, request, jsonify
from rag_query_parser import QueryParser
import logging

logger = logging.getLogger(__name__)

# Create Blueprint
rag_api = Blueprint('rag_api', __name__)

# Initialize query parser (contains shared RAGService instance)
query_parser = QueryParser()
# Use the RAGService from QueryParser to avoid duplicate initialization
rag_service = query_parser.rag


@rag_api.route('/api/v1/rag/search', methods=['POST'])
def unified_search():
    """
    Unified search endpoint - handles all query types intelligently with multi-granularity

    Request body:
    {
        "query": "string",
        "granularity": "auto" | "chunks" | "sessions" | "both",  // Optional
        "filter_to_user": false,  // Optional: filter to user's sessions
        "n_results": 5  // Optional
    }

    Response varies by query type but always includes:
    {
        "query": "original query",
        "query_type": "retrieval|insights|session_search|session_insights|hybrid_search|...",
        "search_level": "chunks" | "sessions" | "both",  // NEW: indicates granularity used
        "results": [...] or null,           // For chunk-level retrieval
        "session_results": [...] or null,   // NEW: For session-level results
        "insights": "..." or null,          // Auto-generated for analytical queries
        "comparison": {...} or null,        // For comparative queries
        "similar": {...} or null,           // For similarity queries
        "timeline": {...} or null,          // For temporal queries
        "filters_applied": {...} or null,   // NEW: Session filters that were used
        "total_found": N,
        "error": "..." or null
    }
    """
    try:
        data = request.get_json()
        query = data.get('query', '')
        granularity = data.get('granularity', 'auto')  # NEW: granularity parameter
        filter_to_user = data.get('filter_to_user', False)

        if not query:
            return jsonify({"error": "Query is required"}), 400

        # Validate granularity
        if granularity not in ['auto', 'chunks', 'sessions', 'speakers', 'both']:
            return jsonify({"error": "granularity must be 'auto', 'chunks', 'sessions', 'speakers', or 'both'"}), 400

        # Get user's session devices if filtering
        user_devices = None
        if filter_to_user:
            # Filter to sessions owned by the current user
            from flask import session as flask_session
            from tables.session_device import SessionDevice
            from tables.session import Session

            user = flask_session.get('user')
            if user:
                # Get sessions owned by this user
                user_sessions = Session.query.filter_by(owner_id=user['id']).all()
                session_ids = [s.id for s in user_sessions]
                # Get session_devices for those sessions
                session_devices = SessionDevice.query.filter(
                    SessionDevice.session_id.in_(session_ids)
                ).all() if session_ids else []
                user_devices = [sd.id for sd in session_devices]

            if not user_devices:
                # No sessions found for this user
                return jsonify({
                    "query": query,
                    "query_type": "no_results",
                    "search_level": "sessions",
                    "results": None,
                    "session_results": [],
                    "total_found": 0,
                    "error": "No sessions found for your account"
                })

        # Use QueryParser to handle the query intelligently with granularity
        result = query_parser.parse_and_execute(query, user_devices, granularity)

        # Normalize response format for frontend consistency
        response = {
            "query": query,
            "query_type": result.get('type', 'unknown'),
            "search_level": result.get('search_level', 'chunks'),
            "results": None,
            "session_results": None,
            "speaker_results": None,  # Speaker-level results
            "speaker_comparison": None,  # Speaker comparison profiles
            "insights": None,
            "comparison": None,
            "similar": None,
            "timeline": None,
            "filters_applied": None,
            "total_found": 0,
            "error": None
        }

        query_type = result.get('type')

        if query_type == 'error':
            response['error'] = result.get('message', 'Unknown error')
            response['example'] = result.get('example')

        elif query_type == 'no_results':
            # No relevant content found - return helpful message instead of garbage
            response['query_type'] = 'no_results'
            response['message'] = result.get('message', 'No relevant content found.')
            response['suggestion'] = result.get('suggestion')
            response['total_found'] = 0

        elif query_type in ['topic_search', 'pattern_analysis']:
            # Simple retrieval (chunk-level) - return results
            search_results = result.get('results', {})
            response['results'] = search_results.get('results', [])
            response['total_found'] = search_results.get('total_found', 0)
            response['search_level'] = 'chunks'

        elif query_type == 'insights':
            # Analytical query (chunk-level) - insights auto-generated
            search_results = result.get('evidence', {})
            response['results'] = search_results.get('results', [])
            response['total_found'] = search_results.get('total_found', 0)
            response['insights'] = result.get('insights')
            response['search_level'] = 'chunks'

        elif query_type == 'session_search':
            # Session-level search results (no auto-insights)
            response['session_results'] = result.get('session_results', [])
            evidence = result.get('evidence', {})
            response['total_found'] = evidence.get('total_found', len(response['session_results']))
            response['filters_applied'] = result.get('filters_applied')
            response['search_level'] = 'sessions'

        elif query_type == 'session_insights':
            # Session-level insights (with auto-generated insights)
            response['session_results'] = result.get('session_results', [])
            evidence = result.get('evidence', {})
            response['total_found'] = evidence.get('total_found', len(response['session_results']))
            response['insights'] = result.get('insights')
            response['filters_applied'] = result.get('filters_applied')
            response['search_level'] = 'sessions'

        elif query_type == 'hybrid_search':
            # NEW: Both chunk and session results
            chunk_results = result.get('chunk_results', {})
            session_results = result.get('session_results', {})
            response['results'] = chunk_results.get('results', [])
            response['session_results'] = session_results.get('results', [])
            response['total_found'] = chunk_results.get('total_found', 0) + session_results.get('total_found', 0)
            response['insights'] = result.get('combined_insights')
            response['search_level'] = 'both'

        elif query_type == 'comparative':
            # Comparison between sessions
            response['comparison'] = result.get('comparisons', {})

        elif query_type in ['similar', 'similar_sessions']:
            # Similar sessions (supports both chunk and session level)
            response['similar'] = result.get('results', {})
            response['search_level'] = result.get('search_level', 'chunks')

        elif query_type == 'speaker_search':
            # Speaker-level search results
            response['speaker_results'] = result.get('speaker_results', [])
            response['total_found'] = result.get('total_found', 0)
            response['search_level'] = 'speakers'
            if result.get('message'):
                response['message'] = result.get('message')

        elif query_type == 'speaker_insights':
            # Speaker-level insights
            response['speaker_results'] = result.get('speaker_results', [])
            response['total_found'] = result.get('total_found', 0)
            response['insights'] = result.get('insights')
            response['search_level'] = 'speakers'

        elif query_type == 'speaker_comparison':
            # Speaker comparison (comparing two speakers' engagement styles)
            speaker_profiles = result.get('speakers', {})
            response['speaker_comparison'] = speaker_profiles
            response['insights'] = result.get('insights')
            response['total_found'] = len(speaker_profiles)
            response['search_level'] = 'speakers'

        elif query_type == 'temporal':
            # Timeline data
            response['timeline'] = result.get('timeline', [])
            response['summary'] = result.get('summary', {})

        elif query_type == 'metric_chunks':
            # Metric-based chunk search (e.g., "moments of analytical thinking")
            response['results'] = result.get('results', [])
            response['total_found'] = result.get('total_found', 0)
            response['search_level'] = 'chunks'
            response['metric_field'] = result.get('metric_field')
            response['artifacts_referenced'] = result.get('artifacts_referenced', [])

        elif query_type == 'chunk_search':
            # Legacy chunk search
            response['results'] = result.get('results', [])
            response['total_found'] = result.get('total_found', 0)
            response['search_level'] = 'chunks'

        elif query_type == 'session_comparison':
            # Session comparison (from entity-resolved comparison)
            response['comparison'] = result.get('comparison', {})
            response['total_found'] = 2

        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Unified search error: {e}", exc_info=True)
        return jsonify({
            "query": query if 'query' in locals() else '',
            "query_type": "error",
            "results": None,
            "session_results": None,
            "speaker_results": None,
            "speaker_comparison": None,
            "insights": None,
            "comparison": None,
            "similar": None,
            "timeline": None,
            "total_found": 0,
            "error": str(e)
        }), 500


def _build_retrieval_rationale_from_results(query: str, search_results: dict) -> str:
    """Build retrieval rationale to explain WHY these results were shown."""
    # Extract metadata from search results
    total_found = search_results.get('total_found', 0)
    search_level = search_results.get('search_level', 'unknown')

    # Determine what types of results we have
    has_chunks = bool(search_results.get('results'))
    has_sessions = bool(search_results.get('session_results'))
    has_speakers = bool(search_results.get('speaker_results'))

    result_types = []
    if has_chunks:
        result_types.append(f"{len(search_results.get('results', []))} specific moments")
    if has_sessions:
        result_types.append(f"{len(search_results.get('session_results', []))} sessions")
    if has_speakers:
        result_types.append(f"{len(search_results.get('speaker_results', []))} speaker profiles")

    # Get session IDs mentioned
    session_ids = set()
    # Use 'or []' pattern because .get() returns None when key exists with value None (from JS null)
    for result in (search_results.get('results') or []) + (search_results.get('session_results') or []):
        sid = result.get('session_device_id') or result.get('metadata', {}).get('session_device_id')
        if sid:
            session_ids.add(str(sid))

    rationale = f"""## RETRIEVAL CONTEXT

**User Query:** "{query}"
**Total Results Found:** {total_found}
**Result Types:** {', '.join(result_types) if result_types else 'mixed results'}
**Sessions Included:** {', '.join(sorted(session_ids)[:10]) if session_ids else 'various'}

These results were retrieved based on semantic similarity to the user's query.
When generating insights:
1. Explain findings in relation to the query "{query}"
2. Reference specific sessions and time points when available
3. Acknowledge that these results represent discussions most relevant to the query"""

    return rationale


@rag_api.route('/api/v1/rag/insights', methods=['POST'])
def generate_insights():
    """
    Manual insights generation endpoint

    Request body:
    {
        "query": "string",
        "search_results": {
            "query": "...",
            "results": [...],
            "total_found": N
        }
    }
    """
    try:
        data = request.get_json()

        query = data.get('query', '')
        search_results = data.get('search_results')

        if not query or not search_results:
            return jsonify({"error": "Query and search_results are required"}), 400

        # Build retrieval rationale to explain WHY these results were shown
        retrieval_rationale = _build_retrieval_rationale_from_results(query, search_results)

        insights = rag_service.generate_insights(query, search_results, retrieval_rationale=retrieval_rationale)

        return jsonify({
            "query": query,
            "insights": insights
        })
        
    except Exception as e:
        logger.error(f"Insights generation error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@rag_api.route('/api/v1/rag/stats', methods=['GET'])
def get_stats():
    """Get collection statistics for chunk, session, and speaker collections"""
    try:
        stats = rag_service.get_all_collection_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return jsonify({"error": str(e)}), 500


@rag_api.route('/api/v1/rag/suggestions', methods=['GET'])
def get_suggestions():
    """Get suggested queries for UI"""
    try:
        return jsonify({
            "suggestions": query_parser.get_suggested_queries()
        })
    except Exception as e:
        logger.error(f"Suggestions error: {e}")
        return jsonify({"error": str(e)}), 500


@rag_api.route('/api/v1/rag/index-session/<int:session_device_id>', methods=['POST'])
def index_session(session_device_id):
    """
    Manually trigger session-level indexing for a specific session.

    This is useful for re-indexing after concept map or 7C analysis updates.
    Normally called automatically after clustering or 7C completion.
    """
    from session_serializer import SessionSerializer

    try:
        serializer = SessionSerializer()

        # Try to serialize with concept map data
        serialized = serializer.serialize_for_embedding(session_device_id)

        # Fallback to transcript-based if no concept map
        if not serialized:
            serialized = serializer.generate_fallback_summary(session_device_id)

        if not serialized:
            return jsonify({
                "success": False,
                "message": f"No data available to index for session_device {session_device_id}"
            }), 404

        success = rag_service.index_session(session_device_id, serialized)

        return jsonify({
            "success": success,
            "session_device_id": session_device_id,
            "has_concept_map": serialized['metadata'].get('has_concept_map', False),
            "has_seven_cs": serialized['metadata'].get('has_seven_cs', False),
            "node_count": serialized['metadata'].get('node_count', 0),
            "cluster_count": serialized['metadata'].get('cluster_count', 0)
        })

    except Exception as e:
        logger.error(f"Session indexing error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@rag_api.route('/api/v1/rag/session/<int:session_device_id>', methods=['DELETE'])
def delete_session_index(session_device_id):
    """Delete a session's index from the collection"""
    try:
        success = rag_service.delete_session_index(session_device_id)
        return jsonify({
            "success": success,
            "session_device_id": session_device_id
        })
    except Exception as e:
        logger.error(f"Session deletion error: {e}")
        return jsonify({"error": str(e)}), 500


# ==================== SPEAKER ENDPOINTS ====================

@rag_api.route('/api/v1/rag/speakers', methods=['GET'])
def list_speakers():
    """
    List all indexed speakers with their metadata.

    Response:
    {
        "speakers": [
            {
                "alias": "Lex",
                "session_count": 5,
                "transcript_count": 45,
                "avg_clout": 72.5,
                "question_count": 23,
                ...
            }
        ],
        "total": 13
    }
    """
    try:
        # Get speaker collection stats
        stats = rag_service.get_speaker_collection_stats()

        # Get all speaker documents for metadata
        collection = rag_service.speaker_collection
        all_speakers = collection.get(include=['metadatas'])

        speakers = []
        if all_speakers and all_speakers.get('ids'):
            for i, speaker_id in enumerate(all_speakers['ids']):
                metadata = all_speakers['metadatas'][i] if all_speakers.get('metadatas') else {}
                speakers.append({
                    'alias': metadata.get('speaker_alias', speaker_id),
                    'session_count': metadata.get('session_count', 0),
                    'transcript_count': metadata.get('transcript_count', 0),
                    'concept_count': metadata.get('concept_count', 0),
                    'question_count': metadata.get('question_count', 0),
                    'total_word_count': metadata.get('total_word_count', 0),
                    'avg_emotional_tone': metadata.get('avg_emotional_tone', 0),
                    'avg_analytic_thinking': metadata.get('avg_analytic_thinking', 0),
                    'avg_clout': metadata.get('avg_clout', 0),
                    'indexed_at': metadata.get('indexed_at', '')
                })

        return jsonify({
            "speakers": speakers,
            "total": len(speakers)
        })

    except Exception as e:
        logger.error(f"List speakers error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@rag_api.route('/api/v1/rag/index-speaker/<speaker_alias>', methods=['POST'])
def index_speaker(speaker_alias):
    """
    Manually trigger speaker-level indexing for a specific speaker.

    This indexes the speaker's cross-session profile for semantic search.
    Normally called automatically after sessions are created/updated.
    """
    from speaker_serializer import SpeakerSerializer

    try:
        serializer = SpeakerSerializer()
        serialized = serializer.serialize_speaker(speaker_alias)

        if not serialized:
            return jsonify({
                "success": False,
                "message": f"No data found for speaker: {speaker_alias}"
            }), 404

        success = rag_service.index_speaker(speaker_alias, serialized)

        return jsonify({
            "success": success,
            "speaker_alias": speaker_alias,
            "session_count": serialized['metadata'].get('session_count', 0),
            "transcript_count": serialized['metadata'].get('transcript_count', 0),
            "concept_count": serialized['metadata'].get('concept_count', 0)
        })

    except Exception as e:
        logger.error(f"Speaker indexing error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@rag_api.route('/api/v1/rag/speaker/<speaker_alias>', methods=['DELETE'])
def delete_speaker_index(speaker_alias):
    """Delete a speaker's index from the collection"""
    try:
        success = rag_service.delete_speaker_index(speaker_alias)
        return jsonify({
            "success": success,
            "speaker_alias": speaker_alias
        })
    except Exception as e:
        logger.error(f"Speaker deletion error: {e}")
        return jsonify({"error": str(e)}), 500


@rag_api.route('/api/v1/rag/index-all-speakers', methods=['POST'])
def index_all_speakers():
    """
    Batch index all speakers in the database.

    This is useful for initial setup or re-indexing.
    """
    from speaker_serializer import SpeakerSerializer, get_all_speaker_aliases

    try:
        serializer = SpeakerSerializer()
        aliases = get_all_speaker_aliases()

        results = {
            "indexed": [],
            "failed": [],
            "skipped": []
        }

        for alias in aliases:
            try:
                serialized = serializer.serialize_speaker(alias)
                if serialized:
                    success = rag_service.index_speaker(alias, serialized)
                    if success:
                        results["indexed"].append(alias)
                    else:
                        results["failed"].append(alias)
                else:
                    results["skipped"].append(alias)
            except Exception as e:
                logger.error(f"Error indexing speaker {alias}: {e}")
                results["failed"].append(alias)

        return jsonify({
            "success": True,
            "total_speakers": len(aliases),
            "indexed_count": len(results["indexed"]),
            "failed_count": len(results["failed"]),
            "skipped_count": len(results["skipped"]),
            "results": results
        })

    except Exception as e:
        logger.error(f"Batch speaker indexing error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500