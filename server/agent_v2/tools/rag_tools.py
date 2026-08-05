"""
RAG Service Tools for BLINC Agent V2

Exposes the sophisticated RAG features that the legacy agent was NOT using:
- RRF fusion across collections
- Hybrid search (metric + semantic)
- Metric-first retrieval
- Contrastive analysis
- THREE-LAYER insights generation
- Speaker profile search
- Structural similarity search
"""

import sys
import os
import logging
from typing import List, Dict, Optional, Any, Tuple

from langchain_core.tools import tool

# Add server directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logger = logging.getLogger(__name__)

# Lazy initialization to avoid circular imports
_rag_service = None

def get_rag_service():
    """Get or create RAG service instance."""
    global _rag_service
    if _rag_service is None:
        from rag_service import RAGService
        _rag_service = RAGService()
    return _rag_service


@tool
def search_sessions_multi(
    query: str,
    collections: Optional[List[str]] = None,
    n_results: int = 5,
    session_device_ids: Optional[List[int]] = None
) -> Dict[str, Any]:
    """
    Search multiple session collections with RRF (Reciprocal Rank Fusion).

    This is the most powerful search tool - it searches across transcripts,
    concept maps, and 7C analyses simultaneously, then fuses results using
    RRF for better ranking than any single collection.

    Args:
        query: Natural language search query
        collections: Which collections to search. Options: 'transcripts', 'concepts', 'seven_c'.
                    If None, searches all three.
        n_results: Number of results to return (default 5)
        session_device_ids: Optional list of session IDs to filter to

    Returns:
        Dict with 'fused_results' (ranked by RRF score) and 'results_by_collection'

    Use for:
        - Broad session-level queries ("sessions about dinosaurs")
        - Multi-dimensional search ("sessions with good debate about evolution")
        - When you need the best overall ranking
    """
    try:
        rag = get_rag_service()
        result = rag.search_sessions_multi(
            query=query,
            collections=collections or ['transcripts', 'concepts', 'seven_c'],
            n_results=n_results,
            session_device_ids=session_device_ids
        )
        return result
    except Exception as e:
        logger.error(f"search_sessions_multi error: {e}")
        return {"error": str(e), "fused_results": []}


@tool
def hybrid_session_search(
    query: str,
    metric_filters: Dict[str, Tuple[str, Any]],
    sort_metric: Optional[str] = None,
    n_results: int = 5,
    metric_weight: float = 0.4,
    semantic_weight: float = 0.6
) -> List[Dict[str, Any]]:
    """
    Hybrid search combining metric filtering with semantic search.

    First filters sessions by quantitative metrics (debate score, 7C scores, etc.),
    then ranks by semantic similarity to the query. Combines both signals for
    optimal results.

    Args:
        query: Semantic search query
        metric_filters: Dict of filters like {'debate_score': ('>=', 3), 'communication_score': ('>=', 70)}
                       Supported operators: '>=', '>', '<=', '<', '=='
        sort_metric: Metric to prioritize in ranking
        n_results: Number of results to return
        metric_weight: Weight for metric-based ranking (0-1)
        semantic_weight: Weight for semantic ranking (0-1)

    Available metrics:
        - debate_score: Number of challenges + contrasts
        - reasoning_depth: Number of builds_on + elaborates edges
        - challenge_count, support_count: Specific edge types
        - node_count, edge_count: Graph size
        - question_count, problem_count, solution_count: Node types
        - communication_score, climate_score, contribution_score: 7C scores (0-100)

    Returns:
        List of sessions with hybrid_score, metric_score, semantic_score, and metrics

    Use for:
        - "Sessions with high debate about evolution"
        - "Good collaboration (7C > 70) discussing dinosaurs"
        - Any query combining qualitative AND quantitative criteria
    """
    try:
        rag = get_rag_service()
        result = rag.hybrid_session_search(
            query=query,
            metric_filters=metric_filters,
            sort_metric=sort_metric,
            n_results=n_results,
            metric_weight=metric_weight,
            semantic_weight=semantic_weight
        )
        return result
    except Exception as e:
        logger.error(f"hybrid_session_search error: {e}")
        return [{"error": str(e)}]


