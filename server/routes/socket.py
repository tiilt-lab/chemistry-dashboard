from flask import Blueprint, Response, jsonify, request, abort, session
from app import socketio
from flask_socketio import join_room, leave_room, send, emit, disconnect
import logging
import database
import json

# ------------------------------
# /session
# ------------------------------
@socketio.on('connect', namespace='/session')
def connect_handler():
    if session.get('user', None):
        return True
    else:
        disconnect()
        return False

@socketio.on('join_room', namespace='/session')
def join_session(message):
    room = message.get('room', None)
    user = session.get('user', None)
    if room and user:
        session_model = database.get_sessions(id=room, owner_id=user['id'])
        if session_model:
            join_room(str(room))
            #logging.info(str(room))
            #logging.info(str(user))
            #logging.info(database.get_transcripts(session_id=room))
            transcripts = database.get_transcripts(session_id=room)
            page_size = 1000
            transcript_speaker_metrics = []
            for transcript in transcripts:
                if len(transcript_speaker_metrics) == page_size:
                    emit('transcript_metrics_digest', json.dumps(transcript_speaker_metrics))
                    transcript_speaker_metrics = [] 
                speaker_metrics = database.get_speaker_transcript_metrics(transcript_id=transcript.id)
                transcript_speaker_metrics.append({'transcript' : transcript.json(),
                                                   'speaker_metrics' : [speaker_metric.json() for speaker_metric in speaker_metrics]})
            emit('transcript_metrics_digest', json.dumps(transcript_speaker_metrics))
    emit('room_joined', json.dumps({'success': True if room else False}))
            

@socketio.on('leave_room', namespace='/session')
def leave_session(message):
    room = message.get('room', None)
    if room:
        leave_room(room)
    emit('room_left', json.dumps({'success': True if room else False}))
