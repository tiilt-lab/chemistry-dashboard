from app import socketio
from flask import Blueprint, Response, request, abort
from device_websockets import ConnectionManager
from flask_socketio import emit
from datetime import datetime
from utility import json_response
import logging
import database
import json
import wrappers
import config as cf
import requests
from handlers import callback_handlers
import posthoc_state

api_routes = Blueprint('callback', __name__)

@api_routes.route('/api/v1/callback/connect', methods=['POST'])
# @wrappers.verify_local
def device_connected(**kwargs):
  # EXPECTED FORMAT
  # {
  #     'source': str
  #     'time': str
  # }
  content = request.get_json()
  key = content['source']
  session_device = database.get_session_devices(processing_key=key)

  # Update websockets
  if session_device:
    session_device.connected = True
    database.save_changes()
    room_name = str(session_device.session_id)
    socketio.emit('device_update', json.dumps(session_device.json()), room=room_name, namespace="/session")
    logging.info('Device {0} connected to the Audio Processing Service.'.format(session_device.id))
  return json_response()

@api_routes.route('/api/v1/callback/disconnect', methods=['POST'])
# @wrappers.verify_local
def device_disconnected(**kwargs):
  # EXPECTED FORMAT
  # {
  #     'source': str
  #     'time': str
  # }
  content = request.get_json()
  key = content['source']
  session_device = database.get_session_devices(processing_key=key)

  # Update websockets
  if session_device:
    session_device.connected = False
    session_device.button_pressed = False
    database.save_changes()
    room_name = str(session_device.session_id)
    socketio.emit('device_update', json.dumps(session_device.json()), room=room_name, namespace="/session")
    logging.info('Session device {0} disconnected from the APS.'.format(session_device.id))

    # Reconnect device if disconenct was not expected.
    if not session_device.removed and session_device.device_id:
      logging.info('Sending message to session device {0} to start again...'.format(session_device.id))
      ConnectionManager.instance.send_command(session_device.device_id, {'cmd': 'start', 'key': session_device.processing_key})
  return json_response()

@api_routes.route('/api/v1/callback/transcript_features', methods=['POST'])
def update_transcript_features(**kwargs):
    # Post-hoc E&T recomputation posts re-scored feature values for existing
    # transcript rows. Authenticated the same way as the other processing
    # callbacks: by the device's processing key ('source').
    content = request.get_json()
    key = content.get('source', '')
    updates = content.get('updates', [])
    session_device = database.get_session_devices(processing_key=key)
    if not session_device:
        return json_response({'message': 'Unknown processing key.'}, 400)
    count = database.update_transcript_features_batch(session_device.id, updates)
    logging.info('Recomputed features persisted for %d transcripts on device %d.',
                 count, session_device.id)
    return json_response({'updated': count})


@api_routes.route('/api/v1/callback/enqueue_posthoc', methods=['POST'])
@wrappers.verify_local
def enqueue_posthoc_local(**kwargs):
    # Localhost-only batch enqueue (ops/automation).
    import posthoc_queue
    body = request.get_json(silent=True) or {}
    added = posthoc_queue.enqueue(body['session_id'], body['device_ids'], models=body.get('models'))
    return json_response({'queued': added})


@api_routes.route('/api/v1/callback/posthoc_reset', methods=['POST'])
@wrappers.verify_local
def posthoc_reset(**kwargs):
    # A processing service is starting a FULL re-run: wipe the pod's previous
    # results so the new run replaces them instead of stacking duplicates.
    content = request.get_json() or {}
    device = database.get_session_devices(processing_key=content.get('source', ''))
    if device:
        # Keep serving the last-known duration while the wipe+re-run is in
        # flight (it is derived from the transcripts being deleted).
        posthoc_state.remember_duration(device.id, database.get_pod_duration(device.id))
        database.delete_pod_analysis(device.id, scope=content.get('scope', 'audio'))
        posthoc_state.mark_running(device.id, content.get('scope', 'audio'))
        logging.info('Post-hoc reset (%s) for device %d.', content.get('scope'), device.id)
    return json_response()