@tool
def get_sessions_by_metrics(
    metric_filters: Dict[str, Tuple[str, Any]],
    n_results: int = 10,
    sort_by: Optional[str] = None,
    descending: bool = True
) -> List[Dict[str, Any]]:
    """
    Get sessions filtered and sorted purely by metrics (database-first).

    This is a metric-FIRST approach - no semantic search involved.
    Use when you need sessions with specific quantitative characteristics.

    Args:
        metric_filters: Dict of filters like {'debate_score': ('>=', 3)}
                       Pass {} for no filters (get all sessions with metrics)
        n_results: Maximum results to return
        sort_by: Metric to sort by (e.g., 'debate_score', 'communication_score')
        descending: Sort order (True = highest first)

    Available metrics:
        Argumentation metrics (from concept maps):
        - debate_score: challenges + contrasts
        - reasoning_depth: builds_on + elaborates
        - challenge_count, support_count
        - node_count, edge_count
        - question_count, problem_count, solution_count

        7C collaboration metrics:
        - communication_score (0-100)
        - climate_score (0-100)
        - contribution_score (0-100)
        - conflict_score (0-100)
        - constructive_score (0-100)

    Returns:
        List of session dicts with all metrics

    Use for:
        - "Most argumentative sessions"
        - "Sessions with low conflict scores"
        - "Sessions with most questions asked"
        - Any purely metric-based ranking
    """
    try:
        rag = get_rag_service()
        result = rag.get_sessions_by_metrics(
            metric_filters=metric_filters,
            n_results=n_results,
            sort_by=sort_by,
            descending=descending
        )
        return result
    except Exception as e:
        logger.error(f"get_sessions_by_metrics error: {e}")
        return [{"error": str(e)}]


@tool
def get_contrastive_sessions(
    metric_name: str,
    n_high: int = 3,
    n_low: int = 3
) -> Dict[str, List[int]]:
    """
    Get sessions with highest and lowest values for a metric.

    Use for contrastive analysis - understanding WHY some sessions
    score high and others score low on a metric.

    Args:
        metric_name: The metric to analyze (e.g., 'debate_score', 'communication_score')
        n_high: Number of high-scoring sessions to return
        n_low: Number of low-scoring sessions to return

    Returns:
        Dict with 'high_sessions' and 'low_sessions' lists of session_device_ids

    Use for:
        - "Why do some sessions have more debate?"
        - "What makes a high vs low collaboration score?"
        - Contrastive explanations
    """
    try:
        rag = get_rag_service()
        high_sessions, low_sessions = rag.get_contrastive_sessions(
            metric_name=metric_name,
            n_high=n_high,
            n_low=n_low
        )
        return {
            "high_sessions": high_sessions,
            "low_sessions": low_sessions
        }
    except Exception as e:
        logger.error(f"get_contrastive_sessions error: {e}")
        return {"error": str(e), "high_sessions": [], "low_sessions": []}


@tool
def generate_ultra_insights(
    query: str,
    focus_area: str,
    session_contexts: str,
    artifact_context: str = "",
    retrieval_rationale: str = ""
) -> str:
    """
    Generate insights using the THREE-LAYER response model.

    The three layers are:
    1. GROUND: Reference artifacts (concept maps, 7C scores) - what user sees in UI
    2. ENRICH: Cite transcripts with quotes and timestamps - add depth
    3. EXTEND: Provide original insight - patterns artifacts might miss

    Args:
        query: The user's original question
        focus_area: Analysis focus - 'argumentation', 'collaboration', 'speaker', 'evolution'
        session_contexts: Transcript text to cite for the ENRICH layer
        artifact_context: Description of artifacts for GROUND layer (concept map structure, 7C scores)
        retrieval_rationale: Explanation of WHY these sessions were retrieved (shows reasoning)

    Focus areas:
        - argumentation: Debate, challenges, reasoning depth
        - collaboration: 7C scores, teamwork, communication
        - speaker: Individual speaker patterns and contributions
        - evolution: How discussion developed over time

    Returns:
        Generated insight text following THREE-LAYER format

    Use for:
        - Analytical queries ("Why does session X have high debate?")
        - Deep analysis requiring synthesis
        - When you need insights grounded in artifacts the user can see
    """
    try:
        rag = get_rag_service()
        result = rag.generate_ultra_insights(
            query=query,
            focus_area=focus_area,
            session_contexts=session_contexts,
            artifact_context=artifact_context,
            retrieval_rationale=retrieval_rationale
        )
        return result
    except Exception as e:
        logger.error(f"generate_ultra_insights error: {e}")
        return f"Error generating insights: {str(e)}"


