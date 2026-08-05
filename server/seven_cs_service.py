import logging
import json
from openai import OpenAI
import os
from dotenv import load_dotenv
import time
from datetime import datetime, timedelta
from app import db
from tables.seven_cs_analysis import SevenCsAnalysis
from tables.seven_cs_coded_segment import SevenCsCodedSegment
from tables.speaker import Speaker
import database as db_helper

load_dotenv()


# Initialize OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key) if api_key else None

# 7C Framework Definition
SEVEN_CS_FRAMEWORK = {
    "climate": {
        "description": "The emotional and affective aspects of the collaboration",
        "indicators": ["respect", "comfort", "tone", "welcome", "safe", "listening", "being heard"],
        "scoring_criteria": "High scores indicate a respectful, comfortable environment where members feel safe to share ideas"
    },
    "communication": {
        "description": "The quantity and quality of information shared among group members",
        "indicators": ["verbal", "nonverbal", "discussion", "listening", "sharing", "goals", "expectations"],
        "scoring_criteria": "High scores indicate clear, active communication with good listening and information sharing"
    },
    "compatibility": {
        "description": "How well group members' working and interaction styles complement each other",
        "indicators": ["working style", "active", "equal distribution", "friends", "creative vision", "complementary skills"],
        "scoring_criteria": "High scores indicate compatible work styles and good team synergy"
    },
    "conflict": {
        "description": "Approaches to handling disagreements and contentious situations that arise during group work",
        "indicators": ["adapting", "differences", "confronting", "mediator", "resolution", "external validation"],
        "scoring_criteria": "High scores indicate effective conflict resolution and constructive handling of disagreements"
    },
    "context": {
        "description": "Environmental factors and situational awareness: the who, why, and where of the collaboration",
        "indicators": ["privacy", "out of school", "in/out of context", "interest", "group members", "setting"],
        "scoring_criteria": "High scores indicate appropriate context awareness and comfort with the environment"
    },
    "contribution": {
        "description": "Individual participation and effort balance: what individual participants are, and are not, bringing to the collaboration",
        "indicators": ["accountable", "balance of work", "tracking", "engagement", "effort", "verbal contributions"],
        "scoring_criteria": "High scores indicate balanced participation and equitable contribution from all members"
    },
    "constructive": {
        "description": "Overall goals of the collaboration and the team's progress toward achieving them",
        "indicators": ["goal", "product", "efficiency", "learning", "mutual benefit", "insights"],
        "scoring_criteria": "High scores indicate productive collaboration toward shared goals with mutual learning"
    }
}

def _load_dimensions(schema_id=None):
    """Load dimension definitions from DB schema or fall back to hardcoded default."""
    if schema_id:
        from tables.dimension_schema import DimensionSchema
        schema = DimensionSchema.query.get(schema_id)
        if schema:
            return schema.get_dimension_dict(), schema_id
    # Fall back: try default schema from DB, then hardcoded
    from tables.dimension_schema import DimensionSchema
    default = DimensionSchema.query.filter_by(is_default=True).first()
    if default:
        return default.get_dimension_dict(), default.id
    return SEVEN_CS_FRAMEWORK, None


