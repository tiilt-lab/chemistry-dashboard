import logging
from typing import List
from rag_service import RAGService
import database

logger = logging.getLogger(__name__)

class RAGAutoIndexer:
    def __init__(self):
        self.rag = RAGService()
        self.pending_transcripts = {}  # session_device_id -> transcripts list
        self.MIN_TRANSCRIPTS = 10  # Index when there are at least 10 new transcripts
    
    def add_transcript(self, session_device_id: int, transcript):
        """Add a new transcript and index if threshold reached"""
        
        if session_device_id not in self.pending_transcripts:
            self.pending_transcripts[session_device_id] = []
        
        self.pending_transcripts[session_device_id].append(transcript)
        
        # Check if should index
        if len(self.pending_transcripts[session_device_id]) >= self.MIN_TRANSCRIPTS:
            self.index_pending(session_device_id)
    
    def index_pending(self, session_device_id: int):
        """Index pending transcripts for a session"""
        
        if session_device_id not in self.pending_transcripts:
            return
        
        transcripts = self.pending_transcripts[session_device_id]
        
        if not transcripts:
            return
        
        try:
            # Index the new chunks
            chunks_created = self.rag.index_session_chunks(session_device_id, transcripts)
            logger.info(f"Auto-indexed {chunks_created} chunks for session_device {session_device_id}")
            
            # Clear pending
            self.pending_transcripts[session_device_id] = []
            
        except Exception as e:
            logger.error(f"Auto-indexing failed for session_device {session_device_id}: {e}")
    
    def force_index_all_pending(self):
        """Force index all pending transcripts regardless of threshold"""
        
        for session_device_id in list(self.pending_transcripts.keys()):
            if self.pending_transcripts[session_device_id]:
                self.index_pending(session_device_id)


# Lazy singleton pattern - avoids creating RAGService at import time
_auto_indexer_instance = None

def get_auto_indexer():
    """Lazy singleton - only creates RAGAutoIndexer when first needed"""
    global _auto_indexer_instance
    if _auto_indexer_instance is None:
        _auto_indexer_instance = RAGAutoIndexer()
    return _auto_indexer_instance