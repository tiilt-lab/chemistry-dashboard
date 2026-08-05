"""
Graph Navigation Tools for BLINC Agent V3

Tools for exploring and navigating concept map graphs.
"""

import logging
import sys
import os
from typing import Dict, Any, List, Optional

# Add server directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logger = logging.getLogger(__name__)


def _get_db_connection():
    """Get direct MySQL connection."""
    import mysql.connector
    return mysql.connector.connect(
        host='localhost',
        user='vagrant',
        password='vagrant',
        database='discussion_capture'
    )


def explore_concepts(
    concept_id: str,
    direction: str = "both",
    depth: int = 2
) -> Dict[str, Any]:
    """
    Explore concepts connected to a given concept.

    Args:
        concept_id: The concept node ID to explore from
        direction: 'outgoing', 'incoming', or 'both'
        depth: How many hops to explore (1-3)

    Returns:
        Connected concepts with relationship types
    """
    logger.info(f"Exploring concepts from: {concept_id} (direction={direction}, depth={depth})")

    try:
        connection = _get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Get the starting node
        cursor.execute("""
            SELECT cn.*, s.alias as speaker_alias, cc.cluster_name
            FROM concept_node cn
            LEFT JOIN speaker s ON s.id = cn.speaker_id
            LEFT JOIN cluster_node_mapping cnm ON cnm.node_id = cn.id
            LEFT JOIN concept_cluster cc ON cc.id = cnm.cluster_id
            WHERE cn.id = %s
        """, (concept_id,))
        start_node = cursor.fetchone()

        if not start_node:
            cursor.close()
            connection.close()
            return {
                "tool_name": "explore_concepts",
                "error": f"Concept {concept_id} not found",
                "result_count": 0,
                "results": [],
                "is_relevant": False
            }

        # Get connected nodes
        neighbors = []

        if direction in ("outgoing", "both"):
            cursor.execute("""
                SELECT
                    ce.edge_type,
                    'outgoing' as direction,
                    cn.id, cn.text, cn.node_type,
                    s.alias as speaker_alias,
                    cc.cluster_name
                FROM concept_edge ce
                JOIN concept_node cn ON cn.id = ce.target_node_id
                LEFT JOIN speaker s ON s.id = cn.speaker_id
                LEFT JOIN cluster_node_mapping cnm ON cnm.node_id = cn.id
                LEFT JOIN concept_cluster cc ON cc.id = cnm.cluster_id
                WHERE ce.source_node_id = %s
            """, (concept_id,))
            neighbors.extend(cursor.fetchall())

        if direction in ("incoming", "both"):
            cursor.execute("""
                SELECT
                    ce.edge_type,
                    'incoming' as direction,
                    cn.id, cn.text, cn.node_type,
                    s.alias as speaker_alias,
                    cc.cluster_name
                FROM concept_edge ce
                JOIN concept_node cn ON cn.id = ce.source_node_id
                LEFT JOIN speaker s ON s.id = cn.speaker_id
                LEFT JOIN cluster_node_mapping cnm ON cnm.node_id = cn.id
                LEFT JOIN concept_cluster cc ON cc.id = cnm.cluster_id
                WHERE ce.target_node_id = %s
            """, (concept_id,))
            neighbors.extend(cursor.fetchall())

        cursor.close()
        connection.close()

        # Format results
        result = {
            "start_concept": {
                "id": start_node['id'],
                "text": start_node['text'],
                "type": start_node['node_type'],
                "speaker": start_node.get('speaker_alias'),
                "theme": start_node.get('cluster_name')
            },
            "connections": [
                {
                    "id": n['id'],
                    "text": n['text'],
                    "type": n['node_type'],
                    "speaker": n.get('speaker_alias'),
                    "theme": n.get('cluster_name'),
                    "relationship": n['edge_type'],
                    "direction": n['direction']
                }
                for n in neighbors
            ],
            "connection_count": len(neighbors)
        }

        return {
            "tool_name": "explore_concepts",
            "result_count": len(neighbors),
            "results": [result],
            "is_relevant": True
        }

    except Exception as e:
        logger.error(f"Concept exploration error: {e}")
        return {
            "tool_name": "explore_concepts",
            "error": str(e),
            "result_count": 0,
            "results": [],
            "is_relevant": False
        }


