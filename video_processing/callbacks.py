import config
import requests
import os
from datetime import datetime
import logging
import base64

    
def post_cartoonized_image(source, sessionId,deviceId, byteimage):
    encoded = base64.b64encode(byteimage) 
    result = {
        'source': source,
        'sessionid' : sessionId,
        'deviceid' : deviceId,
        'image': encoded
    }
    try:
        response = requests.post(config.cartoonize_image_callback(),json=result)
        return response.status_code == 200
    except Exception as e:
        logging.info('cartoonize image callback  failed: {0}'.format(e))
        return False

def get_redis_session_key(auth_key):
    payload = {
        'auth_key': auth_key
    }
    try:
        response = requests.post(config.redis_session_key_callback(),json=payload)
        if response.status_code == 200:
            data = response.json()
            return data['redis_key']
        else:
            logging.info('get_redis_device_key  failed: {0}'.format(response))  
            return None 
    except Exception as e:
        logging.info('get_redis_device_key  failed: {0}'.format(e))
        return None        
 

def get_redis_session_config(session_key):
    payload = {
    'session_key': session_key
    }
    try:
        response = requests.post(config.redis_session_config_callback(),json=payload)
        if response.status_code == 200:
            data = response.json()
            return data['redis_session_key']
        else:
            logging.info('get_redis_session_config callback  failed: {0}'.format(response))  
            return None 
    except Exception as e:
        logging.info('get_redis_session_config callback  failed: {0}'.format(e))
        return None  
    
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
    
def post_video_metrics(source, video_metrics):
    result = {
        'source': source,
        'video_metrics': video_metrics
    }
    try:
        response = requests.post(config.video_metrics_callback(), json=result)
        transcript_id = response.json()['transcript_id'] if response.status_code == 200 else -1
        return response.status_code == 200, transcript_id
    except Exception as e:
        logging.warning('Transcript callback failed: {0}'.format(e))
        return False, -1