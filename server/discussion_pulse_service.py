"""
Discussion Pulse Service - Real-time rolling summary generation.

Generates periodic (every ~60 seconds) summaries of discussion segments,
extracting key topics and providing a digestible overview of the conversation.
"""
import logging
import json
from openai import OpenAI
import os
from dotenv import load_dotenv
from datetime import datetime
from app import db
from tables.discussion_pulse import DiscussionPulse
import database as db_helper

load_dotenv()

# Initialize OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key) if api_key else None

# Default time window for pulse generation (seconds)
DEFAULT_WINDOW_SECONDS = 45


def generate_pulse_for_window(session_device_id, start_time, end_time, transcripts):
    """
    Generate a single discussion pulse for a time window.

    Args:
        session_device_id: ID of the session device
        start_time: Start time of the window (seconds)
        end_time: End time of the window (seconds)
        transcripts: List of transcript objects within the window

    Returns:
        DiscussionPulse object if successful, None if failed
    """
    if not client:
        logging.error("Cannot generate pulse - OpenAI client not initialized")
        return None

    if not transcripts:
        logging.info(f"No transcripts in window {start_time}-{end_time}")
        return None

    try:
        # Build transcript text for LLM
        speaker_aliases = get_speaker_aliases(transcripts)
        transcript_text = prepare_transcript_text(transcripts, speaker_aliases)

        # Count unique speakers
        speaker_ids = set()
        speaker_counts = {}
        for t in transcripts:
            if t.speaker_id:
                speaker_ids.add(t.speaker_id)
                speaker_counts[t.speaker_id] = speaker_counts.get(t.speaker_id, 0) + 1

        # Get dominant speaker, but verify it exists in speaker table (FK constraint)
        dominant_speaker_id = None
        if speaker_counts:
            candidate_id = max(speaker_counts.items(), key=lambda x: x[1])[0]
            # Only use if speaker exists in database
            speaker = db_helper.get_speakers(id=candidate_id)
            if speaker:
                dominant_speaker_id = candidate_id

        # Call LLM to generate summary and extract topics
        result = call_llm_for_pulse(transcript_text, start_time, end_time)

        if not result:
            logging.error(f"LLM failed to generate pulse for window {start_time}-{end_time}")
            return None

        # Create and store the pulse
        pulse = DiscussionPulse(
            session_device_id=session_device_id,
            start_time=start_time,
            end_time=end_time,
            summary_text=result.get('summary', ''),
            topics=result.get('topics', []),
            speaker_count=len(speaker_ids),
            dominant_speaker_id=dominant_speaker_id,
            transcript_count=len(transcripts)
        )

        db.session.add(pulse)
        db.session.commit()

        logging.info(f"Generated pulse for session_device {session_device_id}: {start_time}-{end_time}")
        return pulse

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error generating pulse: {e}", exc_info=True)
        return None


def get_latest_pulse_time(session_device_id):
    """Get the end_time of the most recent pulse for this session device."""
    latest = DiscussionPulse.query.filter_by(
        session_device_id=session_device_id
    ).order_by(DiscussionPulse.end_time.desc()).first()

    return latest.end_time if latest else 0


