"""
Search Tools for BLINC Agent V2

Adapted from existing tools with LangChain @tool decorator.
"""

import sys
import os
import logging
from typing import List, Dict, Optional, Any

from langchain_core.tools import tool

# Add server directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logger = logging.getLogger(__name__)


@tool
def search_transcript_chunks(
    query: str,
    session_device_ids: Optional[List[int]] = None,
    n_results: int = 5,
    speaker: Optional[str] = None
) -> Dict[str, Any]:
    """
    Search semantically-chunked transcript segments by topic or content.

    Returns specific discussion moments with timestamps, speakers, and context.
    Use this to find what was said about a specific topic.

    Args:
        query: Search query - what to look for in transcripts
        session_device_ids: Optional list of session device IDs to filter
        n_results: Maximum number of results to return (default 5)
        speaker: Optional speaker name to filter by

    Returns:
        Dict with 'results' containing matched transcript chunks with:
        - text: The transcript text
        - session_device_id: Which session it's from
        - speaker: Who said it
        - start_time, end_time: Timestamps
        - distance: Semantic similarity score
    """
    try:
        from graph_rag import GraphIndexer
        indexer = GraphIndexer()

        results = indexer.search_semantic_chunks(
            query=query,
            session_device_ids=session_device_ids,
            n_results=n_results,
            speaker=speaker
        )

        return {
            "query": query,
            "result_count": len(results),
            "results": results,
            "session_filter": session_device_ids,
            "speaker_filter": speaker
        }
    except Exception as e:
        logger.error(f"Error searching transcript chunks: {e}")
        return {"error": str(e), "results": []}


@tool
def search_concept_nodes(
    query: str,
    session_device_ids: Optional[List[int]] = None,
    node_types: Optional[List[str]] = None,
    n_results: int = 10
) -> Dict[str, Any]:
    """
    Search individual concept nodes (ideas, questions, hypotheses, etc.) by semantic similarity.

    Returns specific concepts with speaker attribution. Use this to find
    specific ideas or questions about a topic.

    Args:
        query: The concept to search for
        session_device_ids: Optional list of session device IDs to filter
        node_types: Optional list of node types to filter
                   Options: 'idea', 'question', 'hypothesis', 'problem', 'solution', 'evidence', 'claim'
        n_results: Maximum number of results to return (default 10)

    Returns:
        Dict with 'results' containing matched concept nodes with:
        - node_text: The concept text
        - node_type: Type of concept
        - speaker: Who contributed it
        - session_device_id: Which session
        - cluster_name: Theme it belongs to
    """
    try:
        from graph_rag import GraphIndexer
        indexer = GraphIndexer()

        results = indexer.search_concept_nodes(
            query=query,
            session_device_ids=session_device_ids,
            node_types=node_types,
            n_results=n_results
        )

        return {
            "query": query,
            "result_count": len(results),
            "results": results,
            "session_filter": session_device_ids,
            "type_filter": node_types
        }
    except Exception as e:
        logger.error(f"Error searching concept nodes: {e}")
        return {"error": str(e), "results": []}


@tool
def search_concept_clusters(
    query: str,
    session_device_ids: Optional[List[int]] = None,
    n_results: int = 5
) -> Dict[str, Any]:
    """
    Search concept clusters (themes) for high-level topic matching.

    Returns thematic clusters with constituent concepts. Use this to find
    sessions that discussed a particular theme or to understand what topics
    were covered.

    Args:
        query: The theme to search for
        session_device_ids: Optional list of session device IDs to filter
        n_results: Maximum number of results to return (default 5)

    Returns:
        Dict with 'results' containing matched clusters with:
        - cluster_name: Name of the theme
        - cluster_summary: Summary of the theme
        - session_device_id: Which session
        - node_count: How many concepts in this theme
        - key_concepts: Sample concepts in this cluster
    """
    try:
        from graph_rag import GraphIndexer
        indexer = GraphIndexer()

        results = indexer.search_concept_clusters(
            query=query,
            session_device_ids=session_device_ids,
            n_results=n_results
        )

        return {
            "query": query,
            "result_count": len(results),
            "results": results,
            "session_filter": session_device_ids
        }
    except Exception as e:
        logger.error(f"Error searching concept clusters: {e}")
        return {"error": str(e), "results": []}
