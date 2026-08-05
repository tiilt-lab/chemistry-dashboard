#!/usr/bin/env python3
"""
Re-index speakers for demo sessions with correct embedding dimensions.
"""

import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

import config
config.initialize()
DATABASE_USER = config.config['server']['database_user']
DATABASE_URL = f'mysql+mysqlconnector://{DATABASE_USER}:{DATABASE_USER}@localhost/discussion_capture'

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy()
db.init_app(app)

import types
fake_app_module = types.ModuleType('app')
fake_app_module.db = db
fake_app_module.app = app
sys.modules['app'] = fake_app_module


def run_reindex():
    """Re-index speakers for demo sessions."""

    DEMO_SESSIONS = [18, 19, 20, 21, 22, 23, 24, 25]

    logger.info("=" * 60)
    logger.info("SPEAKER RE-INDEXING FOR DEMO SESSIONS")
    logger.info("=" * 60)

    with app.app_context():
        import database
        from rag_service import RAGService
        from speaker_rag_indexer import SpeakerRAGIndexer

        rag = RAGService()
        indexer = SpeakerRAGIndexer()

        logger.info(f"Current speaker collection: {rag.speaker_collection.count()} documents")

        # Index speakers for demo sessions
        total_speakers = 0
        for sd_id in DEMO_SESSIONS:
            logger.info(f"Processing speakers for session {sd_id}...")
            try:
                # Get speakers for this session
                transcripts = database.get_transcripts(session_device_id=sd_id)
                if not transcripts:
                    continue

                speaker_ids = set()
                for t in transcripts:
                    if hasattr(t, 'speaker_id') and t.speaker_id:
                        speaker_ids.add(t.speaker_id)

                for speaker_id in speaker_ids:
                    try:
                        success = indexer.index_speaker(speaker_id)
                        if success:
                            total_speakers += 1
                            logger.info(f"  Indexed speaker {speaker_id}")
                    except Exception as e:
                        logger.warning(f"  Error indexing speaker {speaker_id}: {e}")

            except Exception as e:
                logger.error(f"  Error processing session {sd_id}: {e}")

        logger.info("=" * 60)
        logger.info(f"COMPLETE: Indexed {total_speakers} speakers")
        logger.info(f"Final speaker collection: {rag.speaker_collection.count()} documents")
        logger.info("=" * 60)

        return 0


if __name__ == '__main__':
    sys.exit(run_reindex())
