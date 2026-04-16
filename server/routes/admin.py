import email

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
import config as cf
from redis_helper import RedisLogin
from utility import json_response, sanitize, sanitize_int_value

api_routes = Blueprint('admin', __name__)

@api_routes.route('/api/v1/admin/users', methods=['GET'])
@wrappers.verify_login(roles=['admin', 'super'])
def get_users(user, **kwargs):
    roles = ['user', 'admin']
    if user['role'] == 'super':
        roles.append('super')
    return json_response([user.json() for user in database.get_users(roles=roles)])

@api_routes.route('/api/v1/admin/students', methods=['GET'])
@wrappers.verify_login(roles=['admin', 'super'])
def get_students(**kwargs):
    students = database.get_students()
    if students:
        return json_response([student.json() for student in students])
    else:
        return json_response({'message': 'No Records found.'}, 400)

@api_routes.route('/api/v1/admin/raters', methods=['GET'])
@wrappers.verify_login(roles=['admin', 'super'])
def get_raters(**kwargs):
    raters = database.get_raters()
    if raters:
        return json_response([rater.json() for rater in raters])
    else:
        return json_response({'message': 'No Records found.'}, 400)        

@api_routes.route('/api/v1/admin/raters/<string:rater_id>', methods=['GET'])
def get_rater_by_id(rater_id, **kwargs):
    raters = database.get_raters(raterid=rater_id,completed=0)
    if raters:
        return json_response([rater.json() for rater in raters])
    else:
        return json_response({'message': 'No Records found.'}, 400)
    
        
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
    
@api_routes.route('/api/v1/admin/raters', methods=['POST'])
@wrappers.verify_login(roles=['admin', 'super'])
def add_rater(**kwargs):
    content = request.json
    sessionid = sanitize_int_value(content.get('sessionid', None))
    sessiondeviceid = sanitize(content.get('sessiondeviceid', None))
    speakerid = sanitize(content.get('speakerid', None))
    speakertag = sanitize(content.get('speakertag', None))
    raterid = sanitize(content.get('raterid', None))
    type = sanitize(content.get('type', None))
    evaluationcategory = sanitize(content.get('evaluationcategory',None))
    if not sessionid:
        return json_response({'message': 'Must provide session ID as an integer.'}, 400)
    if not sessiondeviceid:
        return json_response({'message': 'Must provide session device ID as an integer.'}, 400)
    if not speakerid:
        return json_response({'message': 'Must provide speaker ID as an integer.'}, 400)
    if not speakertag:
        return json_response({'message': 'Must provide speaker tag as a string.'}, 400)
    if not raterid:
        return json_response({'message': 'Must provide rater ID as a string.'}, 400)
    if not type:
        return json_response({'message': 'Must provide type as a string.'}, 400)
    if not evaluationcategory:
        return json_response({'message': 'Must provide evaluation category as a string.'}, 400)
    success, rater = database.add_rater(sessionid,sessiondeviceid,speakerid,speakertag,raterid,type,evaluationcategory)
    if success:
        return json_response({'rater': rater.json()})
    else:
        return json_response({'message': rater}, 400)    

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
    
@api_routes.route('/api/v1/admin/students/<int:student_id>', methods=['DELETE'])
@wrappers.verify_login(roles=['admin', 'super'])
def delete_student(student_id, **kwargs):
    student = database.delete_student(student_id)
    if student is not None:
        biometric_file_path = os.path.join(cf.root_dir(), "chemistry-dashboard/audio_processing/audiovideobiometrics","{0}.webm".format(student.username))
        try:
            if os.path.isfile(biometric_file_path):
                os.remove(biometric_file_path)        
        except Exception as e:
            logging.info('Unable to delete biometric file: {0}'.format(e)) 
        return json_response()
    else:
        return json_response({'User not found.'}, 400)
    
@api_routes.route('/api/v1/admin/raters/<int:id>', methods=['DELETE'])
@wrappers.verify_login(roles=['admin', 'super'])
def delete_rater(id, **kwargs):
    rater = database.delete_rater(id)
    if rater is not None:
        return json_response()
    else:
        return json_response({'Rater not found.'}, 400)


@api_routes.route('/api/v1/admin/devicedata/sessiondeviceid/<int:session_device_id>/data_type/<string:data_type>', methods=['DELETE'])
@wrappers.verify_login(roles=['admin', 'super'])
def delete_session_device_data(session_device_id,data_type, **kwargs):
    if data_type == 'transcriptmetric':
        trscript = database.delete_device_transcriptsV2(session_device_id)
    elif data_type == 'videometric':
        vidmetric = database.delete_speaker_video_metrics_by_sessionDeviceID(session_device_id)
    if trscript is not None or vidmetric is not None:
        return json_response()
    else:
        return json_response({'Data not found.'}, 400)

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
