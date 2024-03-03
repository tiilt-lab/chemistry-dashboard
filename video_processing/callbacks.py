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
