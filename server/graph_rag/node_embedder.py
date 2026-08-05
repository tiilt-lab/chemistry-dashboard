"""
Node Embedder for Concept Maps

Creates individual embeddings for each concept node, enabling
fine-grained semantic search over concepts.

Each node is embedded with rich context:
- Node text and type
- Speaker attribution
- Cluster context (if available)
- Temporal position
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import json

logger = logging.getLogger(__name__)


@dataclass
class NodeEmbeddingDocument:
    """Document for embedding a concept node."""
    node_id: str
    session_device_id: int
    concept_session_id: int
    text: str  # The embedding text

    # Node properties
    node_type: str
    original_text: str
    speaker_id: Optional[int]
    speaker_alias: Optional[str]
    timestamp: Optional[float]

    # Cluster context
    cluster_id: Optional[int]
    cluster_name: Optional[str]

    # Graph context
    neighbor_count: int
    incoming_edges: int
    outgoing_edges: int


class NodeEmbedder:
    """
    Creates embeddings for individual concept nodes.

    Each node gets a rich text representation that includes:
    - The node type (question, idea, hypothesis, etc.)
    - The full node text (no truncation!)
    - Speaker attribution
    - Cluster context for thematic grounding

    This enables queries like:
    - "Find ideas about photosynthesis"
    - "What questions did Student A ask?"
    - "Show hypotheses from the energy cluster"
    """

    # Template for creating embeddable node text
    NODE_TEMPLATE = """{type}: {text}
Speaker: {speaker}
Theme: {cluster}"""

    # Simplified template for nodes without cluster
    NODE_TEMPLATE_SIMPLE = """{type}: {text}
