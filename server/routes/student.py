from flask import Blueprint, Response, request, abort, session, send_file
from tables.user import User
from app import base_dir
import json
import logging
import database
import wrappers
from utility import json_response

api_routes = Blueprint('student', __name__)

@api_routes.route('/api/v1/student/getstudentbyid/<string:user_name>', methods=['GET'])
def get_students(user_name, **kwargs):
    student = database.get_students(username=user_name)
    if student:
        return json_response(student.json())
    else:
        return json_response({'message': 'Student  not found.'}, 400)
      
@api_routes.route('/api/v1/student/addstudent', methods=['POST'])
def add_students(**kwargs):
    content = request.json
    lastname = content.get('lastname', None)
    firstname = content.get('firstname', None)
    username = content.get('username', None)
    if not lastname:
        return json_response({'message': 'Must provide Last name.'}, 400)
    if not firstname:
        return json_response({'message': 'Must provide First name.'}, 400)
    if not username:
        return json_response({'message': 'Must provide User name.'}, 400)
    success, student = database.add_student(lastname, firstname,username)
    if success:
        database.save_changes()
        return json_response(student.json())
    else:
        return json_response({'message': "Username already exists.", "data":student.json()}, 400)
       
        
@api_routes.route('/api/v1/student/updatestudent', methods=['POST'])
def update_students(**kwargs):
    content = request.json
    id = content.get('id',None)
    if not id:
        return json_response({'message': 'Student  Id must be provided '}, 400)
    lastname = content.get('lastname', None)
    firstname = content.get('firstname', None)
    biometric_captured = content.get('biometric_captured', None)
    
    success, student = database.update_student(id,lastname, firstname,biometric_captured)
    if success:
        database.save_changes()
        return json_response(student.json())
    else:
        return json_response({'message': "Update unsuccessful"}, 400)
