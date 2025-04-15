import config
import requests
import os
from datetime import datetime
import logging
import base64

def post_transcripts(source, start_time, end_time, transcript, doa, questions, keywords, features, topic_id, speaker_tag, speaker_id):
    result = {
        'source': source,
        'start_time': start_time,
        'end_time': end_time
    }
    if transcript:
        result['transcript'] = transcript
        result['questions'] = questions
    if doa:
        result['direction'] = doa
    if keywords:
        result['keywords'] = keywords
    if features:
        result['features'] = features
    if topic_id:
        result['topic_id'] = topic_id
    if speaker_tag:
        result['speaker_tag'] = speaker_tag
    if speaker_id:
        result['speaker_id'] = speaker_id
    try:
        response = requests.post(config.processing_callback(), json=result)
        transcript_id = response.json()['transcript_id'] if response.status_code == 200 else -1
        return response.status_code == 200, transcript_id
    except Exception as e:
        logging.warning('Transcript callback failed: {0}'.format(e))
        return False, -1

def post_tagging(source, tag, embeddingsFile):
    result = {
        'source': source,
        'tagging': tag,
        'embeddingsFile': embeddingsFile
    }
    try:
        response = requests.post(config.tagging_callback(),json=result)
        return response.status_code == 200
    except Exception as e:
        logging.info('Tagging callback failed: {0}'.format(e))
        return False

def post_connect(source):
    connection = {
        'source': source,
        'time': str(datetime.utcnow())
    }
    try:
        logging.info('end point')
        logging.info(config.connect_callback())
        response = requests.post(config.connect_callback(), json=connection)
        logging.info(response.status_code)
        return response.status_code == 200
    except Exception as e:
        logging.info('connect callback failed: {0}'.format(e))
        return False

def post_disconnect(source):
    disconnection = {
        'source': source,
        'time': str(datetime.utcnow())
    }
    try:
        response = requests.post(config.disconnect_callback(), json=disconnection)
        return response.status_code == 200
    except Exception as e:
        logging.info('disconnect callback failed: {0}'.format(e))
        return False

def post_speaker_transcript_metrics(transcript_data, speakers, participation_scores, internal_cohesion, responsivity, social_impact, newness, communication_density):
    result = {
        'transcript_data': transcript_data,
        'speakers':speakers,
        'participation_scores': participation_scores,
        'internal_cohesion': internal_cohesion,
        'responsivity': responsivity,
        'social_impact': social_impact,
        'newness': newness,
        'communication_density': communication_density
    }
    try:
        response = requests.post(config.speaker_metrics_callback(), json=result)
        return response.status_code == 200
    except Exception as e:
        logging.warning('Speaker Metrics callback failed: {0}'.format(e))
        return False
