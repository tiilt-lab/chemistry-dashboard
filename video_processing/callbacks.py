import config
import requests
import os
from datetime import datetime
import logging
import base64


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