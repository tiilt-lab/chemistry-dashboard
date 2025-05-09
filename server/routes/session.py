from flask import Blueprint, Response, request, abort, session, make_response
from utility import sanitize, string_to_bool, json_response
from tables.session_device import SessionDevice
from redis_helper import RedisSessions
from tables.session import Session
from utility import json_response
from app import socketio
import logging
import database
import json
from datetime import datetime, timedelta
from handlers import session_handler
import wrappers
import config as cf
import socketio_helper
import string
import csv
import io
import os
import base64
import queue

api_routes = Blueprint('session', __name__)
image_queue_dict = {}

@api_routes.route('/api/v1/sessions', methods=['GET'])
@wrappers.verify_login(public=True)
def get_sessions(user, **kwargs):
    return json_response([session.json() for session in database.get_sessions(owner_id=user['id'])])

@api_routes.route('/api/v1/sessions/<int:session_id>', methods=['GET'])
@wrappers.verify_login(public=True)
@wrappers.verify_session_access
def get_session(session, **kwargs):
    return json_response(session.json())

@api_routes.route('/api/v1/sessions/<int:session_id>', methods=['PUT'])
@wrappers.verify_login(public=True)
@wrappers.verify_session_access
def update_session(session_id, user, **kwargs):
    name = request.json.get('name', None)
    folder= request.json.get('folder', None)
    if name:
        valid, message = Session.verify_fields(name=name)
        if not valid:
            return json_response({'message': message}, 400)
    if folder != -1:
        owned_folder = database.get_folders(id=folder, owner_id=user['id'], first =True)
        if not owned_folder:
            return json_response({'message': 'Either the folder does not exist or invalid access'}, 404)
    session = database.update_session(session_id, name, folder)
    return json_response(session.json())

@api_routes.route('/api/v1/sessions/<int:session_id>', methods=['DELETE'])
@wrappers.verify_login(public=True)
@wrappers.verify_session_access
def delete_session(session_id, **kwargs):
    success = database.delete_session(session_id)
    if success:
        return json_response()
    else:
        return json_response({'message': 'Failed to delete session.'}, 400)

@api_routes.route('/api/v1/sessions', methods=['POST'])
@wrappers.verify_login(public=True)
def create_session(user, **kwargs):
    name = request.json.get('name', 'Session')
    valid, message = Session.verify_fields(name=name)
    if not valid:
        return json_response({'message': message}, 400)
    devices = request.json.get('devices', [])
    keyword_list_id = sanitize(request.json.get('keywordListId', None))
    topic_model_id = sanitize(request.json.get('topicModelId', None))
    byod = request.json.get('byod', False)
    features = request.json.get('features', True)
    doa = request.json.get('doa', False)
    folder = request.json.get('folder', None)
    if folder == -1:
        folder = None
    if folder:
        owned_folder = database.get_folders(id=folder, owner_id=user['id'], first =True)
        if not owned_folder:
            return json_response({'message': 'Either the folder does not exist or invalid access'}, 404)
    new_session = session_handler.create_session(user['id'], name, devices, keyword_list_id, topic_model_id, byod, features, doa, folder)
    return json_response(new_session.json())

@api_routes.route('/api/v1/sessions/byod', methods=['POST'])
def byod_join_session(**kwargs):
    name = request.json.get('name', None)
    passcode = sanitize(request.json.get('passcode', None))
    collaborators = request.json.get('collaborators', None)
    if not name or not passcode:
        return json_response({'message': 'Must supply name and passcode.'}, 400)
    valid, message = SessionDevice.verify_fields(name=name)
    if not valid:
        return json_response({'message': message}, 400)
    success, data = session_handler.byod_join_session(name, passcode, collaborators)
    if success:
        return json_response(data)
    else:
        return json_response({'message': data}, 400)

# Same as /api/sessions/byod but bypasses the passcode.
@api_routes.route('/api/v1/sessions/<int:session_id>/devices', methods=['POST'])
@wrappers.verify_login(public=True)
def device_join_session(session_id, **kwargs):
    name = request.json.get('name', None)
    valid, message = SessionDevice.verify_fields(name=name)
    if not valid:
        return json_response({'message': message}, 400)
    success, data = database.create_session_device(session_id, name)
    if success:
        RedisSessions.create_device_key(data.processing_key, session_id)
        return json_response({'session_device': data.json(), 'key': data.processing_key})
    else:
        return json_response({'message': data}, 400)

