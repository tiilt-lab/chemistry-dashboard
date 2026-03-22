from flask import Blueprint, Response, request, abort, session, make_response
from app import socketio
import logging
import json
from google import genai
from dotenv import load_dotenv
from utility import json_response, build_prompt
import os

api_routes = Blueprint('llmquery', __name__)

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
logging.info("API KEY {0}".format(GOOGLE_API_KEY))

client = genai.Client(api_key=GOOGLE_API_KEY)






@api_routes.route('/api/v1/llmqueries/generate_llm_feedback_based_on_metrics', methods=['POST'])
def generate_llm_feedback_based_on_metrics(**kwargs):
    metricObj = request.json
    
    if not metricObj:
        return json_response({'message': 'Missing data.'}, 400)
    
    prompt = build_prompt(metricObj,"Session_level analysis for participant")

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        
        raw = response.text.strip()

        if raw.startswith("```"):
            raw = raw.replace("```json", "").replace("```", "").strip()

        try:
            parsed = json.loads(raw)
        except:
            parsed = {"raw": raw}

        # logging.info("LLm response {0}".format(parsed))
        return json_response({
            "answer": parsed
        })
        

    except Exception as e:
        return json_response({{
            "message": str(e)
        }}, 400)
        
    

