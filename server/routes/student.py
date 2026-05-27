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
    
@api_routes.route('/api/v1/student/raters/<string:rater_id>', methods=['GET'])
def get_rater_by_id(rater_id, **kwargs):
    raters = database.get_raters(raterid=rater_id,completed=0)
    if raters:
        return json_response([rater.json() for rater in raters])
    else:
        return json_response({'message': 'No Records found.'}, 400)

@api_routes.route('/api/v1/student/postrating', methods=['POST'])
def post_rating(**kwargs):
    content = request.json
    id = content.get('id',None)
    sessionid = content.get('sessionid',None)
    sessionDeviceId = content.get('sessionDeviceId',None)
    speakerTag = content.get('speakerTag',None)
    raterid = content.get('raterid',None)
    evaluationCategory = content.get('evaluationCategory',None)
    response = content.get('response',None)
    rating = database.get_ratings(sessionid=sessionid,sessiondeviceid=sessionDeviceId,speakertag=speakerTag,raterid=raterid,evaluationcategory=evaluationCategory)
    if rating and response:
        resp = json.dumps(response)
        success, _ = database.update_rating(rating[0].id,response=resp)
    elif sessionid and sessionDeviceId and speakerTag and raterid and evaluationCategory and response:
        resp = json.dumps(response)
        success, _ = database.add_rating(sessionid,sessionDeviceId, speakerTag,raterid,evaluationCategory,resp) 
        # database.update_rater(id,completed=1)

    if success:
        return json_response({'message': "success"})
    else:
        return json_response({'message': "Posting unsuccessful"}, 400)
    
@api_routes.route('/api/v1/student/postsurveyresponse', methods=['POST'])
def post_survey_response(**kwargs):
    content = request.json
    id = content.get('id',None)
    sessionid = content.get('sessionid',None)
    sessionDeviceId = content.get('sessionDeviceId',None)
    username = content.get('username',None)
    response = content.get('response',None)
    survey = database.get_survey_reponse(sessionid=sessionid,sessiondeviceid=sessionDeviceId,username=username)
    if survey and response:
        resp = json.dumps(response)
        success, _ = database.update_survey_reponse(survey[0].id,response=resp)
    elif sessionid and sessionDeviceId and username and response:
        resp = json.dumps(response)
        success, _ = database.add_survey_reponse(sessionid,sessionDeviceId, username,resp) 
    if success:
        return json_response({'message': "success"})
    else:
        return json_response({'message': "Survey submission unsuccessful"}, 400)

@api_routes.route('/api/v1/student/postuserinteraction', methods=['POST'])
def post_user_interaction(**kwargs):
    content = request.json
    id = content.get('id',None)
    sessionid = content.get('sessionid',None)
    sessionDeviceId = content.get('sessionDeviceId',None)
    username = content.get('username',None)
    action = content.get('action',None)
    
    if sessionid and sessionDeviceId and username and action:
        success, _ = database.add_user_interaction(sessionid,sessionDeviceId, username,action) 
    if success:
        return json_response({'message': "success"})
    else:
        return json_response({'message': "Interaction submission unsuccessful"}, 400)    
