import config
import requests
import os
from datetime import datetime
import logging
import base64
import json

def post_transcripts(source, start_time, end_time, transcript, doa, questions, keywords, features, topic_id, speaker_tag, speaker_id):
    result = {
        'source': source,
        'start_time': start_time,
        'end_time': end_time
    }
    if transcript:
        result['transcript'] = transcript
        result['questions'] = questions
    if doa:
        result['direction'] = doa
    if keywords:
        result['keywords'] = keywords
    if features:
        result['features'] = features
    if topic_id:
        result['topic_id'] = topic_id
    if speaker_tag:
        result['speaker_tag'] = speaker_tag
    if speaker_id:
        result['speaker_id'] = speaker_id
    try:
        response = requests.post(config.processing_callback(), json=result)
        transcript_id = response.json()['transcript_id'] if response.status_code == 200 else -1
        return response.status_code == 200, transcript_id
    except Exception as e:
        logging.warning('Transcript callback failed: {0}'.format(e))
        return False, -1

def post_tagging(source, tag, embeddingsFile):
    result = {
        'source': source,
        'tagging': tag,
        'embeddingsFile': embeddingsFile
    }
    try:
        response = requests.post(config.tagging_callback(),json=result)
        return response.status_code == 200
    except Exception as e:
        logging.info('Tagging callback failed: {0}'.format(e))
        return False

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

def post_speaker_transcript_metrics(transcript_data, speakers, participation_scores, internal_cohesion, responsivity, social_impact, newness, communication_density):
    result = {
        'source': transcript_data['source'],
        'start_time': transcript_data['start_time'],
        'end_time': transcript_data['end_time'],
        'transcript': transcript_data['transcript'],
        'direction': transcript_data['doa'],
        'questions': transcript_data['questions'],
        'keywords': transcript_data['keywords'],
        'features': transcript_data['features'],
        'topic_id': transcript_data['topic_id'],
        'speaker_tag': transcript_data['speaker_tag'],
        'speaker_id':transcript_data['speaker_id'],
        'speakers':speakers,
        'participation_scores': participation_scores,
        'internal_cohesion': internal_cohesion,
        'responsivity': responsivity,
        'social_impact': social_impact,
        'newness': newness,
        'communication_density': communication_density
    }
    try:
        response = requests.post(config.speaker_metrics_callback(), json=result)
        return response.status_code == 200
    except Exception as e:
        logging.warning('Speaker Metrics callback failed: {0}'.format(e))
        return False


def post_concept_update(session_device_id, concept_update, timestamp):
    """Post concept graph updates to the server
    
    Args:
        session_device_id: Format "sessionId:deviceId" (e.g., "123:456")
        concept_update: Dictionary containing nodes, edges, and discourse info
        timestamp: Time of the update
    """
    try:
        url = "http://127.0.0.1:5000/api/v1/concepts"
        
        data = {
            'source': session_device_id,
            'concept_update': concept_update,
            'timestamp': timestamp
        }
        
        logging.info(f"=== CONCEPT POST DEBUG ===")
        logging.info(f"URL: {url}")
        logging.info(f"Session Device ID: {session_device_id}")
        logging.info(f"Timestamp: {timestamp}")
        logging.info(f"Update type: {concept_update.get('type', 'unknown')}")
        logging.info(f"Nodes count: {len(concept_update.get('nodes', []))}")
        logging.info(f"Edges count: {len(concept_update.get('edges', []))}")
        
        # Log sample data for debugging
        if concept_update.get('nodes'):
            logging.info(f"First node: {json.dumps(concept_update['nodes'][0], indent=2)}")
        if concept_update.get('edges'):
            logging.info(f"First edge: {json.dumps(concept_update['edges'][0], indent=2)}")
        
        # Make the HTTP request
        response = requests.post(url, json=data, timeout=10)
        
        logging.info(f"Response status: {response.status_code}")
        if response.status_code != 200:
            logging.error(f"Response body: {response.text}")
        
        # Broadcast via WebSocket after successful save
        if response.status_code == 200:
            try:
                # Import here to avoid circular dependencies
                import requests as req
                websocket_url = "http://127.0.0.1:5000/api/v1/concepts/broadcast"
                broadcast_data = {
                    'session_device_id': session_device_id,
                    'concept_update': concept_update
                }
                req.post(websocket_url, json=broadcast_data, timeout=5)
                logging.info(f"WebSocket broadcast triggered for {session_device_id}")
            except Exception as ws_error:
                logging.warning(f"WebSocket broadcast failed (non-critical): {ws_error}")
        
        return response.status_code == 200
            
    except requests.exceptions.Timeout:
        logging.error(f"TIMEOUT: Concept update request timed out for {session_device_id}")
        return False
    except requests.exceptions.ConnectionError as e:
        logging.error(f"CONNECTION ERROR: Cannot reach concept server at {url}: {e}")
        return False
    except Exception as e:
        logging.error(f"EXCEPTION in post_concept_update: {e}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        return False