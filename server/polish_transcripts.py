#!/usr/bin/env python3
"""
Polish transcripts and infer multiple speakers for Session 46 (GRIND Youth STEM Programs).

This script:
1. Reads all transcripts for a table (e.g., Table301 = devices 71, 72, 73)
2. Analyzes conversational patterns to infer different speakers
3. Polishes transcript text (fixes transcription errors, makes coherent)
4. Updates the database with correct speaker assignments and polished text
"""

import os
import sys
import json
import re

SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SERVER_DIR)
sys.path.insert(0, SERVER_DIR)

from dotenv import load_dotenv
load_dotenv()

import mysql.connector
from openai import OpenAI

import config
config.initialize()

DATABASE_USER = config.config['server']['database_user']

def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        user=DATABASE_USER,
        password=DATABASE_USER,
        database='discussion_capture'
    )

def get_transcripts_for_devices(device_ids):
    """Get all transcripts for the given device IDs, ordered by start_time."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    placeholders = ', '.join(['%s'] * len(device_ids))
    query = f"""
        SELECT t.id, t.transcript, t.start_time, t.session_device_id, t.speaker_tag, t.speaker_id,
               sd.name as device_name
        FROM transcript t
        JOIN session_device sd ON t.session_device_id = sd.id
        WHERE sd.id IN ({placeholders})
        ORDER BY t.start_time
    """
    cursor.execute(query, device_ids)
    results = cursor.fetchall()

    cursor.close()
    conn.close()
    return results

def get_existing_speakers(device_ids):
    """Get existing speakers for the given devices."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    placeholders = ', '.join(['%s'] * len(device_ids))
    query = f"SELECT id, session_device_id, alias FROM speaker WHERE session_device_id IN ({placeholders})"
    cursor.execute(query, device_ids)
    results = cursor.fetchall()

    cursor.close()
    conn.close()
    return results

def create_speaker(device_id, alias):
    """Create a new speaker for a device."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO speaker (session_device_id, alias) VALUES (%s, %s)",
        (device_id, alias)
    )
    speaker_id = cursor.lastrowid
    conn.commit()

    cursor.close()
    conn.close()
    return speaker_id

def update_transcript(transcript_id, polished_text, speaker_tag, speaker_id):
    """Update a transcript with polished text and speaker info."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE transcript SET transcript = %s, speaker_tag = %s, speaker_id = %s WHERE id = %s",
        (polished_text, speaker_tag, speaker_id, transcript_id)
    )
    conn.commit()

    cursor.close()
    conn.close()