@api_routes.route('/api/v1/callback/posthoc_service_restarted', methods=['POST'])
@wrappers.verify_local
def posthoc_service_restarted(**kwargs):
    # A posthoc service announces a (re)start: clear its scope's running
    # flags. Any in-flight run died with the old process (observed: a system
    # OOM-kill mid-run left the queue waiting out the full 150-minute pod
    # timeout on a flag nobody would ever clear).
    content = request.get_json() or {}
    scope = content.get('scope', 'audio')
    cleared = posthoc_state.clear_scope(scope)
    if cleared:
        logging.info('Posthoc %s service restarted: cleared %d stale running flag(s).', scope, cleared)
    return json_response({'cleared': cleared})


@api_routes.route('/api/v1/callback/posthoc_completed', methods=['POST'])
@wrappers.verify_local
def posthoc_completed(**kwargs):
    # A processing service reports that a pod's post-hoc run finished. Lets a
    # run be marked complete even if the browser that triggered it disconnected.
    # Authenticated by processing key ('source'), like the other callbacks.
    content = request.get_json() or {}
    key = content.get('source', '')
    models = content.get('models')
    device = database.get_session_devices(processing_key=key)
    if device:
        database.mark_session_device_posthoc(device.id, models=models)
        posthoc_state.mark_done(device.id, content.get('scope'))
        logging.info('Post-hoc marked complete for device %d (server-side).', device.id)
    return json_response()


@api_routes.route('/api/v1/callback/transcript', methods=['POST'])
@wrappers.verify_local
def add_transcript(**kwargs):
  # EXPECTED FORMAT
  # {
  #     'source': str
  #     'start_time': int
  #     'end_time': int
  #     'transcript': str
  #     'direction': int
  #     'questions': [str]
  #     'keywords': [keyword]
  #     'features': features object
  #     'topic_id': int
  #     'speaker_tag':str
  #     'speaker_id': int
  # }
  content = request.get_json()
  key = content.get('source', '')
  start_time = content.get('start_time', 0)
  end_time = content.get('end_time', 0)
  transcript = content.get('transcript', '')
  direction = content.get('direction', -1)
  questions = content.get('questions', [])
  if questions is None:
    questions = []
  keywords = content.get('keywords', [])
  if keywords is None:
    keywords = []
  # Arrives as an explicit null when feature scoring is off — .get's
  # default only covers a missing key.
  features = content.get('features') or {}
  topic_id = content.get('topic_id', -1)
  emotional_tone = features.get('emotional_tone_value', 0)
  analytic_thinking = features.get('analytic_thinking_value', 0)
  clout = features.get('clout_value', 0)
  authenticity = features.get('authenticity_value', 0)
  certainty = features.get('certainty_value', 0)
  speaker_tag = content.get('speaker_tag', '')
  speaker_id = content.get('speaker_id', -1)
  voice_features = content.get('voice_features', None)
  res = {}

  session_device = database.get_session_devices(processing_key=key)
  if session_device:
    logging.info('Transcript received for session device {0} on session {1}.'.format(session_device.id, session_device.session_id))
    # Add data to database.
    transcript = database.add_transcript(session_device.id, start_time, end_time - start_time, transcript, len(questions) > 0, direction, emotional_tone, analytic_thinking, clout, authenticity, certainty, topic_id, speaker_tag, speaker_id, voice_features=voice_features)
    added_keywords = []
    for keyword in keywords:
      added_keywords.append(database.add_keyword_usage(transcript.id, keyword['word'], keyword['keyword'], keyword['similarity']))
    # Emit data on sockets.
    room_name = str(session_device.session_id)
    socketio.emit('transcript_update', json.dumps(transcript.json()), room=room_name, namespace="/session")
    res = {'transcript_id':transcript.__hash__()}
  return json_response(payload=res)

