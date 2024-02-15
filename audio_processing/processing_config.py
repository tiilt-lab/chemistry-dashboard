from datetime import datetime
from redis_helper import RedisSessions
import json
import logging
import config as cf

class ProcessingConfig:
    def __init__(self, auth_key, session_key, server_start, start_offset, sample_rate, encoding, channels, transcribe, keywords, doa, features, tag, diarization, embeddingsFile,sessionId,deviceId,videocartoonify):
        self.auth_key = auth_key
        self.session_key = session_key
        self.server_start = server_start
        self.start_offset = start_offset
        self.sample_rate = sample_rate
        self.encoding = encoding
        self.depth = 2 if self.encoding in ['pcm_f16le', 'pcm_i16le'] else 4
        self.channels = channels
        self.transcribe = transcribe
        self.keywords = keywords
        self.doa = doa
        self.features = features
        self.tag = tag
        self.diarization = True # Default to true for testing.
        self.embeddingsFile = embeddingsFile
        self.sessionId = sessionId
        self.deviceId = deviceId
        self.videocartoonify = videocartoonify

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
        # Check if tagging is requested and is possible.
        tag = data.get('tag', False) and cf.record_original() and channels == 2
        # Check if diarization is requested and possible.
        diarization = data.get('tag', False)
        embeddingsFile = data.get('embeddingsFile', None)

        # check if video cartoonify is activated and  selected by user
        videocartoonify = data.get('Video_cartoonify',False) and cf.video_cartoonize()

        # Check if auth is required and if key is valid.
        session_key = RedisSessions.get_device_key(auth_key)
        if session_key:
            RedisSessions.get_session_config(session_key)
            session_config = json.loads(RedisSessions.get_session_config(session_key))
            server_start = datetime.strptime(session_config.get('server_start', None), "%Y-%m-%d %H:%M:%S")
            start_offset = max((datetime.utcnow() - server_start).total_seconds() - offset, 0.0)
            transcribe = session_config.get('transcribe', True)
            features = session_config.get('features', False)
            keywords = session_config.get('keywords', [])
            doa = session_config.get('doa', False)
        else:
            logging.warning('Invalid key sent by device.')
            return False, "Invalid key."

        return True, ProcessingConfig(auth_key, session_key, server_start, start_offset, sample_rate, encoding, channels, transcribe, keywords, doa, features, tag, diarization, embeddingsFile,sessionId,deviceId,videocartoonify)

    def is_valid_key(self):
        return RedisSessions.get_device_key(self.auth_key) != None

