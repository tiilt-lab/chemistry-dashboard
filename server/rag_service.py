import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from openai import OpenAI
import os
import json
from datetime import datetime
from typing import List, Dict, Optional
import logging
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self, persist_directory="./chroma_db"):
        """Initialize RAG service with ChromaDB and OpenAI"""

        # Disable ChromaDB telemetry to avoid RecursionError in send_request
        os.environ["ANONYMIZED_TELEMETRY"] = "false"

        # Initialize ChromaDB with telemetry disabled
        settings = chromadb.Settings(
            anonymized_telemetry=False,
            allow_reset=True
        )
        self.client = chromadb.PersistentClient(path=persist_directory, settings=settings)
        
        # Initialize OpenAI
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_client = OpenAI(api_key=self.openai_api_key)
        
        # Create embedding function - use text-embedding-3-large for quality
        self.embedding_function = OpenAIEmbeddingFunction(
            api_key=self.openai_api_key,
            model_name="text-embedding-3-large"  # 3072 dimensions, prioritize quality
        )

        # Get or create chunk collection (existing - 30-sec transcript chunks)
        self.collection = self.client.get_or_create_collection(
            name="discussion_chunks",
            embedding_function=self.embedding_function,
            metadata={"description": "30-second discussion chunks with metadata"}
        )

        # ============================================================
        # SESSION-LEVEL COLLECTIONS (Separate embeddings for different data types)
        # ============================================================

        # Full session transcripts - for topic/content queries
        self.transcript_collection = self.client.get_or_create_collection(
            name="session_transcripts",
            embedding_function=self.embedding_function,
            metadata={"description": "Full session transcripts for topic-based search"}
        )

        # Concept map structure - for structural/argumentation queries
        self.concept_collection = self.client.get_or_create_collection(
            name="session_concepts",
            embedding_function=self.embedding_function,
            metadata={"description": "Concept map structure for pattern queries"}
        )

        # 7C analysis - for quality/collaboration queries
        self.seven_c_collection = self.client.get_or_create_collection(
            name="session_7c",
            embedding_function=self.embedding_function,
            metadata={"description": "7C collaborative quality analysis"}
        )

        # Legacy combined session collection (kept for backward compatibility)
        self.session_collection = self.client.get_or_create_collection(
            name="session_summaries",
            embedding_function=self.embedding_function,
            metadata={"description": "Legacy combined session embeddings"}
        )

        # Get or create speaker collection (for cross-session speaker analysis)
        self.speaker_collection = self.client.get_or_create_collection(
            name="speaker_profiles",
            embedding_function=self.embedding_function,
            metadata={"description": "Cross-session speaker profiles indexed by alias"}
        )

        # ============================================================
        # GRAPH-ENHANCED RAG COLLECTIONS (NEW - for agentic workflows)
        # ============================================================

        # Semantic transcript chunks - topic-based instead of fixed 30-sec windows
        self.semantic_chunks_collection = self.client.get_or_create_collection(
            name="semantic_chunks",
            embedding_function=self.embedding_function,
            metadata={"description": "Semantic topic-based transcript chunks"}
        )

        # Individual concept nodes - fine-grained concept search
        self.concept_nodes_collection = self.client.get_or_create_collection(
            name="concept_nodes",
            embedding_function=self.embedding_function,
            metadata={"description": "Individual concept node embeddings"}
        )

        # Concept clusters (themes) - high-level thematic search
        self.concept_clusters_collection = self.client.get_or_create_collection(
            name="concept_clusters",
            embedding_function=self.embedding_function,
            metadata={"description": "Concept cluster (theme) embeddings"}
        )

        logger.info(f"RAG Service initialized - chunks: {self.collection.count()}, "
                   f"transcripts: {self.transcript_collection.count()}, "
                   f"concepts: {self.concept_collection.count()}, "
                   f"7c: {self.seven_c_collection.count()}, "
                   f"speakers: {self.speaker_collection.count()}, "
                   f"semantic_chunks: {self.semantic_chunks_collection.count()}, "
                   f"concept_nodes: {self.concept_nodes_collection.count()}, "
                   f"concept_clusters: {self.concept_clusters_collection.count()}")
    
    def chunk_transcripts(self, transcripts: List, window_seconds: int = 30) -> List[Dict]:
        """
        Chunk transcripts into fixed time windows
        
        Args:
            transcripts: List of transcript objects from database
            window_seconds: Size of each chunk in seconds
            
        Returns:
            List of chunks with metadata
        """
        if not transcripts:
            return []
        
        chunks = []
        current_chunk_transcripts = []
        current_chunk_start = 0
        
        for transcript in transcripts:
            # Check if transcript belongs to current window
            if transcript.start_time < current_chunk_start + window_seconds:
                current_chunk_transcripts.append(transcript)
            else:
                # Save current chunk if it has content
                if current_chunk_transcripts:
                    chunks.append(self._create_chunk(
                        current_chunk_transcripts, 
                        current_chunk_start,
                        current_chunk_start + window_seconds
                    ))
                
                # Start new chunk
                current_chunk_transcripts = [transcript]
                current_chunk_start = (transcript.start_time // window_seconds) * window_seconds
        
        # Don't forget the last chunk
        if current_chunk_transcripts:
            chunks.append(self._create_chunk(
                current_chunk_transcripts,
                current_chunk_start,
                current_chunk_start + window_seconds
            ))
        
        return chunks
    
    def _create_chunk(self, transcripts: List, start_time: float, end_time: float) -> Dict:
        """Create a chunk with text and metadata"""
        
        # Combine transcript texts
        texts = []
        speakers = set()
        total_emotional = 0
        total_analytic = 0
        total_clout = 0
        total_authenticity = 0
        total_certainty = 0
        count = 0
        
        for t in transcripts:
            # Add speaker prefix if available
            if hasattr(t, 'speaker_tag') and t.speaker_tag:
                texts.append(f"{t.speaker_tag}: {t.transcript}")
                speakers.add(t.speaker_tag)
            else:
                texts.append(t.transcript)
            
            # Aggregate metrics
            if hasattr(t, 'emotional_tone_value'):
                total_emotional += t.emotional_tone_value or 0
                total_analytic += t.analytic_thinking_value or 0
                total_clout += t.clout_value or 0
                total_authenticity += t.authenticity_value or 0
                total_certainty += t.certainty_value or 0
                count += 1
        
        # Calculate averages
        if count > 0:
            avg_emotional = round(total_emotional / count, 2)
            avg_analytic = round(total_analytic / count, 2)
            avg_clout = round(total_clout / count, 2)
            avg_authenticity = round(total_authenticity / count, 2)
            avg_certainty = round(total_certainty / count, 2)
        else:
            avg_emotional = avg_analytic = avg_clout = avg_authenticity = avg_certainty = 0
        
        chunk_text = " ".join(texts)
        
        return {
            "text": chunk_text,
            "start_time": start_time,
            "end_time": end_time,
            "speaker_count": len(speakers),
            "speakers": list(speakers),
            "transcript_count": len(transcripts),
            "avg_emotional_tone": avg_emotional,
            "avg_analytic_thinking": avg_analytic,
            "avg_clout": avg_clout,
            "avg_authenticity": avg_authenticity,
            "avg_certainty": avg_certainty,
            "session_device_id": transcripts[0].session_device_id if transcripts else None
        }
    
    def index_session_chunks(self, session_device_id: int, transcripts: List) -> int:
        """
        Index all chunks from a session

        Returns:
            Number of chunks indexed
        """
        chunks = self.chunk_transcripts(transcripts)

        if not chunks:
            logger.warning(f"No chunks created for session_device {session_device_id}")
            return 0

        # Look up session_id from session_device_id
        session_id = None
        try:
            from tables.session_device import SessionDevice
            sd = SessionDevice.query.get(session_device_id)
            if sd:
                session_id = sd.session_id
        except Exception as e:
            logger.warning(f"Could not look up session_id for {session_device_id}: {e}")

        # Prepare data for ChromaDB
        documents = []
        metadatas = []
        ids = []

        for i, chunk in enumerate(chunks):
            chunk_id = f"sd{session_device_id}_chunk{i}_{int(chunk['start_time'])}"

            documents.append(chunk["text"])
            ids.append(chunk_id)

            # Prepare metadata (ChromaDB requires serializable types)
            metadata = {
                "session_device_id": session_device_id,
                "session_id": session_id,  # Add session_id for proper linking
                "start_time": chunk["start_time"],
                "end_time": chunk["end_time"],
                "speaker_count": chunk["speaker_count"],
                "speakers": json.dumps(chunk["speakers"]),  # Convert list to string
                "transcript_count": chunk["transcript_count"],
                "avg_emotional_tone": chunk["avg_emotional_tone"],
                "avg_analytic_thinking": chunk["avg_analytic_thinking"],
                "avg_clout": chunk["avg_clout"],
                "avg_authenticity": chunk["avg_authenticity"],
                "avg_certainty": chunk["avg_certainty"]
            }
            metadatas.append(metadata)
        
        # Add to ChromaDB
        try:
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"Indexed {len(chunks)} chunks for session_device {session_device_id}")
            return len(chunks)
        except Exception as e:
            logger.error(f"Error indexing session_device {session_device_id}: {e}")
            return 0
    
    def search(self, 
              query: str, 
              n_results: int = 5,
              session_device_id: Optional[int] = None,
              session_device_ids: Optional[List[int]] = None,
              min_emotional_tone: Optional[float] = None,
              min_analytic_thinking: Optional[float] = None) -> Dict:
        """
        Search for relevant discussion chunks
        
        Args:
            query: Search query text
            n_results: Number of results to return
            session_device_id: Filter by specific session_device
            min_emotional_tone: Filter by minimum emotional tone
            min_analytic_thinking: Filter by minimum analytic thinking
            
        Returns:
            Search results with documents and metadata
        """
        
        # Build where clause for filtering
        where = {}
        if session_device_id:
            where["session_device_id"] = session_device_id
        elif session_device_ids:  # Use list filter if provided
            where["session_device_id"] = {"$in": session_device_ids}
        if min_emotional_tone:
            where["avg_emotional_tone"] = {"$gte": min_emotional_tone}
        if min_analytic_thinking:
            where["avg_analytic_thinking"] = {"$gte": min_analytic_thinking}
        
        # Perform search
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where if where else None
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results['ids'][0])):
                result = {
                    "chunk_id": results['ids'][0][i],
                    "text": results['documents'][0][i],
                    "distance": results['distances'][0][i],
                    "metadata": results['metadatas'][0][i]
                }
                # Parse speakers back to list
                if 'speakers' in result['metadata']:
                    result['metadata']['speakers'] = json.loads(result['metadata']['speakers'])
                formatted_results.append(result)
            
            return {
                "query": query,
                "results": formatted_results,
                "total_found": len(formatted_results)
            }
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return {
                "query": query,
                "results": [],
                "total_found": 0,
                "error": str(e)
            }
    
    def find_similar_discussions(self, session_device_id: int, n_results: int = 5) -> Dict:
        """
        Find discussions similar to a given session
        
        Args:
            session_device_id: Reference session_device ID
            n_results: Number of similar discussions to return
            
        Returns:
            Similar discussion chunks from other sessions
        """
        
        # Get chunks from the reference session
        reference_chunks = self.collection.get(
            where={"session_device_id": session_device_id},
            limit=5  # Use first 5 chunks as reference
        )
        
        if not reference_chunks['ids']:
            return {
                "reference_session_device_id": session_device_id,
                "results": [],
                "message": "No chunks found for reference session"
            }
        
        # Combine reference texts
        reference_text = " ".join(reference_chunks['documents'])
        
        # Search for similar, excluding the reference session
        results = self.collection.query(
            query_texts=[reference_text[:1000]],  # Limit text length
            n_results=n_results * 2,  # Get more to filter
            where={"session_device_id": {"$ne": session_device_id}}
        )
        
        # Group by session and format
        session_groups = {}
        for i in range(len(results['ids'][0])):
            sd_id = results['metadatas'][0][i]['session_device_id']
            if sd_id not in session_groups:
                session_groups[sd_id] = {
                    "session_device_id": sd_id,
                    "chunks": [],
                    "avg_distance": 0
                }
            session_groups[sd_id]["chunks"].append({
                "text": results['documents'][0][i],
                "distance": results['distances'][0][i],
                "metadata": results['metadatas'][0][i]
            })
        
        # Calculate average distances and sort
        for sd_id in session_groups:
            chunks = session_groups[sd_id]["chunks"]
            session_groups[sd_id]["avg_distance"] = sum(c["distance"] for c in chunks) / len(chunks)
        
        sorted_sessions = sorted(session_groups.values(), key=lambda x: x["avg_distance"])[:n_results]
        
        return {
            "reference_session_device_id": session_device_id,
            "similar_sessions": sorted_sessions
        }
    
    def generate_insights(self, query: str, search_results: Dict,
                          retrieval_rationale: str = "") -> str:
        """
        Generate insights based on search results using GPT-4

        Args:
            query: Original search query
            search_results: Results from search() - can contain results, session_results, or speaker_results
            retrieval_rationale: Optional explanation of WHY these results were retrieved

        Returns:
            Generated insights text
        """

        # Get results from any of the result types
        results = (
            search_results.get('results') or
            search_results.get('session_results') or
            search_results.get('speaker_results') or
            []
        )

        if not results:
            return "No relevant discussions found for generating insights."

        # Prepare context from search results
        context_parts = []
        for i, result in enumerate(results[:5], 1):
            metadata = result.get('metadata', {})

            # Handle different result structures
            # Chunks have 'text', sessions have 'text_preview', speakers have 'text' or 'text_preview'
            text = result.get('text') or result.get('text_preview') or ''

            # Build time range string if available (chunks only)
            start_time = metadata.get('start_time')
            end_time = metadata.get('end_time')
            time_range = f", {start_time:.0f}-{end_time:.0f}s" if start_time is not None and end_time is not None else ""

            # Get session identifier
            session_id = (
                result.get('session_device_id') or
                metadata.get('session_device_id') or
                metadata.get('session_id') or
                'Unknown'
            )

            # Get speaker info (varies by result type)
            speakers = metadata.get('speakers') or metadata.get('speaker_alias') or result.get('speaker_alias') or 'Unknown'

            context_parts.append(
                f"Excerpt {i} (Session {session_id}{time_range}, "
                f"Speakers: {speakers}):\n"
                f"{text[:800] if text else 'No text available'}\n"
            )

        context = "\n".join(context_parts)

        # Build prompt with optional retrieval rationale
        if retrieval_rationale:
            prompt = f"""{retrieval_rationale}

---

Based on the retrieval context above and these discussion excerpts related to "{query}", provide insights about:
1. Common patterns or themes (explain findings in relation to WHY these sessions were selected)
2. Collaboration dynamics observed
3. Key discussion characteristics
4. Actionable recommendations

Context:
{context}

Ground your insights in the specific sessions and metrics above. Cite specific evidence (quotes, metrics) from the excerpts."""
        else:
            prompt = f"""Based on these discussion excerpts related to "{query}", provide insights about:
1. Common patterns or themes
2. Collaboration dynamics observed
3. Key discussion characteristics
4. Actionable recommendations

Context:
{context}

Provide specific, evidence-based insights with references to the excerpts."""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Using mini for cost efficiency
                messages=[
                    {"role": "system", "content": """You are an expert at analyzing discussion patterns and collaboration dynamics.

When providing insights:
- Include 2-3 specific quotes from the data that illustrate key patterns
- Make direct observations about what the data shows
- Reference specific metrics when relevant
- Focus on what's interesting, surprising, or actionable"""},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            return f"Error generating insights: {str(e)}"
    
    def get_collection_stats(self) -> Dict:
        """Get statistics about the indexed collection"""

        count = self.collection.count()

        # Get sample to understand the data
        if count > 0:
            sample = self.collection.get(limit=1)
            return {
                "total_chunks": count,
                "collection_name": "discussion_chunks",
                "sample_metadata_keys": list(sample['metadatas'][0].keys()) if sample['metadatas'] else []
            }

        return {
            "total_chunks": 0,
            "collection_name": "discussion_chunks",
            "sample_metadata_keys": []
        }

    # ============================================================
    # SESSION-LEVEL RAG METHODS (Hierarchical RAG)
    # ============================================================

    def index_session(self, session_device_id: int, serialized_doc: Dict) -> bool:
        """
        Index a session's concept map and 7C analysis for session-level search.

        Args:
            session_device_id: The session device ID
            serialized_doc: Output from SessionSerializer.serialize_for_embedding()
                           Contains 'text' and 'metadata' keys

        Returns:
            True if successful, False otherwise
        """
        if not serialized_doc or not serialized_doc.get('text'):
            logger.warning(f"No content to index for session_device {session_device_id}")
            return False

        doc_id = f"session_{session_device_id}"

        try:
            # Upsert - delete if exists, then add
            try:
                existing = self.session_collection.get(ids=[doc_id])
                if existing['ids']:
                    self.session_collection.delete(ids=[doc_id])
                    logger.info(f"Deleted existing session index for {session_device_id}")
            except Exception:
                pass  # May not exist

            # Prepare metadata (ensure all values are serializable)
            metadata = serialized_doc.get('metadata', {})
            clean_metadata = {}
            for key, value in metadata.items():
                if isinstance(value, (str, int, float, bool)):
                    clean_metadata[key] = value
                elif value is None:
                    clean_metadata[key] = ""
                else:
                    clean_metadata[key] = str(value)

            self.session_collection.add(
                documents=[serialized_doc['text']],
                metadatas=[clean_metadata],
                ids=[doc_id]
            )

            logger.info(f"Indexed session summary for session_device {session_device_id}")
            return True

        except Exception as e:
            logger.error(f"Error indexing session {session_device_id}: {e}")
            return False

    def search_sessions(self,
                       query: str,
                       n_results: int = 5,
                       session_device_ids: Optional[List[int]] = None,
                       filters: Optional[Dict] = None) -> Dict:
        """
        Search for sessions by discussion patterns, structure, or collaborative quality.

        Args:
            query: Natural language query (e.g., "discussions with strong argumentation")
            n_results: Number of results to return
            session_device_ids: Optional filter to specific sessions
            filters: Optional filters like:
                - discourse_type: "problem_solving", "exploratory", etc.
                - min_question_ratio: float
                - min_communication_score: int (0-100)

        Returns:
            Search results with session metadata
        """
        where_clauses = []

        # Session device filter
        if session_device_ids:
            where_clauses.append({"session_device_id": {"$in": session_device_ids}})

        # Apply additional filters
        if filters:
            if filters.get('discourse_type'):
                where_clauses.append({"discourse_type": filters['discourse_type']})
            if filters.get('min_question_ratio') is not None:
                where_clauses.append({"question_ratio": {"$gte": filters['min_question_ratio']}})
            if filters.get('min_challenge_ratio') is not None:
                where_clauses.append({"challenge_ratio": {"$gte": filters['min_challenge_ratio']}})
            if filters.get('min_node_count') is not None:
                where_clauses.append({"node_count": {"$gte": filters['min_node_count']}})

            # 7C dimension filters
            for dim in ['climate', 'communication', 'conflict', 'contribution', 'constructive']:
                min_key = f'min_{dim}_score'
                if filters.get(min_key) is not None:
                    where_clauses.append({f"{dim}_score": {"$gte": filters[min_key]}})

        # Build where clause
        where = None
        if len(where_clauses) == 1:
            where = where_clauses[0]
        elif len(where_clauses) > 1:
            where = {"$and": where_clauses}

        try:
            results = self.session_collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where
            )

            formatted_results = []
            for i in range(len(results['ids'][0])):
                result = {
                    "session_id": results['ids'][0][i],
                    "session_device_id": results['metadatas'][0][i].get('session_device_id'),
                    "text_preview": results['documents'][0][i][:500] + "..." if len(results['documents'][0][i]) > 500 else results['documents'][0][i],
                    "distance": results['distances'][0][i],
                    "metadata": results['metadatas'][0][i]
                }
                # Parse JSON fields back
                if 'cluster_names' in result['metadata']:
                    try:
                        result['metadata']['cluster_names'] = json.loads(
                            result['metadata']['cluster_names']
                        )
                    except:
                        result['metadata']['cluster_names'] = []

                formatted_results.append(result)

            return {
                "query": query,
                "search_level": "sessions",
                "results": formatted_results,
                "total_found": len(formatted_results)
            }

        except Exception as e:
            logger.error(f"Session search error: {e}")
            return {
                "query": query,
                "search_level": "sessions",
                "results": [],
                "total_found": 0,
                "error": str(e)
            }

    def find_similar_sessions(self, session_device_id: int, n_results: int = 5) -> Dict:
        """
        Find sessions with similar discussion structure to a reference session.

        Args:
            session_device_id: Reference session to find similar ones
            n_results: Number of similar sessions to return

        Returns:
            Similar sessions excluding the reference
        """
        doc_id = f"session_{session_device_id}"

        try:
            # Get the reference session's document
            ref_doc = self.session_collection.get(ids=[doc_id])

            if not ref_doc['documents']:
                return {
                    "reference_session_device_id": session_device_id,
                    "results": [],
                    "message": "Reference session not found in index"
                }

            ref_text = ref_doc['documents'][0]

            # Search for similar, excluding self
            results = self.session_collection.query(
                query_texts=[ref_text[:2000]],  # Limit query length
                n_results=n_results + 1  # Get extra to filter self
            )

            formatted_results = []
            for i in range(len(results['ids'][0])):
                if results['ids'][0][i] == doc_id:
                    continue  # Skip self

                result = {
                    "session_id": results['ids'][0][i],
                    "session_device_id": results['metadatas'][0][i].get('session_device_id'),
                    "distance": results['distances'][0][i],
                    "metadata": results['metadatas'][0][i]
                }
                # Parse cluster_names
                if 'cluster_names' in result['metadata']:
                    try:
                        result['metadata']['cluster_names'] = json.loads(
                            result['metadata']['cluster_names']
                        )
                    except:
                        result['metadata']['cluster_names'] = []

                formatted_results.append(result)

            return {
                "reference_session_device_id": session_device_id,
                "similar_sessions": formatted_results[:n_results]
            }

        except Exception as e:
            logger.error(f"Similar session search error: {e}")
            return {
                "reference_session_device_id": session_device_id,
                "similar_sessions": [],
                "error": str(e)
            }

    def get_session_collection_stats(self) -> Dict:
        """Get statistics about the session collection"""
        count = self.session_collection.count()

        if count > 0:
            sample = self.session_collection.get(limit=1)
            return {
                "total_sessions": count,
                "collection_name": "session_summaries",
                "sample_metadata_keys": list(sample['metadatas'][0].keys()) if sample['metadatas'] else []
            }

        return {
            "total_sessions": 0,
            "collection_name": "session_summaries",
            "sample_metadata_keys": []
        }

    def delete_session_index(self, session_device_id: int) -> bool:
        """Delete a session's index from ALL collections (comprehensive cleanup)"""
        deleted_count = 0
        errors = []

        # 0. Get speaker aliases BEFORE deletion (needed for speaker collection cleanup)
        speaker_aliases_to_update = []
        try:
            from tables.speaker import Speaker
            speakers = Speaker.query.filter_by(session_device_id=session_device_id).all()
            speaker_aliases_to_update = [s.alias for s in speakers if s.alias]
            logger.info(f"Found {len(speaker_aliases_to_update)} speakers to update after session deletion")
        except Exception as e:
            logger.warning(f"Could not get speaker aliases for cleanup: {e}")

        # 1. Delete from session_collection (legacy)
        try:
            doc_id = f"session_{session_device_id}"
            self.session_collection.delete(ids=[doc_id])
            deleted_count += 1
        except Exception as e:
            errors.append(f"session: {e}")

        # 2. Delete from transcript_collection
        try:
            doc_id = f"transcript_{session_device_id}"
            self.transcript_collection.delete(ids=[doc_id])
            deleted_count += 1
        except Exception as e:
            errors.append(f"transcript: {e}")

        # 3. Delete from concept_collection
        try:
            doc_id = f"concepts_{session_device_id}"
            self.concept_collection.delete(ids=[doc_id])
            deleted_count += 1
        except Exception as e:
            errors.append(f"concepts: {e}")

        # 4. Delete from seven_c_collection
        try:
            doc_id = f"7c_{session_device_id}"  # Must match index_session_7c() format
            self.seven_c_collection.delete(ids=[doc_id])
            deleted_count += 1
        except Exception as e:
            errors.append(f"seven_c: {e}")

        # 5. Delete chunks from collection (by session_device_id metadata filter)
        try:
            # Get all chunk IDs for this session
            chunks = self.collection.get(
                where={"session_device_id": session_device_id},
                include=[]
            )
            if chunks and chunks.get('ids'):
                self.collection.delete(ids=chunks['ids'])
                deleted_count += len(chunks['ids'])
                logger.info(f"Deleted {len(chunks['ids'])} chunks for session_device {session_device_id}")
        except Exception as e:
            errors.append(f"chunks: {e}")

        if errors:
            logger.warning(f"Some errors during RAG cleanup for session_device {session_device_id}: {errors}")

        logger.info(f"Deleted {deleted_count} items from RAG collections for session_device {session_device_id}")
        return len(errors) == 0

    # ============================================================
    # SEPARATE SESSION EMBEDDING METHODS (5-Collection Architecture)
    # ============================================================

    def index_session_transcript(self, session_device_id: int, text: str, metadata: Dict) -> bool:
        """Index a session's full transcript for topic-based search."""
        if not text:
            logger.warning(f"No transcript to index for session_device {session_device_id}")
            return False

        doc_id = f"transcript_{session_device_id}"

        try:
            # Upsert
            try:
                existing = self.transcript_collection.get(ids=[doc_id])
                if existing['ids']:
                    self.transcript_collection.delete(ids=[doc_id])
            except Exception:
                pass

            clean_metadata = self._clean_metadata(metadata)
            self.transcript_collection.add(
                documents=[text],
                metadatas=[clean_metadata],
                ids=[doc_id]
            )
            logger.info(f"Indexed transcript for session_device {session_device_id}")
            return True
        except Exception as e:
            logger.error(f"Error indexing transcript {session_device_id}: {e}")
            return False

    def index_session_concepts(self, session_device_id: int, text: str, metadata: Dict) -> bool:
        """Index a session's concept map structure for pattern queries."""
        if not text:
            logger.warning(f"No concepts to index for session_device {session_device_id}")
            return False

        doc_id = f"concepts_{session_device_id}"

        try:
            # Upsert
            try:
                existing = self.concept_collection.get(ids=[doc_id])
                if existing['ids']:
                    self.concept_collection.delete(ids=[doc_id])
            except Exception:
                pass

            clean_metadata = self._clean_metadata(metadata)
            self.concept_collection.add(
                documents=[text],
                metadatas=[clean_metadata],
                ids=[doc_id]
            )
            logger.info(f"Indexed concepts for session_device {session_device_id}")
            return True
        except Exception as e:
            logger.error(f"Error indexing concepts {session_device_id}: {e}")
            return False

    def index_session_7c(self, session_device_id: int, text: str, metadata: Dict) -> bool:
        """Index a session's 7C analysis for quality-based queries."""
        if not text:
            logger.warning(f"No 7C analysis to index for session_device {session_device_id}")
            return False

        doc_id = f"7c_{session_device_id}"

        try:
            # Upsert
            try:
                existing = self.seven_c_collection.get(ids=[doc_id])
                if existing['ids']:
                    self.seven_c_collection.delete(ids=[doc_id])
            except Exception:
                pass

            clean_metadata = self._clean_metadata(metadata)
            self.seven_c_collection.add(
                documents=[text],
                metadatas=[clean_metadata],
                ids=[doc_id]
            )
            logger.info(f"Indexed 7C analysis for session_device {session_device_id}")
            return True
        except Exception as e:
            logger.error(f"Error indexing 7C {session_device_id}: {e}")
            return False

    def _clean_metadata(self, metadata: Dict) -> Dict:
        """Clean metadata for ChromaDB (ensure all values are serializable)."""
        clean = {}
        for key, value in metadata.items():
            if isinstance(value, (str, int, float, bool)):
                clean[key] = value
            elif value is None:
                clean[key] = ""
            else:
                clean[key] = str(value)
        return clean

    def search_transcripts(self,
                          query: str,
                          n_results: int = 5,
                          session_device_ids: Optional[List[int]] = None,
                          filters: Optional[Dict] = None) -> Dict:
        """Search full session transcripts for topic/content queries."""
        return self._search_collection(
            collection=self.transcript_collection,
            collection_name="transcripts",
            query=query,
            n_results=n_results,
            session_device_ids=session_device_ids,
            filters=filters
        )

    def search_concepts(self,
                       query: str,
                       n_results: int = 5,
                       session_device_ids: Optional[List[int]] = None,
                       filters: Optional[Dict] = None) -> Dict:
        """Search concept map structures for argumentation/structure queries."""
        return self._search_collection(
            collection=self.concept_collection,
            collection_name="concepts",
            query=query,
            n_results=n_results,
            session_device_ids=session_device_ids,
            filters=filters
        )

    def search_7c(self,
                  query: str,
                  n_results: int = 5,
                  session_device_ids: Optional[List[int]] = None,
                  filters: Optional[Dict] = None) -> Dict:
        """Search 7C analyses for quality/collaboration queries."""
        return self._search_collection(
            collection=self.seven_c_collection,
            collection_name="seven_c",
            query=query,
            n_results=n_results,
            session_device_ids=session_device_ids,
            filters=filters
        )

    def _search_collection(self,
                          collection,
                          collection_name: str,
                          query: str,
                          n_results: int = 5,
                          session_device_ids: Optional[List[int]] = None,
                          filters: Optional[Dict] = None) -> Dict:
        """Generic search across any collection with filtering."""
        where_clauses = []

        if session_device_ids:
            where_clauses.append({"session_device_id": {"$in": session_device_ids}})

        if filters:
            for key, value in filters.items():
                if isinstance(value, dict):  # Already a filter expression
                    where_clauses.append({key: value})
                elif key.startswith('min_') and key.endswith('_score'):
                    # Convert min_X_score to X_score >= value
                    actual_field = key[4:]  # Remove 'min_' prefix
                    where_clauses.append({actual_field: {"$gte": value}})
                elif key.startswith('min_') and key.endswith('_ratio'):
                    # Convert min_X_ratio to X_ratio >= value
                    actual_field = key[4:]  # Remove 'min_' prefix
                    where_clauses.append({actual_field: {"$gte": value}})
                else:
                    where_clauses.append({key: value})

        where = None
        if len(where_clauses) == 1:
            where = where_clauses[0]
        elif len(where_clauses) > 1:
            where = {"$and": where_clauses}

        try:
            # Validate query is not empty - prevents OpenAI API 400 errors
            if not query or not str(query).strip():
                logger.warning(f"Empty query passed to {collection_name} search")
                return {
                    "results": [],
                    "total_results": 0,
                    "collection": collection_name,
                    "query": query,
                    "error": "Empty query"
                }

            results = collection.query(
                query_texts=[str(query).strip()],
                n_results=n_results,
                where=where
            )

            formatted_results = []
            for i in range(len(results['ids'][0])):
                result = {
                    "doc_id": results['ids'][0][i],
                    "session_device_id": results['metadatas'][0][i].get('session_device_id'),
                    "text_preview": results['documents'][0][i][:500] + "..." if len(results['documents'][0][i]) > 500 else results['documents'][0][i],
                    "distance": results['distances'][0][i],
                    "metadata": results['metadatas'][0][i]
                }
                # Parse JSON string fields back to native types
                if 'cluster_names' in result['metadata']:
                    try:
                        result['metadata']['cluster_names'] = json.loads(
                            result['metadata']['cluster_names']
                        )
                    except:
                        result['metadata']['cluster_names'] = []
                formatted_results.append(result)

            return {
                "query": query,
                "collection": collection_name,
                "results": formatted_results,
                "total_found": len(formatted_results)
            }

        except Exception as e:
            logger.error(f"Search error in {collection_name}: {e}")
            return {
                "query": query,
                "collection": collection_name,
                "results": [],
                "total_found": 0,
                "error": str(e)
            }

    def search_sessions_multi(self,
                             query: str,
                             collections: List[str] = None,
                             n_results: int = 5,
                             session_device_ids: Optional[List[int]] = None,
                             filters: Optional[Dict] = None) -> Dict:
        """
        Search multiple session collections and fuse results using RRF.

        Args:
            query: Search query
            collections: List of collections to search ['transcripts', 'concepts', 'seven_c']
                        If None, searches all three
            n_results: Number of results per collection before fusion
            session_device_ids: Optional filter
            filters: Optional metadata filters

        Returns:
            Fused results with scores from each collection
        """
        if collections is None:
            collections = ['transcripts', 'concepts', 'seven_c']

        # Search each collection
        results_by_collection = {}

        if 'transcripts' in collections:
            results_by_collection['transcripts'] = self.search_transcripts(
                query, n_results, session_device_ids, filters
            )
        if 'concepts' in collections:
            results_by_collection['concepts'] = self.search_concepts(
                query, n_results, session_device_ids, filters
            )
        if 'seven_c' in collections:
            results_by_collection['seven_c'] = self.search_7c(
                query, n_results, session_device_ids, filters
            )

        # Fuse results using Reciprocal Rank Fusion (RRF)
        fused = self._fuse_results(results_by_collection)

        return {
            "query": query,
            "collections_searched": collections,
            "fused_results": fused,
            "results_by_collection": results_by_collection
        }

    def _fuse_results(self, results_by_collection: Dict) -> List[Dict]:
        """
        Reciprocal Rank Fusion (RRF) across collections.
        RRF score = Σ 1/(k + rank) where k=60 is standard
        """
        from collections import defaultdict

        k = 60  # RRF constant
        scores = defaultdict(float)
        metadata_cache = {}  # Store metadata for each session

        for collection_name, result_dict in results_by_collection.items():
            results = result_dict.get('results', [])
            for rank, result in enumerate(results):
                session_id = result.get('session_device_id')
                if session_id is None:
                    continue

                # RRF score contribution
                scores[session_id] += 1 / (k + rank + 1)

                # Cache metadata (prefer most complete)
                if session_id not in metadata_cache:
                    metadata_cache[session_id] = result.get('metadata', {})

        # Sort by fused score and format results
        sorted_sessions = sorted(scores.items(), key=lambda x: -x[1])

        fused_results = []
        for session_id, score in sorted_sessions:
            fused_results.append({
                "session_device_id": session_id,
                "rrf_score": round(score, 4),
                "metadata": metadata_cache.get(session_id, {})
            })

        return fused_results

    def get_transcript_collection_stats(self) -> Dict:
        """Get statistics about the transcript collection."""
        return self._get_collection_stats(self.transcript_collection, "session_transcripts")

    def get_concept_collection_stats(self) -> Dict:
        """Get statistics about the concept collection."""
        return self._get_collection_stats(self.concept_collection, "session_concepts")

    def get_7c_collection_stats(self) -> Dict:
        """Get statistics about the 7C collection."""
        return self._get_collection_stats(self.seven_c_collection, "session_7c")

    def _get_collection_stats(self, collection, name: str) -> Dict:
        """Generic collection stats."""
        count = collection.count()
        if count > 0:
            sample = collection.get(limit=1)
            return {
                "total_documents": count,
                "collection_name": name,
                "sample_metadata_keys": list(sample['metadatas'][0].keys()) if sample['metadatas'] else []
            }
        return {
            "total_documents": 0,
            "collection_name": name,
            "sample_metadata_keys": []
        }

    # ============================================================
    # SPEAKER-LEVEL RAG METHODS (Cross-Session Analysis)
    # ============================================================

    def index_speaker(self, speaker_alias: str, serialized_doc: Dict) -> bool:
        """
        Index a speaker's cross-session profile.

        Args:
            speaker_alias: The speaker's alias (e.g., "Lex")
            serialized_doc: Output from SpeakerSerializer.serialize_speaker()
                           Contains 'text' and 'metadata' keys

        Returns:
            True if successful, False otherwise
        """
        if not serialized_doc or not serialized_doc.get('text'):
            logger.warning(f"No content to index for speaker {speaker_alias}")
            return False

        # Use alias as doc_id for easy upsert
        doc_id = f"speaker_{speaker_alias.lower().replace(' ', '_')}"

        try:
            # Upsert - delete if exists, then add
            try:
                existing = self.speaker_collection.get(ids=[doc_id])
                if existing['ids']:
                    self.speaker_collection.delete(ids=[doc_id])
                    logger.info(f"Deleted existing speaker index for {speaker_alias}")
            except Exception:
                pass  # May not exist

            # Prepare metadata (ensure all values are serializable)
            metadata = serialized_doc.get('metadata', {})
            clean_metadata = {}
            for key, value in metadata.items():
                if isinstance(value, (str, int, float, bool)):
                    clean_metadata[key] = value
                elif value is None:
                    clean_metadata[key] = ""
                else:
                    clean_metadata[key] = str(value)

            self.speaker_collection.add(
                documents=[serialized_doc['text']],
                metadatas=[clean_metadata],
                ids=[doc_id]
            )

            logger.info(f"Indexed speaker profile for {speaker_alias}")
            return True

        except Exception as e:
            logger.error(f"Error indexing speaker {speaker_alias}: {e}")
            return False

    def search_speakers(self,
                       query: str,
                       n_results: int = 5,
                       filters: Optional[Dict] = None) -> Dict:
        """
        Search for speakers by engagement patterns or characteristics.

        Args:
            query: Natural language query (e.g., "speakers who ask many questions")
            n_results: Number of results to return
            filters: Optional filters like:
                - min_session_count: int
                - min_question_count: int

        Returns:
            Search results with speaker metadata
        """
        where_clauses = []

        # Apply filters
        if filters:
            if filters.get('min_session_count') is not None:
                where_clauses.append({"session_count": {"$gte": filters['min_session_count']}})
            if filters.get('min_question_count') is not None:
                where_clauses.append({"question_count": {"$gte": filters['min_question_count']}})

        # Build where clause
        where = None
        if len(where_clauses) == 1:
            where = where_clauses[0]
        elif len(where_clauses) > 1:
            where = {"$and": where_clauses}

        try:
            results = self.speaker_collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where
            )

            formatted_results = []
            for i in range(len(results['ids'][0])):
                result = {
                    "speaker_id": results['ids'][0][i],
                    "speaker_alias": results['metadatas'][0][i].get('speaker_alias'),
                    "text_preview": results['documents'][0][i][:500] + "..." if len(results['documents'][0][i]) > 500 else results['documents'][0][i],
                    "distance": results['distances'][0][i],
                    "metadata": results['metadatas'][0][i]
                }
                formatted_results.append(result)

            return {
                "query": query,
                "search_level": "speakers",
                "results": formatted_results,
                "total_found": len(formatted_results)
            }

        except Exception as e:
            logger.error(f"Speaker search error: {e}")
            return {
                "query": query,
                "search_level": "speakers",
                "results": [],
                "total_found": 0,
                "error": str(e)
            }

    def get_speaker_collection_stats(self) -> Dict:
        """Get statistics about the speaker collection"""
        count = self.speaker_collection.count()

        if count > 0:
            sample = self.speaker_collection.get(limit=1)
            return {
                "total_speakers": count,
                "collection_name": "speaker_profiles",
                "sample_metadata_keys": list(sample['metadatas'][0].keys()) if sample['metadatas'] else []
            }

        return {
            "total_speakers": 0,
            "collection_name": "speaker_profiles",
            "sample_metadata_keys": []
        }

    def delete_speaker_index(self, speaker_alias: str) -> bool:
        """Delete a speaker's index from the collection"""
        doc_id = f"speaker_{speaker_alias.lower().replace(' ', '_')}"
        try:
            self.speaker_collection.delete(ids=[doc_id])
            logger.info(f"Deleted speaker index for {speaker_alias}")
            return True
        except Exception as e:
            logger.error(f"Error deleting speaker index: {e}")
            return False

    def get_all_collection_stats(self) -> Dict:
        """Get statistics about all collections (5-collection architecture)"""
        return {
            "chunks": self.get_collection_stats(),
            "transcripts": self.get_transcript_collection_stats(),
            "concepts": self.get_concept_collection_stats(),
            "seven_c": self.get_7c_collection_stats(),
            "sessions_legacy": self.get_session_collection_stats(),
            "speakers": self.get_speaker_collection_stats()
        }

    # ============================================================
    # ULTRA RAG: METRIC-FIRST RETRIEVAL
    # ============================================================

    def get_sessions_by_metrics(
        self,
        metric_filters: Dict[str, tuple],
        n_results: int = 10,
        sort_by: Optional[str] = None,
        descending: bool = True
    ) -> List[Dict]:
        """
        Get sessions filtered and sorted by metrics (database-first approach).

        Args:
            metric_filters: Dict of {metric_name: (operator, value)}
                e.g., {'debate_score': ('>=', 3), 'communication_score': ('>=', 70)}
            n_results: Maximum results to return
            sort_by: Metric to sort by (e.g., 'debate_score')
            descending: Sort order

        Returns:
            List of session dicts with metrics
        """
        from tables.concept_session import ConceptSession
        from tables.concept_edge import ConceptEdge
        from tables.concept_node import ConceptNode
        from tables.seven_cs_analysis import SevenCsAnalysis
        from tables.session_device import SessionDevice
        from tables.session import Session

        # Get all sessions with concept maps
        sessions = SessionDevice.query.all()
        results = []

        for sd in sessions:
            # Get session name via separate query
            session = Session.query.get(sd.session_id)
            session_name = session.name if session else f"Session {sd.id}"

            # Compute argumentation metrics
            concept_session = ConceptSession.query.filter_by(
                session_device_id=sd.id
            ).first()

            metrics = {
                'session_device_id': sd.id,
                'session_id': sd.session_id,  # For frontend URL routing
                'session_name': session_name,
                'has_concept_map': bool(concept_session)
            }

            if concept_session:
                edges = ConceptEdge.query.filter_by(
                    concept_session_id=concept_session.id
                ).all()
                nodes = ConceptNode.query.filter_by(
                    concept_session_id=concept_session.id
                ).all()

                # Compute derived metrics
                edge_counts = {}
                for edge in edges:
                    edge_counts[edge.edge_type] = edge_counts.get(edge.edge_type, 0) + 1

                # Cluster info
                cluster_count = len(concept_session.clusters) if concept_session.clusters else 0
                cluster_names = [c.cluster_name for c in concept_session.clusters[:5]] if concept_session.clusters else []

                metrics.update({
                    'debate_score': edge_counts.get('challenges', 0) + edge_counts.get('contrasts_with', 0),
                    'challenge_count': edge_counts.get('challenges', 0),
                    'reasoning_depth': edge_counts.get('builds_on', 0) + edge_counts.get('elaborates', 0),
                    'support_count': edge_counts.get('supports', 0),
                    'edge_count': len(edges),
                    'node_count': len(nodes),
                    'question_count': sum(1 for n in nodes if n.node_type == 'question'),
                    'problem_count': sum(1 for n in nodes if n.node_type == 'problem'),
                    'solution_count': sum(1 for n in nodes if n.node_type == 'solution'),
                    'cluster_count': cluster_count,
                    'cluster_names': cluster_names
                })

            # Get 7C scores from analysis
            seven_cs_analysis = SevenCsAnalysis.query.filter_by(session_device_id=sd.id).first()
            if seven_cs_analysis and seven_cs_analysis.analysis_summary:
                summary = seven_cs_analysis.analysis_summary
                metrics.update({
                    'communication_score': summary.get('communication', {}).get('score', 0),
                    'climate_score': summary.get('climate', {}).get('score', 0),
                    'contribution_score': summary.get('contribution', {}).get('score', 0),
                    'conflict_score': summary.get('conflict', {}).get('score', 0),
                    'constructive_score': summary.get('constructive', {}).get('score', 0)
                })

            results.append(metrics)

        # Apply filters
        filtered = []
        for r in results:
            passes = True
            for metric, (operator, value) in metric_filters.items():
                metric_value = r.get(metric, 0)
                if operator == '>=' and metric_value < value:
                    passes = False
                elif operator == '>' and metric_value <= value:
                    passes = False
                elif operator == '<=' and metric_value > value:
                    passes = False
                elif operator == '<' and metric_value >= value:
                    passes = False
                elif operator == '==' and metric_value != value:
                    passes = False
            if passes:
                filtered.append(r)

        # Sort
        if sort_by and sort_by in filtered[0] if filtered else False:
            filtered.sort(key=lambda x: x.get(sort_by, 0), reverse=descending)

        return filtered[:n_results]

    def get_contrastive_sessions(
        self,
        metric_name: str,
        n_high: int = 3,
        n_low: int = 3
    ) -> tuple:
        """
        Get sessions with highest and lowest values for a metric.
        Used for contrastive analysis ("why" queries).

        Returns:
            (high_sessions, low_sessions) - Lists of session_device_ids
        """
        all_sessions = self.get_sessions_by_metrics({}, n_results=100)

        # Sort by metric
        sorted_sessions = sorted(
            [s for s in all_sessions if s.get(metric_name) is not None],
            key=lambda x: x.get(metric_name, 0),
            reverse=True
        )

        high_sessions = [s['session_device_id'] for s in sorted_sessions[:n_high]]
        low_sessions = [s['session_device_id'] for s in sorted_sessions[-n_low:]]

        return high_sessions, low_sessions

    def hybrid_session_search(
        self,
        query: str,
        metric_filters: Dict[str, tuple],
        sort_metric: Optional[str] = None,
        n_results: int = 5,
        metric_weight: float = 0.4,
        semantic_weight: float = 0.6
    ) -> List[Dict]:
        """
        Hybrid search combining metric filtering with semantic search.

        Args:
            query: Semantic search query
            metric_filters: Filters to apply before semantic search
            sort_metric: Metric to prioritize in ranking
            n_results: Final number of results
            metric_weight: Weight for metric-based ranking (0-1)
            semantic_weight: Weight for semantic ranking (0-1)

        Returns:
            Combined and re-ranked results
        """
        # Step 1: Get sessions passing metric filters
        metric_results = self.get_sessions_by_metrics(
            metric_filters,
            n_results=20,  # Get more for re-ranking
            sort_by=sort_metric
        )

        if not metric_results:
            # Fall back to pure semantic search - extract list from dict
            semantic_fallback = self.search_sessions_multi(query, n_results=n_results)
            fused = semantic_fallback.get('fused_results', [])
            # Convert to expected format
            return [{
                'session_device_id': r.get('session_device_id'),
                'hybrid_score': r.get('rrf_score', 0),
                'metric_score': 0,
                'semantic_score': r.get('rrf_score', 0),
                'metrics': r.get('metadata', {})
            } for r in fused]

        # Step 2: Get semantic search results
        semantic_results = self.search_sessions_multi(
            query,
            collections=['transcripts', 'concepts', 'seven_c'],
            n_results=20
        )

        # Step 3: Compute hybrid scores
        session_scores = {}

        # Metric-based scores (higher metric = higher score)
        for rank, session in enumerate(metric_results):
            sid = session['session_device_id']
            session_scores[sid] = {
                'metric_score': 1.0 / (rank + 1),  # RRF-style
                'semantic_score': 0,
                'metrics': session
            }

        # Semantic scores
        for rank, result in enumerate(semantic_results.get('fused_results', [])):
            sid = result.get('session_device_id')
            if sid in session_scores:
                session_scores[sid]['semantic_score'] = 1.0 / (rank + 1)
            else:
                session_scores[sid] = {
                    'metric_score': 0,
                    'semantic_score': 1.0 / (rank + 1),
                    'metrics': result.get('metadata', {})
                }

        # Step 4: Compute final scores and rank
        final_results = []
        for sid, scores in session_scores.items():
            final_score = (
                metric_weight * scores['metric_score'] +
                semantic_weight * scores['semantic_score']
            )
            final_results.append({
                'session_device_id': sid,
                'hybrid_score': final_score,
                'metric_score': scores['metric_score'],
                'semantic_score': scores['semantic_score'],
                'metrics': scores['metrics']
            })

        final_results.sort(key=lambda x: x['hybrid_score'], reverse=True)

        return final_results[:n_results]

    def generate_ultra_insights(
        self,
        query: str,
        focus_area: str,
        session_contexts: str,
        high_context: str = "",
        low_context: str = "",
        speaker_context: str = "",
        speaker_name: str = "",
        retrieval_rationale: str = "",
        artifact_context: str = "",
        grounding_strategy: str = ""
    ) -> str:
        """
        Generate insights using Ultra RAG architecture with THREE-LAYER response.

        THREE-LAYER RESPONSE MODEL:
        - GROUND: Reference artifacts (concept maps, 7C scores) - what user sees in UI
        - ENRICH: Cite transcripts with quotes and timestamps - add depth
        - EXTEND: Provide original insight - patterns artifacts might miss

        Args:
            query: Original user query
            focus_area: 'argumentation', 'collaboration', 'speaker', etc.
            session_contexts: Transcript context for ENRICH layer
            high_context: For contrastive - high metric sessions
            low_context: For contrastive - low metric sessions
            speaker_context: For speaker analysis
            speaker_name: Speaker being analyzed
            retrieval_rationale: Explanation of WHY these sessions were retrieved
            artifact_context: Artifact descriptions for GROUND layer (concept maps, 7C scores)
            grounding_strategy: How to ground response in user-visible artifacts
        """
        # Use three-layer response if artifact context provided
        if artifact_context:
            return self._generate_three_layer_insights(
                query=query,
                focus_area=focus_area,
                artifact_context=artifact_context,
                transcript_context=session_contexts,
                grounding_strategy=grounding_strategy,
                retrieval_rationale=retrieval_rationale
            )

        # Fall back to legacy prompt structure for contrastive and speaker queries
        from insight_prompts import get_system_prompt, get_user_prompt

        # Determine intent from context
        intent = 'analyze'
        if high_context and low_context:
            intent = 'explain'
        elif speaker_context:
            intent = 'describe'

        system_prompt = get_system_prompt(focus_area if not (high_context and low_context) else 'contrastive')
        user_prompt = get_user_prompt(
            focus_area=focus_area,
            intent=intent,
            query=query,
            session_contexts=session_contexts,
            high_context=high_context,
            low_context=low_context,
            speaker_context=speaker_context,
            speaker_name=speaker_name,
            retrieval_rationale=retrieval_rationale
        )

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Ultra insights generation failed: {e}")
            return f"Error generating insights: {str(e)}"

    def _generate_three_layer_insights(
        self,
        query: str,
        focus_area: str,
        artifact_context: str,
        transcript_context: str,
        grounding_strategy: str = "",
        retrieval_rationale: str = ""
    ) -> str:
        """
        Generate insights using the THREE-LAYER response framework.

        GROUND → ENRICH → EXTEND

        This creates responses that:
        1. Reference what user sees in UI (artifacts) - creates common ground
        2. Add depth with transcript quotes - shows the actual dialogue
        3. Provide original insight - patterns artifacts might miss
        """
        from insight_prompts import get_smart_assistant_prompt, build_grounding_instructions

        # Determine which artifacts are relevant based on focus area
        primary_artifacts = []
        if focus_area == 'argumentation':
            primary_artifacts = ['concept_map']
        elif focus_area == 'collaboration':
            primary_artifacts = ['7c', 'concept_map']
        elif focus_area == 'speaker':
            primary_artifacts = ['speakers', 'concept_map']
        elif focus_area == 'evolution':
            primary_artifacts = ['evolution', 'concept_map']
        else:
            primary_artifacts = ['concept_map', '7c']

        # Build grounding instructions based on artifacts
        grounding_instructions = build_grounding_instructions(
            primary_artifacts=primary_artifacts,
            grounding_strategy=grounding_strategy
        )

        # Get smart assistant prompts
        system_prompt, user_prompt = get_smart_assistant_prompt(
            query=query,
            grounding_strategy=grounding_instructions,
            artifact_description=artifact_context,
            transcript_context=transcript_context,
            focus_area=focus_area
        )

        # Add retrieval rationale to user prompt if provided
        if retrieval_rationale:
            user_prompt = f"{retrieval_rationale}\n\n{user_prompt}"

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Three-layer insights generation failed: {e}")
            return f"Error generating insights: {str(e)}"