from flask import Blueprint, Response, request, abort, session
from utility import json_response
from datetime import datetime
from app import limiter
import json
import logging
import database
import wrappers
import utility
from redis_helper import RedisLogin

api_routes = Blueprint('auth', __name__)

def get_request_username():
    content = request.json
    username = content.get('email', None)
    return username

def get_request_client_id():
    return request.headers.get('X-Client-Id', None)

@api_routes.route('/api/v1/login', methods=['POST'])
@limiter.limit("5 per 5 second", get_request_username)
def login():
    content = request.json
    ip = utility.get_client_ip(request)
    email = content.get('email', None)
    password = content.get('password', None)
    success = False
    message = ''
    user = None
    if not email or not password:
        message = 'Please provide both an email and password.'
    elif not RedisLogin.can_login(email, ip):
        message = 'Too many failed login attempts.  Please try again later.'
    else:
        system_user = database.get_users(email=email)
        if system_user:
            if not system_user.verify_password(password):
                message = 'Incorrect username or password.'
                RedisLogin.failed_login_attempt(email, ip)
            else:
                if system_user.locked:
                    message = 'Your account has been locked. \nPlease contact your IT department to unlock your account.'
                else:
                    system_user.last_login = datetime.utcnow()
                    database.save_changes()
                    user = system_user.json()
                    session['user'] = user
                    session.permanent = True
                    success = True
                    message = 'Login successful.'
                    RedisLogin.successful_login_attempt(email, ip)
                    logging.info('Login attempt for {0} from {1} succeeded.'.format(email, ip))
                    return json_response(user)
        else:
            message = 'Incorrect username or password.'
            RedisLogin.failed_login_attempt(email, ip)
    logging.info('Login attempt for {0} from {1} failed'.format(email, ip))
    return json_response({'message': message}, 400)

@api_routes.route('/api/v1/logout', methods=['POST'])
@wrappers.verify_login()
def logout(**kwargs):
    session.clear()
    return json_response()

@api_routes.route('/api/v1/me', methods=['GET'])
@wrappers.verify_login()
def me(user, **kwargs):
    if user:
        return json_response(user)
    else:
        return json_response(status=400)

@api_routes.route('/api/v1/password', methods=['POST'])
@wrappers.verify_login()
def change_password(**kwargs):
    content = request.json
    current_password = content.get('password', None)
    new_password = content.get('new', None)
    confirm_password = content.get('confirm', None)
    success = False
    message = ''
    session_user = session.get('user', None)
    if new_password != confirm_password:
        message = 'Confirmation password and password do not match.'
    elif session_user:
        user = database.get_users(id=session_user['id'])
        if user and user.verify_password(current_password):
            success, message = user.set_password(new_password)
            if success:
                session['user'] = user.json()
                database.save_changes()
                return json_response()
        else:
            message = 'Password was not correct.'
    return json_response({'message': message}, 400)

@api_routes.route('/api/v1/token', methods=['GET'])
@limiter.limit("5 per 5 second", get_request_client_id)
def get_access_token(**kwargs):
    client_id = request.headers.get('X-Client-Id', None)
    client_secret = request.headers.get('X-Client-Secret', None)
    if client_id and client_secret:
        api_client = database.get_api_clients(client_id=client_id)
        if api_client and api_client.verify_secret(client_secret):
            new_token = api_client.generate_token()
            database.save_changes()
            return json_response({'token': new_token})
        else:
            return json_response({'message': 'Invalid credentials.'}, 400)
    else:
        return json_response({'message': 'X-Client-Id and X-Client_Secret must be set.'}, 400)
