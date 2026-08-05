"""
Graph Traversal Tools for BLINC Agent V2

Tools for querying the concept map graph structure.
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
def get_node_neighbors(
    node_id: str,
    edge_types: Optional[List[str]] = None,
    direction: str = "both"
) -> Dict[str, Any]:
    """
    Get all concept nodes directly connected to a given node.

    Returns connected nodes with their relationship types and directions.
    Use this to explore what concepts are related to a specific idea.

    Args:
        node_id: The concept node ID to find neighbors for
        edge_types: Optional list of edge types to filter
                   Options: 'builds_on', 'challenges', 'supports', 'contrasts_with',
                           'elaborates', 'causes', 'leads_to', 'enables', 'solves'
        direction: Direction of edges - 'incoming', 'outgoing', or 'both'

    Returns:
        Dict with 'neighbors' list containing connected nodes with relationship info
    """
    try:
        import database as db_helper

        neighbors = db_helper.get_node_neighbors(
            node_id=node_id,
            edge_types=edge_types,
            direction=direction
        )

        return {
            "node_id": node_id,
            "neighbor_count": len(neighbors),
            "neighbors": neighbors,
            "direction": direction,
            "edge_types_filter": edge_types
        }
    except Exception as e:
        logger.error(f"Error getting node neighbors: {e}")
        return {"error": str(e), "neighbors": []}


@tool
def get_concept_path(
    source_node_id: str,
    target_node_id: str,
    max_depth: int = 4
) -> Dict[str, Any]:
    """
    Find the shortest path between two concept nodes in the same session.

    Returns the sequence of nodes and edge types connecting them.
    Use this to understand how two ideas are connected through intermediate concepts.

    Args:
        source_node_id: The starting concept node ID
        target_node_id: The target concept node ID
        max_depth: Maximum path length to search (default 4)

    Returns:
        Dict with 'path_found' boolean and 'path' list showing the connection
    """
    try:
        import database as db_helper

        path = db_helper.get_concept_path(
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            max_depth=max_depth
        )

        if path is None:
            return {
                "path_found": False,
                "source_node_id": source_node_id,
                "target_node_id": target_node_id,
                "message": "No path found between the concepts within the depth limit"
            }

        return {
            "path_found": True,
            "path_length": len(path),
            "path": path,
            "source_node_id": source_node_id,
            "target_node_id": target_node_id
        }
    except Exception as e:
        logger.error(f"Error finding concept path: {e}")
        return {"error": str(e), "path_found": False}


@tool
def get_causal_chain(
    node_id: str,
    direction: str = "forward",
    max_depth: int = 5
) -> Dict[str, Any]:
    """
    Extract causal or logical chains starting from a concept.

    Follows edges like 'causes', 'leads_to', 'enables', 'solves'.
    Use this to trace cause-effect relationships or problem-solution chains.

    Args:
        node_id: The starting concept node ID
        direction: 'forward' to follow effects, 'backward' to find causes
        max_depth: Maximum chain length to follow (default 5)

    Returns:
        Dict with 'chain' list showing the causal sequence
    """
    try:
        import database as db_helper

        chain = db_helper.get_causal_chain(
            node_id=node_id,
            direction=direction,
            max_depth=max_depth
        )

        return {
            "node_id": node_id,
            "chain_length": len(chain) if chain else 0,
            "chain": chain or [],
            "direction": direction
        }
    except Exception as e:
        logger.error(f"Error extracting causal chain: {e}")
        return {"error": str(e), "chain": []}


@tool
def get_cluster_subgraph(
    cluster_id: int,
    include_edges: bool = True
) -> Dict[str, Any]:
    """
    Get all nodes and edges within a specific concept cluster (theme).

    Returns the complete subgraph for a thematic cluster.
    Use this to understand the structure of a specific theme in discussion.

    Args:
        cluster_id: The cluster ID to get subgraph for
        include_edges: Whether to include edge data (default True)

    Returns:
        Dict with 'nodes' and 'edges' lists for the cluster
    """
    try:
        import database as db_helper

        subgraph = db_helper.get_cluster_subgraph(
            cluster_id=cluster_id,
            include_edges=include_edges
        )

        return {
            "cluster_id": cluster_id,
            "node_count": len(subgraph.get('nodes', [])),
            "edge_count": len(subgraph.get('edges', [])) if include_edges else 0,
            "nodes": subgraph.get('nodes', []),
            "edges": subgraph.get('edges', []) if include_edges else []
        }
    except Exception as e:
        logger.error(f"Error getting cluster subgraph: {e}")
        return {"error": str(e), "nodes": [], "edges": []}


@tool
def get_speaker_contribution_graph(
    session_device_id: int,
    speaker_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get concept nodes and edges attributed to a specific speaker or all speakers.

    Shows how each speaker contributed to the concept map.
    Use this to analyze individual speaker contributions to the discussion.

    Args:
        session_device_id: The session to analyze
        speaker_id: Optional specific speaker ID to filter

    Returns:
        Dict with contribution data per speaker including nodes, edges, and patterns
    """
    try:
        import database as db_helper

        contributions = db_helper.get_speaker_contribution_graph(
            session_device_id=session_device_id,
            speaker_id=speaker_id
        )

        return {
            "session_device_id": session_device_id,
            "speaker_filter": speaker_id,
            "contributions": contributions
        }
    except Exception as e:
        logger.error(f"Error getting speaker contributions: {e}")
        return {"error": str(e), "contributions": {}}


@tool
def get_full_concept_map(
    session_device_id: int,
    include_clusters: bool = True
) -> Dict[str, Any]:
    """
    Get the complete concept map structure for a session.

    Returns all nodes, edges, and clusters. Use this when you need
    the full picture of how ideas connect in a discussion.

    Args:
        session_device_id: The session device ID to get concept map for
        include_clusters: Whether to include cluster assignments (default True)

    Returns:
        Dict with 'nodes', 'edges', and optionally 'clusters' lists
    """
    try:
        from tables.concept_session import ConceptSession
        import database as db_helper

        # Get concept session
        concept_session = ConceptSession.query.filter_by(
            session_device_id=session_device_id
        ).first()

        if not concept_session:
            return {
                "error": f"No concept map found for session {session_device_id}",
                "nodes": [],
                "edges": []
            }

        # Get all nodes and edges
        nodes = db_helper.get_concept_nodes(
            concept_session_id=concept_session.id
        )
        edges = db_helper.get_concept_edges(
            concept_session_id=concept_session.id
        )

        result = {
            "session_device_id": session_device_id,
            "discourse_type": concept_session.discourse_type,
            "generation_status": concept_session.generation_status,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "nodes": [n.json() for n in nodes],
            "edges": [e.json() for e in edges]
        }

        # Add clusters if requested
        if include_clusters and concept_session.clusters:
            result["clusters"] = [c.json() for c in concept_session.clusters]
            result["cluster_count"] = len(concept_session.clusters)

        return result

    except Exception as e:
        logger.error(f"Error getting concept map: {e}")
        return {"error": str(e), "nodes": [], "edges": []}