def analyze_session_seven_cs(session_device_id, schema_id=None):
    """
    Perform collaboration assessment for a session device.
    Single-pass generation: sends full transcript to LLM and gets scores + explanations.

    Args:
        session_device_id: ID of the session device to analyze
        schema_id: Optional ID of a DimensionSchema to use (None = default)

    Returns:
        SevenCsAnalysis object if successful, None if failed
    """
    if not client:
        logging.error(f"Cannot perform analysis - OpenAI client not initialized")
        return None

    try:
        start_time = time.time()
        pool_dimensions, resolved_schema_id = _load_dimensions(schema_id)

        # Check for existing analysis - update instead of creating duplicate
        existing = SevenCsAnalysis.query.filter_by(
            session_device_id=session_device_id
        ).first()

        if existing:
            logging.info(f"Found existing analysis (id={existing.id}) for session_device {session_device_id}, will replace")

            # Capture active dimension keys BEFORE wiping — these define what to regenerate
            active_keys = list((existing.analysis_summary or {}).keys())

            if active_keys:
                # Filter pool to only the session's active dimensions
                dimensions = {}
                for key in active_keys:
                    if key in pool_dimensions:
                        dimensions[key] = pool_dimensions[key]
                    else:
                        logging.warning(
                            f"Dimension '{key}' active in session {session_device_id} "
                            f"but not found in pool — skipping"
                        )
                if not dimensions:
                    # All active keys were orphaned — fall back to full pool
                    logging.warning(f"No pool definitions found for any active dimension in session {session_device_id}, using full pool")
                    dimensions = pool_dimensions
            else:
                # Empty analysis_summary (shouldn't happen for completed analysis) — use full pool
                dimensions = pool_dimensions

            from tables.seven_cs_coded_segment import SevenCsCodedSegment
            SevenCsCodedSegment.query.filter_by(analysis_id=existing.id).delete()
            analysis = existing
            analysis.analysis_status = 'processing'
            analysis.analysis_summary = {}
            analysis.ai_baseline = {}
            analysis.schema_id = resolved_schema_id
        else:
            # First-time analysis: use full pool (7C default)
            dimensions = pool_dimensions
            analysis = SevenCsAnalysis(
                session_device_id=session_device_id,
                analysis_status='processing',
                schema_id=resolved_schema_id
            )
            db.session.add(analysis)

        db.session.commit()

        # Get all transcripts
        transcripts = db_helper.get_transcripts(session_device_id=session_device_id)

        if not transcripts:
            logging.info(f"No transcripts found for session_device {session_device_id}")
            analysis.analysis_status = 'failed'
            db.session.commit()
            return None

        # Single-pass generation: full transcript → LLM → scores + explanations
        full_transcript_text = prepare_full_transcript(transcripts)
        summary_result = generate_overall_seven_cs_summary(full_transcript_text, dimensions)

        processing_time = time.time() - start_time
        total_tokens = estimate_tokens(full_transcript_text)

        analysis.update_summary(
            summary_data=summary_result,
            segments_analyzed=len(transcripts),
            processing_time=processing_time,
            tokens_used=total_tokens
        )
        db.session.commit()

        logging.info(f"Successfully completed analysis for session_device {session_device_id} "
                     f"({len(dimensions)} dimensions, {processing_time:.1f}s)")

        from indexing_service import reindex_session
        from study_context import get_chroma_path
        reindex_session(session_device_id, reason="7c_analysis", chroma_path=get_chroma_path())

        return analysis

    except Exception as e:
        logging.error(f"Error in analysis for session_device {session_device_id}: {str(e)}")
        if 'analysis' in locals():
            analysis.analysis_status = 'failed'
            db.session.commit()
        return None