@tool
def search_speakers(
    query: str,
    n_results: int = 5,
    filters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Search cross-session speaker profiles by engagement patterns.

    Finds speakers across ALL sessions based on their participation patterns,
    not just within a single session.

    Args:
        query: Natural language query describing speaker characteristics
               Examples: "speakers who ask many questions", "analytical speakers"
        n_results: Number of speaker results to return
        filters: Optional filters like:
                - min_session_count: Minimum sessions participated
                - min_question_count: Minimum questions asked

    Returns:
        Dict with 'results' containing speaker profiles with metadata

    Use for:
        - "Who asks the most questions?"
        - "Find speakers with analytical style"
        - Cross-session speaker analysis
    """
    try:
        rag = get_rag_service()
        result = rag.search_speakers(
            query=query,
            n_results=n_results,
            filters=filters
        )
        return result
    except Exception as e:
        logger.error(f"search_speakers error: {e}")
        return {"error": str(e), "results": []}


@tool
def find_similar_sessions(
    session_device_id: int,
    n_results: int = 5
) -> Dict[str, Any]:
    """
    Find sessions structurally similar to a reference session.

    Uses concept map embeddings to find sessions with similar
    discussion structure, not just similar topics.

    Args:
        session_device_id: The reference session to find similar ones to
        n_results: Number of similar sessions to return

    Returns:
        Dict with 'similar_sessions' list containing sessions with similarity scores

    Use for:
        - "Find sessions similar to session 23"
        - "What other sessions have this discussion pattern?"
        - Discovering related discussions
    """
    try:
        rag = get_rag_service()
        result = rag.find_similar_sessions(
            session_device_id=session_device_id,
            n_results=n_results
        )
        return result
    except Exception as e:
        logger.error(f"find_similar_sessions error: {e}")
        return {"error": str(e), "similar_sessions": []}


@tool
def search_chunks(
    query: str,
    n_results: int = 5,
    session_device_ids: Optional[List[int]] = None,
    min_emotional_tone: Optional[float] = None,
    min_analytic_thinking: Optional[float] = None
) -> Dict[str, Any]:
    """
    Search 30-second transcript chunks for specific content.

    This is the most granular search - finds specific moments
    in discussions with precise timestamps.

    Args:
        query: What to search for
        n_results: Number of chunks to return
        session_device_ids: Filter to specific sessions
        min_emotional_tone: Filter by LIWC emotional tone score
        min_analytic_thinking: Filter by LIWC analytic thinking score

    Returns:
        Dict with 'results' containing chunks with text, timestamps, speakers

    Use for:
        - "What was said about T-Rex?"
        - Finding specific quotes or moments
        - Fine-grained content retrieval
    """
    try:
        rag = get_rag_service()
        # Handle single session ID or list
        if isinstance(session_device_ids, int):
            session_device_ids = [session_device_ids]

        result = rag.search(
            query=query,
            n_results=n_results,
            session_device_ids=session_device_ids,
            min_emotional_tone=min_emotional_tone,
            min_analytic_thinking=min_analytic_thinking
        )
        return result
    except Exception as e:
        logger.error(f"search_chunks error: {e}")
        return {"error": str(e), "results": []}
