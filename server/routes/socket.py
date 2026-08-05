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
    user = session.get('user', None)
    logging.info(f"Socket connect: user={user}")
    if user:
        return True
    else:
        logging.warning("Socket connect: No user in session, disconnecting")
        disconnect()
        return False

@socketio.on('join_room', namespace='/session')
def join_session(message):
    room = message.get('room', None)
    user = session.get('user', None)
    logging.info(f"Socket join_room: room={room}, user={user}")
    if room and user:
        session_model = database.get_sessions(id=room, owner_id=user['id'])
        logging.info(f"Socket join_room: session_model={session_model}")
        if session_model:
            try:
                join_room(str(room))
                # Emit room_joined FIRST so frontend sets initialized=true before transcripts arrive
                emit('room_joined', json.dumps({'success': True}))
                logging.info(f"Socket join_room: Joined room {room}, now fetching transcripts")
                transcripts = database.get_transcripts(session_id=room)
                logging.info(f"Socket join_room: Found {len(transcripts)} transcripts for session {room}")
                page_size = 1000
                transcript_speaker_metrics = []
                for transcript in transcripts:
                    if len(transcript_speaker_metrics) == page_size:
                        logging.info(f"Socket join_room: Emitting batch of {len(transcript_speaker_metrics)} transcript_metrics_digest")
                        emit('transcript_metrics_digest', json.dumps(transcript_speaker_metrics))
                        transcript_speaker_metrics = []
                    speaker_metrics = database.get_speaker_transcript_metrics(transcript_id=transcript.id)
                    transcript_speaker_metrics.append({'transcript' : transcript.json(),
                                                       'speaker_metrics' : [speaker_metric.json() for speaker_metric in speaker_metrics]})
                logging.info(f"Socket join_room: Emitting final batch of {len(transcript_speaker_metrics)} transcript_metrics_digest")
                emit('transcript_metrics_digest', json.dumps(transcript_speaker_metrics))
                logging.info(f"Socket join_room: Successfully emitted all transcripts for session {room}")
            except Exception as e:
                logging.error(f"Socket join_room: ERROR during transcript loading: {e}", exc_info=True)
                emit('room_joined', json.dumps({'success': False}))
        else:
            # Session not found for this user
            emit('room_joined', json.dumps({'success': False}))
    else:
        # Missing room or user
        emit('room_joined', json.dumps({'success': False}))
            

@socketio.on('leave_room', namespace='/session')
def leave_session(message):
    room = message.get('room', None)
    if room:
        leave_room(room)
    emit('room_left', json.dumps({'success': True if room else False}))
