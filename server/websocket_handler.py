from flask_socketio import SocketIO, emit, join_room, leave_room
import logging

def init_concept_websocket(socketio):
    """Initialize WebSocket handlers for concept updates"""
    
    @socketio.on('join_concept_session')
    def handle_join_concept_session(data):
        """Client joins a concept session room"""
        session_device_id = data.get('session_device_id')
        if session_device_id:
            room = f'concepts_{session_device_id}'
            join_room(room)
            logging.info(f"Client joined concept room: {room}")
            emit('joined', {'room': room})
    
    @socketio.on('leave_concept_session')
    def handle_leave_concept_session(data):
        """Client leaves a concept session room"""
        session_device_id = data.get('session_device_id')
        if session_device_id:
            room = f'concepts_{session_device_id}'
            leave_room(room)
            logging.info(f"Client left concept room: {room}")
    
    return socketio

def broadcast_concept_update(socketio, session_device_id, concept_update):
    """Broadcast concept updates to all clients in the session room"""
    room = f'concepts_{session_device_id}'
    
    # Emit the update to all clients in the room
    socketio.emit('concept_update', {
        'session_device_id': session_device_id,
        'nodes': concept_update.get('nodes', []),
        'edges': concept_update.get('edges', []),
        'discourse_type': concept_update.get('discourse_type', 'exploratory'),
        'timestamp': concept_update.get('timestamp')
    }, room=room)
    
    logging.info(f"Broadcasted concept update to room {room}: {len(concept_update.get('nodes', []))} nodes")
