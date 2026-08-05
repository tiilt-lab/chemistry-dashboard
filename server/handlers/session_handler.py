import os
import logging
import database
import requests
import socketio_helper
from datetime import datetime
from app import socketio, scheduler
import json
from device_websockets import ConnectionManager
from redis_helper import RedisSessions
from seven_cs_service import analyze_session_seven_cs
from concept_generation_service import generate_concepts_for_session_device
from discussion_pulse_service import generate_next_pulse

# Track active pulse generation jobs
_active_pulse_jobs = set()

def start_pulse_generation(session_device_id):
    """Start recurring pulse generation for a session device (every 50 seconds)"""
    job_id = f'pulse_generation_{session_device_id}'

    if job_id in _active_pulse_jobs:
        logging.info(f"Pulse generation already active for session_device {session_device_id}")
        return

    try:
        scheduler.add_job(
            func=generate_next_pulse,
            trigger='interval',
            seconds=45,  # Generate pulse every 45 seconds
            args=[session_device_id],
            id=job_id,
            replace_existing=True,
            misfire_grace_time=30,
            next_run_time=datetime.now()  # Run immediately on first call
        )
        _active_pulse_jobs.add(job_id)
        logging.info(f"Started pulse generation for session_device {session_device_id}")
    except Exception as e:
        logging.error(f"Failed to start pulse generation for session_device {session_device_id}: {e}")

def stop_pulse_generation(session_device_id):
    """Stop recurring pulse generation for a session device"""
    job_id = f'pulse_generation_{session_device_id}'

    try:
        scheduler.remove_job(job_id)
        _active_pulse_jobs.discard(job_id)
        logging.info(f"Stopped pulse generation for session_device {session_device_id}")
    except Exception as e:
        logging.debug(f"Pulse generation job not found for session_device {session_device_id}: {e}")

def create_session(user_id, name, devices, keyword_list_id, topic_model_id, byod, features, doa, folder):
    # keyword_list_id and topic_model_id are deprecated but kept for API compatibility
    session, _ = database.create_session(user_id, None, None, name, folder)
    if byod:
        session = database.generate_session_passcode(session.id)
    config = {
        'server_start': str(session.creation_date),
        'transcribe': True,
        'features': features,
        'keywords': [],  # Keywords feature deprecated
        'doa': doa,
        'topic_model': None,  # Topic model feature deprecated
        'owner': user_id
    }
    RedisSessions.create_session(session.id, config)
    if devices:
        for device in devices:
            result = pod_join_session(session.id, device)
    return session

