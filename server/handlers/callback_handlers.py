import database
import logging
import re

def process_tagging_data(session_device_id, tagging_data):
    # Get device transcripts.
    transcripts = database.get_transcripts(session_device_id=session_device_id)
    if len(transcripts) == 0:
        return

    # Parse current transcripts to sentences.
    sentence_timings = []
    regex = re.compile("[\.\?!]\s|$")
    for transcript in transcripts:
        average_word_duration = (transcript.length / transcript.word_count)
        duration_offset = transcript.start_time
        start = 0
        for m in regex.finditer(transcript.transcript):
            sentence = transcript.transcript[start:m.start() + 1]
            start = m.start() + 1
            sentence_length = len(sentence.split(' ')) * average_word_duration
            sentence_timings.append({
                'sentence': sentence,
                'start': duration_offset,
                'end': duration_offset + sentence_length,
                'model': transcript
            })
            duration_offset += sentence_length

    # Map speaker taggings to sentences.
    for tag, times_ranges in tagging_data.items():
        for time_range in times_ranges:
            start = sum(x * int(t) for x, t in zip([3600, 60, 1, 0.001], time_range[0].split(":")))
            end = sum(x * int(t) for x, t in zip([3600, 60, 1, 0.001], time_range[1].split(":")))
            duration = end - start
            for sentence_timing in sentence_timings:
                overlap = (min(sentence_timing['end'], end) - max(sentence_timing['start'], start)) / duration
                if overlap > 0:
                    if not 'overlap' in sentence_timing or overlap > sentence_timing['overlap']:
                        sentence_timing['overlap'] = overlap
                        sentence_timing['tag'] = tag
    sentence_timings = [sentence_timing for sentence_timing in sentence_timings if 'tag' in sentence_timing]

    # Rewrite transcripts.
    transcript_model = None
    transcript_models = []
    for sentence_timing in sentence_timings:
        if not transcript_model or transcript_model['tag'] != sentence_timing['tag']:
            if transcript_model:
                transcript_models.append(transcript_model)
            transcript_model = {'tag': sentence_timing['tag'], 'start': sentence_timing['start'], 'length': 0, 'transcript': '', 'keywords': []}
        transcript_model['transcript'] += sentence_timing['sentence']
        transcript_model['length'] += sentence_timing['end'] - sentence_timing['start']
        transcript_model['keywords'].extend(
            [keyword.json() for keyword in sentence_timing['model'].keywords if keyword.word in sentence_timing['sentence'] and not keyword.word in [keyword['word'] for keyword in transcript_model['keywords']]]
        )
    if transcript_model:
        transcript_models.append(transcript_model)

    # Replace the transcripts in the database.
    session_device = database.get_session_devices(id=session_device_id)

    if(session_device.in_session):
        database.delete_device_transcripts(session_device_id)
    
        for transcript_model in transcript_models:
            new_transcript = database.add_transcript(session_device_id, transcript_model['start'], transcript_model['length'], transcript_model['transcript'], '?' in transcript_model['transcript'], -1, 0, 0, 0, 0, 0, transcript_model['tag'])
            for keyword_model in transcript_model['keywords']:
    	        database.add_keyword_usage(new_transcript.id, keyword_model['word'], keyword_model['keyword'], keyword_model['similarity'])
