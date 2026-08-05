"""
Graph RAG V2 Indexer

Orchestrates the creation of new graph-aware embeddings:
1. Community summaries (for global search)
2. Session narratives (for "what happened" queries)
3. Structure-aware node embeddings (with neighbor context)

These are stored in NEW collections, not affecting existing RAG Discovery.
"""

import logging
import os
from typing import Dict, List, Any
from datetime import datetime

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

from .community_detector import CommunityDetector
from .community_summarizer import CommunitySummarizer
from .session_narrator import SessionNarrator

logger = logging.getLogger(__name__)


class GraphRAGIndexer:
    """
    Indexes sessions with graph-aware embeddings.

    Creates three new collections:
    - graph_communities: Community summaries for global search
    - session_narratives: Full session narratives
    - graph_nodes: Structure-aware node embeddings
    """

    # New collection names (don't conflict with existing)
    COMMUNITIES_COLLECTION = "graph_communities"
    NARRATIVES_COLLECTION = "session_narratives"
    GRAPH_NODES_COLLECTION = "graph_nodes"

    def __init__(self, persist_directory: str = "./chroma_db"):
        """Initialize the indexer."""
        os.environ["ANONYMIZED_TELEMETRY"] = "false"

        settings = chromadb.Settings(
            anonymized_telemetry=False,
            allow_reset=True
        )
        self.client = chromadb.PersistentClient(path=persist_directory, settings=settings)

        # Use large model for quality
        self.embedding_function = OpenAIEmbeddingFunction(
            api_key=os.getenv("OPENAI_API_KEY"),
            model_name="text-embedding-3-large"
        )

        # Initialize collections
        self.communities_collection = self.client.get_or_create_collection(
            name=self.COMMUNITIES_COLLECTION,
            embedding_function=self.embedding_function,
            metadata={"description": "Community summaries for global search"}
        )

        self.narratives_collection = self.client.get_or_create_collection(
            name=self.NARRATIVES_COLLECTION,
            embedding_function=self.embedding_function,
            metadata={"description": "Session narratives for overview queries"}
        )

        self.graph_nodes_collection = self.client.get_or_create_collection(
            name=self.GRAPH_NODES_COLLECTION,
            embedding_function=self.embedding_function,
            metadata={"description": "Structure-aware node embeddings"}
        )

        # Initialize components
        self.community_detector = CommunityDetector()
        self.community_summarizer = CommunitySummarizer()
        self.session_narrator = SessionNarrator()

        logger.info(f"GraphRAGIndexer initialized - communities: {self.communities_collection.count()}, "
                   f"narratives: {self.narratives_collection.count()}, "
                   f"graph_nodes: {self.graph_nodes_collection.count()}")

    def index_session(self, session_device_id: int) -> Dict[str, int]:
        """
        Index a session with graph-aware embeddings.

        Args:
            session_device_id: Session to index

        Returns:
            Counts of indexed items
        """
        logger.info(f"Indexing session {session_device_id} for GraphRAG V2")

        results = {
            'session_device_id': session_device_id,
            'communities': 0,
            'narrative': 0,
            'graph_nodes': 0,
            'errors': []
        }

        # Get session data
        session_data = self._get_session_data(session_device_id)
        if not session_data:
            results['errors'].append('Session not found')
            return results

        nodes = session_data.get('nodes', [])
        edges = session_data.get('edges', [])

        # 1. Index communities
        try:
            communities = self.community_detector.detect_communities(nodes, edges)
            summaries = self.community_summarizer.summarize_all_communities(
                communities, nodes, edges
            )
            self._index_communities(session_device_id, summaries)
            results['communities'] = len(summaries)
        except Exception as e:
            logger.error(f"Community indexing error: {e}")
            results['errors'].append(f"communities: {str(e)}")

        # 2. Index narrative
        try:
            narrative = self.session_narrator.generate_narrative(
                session_device_id, session_data
            )
            self._index_narrative(session_device_id, narrative)
            results['narrative'] = 1
        except Exception as e:
            logger.error(f"Narrative indexing error: {e}")
            results['errors'].append(f"narrative: {str(e)}")

        # 3. Index graph-aware nodes
        try:
            count = self._index_graph_nodes(session_device_id, nodes, edges)
            results['graph_nodes'] = count
        except Exception as e:
            logger.error(f"Graph node indexing error: {e}")
            results['errors'].append(f"graph_nodes: {str(e)}")

        logger.info(f"Indexed session {session_device_id}: {results}")
        return results

    def _get_session_data(self, session_device_id: int) -> Dict[str, Any]:
        """Get all session data needed for indexing."""
        import mysql.connector

        try:
            connection = mysql.connector.connect(
                host='localhost',
                user='vagrant',
                password='vagrant',
                database='discussion_capture'
            )
            cursor = connection.cursor(dictionary=True)

            # Get session info
            cursor.execute("""
                SELECT sd.id, sd.name as device_name, s.name as session_name
                FROM session_device sd
                JOIN session s ON s.id = sd.session_id
                WHERE sd.id = %s
            """, (session_device_id,))
            session_info = cursor.fetchone()

            if not session_info:
                cursor.close()
                connection.close()
                return None

            # Get concept session
            cursor.execute("""
                SELECT id, discourse_type FROM concept_session
                WHERE session_device_id = %s
            """, (session_device_id,))
            concept_session = cursor.fetchone()

            if not concept_session:
                cursor.close()
                connection.close()
                return {
                    'session_name': session_info.get('session_name') or session_info.get('device_name'),
                    'nodes': [],
                    'edges': []
                }

            # Get nodes
            cursor.execute("""
                SELECT cn.*, s.alias as speaker_alias
                FROM concept_node cn
                LEFT JOIN speaker s ON s.id = cn.speaker_id
                WHERE cn.concept_session_id = %s
            """, (concept_session['id'],))
            nodes = cursor.fetchall()

            # Get edges
            cursor.execute("""
                SELECT * FROM concept_edge
                WHERE concept_session_id = %s
            """, (concept_session['id'],))
            edges = cursor.fetchall()

            # Get clusters/themes
            cursor.execute("""
                SELECT cluster_name FROM concept_cluster
                WHERE concept_session_id = %s
                ORDER BY node_count DESC
            """, (concept_session['id'],))
            clusters = cursor.fetchall()
            themes = [c['cluster_name'] for c in clusters]

            # Get participants
            cursor.execute("""
                SELECT DISTINCT s.alias
                FROM speaker s
                JOIN transcript t ON t.speaker_id = s.id
                WHERE t.session_device_id = %s
            """, (session_device_id,))
            speakers = cursor.fetchall()
            participants = [s['alias'] for s in speakers]

            # Get duration
            cursor.execute("""
                SELECT MAX(end_time) as duration FROM transcript
                WHERE session_device_id = %s
            """, (session_device_id,))
            duration_row = cursor.fetchone()

            # Get 7C scores
            cursor.execute("""
                SELECT * FROM seven_cs_analysis
                WHERE session_device_id = %s
                ORDER BY created_at DESC LIMIT 1
            """, (session_device_id,))
            seven_cs = cursor.fetchone()

            cursor.close()
            connection.close()

            return {
                'session_name': session_info.get('session_name') or session_info.get('device_name'),
                'discourse_type': concept_session.get('discourse_type'),
                'nodes': nodes,
                'edges': edges,
                'themes': themes,
                'participants': participants,
                'duration': duration_row.get('duration') if duration_row else None,
                'seven_cs': seven_cs,
                'key_concepts': nodes[:20]  # Top 20 concepts
            }

        except Exception as e:
            logger.error(f"Error getting session data: {e}")
            return None

    def _index_communities(
        self,
        session_device_id: int,
        summaries: List[Dict]
    ):
        """Index community summaries."""
        # Delete existing for this session
        existing = self.communities_collection.get(
            where={"session_device_id": session_device_id}
        )
        if existing and existing.get('ids'):
            self.communities_collection.delete(ids=existing['ids'])

        if not summaries:
            return

        # Add new
        ids = []
        documents = []
        metadatas = []

        for summary in summaries:
            doc_id = f"community_{session_device_id}_{summary['community_id']}"
            ids.append(doc_id)

            # Embedding text
            text = f"Theme: {summary.get('theme', '')}\n\n{summary.get('summary', '')}"
            if summary.get('key_concepts'):
                text += "\n\nKey concepts: " + ", ".join(summary['key_concepts'][:5])
            documents.append(text)

            metadatas.append({
                'session_device_id': session_device_id,
                'community_id': summary['community_id'],
                'theme': summary.get('theme', ''),
                'node_count': summary.get('node_count', 0),
                'indexed_at': datetime.utcnow().isoformat()
            })

        self.communities_collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )

    def _index_narrative(
        self,
        session_device_id: int,
        narrative: Dict
    ):
        """Index session narrative."""
        # Delete existing
        existing = self.narratives_collection.get(
            where={"session_device_id": session_device_id}
        )
        if existing and existing.get('ids'):
            self.narratives_collection.delete(ids=existing['ids'])

        doc_id = f"narrative_{session_device_id}"

        self.narratives_collection.add(
            ids=[doc_id],
            documents=[narrative.get('narrative', '')],
            metadatas=[{
                'session_device_id': session_device_id,
                'session_name': narrative.get('session_name', ''),
                'participants': ','.join(narrative.get('participants', [])),
                'themes': ','.join(narrative.get('themes', [])),
                'discourse_type': narrative.get('discourse_type', ''),
                'indexed_at': datetime.utcnow().isoformat()
            }]
        )

    def _index_graph_nodes(
        self,
        session_device_id: int,
        nodes: List[Dict],
        edges: List[Dict]
    ) -> int:
        """
        Index nodes with structure-aware embeddings.

        Each node embedding includes neighbor context.
        """
        # Delete existing
        existing = self.graph_nodes_collection.get(
            where={"session_device_id": session_device_id}
        )
        if existing and existing.get('ids'):
            self.graph_nodes_collection.delete(ids=existing['ids'])

        if not nodes:
            return 0

        # Build neighbor map
        neighbor_map = self._build_neighbor_map(nodes, edges)

        ids = []
        documents = []
        metadatas = []

        for node in nodes:
            node_id = node.get('id')
            doc_id = f"graphnode_{session_device_id}_{node_id}"
            ids.append(doc_id)

            # Build structure-aware text
            text = self._build_graph_aware_text(node, neighbor_map)
            documents.append(text)

            neighbors = neighbor_map.get(node_id, {})
            metadatas.append({
                'session_device_id': session_device_id,
                'node_id': node_id,
                'node_type': node.get('node_type', 'concept'),
                'speaker': node.get('speaker_alias', ''),
                'neighbor_count': neighbors.get('total', 0),
                'incoming_count': len(neighbors.get('incoming', [])),
                'outgoing_count': len(neighbors.get('outgoing', [])),
                'indexed_at': datetime.utcnow().isoformat()
            })

        # Batch insert
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            self.graph_nodes_collection.add(
                ids=ids[i:i+batch_size],
                documents=documents[i:i+batch_size],
                metadatas=metadatas[i:i+batch_size]
            )

        return len(ids)

    def _build_neighbor_map(
        self,
        nodes: List[Dict],
        edges: List[Dict]
    ) -> Dict[str, Dict]:
        """Build a map of node ID to neighbor information."""
        node_text = {n['id']: n.get('text', '')[:100] for n in nodes}

        neighbor_map = {}
        for node in nodes:
            neighbor_map[node['id']] = {
                'incoming': [],
                'outgoing': [],
                'total': 0
            }

        for edge in edges:
            src = edge.get('source_node_id')
            tgt = edge.get('target_node_id')
            etype = edge.get('edge_type', 'relates_to')

            if src in neighbor_map:
                neighbor_map[src]['outgoing'].append({
                    'node_id': tgt,
                    'text': node_text.get(tgt, ''),
                    'edge_type': etype
                })

            if tgt in neighbor_map:
                neighbor_map[tgt]['incoming'].append({
                    'node_id': src,
                    'text': node_text.get(src, ''),
                    'edge_type': etype
                })

        # Calculate totals
        for node_id in neighbor_map:
            neighbor_map[node_id]['total'] = (
                len(neighbor_map[node_id]['incoming']) +
                len(neighbor_map[node_id]['outgoing'])
            )

        return neighbor_map

    def _build_graph_aware_text(
        self,
        node: Dict,
        neighbor_map: Dict
    ) -> str:
        """
        Build embedding text that includes graph structure.

        This is a simplified version of GraphSAGE's neighbor aggregation.
        """
        node_id = node.get('id')
        node_type = node.get('node_type', 'concept').title()
        node_text = node.get('text', '')
        speaker = node.get('speaker_alias', '')

        lines = [f"{node_type}: {node_text}"]

        if speaker:
            lines.append(f"Speaker: {speaker}")

        neighbors = neighbor_map.get(node_id, {})

        # Add incoming context (what leads to this)
        incoming = neighbors.get('incoming', [])[:3]
        if incoming:
            leads_to = "; ".join(n['text'][:50] for n in incoming)
            lines.append(f"Builds on: {leads_to}")

        # Add outgoing context (what this leads to)
        outgoing = neighbors.get('outgoing', [])[:3]
        if outgoing:
            leads_to = "; ".join(n['text'][:50] for n in outgoing)
            lines.append(f"Leads to: {leads_to}")

        return "\n".join(lines)

    def get_stats(self) -> Dict[str, int]:
        """Get collection statistics."""
        return {
            'communities': self.communities_collection.count(),
            'narratives': self.narratives_collection.count(),
            'graph_nodes': self.graph_nodes_collection.count()
        }