@api_routes.route('/api/v1/sessions/pod', methods=['POST'])
@wrappers.verify_login(public=True)
@wrappers.verify_session_access_json
def pod_join_session(**kwargs):
    session_id = request.json.get('sessionId', None)
    pod_id = request.json.get('podId', None)
    if not session_id or not pod_id:
        return json_response({'message': 'Must supply sessionId and PodId.'}, 400)
    success, response = session_handler.pod_join_session(session_id, pod_id)
    if success:
        return json_response(response)
    else:
        return json_response(response, 400)

@api_routes.route('/api/v1/sessions/<int:session_id>/stop', methods=['POST'])
@wrappers.verify_login(public=True)
@wrappers.verify_session_access
def end_session(session_id, **kwargs):
    success, data = session_handler.end_session(session_id)
    if success:
        return json_response(data.json())
    else:
        return json_response({'message': data}, 400)

@api_routes.route('/api/v1/sessions/<int:session_id>/devices/<int:device_id>/transcripts', methods=['GET'])
@wrappers.verify_login(public=True)
@wrappers.verify_session_access
def session_device_transcripts(session_id, device_id, **kwargs):
    transcripts = database.get_transcripts(session_device_id=device_id)
    return json_response([transcript.json() for transcript in transcripts])

@api_routes.route('/api/v1/sessions/devices/<int:device_id>/speakers/<int:speaker_id>/transcripts', methods=['GET'])
@wrappers.verify_login(public=True)
@wrappers.verify_session_access
def speaker_id_transcripts_for(device_id, speaker_id, **kwargs):
    transcripts = database.get_transcripts(speaker_id=speaker_id)
    return json_response([transcript.json() for transcript in transcripts])

@api_routes.route('/api/v1/sessions/devices/<int:device_id>/speaker_tags', methods=['GET'])
#@wrappers.verify_login(public=True)
#@wrappers.verify_session_access
def speaker_tags_for(device_id, **kwargs):
    tags = database.get_speaker_tags(session_device_id=device_id)
    return json_response({"Speakers": tags})

@api_routes.route('/api/v1/devices/<int:device_id>/transcripts/client', methods=['GET'])
# @wrappers.verify_login(public=True)
# @wrappers.verify_session_access
def session_device_transcripts_for_client(device_id, **kwargs):
    transcripts = database.get_transcripts(session_device_id=device_id)
    return json_response([transcript.json() for transcript in transcripts])

@api_routes.route('/api/v1/devices/<int:device_id>/transcripts/speaker_metrics', methods=['GET'])
def session_device_speaker_metrics(device_id, **kwargs):
    speaker_metrics = database.get_speaker_transcript_metrics(session_device_id=device_id)
    logging.info(f'Received speaker metrics from database{speaker_metrics}')
    return json_response([speaker_metric.json() for speaker_metric in speaker_metrics])

@api_routes.route('/api/v1/sessions/<int:session_id>/transcripts/speaker_metrics', methods=['POST'])
def session_transcript_speaker_metrics(session_id):
    transcripts = database.get_transcripts(session_id=session_id)
    transcripts_metrics = []
    for transcript in transcripts:
        speaker_metrics = database.get_speaker_transcript_metrics(transcript_id=transcript.id)
        transcripts_metrics.append({'transcript' : transcript.json(),
                                    'speaker_metrics' : [speaker_metric.json() for speaker_metric in speaker_metrics]})
    return json_response(json.dumps(transcripts_metrics))

@api_routes.route('/api/v1/sessions/devices/<int:device_id>/speakers/<int:speaker_id>/transcripts/client', methods=['GET'])
# @wrappers.verify_login(public=True)
# @wrappers.verify_session_access
def speaker_id_transcripts_for_client(device_id, speaker_id, **kwargs):
    transcripts = database.get_transcripts(speaker_id=speaker_id)
    return json_response([transcript.json() for transcript in transcripts])

