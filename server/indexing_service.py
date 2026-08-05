"""
Unified re-indexing service for RAG search.

Consolidates duplicate re-indexing logic from seven_cs_service.py,
concept_generation_service.py, and concept_routes.py into a single entry point.

Writes to the 3 active collections (session_transcripts, session_concepts,
session_7c) used by the agent's search_for_sessions tool.  The legacy
session_summaries collection is no longer updated.
"""
import logging

logger = logging.getLogger(__name__)


def reindex_session(session_device_id: int, reason: str = "unknown",
                    chroma_path: str = None) -> bool:
    """
    Re-index a session and its speakers for RAG search.

    Single entry point for all session re-indexing after data changes
    (7C analysis, concept generation, clustering, etc.).

    Args:
        session_device_id: ID of the session device to re-index
        reason: Why re-indexing was triggered (for logging)
        chroma_path: ChromaDB persist directory (for study isolation)

    Returns:
        True if indexing succeeded, False otherwise.
    """
    try:
        from session_serializer import SessionSerializer
        from rag_service import RAGService

        serializer = SessionSerializer()
        rag_service = RAGService(persist_directory=chroma_path or "./chroma_db")

        docs = serializer.serialize_all(session_device_id)

        if not docs:
            logger.warning(f"[Indexing] No data to index for session {session_device_id} (reason: {reason})")
            return False

        metadata = docs.get('metadata', {})
        success = True
        indexed = []

        if docs.get('transcript'):
            if rag_service.index_session_transcript(session_device_id, docs['transcript'], metadata):
                indexed.append('transcript')
            else:
                success = False

        if docs.get('concepts'):
            if rag_service.index_session_concepts(session_device_id, docs['concepts'], metadata):
                indexed.append('concepts')
            else:
                success = False

        if docs.get('seven_c'):
            if rag_service.index_session_7c(session_device_id, docs['seven_c'], metadata):
                indexed.append('7c')
            else:
                success = False

        if indexed:
            logger.info(
                f"[Indexing] Session {session_device_id} re-indexed (reason: {reason}) — "
                f"collections: {', '.join(indexed)}, "
                f"nodes: {metadata.get('node_count', 0)}, "
                f"transcripts: {metadata.get('transcript_count', 0)}"
            )
            _reindex_speakers_for_session(session_device_id, rag_service)
        else:
            logger.error(f"[Indexing] Failed to re-index session {session_device_id} (reason: {reason})")

        return success

    except Exception as e:
        logger.error(f"[Indexing] Error re-indexing session {session_device_id} (reason: {reason}): {e}", exc_info=True)
        return False


def _reindex_speakers_for_session(session_device_id: int, rag_service=None):
    """
    Re-index all speakers in a session after session data changes.

    Uses the Speaker table to find aliases (consistent across all callers).
    """
    try:
        from tables.speaker import Speaker
        from speaker_serializer import SpeakerSerializer

        if rag_service is None:
            from rag_service import RAGService
            rag_service = RAGService()

        speakers = Speaker.query.filter_by(session_device_id=session_device_id).all()
        aliases = set(s.alias for s in speakers if s.alias)

        if not aliases:
            return

        logger.info(f"[Indexing] Re-indexing {len(aliases)} speakers for session {session_device_id}")

        serializer = SpeakerSerializer()

        for alias in aliases:
            try:
                serialized = serializer.serialize_speaker(alias)
                if serialized:
                    rag_service.index_speaker(alias, serialized)
                    logger.debug(f"[Indexing]   Re-indexed speaker: {alias}")
            except Exception as e:
                logger.error(f"[Indexing]   Failed to re-index speaker {alias}: {e}")

    except Exception as e:
        logger.error(f"[Indexing] Error re-indexing speakers for session {session_device_id}: {e}", exc_info=True)
