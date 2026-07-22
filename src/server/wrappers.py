from flask import request, session
from functools import wraps
import logging
import database
import utility
from utility import json_response

def verify_login(roles=None, allow_key=False, public=False):
    def verify_login_decorator(f):
        @wraps(f)
        def verify_function(*args, **kwargs):
            # Allow access for sessions.
            if session.get('user', None):
                user = session.get('user', None)
                kwargs['user'] = user
                if (not roles) or (roles and user.get('role', '') in roles):
                    return f(*args, **kwargs)
                else:
                    return json_response({'message': 'You are not authorized to use this endpoint.'}, 401)

            # Allow devices communicating with processing keys.
            if allow_key and request.headers.get('X-Processing-Key', None):
                processing_key = request.headers.get('X-Processing-Key', None)
                session_device = database.get_session_devices(processing_key=processing_key)
                if session_device:
                    return f(*args, **kwargs)

            # Allow public API access with client keys.
            if public and request.headers.get('X-Client-Id', None):
                client_id = request.headers.get('X-Client-Id', None)
                client_token = request.headers.get('X-Client-Token', None)
                if client_id and client_token:
                    api_client = database.get_api_clients(client_id=client_id)
                    if api_client and api_client.verify_token(client_token):
                        user = database.get_users(id=api_client.user_id)
                        kwargs['user'] = user.json()
                        if (not roles) or (roles and user.get('role', '') in roles):
                            return f(*args, **kwargs)
                        else:
                            return json_response({'message': 'You are not authorized to use this endpoint.'}, 401)
            return json_response({'message': 'You are not authorized to use this endpoint.'}, 401)

        return verify_function
    return verify_login_decorator

def verify_local(f):
    @wraps(f)
    def verify_function(*args, **kwargs):
        ip = utility.get_client_ip(request)
        if ip in ['localhost', '127.0.0.1']:
            return f(*args, **kwargs)
        else:
            return json_response({'message': 'Endpoint authorized for local use only.'}, 403)

    return verify_function

# Cross-account session reach, by role:
#
#   user   own sessions only, read and write
#   admin  own sessions read and write, everyone else's read-only
#   super  every session, read and write
#
# _session_for() resolves the session a request names and returns None when the
# caller may not touch it at that level, so both guards below (and the listing
# in session.get_sessions) share one definition of "can reach".
def _session_for(session_id, user, write):
    role = user.get('role', 'user')
    if role == 'super' or (role == 'admin' and not write):
        return database.get_sessions(id=session_id)
    return database.get_sessions(id=session_id, owner_id=user['id'])

# Read guard: attach the session for endpoints that only report on it.
def verify_session_read_access(f):
    @wraps(f)
    def verify_function(*args, **kwargs):
        session_id = kwargs['session_id']
        user = kwargs['user']
        session_model = _session_for(session_id, user, write=False)
        if session_model:
            kwargs['session'] = session_model
            return f(*args, **kwargs)
        else:
            return json_response({'message': 'Does not exist.'}, 404)

    return verify_function

# Write guard: mutating a session (rename, delete, stop, re-run analysis)
# stays with its owner, or a super.
def verify_session_access(f):
    @wraps(f)
    def verify_function(*args, **kwargs):
        session_id = kwargs['session_id']
        user = kwargs['user']
        session_model = _session_for(session_id, user, write=True)
        if session_model:
            kwargs['session'] = session_model
            return f(*args, **kwargs)
        else:
            return json_response({'message': 'Does not exist.'}, 404)

    return verify_function

# Read access to one pod's data (transcripts, metrics) for endpoints that name
# a session device rather than a session. Two callers are legitimate:
#
#   - a logged-in user with read access to the owning session, and
#   - the BYOD client, which holds that device's processing key from its join
#     response and sends it as X-Processing-Key.
#
# The key is checked against the device named in the URL, so one pod's key
# cannot read another pod's transcripts. Without either, the device id alone
# proves nothing: ids are sequential, so an unguarded endpoint hands any
# passer-by every group's speech by counting upwards.
def verify_device_read_access(f):
    @wraps(f)
    def verify_function(*args, **kwargs):
        device_id = kwargs.get('device_id', kwargs.get('session_device_id'))
        session_device = database.get_session_devices(id=device_id)
        if not session_device:
            return json_response({'message': 'Does not exist.'}, 404)

        processing_key = request.headers.get('X-Processing-Key', None)
        if processing_key and processing_key == session_device.processing_key:
            kwargs['session_device'] = session_device
            return f(*args, **kwargs)

        user = kwargs.get('user', session.get('user', None))
        if user and _session_for(session_device.session_id, user, write=False):
            kwargs['session_device'] = session_device
            return f(*args, **kwargs)

        return json_response({'message': 'Does not exist.'}, 404)

    return verify_function