@api_routes.route('/api/v1/sessions/<int:session_id>/devices/<int:device_id>/speakers', methods=['GET'])
@wrappers.verify_login(public=True)
@wrappers.verify_session_access
def session_device_speakers(session_id, device_id, **kwargs):
    speakers = database.get_speakers(session_device_id=device_id)
    return json_response([speaker.json() for speaker in speakers])

@api_routes.route('/api/v1/sessions/<int:session_id>/devices/<int:device_id>/keywords', methods=['GET'])
@wrappers.verify_login(public=True)
@wrappers.verify_session_access
def session_device_keywords(session_id, device_id, **kwargs):
    keywords = database.get_keyword_usages(session_device_id=device_id)
    return json_response([keyword.json() for keyword in keywords])

@api_routes.route('/api/v1/sessions/<int:session_id>/devices/<int:session_device_id>', methods=['GET'])
@wrappers.verify_login(public=True)
@wrappers.verify_session_access
def session_device(session_id, session_device_id, processing_key, **kwargs):
        if session_device_id:
          session_device = database.get_session_devices(id=session_device_id)
        elif processing_key:
          session_device = database.get_session_devices(processing_key=processing_key)
        return json_response(session_device.json())

@api_routes.route('/api/v1/sessions/<int:session_id>/devices', methods=['GET'])
@wrappers.verify_login(public=True)
@wrappers.verify_session_access
def session_devices(session_id, **kwargs):
        devices = database.get_session_devices(session_id=session_id)
        return json_response([device.json() for device in devices])

@api_routes.route('/api/v1/help_button', methods=['POST'])
@wrappers.verify_login(allow_key=True)
def set_help_button(**kwargs):
    session_device_id = request.json.get('id', None)
    state = request.json.get('activated', False)
    if not session_device_id:
        return json_response({'message': 'Session device ID must be provided.'}, 400)

    session_device = database.get_session_devices(id=session_device_id)
    if session_device:
        if session_device.button_pressed != state:
            session_device.button_pressed = state
            database.save_changes()
            room_name = str(session_device.session_id)
            socketio.emit('device_update', json.dumps(session_device.json()), room=room_name, namespace="/session")
        return json_response()
    return json_response({'message': 'Session device not found.'}, 400)

@api_routes.route('/api/v1/sessions/<int:session_id>/passcode', methods=['POST'])
@wrappers.verify_login(public=True)
@wrappers.verify_session_access
def set_session_passcode(session_id, **kwargs):
    state = request.json.get('state', None)
    if not state in ['lock', 'unlock', 'refresh']:
        return json_response({'message': 'Invalid passcode state.'}, 400)
    session = database.get_sessions(id=session_id)
    if session:
        if state == 'lock':
            session.passcode = None
            database.save_changes()
        elif state in ['unlock', 'refresh']:
            database.generate_session_passcode(session.id)
        socketio_helper.update_session(session)
        return json_response(session.json())
    return json_response({'message': 'Session not found.'}, 404)

@api_routes.route('/api/v1/sessions/<int:session_id>/devices/<int:session_device_id>', methods=['DELETE'])
@wrappers.verify_login(public=True)
@wrappers.verify_session_access
def remove_device_from_session(session_id, session_device_id, **kwargs):
    delete = string_to_bool(request.args.get('delete', 'false'))
    session_handler.remove_session_device(session_device_id)
    if delete:
        database.delete_session_device(session_device_id)
        socketio_helper.remove_session_device(session_id, session_device_id)
    return json_response()

