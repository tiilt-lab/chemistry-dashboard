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
from handlers import callback_handlers
from rag_auto_indexer import get_auto_indexer

api_routes = Blueprint('callback', __name__)

@api_routes.route('/api/v1/callback/connect', methods=['POST'])
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

@api_routes.route('/api/v1/callback/transcript', methods=['POST'])
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
    if transcript:
    # Add to RAG auto-indexer (lazy init on first use)
      try:
          get_auto_indexer().add_transcript(transcript.session_device_id, transcript)
      except Exception as e:
          logging.warning(f"RAG auto-index failed: {e}")
    # Emit data on sockets.
    room_name = str(session_device.session_id)
    socketio.emit('transcript_update', json.dumps(transcript.json()), room=room_name, namespace="/session")
    res = {'transcript_id':transcript.__hash__()}
  return json_response(payload=res)

@api_routes.route('/api/v1/callback/speaker_transcript_metrics', methods=['POST'])
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


@api_routes.route('/api/v1/callback/tag', methods=['POST'])
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
