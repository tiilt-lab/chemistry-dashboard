#!/usr/bin/env python3
"""
Compute LIWC psycholinguistic metrics for transcripts that have zeros.
"""

import os
import sys

# Set working directory to server folder
SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SERVER_DIR)

# Add server path first for config
sys.path.insert(0, SERVER_DIR)

from dotenv import load_dotenv
load_dotenv()

import config
config.initialize()

# Now add audio_processing path for LIWC
sys.path.insert(0, os.path.join(SERVER_DIR, '..', 'audio_processing'))

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

DATABASE_USER = config.config['server']['database_user']
DATABASE_URL = f'mysql+mysqlconnector://{DATABASE_USER}:{DATABASE_USER}@localhost/discussion_capture'

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy()
db.init_app(app)

# Patch sys.modules for table imports
import types
fake_app_module = types.ModuleType('app')
fake_app_module.db = db
fake_app_module.app = app
sys.modules['app'] = fake_app_module

# Import LIWC detector
from features_detector.respeaker_hi_liwc import populate_dictionary_index_hi, populate_dictionary_index_liwc, process_text


def detect_features(transcript, hgi_dictionary, hgi_emots, liwc_dictionary, liwc_emots):
    """Compute LIWC features for a transcript."""
    hgi_count, hgi_emot_dict = process_text(transcript, hgi_dictionary, hgi_emots)
    liwc_count, liwc_emot_dict = process_text(transcript, liwc_dictionary, liwc_emots)

    emotion_val = 0.0
    analytic_val = 0.0
    clout_val = 0.0
    certainty_val = 0.0
    authenticity_val = 0.0

    if liwc_count > 0:
        emotion_val = 100.0 * max([hgi_emot_dict.get('Positiv', 0)]) / float(liwc_count)
        analytic_val = 100.0 * max([
            hgi_emot_dict.get('Causal', 0),
            liwc_emot_dict.get('CogMech', 0),
            liwc_emot_dict.get('Insight', 0)
        ]) / float(liwc_count)
        clout_val = 100.0 * max([
            liwc_emot_dict.get('Conj', 0),
            liwc_emot_dict.get('Assent', 0)
        ]) / float(liwc_count)
        certainty_val = 100.0 * max([
            hgi_emot_dict.get('SureLw', 0),
            liwc_emot_dict.get('Certain', 0)
        ]) / float(liwc_count)
        authenticity_val = 100.0 * liwc_emot_dict.get('I', 0) / float(liwc_count)

    return {
        'emotional_tone_value': emotion_val,
        'analytic_thinking_value': analytic_val,
        'clout_value': clout_val,
        'certainty_value': certainty_val,
        'authenticity_value': authenticity_val
    }


def run_computation(session_device_ids=None):
    """Compute LIWC metrics for transcripts."""
    print("=" * 60)
    print("LIWC METRICS COMPUTATION")
    print("=" * 60)

    # Load dictionaries
    print("\nLoading LIWC dictionaries...")
    hgi_emots_full, hgi_dictionary = populate_dictionary_index_hi()
    hgi_emots = ['Positiv', 'Know', 'Causal', 'SureLw']
    liwc_emots_full, liwc_dictionary = populate_dictionary_index_liwc()
    liwc_emots = ['CogMech', 'Assent', 'Conj', 'Insight', 'Certain', 'I']
    print("  Dictionaries loaded.")

    with app.app_context():
        import database
        from tables.transcript import Transcript
        from tables.session_device import SessionDevice

        # Build query
        query = Transcript.query
        if session_device_ids:
            query = query.filter(Transcript.session_device_id.in_(session_device_ids))

        # Find transcripts with zero metrics
        transcripts = query.filter(
            Transcript.emotional_tone_value == 0,
            Transcript.analytic_thinking_value == 0,
            Transcript.clout_value == 0,
            Transcript.certainty_value == 0,
            Transcript.authenticity_value == 0
        ).all()

        print(f"\nFound {len(transcripts)} transcripts with zero metrics")

        if not transcripts:
            print("No transcripts to process.")
            return

        # Process each transcript
        updated = 0
        for i, t in enumerate(transcripts):
            if not t.transcript or len(t.transcript.strip()) < 5:
                continue

            features = detect_features(
                t.transcript,
                hgi_dictionary, hgi_emots,
                liwc_dictionary, liwc_emots
            )

            # Update transcript
            t.emotional_tone_value = features['emotional_tone_value']
            t.analytic_thinking_value = features['analytic_thinking_value']
            t.clout_value = features['clout_value']
            t.certainty_value = features['certainty_value']
            t.authenticity_value = features['authenticity_value']
            updated += 1

            if (i + 1) % 20 == 0:
                print(f"  Processed {i + 1}/{len(transcripts)} transcripts...")

        # Commit changes
        db.session.commit()

        print(f"\n  Updated {updated} transcripts")
        print("\n" + "=" * 60)
        print("COMPUTATION COMPLETE")
        print("=" * 60)


if __name__ == '__main__':
    # Compute for GRIND Innovation Roundtable session devices
    run_computation(session_device_ids=[52, 53, 54])