def end_session(session_id):
    logging.info(f"END_SESSION called for session {session_id}")
    session = database.get_sessions(id=session_id)
    if not session:
        return False, 'Session does not exist.'
    if session.end_date != None:
        return False, 'Session is already closed.'
    session.end_date = datetime.utcnow()
    database.save_changes()
    RedisSessions.delete_session(session.id)
    socketio_helper.update_session(session)
    socketio.emit('session_update', json.dumps(session.json()), room=str(session.id), namespace="/session")
    session_devices = database.get_session_devices(session_id=session_id)

    # Force index any pending chunks for RAG before session ends
    try:
        from rag_auto_indexer import get_auto_indexer
        auto_indexer = get_auto_indexer()
        if auto_indexer:
            auto_indexer.force_index_all_pending()
            logging.info(f"Flushed pending chunks to RAG for session {session_id}")
    except Exception as e:
        logging.error(f"Failed to flush pending chunks to RAG: {e}")
        # Don't fail session end if RAG indexing fails

    # Note: Concept clustering is now handled by concept_generation_service
    # after post-discussion concept map generation completes

    # Schedule 7C analysis for each session device ===
    try:
        for session_device in session_devices:
            # Schedule as background job to avoid blocking the response
            scheduler.add_job(
                func=analyze_session_seven_cs,
                trigger='date',  # Run once, immediately
                args=[session_device.id],
                id=f'seven_cs_analysis_{session_device.id}',  # Unique job ID
                replace_existing=True,  # Replace if job already exists
                misfire_grace_time=30  # Allow 30 seconds grace time
            )
            logging.info(f"Scheduled 7C analysis for session_device {session_device.id}")
    except Exception as e:
        logging.error(f"Failed to schedule 7C analysis: {e}")
        # Don't fail the session end if 7C analysis fails

    # Schedule post-discussion concept map generation for each session device ===
    try:
        for session_device in session_devices:
            scheduler.add_job(
                func=generate_concepts_for_session_device,
                trigger='date',  # Run once, immediately
                args=[session_device.id],
                id=f'concept_generation_{session_device.id}',
                replace_existing=True,
                misfire_grace_time=60  # Allow 60 seconds grace time (concept generation takes longer)
            )
            logging.info(f"Scheduled concept map generation for session_device {session_device.id}")
    except Exception as e:
        logging.error(f"Failed to schedule concept generation: {e}")
        # Don't fail the session end if concept generation fails

    # Stop pulse generation and update session_devices
    for session_device in session_devices:
        stop_pulse_generation(session_device.id)
        session_device.button_pressed = False
        session_device.removed = True
        RedisSessions.delete_device_key(session_device.processing_key)
    database.save_changes()

    # Ping pod devices to stop session
    devices_to_ping = database.get_devices(ids=[session_device.device_id for session_device in session_devices if session_device.device_id != None])
    for device in devices_to_ping:
        try:
            sent = ConnectionManager.instance.send_command(device.id, {'cmd': 'end'})
        except Exception as e:
            logging.critical('Session End: Pod ' + str(device.id) + ' was unreachable or failed to respond.')
    return True, session

def byod_join_session(name, passcode, collaborators):
    success, session_device, speakers = database.create_byod_session_device(passcode, name, collaborators)
    if success:
        session = database.get_sessions(id=session_device.session_id)
        RedisSessions.create_device_key(session_device.processing_key, session.id)
        socketio_helper.update_session_device(session_device)
        # Start Discussion Pulse auto-generation for this device
        start_pulse_generation(session_device.id)
        return True, {'session': session.json(), 'session_device': session_device.json(), 'key': session_device.processing_key, 'speakers': [speaker.json() for speaker in speakers]}
    else:
        return False, session_device

def pod_join_session(session_id, pod_id):
    success, session_device = database.create_pod_session_device(session_id, pod_id)
    if success:
        # Add pod redis key and update session.
        RedisSessions.create_device_key(session_device.processing_key, session_device.session_id)
        socketio_helper.update_session_device(session_device)

        # Send message to pod to connect.
        pod = database.get_devices(id=pod_id)
        if pod:
            try:
                sent = ConnectionManager.instance.send_command(pod.id, {'cmd': 'start', 'key': session_device.processing_key})
                if not sent:
                    logging.critical('pod_join_session: Pod {0} was not able to connect to the Audio Processing Service.  Is it in another session?'.format(pod.pod_id))
                sent = ConnectionManager.instance.send_command(pod.id, {'cmd': 'color', 'color': '0xFF0000'})
            except:
                logging.critical('pod_join_session: Pod {0} was unreachable or failed to respond.'.format(pod.id))

        # Start Discussion Pulse auto-generation for this device
        start_pulse_generation(session_device.id)

        return True, {'session_device': session_device.json()}
    else:
        return False, {'message': session_device}

def remove_session_device(session_device_id):
    session_device = database.get_session_devices(id=session_device_id)
    if session_device:
        stop_pulse_generation(session_device.id)
        RedisSessions.delete_device_key(session_device.processing_key)
        session_device.removed = True
        database.save_changes()
        if session_device.device_id:
            try:
                ConnectionManager.instance.send_command(session_device.device_id, {'cmd': 'end'})
            except Exception as e:
                logging.critical('Session End: Pod ' + str(session_device.device_id) + ' was unreachable or failed to respond.')
