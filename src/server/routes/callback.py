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
  features = content.get('features', {})
  topic_id = content.get('topic_id', -1)
  emotional_tone = features.get('emotional_tone_value', 0)
  analytic_thinking = features.get('analytic_thinking_value', 0)
  clout = features.get('clout_value', 0)
  authenticity = features.get('authenticity_value', 0)
  certainty = features.get('certainty_value', 0)
  speaker_tag = content.get('speaker_tag', '')
  speaker_id = content.get('speaker_id', -1)
  res = {}

  session_device = database.get_session_devices(processing_key=key)
  if session_device:
    logging.info('Transcript received for session device {0} on session {1}.'.format(session_device.id, session_device.session_id))
    # Add data to database.
    transcript = database.add_transcript(session_device.id, start_time, end_time - start_time, transcript, len(questions) > 0, direction, emotional_tone, analytic_thinking, clout, authenticity, certainty, topic_id, speaker_tag, speaker_id)
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
  features = content.get('features', {})
  topic_id = content.get('topic_id', -1)
  emotional_tone = features.get('emotional_tone_value', 0)
  analytic_thinking = features.get('analytic_thinking_value', 0)
  clout = features.get('clout_value', 0)
  authenticity = features.get('authenticity_value', 0)
  certainty = features.get('certainty_value', 0)
  speaker_tag = content.get('speaker_tag', '')
  speaker_id = content.get('speaker_id', -1)


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

    transcript = database.add_transcript(session_device.id, start_time, end_time - start_time, transcript, len(questions) > 0, direction, emotional_tone, analytic_thinking, clout, authenticity, certainty, topic_id, speaker_tag, speaker_id)
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

@api_routes.route('/api/v1/processsyncstudentdata', methods=['POST'])
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
    asr, scorer = 'google-cloud-speech', 'liwc'
    try:
        parser = configparser.RawConfigParser()
        parser.read(path)
        if parser.has_section('processing'):
            asr = parser['processing'].get('asr', asr).strip()
            scorer = parser['processing'].get('scorer', scorer).strip()
    except Exception as e:
        logging.warning('Could not read audio model config: {0}'.format(e))
    return asr, scorer


# Fixed model stack of the video/metrics pipelines (not config-switchable yet),
# surfaced so every analysis section in the UI can say what computed it.
_STATIC_MODELS = {
    "attention": {
        "id": "gazefollow-modelspatial",
        "label": "Attended-visual-targets gaze model (Chong et al. 2020, GazeFollow) + YOLOv5m head detector (CrowdHuman)",
    },
    "emotion": {
        "id": "resmasking-fer2013",
        "label": "ResMaskingNet (FER-2013, 7 emotions)",
    },
    "objects": {
        "id": "yolov4-p7-coco",
        "label": "YOLOv4-P7 object detector (COCO)",
    },
    "participation": {
        "id": "all-mpnet-base-v2",
        "label": "Sentence-transformer semantic cohesion (all-mpnet-base-v2)",
    },
    "diarization": {
        "id": "spkrec-ecapa-voxceleb",
        "label": "SpeechBrain ECAPA-TDNN speaker embeddings (VoxCeleb)",
    },
    "keywords": {
        "id": "word2vec-googlenews",
        "label": "word2vec semantic matching (GoogleNews-300)",
    },
}


@api_routes.route('/api/v1/models', methods=['GET'])
@wrappers.verify_login(public=True)
def get_models(**kwargs):
    asr, scorer = _read_audio_models()
    result = {
        "transcription": {"id": asr, "label": _ASR_LABELS.get(asr, asr)},
        "scoring": {"id": scorer, "label": _SCORER_LABELS.get(scorer, scorer)},
    }
    result.update(_STATIC_MODELS)
    return json_response(result)


@api_routes.route('/api/v1/syncstudenttable', methods=['POST'])
@wrappers.verify_login()
def sync_student_table(**kwargs):
    if not cf.sync_enabled():
        return json_response({"message": "Student syncing is not configured for this instance."}, 400)
    url = cf.sync_peer_url() + "/api/v1/callback/processsyncstudentdata"
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