def generate_next_pulse(session_device_id, window_seconds=DEFAULT_WINDOW_SECONDS):
    """
    Generate the next pulse for a session device.
    Called periodically during an active session.

    Args:
        session_device_id: ID of the session device
        window_seconds: Time window to summarize (default 60 seconds)

    Returns:
        DiscussionPulse object if successful, None if no new content
    """
    logging.info(f"[PULSE] generate_next_pulse called for session_device {session_device_id}")
    try:
        # Get the last pulse end time
        last_end = get_latest_pulse_time(session_device_id)
        logging.info(f"[PULSE] Last pulse end time: {last_end}")

        # Get new transcripts since last pulse
        transcripts = db_helper.get_transcripts(
            session_device_id=session_device_id
        )

        # Filter to only transcripts after last pulse
        new_transcripts = [t for t in transcripts if t.start_time >= last_end]

        if not new_transcripts:
            logging.info(f"[PULSE] No new transcripts for session_device {session_device_id}")
            return None

        # Determine the time range
        # If no previous pulse, start from first transcript time instead of 0
        # This ensures pulse generation works even when talking starts late
        if last_end == 0 and new_transcripts:
            start_time = min(t.start_time for t in new_transcripts)
        else:
            start_time = last_end
        max_time = max(t.start_time + t.length for t in new_transcripts)

        # Only generate if we have at least 20 seconds of content
        # (40% of window size to allow faster first pulse)
        if max_time - start_time < window_seconds * 0.4:  # 20 seconds minimum
            logging.info(f"[PULSE] Insufficient content duration: {max_time - start_time:.1f}s < {window_seconds * 0.4:.1f}s for session_device {session_device_id}")
            return None

        end_time = min(start_time + window_seconds, max_time)

        # Filter transcripts within this window
        window_transcripts = [t for t in new_transcripts if t.start_time < end_time]

        if len(window_transcripts) < 1:  # Need at least 1 transcript
            return None

        return generate_pulse_for_window(
            session_device_id,
            start_time,
            end_time,
            window_transcripts
        )

    except Exception as e:
        logging.error(f"Error in generate_next_pulse: {e}", exc_info=True)
        return None


def get_speaker_aliases(transcripts):
    """Get speaker ID to alias mapping."""
    speaker_ids = set()
    for t in transcripts:
        if t.speaker_id:
            speaker_ids.add(t.speaker_id)

    speaker_map = {}
    for speaker_id in speaker_ids:
        speaker = db_helper.get_speakers(id=speaker_id)
        if speaker:
            speaker_map[speaker_id] = speaker.get_alias()
        else:
            speaker_map[speaker_id] = f"Speaker {speaker_id}"

    return speaker_map


def prepare_transcript_text(transcripts, speaker_aliases):
    """Format transcripts for LLM input."""
    lines = []
    for t in transcripts:
        if t.speaker_id and t.speaker_id in speaker_aliases:
            speaker = speaker_aliases[t.speaker_id]
        elif t.speaker_tag:
            speaker = f"Speaker {t.speaker_tag}"
        else:
            speaker = "Unknown"

        lines.append(f"{speaker}: {t.transcript}")

    return "\n".join(lines)


def call_llm_for_pulse(transcript_text, start_time, end_time):
    """
    Call LLM to generate summary and extract topics.

    Args:
        transcript_text: Formatted transcript text
        start_time: Window start time
        end_time: Window end time

    Returns:
        Dict with 'summary' and 'topics' keys, or None on failure
    """
    if len(transcript_text) < 20:  # Too short to summarize
        return None

    # Format time for display
    start_min, start_sec = int(start_time // 60), int(start_time % 60)
    end_min, end_sec = int(end_time // 60), int(end_time % 60)
    time_range = f"{start_min}:{start_sec:02d} - {end_min}:{end_sec:02d}"

    prompt = f"""Analyze this segment of a collaborative discussion ({time_range}).

DISCUSSION SEGMENT:
{transcript_text}

Generate:
1. A brief 2-3 sentence summary capturing the main focus and progress of this segment
2. 3-5 key topics as short tags (1-3 words each)

Return JSON:
{{
    "summary": "Your 2-3 sentence summary here",
    "topics": ["topic1", "topic2", "topic3"]
}}

Focus on:
- What the group is working on or discussing
- Key ideas, questions, or decisions made
- The direction or momentum of the conversation"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Use faster/cheaper model for real-time
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "You are a skilled discussion analyst. Generate concise, insightful summaries that capture the essence of collaborative conversations. Return valid JSON only."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=300
        )

        result = json.loads(response.choices[0].message.content)
        return {
            'summary': result.get('summary', ''),
            'topics': result.get('topics', [])
        }

    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse LLM response: {e}")
        return None
    except Exception as e:
        logging.error(f"LLM call failed: {e}")
        return None


def get_all_pulses_for_session(session_device_id):
    """Get all pulses for a session device, ordered chronologically."""
    pulses = DiscussionPulse.query.filter_by(
        session_device_id=session_device_id
    ).order_by(DiscussionPulse.start_time).all()

    return [p.json() for p in pulses]
