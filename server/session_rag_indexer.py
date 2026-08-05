# server/session_rag_indexer.py
"""
Batch indexing utility for session-level RAG.

This script indexes all existing sessions with concept maps and/or 7C analysis
into the session_summaries ChromaDB collection for session-level semantic search.

Usage:
    python session_rag_indexer.py                    # Index all sessions
    python session_rag_indexer.py --dry-run          # Preview without indexing
    python session_rag_indexer.py --session-id 448   # Index specific session
    python session_rag_indexer.py --force            # Re-index all (including existing)
"""

import argparse
import logging
import sys
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_flask_context():
    """Setup Flask application context for database access."""
    from app import app, db
    return app.app_context()


def get_sessions_to_index(session_device_id=None, force=False):
    """
    Get list of session_device_ids that should be indexed.

    Args:
        session_device_id: Specific session to index (optional)
        force: If True, return all sessions; if False, skip already indexed

    Returns:
        List of (session_device_id, has_concept_map, has_7c) tuples
    """
    from tables.concept_session import ConceptSession
    from tables.seven_cs_analysis import SevenCsAnalysis
    from tables.session_device import SessionDevice
    from rag_service import RAGService

    rag = RAGService()
    sessions_to_index = []

    # If specific session requested
    if session_device_id:
        concept_session = ConceptSession.query.filter_by(
            session_device_id=session_device_id
        ).first()
        seven_cs = SevenCsAnalysis.query.filter_by(
            session_device_id=session_device_id,
            analysis_status='completed'
        ).first()

        has_concept_map = concept_session is not None and concept_session.generation_status == 'completed'
        has_7c = seven_cs is not None

        if has_concept_map or has_7c:
            sessions_to_index.append((session_device_id, has_concept_map, has_7c))
        else:
            logger.warning(f"Session {session_device_id} has no concept map or 7C analysis")

        return sessions_to_index

    # Get all session devices with either concept maps or 7C analysis
    all_session_devices = SessionDevice.query.all()

    # Check which already exist in the index (unless force)
    existing_ids = set()
    if not force:
        try:
            existing = rag.session_collection.get(limit=10000)
            for doc_id in existing['ids']:
                if doc_id.startswith('session_'):
                    sd_id = int(doc_id.replace('session_', ''))
                    existing_ids.add(sd_id)
            logger.info(f"Found {len(existing_ids)} sessions already indexed")
        except Exception as e:
            logger.warning(f"Could not check existing index: {e}")

    for sd in all_session_devices:
        # Skip if already indexed (unless force)
        if sd.id in existing_ids and not force:
            continue

        # Check for concept map
        concept_session = ConceptSession.query.filter_by(
            session_device_id=sd.id
        ).first()
        has_concept_map = (concept_session is not None and
                         concept_session.generation_status == 'completed' and
                         concept_session.nodes and len(concept_session.nodes) > 0)

        # Check for 7C analysis
        seven_cs = SevenCsAnalysis.query.filter_by(
            session_device_id=sd.id,
            analysis_status='completed'
        ).first()
        has_7c = seven_cs is not None

        # Only include if has some data to index
        if has_concept_map or has_7c:
            sessions_to_index.append((sd.id, has_concept_map, has_7c))

    return sessions_to_index


