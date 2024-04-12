import config
import requests
import os
from datetime import datetime
import logging
import base64

def post_transcripts(source, start_time, end_time, transcript, doa, questions, keywords, features, topic_id):
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
    logging.info(result)
    try:
        response = requests.post(config.processing_callback(), json=result)
        return response.status_code == 200
    except Exception as e:
        return False

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
        return False
