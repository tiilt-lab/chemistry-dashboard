#!/usr/bin/env python3
"""
Import GRIND 11/7 Afternoon session from GRIND117Afternoon_all.md
Devices: 215, 218, 219 (the meaningful discussions)
"""

import os
import sys
import re
from datetime import datetime

SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SERVER_DIR)
sys.path.insert(0, SERVER_DIR)

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

import types
fake_app_module = types.ModuleType('app')
fake_app_module.db = db
fake_app_module.app = app
sys.modules['app'] = fake_app_module

# Only import these devices (meaningful discussions)
DEVICES_TO_IMPORT = ['Device 215', 'Device 218', 'Device 219']

# Speaker mappings - unique names not in database
SPEAKER_MAPS = {
    'Device 215': {'Speaker A': 'Preston', 'Speaker B': 'Silas'},
    'Device 218': {'Speaker A': 'Rashid', 'Speaker B': 'Malik'},
    'Device 219': {'Speaker A': 'Darius', 'Speaker B': 'Kenji'},
}

# Device name mappings
DEVICE_NAMES = {
    'Device 215': 'Table215',
    'Device 218': 'Table218',
    'Device 219': 'Table219',
}


def parse_timestamp(ts_str):
    """Convert timestamp like '0:26:12' or '1:36:24' to seconds."""
    parts = ts_str.strip().split(':')
    if len(parts) == 3:
        hours, mins, secs = int(parts[0]), int(parts[1]), int(parts[2])
        return hours * 3600 + mins * 60 + secs
    elif len(parts) == 2:
        mins, secs = int(parts[0]), int(parts[1])
        return mins * 60 + secs
    return 0


def parse_markdown(filepath):
    """Parse the markdown file into device -> transcripts structure."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    devices = {}
    current_device = None
    current_time = None
    current_speaker = None

    lines = content.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Device header
        if line.startswith('# Device '):
            current_device = line[2:].strip()
            if current_device in DEVICES_TO_IMPORT:
                devices[current_device] = []
            i += 1
            continue

        # Skip if not a device we want
        if current_device not in DEVICES_TO_IMPORT:
            i += 1
            continue

        # Time line
        if line.startswith('**Time:**'):
            current_time = line.replace('**Time:**', '').strip()
            i += 1
            continue

        # Speaker line
        if line.startswith('**Speaker:**'):
            current_speaker = line.replace('**Speaker:**', '').strip()
            i += 1
            # Next line(s) should be the transcript
            transcript_lines = []
            while i < len(lines):
                next_line = lines[i].strip()
                if next_line.startswith('**Time:**') or next_line.startswith('**Speaker:**') or next_line.startswith('# Device'):
                    break
                if next_line:
                    transcript_lines.append(next_line)
                i += 1

            if current_device and current_time and current_speaker and transcript_lines:
                devices[current_device].append({
                    'timestamp': current_time,
                    'speaker_tag': current_speaker,
                    'transcript': ' '.join(transcript_lines)
                })
            continue

        i += 1

    return devices


def run_import():
    """Run the import process."""
    print("=" * 60)
    print("GRIND Innovation Roundtable Import")
    print("Devices: 215, 218, 219")
    print("=" * 60)

    filepath = '/home/ubuntu/chemistry-dashboard/GRIND117Afternoon_all.md'
    print(f"\nParsing {filepath}...")

    devices = parse_markdown(filepath)

    total_transcripts = 0
    for device, transcripts in devices.items():
        print(f"  {device}: {len(transcripts)} transcripts")
        total_transcripts += len(transcripts)
    print(f"  Total: {total_transcripts} transcripts")

    with app.app_context():
        import database
        from tables.session import Session
        from tables.session_device import SessionDevice
        from tables.speaker import Speaker
        from tables.transcript import Transcript

        # Create session - Nov 7, 2025
        print("\nCreating session 'GRIND Innovation Roundtable'...")
        session = Session(owner_id=1, name='GRIND Innovation Roundtable')
        db.session.add(session)
        db.session.flush()
        session_id = session.id

        # Set proper dates - afternoon session ~2 hours
        session.creation_date = datetime(2025, 11, 7, 13, 0, 0)  # 1:00 PM
        session.end_date = datetime(2025, 11, 7, 15, 30, 0)  # 3:30 PM
        db.session.flush()

        print(f"  Created session ID: {session_id}")

        session_device_ids = []

        # Process each device
        for device_key in DEVICES_TO_IMPORT:
            if device_key not in devices:
                print(f"\nSkipping {device_key} - not found in file")
                continue

            device_transcripts = devices[device_key]
            if not device_transcripts:
                continue

            device_name = DEVICE_NAMES.get(device_key, device_key)
            speaker_map = SPEAKER_MAPS.get(device_key, {})

            print(f"\nProcessing device: {device_key} -> {device_name}")

            # Create session_device
            session_device = SessionDevice(
                session_id=session_id,
                device_id=None,
                name=device_name
            )
            session_device.connected = False
            session_device.removed = True
            db.session.add(session_device)
            db.session.flush()
            sd_id = session_device.id
            session_device_ids.append(sd_id)
            print(f"  Created session_device ID: {sd_id}")

            # Create speakers
            speaker_ids = {}
            unique_tags = set(t['speaker_tag'] for t in device_transcripts)
            for tag in unique_tags:
                speaker_name = speaker_map.get(tag, tag)
                speaker = Speaker(
                    session_device_id=sd_id,
                    alias=speaker_name
                )
                db.session.add(speaker)
                db.session.flush()
                speaker_ids[tag] = speaker.id
                print(f"    Created speaker: {speaker_name} (ID: {speaker.id})")

            # Insert transcripts
            transcript_count = 0
            for t in device_transcripts:
                start_time = parse_timestamp(t['timestamp'])
                text = t['transcript']
                tag = t['speaker_tag']
                speaker_id = speaker_ids.get(tag)
                speaker_name = speaker_map.get(tag, tag)

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

        db.session.commit()

        print("\n" + "=" * 60)
        print("Import complete!")
        print(f"Session ID: {session_id}")
        print(f"Session: GRIND Innovation Roundtable")
        print(f"Date: Nov 7, 2025 (1:00 PM - 3:30 PM)")
        print(f"Session Device IDs: {session_device_ids}")
        print("=" * 60)

        return session_id, session_device_ids


if __name__ == '__main__':
    run_import()