def index_sessions(sessions_to_index, dry_run=False):
    """
    Index the given sessions into ChromaDB using the 5-collection architecture.

    Indexes 3 separate embeddings per session:
    - transcript: Full session transcript
    - concepts: Concept map structure
    - seven_c: 7C collaborative quality analysis

    Args:
        sessions_to_index: List of (session_device_id, has_concept_map, has_7c) tuples
        dry_run: If True, just log what would be done

    Returns:
        Dict with success/failure counts
    """
    from session_serializer import SessionSerializer
    from rag_service import RAGService

    serializer = SessionSerializer()
    rag = RAGService()

    results = {
        'total': len(sessions_to_index),
        'successful': 0,
        'failed': 0,
        'skipped': 0,
        'details': []
    }

    for i, (sd_id, has_cm, has_7c) in enumerate(sessions_to_index, 1):
        logger.info(f"[{i}/{len(sessions_to_index)}] Processing session_device {sd_id} "
                   f"(concept_map: {has_cm}, 7C: {has_7c})")

        if dry_run:
            results['details'].append({
                'session_device_id': sd_id,
                'status': 'would_index',
                'has_concept_map': has_cm,
                'has_7c': has_7c
            })
            results['successful'] += 1
            continue

        try:
            # Serialize to 3 separate documents
            docs = serializer.serialize_all(sd_id)

            if not docs:
                logger.warning(f"  Could not serialize session {sd_id}")
                results['skipped'] += 1
                results['details'].append({
                    'session_device_id': sd_id,
                    'status': 'skipped',
                    'reason': 'No data to serialize'
                })
                continue

            metadata = docs['metadata']
            indexed_collections = []

            # Index transcript (if available)
            if docs.get('transcript'):
                success = rag.index_session_transcript(sd_id, docs['transcript'], metadata)
                if success:
                    indexed_collections.append('transcript')

            # Index concepts (if available)
            if docs.get('concepts'):
                success = rag.index_session_concepts(sd_id, docs['concepts'], metadata)
                if success:
                    indexed_collections.append('concepts')

            # Index 7C analysis (if available)
            if docs.get('seven_c'):
                success = rag.index_session_7c(sd_id, docs['seven_c'], metadata)
                if success:
                    indexed_collections.append('seven_c')

            # Also index in legacy combined collection for backward compatibility
            legacy_serialized = serializer.serialize_for_embedding(sd_id)
            if legacy_serialized:
                rag.index_session(sd_id, legacy_serialized)
                indexed_collections.append('legacy')

            if indexed_collections:
                logger.info(f"  ✓ Indexed [{', '.join(indexed_collections)}]: "
                           f"nodes={metadata.get('node_count', 0)}, "
                           f"transcripts={metadata.get('transcript_count', 0)}, "
                           f"7C_comm={metadata.get('communication_score', 0)}")
                results['successful'] += 1
                results['details'].append({
                    'session_device_id': sd_id,
                    'status': 'indexed',
                    'collections': indexed_collections,
                    'metadata': {
                        'node_count': metadata.get('node_count', 0),
                        'transcript_count': metadata.get('transcript_count', 0),
                        'has_concept_map': metadata.get('has_concept_map', False),
                        'has_seven_cs': metadata.get('has_seven_cs', False)
                    }
                })
            else:
                logger.error(f"  ✗ Failed to index any collection for session {sd_id}")
                results['failed'] += 1
                results['details'].append({
                    'session_device_id': sd_id,
                    'status': 'failed',
                    'reason': 'No collections indexed'
                })

        except Exception as e:
            logger.error(f"  ✗ Error indexing session {sd_id}: {e}")
            results['failed'] += 1
            results['details'].append({
                'session_device_id': sd_id,
                'status': 'error',
                'reason': str(e)
            })

    return results


def print_summary(results, dry_run=False):
    """Print a summary of the indexing results."""
    print("\n" + "=" * 60)
    if dry_run:
        print("DRY RUN SUMMARY (no changes made)")
    else:
        print("INDEXING SUMMARY")
    print("=" * 60)
    print(f"Total sessions processed: {results['total']}")
    print(f"Successfully indexed:     {results['successful']}")
    print(f"Failed:                   {results['failed']}")
    print(f"Skipped:                  {results['skipped']}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description='Batch index sessions for session-level RAG search'
    )
    parser.add_argument(
        '--session-id',
        type=int,
        help='Index specific session_device_id only'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview what would be indexed without making changes'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Re-index all sessions, including already indexed ones'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("Starting session RAG indexer...")
    logger.info(f"Options: dry_run={args.dry_run}, force={args.force}")

    # Setup Flask context
    with setup_flask_context():
        # Get sessions to index
        logger.info("Finding sessions to index...")
        sessions_to_index = get_sessions_to_index(
            session_device_id=args.session_id,
            force=args.force
        )

        if not sessions_to_index:
            logger.info("No sessions found to index")
            return 0

        logger.info(f"Found {len(sessions_to_index)} sessions to index")

        # Preview
        for sd_id, has_cm, has_7c in sessions_to_index[:10]:
            logger.info(f"  - Session {sd_id}: concept_map={has_cm}, 7C={has_7c}")
        if len(sessions_to_index) > 10:
            logger.info(f"  ... and {len(sessions_to_index) - 10} more")

        # Index
        results = index_sessions(sessions_to_index, dry_run=args.dry_run)

        # Print summary
        print_summary(results, dry_run=args.dry_run)

        return 0 if results['failed'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
