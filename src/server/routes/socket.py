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
            videoMetrics = database.get_speaker_video_metrics(session_id=room)
            page_size = 1000

            # Fetch every speaker-transcript metric for the session in one query
            # and group by transcript id, instead of one query per transcript.
            metrics_by_transcript = {}
            for metric in database.get_speaker_transcript_metrics(session_id=room):
                metrics_by_transcript.setdefault(metric.transcript_id, []).append(metric.json())

            transcript_speaker_metrics = []
            speaker_video_metrics = []
            for transcript in transcripts:
                if len(transcript_speaker_metrics) == page_size:
                    emit('transcript_metrics_digest', json.dumps(transcript_speaker_metrics))
                    transcript_speaker_metrics = []
                transcript_speaker_metrics.append({'transcript' : transcript.json(),
                                                   'speaker_metrics' : metrics_by_transcript.get(transcript.id, [])})
            emit('transcript_metrics_digest', json.dumps(transcript_speaker_metrics))


            for videometric in videoMetrics:
                if len(speaker_video_metrics) == page_size:
                    emit('video_metrics_digest', json.dumps(speaker_video_metrics))
                    speaker_video_metrics = [] 
                speaker_video_metrics.append({'speaker_video_metrics' : videometric.json()})
            emit('video_metrics_digest', json.dumps(speaker_video_metrics))

    emit('room_joined', json.dumps({'success': True if room else False}))
            

@socketio.on('leave_room', namespace='/session')
def leave_session(message):
    room = message.get('room', None)
    if room:
        leave_room(room)
    emit('room_left', json.dumps({'success': True if room else False}))
