import os
import sys
import config
import requests
import logging

# Shared payloads + retry policy live in src/common/callbacks_common.py
# (same shim pattern as connection_manager.py / redis_helper.py).
_COMMON = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
import callbacks_common  # noqa: E402


def _callback_base():
    # .../api/v1/callback — derived once from the video-metrics callback URL.
    # (Video config has no processing_callback accessor — a typo here once made
    # the restart callback fail every time, leaving dead runs flagged as
    # running for the 3h TTL.)
    return config.video_metrics_callback().rsplit('/', 1)[0]


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


def post_service_restarted(scope='video'):
    callbacks_common.post_service_restarted(_callback_base(), scope)


def post_connect(source):
    return callbacks_common.post_connect(config.connect_callback(), source)


def post_disconnect(source):
    return callbacks_common.post_disconnect(config.disconnect_callback(), source)


def post_video_metrics(source, video_metrics):
    result = {
        'source': source,
        'video_metrics': video_metrics
    }
    try:
        response = requests.post(config.video_metrics_callback(), json=result)
        return response.status_code == 200
    except Exception as e:
        logging.warning('video metric callback failed: {0}'.format(e))
        return False


def post_gaze_overlays(source, records, reset=False):
    # Overlay geometry (head/gaze/object boxes) for the dashboard's video
    # overlay toggles. The server appends to a per-pod JSONL; reset=True on a
    # run's first batch replaces the previous run's file.
    try:
        response = requests.post(_callback_base() + '/gaze_overlays',
                                 json={'source': source, 'records': records, 'reset': reset})
        return response.status_code == 200
    except Exception as e:
        logging.warning('gaze overlay callback failed: {0}'.format(e))
        return False


def post_posthoc_reset(source, scope):
    callbacks_common.post_posthoc_reset(_callback_base(), source, scope)


def post_posthoc_completed(source, models=None, scope='video'):
    callbacks_common.post_posthoc_completed(_callback_base(), source, models, scope)
