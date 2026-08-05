# server/speaker_rag_indexer.py
"""
Speaker RAG Indexer - Batch index all speakers for cross-session search.

This script indexes all unique speakers in the database into the ChromaDB
speaker_profiles collection for semantic search queries like:
- "How did Lex typically engage in discussions?"
- "Which speakers ask the most questions?"
- "Compare speaker engagement styles"

Usage:
    python speaker_rag_indexer.py [--verbose] [--speaker ALIAS]
"""

import sys
import os
import argparse
import logging

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def index_all_speakers(verbose: bool = False):
    """Index all speakers in the database."""
    from app import app
    from speaker_serializer import SpeakerSerializer, get_all_speaker_aliases
    from rag_service import RAGService

    with app.app_context():
        serializer = SpeakerSerializer()
        rag_service = RAGService()
        aliases = get_all_speaker_aliases()

        logger.info(f"Found {len(aliases)} unique speaker aliases to index")

        results = {
            "indexed": [],
            "failed": [],
            "skipped": []
        }

        for i, alias in enumerate(aliases, 1):
            try:
                logger.info(f"[{i}/{len(aliases)}] Indexing speaker: {alias}")

                serialized = serializer.serialize_speaker(alias)

                if serialized:
                    if verbose:
                        logger.info(f"  - Sessions: {serialized['metadata'].get('session_count', 0)}")
                        logger.info(f"  - Transcripts: {serialized['metadata'].get('transcript_count', 0)}")
                        logger.info(f"  - Concepts: {serialized['metadata'].get('concept_count', 0)}")

                    success = rag_service.index_speaker(alias, serialized)

                    if success:
                        results["indexed"].append(alias)
                        logger.info(f"  -> Indexed successfully")
                    else:
                        results["failed"].append(alias)
                        logger.warning(f"  -> Indexing failed")
                else:
                    results["skipped"].append(alias)
                    logger.warning(f"  -> Skipped (no data)")

            except Exception as e:
                logger.error(f"  -> Error indexing {alias}: {e}")
                results["failed"].append(alias)

        # Summary
        logger.info("\n" + "=" * 50)
        logger.info("INDEXING SUMMARY")
        logger.info("=" * 50)
        logger.info(f"Total speakers:   {len(aliases)}")
        logger.info(f"Indexed:          {len(results['indexed'])}")
        logger.info(f"Failed:           {len(results['failed'])}")
        logger.info(f"Skipped:          {len(results['skipped'])}")

        if results["indexed"]:
            logger.info(f"\nSuccessfully indexed: {', '.join(results['indexed'])}")
        if results["failed"]:
            logger.warning(f"\nFailed to index: {', '.join(results['failed'])}")
        if results["skipped"]:
            logger.info(f"\nSkipped (no data): {', '.join(results['skipped'])}")

        return results


def index_single_speaker(alias: str, verbose: bool = False):
    """Index a single speaker by alias."""
    from app import app
    from speaker_serializer import SpeakerSerializer
    from rag_service import RAGService

    with app.app_context():
        serializer = SpeakerSerializer()
        rag_service = RAGService()

        logger.info(f"Indexing speaker: {alias}")

        serialized = serializer.serialize_speaker(alias)

        if not serialized:
            logger.error(f"No data found for speaker: {alias}")
            return False

        if verbose:
            logger.info(f"  - Sessions: {serialized['metadata'].get('session_count', 0)}")
            logger.info(f"  - Transcripts: {serialized['metadata'].get('transcript_count', 0)}")
            logger.info(f"  - Concepts: {serialized['metadata'].get('concept_count', 0)}")
            logger.info(f"\nDocument preview:")
            logger.info(serialized['text'][:500] + "...")

        success = rag_service.index_speaker(alias, serialized)

        if success:
            logger.info(f"Successfully indexed speaker: {alias}")
        else:
            logger.error(f"Failed to index speaker: {alias}")

        return success


def show_speaker_stats():
    """Show current speaker collection stats."""
    from app import app
    from rag_service import RAGService

    with app.app_context():
        rag_service = RAGService()
        stats = rag_service.get_speaker_collection_stats()

        logger.info("\n" + "=" * 50)
        logger.info("SPEAKER COLLECTION STATS")
        logger.info("=" * 50)
        logger.info(f"Total indexed: {stats.get('count', 0)}")

        # List all speakers
        collection = rag_service.speaker_collection
        all_speakers = collection.get(include=['metadatas'])

        if all_speakers and all_speakers.get('ids'):
            logger.info("\nIndexed speakers:")
            for i, speaker_id in enumerate(all_speakers['ids']):
                metadata = all_speakers['metadatas'][i] if all_speakers.get('metadatas') else {}
                alias = metadata.get('speaker_alias', speaker_id)
                sessions = metadata.get('session_count', 0)
                logger.info(f"  - {alias} ({sessions} sessions)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Index speakers for RAG search")
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--speaker', '-s', type=str, help='Index a specific speaker by alias')
    parser.add_argument('--stats', action='store_true', help='Show collection stats only')

    args = parser.parse_args()

    if args.stats:
        show_speaker_stats()
    elif args.speaker:
        index_single_speaker(args.speaker, verbose=args.verbose)
    else:
        index_all_speakers(verbose=args.verbose)
