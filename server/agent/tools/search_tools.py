"""
Search Tools

Semantic search tools that use ChromaDB collections.
"""

import logging
from typing import Dict, List, Optional

from .base import BaseTool, ToolResult, ParameterSpec, ToolCategory

logger = logging.getLogger(__name__)


def get_session_display_names(session_device_ids: List[int]) -> Dict[int, Dict[str, str]]:
    """
    Get display names (session name + device name) for a list of device IDs.

    Returns:
        Dict mapping device_id to {session_name, device_name, display_name}
    """
    if not session_device_ids:
        return {}

    try:
        from app import db
        from tables.session import Session
        from tables.session_device import SessionDevice

        results = db.session.query(
            SessionDevice.id.label('device_id'),
            Session.name.label('session_name'),
            SessionDevice.name.label('device_name')
        ).join(
            Session, Session.id == SessionDevice.session_id
        ).filter(
            SessionDevice.id.in_(session_device_ids)
        ).all()

        name_map = {}
        for device_id, session_name, device_name in results:
            # Create display name showing both session and device
            if device_name and device_name != session_name:
                display_name = f"{session_name} ({device_name})"
            else:
                display_name = session_name or f"Session {device_id}"

            name_map[device_id] = {
                'session_name': session_name or f"Session {device_id}",
                'device_name': device_name or f"Device {device_id}",
                'display_name': display_name
            }

        return name_map
    except Exception as e:
        logger.error(f"Failed to get session display names: {e}")
        return {}


class SearchTranscriptChunksTool(BaseTool):
    """Search semantic transcript chunks."""

    name = "search_transcript_chunks"
    description = (
        "Search semantically-chunked transcript segments by topic or content. "
        "Returns relevant discussion excerpts with speaker information. "
        "Use this to find what was said about a specific topic."
    )
    category = ToolCategory.SEARCH
    parameters = {
        "query": ParameterSpec(
            name="query",
            type="str",
            description="Search query - what to look for in transcripts",
            required=True
        ),
        "session_device_ids": ParameterSpec(
            name="session_device_ids",
            type="list",
            description="Optional list of session device IDs to filter",
            required=False,
            default=None
        ),
        "n_results": ParameterSpec(
            name="n_results",
            type="int",
            description="Maximum number of results to return",
            required=False,
            default=5
        ),
        "speaker": ParameterSpec(
            name="speaker",
            type="str",
            description="Optional speaker name to filter by",
            required=False,
            default=None
        )
    }

    def execute(self, query: str, session_device_ids: List[int] = None,
                n_results: int = 5, speaker: str = None) -> ToolResult:
        """Execute semantic chunk search."""
        try:
            from graph_rag import GraphIndexer
            indexer = GraphIndexer()

            results = indexer.search_semantic_chunks(
                query=query,
                session_device_ids=session_device_ids,
                n_results=n_results,
                speaker=speaker
            )

            return ToolResult(
                success=True,
                data={
                    "query": query,
                    "result_count": len(results),
                    "results": results
                },
                metadata={
                    "session_filter": session_device_ids,
                    "speaker_filter": speaker
                }
            )
        except Exception as e:
            logger.error(f"Error searching transcript chunks: {e}")
            return ToolResult(success=False, data=None, error=str(e))


class SearchConceptNodesTool(BaseTool):
    """Search individual concept nodes."""

    name = "search_concept_nodes"
    description = (
        "Search individual concept nodes (ideas, questions, hypotheses, etc.) "
        "by semantic similarity. Returns specific concepts with speaker attribution. "
        "Use this to find specific ideas or questions about a topic."
    )
    category = ToolCategory.SEARCH
    parameters = {
        "query": ParameterSpec(
            name="query",
            type="str",
            description="The concept to search for",
            required=True
        ),
        "session_device_ids": ParameterSpec(
            name="session_device_ids",
            type="list",
            description="Optional list of session device IDs to filter",
            required=False,
            default=None
        ),
        "node_types": ParameterSpec(
            name="node_types",
            type="list",
            description="Optional list of node types to filter (idea, question, hypothesis, etc.)",
            required=False,
            default=None
        ),
        "n_results": ParameterSpec(
            name="n_results",
            type="int",
            description="Maximum number of results to return",
            required=False,
            default=10
        )
    }

    def execute(self, query: str, session_device_ids: List[int] = None,
                node_types: List[str] = None, n_results: int = 10) -> ToolResult:
        """Execute concept node search."""
        try:
            from graph_rag import GraphIndexer
            indexer = GraphIndexer()

            results = indexer.search_concept_nodes(
                query=query,
                session_device_ids=session_device_ids,
                node_types=node_types,
                n_results=n_results
            )

            return ToolResult(
                success=True,
                data={
                    "query": query,
                    "result_count": len(results),
                    "results": results
                },
                metadata={
                    "session_filter": session_device_ids,
                    "type_filter": node_types
                }
            )
        except Exception as e:
            logger.error(f"Error searching concept nodes: {e}")
            return ToolResult(success=False, data=None, error=str(e))