def verify_session_access_json(f):
    @wraps(f)
    def verify_function(*args, **kwargs):
        session_id = request.json.get('sessionId', None)
        user = kwargs['user']
        if not session_id or not user:
            return json_response({'message': 'You are not authorized to use this endpoint.'}, 403)
        session_model = _session_for(session_id, user, write=True)
        if session_model:
            kwargs['session'] = session_model
            return f(*args, **kwargs)
        else:
            return json_response({'message': 'Does not exist.'}, 404)

    return verify_function

def verify_folder_access(f):
    @wraps(f)
    def verify_function(*args, **kwargs):
        folder_id = kwargs['folder_id']
        user = kwargs['user']
        folder_model = database.get_folders(id=folder_id, owner_id=user['id'])
        if folder_model:
            kwargs['folder'] = folder_model
            return f(*args, **kwargs)
        else:
            return json_response({'message': 'Does not exist.'}, 404)

    return verify_function


def verify_keyword_list_access(f):
    @wraps(f)
    def verify_function(*args, **kwargs):
        keyword_list_id = kwargs['keyword_list_id']
        user = kwargs['user']
        keyword_list_model = database.get_keyword_lists(id=keyword_list_id, owner_id=user['id'])
        if keyword_list_model:
            kwargs['keyword_list'] = keyword_list_model
            return f(*args, **kwargs)
        else:
            return json_response({'message': 'Keyword list not found.'}, 403)

    return verify_function

def verify_topic_model_access(f):
    @wraps(f)
    def verify_function(*args, **kwargs):
        topic_model_id= kwargs['topic_model_id']
        user = kwargs['user']
        topic_model_model = database.get_topic_models(id=topic_model_id)
        if topic_model_model:
            kwargs['topic_model'] = topic_model_model
            return f(*args, **kwargs)
        else:
            return json_response({'message': 'Topic model not found.'}, 403)

    return verify_function

# Expects 'user_id' to exist in keyword args.
def verify_user_authority(f):
    @wraps(f)
    def verify_function(*args, **kwargs):
        ranks = ['user', 'admin', 'super']
        user = kwargs['user']
        # The recipient is the target of the operation, not the caller. Looking
        # up the caller here made the rank comparison compare a role to itself,
        # so the check always passed and an admin could reset, delete, or demote
        # a super account.
        recipient_user = database.get_users(id=kwargs['user_id'])
        if recipient_user:
            recipient_role = recipient_user.role
            acting_role = user['role']
            if ranks.index(recipient_role) <= ranks.index(acting_role):
                return f(*args, **kwargs)
        # A caller who may not act on this user is told the same thing as one
        # naming an id that does not exist. Distinguishing the two let an admin
        # probe ids and learn which ones hold super accounts, since the listing
        # in admin.get_users hides those rows from them.
        return json_response({'message': 'User does not exist.'}, 404)

    return verify_function

# Expects 'user_id' and 'user' to exist in keyword args.
def avoid_self(f):
    @wraps(f)
    def verify_function(*args, **kwargs):
        user_id = kwargs['user_id']
        user = kwargs['user']
        if user_id != user['id']:
            return f(*args, **kwargs)
        else:
            return json_response({'message': 'You can not perform this operation on your account.'}, 403)

    return verify_function

# Expects 'user_id' and 'user' to exist in keyword args.
def verify_valid_role(f):
    @wraps(f)
    def verify_function(*args, **kwargs):
        ranks = ['user', 'admin']
        user_role = kwargs['user']['role']
        if user_role == 'super':
            ranks.append('super')
        role = request.json.get('role', None)
        if role in ranks:
            return f(*args, **kwargs)
        else:
            return json_response({'message': 'Invalid role.'}, 400)

    return verify_function

