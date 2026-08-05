"""
Graph Indexer - Orchestrates Graph-Enhanced RAG Indexing

Coordinates the indexing of:
1. Semantic transcript chunks (topic-based)
2. Individual concept nodes
3. Concept clusters (themes)

This replaces the single text serialization approach with
hierarchical graph-aware embeddings.
"""

import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
import os
from dataclasses import asdict

from .semantic_chunker import SemanticChunker, SemanticChunk
from .node_embedder import NodeEmbedder, NodeEmbeddingDocument
from .cluster_embedder import ClusterEmbedder, ClusterEmbeddingDocument

logger = logging.getLogger(__name__)


class GraphIndexer:
    """
    Orchestrates graph-enhanced RAG indexing for sessions.

    Creates embeddings at multiple levels:
    - Semantic chunks: Topic-based transcript segments
    - Concept nodes: Individual concepts with full context
    - Concept clusters: Thematic groups for high-level search

    Usage:
        indexer = GraphIndexer()
        indexer.index_session(session_device_id)
    """

    # Collection names
    SEMANTIC_CHUNKS_COLLECTION = "semantic_chunks"
    CONCEPT_NODES_COLLECTION = "concept_nodes"
    CONCEPT_CLUSTERS_COLLECTION = "concept_clusters"

    def __init__(self, persist_directory: str = "./chroma_db"):
        """
        Initialize the graph indexer.

        Args:
            persist_directory: Path to ChromaDB persistence directory
        """
        # Disable telemetry
        os.environ["ANONYMIZED_TELEMETRY"] = "false"

        # Initialize ChromaDB
        settings = chromadb.Settings(
            anonymized_telemetry=False,
            allow_reset=True
        )
        self.client = chromadb.PersistentClient(path=persist_directory, settings=settings)

        # Initialize OpenAI embedding function
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.embedding_function = OpenAIEmbeddingFunction(
            api_key=self.openai_api_key,
            model_name="text-embedding-3-large"  # 3072 dimensions for quality
        )

        # Initialize collections
        self.semantic_chunks_collection = self.client.get_or_create_collection(
            name=self.SEMANTIC_CHUNKS_COLLECTION,
            embedding_function=self.embedding_function,
            metadata={"description": "Semantic topic-based transcript chunks"}
        )

        self.concept_nodes_collection = self.client.get_or_create_collection(
            name=self.CONCEPT_NODES_COLLECTION,
            embedding_function=self.embedding_function,
            metadata={"description": "Individual concept node embeddings"}
        )

        self.concept_clusters_collection = self.client.get_or_create_collection(
            name=self.CONCEPT_CLUSTERS_COLLECTION,
            embedding_function=self.embedding_function,
            metadata={"description": "Concept cluster (theme) embeddings"}
        )

        # Initialize component embedders
        self.semantic_chunker = SemanticChunker(self.openai_api_key)
        self.node_embedder = NodeEmbedder()
        self.cluster_embedder = ClusterEmbedder()

        logger.info(f"GraphIndexer initialized - "
                   f"semantic_chunks: {self.semantic_chunks_collection.count()}, "
                   f"concept_nodes: {self.concept_nodes_collection.count()}, "
                   f"concept_clusters: {self.concept_clusters_collection.count()}")

    def index_session(self, session_device_id: int,
                      index_chunks: bool = True,
                      index_nodes: bool = True,
                      index_clusters: bool = True) -> Dict[str, int]:
        """
        Index all components of a session.

        Args:
            session_device_id: The session device to index
            index_chunks: Whether to index semantic transcript chunks
            index_nodes: Whether to index concept nodes
            index_clusters: Whether to index concept clusters

        Returns:
            Dict with counts of indexed items
        """
        results = {
            "session_device_id": session_device_id,
            "semantic_chunks": 0,
            "concept_nodes": 0,
            "concept_clusters": 0,
            "errors": []
        }

        # First, remove any existing data for this session
        self.delete_session(session_device_id)

        # Index semantic chunks
        if index_chunks:
            try:
                chunk_count = self._index_semantic_chunks(session_device_id)
                results["semantic_chunks"] = chunk_count
            except Exception as e:
                logger.error(f"Error indexing semantic chunks: {e}")
                results["errors"].append(f"semantic_chunks: {str(e)}")

        # Index concept nodes
        if index_nodes:
            try:
                node_count = self._index_concept_nodes(session_device_id)
                results["concept_nodes"] = node_count
            except Exception as e:
                logger.error(f"Error indexing concept nodes: {e}")
                results["errors"].append(f"concept_nodes: {str(e)}")

        # Index concept clusters
        if index_clusters:
            try:
                cluster_count = self._index_concept_clusters(session_device_id)
                results["concept_clusters"] = cluster_count
            except Exception as e:
                logger.error(f"Error indexing concept clusters: {e}")
                results["errors"].append(f"concept_clusters: {str(e)}")

        # Clear chunker cache to free memory
        self.semantic_chunker.clear_cache()

        logger.info(f"Indexed session {session_device_id}: "
                   f"{results['semantic_chunks']} chunks, "
                   f"{results['concept_nodes']} nodes, "
                   f"{results['concept_clusters']} clusters")

        return results

    def _index_semantic_chunks(self, session_device_id: int) -> int:
        """Index semantic transcript chunks for a session."""
        from tables.transcript import Transcript

        # Get transcripts
        transcripts = Transcript.query.filter_by(
            session_device_id=session_device_id
        ).order_by(Transcript.start_time).all()

        if not transcripts:
            logger.warning(f"No transcripts found for session {session_device_id}")
            return 0

        # Create semantic chunks
        chunks = self.semantic_chunker.chunk_transcripts(transcripts, session_device_id)

        if not chunks:
            return 0

        # Prepare for ChromaDB
        ids = []
        documents = []
        metadatas = []

        for chunk in chunks:
            chunk_id = f"chunk_{session_device_id}_{chunk.chunk_index}"
            ids.append(chunk_id)
            documents.append(chunk.text)
            metadatas.append({
                "session_device_id": session_device_id,
                "chunk_index": chunk.chunk_index,
                "start_time": chunk.start_time,
                "end_time": chunk.end_time,
                "speakers": ",".join(chunk.speakers),
                "speaker_ids": ",".join(map(str, chunk.speaker_ids)),
                "transcript_count": len(chunk.transcript_ids),
                "topic_keywords": ",".join(chunk.topic_keywords),
                "avg_emotional_tone": chunk.avg_emotional_tone,
                "avg_analytic_thinking": chunk.avg_analytic_thinking,
                "avg_clout": chunk.avg_clout,
                "avg_authenticity": chunk.avg_authenticity,
                "avg_certainty": chunk.avg_certainty,
                "indexed_at": datetime.utcnow().isoformat()
            })

        # Add to collection in batches
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i+batch_size]
            batch_docs = documents[i:i+batch_size]
            batch_metas = metadatas[i:i+batch_size]

            self.semantic_chunks_collection.add(
                ids=batch_ids,
                documents=batch_docs,
                metadatas=batch_metas
            )

        return len(chunks)

    def _index_concept_nodes(self, session_device_id: int) -> int:
        """Index concept nodes for a session."""
        # Create node documents
        documents = self.node_embedder.create_node_documents(session_device_id)

        if not documents:
            return 0

        # Prepare for ChromaDB
        ids = []
        texts = []
        metadatas = []

        for doc in documents:
            ids.append(f"node_{doc.node_id}")
            texts.append(doc.text)
            metadatas.append(self.node_embedder.document_to_metadata(doc))

        # Add to collection in batches
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i+batch_size]
            batch_texts = texts[i:i+batch_size]
            batch_metas = metadatas[i:i+batch_size]

            self.concept_nodes_collection.add(
                ids=batch_ids,
                documents=batch_texts,
                metadatas=batch_metas
            )

        return len(documents)

    def _index_concept_clusters(self, session_device_id: int) -> int:
        """Index concept clusters for a session."""
        # Create cluster documents
        documents = self.cluster_embedder.create_cluster_documents(session_device_id)

        if not documents:
            return 0

        # Prepare for ChromaDB
        ids = []
        texts = []
        metadatas = []

        for doc in documents:
            ids.append(f"cluster_{doc.cluster_id}")
            texts.append(doc.text)
            metadatas.append(self.cluster_embedder.document_to_metadata(doc))

        # Add to collection
        self.concept_clusters_collection.add(
            ids=ids,
            documents=texts,
            metadatas=metadatas
        )

        return len(documents)

    def delete_session(self, session_device_id: int) -> Dict[str, int]:
        """
        Delete all indexed data for a session.

        Args:
            session_device_id: The session device to delete

        Returns:
            Dict with counts of deleted items
        """
        results = {
            "semantic_chunks": 0,
            "concept_nodes": 0,
            "concept_clusters": 0
        }

        # Delete semantic chunks
        try:
            existing = self.semantic_chunks_collection.get(
                where={"session_device_id": session_device_id}
            )
            if existing['ids']:
                self.semantic_chunks_collection.delete(ids=existing['ids'])
                results["semantic_chunks"] = len(existing['ids'])
        except Exception as e:
            logger.warning(f"Error deleting semantic chunks: {e}")

        # Delete concept nodes
        try:
            existing = self.concept_nodes_collection.get(
                where={"session_device_id": session_device_id}
            )
            if existing['ids']:
                self.concept_nodes_collection.delete(ids=existing['ids'])
                results["concept_nodes"] = len(existing['ids'])
        except Exception as e:
            logger.warning(f"Error deleting concept nodes: {e}")

        # Delete concept clusters
        try:
            existing = self.concept_clusters_collection.get(
                where={"session_device_id": session_device_id}
            )
            if existing['ids']:
                self.concept_clusters_collection.delete(ids=existing['ids'])
                results["concept_clusters"] = len(existing['ids'])
        except Exception as e:
            logger.warning(f"Error deleting concept clusters: {e}")

        return results

    # =========================================================================
    # SEARCH METHODS (for agent tools to use)
    # =========================================================================

    def search_semantic_chunks(self, query: str,
                                session_device_ids: List[int] = None,
                                n_results: int = 5,
                                speaker: str = None) -> List[Dict]:
        """
        Search semantic transcript chunks.

        Args:
            query: Search query
            session_device_ids: Optional filter by sessions
            n_results: Maximum results to return
            speaker: Optional filter by speaker name

        Returns:
            List of matching chunks with metadata
        """
        where_filter = {}

        if session_device_ids:
            if len(session_device_ids) == 1:
                where_filter["session_device_id"] = session_device_ids[0]
            else:
                where_filter["session_device_id"] = {"$in": session_device_ids}

        results = self.semantic_chunks_collection.query(
            query_texts=[query],
            n_results=n_results * 2 if speaker else n_results,  # Get extra if filtering
            where=where_filter if where_filter else None
        )

        # Format results
        formatted = []
        for i, doc_id in enumerate(results['ids'][0]):
            metadata = results['metadatas'][0][i]

            # Filter by speaker if specified
            if speaker:
                speakers = metadata.get('speakers', '').split(',')
                if not any(speaker.lower() in s.lower() for s in speakers):
                    continue

            formatted.append({
                "id": doc_id,
                "text": results['documents'][0][i],
                "distance": results['distances'][0][i] if results.get('distances') else None,
                "session_device_id": metadata.get('session_device_id'),
                "start_time": metadata.get('start_time'),
                "end_time": metadata.get('end_time'),
                "speakers": metadata.get('speakers', '').split(','),
                "topic_keywords": metadata.get('topic_keywords', '').split(','),
                "avg_emotional_tone": metadata.get('avg_emotional_tone'),
                "chunk_index": metadata.get('chunk_index')
            })

            if len(formatted) >= n_results:
                break

        return formatted

    def search_concept_nodes(self, query: str,
                              session_device_ids: List[int] = None,
                              node_types: List[str] = None,
                              n_results: int = 10) -> List[Dict]:
        """
        Search concept nodes by semantic similarity.

        Args:
            query: Search query (concept to find)
            session_device_ids: Optional filter by sessions
            node_types: Optional filter by node types (idea, question, etc.)
            n_results: Maximum results to return

        Returns:
            List of matching nodes with metadata
        """
        where_filter = {}

        if session_device_ids:
            if len(session_device_ids) == 1:
                where_filter["session_device_id"] = session_device_ids[0]
            else:
                where_filter["session_device_id"] = {"$in": session_device_ids}

        if node_types:
            if len(node_types) == 1:
                where_filter["node_type"] = node_types[0]
            else:
                where_filter["node_type"] = {"$in": node_types}

        results = self.concept_nodes_collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter if where_filter else None
        )

        # Format results
        formatted = []
        for i, doc_id in enumerate(results['ids'][0]):
            metadata = results['metadatas'][0][i]
            formatted.append({
                "id": doc_id,
                "node_id": metadata.get('node_id'),
                "text": results['documents'][0][i],
                "distance": results['distances'][0][i] if results.get('distances') else None,
                "session_device_id": metadata.get('session_device_id'),
                "node_type": metadata.get('node_type'),
                "speaker_alias": metadata.get('speaker_alias'),
                "speaker_id": metadata.get('speaker_id'),
                "cluster_name": metadata.get('cluster_name'),
                "cluster_id": metadata.get('cluster_id'),
                "timestamp": metadata.get('timestamp'),
                "neighbor_count": metadata.get('neighbor_count')
            })

        return formatted

    def search_concept_clusters(self, query: str,
                                 session_device_ids: List[int] = None,
                                 n_results: int = 5) -> List[Dict]:
        """
        Search concept clusters (themes) by semantic similarity.

        Args:
            query: Search query (theme to find)
            session_device_ids: Optional filter by sessions
            n_results: Maximum results to return

        Returns:
            List of matching clusters with metadata
        """
        where_filter = {}

        if session_device_ids:
            if len(session_device_ids) == 1:
                where_filter["session_device_id"] = session_device_ids[0]
            else:
                where_filter["session_device_id"] = {"$in": session_device_ids}

        results = self.concept_clusters_collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter if where_filter else None
        )

        # Format results
        formatted = []
        for i, doc_id in enumerate(results['ids'][0]):
            metadata = results['metadatas'][0][i]
            formatted.append({
                "id": doc_id,
                "cluster_id": metadata.get('cluster_id'),
                "text": results['documents'][0][i],
                "distance": results['distances'][0][i] if results.get('distances') else None,
                "session_device_id": metadata.get('session_device_id'),
                "cluster_name": metadata.get('cluster_name'),
                "node_count": metadata.get('node_count'),
                "speaker_count": metadata.get('speaker_count'),
                "speakers": metadata.get('speakers'),
                "start_time": metadata.get('start_time'),
                "end_time": metadata.get('end_time'),
                "question_count": metadata.get('question_count'),
                "idea_count": metadata.get('idea_count'),
                "hypothesis_count": metadata.get('hypothesis_count')
            })

        return formatted

    def get_collection_stats(self) -> Dict:
        """Get statistics for all graph RAG collections."""
        return {
            "semantic_chunks": self.semantic_chunks_collection.count(),
            "concept_nodes": self.concept_nodes_collection.count(),
            "concept_clusters": self.concept_clusters_collection.count()
        }
