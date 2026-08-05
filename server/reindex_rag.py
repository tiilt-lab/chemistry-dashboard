#!/usr/bin/env python3
"""
Standalone RAG re-indexing script for 5-collection architecture.
"""

import os
import sys
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

# Get database URL from config
import config
config.initialize()
DATABASE_USER = config.config['server']['database_user']
DATABASE_URL = f'mysql+mysqlconnector://{DATABASE_USER}:{DATABASE_USER}@localhost/discussion_capture'

# Create a minimal Flask app for database access
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy()
db.init_app(app)

# Patch sys.modules so that "from app import db" uses our db
# This is needed because the table models import from app
import types
fake_app_module = types.ModuleType('app')
fake_app_module.db = db
fake_app_module.app = app
sys.modules['app'] = fake_app_module


def run_indexing():
    """Run the indexing process."""
    logger.info("=" * 60)
    logger.info("5-COLLECTION RAG RE-INDEXING")
    logger.info("=" * 60)
    logger.info(f"Started at: {datetime.now().isoformat()}")

    with app.app_context():
        # Import database module which imports all models
        import database

        # Get the models we need directly
        from tables.session_device import SessionDevice
        from tables.concept_session import ConceptSession
        from tables.seven_cs_analysis import SevenCsAnalysis

        # Now import services
        from rag_service import RAGService
        from session_serializer import SessionSerializer

        rag = RAGService()
        serializer = SessionSerializer()

        # Get initial stats
        logger.info("\nInitial collection stats:")
        stats = rag.get_all_collection_stats()
        for name, stat in stats.items():
            count = stat.get('total_documents', stat.get('total_chunks', stat.get('total_sessions', stat.get('total_speakers', 0))))
            logger.info(f"  {name}: {count} documents")

        # Get sessions to index - those with concept maps or 7C
        logger.info("\nFinding sessions to index...")
        sessions_to_index = []

        for sd in SessionDevice.query.all():
            concept_session = ConceptSession.query.filter_by(
                session_device_id=sd.id
            ).first()

            has_cm = (concept_session is not None and
                     concept_session.generation_status == 'completed' and
                     concept_session.nodes and len(concept_session.nodes) > 0)

            seven_cs = SevenCsAnalysis.query.filter_by(
                session_device_id=sd.id,
                analysis_status='completed'
            ).first()
            has_7c = seven_cs is not None

            if has_cm or has_7c:
                sessions_to_index.append((sd.id, has_cm, has_7c))

        logger.info(f"Found {len(sessions_to_index)} sessions to index")

        # Index each session
        results = {
            'total': len(sessions_to_index),
            'successful': 0,
            'failed': 0,
            'skipped': 0
        }

        for i, (sd_id, has_cm, has_7c) in enumerate(sessions_to_index, 1):
            logger.info(f"[{i}/{len(sessions_to_index)}] Processing session_device {sd_id} "
                       f"(concept_map: {has_cm}, 7C: {has_7c})")

            try:
                # Serialize to 3 separate documents
                docs = serializer.serialize_all(sd_id)

                if not docs:
                    logger.warning(f"  Could not serialize session {sd_id}")
                    results['skipped'] += 1
                    continue

                metadata = docs['metadata']
                indexed = []

                # Index each collection
                if docs.get('transcript'):
                    if rag.index_session_transcript(sd_id, docs['transcript'], metadata):
                        indexed.append('transcript')

                if docs.get('concepts'):
                    if rag.index_session_concepts(sd_id, docs['concepts'], metadata):
                        indexed.append('concepts')

                if docs.get('seven_c'):
                    if rag.index_session_7c(sd_id, docs['seven_c'], metadata):
                        indexed.append('7c')

                # Also index legacy combined
                legacy = serializer.serialize_for_embedding(sd_id)
                if legacy:
                    if rag.index_session(sd_id, legacy):
                        indexed.append('legacy')

                if indexed:
                    logger.info(f"  ✓ Indexed [{', '.join(indexed)}]")
                    results['successful'] += 1
                else:
                    logger.error(f"  ✗ No collections indexed")
                    results['failed'] += 1

            except Exception as e:
                logger.error(f"  ✗ Error: {e}")
                import traceback
                traceback.print_exc()
                results['failed'] += 1

        # Final stats
        logger.info("\n" + "=" * 60)
        logger.info("INDEXING SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total: {results['total']}")
        logger.info(f"Successful: {results['successful']}")
        logger.info(f"Failed: {results['failed']}")
        logger.info(f"Skipped: {results['skipped']}")

        logger.info("\nFinal collection stats:")
        stats = rag.get_all_collection_stats()
        for name, stat in stats.items():
            count = stat.get('total_documents', stat.get('total_chunks', stat.get('total_sessions', stat.get('total_speakers', 0))))
            logger.info(f"  {name}: {count} documents")

        logger.info(f"\nCompleted at: {datetime.now().isoformat()}")

        return 0 if results['failed'] == 0 else 1


if __name__ == '__main__':
    sys.exit(run_indexing())