@api_routes.route('/api/v1/callback/speaker_transcript_metrics', methods=['POST'])
@wrappers.verify_local
def add_speaker_transcript_metrics(**kwargs):
  # EXPECTED FORMAT
  # {
  #     'source': str
  #     'start_time': int
  #     'end_time': int
  #     'transcript': str
  #     'direction': int
  #     'questions': [str]
  #     'keywords': [keyword]
  #     'features': features object
  #     'topic_id': int
  #     'speaker_tag':str
  #     'speaker_id': int
  #     'speakers': [str]
  #     'participation_scores': [float]
  #     'internal_cohesion': [float]
  #     'responsivity': [float]
  #     'social_impact': [float]
  #     'newness': [float]
  #     'communication_density': [float]
  # }
  content = request.get_json()
  key = content.get('source', '')
  start_time = content.get('start_time', 0)
  end_time = content.get('end_time', 0)
  transcript = content.get('transcript', '')
  direction = content.get('direction', -1)
  questions = content.get('questions', [])
  if questions is None:
    questions = []
  keywords = content.get('keywords', [])
  if keywords is None:
    keywords = []
  # Arrives as an explicit null when feature scoring is off — .get's
  # default only covers a missing key.
  features = content.get('features') or {}
  topic_id = content.get('topic_id', -1)
  emotional_tone = features.get('emotional_tone_value', 0)
  analytic_thinking = features.get('analytic_thinking_value', 0)
  clout = features.get('clout_value', 0)
  authenticity = features.get('authenticity_value', 0)
  certainty = features.get('certainty_value', 0)
  speaker_tag = content.get('speaker_tag', '')
  speaker_id = content.get('speaker_id', -1)
  voice_features = content.get('voice_features', None)

  speakers = content.get('speakers', [])
  participation_scores = content.get('participation_scores', [])
  internal_cohesion = content.get('internal_cohesion', [])
  responsivity = content.get('responsivity', [])
  social_impact = content.get('social_impact', [])
  newness = content.get('newness', [])
  communication_density = content.get('communication_density', [])

  res = {}

  session_device = database.get_session_devices(processing_key=key)
  if session_device:
    logging.info("Speaker Metrics received for session device %s for session %s." %
                 (session_device.id, session_device.session_id))

    transcript = database.add_transcript(session_device.id, start_time, end_time - start_time, transcript, len(questions) > 0, direction, emotional_tone, analytic_thinking, clout, authenticity, certainty, topic_id, speaker_tag, speaker_id, voice_features=voice_features)
    added_keywords = []
    for keyword in keywords:
      added_keywords.append(database.add_keyword_usage(transcript.id, keyword['word'], keyword['keyword'], keyword['similarity']))

    room_name = str(session_device.session_id)
    metrics = []
    for i in range(0, len(participation_scores)):
      speaker_id = speakers[i-1] if i != 0 else None
      metric = database.add_speaker_transcript_metrics(speaker_id=speaker_id,
                                              transcript_id=transcript.id,
                                              participation_score=participation_scores[i],
                                              internal_cohesion=internal_cohesion[i],
                                              responsivity=responsivity[i],
                                              social_impact=social_impact[i],
                                              newness=newness[i],
                                              communication_density=communication_density[i])
      metrics.append(metric.json())
    socketio.emit('transcript_metrics_update', json.dumps({'transcript':transcript.json(), 'speaker_metrics':metrics}), room=room_name, namespace="/session")
    res = {'transcript_id':transcript.__hash__()}
  return json_response(payload=res)

@api_routes.route('/api/v1/callback/speakervideometrics', methods=['POST'])
def add_speaker_video_metrics(**kwargs):
  # EXPECTED FORMAT
  # {
  #     'source': str
  #     'video_metrics': {"person_id_1" :[[time_stamp_1 :int, 
                                          # facial_emotion_1 :str, 
                                          # attention_level_1 : int,
                                          # object_focused_on_1 : str], ... ]
                          
                          # .... }
  # }
  content = request.get_json()
  key = content.get('source', '')
  video_metrics = content.get('video_metrics', {})
  

  session_device = database.get_session_devices(processing_key=key)
  if session_device:
    logging.info("Video Metrics received for session device %s for session %s." %
                 (session_device.id, session_device.session_id))
    
    room_name = str(session_device.session_id)
    added_metrics = []
    for persion_id in video_metrics:
      for metric in video_metrics[persion_id]:
        time_stamp, facial_emotion,attention_level,object_on_focus = metric
        added_metric = database.add_speaker_video_metrics(session_device.id,persion_id,time_stamp, facial_emotion,attention_level,object_on_focus)

        added_metrics.append(added_metric.json())
    
    socketio.emit('video_metrics_update', json.dumps({'speaker_video_metrics':added_metrics}), room=room_name, namespace="/session")
      
  return json_response()


