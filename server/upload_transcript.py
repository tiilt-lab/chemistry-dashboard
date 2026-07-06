import database
import pandas as pd
import math
import re
import logging


CSV_FILE = "Week5-thursday-group6-10am_2.csv"




def time_to_seconds(value):
    """
    Converts Excel time like 0:01:05 into seconds.
    """
    if pd.isna(value):
        return 0

    value = str(value).strip()

    parts = value.split(":")
    parts = [int(float(p)) for p in parts]

    if len(parts) == 3:
        hours, minutes, seconds = parts
        return hours * 3600 + minutes * 60 + seconds

    if len(parts) == 2:
        minutes, seconds = parts
        return minutes * 60 + seconds

    return int(parts[0])


def clean_int(value, default=None):
    if pd.isna(value) or value == "":
        return default

    try:
        return int(float(value))
    except ValueError:
        return default


def is_question(transcript):
    if not transcript:
        return 0

    return 1 if str(transcript).strip().endswith("?") else 0


def estimate_length_seconds(current_start, next_start):
    """
    Uses the next utterance start time to estimate length.
    If unavailable, defaults to 0.
    """
    if next_start is None:
        return 0

    length = next_start - current_start
    return max(length, 0)


def main():
    df = pd.read_csv(CSV_FILE)

    # Normalize column names
    df.columns = [col.strip() for col in df.columns]

    # Convert start time first
    df["start_time_seconds"] = df["Start Time"].apply(time_to_seconds)

    # Estimate length using next row's start time
    df["next_start_time_seconds"] = df["start_time_seconds"].shift(-1)
    df["length_seconds"] = df.apply(
        lambda row: estimate_length_seconds(
            row["start_time_seconds"],
            row["next_start_time_seconds"]
        ),
        axis=1
    )

    

    rows_inserted = 0

    for _, row in df.iterrows():
        transcript = str(row.get("Transcript", "")).strip()             # transcript
        session_device_id = clean_int(row.get("Device ID"))             # session_device_id
        start_time = clean_int(row.get("start_time_seconds"), 0)        # start_time
        length = clean_int(row.get("length_seconds"), 0)                # length
        question = is_question(transcript)                              # question
        direction = clean_int(row.get("Direction"))                     # direction
        emotional_tone = clean_int(row.get("Emotional Tone"))           # emotional_tone_value
        analytic_thinking = clean_int(row.get("Analytic Thinking"))     # analytic_thinking_value
        clout = clean_int(row.get("Clout"))                             # clout_value
        authenticity = clean_int(row.get("Authenticity"))               # authenticity_value
        certainty = clean_int(row.get("Certainty"))                     # certainty_value
        tag = str(row.get("Speaker Tag", None))                         # speaker_tag
        topic_id = clean_int(row.get("Topic ID"))                       # topic_id
        speaker_id = clean_int(row.get("Speaker ID"))                   # speaker_id
        retVal = database.add_transcript(session_device_id, start_time, length, transcript, question, direction, emotional_tone, analytic_thinking, clout, authenticity, certainty, topic_id ,tag, speaker_id)
        if retVal:
            rows_inserted += 1
        # values = (
        #     clean_int(row.get("Device ID")),                       # session_device_id
        #     clean_int(row.get("start_time_seconds"), 0),           # start_time
        #     clean_int(row.get("length_seconds"), 0),               # length
        #     is_question(transcript),                               # question
        #     transcript,                                            # transcript
        #     clean_int(row.get("Word Count"), 0),                   # word_count
        #     clean_int(row.get("Direction")),                       # direction
        #     clean_int(row.get("Emotional Tone")),                  # emotional_tone_value
        #     clean_int(row.get("Analytic Thinking")),               # analytic_thinking_value
        #     clean_int(row.get("Clout")),                           # clout_value
        #     clean_int(row.get("Authenticity")),                    # authenticity_value
        #     clean_int(row.get("Certainty")),                       # certainty_value
        #     str(row.get("Speaker Tag", None))                      # speaker_tag
        #     clean_int(row.get("Topic ID")),                        # topic_id
        #     clean_int(row.get("Speaker ID")),                      # speaker_id
        # )
        # logging.info("transcript processed {0}".format(values))
        

    print(f"Inserted {rows_inserted} rows successfully.")


if __name__ == "__main__":
    main()