#!/usr/bin/env python3
"""
Import SRT file into the discussion_capture database.
Parses SRT, merges consecutive same-speaker segments, and inserts into DB.
"""

import re
import sys
import mysql.connector
from datetime import datetime

def parse_timestamp(ts):
    """Convert SRT timestamp to seconds."""
    # Format: HH:MM:SS,mmm
    match = re.match(r'(\d+):(\d+):(\d+),(\d+)', ts)
    if match:
        h, m, s, ms = map(int, match.groups())
        return h * 3600 + m * 60 + s + ms / 1000
    return 0

def parse_srt(file_path):
    """Parse SRT file into list of entries."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by double newlines (entry separators)
    blocks = re.split(r'\n\n+', content.strip())

    entries = []
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue

        # Line 1: index
        # Line 2: timestamps
        # Line 3+: text
        try:
            index = int(lines[0])
        except ValueError:
            continue

        # Parse timestamps
        ts_match = re.match(r'(\d+:\d+:\d+,\d+)\s*-->\s*(\d+:\d+:\d+,\d+)', lines[1])
        if not ts_match:
            continue

        start_ts = parse_timestamp(ts_match.group(1))
        end_ts = parse_timestamp(ts_match.group(2))

        # Get text (may be multiple lines)
        text = ' '.join(lines[2:]).strip()

        # Extract speaker tag
        speaker_match = re.match(r'\[([^\]]+)\]:\s*(.*)', text)
        if speaker_match:
            speaker = speaker_match.group(1)
            text = speaker_match.group(2).strip()
        else:
            speaker = None

        entries.append({
            'index': index,
            'start': start_ts,
            'end': end_ts,
            'speaker': speaker,
            'text': text
        })

    return entries

def merge_consecutive_speakers(entries):
    """Merge consecutive entries from the same speaker."""
    if not entries:
        return []

    merged = []
    current = None

    for entry in entries:
        # Fix missing speaker tags - assign to previous speaker if within 3 seconds
        if entry['speaker'] is None and current and (entry['start'] - current['end']) < 3:
            entry['speaker'] = current['speaker']

        if current is None:
            current = entry.copy()
        elif entry['speaker'] == current['speaker'] and entry['speaker'] is not None:
            # Same speaker - merge
            current['end'] = entry['end']
            current['text'] = current['text'] + ' ' + entry['text']
        else:
            # Different speaker - save current and start new
            merged.append(current)
            current = entry.copy()

    # Don't forget the last one
    if current:
        merged.append(current)

    return merged

def get_db_connection():
    """Get MySQL database connection."""
    return mysql.connector.connect(
        host='localhost',
        user='vagrant',
        password='vagrant',
        database='discussion_capture'
    )

def create_session(conn, session_name, owner_id=1):
    """Create a new session."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO session (name, owner_id, creation_date)
        VALUES (%s, %s, %s)
    """, (session_name, owner_id, datetime.now()))
    conn.commit()
    session_id = cursor.lastrowid
    cursor.close()
    return session_id

def create_session_device(conn, session_id, device_name):
    """Create a session device."""
    cursor = conn.cursor()

    # Generate a unique processing key
    import uuid
    processing_key = str(uuid.uuid4())[:32]

    cursor.execute("""
        INSERT INTO session_device (session_id, device_id, name, connected, removed, button_pressed, processing_key)
        VALUES (%s, NULL, %s, 0, 0, 0, %s)
    """, (session_id, device_name, processing_key))
    conn.commit()
    session_device_id = cursor.lastrowid
    cursor.close()
    return session_device_id

def create_speakers(conn, session_device_id, speaker_tags):
    """Create speaker records and return mapping."""
    cursor = conn.cursor()
    speaker_map = {}

    for tag in speaker_tags:
        cursor.execute("""
            INSERT INTO speaker (session_device_id, alias)
            VALUES (%s, %s)
        """, (session_device_id, tag))
        speaker_map[tag] = cursor.lastrowid

    conn.commit()
    cursor.close()
    return speaker_map

def insert_transcripts(conn, session_device_id, entries, speaker_map):
    """Insert transcript entries."""
    cursor = conn.cursor()

    for entry in entries:
        start_time = int(entry['start'])
        length = int(entry['end'] - entry['start'])
        if length < 1:
            length = 1

        text = entry['text']
        speaker_tag = entry['speaker']
        speaker_id = speaker_map.get(speaker_tag)

        # Check if it's a question
        is_question = text.strip().endswith('?')

        # Word count
        word_count = len(text.split())

        cursor.execute("""
            INSERT INTO transcript
            (session_device_id, start_time, length, transcript, question, word_count, speaker_tag, speaker_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (session_device_id, start_time, length, text, is_question, word_count, speaker_tag, speaker_id))

    conn.commit()
    cursor.close()

def main():
    if len(sys.argv) < 4:
        print("Usage: python import_srt.py <srt_file> <session_name> <device_name>")
        print("Example: python import_srt.py new_session.srt 'CFAA Discussion' 'Group 2'")
        sys.exit(1)

    srt_file = sys.argv[1]
    session_name = sys.argv[2]
    device_name = sys.argv[3]

    print(f"Parsing SRT file: {srt_file}")
    entries = parse_srt(srt_file)
    print(f"  Found {len(entries)} entries")

    # Get unique speakers
    speakers = set(e['speaker'] for e in entries if e['speaker'])
    print(f"  Speakers: {speakers}")

    print(f"\nMerging consecutive same-speaker segments...")
    merged = merge_consecutive_speakers(entries)
    print(f"  Merged to {len(merged)} entries")

    # Preview merged entries
    print("\n--- Preview (first 5 merged entries) ---")
    for i, entry in enumerate(merged[:5]):
        duration = entry['end'] - entry['start']
        preview = entry['text'][:80] + "..." if len(entry['text']) > 80 else entry['text']
        print(f"{i+1}. [{entry['speaker']}] ({duration:.1f}s): {preview}")

    print("\n--- Preview (last 5 merged entries) ---")
    for i, entry in enumerate(merged[-5:]):
        duration = entry['end'] - entry['start']
        preview = entry['text'][:80] + "..." if len(entry['text']) > 80 else entry['text']
        print(f"{len(merged)-4+i}. [{entry['speaker']}] ({duration:.1f}s): {preview}")

    # Ask for confirmation
    response = input(f"\nProceed with import? Session: '{session_name}', Device: '{device_name}' [y/N]: ")
    if response.lower() != 'y':
        print("Aborted.")
        sys.exit(0)

    # Connect to database
    print("\nConnecting to database...")
    conn = get_db_connection()

    try:
        # Create session
        print(f"Creating session: {session_name}")
        session_id = create_session(conn, session_name)
        print(f"  Session ID: {session_id}")

        # Create session device
        print(f"Creating session device: {device_name}")
        session_device_id = create_session_device(conn, session_id, device_name)
        print(f"  Session Device ID: {session_device_id}")

        # Create speakers
        print(f"Creating speakers: {speakers}")
        speaker_map = create_speakers(conn, session_device_id, speakers)
        print(f"  Speaker map: {speaker_map}")

        # Insert transcripts
        print(f"Inserting {len(merged)} transcript entries...")
        insert_transcripts(conn, session_device_id, merged, speaker_map)
        print("  Done!")

        print(f"\n=== Import Complete ===")
        print(f"Session ID: {session_id}")
        print(f"Session Device ID: {session_device_id}")
        print(f"Transcripts: {len(merged)}")
        print(f"Speakers: {len(speakers)}")

    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    main()
