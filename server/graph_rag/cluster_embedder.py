"""
Cluster Embedder for Concept Maps

Creates embeddings for thematic clusters, enabling high-level
topic/theme search across sessions.

Each cluster represents a coherent theme in the discussion,
and gets embedded with:
- Cluster name and summary
- Key concepts within the cluster
- Temporal span
- Node type distribution
"""

import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
from collections import Counter
import json

logger = logging.getLogger(__name__)


@dataclass
class ClusterEmbeddingDocument:
    """Document for embedding a concept cluster."""
    cluster_id: int
    session_device_id: int
    concept_session_id: int
    text: str  # The embedding text

    # Cluster properties
    cluster_name: str
    summary: Optional[str]
    start_time: Optional[float]
    end_time: Optional[float]

    # Aggregate stats
    node_count: int
    speaker_count: int
    speakers: List[str]

    # Node type distribution
    question_count: int
    idea_count: int
    hypothesis_count: int
    problem_count: int
    solution_count: int

    # Top concepts
    top_concepts: List[str]


class ClusterEmbedder:
    """
    Creates embeddings for concept clusters (thematic groups).

    Clusters represent high-level themes in a discussion. Each cluster
    gets a rich text representation that includes:
    - The cluster name (theme label)
    - LLM-generated summary
    - Representative concepts from the cluster
    - Discussion dynamics (speakers, duration)

    This enables queries like:
    - "Find sessions discussing climate change themes"
    - "Which discussions had problem-solving clusters?"
    - "Show themes where multiple students contributed"
    """

    # Template for creating embeddable cluster text
    CLUSTER_TEMPLATE = """Theme: {name}

Summary: {summary}

Key Concepts:
{concepts}

Participants: {speakers}
Discussion Elements: {elements}"""

    # Simplified template when no summary
    CLUSTER_TEMPLATE_SIMPLE = """Theme: {name}

Key Concepts:
{concepts}

Participants: {speakers}"""

    def __init__(self):
        """Initialize the cluster embedder."""
        pass

    def create_cluster_documents(self, session_device_id: int) -> List[ClusterEmbeddingDocument]:
        """
        Create embedding documents for all clusters in a session.

        Args:
            session_device_id: The session device to process

        Returns:
            List of ClusterEmbeddingDocument objects ready for embedding
        """
        from tables.concept_session import ConceptSession
        import database as db_helper

        # Get concept session
        concept_session = ConceptSession.query.filter_by(
            session_device_id=session_device_id
        ).first()

        if not concept_session:
            logger.warning(f"No concept session found for {session_device_id}")
            return []

        clusters = concept_session.clusters

        if not clusters:
            logger.warning(f"No clusters found for session {session_device_id}")
            return []

        # Build speaker aliases
        all_nodes = concept_session.nodes or []
        speaker_aliases = self._build_speaker_aliases(all_nodes)

        # Create documents for each cluster
        documents = []
        for cluster in clusters:
            doc = self._create_cluster_document(
                cluster=cluster,
                session_device_id=session_device_id,
                concept_session_id=concept_session.id,
                speaker_aliases=speaker_aliases
            )
            documents.append(doc)

        logger.info(f"Created {len(documents)} cluster documents for session {session_device_id}")
        return documents

    def _create_cluster_document(self, cluster, session_device_id: int,
                                  concept_session_id: int,
                                  speaker_aliases: Dict[int, str]) -> ClusterEmbeddingDocument:
        """Create a single cluster embedding document."""

        nodes = cluster.nodes or []

        # Get speakers in this cluster
        cluster_speakers = set()
        speaker_ids = set()
        for node in nodes:
            if node.speaker_id:
                speaker_ids.add(node.speaker_id)
                alias = speaker_aliases.get(node.speaker_id, f"Speaker {node.speaker_id}")
                cluster_speakers.add(alias)

        # Count node types
        type_counts = Counter(n.node_type for n in nodes if n.node_type)

        # Get top concepts (prioritize questions, ideas, hypotheses)
        priority_types = ['question', 'hypothesis', 'problem', 'idea', 'solution', 'conclusion']
        top_concepts = []

        # First add high-priority types
        for ptype in priority_types:
            type_nodes = [n for n in nodes if n.node_type == ptype]
            for node in type_nodes[:2]:  # Max 2 per type
                if len(top_concepts) < 8:
                    top_concepts.append(f"- {self._format_node_type(node.node_type)}: {node.text[:100]}")

        # Fill with remaining nodes if needed
        if len(top_concepts) < 5:
            remaining = [n for n in nodes if n.node_type not in priority_types]
            for node in remaining[:5 - len(top_concepts)]:
                top_concepts.append(f"- {self._format_node_type(node.node_type)}: {node.text[:100]}")

        # Format discussion elements description
        elements = []
        if type_counts.get('question'):
            elements.append(f"{type_counts['question']} questions")
        if type_counts.get('idea'):
            elements.append(f"{type_counts['idea']} ideas")
        if type_counts.get('hypothesis'):
            elements.append(f"{type_counts['hypothesis']} hypotheses")
        if type_counts.get('problem'):
            elements.append(f"{type_counts['problem']} problems")
        if type_counts.get('solution'):
            elements.append(f"{type_counts['solution']} solutions")

        elements_str = ", ".join(elements) if elements else "various concepts"

        # Create embedding text
        if cluster.summary:
            embedding_text = self.CLUSTER_TEMPLATE.format(
                name=cluster.cluster_name or "Unnamed Theme",
                summary=cluster.summary[:500] if cluster.summary else "No summary available",
                concepts="\n".join(top_concepts) if top_concepts else "No key concepts",
                speakers=", ".join(sorted(cluster_speakers)) if cluster_speakers else "Unknown",
                elements=elements_str
            )
        else:
            embedding_text = self.CLUSTER_TEMPLATE_SIMPLE.format(
                name=cluster.cluster_name or "Unnamed Theme",
                concepts="\n".join(top_concepts) if top_concepts else "No key concepts",
                speakers=", ".join(sorted(cluster_speakers)) if cluster_speakers else "Unknown"
            )

        return ClusterEmbeddingDocument(
            cluster_id=cluster.id,
            session_device_id=session_device_id,
            concept_session_id=concept_session_id,
            text=embedding_text,
            cluster_name=cluster.cluster_name or "Unnamed",
            summary=cluster.summary,
            start_time=cluster.start_time,
            end_time=cluster.end_time,
            node_count=len(nodes),
            speaker_count=len(speaker_ids),
            speakers=list(sorted(cluster_speakers)),
            question_count=type_counts.get('question', 0),
            idea_count=type_counts.get('idea', 0),
            hypothesis_count=type_counts.get('hypothesis', 0),
            problem_count=type_counts.get('problem', 0),
            solution_count=type_counts.get('solution', 0),
            top_concepts=[n.text[:100] for n in nodes[:5]]
        )

    def _format_node_type(self, node_type: str) -> str:
        """Format node type for display."""
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
            'observation': 'Observation'
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

    def document_to_metadata(self, doc: ClusterEmbeddingDocument) -> Dict:
        """Convert document to ChromaDB metadata format."""
        return {
            "cluster_id": doc.cluster_id,
            "session_device_id": doc.session_device_id,
            "concept_session_id": doc.concept_session_id,
            "cluster_name": doc.cluster_name,
            "has_summary": doc.summary is not None,
            "start_time": doc.start_time or 0.0,
            "end_time": doc.end_time or 0.0,
            "node_count": doc.node_count,
            "speaker_count": doc.speaker_count,
            "speakers": json.dumps(doc.speakers),
            "question_count": doc.question_count,
            "idea_count": doc.idea_count,
            "hypothesis_count": doc.hypothesis_count,
            "problem_count": doc.problem_count,
            "solution_count": doc.solution_count,
            "indexed_at": datetime.utcnow().isoformat()
        }
