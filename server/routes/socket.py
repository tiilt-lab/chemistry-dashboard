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
            emit('transcript_digest', json.dumps([transcript.json() for transcript in database.get_transcripts(session_id=room)]))
            emit('room_joined', json.dumps({'success': True if room else False}))

@socketio.on('leave_room', namespace='/session')
def leave_session(message):
    room = message.get('room', None)
    if room:
        leave_room(room)
    emit('room_left', json.dumps({'success': True if room else False}))