def code_transcripts_with_seven_cs(analysis_id, transcripts, window_size=8, overlap=2, deduplicate=True):
    """
    Process transcripts in sliding windows and code them with 7C dimensions.

    Uses transcript-count-based windows instead of time-based windows for consistent
    content density regardless of conversation pace.

    Args:
        analysis_id: ID of the analysis record
        transcripts: List of transcript objects
        window_size: Number of transcripts per window (default 8)
        overlap: Number of transcripts to overlap between windows (default 2)
        deduplicate: Whether to deduplicate segments (default True)

    Returns:
        List of SevenCsCodedSegment objects
    """
    coded_segments = []
    # Track already coded (quote, dimension) pairs to avoid duplicates
    already_coded = set()
    total_codings = 0
    duplicates_skipped = 0

    # Sort transcripts by start time
    sorted_transcripts = sorted(transcripts, key=lambda t: t.start_time)

    if not sorted_transcripts:
        logging.info(f"No transcripts to process for analysis {analysis_id}")
        return coded_segments

    total_transcripts = len(sorted_transcripts)
    step = window_size - overlap  # How many transcripts to advance each iteration

    logging.info(f"Processing {total_transcripts} transcripts with window_size={window_size}, overlap={overlap}")

    # Process transcript-count-based sliding windows
    window_start_idx = 0
    window_num = 0

    while window_start_idx < total_transcripts:
        window_end_idx = min(window_start_idx + window_size, total_transcripts)
        window_transcripts = sorted_transcripts[window_start_idx:window_end_idx]
        window_num += 1

        if window_transcripts:
            # Get time range for logging and storage
            window_start_time = window_transcripts[0].start_time
            window_end_time = window_transcripts[-1].start_time + window_transcripts[-1].length

            # Prepare window text
            window_text = prepare_window_text(window_transcripts)
            logging.info(f"Processing window {window_num} (transcripts {window_start_idx+1}-{window_end_idx}, time {window_start_time:.0f}-{window_end_time:.0f}s)")

            # Code this window with deduplication
            window_codings = code_window_with_seven_cs_deduplicated(
                window_text,
                analysis_id,
                window_transcripts,
                window_start_time,
                window_end_time,
                already_coded,
                deduplicate
            )

            # Track statistics
            total_codings += window_codings['total']
            duplicates_skipped += window_codings['duplicates_skipped']
            coded_segments.extend(window_codings['segments'])

            logging.info(f"Window {window_num} produced {window_codings['total']} codings, {window_codings['duplicates_skipped']} duplicates skipped")

        # Move to next window by step (window_size - overlap)
        window_start_idx += step

    logging.info(f"Coding complete: {total_codings} total codings from LLM, {duplicates_skipped} duplicates skipped, {len(coded_segments)} unique segments stored")
    return coded_segments

def get_speaker_aliases(transcripts):
    """
    Get a mapping of speaker_id to alias for all speakers in transcripts.

    Args:
        transcripts: List of transcript objects

    Returns:
        Dictionary mapping speaker_id to speaker alias
    """
    # Collect unique speaker IDs
    speaker_ids = set()
    for t in transcripts:
        if t.speaker_id:
            speaker_ids.add(t.speaker_id)

    # Fetch speakers from database
    speaker_map = {}
    for speaker_id in speaker_ids:
        speaker = db_helper.get_speakers(id=speaker_id)
        if speaker:
            speaker_map[speaker_id] = speaker.get_alias()
        else:
            # Fallback if speaker not found
            speaker_map[speaker_id] = f"Speaker {speaker_id}"

    return speaker_map

def prepare_window_text(transcripts):
    """
    Prepare transcript text for a window of transcripts.

    Args:
        transcripts: List of transcript objects in the window

    Returns:
        Formatted string of transcripts
    """
    # Get speaker aliases
    speaker_aliases = get_speaker_aliases(transcripts)

    transcript_lines = []
    for t in transcripts:
        # Determine speaker name
        if t.speaker_id and t.speaker_id in speaker_aliases:
            speaker = speaker_aliases[t.speaker_id]
        elif t.speaker_tag:
            speaker = f"Speaker {t.speaker_tag}"
        else:
            speaker = "Unknown"

        time_min, time_sec = divmod(t.start_time, 60)
        transcript_lines.append(f"[{speaker} at {time_min}:{time_sec:02d}]: {t.transcript}")

    return "\n".join(transcript_lines)

def find_matching_transcript(quote, window_transcripts):
    """
    Find which transcript best matches the given quote.

    Args:
        quote: The quote text from LLM coding
        window_transcripts: List of transcript objects in the window

    Returns:
        transcript_id of the best matching transcript, or None
    """
    if not quote or not window_transcripts:
        return window_transcripts[0].id if window_transcripts else None

    quote_lower = quote.lower().strip()
    best_match = None
    best_score = 0

    for transcript in window_transcripts:
        transcript_text = transcript.transcript.lower().strip()

        # Check for exact match
        if quote_lower in transcript_text:
            return transcript.id

        # Check for partial match (quote might be a substring)
        if transcript_text in quote_lower:
            return transcript.id

        # Calculate simple overlap score
        overlap_chars = sum(1 for char in quote_lower if char in transcript_text)
        score = overlap_chars / max(len(quote_lower), 1)

        if score > best_score:
            best_score = score
            best_match = transcript

    return best_match.id if best_match else window_transcripts[0].id