Speaker: {speaker}"""

    def __init__(self):
        """Initialize the node embedder."""
        pass

    def create_node_documents(self, session_device_id: int) -> List[NodeEmbeddingDocument]:
        """
        Create embedding documents for all nodes in a session.

        Args:
            session_device_id: The session device to process

        Returns:
            List of NodeEmbeddingDocument objects ready for embedding
        """
        from tables.concept_session import ConceptSession
        from tables.concept_node import ConceptNode
        from tables.concept_edge import ConceptEdge
        from tables.concept_cluster import ConceptCluster
        import database as db_helper

        # Get concept session
        concept_session = ConceptSession.query.filter_by(
            session_device_id=session_device_id
        ).first()

        if not concept_session:
            logger.warning(f"No concept session found for {session_device_id}")
            return []

        nodes = concept_session.nodes
        edges = concept_session.edges or []
        clusters = concept_session.clusters or []

        if not nodes:
            logger.warning(f"No nodes found for session {session_device_id}")
            return []

        # Build lookup maps
        speaker_aliases = self._build_speaker_aliases(nodes)
        node_clusters = self._build_node_cluster_map(clusters)
        edge_counts = self._count_edges(nodes, edges)

        # Create documents for each node
        documents = []
        for node in nodes:
            doc = self._create_node_document(
                node=node,
                session_device_id=session_device_id,
                concept_session_id=concept_session.id,
                speaker_aliases=speaker_aliases,
                node_clusters=node_clusters,
                edge_counts=edge_counts
            )
            documents.append(doc)

        logger.info(f"Created {len(documents)} node documents for session {session_device_id}")
        return documents

    def _create_node_document(self, node, session_device_id: int,
                               concept_session_id: int,
                               speaker_aliases: Dict[int, str],
                               node_clusters: Dict[str, Tuple[int, str]],
                               edge_counts: Dict[str, Tuple[int, int]]) -> NodeEmbeddingDocument:
        """Create a single node embedding document."""

        # Get speaker info
        speaker_alias = None
        if node.speaker_id:
            speaker_alias = speaker_aliases.get(node.speaker_id, f"Speaker {node.speaker_id}")

        # Get cluster info
        cluster_id, cluster_name = node_clusters.get(node.id, (None, None))

        # Get edge counts
        incoming, outgoing = edge_counts.get(node.id, (0, 0))

        # Format node type for embedding
        node_type = self._format_node_type(node.node_type)

        # Create embedding text
        if cluster_name:
            embedding_text = self.NODE_TEMPLATE.format(
                type=node_type,
                text=node.text,
                speaker=speaker_alias or "Unknown",
                cluster=cluster_name
            )
        else:
            embedding_text = self.NODE_TEMPLATE_SIMPLE.format(
                type=node_type,
                text=node.text,
                speaker=speaker_alias or "Unknown"
            )

        return NodeEmbeddingDocument(
            node_id=node.id,
            session_device_id=session_device_id,
            concept_session_id=concept_session_id,
            text=embedding_text,
            node_type=node.node_type or 'concept',
            original_text=node.text,
            speaker_id=node.speaker_id,
            speaker_alias=speaker_alias,
            timestamp=node.timestamp,
            cluster_id=cluster_id,
            cluster_name=cluster_name,
            neighbor_count=incoming + outgoing,
            incoming_edges=incoming,
            outgoing_edges=outgoing
        )

    def _format_node_type(self, node_type: str) -> str:
        """Format node type for better embedding quality."""
        type_labels = {
            'question': 'Question',
            'idea': 'Idea',
            'hypothesis': 'Hypothesis',
            'evidence': 'Evidence',
            'conclusion': 'Conclusion',
            'problem': 'Problem',
            'solution': 'Solution',
            'cause': 'Cause',
            'effect': 'Effect',
            'example': 'Example',
            'elaboration': 'Elaboration',
            'synthesis': 'Synthesis',
            'evaluation': 'Evaluation',
            'challenge': 'Challenge',
            'counterpoint': 'Counterpoint',
            'observation': 'Observation',
            'interpretation': 'Interpretation',
            'uncertainty': 'Uncertainty',
            'goal': 'Goal',
            'constraint': 'Constraint'
        }
        return type_labels.get(node_type, node_type.title() if node_type else 'Concept')

    def _build_speaker_aliases(self, nodes: List) -> Dict[int, str]:
        """Build speaker_id to alias mapping."""
        import database as db_helper

        speaker_ids = set(n.speaker_id for n in nodes if n.speaker_id)
        speaker_map = {}

        for speaker_id in speaker_ids:
            try:
                speaker = db_helper.get_speakers(id=speaker_id)
                if speaker:
                    speaker_map[speaker_id] = speaker.alias or speaker.get_alias()
                else:
                    speaker_map[speaker_id] = f"Speaker {speaker_id}"
            except Exception:
                speaker_map[speaker_id] = f"Speaker {speaker_id}"

        return speaker_map

    def _build_node_cluster_map(self, clusters: List) -> Dict[str, Tuple[int, str]]:
        """Build node_id to (cluster_id, cluster_name) mapping."""
        node_map = {}

        for cluster in clusters:
            if cluster.nodes:
                for node in cluster.nodes:
                    node_map[node.id] = (cluster.id, cluster.cluster_name)

        return node_map

    def _count_edges(self, nodes: List, edges: List) -> Dict[str, Tuple[int, int]]:
        """Count incoming and outgoing edges for each node."""
        from collections import defaultdict

        incoming = defaultdict(int)
        outgoing = defaultdict(int)

        for edge in edges:
            outgoing[edge.source_node_id] += 1
            incoming[edge.target_node_id] += 1

        result = {}
        for node in nodes:
            result[node.id] = (incoming[node.id], outgoing[node.id])

        return result

    def document_to_metadata(self, doc: NodeEmbeddingDocument) -> Dict:
        """Convert document to ChromaDB metadata format."""
        return {
            "node_id": doc.node_id,
            "session_device_id": doc.session_device_id,
            "concept_session_id": doc.concept_session_id,
            "node_type": doc.node_type,
            "speaker_id": doc.speaker_id or 0,
            "speaker_alias": doc.speaker_alias or "Unknown",
            "timestamp": doc.timestamp or 0.0,
            "cluster_id": doc.cluster_id or 0,
            "cluster_name": doc.cluster_name or "",
            "neighbor_count": doc.neighbor_count,
            "incoming_edges": doc.incoming_edges,
            "outgoing_edges": doc.outgoing_edges,
            "indexed_at": datetime.utcnow().isoformat()
        }
