#!/usr/bin/env python
"""
Re-index Sessions with Graph-Enhanced RAG

Migration script to re-index existing sessions with the new
hierarchical graph embeddings (semantic chunks, concept nodes, clusters).

Usage:
    # Index all sessions
    python reindex_sessions.py --all

    # Index specific session
    python reindex_sessions.py --session-device-id 123

    # Index sessions for a user
    python reindex_sessions.py --user-id 1

    # Dry run (show what would be indexed)
    python reindex_sessions.py --all --dry-run
"""

import sys
import os
import argparse
import logging
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_sessions_to_index(user_id: int = None, session_device_id: int = None) -> list:
    """Get list of session device IDs to index."""
    from tables.session_device import SessionDevice
    from tables.session import Session
    from tables.concept_session import ConceptSession

    query = SessionDevice.query

    if session_device_id:
        return [session_device_id]

    if user_id:
        query = query.join(Session).filter(Session.user_id == user_id)

    # Only index sessions with completed concept maps
    session_devices = query.all()
    ids_to_index = []

    for sd in session_devices:
        # Check if concept map exists
        concept_session = ConceptSession.query.filter_by(
            session_device_id=sd.id,
            generation_status='completed'
        ).first()

        if concept_session and concept_session.nodes:
            ids_to_index.append(sd.id)

    return ids_to_index


def main():
    parser = argparse.ArgumentParser(description='Re-index sessions with graph-enhanced RAG')
    parser.add_argument('--all', action='store_true', help='Index all sessions')
    parser.add_argument('--session-device-id', type=int, help='Index specific session device')
    parser.add_argument('--user-id', type=int, help='Index sessions for specific user')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be indexed')
    parser.add_argument('--skip-chunks', action='store_true', help='Skip semantic chunk indexing')
    parser.add_argument('--skip-nodes', action='store_true', help='Skip concept node indexing')
    parser.add_argument('--skip-clusters', action='store_true', help='Skip cluster indexing')

    args = parser.parse_args()

    if not any([args.all, args.session_device_id, args.user_id]):
        parser.print_help()
        sys.exit(1)

    # Initialize Flask app context
    from discussion_capture import app
    with app.app_context():
        # Get sessions to index
        if args.session_device_id:
            session_ids = [args.session_device_id]
        elif args.user_id:
            session_ids = get_sessions_to_index(user_id=args.user_id)
        else:
            session_ids = get_sessions_to_index()

        logger.info(f"Found {len(session_ids)} sessions to index")

        if args.dry_run:
            logger.info("DRY RUN - would index the following sessions:")
            for sid in session_ids:
                logger.info(f"  - session_device_id: {sid}")
            sys.exit(0)

        # Initialize indexer
        from graph_rag import GraphIndexer
        indexer = GraphIndexer()

        # Track results
        total_results = {
            "sessions": 0,
            "semantic_chunks": 0,
            "concept_nodes": 0,
            "concept_clusters": 0,
            "errors": []
        }

        # Index each session
        for i, session_id in enumerate(session_ids):
            logger.info(f"Indexing session {session_id} ({i+1}/{len(session_ids)})")

            try:
                results = indexer.index_session(
                    session_id,
                    index_chunks=not args.skip_chunks,
                    index_nodes=not args.skip_nodes,
                    index_clusters=not args.skip_clusters
                )

                total_results["sessions"] += 1
                total_results["semantic_chunks"] += results["semantic_chunks"]
                total_results["concept_nodes"] += results["concept_nodes"]
                total_results["concept_clusters"] += results["concept_clusters"]

                if results["errors"]:
                    total_results["errors"].extend([
                        f"Session {session_id}: {e}" for e in results["errors"]
                    ])

            except Exception as e:
                logger.error(f"Error indexing session {session_id}: {e}")
                total_results["errors"].append(f"Session {session_id}: {str(e)}")

        # Print summary
        logger.info("=" * 60)
        logger.info("INDEXING COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Sessions indexed: {total_results['sessions']}")
        logger.info(f"Semantic chunks: {total_results['semantic_chunks']}")
        logger.info(f"Concept nodes: {total_results['concept_nodes']}")
        logger.info(f"Concept clusters: {total_results['concept_clusters']}")

        if total_results["errors"]:
            logger.warning(f"Errors ({len(total_results['errors'])}):")
            for error in total_results["errors"]:
                logger.warning(f"  - {error}")

        # Print collection stats
        stats = indexer.get_collection_stats()
        logger.info("\nCollection totals:")
        logger.info(f"  - semantic_chunks: {stats['semantic_chunks']}")
        logger.info(f"  - concept_nodes: {stats['concept_nodes']}")
        logger.info(f"  - concept_clusters: {stats['concept_clusters']}")


if __name__ == '__main__':
    main()
