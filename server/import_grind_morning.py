#!/usr/bin/env python3
"""
Import GRIND Morning session from markdown file.
"""

import os
import sys
import re
from datetime import datetime

# Add server directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

import config
config.initialize()

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


def parse_timestamp(ts_str):
    """Convert timestamp string like '0:08:11' or '1:02:52' to seconds."""
    parts = ts_str.split(':')
    if len(parts) == 3:
        hours, mins, secs = int(parts[0]), int(parts[1]), int(parts[2])
        return hours * 3600 + mins * 60 + secs
    elif len(parts) == 2:
        mins, secs = int(parts[0]), int(parts[1])
        return mins * 60 + secs
    return 0


def parse_markdown_file(filepath):
    """Parse the markdown file and extract transcripts by device."""
    with open(filepath, 'r') as f:
        content = f.read()

    devices = {}
    current_device = None

    lines = content.split('\n')
    for line in lines:
        # Check for device header
        if line.startswith('## '):
            current_device = line[3:].strip()
            devices[current_device] = []
            continue

        # Skip table headers
        if '| Device Name |' in line or '|---|' in line:
            continue

        # Parse transcript rows
        if line.startswith('|') and current_device:
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 5:
                device_name = parts[1]
                timestamp = parts[2]
                speaker_tag = parts[3]
                transcript_text = parts[4]

                if timestamp and speaker_tag and transcript_text:
                    devices[current_device].append({
                        'device_name': device_name,
                        'timestamp': timestamp,
                        'speaker_tag': speaker_tag,
                        'transcript': transcript_text
                    })

    return devices


def run_import():
    """Run the import process."""
    print("=" * 60)
    print("GRIND Morning Session Import")
    print("=" * 60)

    # Speaker name mappings
    speaker_mappings = {
        'Dev10': {'Speaker A': 'Jeremiah', 'Speaker B': 'Khalil'},
        'Dev30': {'Speaker A': 'Andre', 'Speaker B': 'Marcelo'},
        'dev41': {'Speaker A': 'Brian', 'Speaker B': 'Terrence'},
    }

    with app.app_context():
        import database
        from tables.session import Session
        from tables.session_device import SessionDevice
        from tables.speaker import Speaker
        from tables.transcript import Transcript

        # Parse the markdown file
        filepath = '/home/ubuntu/chemistry-dashboard/GRINDMorning.md'
        print(f"\nParsing {filepath}...")
        devices_data = parse_markdown_file(filepath)

        for device, transcripts in devices_data.items():
            print(f"  {device}: {len(transcripts)} transcripts")

        # Create session
        print("\nCreating session 'GRIND Morning'...")
        session = Session(owner_id=1, name='GRIND Morning')
        db.session.add(session)
        db.session.flush()
        session_id = session.id
        print(f"  Created session ID: {session_id}")

        # Create session_devices and import transcripts
        for device_key, device_transcripts in devices_data.items():
            print(f"\nProcessing device: {device_key}")

            # Normalize device key for lookup
            lookup_key = device_key
            if lookup_key not in speaker_mappings:
                # Try case variations
                for k in speaker_mappings.keys():
                    if k.lower() == device_key.lower():
                        lookup_key = k
                        break

            # Create session_device
            session_device = SessionDevice(
                session_id=session_id,
                device_id=None,
                name=device_key
            )
            db.session.add(session_device)
            db.session.flush()
            sd_id = session_device.id
            print(f"  Created session_device ID: {sd_id}")

            # Get speaker mapping for this device
            speaker_map = speaker_mappings.get(lookup_key, {})

            # Create speakers
            speaker_ids = {}
            speakers_created = set()
            for transcript in device_transcripts:
                tag = transcript['speaker_tag']
                if tag not in speakers_created:
                    speaker_name = speaker_map.get(tag, tag)
                    speaker = Speaker(
                        session_device_id=sd_id,
                        alias=speaker_name
                    )
                    db.session.add(speaker)
                    db.session.flush()
                    speaker_ids[tag] = speaker.id
                    speakers_created.add(tag)
                    print(f"    Created speaker: {speaker_name} (ID: {speaker.id})")

            # Insert transcripts
            transcript_count = 0
            for t in device_transcripts:
                start_time = parse_timestamp(t['timestamp'])
                text = t['transcript']
                tag = t['speaker_tag']
                speaker_id = speaker_ids.get(tag)
                speaker_name = speaker_map.get(tag, tag)

                # Transcript constructor: session_device_id, start_time, length, transcript,
                # question, direction, emotional_tone, analytic_thinking, clout, authenticity,
                # certainty, topic_id, speaker_tag, speaker_id
                transcript_obj = Transcript(
                    sd_id,           # session_device_id
                    start_time,      # start_time
                    10,              # length (default)
                    text,            # transcript
                    False,           # question
                    0,               # direction
                    0,               # emotional_tone
                    0,               # analytic_thinking
                    0,               # clout
                    0,               # authenticity
                    0,               # certainty
                    None,            # topic_id
                    speaker_name,    # speaker_tag
                    speaker_id       # speaker_id
                )
                db.session.add(transcript_obj)
                transcript_count += 1

            print(f"    Inserted {transcript_count} transcripts")

        # Commit all changes
        db.session.commit()
        print("\n" + "=" * 60)
        print("Import complete!")
        print(f"Session ID: {session_id}")
        print("=" * 60)

        return session_id


if __name__ == '__main__':
    run_import()
