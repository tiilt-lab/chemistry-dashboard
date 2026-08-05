#!/usr/bin/env python3
"""
Re-index chunks for the demo sessions (18-25) with correct embedding dimensions.
"""

import os
import sys
import logging
import shutil

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
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

# Create a minimal Flask app
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy()
db.init_app(app)

# Patch sys.modules
import types
fake_app_module = types.ModuleType('app')
fake_app_module.db = db
fake_app_module.app = app
sys.modules['app'] = fake_app_module


def run_reindex():
    """Re-index chunks for demo sessions."""

    DEMO_SESSIONS = [18, 19, 20, 21, 22, 23, 24, 25]
    CHROMA_PATH = os.path.join(os.path.dirname(__file__), 'chroma_db')

    logger.info("=" * 60)
    logger.info("CHUNK RE-INDEXING FOR DEMO SESSIONS")
    logger.info("=" * 60)

    with app.app_context():
        import database
        from rag_service import RAGService

        # Get RAG service (this creates collections with correct embedding function)
        rag = RAGService()

        logger.info(f"Current chunk collection: {rag.collection.count()} documents")

        # Delete ALL existing chunks and recreate collection with correct embeddings
        logger.info("Clearing chunk collection...")
        try:
            # Get all chunk IDs and delete
            all_ids = rag.collection.get(limit=10000)['ids']
            if all_ids:
                rag.collection.delete(ids=all_ids)
                logger.info(f"Deleted {len(all_ids)} existing chunks")
        except Exception as e:
            logger.warning(f"Could not clear collection: {e}")

        logger.info(f"Chunk collection after clear: {rag.collection.count()} documents")

        # Re-index chunks for demo sessions
        total_chunks = 0
        for sd_id in DEMO_SESSIONS:
            transcripts = database.get_transcripts(session_device_id=sd_id)
            if not transcripts:
                logger.warning(f"No transcripts for session {sd_id}")
                continue

            logger.info(f"Indexing session {sd_id} ({len(transcripts)} transcripts)...")

            try:
                count = rag.index_session_chunks(sd_id, transcripts)
                total_chunks += count
                logger.info(f"  Indexed {count} chunks")
            except Exception as e:
                logger.error(f"  Error: {e}")

        logger.info("=" * 60)
        logger.info(f"COMPLETE: Indexed {total_chunks} chunks for {len(DEMO_SESSIONS)} sessions")
        logger.info(f"Final chunk collection: {rag.collection.count()} documents")
        logger.info("=" * 60)

        return 0


if __name__ == '__main__':
    sys.exit(run_reindex())