def find_reasoning_path(
    source_id: str,
    target_id: str,
    max_depth: int = 4
) -> Dict[str, Any]:
    """
    Find the path between two concepts.

    Args:
        source_id: Starting concept ID
        target_id: Target concept ID
        max_depth: Maximum path length

    Returns:
        Path of concepts and relationships
    """
    logger.info(f"Finding path from {source_id} to {target_id}")

    try:
        connection = _get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # BFS to find shortest path
        visited = {source_id}
        queue = [(source_id, [])]
        path_found = None

        while queue and not path_found:
            current_id, path = queue.pop(0)

            if len(path) >= max_depth:
                continue

            # Get outgoing edges
            cursor.execute("""
                SELECT
                    ce.target_node_id,
                    ce.edge_type,
                    cn.text,
                    cn.node_type
                FROM concept_edge ce
                JOIN concept_node cn ON cn.id = ce.target_node_id
                WHERE ce.source_node_id = %s
            """, (current_id,))
            edges = cursor.fetchall()

            for edge in edges:
                next_id = edge['target_node_id']

                if next_id == target_id:
                    path_found = path + [{
                        "from_id": current_id,
                        "to_id": next_id,
                        "to_text": edge['text'],
                        "to_type": edge['node_type'],
                        "relationship": edge['edge_type']
                    }]
                    break

                if next_id not in visited:
                    visited.add(next_id)
                    new_path = path + [{
                        "from_id": current_id,
                        "to_id": next_id,
                        "to_text": edge['text'],
                        "to_type": edge['node_type'],
                        "relationship": edge['edge_type']
                    }]
                    queue.append((next_id, new_path))

        cursor.close()
        connection.close()

        if path_found:
            return {
                "tool_name": "find_reasoning_path",
                "result_count": 1,
                "results": [{
                    "path_found": True,
                    "path_length": len(path_found),
                    "path": path_found,
                    "source_id": source_id,
                    "target_id": target_id
                }],
                "is_relevant": True
            }
        else:
            return {
                "tool_name": "find_reasoning_path",
                "result_count": 0,
                "results": [{
                    "path_found": False,
                    "message": f"No path found within {max_depth} hops",
                    "source_id": source_id,
                    "target_id": target_id
                }],
                "is_relevant": True
            }

    except Exception as e:
        logger.error(f"Path finding error: {e}")
        return {
            "tool_name": "find_reasoning_path",
            "error": str(e),
            "result_count": 0,
            "results": [],
            "is_relevant": False
        }


def get_concept_map(
    session_id: int,
    include_edges: bool = True
) -> Dict[str, Any]:
    """
    Get the full concept map for a session.

    Args:
        session_id: The session device ID
        include_edges: Whether to include edge data

    Returns:
        Complete concept map structure
    """
    logger.info(f"Getting concept map for session: {session_id}")

    try:
        connection = _get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Get concept session
        cursor.execute("""
            SELECT id, discourse_type, generation_status
            FROM concept_session
            WHERE session_device_id = %s
        """, (session_id,))
        concept_session = cursor.fetchone()

        if not concept_session:
            cursor.close()
            connection.close()
            return {
                "tool_name": "get_concept_map",
                "error": f"No concept map found for session {session_id}",
                "result_count": 0,
                "results": [],
                "is_relevant": False
            }

        # Get nodes
        cursor.execute("""
            SELECT
                cn.id, cn.text, cn.node_type, cn.timestamp,
                s.alias as speaker_alias,
                cc.cluster_name
            FROM concept_node cn
            LEFT JOIN speaker s ON s.id = cn.speaker_id
            LEFT JOIN cluster_node_mapping cnm ON cnm.node_id = cn.id
            LEFT JOIN concept_cluster cc ON cc.id = cnm.cluster_id
            WHERE cn.concept_session_id = %s
        """, (concept_session['id'],))
        nodes = cursor.fetchall()

        # Get edges if requested
        edges = []
        if include_edges:
            cursor.execute("""
                SELECT source_node_id, target_node_id, edge_type
                FROM concept_edge
                WHERE concept_session_id = %s
            """, (concept_session['id'],))
            edges = cursor.fetchall()

        # Get clusters
        cursor.execute("""
            SELECT id, cluster_name, summary, node_count
            FROM concept_cluster
            WHERE concept_session_id = %s
            ORDER BY cluster_order
        """, (concept_session['id'],))
        clusters = cursor.fetchall()

        cursor.close()
        connection.close()

        result = {
            "session_device_id": session_id,
            "discourse_type": concept_session['discourse_type'],
            "node_count": len(nodes),
            "edge_count": len(edges),
            "cluster_count": len(clusters),
            "nodes": nodes,
            "edges": edges if include_edges else [],
            "clusters": clusters
        }

        return {
            "tool_name": "get_concept_map",
            "result_count": 1,
            "results": [result],
            "is_relevant": True
        }

    except Exception as e:
        logger.error(f"Concept map retrieval error: {e}")
        return {
            "tool_name": "get_concept_map",
            "error": str(e),
            "result_count": 0,
            "results": [],
            "is_relevant": False
        }