def code_window_with_seven_cs_deduplicated(window_text, analysis_id, window_transcripts, window_start, window_end, already_coded, deduplicate=True):
    """
    Wrapper for code_window_with_seven_cs that adds deduplication.

    Args:
        window_text: Formatted text of the window
        analysis_id: ID of the analysis record
        window_transcripts: List of transcript objects in the window
        window_start: Start time of window in seconds
        window_end: End time of window in seconds
        already_coded: Set of (quote, dimension) tuples already processed
        deduplicate: Whether to perform deduplication

    Returns:
        Dict with segments list, total codings count, and duplicates skipped count
    """
    # Get codings from the original function (without storing to DB yet)
    raw_codings = code_window_with_seven_cs_raw(window_text, window_transcripts, window_start, window_end)

    coded_segments = []
    total_codings = len(raw_codings)
    duplicates_skipped = 0

    for coding in raw_codings:
        if not isinstance(coding, dict):
            continue

        quote = coding.get('quote', '').strip()
        dimension = coding.get('dimension', '').lower()

        # Create deduplication key
        key = (quote[:200], dimension)  # Use first 200 chars of quote for key

        # Check if we should skip this coding
        if deduplicate and key in already_coded:
            duplicates_skipped += 1
            logging.debug(f"Skipping duplicate: {dimension} - {quote[:50]}...")
            continue

        # Add to already_coded set
        if deduplicate:
            already_coded.add(key)

        # Find the best matching transcript for this quote
        transcript_id = find_matching_transcript(quote, window_transcripts)

        # Create and store the segment
        segment = SevenCsCodedSegment(
            analysis_id=analysis_id,
            transcript_id=transcript_id,
            dimension=dimension,
            start_time=window_start,
            end_time=window_end,
            text_snippet=quote[:500],  # Limit to 500 chars
            speaker_tag=coding.get('speaker'),
            coding_reason=coding.get('explanation', ''),
            confidence=float(coding.get('confidence', 0.7))
        )
        db.session.add(segment)
        coded_segments.append(segment)

    db.session.commit()

    return {
        'segments': coded_segments,
        'total': total_codings,
        'duplicates_skipped': duplicates_skipped
    }

