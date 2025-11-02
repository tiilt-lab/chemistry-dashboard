from datetime import datetime
from redis_helper import RedisSessions
import callbacks
import json
import logging
import config as cf

class ProcessingConfig:
    def __init__(self, auth_key, session_key, server_start, start_offset, sample_rate, encoding, channels, embeddingsFile,sessionId,deviceId,videocartoonify,video,mimeExtension):
        self.auth_key = auth_key
        self.session_key = session_key
        self.server_start = server_start
        self.start_offset = start_offset
        self.sample_rate = sample_rate
        self.encoding = encoding
        self.depth = 2 if self.encoding in ['pcm_f16le', 'pcm_i16le'] else 4
        self.channels = channels
        self.embeddingsFile = embeddingsFile
        self.sessionId = sessionId
        self.deviceId = deviceId
        self.videocartoonify = videocartoonify
        self.video = video
        self.mimeExtension = mimeExtension

    @staticmethod
    def from_json(data):
        auth_key = data.get('key', None)
        encoding = data.get('encoding', None)
        try:
            sample_rate = int(data.get('sample_rate', None))
        except Exception as e:
            return False, "sample_rate must be an integer."
        try:
            channels = int(data.get('channels', None))
        except Exception as e:
            return False, "channels must be an integer."
        try:
            offset = float(data.get('offset', 0.0))
        except Exception as e:
            return False, "offset must be a float."
        
        try:
            sessionId = int(data.get('sessionid', None))
        except Exception as e:
            return False, "sessionid must be an integer."
        
        try:
            deviceId = int(data.get('deviceid', None))
        except Exception as e:
            return False, "deviceid must be an integer."

        # Check if fields are missing.
        if not auth_key or not sample_rate or not encoding or not channels or not sessionId or not deviceId:
            return False, "Start messege requires key, sample_rate, encoding, sessionid, deviceid and channels."
        # Check if format is supported.
        if not encoding in ['pcm_i16le', 'pcm_f16le', 'pcm_f32le']:
            return False, "Unsupported encoding type."
        # Check if sample rate is supported.
        if not sample_rate in [16000, 32000, 44100, 48000]:
            return False, "Unsupported sample rate."
        
        embeddingsFile = data.get('embeddingsFile', None)

        # check if video cartoonify is activated and  selected by user
        videocartoonify = data.get('Video_cartoonify',False) and cf.video_cartoonize()

        # check if video only is activated and  selected by user
        video = data.get('Video',False) or cf.video_record_original() or cf.video_record_reduced()

        mimeExtension = data.get('mimeextension',None)
        # Check if auth is required and if key is valid.
        try:
            session_key = callbacks.get_redis_session_key(auth_key)
            if session_key:
                session_config = json.loads(callbacks.get_redis_session_config(session_key))
                server_start = datetime.strptime(session_config.get('server_start', None), "%Y-%m-%d %H:%M:%S")
                start_offset = max((datetime.utcnow() - server_start).total_seconds() - offset, 0.0)
            else:
                logging.warning('Invalid key sent by device.')
                return False, "Invalid key."

            return True, ProcessingConfig(auth_key, session_key, server_start, start_offset, sample_rate, encoding, channels, embeddingsFile,sessionId,deviceId,videocartoonify,video,mimeExtension)
        except Exception as e:
            return False, "could not verify auth_key"

    def is_valid_key(self):
        return callbacks.get_redis_session_key(self.auth_key) != None

