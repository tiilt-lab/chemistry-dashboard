"""
Community Detection for Graph RAG V2

Uses the Leiden algorithm to detect communities (clusters of
densely connected concepts) in the discussion graphs.

This enables GraphRAG-style global search where we can answer
questions about themes across the entire corpus.
"""

import logging
from typing import Dict, List, Any, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


class CommunityDetector:
    """
    Detects communities in concept graphs using the Leiden algorithm.

    Communities are groups of concepts that are densely connected,
    representing coherent themes or topics in the discussion.
    """

    def __init__(self, resolution: float = 1.0):
        """
        Initialize the community detector.

        Args:
            resolution: Leiden resolution parameter (higher = more communities)
        """
        self.resolution = resolution

    def detect_communities(
        self,
        nodes: List[Dict],
        edges: List[Dict]
    ) -> List[Dict[str, Any]]:
        """
        Detect communities in a concept graph.

        Args:
            nodes: List of concept nodes with 'id' and 'text'
            edges: List of edges with 'source_node_id' and 'target_node_id'

        Returns:
            List of communities, each with:
            - community_id: Unique identifier
            - node_ids: List of node IDs in this community
            - size: Number of nodes
            - density: Internal edge density
        """
        if not nodes:
            return []

        try:
            # Try to use leidenalg if available
            communities = self._leiden_detect(nodes, edges)
        except ImportError:
            logger.warning("leidenalg not available, using fallback Louvain")
            communities = self._louvain_detect(nodes, edges)
        except Exception as e:
            logger.error(f"Community detection error: {e}")
            # Fallback: treat existing clusters as communities
            communities = self._use_existing_clusters(nodes)

        logger.info(f"Detected {len(communities)} communities from {len(nodes)} nodes")
        return communities

    def _leiden_detect(
        self,
        nodes: List[Dict],
        edges: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Use Leiden algorithm for community detection."""
        import igraph as ig
        import leidenalg

        # Build igraph graph
        g = ig.Graph(directed=False)

        # Add nodes
        node_id_to_idx = {}
        for i, node in enumerate(nodes):
            g.add_vertex(name=node['id'])
            node_id_to_idx[node['id']] = i

        # Add edges
        for edge in edges:
            src = edge.get('source_node_id')
            tgt = edge.get('target_node_id')
            if src in node_id_to_idx and tgt in node_id_to_idx:
                try:
                    g.add_edge(node_id_to_idx[src], node_id_to_idx[tgt])
                except:
                    pass  # Skip duplicate edges

        # Run Leiden
        partition = leidenalg.find_partition(
            g,
            leidenalg.ModularityVertexPartition,
            resolution_parameter=self.resolution
        )

        # Extract communities
        communities = []
        for i, community_nodes in enumerate(partition):
            if len(community_nodes) > 0:
                node_ids = [nodes[idx]['id'] for idx in community_nodes]
                communities.append({
                    'community_id': f"community_{i}",
                    'node_ids': node_ids,
                    'size': len(node_ids),
                    'density': self._compute_density(node_ids, edges)
                })

        return communities

    def _louvain_detect(
        self,
        nodes: List[Dict],
        edges: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Fallback Louvain algorithm using networkx."""
        try:
            import networkx as nx
            from networkx.algorithms import community as nx_community
        except ImportError:
            return self._use_existing_clusters(nodes)

        # Build networkx graph
        G = nx.Graph()

        for node in nodes:
            G.add_node(node['id'])

        for edge in edges:
            src = edge.get('source_node_id')
            tgt = edge.get('target_node_id')
            if src in G and tgt in G:
                G.add_edge(src, tgt)

        # Run Louvain
        try:
            partition = nx_community.louvain_communities(
                G,
                resolution=self.resolution,
                seed=42
            )
        except:
            # Very old networkx version fallback
            partition = list(nx.connected_components(G))

        # Extract communities
        communities = []
        for i, community_nodes in enumerate(partition):
            node_ids = list(community_nodes)
            communities.append({
                'community_id': f"community_{i}",
                'node_ids': node_ids,
                'size': len(node_ids),
                'density': self._compute_density(node_ids, edges)
            })

        return communities

    def _use_existing_clusters(self, nodes: List[Dict]) -> List[Dict[str, Any]]:
        """Use existing cluster assignments as communities."""
        cluster_nodes = defaultdict(list)

        for node in nodes:
            cluster_id = node.get('cluster_id') or node.get('cluster_name') or 'unclustered'
            cluster_nodes[cluster_id].append(node['id'])

        communities = []
        for i, (cluster_id, node_ids) in enumerate(cluster_nodes.items()):
            communities.append({
                'community_id': f"cluster_{i}",
                'node_ids': node_ids,
                'size': len(node_ids),
                'density': 0.0,  # Unknown without edges
                'original_cluster': cluster_id
            })

        return communities

    def _compute_density(
        self,
        node_ids: List[str],
        edges: List[Dict]
    ) -> float:
        """Compute internal edge density of a community."""
        if len(node_ids) < 2:
            return 0.0

        node_set = set(node_ids)
        internal_edges = sum(
            1 for e in edges
            if e.get('source_node_id') in node_set
            and e.get('target_node_id') in node_set
        )

        # Maximum possible edges
        max_edges = len(node_ids) * (len(node_ids) - 1) / 2

        return internal_edges / max_edges if max_edges > 0 else 0.0

    def build_community_hierarchy(
        self,
        communities: List[Dict],
        nodes: List[Dict],
        edges: List[Dict]
    ) -> Dict[str, Any]:
        """
        Build a hierarchical structure of communities.

        For GraphRAG-style hierarchical summarization.

        Args:
            communities: Detected communities
            nodes: All concept nodes
            edges: All concept edges

        Returns:
            Hierarchical community structure
        """
        # For now, return a flat structure
        # TODO: Implement hierarchical community detection

        return {
            'levels': 1,
            'root': {
                'communities': communities,
                'total_nodes': len(nodes),
                'total_communities': len(communities)
            }
        }
