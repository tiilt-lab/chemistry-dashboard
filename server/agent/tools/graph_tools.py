"""
Graph Traversal Tools

Tools for querying the concept map graph structure stored in MySQL.
These tools enable structural queries without embeddings.
"""

import logging
from typing import Dict, List, Optional

from .base import BaseTool, ToolResult, ParameterSpec, ToolCategory

logger = logging.getLogger(__name__)


class GetNodeNeighborsTool(BaseTool):
    """Get all concepts directly connected to a node."""

    name = "get_node_neighbors"
    description = (
        "Get all concept nodes directly connected to a given node. "
        "Returns connected nodes with their relationship types and directions. "
        "Use this to explore what concepts are related to a specific idea."
    )
    category = ToolCategory.GRAPH
    parameters = {
        "node_id": ParameterSpec(
            name="node_id",
            type="str",
            description="The concept node ID to find neighbors for",
            required=True
        ),
        "edge_types": ParameterSpec(
            name="edge_types",
            type="list",
            description="Optional list of edge types to filter (e.g., ['builds_on', 'challenges'])",
            required=False,
            default=None
        ),
        "direction": ParameterSpec(
            name="direction",
            type="str",
            description="Direction of edges: 'incoming', 'outgoing', or 'both'",
            required=False,
            default="both",
            enum=["incoming", "outgoing", "both"]
        )
    }

    def execute(self, node_id: str, edge_types: List[str] = None,
                direction: str = "both") -> ToolResult:
        """Execute the get_node_neighbors query."""
        import database as db_helper

        try:
            neighbors = db_helper.get_node_neighbors(
                node_id=node_id,
                edge_types=edge_types,
                direction=direction
            )

            return ToolResult(
                success=True,
                data={
                    "node_id": node_id,
                    "neighbor_count": len(neighbors),
                    "neighbors": neighbors
                },
                metadata={
                    "direction": direction,
                    "edge_types_filter": edge_types
                }
            )
        except Exception as e:
            logger.error(f"Error getting node neighbors: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=str(e)
            )


class GetConceptPathTool(BaseTool):
    """Find the shortest path between two concepts."""

    name = "get_concept_path"
    description = (
        "Find the shortest path between two concept nodes in the same session. "
        "Returns the sequence of nodes and edge types connecting them. "
        "Use this to understand how two ideas are connected through intermediate concepts."
    )
    category = ToolCategory.GRAPH
    parameters = {
        "source_node_id": ParameterSpec(
            name="source_node_id",
            type="str",
            description="The starting concept node ID",
            required=True
        ),
        "target_node_id": ParameterSpec(
            name="target_node_id",
            type="str",
            description="The target concept node ID",
            required=True
        ),
        "max_depth": ParameterSpec(
            name="max_depth",
            type="int",
            description="Maximum path length to search",
            required=False,
            default=4
        )
    }

    def execute(self, source_node_id: str, target_node_id: str,
                max_depth: int = 4) -> ToolResult:
        """Execute the path finding query."""
        import database as db_helper

        try:
            path = db_helper.get_concept_path(
                source_node_id=source_node_id,
                target_node_id=target_node_id,
                max_depth=max_depth
            )

            if path is None:
                return ToolResult(
                    success=True,
                    data={
                        "path_found": False,
                        "source_node_id": source_node_id,
                        "target_node_id": target_node_id,
                        "message": "No path found between the concepts within the depth limit"
                    }
                )

            return ToolResult(
                success=True,
                data={
                    "path_found": True,
                    "path_length": len(path),
                    "path": path
                },
                metadata={
                    "source_node_id": source_node_id,
                    "target_node_id": target_node_id,
                    "max_depth": max_depth
                }
            )
        except Exception as e:
            logger.error(f"Error finding concept path: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=str(e)
            )


class GetCausalChainTool(BaseTool):
    """Extract causal/logical chains from a concept."""

    name = "get_causal_chain"
    description = (
        "Extract causal or logical chains starting from a concept. "
        "Follows edges like 'causes', 'leads_to', 'enables', 'solves'. "
        "Use this to trace cause-effect relationships or problem-solution chains."
    )
    category = ToolCategory.GRAPH
    parameters = {
        "node_id": ParameterSpec(
            name="node_id",
            type="str",
            description="The starting concept node ID",
            required=True
        ),
        "direction": ParameterSpec(
            name="direction",
            type="str",
            description="'forward' to follow effects, 'backward' to find causes",
            required=False,
            default="forward",
            enum=["forward", "backward"]
        ),
        "max_depth": ParameterSpec(
            name="max_depth",
            type="int",
            description="Maximum chain length to follow",
            required=False,
            default=5
        )
    }

    def execute(self, node_id: str, direction: str = "forward",
                max_depth: int = 5) -> ToolResult:
        """Execute the causal chain extraction."""
        import database as db_helper

        try:
            chain = db_helper.get_causal_chain(
                node_id=node_id,
                direction=direction,
                max_depth=max_depth
            )

            return ToolResult(
                success=True,
                data={
                    "start_node_id": node_id,
                    "chain_length": len(chain),
                    "chain": chain,
                    "direction": direction
                },
                metadata={
                    "max_depth": max_depth,
                    "causal_types": ["causes", "leads_to", "enables", "solves", "answers"]
                }
            )
        except Exception as e:
            logger.error(f"Error extracting causal chain: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=str(e)
            )


