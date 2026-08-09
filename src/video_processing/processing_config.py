from datetime import datetime, timezone
from processing_config_base import validate_start_message
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
    def from_json(data,source=None):
        # Shared field validation (parse/allowlist) — see processing_config_base.
        ok, res = validate_start_message(data)
        if not ok:
            return False, res
        auth_key = res['auth_key']
        encoding = res['encoding']
        sample_rate = res['sample_rate']
        channels = res['channels']
        offset = res['offset']
        sessionId = res['sessionId']
        deviceId = res['deviceId']

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
                start_offset = max((datetime.now(timezone.utc).replace(tzinfo=None) - server_start).total_seconds() - offset, 0.0)
            elif not session_key and source == "posthoc processing":
                server_start = datetime.strptime(data.get('server_start', None), "%Y-%m-%dT%H:%M:%S.%fZ")
                convert_off_set = datetime.strptime(data.get('off_set_date', None), "%a %b %d %H:%M:%S %Y")
                start_offset = max((convert_off_set - server_start).total_seconds() - offset, 0.0)
            else:
                logging.warning('Invalid key sent by device.')
                return False, "Invalid key."

            return True, ProcessingConfig(auth_key, session_key, server_start, start_offset, sample_rate, encoding, channels, embeddingsFile,sessionId,deviceId,videocartoonify,video,mimeExtension)
        except Exception:
            return False, "could not verify auth_key"

    def is_valid_key(self):
        return callbacks.get_redis_session_key(self.auth_key) is not None

