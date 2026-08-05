import database

def get_user_session_device_ids(session_name_pattern=None):
    """
    Get session_device IDs for filtering
    Can Filter by session name pattern to identify sessions
    """
    sessions = database.get_sessions()
    
    user_session_device_ids = []
    
    for session in sessions:
        # Filter by pattern if provided
        if session_name_pattern and session_name_pattern not in (session.name or ""):
            continue
            
        # Get devices for this session
        devices = database.get_session_devices(session_id=session.id)
        for device in devices:
            user_session_device_ids.append(device.id)
    
    return user_session_device_ids


def get_my_recent_sessions():
    """Get recent session_device IDs based on known patterns"""
    
    my_known_session_ids = [159, 158] 
    
    my_device_ids = []
    for sid in my_known_session_ids:
        devices = database.get_session_devices(session_id=sid)
        for device in devices:
            my_device_ids.append(device.id)
    
    return my_device_ids