class GetClusterSubgraphTool(BaseTool):
    """Get all nodes and edges within a thematic cluster."""

    name = "get_cluster_subgraph"
    description = (
        "Get the complete subgraph of a thematic cluster including all nodes and internal edges. "
        "Clusters represent coherent themes in the discussion. "
        "Use this to explore all concepts within a specific theme or topic area."
    )
    category = ToolCategory.GRAPH
    parameters = {
        "cluster_id": ParameterSpec(
            name="cluster_id",
            type="int",
            description="The cluster ID to extract",
            required=True
        ),
        "include_cross_cluster_edges": ParameterSpec(
            name="include_cross_cluster_edges",
            type="bool",
            description="Whether to include edges connecting to nodes in other clusters",
            required=False,
            default=False
        )
    }

    def execute(self, cluster_id: int,
                include_cross_cluster_edges: bool = False) -> ToolResult:
        """Execute the cluster subgraph extraction."""
        import database as db_helper

        try:
            result = db_helper.get_cluster_subgraph(
                cluster_id=cluster_id,
                include_cross_cluster_edges=include_cross_cluster_edges
            )

            if result is None:
                return ToolResult(
                    success=False,
                    data=None,
                    error=f"Cluster {cluster_id} not found"
                )

            return ToolResult(
                success=True,
                data=result,
                metadata={
                    "cluster_id": cluster_id,
                    "include_cross_cluster_edges": include_cross_cluster_edges
                }
            )
        except Exception as e:
            logger.error(f"Error getting cluster subgraph: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=str(e)
            )


class GetSpeakerContributionGraphTool(BaseTool):
    """Get the subgraph of concepts contributed by a speaker."""

    name = "get_speaker_contribution_graph"
    description = (
        "Get all concept nodes contributed by a specific speaker and the edges connecting them. "
        "Shows what ideas a speaker introduced and how they connect to other concepts. "
        "Use this to analyze individual student contributions to the discussion."
    )
    category = ToolCategory.GRAPH
    parameters = {
        "session_device_id": ParameterSpec(
            name="session_device_id",
            type="int",
            description="The session device ID to analyze",
            required=True
        ),
        "speaker_id": ParameterSpec(
            name="speaker_id",
            type="int",
            description="The speaker ID to get contributions for",
            required=True
        )
    }

    def execute(self, session_device_id: int, speaker_id: int) -> ToolResult:
        """Execute the speaker contribution graph query."""
        import database as db_helper

        try:
            result = db_helper.get_speaker_contribution_graph(
                session_device_id=session_device_id,
                speaker_id=speaker_id
            )

            return ToolResult(
                success=True,
                data=result,
                metadata={
                    "session_device_id": session_device_id,
                    "speaker_id": speaker_id
                }
            )
        except Exception as e:
            logger.error(f"Error getting speaker contribution graph: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=str(e)
            )


class TraceConceptToSourceTool(BaseTool):
    """Find the transcript turns that generated a concept."""

    name = "trace_concept_to_source"
    description = (
        "Find the original transcript turns that led to a concept being generated. "
        "Uses the concept's timestamp to find nearby transcripts and matches by content. "
        "Use this to ground concepts in the actual discussion and verify interpretations."
    )
    category = ToolCategory.GRAPH
    parameters = {
        "node_id": ParameterSpec(
            name="node_id",
            type="str",
            description="The concept node ID to trace",
            required=True
        )
    }

    def execute(self, node_id: str) -> ToolResult:
        """Execute the concept tracing query."""
        import database as db_helper

        try:
            result = db_helper.trace_concept_to_source(node_id=node_id)

            if result is None:
                return ToolResult(
                    success=False,
                    data=None,
                    error=f"Node {node_id} not found"
                )

            return ToolResult(
                success=True,
                data=result,
                metadata={
                    "node_id": node_id,
                    "transcript_count": len(result.get("transcripts", [])),
                    "has_best_match": result.get("best_match") is not None
                }
            )
        except Exception as e:
            logger.error(f"Error tracing concept to source: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=str(e)
            )