def analyze_and_polish_batch(transcripts_batch, speaker_names, batch_num, total_batches):
    """
    Use GPT to analyze a batch of transcripts, infer speakers, and polish text.

    Returns list of {id, polished_text, speaker_name}
    """
    client = OpenAI()

    # Format transcripts for analysis
    transcript_texts = []
    for i, t in enumerate(transcripts_batch):
        transcript_texts.append(f"[{t['id']}] {t['transcript']}")

    prompt = f"""You are analyzing a roundtable discussion about STEM education collaboration.
The participants are discussing curriculum sharing, resource collaboration, and building technology platforms.

Known speaker types in this discussion:
- **Facilitator**: Organizes discussion, asks structured questions, does round-robin
- **Tech_Visionary**: Passionate about building platforms, AI, technology solutions
- **Resource_Provider**: Has equipment (micro:bits, iPads, studio, cameras), offers resources
- **Curriculum_Expert**: Focused on educational content, learning management systems
- **Dance_Arts_Rep**: From a dance/arts organization, STEM through dance

Available speaker names: {', '.join(speaker_names)}

For each transcript below:
1. INFER the speaker based on content, perspective, and conversational flow
2. POLISH the text: fix transcription errors, complete fragments, make coherent (preserve meaning)

Transcripts (batch {batch_num}/{total_batches}):
{chr(10).join(transcript_texts)}

Respond with JSON array:
[
  {{"id": <transcript_id>, "speaker": "<speaker_name>", "polished": "<polished text>"}},
  ...
]

IMPORTANT:
- Choose speaker from the available names based on who is most likely speaking
- Fix obvious transcription errors (e.g., "stem from dance" -> "STEM from Dance")
- Make fragments into complete sentences where possible
- Keep the meaning and intent intact
- If uncertain about speaker, use context from surrounding transcripts"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=8000
    )

    result_text = response.choices[0].message.content.strip()

    # Extract JSON from response
    json_match = re.search(r'\[.*\]', result_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            print(f"  Warning: Could not parse JSON response for batch {batch_num}")
            return []
    return []

def process_table(table_name, device_ids, speaker_names):
    """Process all transcripts for a table (e.g., Table301)."""
    print(f"\n{'='*60}")
    print(f"Processing {table_name} (devices {device_ids})")
    print(f"{'='*60}")

    # Get all transcripts
    transcripts = get_transcripts_for_devices(device_ids)
    print(f"Found {len(transcripts)} transcripts")

    # Get existing speakers and create new ones if needed
    existing_speakers = get_existing_speakers(device_ids)

    # Build speaker mapping: {device_id: {speaker_name: speaker_id}}
    speaker_map = {did: {} for did in device_ids}
    for sp in existing_speakers:
        speaker_map[sp['session_device_id']][sp['alias']] = sp['id']

    # Create any missing speakers for each device
    for device_id in device_ids:
        for speaker_name in speaker_names:
            if speaker_name not in speaker_map[device_id]:
                speaker_id = create_speaker(device_id, speaker_name)
                speaker_map[device_id][speaker_name] = speaker_id
                print(f"  Created speaker '{speaker_name}' (id={speaker_id}) for device {device_id}")

    # Process in batches of 25 transcripts
    batch_size = 25
    total_batches = (len(transcripts) + batch_size - 1) // batch_size

    updated_count = 0
    for batch_num in range(total_batches):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, len(transcripts))
        batch = transcripts[start_idx:end_idx]

        print(f"  Processing batch {batch_num + 1}/{total_batches} (transcripts {start_idx + 1}-{end_idx})...")

        results = analyze_and_polish_batch(batch, speaker_names, batch_num + 1, total_batches)

        # Update transcripts in database
        for result in results:
            t_id = result['id']
            polished = result['polished']
            speaker_name = result['speaker']

            # Find the device_id for this transcript
            transcript_data = next((t for t in batch if t['id'] == t_id), None)
            if transcript_data:
                device_id = transcript_data['session_device_id']
                speaker_id = speaker_map[device_id].get(speaker_name)

                if speaker_id:
                    update_transcript(t_id, polished, speaker_name, speaker_id)
                    updated_count += 1

        print(f"    Updated {len(results)} transcripts")

    print(f"\nTotal updated: {updated_count} transcripts")
    return updated_count


def process_table302():
    """Process Table302 - Youth Mentorship Programs discussion."""
    # Speaker types based on content analysis
    speakers = ['Program_Director', 'Mentor_Coordinator', 'Youth_Coach', 'Education_Specialist', 'Community_Builder']
    process_table('Table302', [74, 75, 76], speakers)


def process_table303():
    """Process Table303 - Youth Program Design discussion."""
    # Speaker types based on content analysis (youth voice, soft skills, career pathways)
    speakers = ['Program_Designer', 'Youth_Advocate', 'Career_Counselor', 'Skills_Trainer', 'Industry_Liaison']
    process_table('Table303', [77, 78, 79], speakers)


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        table = sys.argv[1]
        if table == 'Table301':
            speakers = ['Facilitator', 'Tech_Visionary', 'Resource_Provider', 'Curriculum_Expert', 'Dance_Arts_Rep']
            process_table('Table301', [71, 72, 73], speakers)
        elif table == 'Table302':
            process_table302()
        elif table == 'Table303':
            process_table303()
        else:
            print(f"Unknown table: {table}")
    else:
        print("Usage: python polish_transcripts.py [Table301|Table302|Table303]")
