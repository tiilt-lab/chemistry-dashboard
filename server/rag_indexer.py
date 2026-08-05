import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import database 
from rag_service import RAGService
import logging
from typing import List, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGIndexer:
    def __init__(self):
        """Initialize indexer with database and RAG service"""
        self.rag = RAGService()
    
    def get_all_session_devices(self) -> List[Dict]:
        """Get all session_device records"""
        session_devices = database.get_session_devices()
        
        result = []
        for sd in session_devices:
            result.append({
                'id': sd.id,
                'session_id': sd.session_id,
                'device_id': sd.device_id,
                'name': sd.name,
                'session': sd.session  # This has the session object
            })
        
        return result
    
    def get_transcripts_with_metrics(self, session_device_id: int):
        """
        Get all transcripts for a session_device with speaker metrics
        """
        # Use the existing get_transcripts function
        transcripts = database.get_transcripts(session_device_id=session_device_id)
        
        # The transcripts already have the metrics we need
        return transcripts
    
    def index_all_sessions(self):
        """Index all sessions in the database"""
        logger.info("Starting RAG indexing for all sessions...")
        
        # Get all sessions first
        sessions = database.get_sessions()
        logger.info(f"Found {len(sessions)} sessions")
        
        total_chunks = 0
        successful_sessions = 0
        failed_sessions = []
        
        for session in sessions:
            # Get session_devices for this session
            session_devices = database.get_session_devices(session_id=session.id)
            
            for sd in session_devices:
                sd_id = sd.id
                sd_name = sd.name or f"Device {sd_id}"
                session_name = session.name or f"Session {session.id}"
                
                logger.info(f"Processing {session_name} - {sd_name} (ID: {sd_id})...")
                
                try:
                    # Get transcripts with metrics
                    transcripts = database.get_transcripts(session_device_id=sd_id)
                    
                    if not transcripts:
                        logger.warning(f"No transcripts found for session_device {sd_id}")
                        continue
                    
                    logger.info(f"Found {len(transcripts)} transcripts for session_device {sd_id}")
                    
                    # Index the chunks
                    chunks_indexed = self.rag.index_session_chunks(sd_id, transcripts)
                    
                    if chunks_indexed > 0:
                        total_chunks += chunks_indexed
                        successful_sessions += 1
                        logger.info(f"Successfully indexed {chunks_indexed} chunks for {sd_name}")
                    else:
                        logger.warning(f"No chunks indexed for {sd_name}")
                        
                except Exception as e:
                    logger.error(f"Failed to index session_device {sd_id}: {e}")
                    failed_sessions.append(sd_id)
        
        # Final summary
        logger.info("=" * 50)
        logger.info(f"Indexing complete!")
        logger.info(f"Total chunks indexed: {total_chunks}")
        logger.info(f"Successful sessions: {successful_sessions}")
        logger.info(f"Failed sessions: {len(failed_sessions)}")
        if failed_sessions:
            logger.info(f"Failed session_device IDs: {failed_sessions}")
        
        # Get collection stats
        stats = self.rag.get_collection_stats()
        logger.info(f"Collection stats: {stats}")
        
        return {
            "total_chunks": total_chunks,
            "successful_sessions": successful_sessions,
            "failed_sessions": failed_sessions,
            "collection_stats": stats
        }
    
    def clear_all_indexes(self):
        """Clear all indexed data (use with caution!)"""
        confirmation = input("Are you sure you want to clear all indexed data? Type 'yes' to confirm: ")
        if confirmation.lower() == 'yes':
            # Delete and recreate the collection
            self.rag.client.delete_collection("discussion_chunks")
            logger.info("All indexes cleared")
            # Reinitialize the RAG service to recreate collection
            self.rag = RAGService()
            return True
        else:
            logger.info("Clear operation cancelled")
            return False
    
    def reindex_session(self, session_device_id: int):
        """Reindex a specific session_device"""
        logger.info(f"Reindexing session_device {session_device_id}...")
        
        # First remove existing chunks for this session
        try:
            # Get existing chunks for this session
            existing = self.rag.collection.get(
                where={"session_device_id": session_device_id}
            )
            
            if existing['ids']:
                # Delete them
                self.rag.collection.delete(ids=existing['ids'])
                logger.info(f"Removed {len(existing['ids'])} existing chunks")
        except Exception as e:
            logger.warning(f"Error removing existing chunks: {e}")
        
        # Now reindex
        transcripts = database.get_transcripts(session_device_id=session_device_id)
        
        if not transcripts:
            logger.warning(f"No transcripts found for session_device {session_device_id}")
            return 0
        
        chunks_indexed = self.rag.index_session_chunks(session_device_id, transcripts)
        logger.info(f"Reindexed {chunks_indexed} chunks for session_device {session_device_id}")
        
        return chunks_indexed


if __name__ == "__main__":
    """Run the indexer when called directly"""
    import argparse
    
    parser = argparse.ArgumentParser(description='RAG Indexer for discussion transcripts')
    parser.add_argument('--index-all', action='store_true', help='Index all sessions')
    parser.add_argument('--clear', action='store_true', help='Clear all indexes')
    parser.add_argument('--reindex', type=int, help='Reindex specific session_device_id')
    parser.add_argument('--stats', action='store_true', help='Show collection statistics')
    
    args = parser.parse_args()
    
    indexer = RAGIndexer()
    
    if args.clear:
        indexer.clear_all_indexes()
    elif args.index_all:
        indexer.index_all_sessions()
    elif args.reindex:
        indexer.reindex_session(args.reindex)
    elif args.stats:
        stats = indexer.rag.get_collection_stats()
        print(f"Collection statistics: {stats}")
    else:
        print("No action specified. Use --help for options")