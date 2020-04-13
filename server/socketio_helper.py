import json
from app import socketio

def update_session_device(session_device):
    socketio.emit('device_update', json.dumps(session_device.json()), room=str(session_device.session_id), namespace="/session")

def remove_session_device(session_id, session_device_id):
    socketio.emit('device_removed', json.dumps({'id': session_device_id}), room=str(session_id), namespace="/session")

def update_session(session):
    socketio.emit('session_update', json.dumps(session.json()), room=str(session.id), namespace="/session")