def code_window_with_seven_cs_raw(window_text, window_transcripts, window_start, window_end):
    """
    Use LLM to code a window of transcripts with 7C dimensions (returns raw codings without DB storage).

    Args:
        window_text: Formatted text of the window
        window_transcripts: List of transcript objects in the window
        window_start: Start time of window in seconds
        window_end: End time of window in seconds

    Returns:
        List of coding dictionaries from LLM
    """
    # Build the prompt
    prompt = f"""Analyze this discussion segment and identify which of the 7 dimensions of collaboration are present.

For EACH dimension that is clearly present in this segment, provide:
1. Whether it's strongly present (yes/no)
2. A specific quote from the transcript showing this dimension
3. Brief explanation of why this represents the dimension
4. Confidence level (0.0 to 1.0)

The 7 dimensions are:
- Climate: {SEVEN_CS_FRAMEWORK['climate']['description']}
  Indicators: {', '.join(SEVEN_CS_FRAMEWORK['climate']['indicators'])}

- Communication: {SEVEN_CS_FRAMEWORK['communication']['description']}
  Indicators: {', '.join(SEVEN_CS_FRAMEWORK['communication']['indicators'])}

- Compatibility: {SEVEN_CS_FRAMEWORK['compatibility']['description']}
  Indicators: {', '.join(SEVEN_CS_FRAMEWORK['compatibility']['indicators'])}

- Conflict: {SEVEN_CS_FRAMEWORK['conflict']['description']}
  Indicators: {', '.join(SEVEN_CS_FRAMEWORK['conflict']['indicators'])}

- Context: {SEVEN_CS_FRAMEWORK['context']['description']}
  Indicators: {', '.join(SEVEN_CS_FRAMEWORK['context']['indicators'])}

- Contribution: {SEVEN_CS_FRAMEWORK['contribution']['description']}
  Indicators: {', '.join(SEVEN_CS_FRAMEWORK['contribution']['indicators'])}

- Constructive: {SEVEN_CS_FRAMEWORK['constructive']['description']}
  Indicators: {', '.join(SEVEN_CS_FRAMEWORK['constructive']['indicators'])}

Discussion Segment:
{window_text}

Return a JSON object with a "segments" array containing ONLY the dimensions that are clearly present:
{{
    "segments": [
        {{
            "dimension": "climate|communication|compatibility|conflict|context|contribution|constructive",
            "quote": "exact quote from transcript",
            "explanation": "why this shows the dimension",
            "confidence": 0.0-1.0,
            "speaker": "speaker identifier if available"
        }}
    ]
}}

If no clear evidence of any dimension is found, return {{"segments": []}}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert in qualitative analysis of collaborative learning, specializing in the 7-dimension framework. Identify clear evidence of each dimension when present."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=1000
        )

        # Parse response
        result = json.loads(response.choices[0].message.content)
        logging.info(f"LLM response for coding window: {json.dumps(result)[:500]}")

        # Handle both array and object responses
        if isinstance(result, dict) and 'codings' in result:
            codings = result['codings']
        elif isinstance(result, dict) and 'segments' in result:
            codings = result['segments']
        elif isinstance(result, dict) and 'results' in result:
            codings = result['results']
        elif isinstance(result, dict) and 'dimensions' in result:
            codings = result['dimensions']
        elif isinstance(result, list):
            codings = result
        else:
            # If result is a dict with dimension names as keys
            codings = []
            for key, value in result.items():
                if key in ['climate', 'communication', 'compatibility', 'conflict', 'context', 'contribution', 'constructive']:
                    if isinstance(value, dict) and value.get('quote'):
                        value['dimension'] = key
                        codings.append(value)

        logging.info(f"Extracted {len(codings)} codings from LLM response")
        return codings

    except Exception as e:
        logging.error(f"Error coding window with 7 Cs: {e}")
        return []

def code_window_with_seven_cs(window_text, analysis_id, window_transcripts, window_start, window_end):
    """
    Use LLM to code a window of transcripts with 7C dimensions.

    Args:
        window_text: Formatted text of the window
        analysis_id: ID of the analysis record
        window_transcripts: List of transcript objects in the window
        window_start: Start time of window in seconds
        window_end: End time of window in seconds

    Returns:
        List of SevenCsCodedSegment objects
    """
    coded_segments = []

    # Build the prompt
    prompt = f"""Analyze this discussion segment and identify which of the 7 dimensions of collaboration are present.

For EACH dimension that is clearly present in this segment, provide:
1. Whether it's strongly present (yes/no)
2. A specific quote from the transcript showing this dimension
3. Brief explanation of why this represents the dimension
4. Confidence level (0.0 to 1.0)

The 7 dimensions are:
- Climate: {SEVEN_CS_FRAMEWORK['climate']['description']}
  Indicators: {', '.join(SEVEN_CS_FRAMEWORK['climate']['indicators'])}

- Communication: {SEVEN_CS_FRAMEWORK['communication']['description']}
  Indicators: {', '.join(SEVEN_CS_FRAMEWORK['communication']['indicators'])}

- Compatibility: {SEVEN_CS_FRAMEWORK['compatibility']['description']}
  Indicators: {', '.join(SEVEN_CS_FRAMEWORK['compatibility']['indicators'])}

- Conflict: {SEVEN_CS_FRAMEWORK['conflict']['description']}
  Indicators: {', '.join(SEVEN_CS_FRAMEWORK['conflict']['indicators'])}