@api_routes.route('/api/v1/callback/tag', methods=['POST'])
@wrappers.verify_local
def add_tagging(**kwargs):
  logging.info('Received tagging information...recalculating transcripts...')
  content = request.get_json()
  key = content['source']
  tagging_data = content['tagging']
  embeddingsFile = content['embeddingsFile']
  session_device = database.get_session_devices(processing_key=key)
  if session_device:
    callback_handlers.process_tagging_data(session_device.id, tagging_data)
    session_device.embeddings = embeddingsFile
  return json_response()

# Alias kept because older peers post to the /callback/-prefixed path; the
# outbound URL below uses the canonical one. Without the alias the two-instance
# student sync 404'd on every push.
@api_routes.route('/api/v1/processsyncstudentdata', methods=['POST'])
@api_routes.route('/api/v1/callback/processsyncstudentdata', methods=['POST'])
def process_sync_student_data(**kwargs):
  # Inbound: a configured peer pushes its roster here. Reject unless syncing
  # is enabled on this instance and the shared token matches.
  if not cf.sync_enabled() or request.headers.get('X-Sync-Token', '') != cf.sync_token():
    return json_response({"message": "sync not permitted"}, 403)
  contents = request.get_json() or {}
  students_data = contents.get("Students_data", [])
  logging.info("syncing {0} student records from peer".format(len(students_data)))
  try:
      for content in students_data:
        database.sync_student(content.get("lastname"), content.get("firstname"), content.get("username"), content.get("biometric_captured"))
  except Exception as e:
      logging.warning('student sync ingest failed: {0}'.format(e))
      return json_response({"message": "syncing failed"}, 400)
  return json_response()


@api_routes.route('/api/v1/sync/enabled', methods=['GET'])
@wrappers.verify_login(public=True)
def sync_enabled(**kwargs):
    return json_response({"enabled": cf.sync_enabled()})


# Human-readable labels for the models the audio processor is configured with,
# so the UI can state provenance without duplicating the audio config here.
_ASR_LABELS = {
    "google-cloud-speech": "Google Cloud Speech-to-Text (video model, en-US)",
    "whisper": "Whisper (open, offline)",
    "whisperx": "WhisperX (open; batched + word-level alignment)",
    "qwen3": "Qwen3-ASR 1.7B + ForcedAligner (open)",
    "qwen3-0.6b": "Qwen3-ASR 0.6B + ForcedAligner (open, fast)",
}
_EMOTION_LABELS = {
    "resmasking": "ResMaskingNet (FER-2013, 7 emotions)",
    "hsemotion": "HSEmotion EfficientNet-B2 (AffectNet-8, open SOTA)",
}
_SCORER_LABELS = {
    "liwc": "LIWC & Harvard General Inquirer lexicons",
    "open": "Harvard General Inquirer lexicon (open)",
    "llm": "Google Gemini (LLM)",
}


def _read_audio_models():
    import os
    import configparser
    path = os.environ.get('AUDIO_CONFIG_PATH') or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..', '..',
        'audio_processing', 'config.ini')
    # Defaults MUST match the config.py fallbacks, else this endpoint would
    # advertise a model the pipeline doesn't actually run when config.ini omits
    # the key (config.py keyword_backend() falls back to 'word2vec').
    models = {'asr': 'google-cloud-speech', 'scorer': 'liwc',
              'keyword_backend': 'word2vec', 'semantic_embedder': 'all-mpnet-base-v2'}
    try:
        parser = configparser.RawConfigParser()
        parser.read(path)
        if parser.has_section('processing'):
            p = parser['processing']
            models['asr'] = p.get('asr', models['asr']).strip()
            models['scorer'] = p.get('scorer', models['scorer']).strip()
            models['keyword_backend'] = p.get('keyword_backend', models['keyword_backend']).strip()
            models['semantic_embedder'] = p.get('semantic_embedder', models['semantic_embedder']).strip()
    except Exception as e:
        logging.warning('Could not read audio model config: {0}'.format(e))
    return models


# Diarization is a compound stack (ECAPA fingerprints + a selectable clustering
# backend), so it stays described statically. All other analyses are resolved
# from live config in get_models().
_STATIC_MODELS = {
    "diarization": {
        "id": "spkrec-ecapa-voxceleb",
        "label": "SpeechBrain ECAPA-TDNN fingerprints; pyannote 3.1 clustering selectable per re-run",
    },
}