class SearchConceptClustersTool(BaseTool):
    """Search concept clusters (themes)."""

    name = "search_concept_clusters"
    description = (
        "Search thematic clusters by topic. Clusters represent coherent themes "
        "in discussions. Returns high-level topic areas with summaries. "
        "Use this to find sessions that discussed a particular theme."
    )
    category = ToolCategory.SEARCH
    parameters = {
        "query": ParameterSpec(
            name="query",
            type="str",
            description="The theme to search for",
            required=True
        ),
        "session_device_ids": ParameterSpec(
            name="session_device_ids",
            type="list",
            description="Optional list of session device IDs to filter",
            required=False,
            default=None
        ),
        "n_results": ParameterSpec(
            name="n_results",
            type="int",
            description="Maximum number of results to return",
            required=False,
            default=5
        )
    }

    def execute(self, query: str, session_device_ids: List[int] = None,
                n_results: int = 5) -> ToolResult:
        """Execute cluster search."""
        try:
            from graph_rag import GraphIndexer
            indexer = GraphIndexer()

            results = indexer.search_concept_clusters(
                query=query,
                session_device_ids=session_device_ids,
                n_results=n_results
            )

            return ToolResult(
                success=True,
                data={
                    "query": query,
                    "result_count": len(results),
                    "results": results
                },
                metadata={
                    "session_filter": session_device_ids
                }
            )
        except Exception as e:
            logger.error(f"Error searching concept clusters: {e}")
            return ToolResult(success=False, data=None, error=str(e))


class SearchSessionsTool(BaseTool):
    """Search sessions using existing RAG collections."""

    name = "search_sessions"
    description = (
        "Search across sessions for relevant content. Uses multiple collections "
        "(transcripts, concepts, 7C analysis) with fusion ranking. "
        "Use this for broad queries about session content."
    )
    category = ToolCategory.SEARCH
    parameters = {
        "query": ParameterSpec(
            name="query",
            type="str",
            description="Search query",
            required=True
        ),
        "session_device_ids": ParameterSpec(
            name="session_device_ids",
            type="list",
            description="Optional list of session device IDs to filter",
            required=False,
            default=None
        ),
        "n_results": ParameterSpec(
            name="n_results",
            type="int",
            description="Maximum number of results to return",
            required=False,
            default=5
        )
    }

    def execute(self, query: str, session_device_ids: List[int] = None,
                n_results: int = 5) -> ToolResult:
        """Execute session search using RAGService."""
        # Validate query is not empty
        if not query or not query.strip():
            return ToolResult(
                success=False,
                data=None,
                error="Query cannot be empty. Please provide a search term."
            )

        try:
            from rag_service import RAGService
            rag = RAGService()

            # Use the multi-collection search
            raw_results = rag.search_sessions_multi(
                query=query,
                n_results=n_results,
                session_device_ids=session_device_ids
            )

            # Flatten results for easier agent access
            fused_results = raw_results.get('fused_results', [])

            # Build a simplified results list with session_device_id at top level
            # Get all unique session IDs for name lookup
            result_session_ids = list(set(
                item.get('session_device_id') for item in fused_results
                if item.get('session_device_id')
            ))
            session_names = get_session_display_names(result_session_ids)

            simplified_results = []
            for item in fused_results:
                session_id = item.get('session_device_id')
                # Get both session name and device name
                names = session_names.get(session_id, {})
                simplified_results.append({
                    "id": session_id,  # Alias for LLM convenience
                    "session_device_id": session_id,
                    "session_name": names.get('session_name', item.get('metadata', {}).get('session_name', 'Unknown')),
                    "device_name": names.get('device_name', ''),
                    "display_name": names.get('display_name', f"Session {session_id}"),  # Shows "Session (Device)"
                    "rrf_score": item.get('rrf_score', 0),
                    "text_preview": item.get('text_preview', ''),
                    "collections_matched": item.get('collections', [])
                })

            # Also extract unique session IDs for easy reference
            unique_session_ids = list(set(
                r['session_device_id'] for r in simplified_results
                if r['session_device_id'] is not None
            ))

            return ToolResult(
                success=True,
                data={
                    "query": query,
                    "result_count": len(simplified_results),
                    "session_device_ids": unique_session_ids,  # Easy access to all IDs
                    "results": simplified_results,  # Flat structure with session_device_id at top
                    "collections_searched": raw_results.get('collections_searched', [])
                },
                metadata={
                    "session_filter": session_device_ids
                }
            )
        except Exception as e:
            logger.error(f"Error searching sessions: {e}")
            return ToolResult(success=False, data=None, error=str(e))