- Context: {SEVEN_CS_FRAMEWORK['context']['description']}
  Indicators: {', '.join(SEVEN_CS_FRAMEWORK['context']['indicators'])}

- Contribution: {SEVEN_CS_FRAMEWORK['contribution']['description']}
  Indicators: {', '.join(SEVEN_CS_FRAMEWORK['contribution']['indicators'])}

- Constructive: {SEVEN_CS_FRAMEWORK['constructive']['description']}
  Indicators: {', '.join(SEVEN_CS_FRAMEWORK['constructive']['indicators'])}

Discussion Segment:
{window_text}

Return a JSON object with a "segments" array containing ONLY the dimensions that are clearly present:
{{
    "segments": [
        {{
            "dimension": "climate|communication|compatibility|conflict|context|contribution|constructive",
            "quote": "exact quote from transcript",
            "explanation": "why this shows the dimension",
            "confidence": 0.0-1.0,
            "speaker": "speaker identifier if available"
        }}
    ]
}}

If no clear evidence of any dimension is found, return {{"segments": []}}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert in qualitative analysis of collaborative learning, specializing in the 7-dimension framework. Identify clear evidence of each dimension when present."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=1000
        )

        # Parse response
        result = json.loads(response.choices[0].message.content)
        logging.info(f"LLM response for coding window: {json.dumps(result)[:500]}")

        # Handle both array and object responses
        if isinstance(result, dict) and 'codings' in result:
            codings = result['codings']
        elif isinstance(result, dict) and 'segments' in result:
            codings = result['segments']
        elif isinstance(result, dict) and 'results' in result:
            codings = result['results']
        elif isinstance(result, dict) and 'dimensions' in result:
            codings = result['dimensions']
        elif isinstance(result, list):
            codings = result
        else:
            # If result is a dict with dimension names as keys
            codings = []
            for key, value in result.items():
                if key in ['climate', 'communication', 'compatibility', 'conflict', 'context', 'contribution', 'constructive']:
                    if isinstance(value, dict) and value.get('quote'):
                        value['dimension'] = key
                        codings.append(value)

        logging.info(f"Extracted {len(codings)} codings from LLM response")

        # Create coded segment objects
        for coding in codings:
            if not isinstance(coding, dict):
                continue

            # Find the transcript that contains this quote (if possible)
            transcript_id = window_transcripts[0].id if window_transcripts else None

            segment = SevenCsCodedSegment(
                analysis_id=analysis_id,
                transcript_id=transcript_id,
                dimension=coding.get('dimension', '').lower(),
                start_time=window_start,
                end_time=window_end,
                text_snippet=coding.get('quote', '')[:500],  # Limit to 500 chars
                speaker_tag=coding.get('speaker'),
                coding_reason=coding.get('explanation', ''),
                confidence=float(coding.get('confidence', 0.7))
            )
            db.session.add(segment)
            coded_segments.append(segment)

        db.session.commit()

    except Exception as e:
        logging.error(f"Error coding window with 7 Cs: {e}")

    return coded_segments

