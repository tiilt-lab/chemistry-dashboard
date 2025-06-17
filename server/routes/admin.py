from flask import Blueprint, Response, request, abort, session, send_file
from tables.user import User
from app import base_dir
import json
import logging
import database
import wrappers
from device_websockets import ConnectionManager
from io import BytesIO
import base64
import os
from redis_helper import RedisLogin
from utility import json_response, sanitize

api_routes = Blueprint('admin', __name__)

@api_routes.route('/api/v1/admin/users', methods=['GET'])
@wrappers.verify_login(roles=['admin', 'super'])
def get_users(user, **kwargs):
    roles = ['user', 'admin']
    if user['role'] == 'super':
        roles.append('super')
    return json_response([user.json() for user in database.get_users(roles=roles)])

@api_routes.route('/api/v1/admin/users', methods=['POST'])
@wrappers.verify_login(roles=['admin', 'super'])
@wrappers.verify_valid_role
def add_user(**kwargs):
    content = request.json
    email = content.get('email', None)
    role = sanitize(content.get('role', None))
    valid, message = User.verify_fields(email=email, role=role)
    if not email:
        return json_response({'message': 'Must provide email.'}, 400)
    if not role:
        return json_response({'message': 'Must provide role.'}, 400)
    if not valid:
        return json_response({'message': message}, 400)
    success, user = database.add_user(email, role)
    if success:
        new_password = user.reset_password(16)
        database.save_changes()
        return json_response({'user': user.json(), 'password': new_password})
    else:
        return json_response({'message': user}, 400)

@api_routes.route('/api/v1/admin/users/<int:user_id>', methods=['DELETE'])
@wrappers.verify_login(roles=['admin', 'super'])
@wrappers.avoid_self
@wrappers.verify_user_authority
def delete_user(user_id, **kwargs):
    success = database.delete_user(user_id)
    if success:
        return json_response()
    else:
        return json_response({'User not found.'}, 400)

@api_routes.route('/api/v1/admin/users/<int:user_id>/lock', methods=['POST'])
@wrappers.verify_login(roles=['admin', 'super'])
@wrappers.avoid_self
@wrappers.verify_user_authority
def lock_user(user_id, **kwargs):
    user = database.update_user(user_id, {'locked': True})
    if user:
        return json_response(user.json())
    else:
        return json_response({'message': 'User not found.'}, 400)

@api_routes.route('/api/v1/admin/users/<int:user_id>/unlock', methods=['POST'])
@wrappers.verify_login(roles=['admin', 'super'])
@wrappers.avoid_self
@wrappers.verify_user_authority
def unlock_user(user_id, **kwargs):
    user = database.update_user(user_id, {'locked': False})
    if user:
        RedisLogin.unlock_login(user.email)
        return json_response(user.json())
    else:
        return json_response({'message': 'User not found.'}, 400)

@api_routes.route('/api/v1/admin/users/<int:user_id>/role', methods=['POST'])
@wrappers.verify_login(roles=['admin', 'super'])
@wrappers.avoid_self
@wrappers.verify_user_authority
@wrappers.verify_valid_role
def change_user_role(user_id, **kwargs):
    role = sanitize(request.get_json().get('role', None))
    valid, message = User.verify_fields(role=role)
    if not valid:
        return json_response({'message': message}, 400)
    user = database.update_user(user_id, {'role': role})
    if user:
        return json_response(user.json())
    else:
        return json_response({'message': 'User not found.'}, 400)

@api_routes.route('/api/v1/admin/users/<int:user_id>/reset', methods=['POST'])
@wrappers.verify_login(roles=['admin', 'super'])
@wrappers.avoid_self
@wrappers.verify_user_authority
def reset_password(user_id, **kwargs):
    user = database.get_users(id=user_id)
    if user:
        new_password = user.reset_password(16)
        database.save_changes()
        return json_response({'password': new_password})
    else:
        return json_response({'message': 'User not found'}, 400)

@api_routes.route('/api/v1/admin/users/<int:user_id>/api', methods=['POST'])
@wrappers.verify_login(roles=['super'])
@wrappers.avoid_self
@wrappers.verify_user_authority
def allow_api_access(user_id, **kwargs):
    user = database.get_users(id=user_id)
    if user:
        api_client, client_secret = database.create_api_client(user_id)
        return json_response({'api_client': api_client.json(), 'client_secret': client_secret})
    else:
        return json_response({'message': 'User not found'}, 400)

@api_routes.route('/api/v1/admin/users/<int:user_id>/api', methods=['DELETE'])
@wrappers.verify_login(roles=['super'], public=True)
@wrappers.avoid_self
@wrappers.verify_user_authority
def revoke_api_access(user_id, **kwargs):
    user = database.get_users(id=user_id)
    if user:
        database.delete_api_client(user_id=user_id)
        return json_response({'success': True})
    else:
        return json_response({'message': 'User not found'}, 400)

@api_routes.route('/api/v1/admin/server/logs', methods=['GET'])
@wrappers.verify_login(roles=['super'])
def get_server_logs(**kwargs):
    log_type = sanitize(request.args.get('log_type', 'dcs'))
    if log_type in ['dcs', 'aps']:
        log_path = os.path.join(base_dir, 'discussion_capture_server.log')
        if log_type == 'aps':
            log_path = os.path.join(base_dir, '../audio_processing/audio_processing_service.log')
        log_data = None
        with open(log_path, 'r') as f:
            log_data = f.read()
        mem = BytesIO()
        mem.write(log_data.encode('utf-8'))
        mem.seek(0)
        return json_response({
            'type': log_type,
            'data': 'data:application/log;base64,' + base64.b64encode(mem.getvalue()).decode("utf-8")
        })
    return json_response({'message': 'Log type does not exist.'}, 400)

@api_routes.route('/api/v1/admin/devices/<int:device_id>/logs', methods=['GET'])
@wrappers.verify_login(roles=['super'])
def get_device_logs(device_id, **kwargs):
    device = database.get_devices(id=device_id, connected=True, is_pod=True)
    if device:
        success, data = ConnectionManager.instance.send_command_and_wait(device_id, {'cmd': 'logs'})
        if success:
            mem = BytesIO()
            mem.write(data['logs'].encode('utf-8'))
            mem.seek(0)
            return json_response({
                'data': 'data:application/log;base64,' + base64.b64encode(mem.getvalue()).decode("utf-8")
            })
    return json_response({'message': 'Device does not exist or did not respond.'}, 400)

@api_routes.route('/api/v1/admin/server/logs', methods=['DELETE'])
@wrappers.verify_login(roles=['super'])
def delete_server_logs(**kwargs):
    log_type = sanitize(request.args.get('log_type', 'dcs'))
    if log_type in ['dcs', 'aps']:
        log_path = os.path.join(base_dir, 'discussion_capture_server.log')
        if log_type == 'aps':
            log_path = os.path.join(base_dir, '../audio_processing/audio_processing_service.log')
        open(log_path, 'w').close()
        return json_response({})
    return json_response({'message': 'Log type does not exist.'}, 400)

@api_routes.route('/api/v1/admin/devices/<int:device_id>/logs', methods=['DELETE'])
@wrappers.verify_login(roles=['super'])
def delete_device_logs(device_id, **kwargs):
    device = database.get_devices(id=device_id, connected=True, is_pod=True)
    if device:
        success, data = ConnectionManager.instance.send_command_and_wait(device_id, {'cmd': 'clear_logs'})
        if success:
            return json_response()
    return json_response({'message': 'Device does not exist or did not respond.'}, 400)
