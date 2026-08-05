#!/usr/bin/env python3
# server/migrate_session_embeddings.py
"""
Migration script for session-level RAG embeddings.

This is a one-time migration to create the session_summaries ChromaDB collection
and populate it with embeddings from all existing sessions that have concept maps
and/or 7C analysis.

Run this after deploying the hierarchical RAG feature to index historical data.

Usage:
    python migrate_session_embeddings.py

The script is idempotent - running it multiple times is safe as it will skip
already indexed sessions unless --force is specified.
"""

import logging
import sys
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f'migration_session_embeddings_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger(__name__)


def run_migration():
    """Run the session embeddings migration."""
    from app import app, db
    from session_rag_indexer import get_sessions_to_index, index_sessions, print_summary

    logger.info("=" * 60)
    logger.info("SESSION EMBEDDINGS MIGRATION")
    logger.info("=" * 60)
    logger.info(f"Started at: {datetime.now().isoformat()}")
    logger.info("")

    with app.app_context():
        # Step 1: Check ChromaDB collections (5-collection architecture)
        logger.info("Step 1: Checking ChromaDB collections (5-collection architecture)...")
        try:
            from rag_service import RAGService
            rag = RAGService()

            chunk_stats = rag.get_collection_stats()
            transcript_stats = rag.get_transcript_collection_stats()
            concept_stats = rag.get_concept_collection_stats()
            seven_c_stats = rag.get_7c_collection_stats()
            session_stats = rag.get_session_collection_stats()

            logger.info(f"  Chunks collection: {chunk_stats.get('total_chunks', 0)} documents")
            logger.info(f"  Transcripts collection: {transcript_stats.get('total_documents', 0)} documents")
            logger.info(f"  Concepts collection: {concept_stats.get('total_documents', 0)} documents")
            logger.info(f"  7C collection: {seven_c_stats.get('total_documents', 0)} documents")
            logger.info(f"  Sessions (legacy): {session_stats.get('total_sessions', 0)} documents")

        except Exception as e:
            logger.error(f"  Failed to initialize RAG service: {e}")
            return 1

        # Step 2: Find sessions to migrate
        logger.info("")
        logger.info("Step 2: Finding sessions to migrate...")

        try:
            sessions_to_index = get_sessions_to_index(force=False)
            logger.info(f"  Found {len(sessions_to_index)} sessions to index")

            # Summary of what we found
            with_cm = sum(1 for _, has_cm, _ in sessions_to_index if has_cm)
            with_7c = sum(1 for _, _, has_7c in sessions_to_index if has_7c)
            logger.info(f"    - With concept maps: {with_cm}")
            logger.info(f"    - With 7C analysis: {with_7c}")

        except Exception as e:
            logger.error(f"  Failed to find sessions: {e}")
            return 1

        if not sessions_to_index:
            logger.info("")
            logger.info("No sessions need migration - all up to date!")
            return 0

        # Step 3: Confirm and run migration
        logger.info("")
        logger.info("Step 3: Running migration...")
        logger.info(f"  Processing {len(sessions_to_index)} sessions...")

        try:
            results = index_sessions(sessions_to_index, dry_run=False)

        except Exception as e:
            logger.error(f"  Migration failed: {e}")
            return 1

        # Step 4: Print results
        logger.info("")
        logger.info("Step 4: Migration complete")
        print_summary(results)

        # Final stats (5-collection architecture)
        logger.info("")
        logger.info("Final collection stats (5-collection architecture):")
        transcript_stats = rag.get_transcript_collection_stats()
        concept_stats = rag.get_concept_collection_stats()
        seven_c_stats = rag.get_7c_collection_stats()
        session_stats = rag.get_session_collection_stats()
        logger.info(f"  Transcripts collection: {transcript_stats.get('total_documents', 0)} documents")
        logger.info(f"  Concepts collection: {concept_stats.get('total_documents', 0)} documents")
        logger.info(f"  7C collection: {seven_c_stats.get('total_documents', 0)} documents")
        logger.info(f"  Sessions (legacy): {session_stats.get('total_sessions', 0)} documents")

        # Step 5: Index speakers
        logger.info("")
        logger.info("Step 5: Indexing speakers...")
        try:
            from speaker_serializer import SpeakerSerializer, get_all_speaker_aliases

            serializer = SpeakerSerializer()
            aliases = get_all_speaker_aliases()
            logger.info(f"  Found {len(aliases)} unique speakers to index")

            speaker_indexed = 0
            speaker_failed = 0

            for alias in aliases:
                try:
                    serialized = serializer.serialize_speaker(alias)
                    if serialized:
                        success = rag.index_speaker(alias, serialized)
                        if success:
                            speaker_indexed += 1
                        else:
                            speaker_failed += 1
                except Exception as e:
                    logger.error(f"  Failed to index speaker {alias}: {e}")
                    speaker_failed += 1

            logger.info(f"  Indexed {speaker_indexed} speakers, {speaker_failed} failed")

            speaker_stats = rag.get_speaker_collection_stats()
            logger.info(f"  Speakers collection: {speaker_stats.get('count', 0)} documents")

        except Exception as e:
            logger.error(f"  Speaker indexing failed: {e}")

        logger.info("")
        logger.info(f"Completed at: {datetime.now().isoformat()}")

        return 0 if results['failed'] == 0 else 1


if __name__ == '__main__':
    sys.exit(run_migration())