def generate_overall_seven_cs_summary(full_transcript_text, dimensions=None):
    """
    Generate scores and explanations for each dimension via single-pass LLM call.

    Args:
        full_transcript_text: Complete transcript text
        dimensions: Dict of dimension definitions (key → {name, description, indicators, scoring_criteria})
                   Falls back to SEVEN_CS_FRAMEWORK if None.

    Returns:
        Dict with scores and explanations for each dimension
    """
    if dimensions is None:
        dimensions = SEVEN_CS_FRAMEWORK

    # Build dimension descriptions dynamically
    dim_lines = []
    dim_keys = []
    for key, dim in dimensions.items():
        name = dim.get('name', key.title())
        desc = dim.get('description', '')
        criteria = dim.get('scoring_criteria', '') or f"High scores indicate the transcript strongly reflects {name.lower()}"
        indicators = dim.get('indicators', [])
        indicator_str = ', '.join(indicators) if indicators else ''
        line = f"- {name} (key: \"{key}\"): {desc}"
        if indicator_str:
            line += f"\n  Indicators: {indicator_str}"
        line += f"\n  Scoring: {criteria}"
        dim_lines.append(line)
        dim_keys.append(key)

    dim_block = "\n".join(dim_lines)
    dim_key_list = "|".join(dim_keys)

    prompt = f"""Analyze this full discussion transcript and provide a comprehensive assessment of collaboration quality.

Full Discussion Transcript:
{full_transcript_text}

For EACH of the following dimensions, provide:
1. A score from 0-100, based on the extent to which the transcript reflects that dimension
2. A detailed explanation (2-3 sentences) of the score
3. 2-3 key evidence points (direct quotes or observations from the transcript)

Dimensions to analyze:
{dim_block}

Return a JSON object with this structure (use the dimension keys exactly as given):
{{
    "<dimension_key>": {{
        "score": 0-100,
        "explanation": "detailed explanation",
        "evidence": ["evidence point 1", "evidence point 2", "evidence point 3"]
    }}
}}

Include ALL {len(dim_keys)} dimensions: {dim_key_list}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {
                    "role": "system",
                    "content": f"You are an expert in collaborative learning assessment. Provide nuanced, evidence-based evaluations across {len(dim_keys)} dimensions."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=3000
        )

        result = json.loads(response.choices[0].message.content)

        # Ensure all dimensions are present
        for key in dim_keys:
            if key not in result:
                result[key] = {
                    "score": 50,
                    "explanation": "Insufficient data to assess this dimension",
                    "evidence": []
                }

        return result

    except Exception as e:
        logging.error(f"Error generating summary: {e}")
        return {
            key: {
                "score": 50,
                "explanation": "Analysis could not be completed",
                "evidence": []
            }
            for key in dim_keys
        }

def prepare_full_transcript(transcripts):
    """
    Prepare the full transcript text for overall analysis.

    Args:
        transcripts: List of all transcript objects

    Returns:
        Formatted string of all transcripts
    """
    sorted_transcripts = sorted(transcripts, key=lambda t: t.start_time)

    # Get speaker aliases
    speaker_aliases = get_speaker_aliases(sorted_transcripts)

    transcript_lines = []

    for t in sorted_transcripts:
        # Determine speaker name
        if t.speaker_id and t.speaker_id in speaker_aliases:
            speaker = speaker_aliases[t.speaker_id]
        elif t.speaker_tag:
            speaker = f"Speaker {t.speaker_tag}"
        else:
            speaker = "Unknown"

        time_min, time_sec = divmod(t.start_time, 60)
        transcript_lines.append(f"[{speaker} at {time_min}:{time_sec:02d}]: {t.transcript}")

    return "\n".join(transcript_lines)

def estimate_tokens(text):
    """
    Rough estimation of tokens in text.

    Args:
        text: Text to estimate tokens for

    Returns:
        Estimated token count
    """
    # Rough estimate: ~4 characters per token
    return len(text) // 4

def update_seven_cs_analysis(session_device_id, schema_id=None):
    """
    Update/re-run analysis for a session device (manual trigger).

    Args:
        session_device_id: ID of the session device to analyze
        schema_id: Optional dimension schema ID

    Returns:
        SevenCsAnalysis object if successful, None if failed
    """
    existing = db.session.query(SevenCsAnalysis).filter_by(
        session_device_id=session_device_id
    ).order_by(SevenCsAnalysis.created_at.desc()).first()

    if existing and existing.analysis_status == 'processing':
        time_since_update = datetime.utcnow() - existing.updated_at
        if time_since_update < timedelta(minutes=5):
            logging.info(f"Analysis already in progress for session_device {session_device_id}")
            return existing
        else:
            logging.warning(f"Analysis stuck in processing for {time_since_update}, marking as failed")
            existing.analysis_status = 'failed'
            db.session.commit()

    return analyze_session_seven_cs(session_device_id, schema_id=schema_id)