def _read_video_models():
    import os
    import configparser
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..',
                        'video_processing', 'config.ini')
    # Defaults MUST match the config.py fallbacks so this endpoint never
    # advertises a model the pipeline isn't running. Note emotion_model() falls
    # back to 'resmasking' (config.ini sets hsemotion); object/attention fall
    # back to yolo11/gazelle.
    models = {'emotion': 'resmasking', 'objects': 'yolo11', 'attention': 'gazelle',
              'face': 'dlib', 'head': 'yolov5'}
    try:
        parser = configparser.RawConfigParser(allow_no_value=True)
        parser.read(path)
        models['emotion'] = parser.get('videoprocessing', 'emotion_model', fallback=models['emotion']).strip()
        models['objects'] = parser.get('videoprocessing', 'object_model', fallback=models['objects']).strip()
        models['attention'] = parser.get('videoprocessing', 'attention_model', fallback=models['attention']).strip()
        models['face'] = parser.get('videoprocessing', 'face_model', fallback=models['face']).strip()
        models['head'] = parser.get('videoprocessing', 'head_model', fallback=models['head']).strip()
    except Exception:
        pass
    return models


_ATTENTION_LABELS = {
    "gazefollow": "Attended-visual-targets gaze model (Chong et al. 2020, GazeFollow)",
    "gazelle": "Gaze-LLE (Meta 2024, DINOv2; open SOTA)",
}
_OBJECT_LABELS = {
    "yolov4": "YOLOv4-P7 object detector (COCO)",
    "yolo11": "YOLO11m object detector (COCO, open SOTA)",
}
_KEYWORD_LABELS = {
    "word2vec": "word2vec semantic matching (GoogleNews-300)",
    "embedding": "SentenceTransformer semantic matching (BGE, open)",
}
_EMBEDDER_LABELS = {
    "all-mpnet-base-v2": "MPNet sentence embedder (all-mpnet-base-v2)",
    "bge-large-en-v1.5": "BGE large v1.5 (open SOTA)",
}
_FACE_LABELS = {
    "dlib": "dlib ResNet face recognition (128-D)",
    "insightface": "InsightFace ArcFace buffalo_l (512-D, open SOTA)",
}
_HEAD_LABELS = {
    "yolov5": "YOLOv5m head detector (CrowdHuman)",
    "ultralytics": "YOLOv8m head detector (SCUT-HEAD classroom dataset)",
}


@api_routes.route('/api/v1/models', methods=['GET'])
@wrappers.verify_login(public=True)
def get_models(**kwargs):
    a = _read_audio_models()
    v = _read_video_models()

    def entry(value, labels):
        return {"id": value, "label": labels.get(value, value)}

    result = {
        "transcription": entry(a['asr'], _ASR_LABELS),
        "scoring": entry(a['scorer'], _SCORER_LABELS),
        "participation": entry(a['semantic_embedder'], _EMBEDDER_LABELS),
        "keywords": entry(a['keyword_backend'], _KEYWORD_LABELS),
        "emotion": entry(v['emotion'], _EMOTION_LABELS),
        "objects": entry(v['objects'], _OBJECT_LABELS),
        "attention": entry(v['attention'], _ATTENTION_LABELS),
        "face": entry(v['face'], _FACE_LABELS),
        "head_detector": entry(v['head'], _HEAD_LABELS),
    }
    # Diarization stays a compound (fingerprint + selectable clustering) entry.
    result["diarization"] = _STATIC_MODELS["diarization"]
    return json_response(result)


@api_routes.route('/api/v1/syncstudenttable', methods=['POST'])
@wrappers.verify_login()
def sync_student_table(**kwargs):
    if not cf.sync_enabled():
        return json_response({"message": "Student syncing is not configured for this instance."}, 400)
    url = cf.sync_peer_url() + "/api/v1/processsyncstudentdata"
    try:
        students = database.get_students()
        result = {"Students_data": [student.json() for student in students]}
        response = requests.post(url, json=result, headers={'X-Sync-Token': cf.sync_token()})
        if response.status_code == 200:
          return json_response()
        else:
          return json_response({"message": "syncing failed"}, 400)
    except Exception as e:
        logging.warning("Student data sync callback failed: {0}".format(e))
        return json_response({"message": "syncing failed"}, 400)