@api_routes.route('/api/v1/sessions/<int:session_id>/export',methods=['GET'])
@wrappers.verify_login(public=True)
@wrappers.verify_session_access
def export_session(session_id, **kwargs):
    si = io.StringIO()
    field_names = ['Device ID', 'Device Name', 'Start Time', 'Transcript', 'Keywords', 'Keywords Detected', 'Similarity', 'Analytic Thinking', 'Authenticity', 'Certainty', 'Clout', 'Emotional Tone', 'Direction', 'Word Count', 'Speaker Tag', 'Speaker ID', 'Topic ID']
    fwrite = csv.DictWriter(si, fieldnames = field_names)
    fwrite.writeheader()
    session_devices = database.get_session_devices(session_id=session_id)
    for session_device in session_devices:
        transcripts = database.get_transcripts(session_device_id=session_device.id)
        keywords = database.get_keyword_usages(session_device_id=session_device.id)
        for t in transcripts:
            transcript_keywords = [keyword for keyword in keywords if keyword.transcript_id == t.id]
            fwrite.writerow({'Device ID':session_device.id,
                'Device Name':session_device.name,
                'Start Time':str(timedelta(seconds=int(t.start_time))),
                'Transcript':t.transcript,
                'Keywords': ', '.join([keyword.keyword for keyword in transcript_keywords]),
                'Keywords Detected': ', '.join([keyword.word for keyword in transcript_keywords]),
                'Similarity': ', '.join([str(round((1-keyword.similarity)*100,3)) for keyword in transcript_keywords]),
                'Analytic Thinking': int(t.analytic_thinking_value),
                'Authenticity': int(t.authenticity_value),
                'Certainty': int(t.certainty_value),
                'Clout': int(t.clout_value),
                'Emotional Tone': int(t.emotional_tone_value),
                'Word Count': int(t.word_count),
                'Speaker Tag': t.speaker_tag,
                'Speaker ID': int(t.speaker_id),
                'Topic ID': int(t.topic_id)
                })

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=export.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@api_routes.route('/api/v1/sessions/getredissessionkey', methods=['POST'])
def get_device_key(**kwargs):
    content = request.get_json()
    redis_key = RedisSessions.get_device_key(content['auth_key'])
    if redis_key:
        return json_response({'redis_key': redis_key})
    else:
        return json_response({'message': "key cannot be authenticated"}, 400)

@api_routes.route('/api/v1/sessions/getredissessionconfig', methods=['POST'])
def get_session_config(**kwargs):
    content = request.get_json()
    redis_session = RedisSessions.get_session_config(content['session_key'])
    if redis_session:
        return json_response({'redis_session_key': redis_session})
    else:
        return json_response({'message': "Session key cannot be authenticated"}, 400)

@api_routes.route('/api/v1/session/addcartoonizedimage', methods=['POST'])
@wrappers.verify_local
def add_cartoonized_image(**kwargs):
    logging.info('Received cartoonized image ...')
    content = request.get_json()
    queue_key = '{0}_{1}_{2}'.format(content['source'],content['sessionid'],content['deviceid'])
    if queue_key in image_queue_dict.keys():
        image_queue_dict[queue_key].put(content)
    else:
        image_queue = queue.Queue()
        image_queue.put(content)
        image_queue_dict[queue_key] = image_queue
    return json_response()

@api_routes.route('/api/v1/sessions/<int:session_id>/devices/<int:device_id>/auth/<auth_id>/streamimages')
def stream_cartonized_images(session_id, device_id,auth_id, **kwargs):
    try:
        filePath  = os.path.dirname(os.path.abspath(__file__))
        os.chdir(filePath)
        os.chdir("../../video_processing/videorecordings")
        loading_img_Path = os.path.join(os.getcwd(),'loading_img')
        loading_frame = read_image(os.path.join(loading_img_Path,'loading.png'))
        queue_key = '{0}_{1}_{2}'.format(auth_id,session_id,device_id)
        return Response(gen(loading_frame,queue_key),
                        mimetype='multipart/x-mixed-replace; boundary=frame')
    except Exception as e:
        logging.error('Error occured while streaming cartoonized image: {0}'.format(e))


def gen(loading_frame,queue_key):
    start = False
    while True:
        if not start:
            if  queue_key in  image_queue_dict.keys():
                logging.info('qsize is {0}'.format(image_queue_dict[queue_key].qsize()))
                if image_queue_dict[queue_key].qsize() >= 1:
                    start = True
            yield (b'--frame\r\n'
                    b'Content-Type: image/png\r\n\r\n' + loading_frame + b'\r\n')

        elif not image_queue_dict[queue_key].empty():
            data = image_queue_dict[queue_key].get(block=False)
            yield (b'--frame\r\n'
            b'Content-Type: image/png\r\n\r\n' +  base64.b64decode(data['image']) + b'\r\n')

def read_image(filepath):
    return  open(filepath , 'rb').read()
