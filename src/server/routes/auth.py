from flask import Blueprint, Response, request, abort, session
from utility import json_response
from datetime import datetime
from app import limiter
import json
import logging
import database
import wrappers
from tables.user import User
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
@limiter.limit("5 per 5 second", key_func=get_request_username)
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

# Self-service sign-up for instructors. Creates a plain 'user': it can run its
# own sessions and see nothing but its own data, and a super promotes it to
# admin afterwards from the Admin panel. Deliberately distinct from
# /student/addstudent, which enrols a study participant and creates no login.
#
# Rate-limited by source address rather than by the submitted email, since the
# email is attacker-chosen here and would make the limit trivial to sidestep.
@api_routes.route('/api/v1/register', methods=['POST'])
# Per source address. Generous enough that someone fighting the password rules
# does not lock themselves out — every rejected attempt counts against it.
@limiter.limit("15 per minute")
def register():
    content = request.json or {}
    # Not passed through sanitize(): that HTML-escapes, and /login compares the
    # raw address, so an email containing & or ' would be stored in a form it
    # could never log in with. verify_fields() below is the character check.
    email = (content.get('email', None) or '').strip()
    password = content.get('password', None) or ''
    confirm = content.get('confirm', None) or ''
    ip = utility.get_client_ip(request)

    if not email or not password:
        return json_response({'message': 'Please provide both an email and password.'}, 400)
    valid, message = User.verify_fields(email=email)
    if not valid:
        return json_response({'message': message}, 400)
    if password != confirm:
        return json_response({'message': 'Confirmation password and password do not match.'}, 400)
    # Checked before the account exists, so a weak password never leaves a
    # half-created row behind.
    valid, message = User.validate_password(password)
    if not valid:
        return json_response({'message': message}, 400)

    success, user = database.add_user(email, role='user', password=password.strip())
    if not success:
        logging.info('Registration attempt for existing account {0} from {1}.'.format(email, ip))
        return json_response({'message': 'An account with that email already exists.'}, 400)

    user.last_login = datetime.utcnow()
    database.save_changes()
    # Signed in immediately, exactly as a successful login would.
    session['user'] = user.json()
    session.permanent = True
    logging.info('Registered new user {0} from {1}.'.format(email, ip))
    return json_response(user.json())

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

@api_routes.route('/api/v1/email', methods=['POST'])
@wrappers.verify_login()
def change_email(**kwargs):
    # Mirrors change_password: requires the current password, validates the
    # new address, and rejects duplicates.
    content = request.json
    current_password = content.get('password', None)
    new_email = (content.get('email', None) or '').strip()
    message = ''
    session_user = session.get('user', None)
    valid, message = User.verify_fields(email=new_email)
    if valid and session_user:
        user = database.get_users(id=session_user['id'])
        if user and user.verify_password(current_password):
            existing = database.get_users(email=new_email)
            if existing and existing.id != user.id:
                message = 'That email is already in use.'
            else:
                user.email = new_email
                session['user'] = user.json()
                database.save_changes()
                return json_response()
        else:
            message = 'Password was not correct.'
    return json_response({'message': message}, 400)

@api_routes.route('/api/v1/token', methods=['GET'])
@limiter.limit("5 per 5 second", key_func=get_request_client_id)
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
