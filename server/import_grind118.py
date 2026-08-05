#!/usr/bin/env python3
"""
Import GRIND 11/8 Afternoon session from GRIND118Afternoon.md
Session: GRIND Youth STEM Programs
Date: Nov 8, 2025
Devices: Dev1, Dev2, Dev3 -> Split into parts of ≤150 transcripts each
Speakers: 76->Whitney, 77->Carmen, 78->Tessa
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

# Speaker mappings - unique names not in database
SPEAKER_MAP = {
    'Speaker 76': 'Whitney',
    'Speaker 77': 'Carmen',
    'Speaker 78': 'Tessa',
}

# Device name prefix
DEVICE_PREFIX = 'Table301'  # Will become Table301-Part1, Table301-Part2, etc.

# Maximum transcripts per device
MAX_TRANSCRIPTS_PER_DEVICE = 150


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


def repair_transcript(text):
    """
    Lightly repair transcripts for readability while preserving meaning.
    - Fix obvious transcription errors
    - Clean up spacing
    """
    # Remove extra spaces
    text = re.sub(r'\s+', ' ', text).strip()

    # Fix common transcription patterns
    text = re.sub(r'\bUm,?\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\bUh,?\s*', '', text, flags=re.IGNORECASE)

    # Capitalize after periods
    def capitalize_after_period(match):
        return match.group(0).upper()
    text = re.sub(r'(?<=\. )[a-z]', capitalize_after_period, text)

    # Ensure first letter is capitalized
    if text:
        text = text[0].upper() + text[1:]

    return text


def parse_markdown(filepath):
    """Parse the markdown file into device -> transcripts structure."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    devices = {}
    current_device = None

    # Pattern for transcript lines: - **timestamp** | **Speaker XX** | text
    transcript_pattern = re.compile(
        r'^- \*\*(\d+:\d+:\d+)\*\* \| \*\*(Speaker \d+)\*\* \| (.+)$',
        re.MULTILINE
    )

    lines = content.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Device header
        if line.startswith('## Dev'):
            current_device = line[3:].strip()  # "Dev1", "Dev2", "Dev3"
            devices[current_device] = []
            i += 1
            continue

        # Check for transcript line
        if line.startswith('- **') and current_device:
            # Match the pattern
            match = transcript_pattern.match(line)
            if match:
                timestamp = match.group(1)
                speaker_tag = match.group(2)
                transcript = match.group(3)

                # Check if transcript continues on next lines (indented continuation)
                i += 1
                while i < len(lines):
                    next_line = lines[i]
                    # Continuation lines start with spaces (indentation)
                    if next_line.startswith('  ') and not next_line.strip().startswith('- **'):
                        transcript += ' ' + next_line.strip()
                        i += 1
                    else:
                        break

                # Repair the transcript slightly
                transcript = repair_transcript(transcript)

                devices[current_device].append({
                    'timestamp': timestamp,
                    'speaker_tag': speaker_tag,
                    'transcript': transcript
                })
                continue

        i += 1

    return devices


def split_device_transcripts(transcripts, max_per_part=MAX_TRANSCRIPTS_PER_DEVICE):
    """
    Split transcripts into parts of max_per_part each.
    Returns list of transcript lists.
    """
    parts = []
    for i in range(0, len(transcripts), max_per_part):
        parts.append(transcripts[i:i + max_per_part])
    return parts


def run_import():
    """Run the import process."""
    print("=" * 60)
    print("GRIND Youth STEM Programs Import")
    print("Date: Nov 8, 2025")
    print("=" * 60)

    filepath = '/home/ubuntu/chemistry-dashboard/GRIND118Afternoon.md'
    print(f"\nParsing {filepath}...")

    devices = parse_markdown(filepath)

    # Show parsed counts
    total_transcripts = 0
    for device, transcripts in devices.items():
        print(f"  {device}: {len(transcripts)} transcripts")
        total_transcripts += len(transcripts)
    print(f"  Total: {total_transcripts} transcripts")

    # Calculate splits
    print("\nPlanned splits (max 150 per device):")
    split_plan = {}
    part_num = 1
    for device in sorted(devices.keys()):
        transcripts = devices[device]
        parts = split_device_transcripts(transcripts)
        split_plan[device] = []
        for part in parts:
            device_name = f"Table30{device[-1]}-Part{len(split_plan[device]) + 1}"
            split_plan[device].append({
                'name': device_name,
                'transcripts': part
            })
            print(f"    {device_name}: {len(part)} transcripts")
        part_num += len(parts)

    with app.app_context():
        import database
        from tables.session import Session
        from tables.session_device import SessionDevice
        from tables.speaker import Speaker
        from tables.transcript import Transcript

        # Create session - Nov 8, 2025
        print("\nCreating session 'GRIND Youth STEM Programs'...")
        session = Session(owner_id=1, name='GRIND Youth STEM Programs')
        db.session.add(session)
        db.session.flush()
        session_id = session.id

        # Set proper dates - afternoon session ~2 hours
        session.creation_date = datetime(2025, 11, 8, 13, 0, 0)  # 1:00 PM
        session.end_date = datetime(2025, 11, 8, 15, 30, 0)  # 3:30 PM
        db.session.flush()

        print(f"  Created session ID: {session_id}")

        session_device_ids = []

        # Process each device part
        for device in sorted(split_plan.keys()):
            parts = split_plan[device]

            for part_info in parts:
                device_name = part_info['name']
                part_transcripts = part_info['transcripts']

                if not part_transcripts:
                    continue

                print(f"\nProcessing device: {device_name}")

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

                # Create speakers for this device
                speaker_ids = {}
                unique_tags = set(t['speaker_tag'] for t in part_transcripts)
                for tag in unique_tags:
                    speaker_name = SPEAKER_MAP.get(tag, tag)
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
                for t in part_transcripts:
                    start_time = parse_timestamp(t['timestamp'])
                    text = t['transcript']
                    tag = t['speaker_tag']
                    speaker_id = speaker_ids.get(tag)
                    speaker_name = SPEAKER_MAP.get(tag, tag)

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
        print(f"Session: GRIND Youth STEM Programs")
        print(f"Date: Nov 8, 2025 (1:00 PM - 3:30 PM)")
        print(f"Session Device IDs: {session_device_ids}")
        print("=" * 60)

        return session_id, session_device_ids


if __name__ == '__main__':
    run_import()
