from flask import Blueprint, Response, request, abort, session, make_response
from app import socketio
import logging
import json
import database
from google import genai
from dotenv import load_dotenv
from utility import json_response, build_prompt
import os

api_routes = Blueprint('llmquery', __name__)

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

client = genai.Client(api_key=GOOGLE_API_KEY)

@api_routes.route('/api/v1/llmqueries/generate_llm_feedback_based_on_metrics', methods=['POST'])
def generate_llm_feedback_based_on_metrics(**kwargs):
    metricObj = request.json
    raw = ""
    if not metricObj:
        return json_response({'message': 'Missing data.'}, 400)
    
    exisiting_feedback = database.get_speaker_session_device_llm_report(username=metricObj['participant_name'], sessionId=metricObj['sessionid'], sessionDeviceId = metricObj['sessiondeviceid'])
    
    if exisiting_feedback and metricObj['retrieve_existing_report'] == 'true':
        raw = str(exisiting_feedback.feedback_analysis)
    else:
        prompt = build_prompt(metricObj,"Session_level analysis for participant")

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )

            
            raw = response.text.strip()

            if raw.startswith("```"):
                raw = raw.replace("```json", "").replace("```", "").strip()

            #add to the database
            if metricObj['retrieve_existing_report'] != 'true' and exisiting_feedback:
                #update the database
                database.update_speaker_session_device_llm_report(id=exisiting_feedback.id,feedback_analysis=raw)
            else:
                #insert to database
                database.add_speaker_session_device_llm_report(metricObj['participant_name'], metricObj['sessionid'], metricObj['sessiondeviceid'],raw)  
        except Exception as e:
            logging.error("exception throw: {0}".format(e))
            return json_response({
                "message": str(e)
            }, 400)
    
    try:
        parsed = json.loads(raw)
    except:
        parsed = {"raw": raw}

    return json_response({
        "answer": parsed
    })
        

    
        
    