class SearchSpeakersTool(BaseTool):
    """Search speaker profiles with optional session filtering."""

    name = "search_speakers"
    description = (
        "Search speaker profiles. Can search across all sessions or filter "
        "to specific sessions. Returns speaker contribution metrics. "
        "Use this to find speakers who contributed in specific ways."
    )
    category = ToolCategory.SEARCH
    parameters = {
        "query": ParameterSpec(
            name="query",
            type="str",
            description="Speaker characteristics to search for",
            required=True
        ),
        "session_device_id": ParameterSpec(
            name="session_device_id",
            type="int",
            description="Optional session ID to filter speakers to a specific session",
            required=False,
            default=None
        ),
        "n_results": ParameterSpec(
            name="n_results",
            type="int",
            description="Maximum number of results to return",
            required=False,
            default=5
        )
    }

    def execute(self, query: str, session_device_id: int = None,
                n_results: int = 5) -> ToolResult:
        """Execute speaker search with optional session filtering."""
        try:
            # If session_device_id provided, get session-specific speaker data
            if session_device_id:
                return self._search_session_speakers(query, session_device_id)

            # Otherwise, use cross-session speaker profiles
            from rag_service import RAGService
            rag = RAGService()

            results = rag.search_speakers(
                query=query,
                n_results=n_results
            )

            return ToolResult(
                success=True,
                data={
                    "query": query,
                    "result_count": len(results.get('results', [])) if results else 0,
                    "results": results
                }
            )
        except Exception as e:
            logger.error(f"Error searching speakers: {e}")
            return ToolResult(success=False, data=None, error=str(e))

    def _search_session_speakers(self, query: str, session_device_id: int) -> ToolResult:
        """Get speaker data for a specific session from database."""
        try:
            from app import db
            from sqlalchemy import func
            from tables.speaker import Speaker
            from tables.transcript import Transcript

            # Query speakers for this session with their metrics
            speaker_data = db.session.query(
                Speaker.id,
                Speaker.alias,
                func.count(Transcript.id).label('utterances'),
                func.sum(Transcript.word_count).label('total_words'),
                func.avg(Transcript.emotional_tone_value).label('avg_tone')
            ).join(
                Transcript, Transcript.speaker_id == Speaker.id
            ).filter(
                Transcript.session_device_id == session_device_id
            ).group_by(
                Speaker.id, Speaker.alias
            ).order_by(
                func.sum(Transcript.word_count).desc()
            ).all()

            if not speaker_data:
                return ToolResult(
                    success=True,
                    data={
                        "query": query,
                        "session_device_id": session_device_id,
                        "result_count": 0,
                        "results": [],
                        "note": "No speakers found for this session"
                    }
                )

            # Format results
            results = []
            for speaker in speaker_data:
                results.append({
                    "speaker_id": speaker.id,
                    "speaker_alias": speaker.alias,
                    "utterances": speaker.utterances,
                    "total_words": int(speaker.total_words) if speaker.total_words else 0,
                    "avg_emotional_tone": round(float(speaker.avg_tone), 2) if speaker.avg_tone else None,
                    "session_device_id": session_device_id
                })

            # Identify most active speaker
            most_active = results[0] if results else None

            return ToolResult(
                success=True,
                data={
                    "query": query,
                    "session_device_id": session_device_id,
                    "result_count": len(results),
                    "most_active_speaker": most_active,
                    "results": results
                },
                metadata={
                    "session_device_id": session_device_id,
                    "source": "database_direct"
                }
            )

        except Exception as e:
            logger.error(f"Error getting session speakers: {e}")
            return ToolResult(success=False, data=None, error=str(e))
