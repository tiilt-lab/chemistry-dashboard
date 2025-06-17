import database
import logging
import re

def process_tagging_data(session_device_id, tagging_data):
    results = tagging_data['results']
    start = results[0]["start"]
    end = results[-1]["end"]

    # Get device transcripts.
    transcripts = database.get_transcripts(session_device_id=session_device_id, start_time=int(start), end_time=end)
    if len(transcripts) == 0:
        return
    # update the transcripts in the database.
    for i in range(len(transcripts)):
      database.set_speaker_tag(transcripts[i], results[i]['speaker'])



