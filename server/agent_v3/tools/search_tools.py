"""
Search Tools for BLINC Agent V3

Clean search tool implementations using existing RAG infrastructure.
"""

import logging
import sys
import os
from typing import Dict, Any, List, Optional

# Add server directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logger = logging.getLogger(__name__)


def _get_rag_service():
    """Lazy import of RAG service to avoid circular imports."""
    from rag_service import RAGService
    return RAGService()


def search_transcripts(
    query: str,
    session_ids: Optional[List[int]] = None,
    speaker: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Search discussion transcripts for specific content.

    Args:
        query: Search query
        session_ids: Optional list of session IDs to filter
        speaker: Optional speaker name to filter results (post-filter)
        limit: Maximum results to return

    Returns:
        Search results with text, speaker, session, and timestamp
    """
    logger.info(f"Searching transcripts: '{query}' (sessions={session_ids}, speaker={speaker}, limit={limit})")

    try:
        rag = _get_rag_service()

        # Use semantic chunks if available, else fall back to 30-sec chunks
        collection = rag.semantic_chunks_collection
        if collection.count() == 0:
            logger.info("Semantic chunks empty, falling back to 30-sec chunk collection")
            collection = rag.collection  # Legacy 30-sec chunks

        results = collection.query(
            query_texts=[query],
            n_results=limit,
            where={"session_device_id": {"$in": session_ids}} if session_ids else None
        )

        # Format results
        formatted = []
        if results and results.get('documents'):
            for i, doc in enumerate(results['documents'][0]):
                metadata = results['metadatas'][0][i] if results.get('metadatas') else {}
                distance = results['distances'][0][i] if results.get('distances') else 0

                result_speaker = metadata.get('speakers', '') or metadata.get('speaker', '')

                # Post-filter by speaker if specified
                if speaker:
                    speaker_lower = speaker.lower()
                    result_speaker_lower = result_speaker.lower() if result_speaker else ''
                    if speaker_lower not in result_speaker_lower:
                        continue  # Skip non-matching speakers

                formatted.append({
                    "text": doc,
                    "session_device_id": metadata.get('session_device_id'),
                    "speaker": result_speaker,
                    "start_time": metadata.get('start_time'),
                    "end_time": metadata.get('end_time'),
                    "distance": distance,
                    "relevance": 1 - distance if distance < 1 else 0
                })

        return {
            "tool_name": "search_transcripts",
            "query_used": query,
            "speaker_filter": speaker,
            "result_count": len(formatted),
            "results": formatted,
            "is_relevant": len(formatted) > 0 and formatted[0].get('distance', 1) < 0.7
        }

    except Exception as e:
        logger.error(f"Transcript search error: {e}")
        return {
            "tool_name": "search_transcripts",
            "query_used": query,
            "result_count": 0,
            "results": [],
            "error": str(e),
            "is_relevant": False
        }


def search_sessions(
    query: str,
    limit: int = 5
) -> Dict[str, Any]:
    """
    Search for sessions by topic or characteristics.

    Args:
        query: What to search for
        limit: Maximum sessions to return

    Returns:
        Session summaries with topics and metrics
    """
    logger.info(f"Searching sessions: '{query}' (limit={limit})")

    try:
        rag = _get_rag_service()

        # Search session transcripts collection
        results = rag.transcript_collection.query(
            query_texts=[query],
            n_results=limit
        )

        # Format results
        formatted = []
        if results and results.get('documents'):
            for i, doc in enumerate(results['documents'][0]):
                metadata = results['metadatas'][0][i] if results.get('metadatas') else {}
                distance = results['distances'][0][i] if results.get('distances') else 0

                formatted.append({
                    "session_device_id": metadata.get('session_device_id'),
                    "session_name": metadata.get('session_name', f"Session {metadata.get('session_device_id')}"),
                    "summary": doc[:500],
                    "topics": metadata.get('topics', []),
                    "participant_count": metadata.get('participant_count', 0),
                    "duration": metadata.get('duration'),
                    "distance": distance,
                    "relevance": 1 - distance if distance < 1 else 0
                })

        return {
            "tool_name": "search_sessions",
            "query_used": query,
            "result_count": len(formatted),
            "results": formatted,
            "is_relevant": len(formatted) > 0
        }

    except Exception as e:
        logger.error(f"Session search error: {e}")
        return {
            "tool_name": "search_sessions",
            "query_used": query,
            "result_count": 0,
            "results": [],
            "error": str(e),
            "is_relevant": False
        }


def search_concepts(
    query: str = "",
    session_ids: Optional[List[int]] = None,
    concept_types: Optional[List[str]] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Search concept nodes in the discussion graphs.

    Args:
        query: Concept to search for (optional - if empty, returns top concepts for session)
        session_ids: Optional session filter
        concept_types: Optional types filter (question, idea, hypothesis, etc.)
        limit: Maximum results

    Returns:
        Concept nodes with type, speaker, and connections
    """
    # Default to generic query if empty
    if not query or query.strip() == "":
        query = "main ideas concepts themes"

    logger.info(f"Searching concepts: '{query}' (sessions={session_ids}, types={concept_types})")

    try:
        rag = _get_rag_service()

        # Build where filter
        where_filter = None
        conditions = []
        if session_ids:
            conditions.append({"session_device_id": {"$in": session_ids}})
        if concept_types:
            conditions.append({"node_type": {"$in": concept_types}})

        if len(conditions) == 1:
            where_filter = conditions[0]
        elif len(conditions) > 1:
            where_filter = {"$and": conditions}

        # Search concept nodes collection
        results = rag.concept_nodes_collection.query(
            query_texts=[query],
            n_results=limit,
            where=where_filter
        )

        # Format results
        formatted = []
        if results and results.get('documents'):
            for i, doc in enumerate(results['documents'][0]):
                metadata = results['metadatas'][0][i] if results.get('metadatas') else {}
                distance = results['distances'][0][i] if results.get('distances') else 0

                formatted.append({
                    "node_id": metadata.get('node_id'),
                    "text": doc,
                    "node_type": metadata.get('node_type', 'concept'),
                    "session_device_id": metadata.get('session_device_id'),
                    "speaker": metadata.get('speaker_alias', ''),
                    "cluster_name": metadata.get('cluster_name', ''),
                    "neighbor_count": metadata.get('neighbor_count', 0),
                    "distance": distance,
                    "relevance": 1 - distance if distance < 1 else 0
                })

        return {
            "tool_name": "search_concepts",
            "query_used": query,
            "result_count": len(formatted),
            "results": formatted,
            "is_relevant": len(formatted) > 0 and formatted[0].get('distance', 1) < 0.7
        }

    except Exception as e:
        logger.error(f"Concept search error: {e}")
        return {
            "tool_name": "search_concepts",
            "query_used": query,
            "result_count": 0,
            "results": [],
            "error": str(e),
            "is_relevant": False
        }


def search_communities(
    query: str,
    limit: int = 5
) -> Dict[str, Any]:
    """
    Search thematic communities (concept clusters) across sessions.

    Args:
        query: Theme or topic to search for
        limit: Maximum communities to return

    Returns:
        Community summaries with key concepts
    """
    logger.info(f"Searching communities: '{query}' (limit={limit})")

    try:
        rag = _get_rag_service()

        # Search concept clusters collection
        results = rag.concept_clusters_collection.query(
            query_texts=[query],
            n_results=limit
        )

        # Format results
        formatted = []
        if results and results.get('documents'):
            for i, doc in enumerate(results['documents'][0]):
                metadata = results['metadatas'][0][i] if results.get('metadatas') else {}
                distance = results['distances'][0][i] if results.get('distances') else 0

                formatted.append({
                    "cluster_id": metadata.get('cluster_id'),
                    "cluster_name": metadata.get('cluster_name'),
                    "summary": doc[:500],
                    "session_device_id": metadata.get('session_device_id'),
                    "node_count": metadata.get('node_count', 0),
                    "speakers": metadata.get('speakers', ''),
                    "distance": distance,
                    "relevance": 1 - distance if distance < 1 else 0
                })

        return {
            "tool_name": "search_communities",
            "query_used": query,
            "result_count": len(formatted),
            "results": formatted,
            "is_relevant": len(formatted) > 0
        }

    except Exception as e:
        logger.error(f"Community search error: {e}")
        return {
            "tool_name": "search_communities",
            "query_used": query,
            "result_count": 0,
            "results": [],
            "error": str(e),
            "is_relevant": False
        }
