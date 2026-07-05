from flask import Blueprint, Response, request, abort, session, make_response
from app import socketio
import logging
import json
import database
from google import genai
from dotenv import load_dotenv
from utility import json_response, build_prompt
import os
import time
import numpy as np

api_routes = Blueprint('llmquery', __name__)

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Fail loudly at startup instead of 400ing every LLM request at runtime:
# real Google API keys are 39 chars starting with "AIza".
if not GOOGLE_API_KEY or len(GOOGLE_API_KEY) < 30 or not GOOGLE_API_KEY.startswith("AIza"):
    logging.warning(
        "GOOGLE_API_KEY is missing or looks like a placeholder (len=%s) — "
        "LLM (Gemini) features (reflection dashboards, Q&A, summaries) will "
        "fail until a real key is set in src/server/.env",
        len(GOOGLE_API_KEY or ""),
    )

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
            response = call_gemini_with_retry(prompt)
            
            # client.models.generate_content(
            #     model="gemini-2.5-flash",
            #     contents=prompt
            # )

            raw = response.text.strip()

            if raw.startswith("```"):
                raw = raw.replace("```json", "").replace("```", "").replace("\n","").strip()

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

@api_routes.route('/api/v1/llmqueries/fetch_response_for_question', methods=['POST'])
def fetch_response_for_question(**kwargs):
    questionObj = request.json
    exisiting_response = None
    raw = ""
    if not questionObj:
        return json_response({'message': 'Missing data.'}, 400)
    
    if int(questionObj['default_question_id']) > -1 :
        exisiting_response = database.get_speaker_session_device_llm_question_answer(username=questionObj['participant_name'], sessionId=questionObj['sessionid'], sessionDeviceId = questionObj['sessiondeviceid'],default_question_id=int(questionObj['default_question_id']))
    
    if exisiting_response and questionObj['retrieve_existing_answer'] == 'true':
        raw = str(exisiting_response.answer)
    else:
        prompt = build_prompt(questionObj,"Interactive question answer")

        try:
            response = call_gemini_with_retry(prompt)

            raw = response.text.replace('\n',"").strip()

            if raw.startswith("```"):
                raw = raw.replace("```json", "").replace("```", "").replace('\n',"").strip()

            #add to the database
            if questionObj['retrieve_existing_answer'] != 'true' and exisiting_response:
                #update the database
                database.update_speaker_session_device_llm_question_answer(id=exisiting_response.id,question=questionObj['question'],answer=raw)
            else:
                #insert to database
                database.add_speaker_session_device_llm_question_answer(questionObj['participant_name'], questionObj['sessionid'], questionObj['sessiondeviceid'],questionObj['default_question_id'],questionObj['question'],raw)  
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


@api_routes.route('/api/v1/llminteractiveprompting/sessionid/<int:session_id>/device/<int:session_device_id>/username/<string:username>', methods=['GET'])
def get_llm_question_answer_interactions(session_id,session_device_id,username, **kwargs):
    answers = database.get_speaker_session_device_llm_question_answer(username = username, sessionId = session_id, sessionDeviceId = session_device_id)
    
    if answers:
        retObj = []
        for ans in answers:
            ans.answer = json.loads(str(ans.answer))
            retObj.append(ans.json())

        return json_response(retObj)
    else:
        return json_response([])


@api_routes.route('/api/v1/sessions/<int:session_id>/device/<int:session_device_id>/summary', methods=['GET'])
def generate_discussion_summary(session_id, session_device_id, **kwargs):
    # LLM summary of a pod's discussion: overview, key moments, participation
    # read, and actionable suggestions, from the diarized transcript.
    transcripts = database.get_transcripts(session_device_id=session_device_id)
    lines = []
    for t in transcripts:
        text = (getattr(t, 'transcript', '') or '').strip()
        if not text:
            continue
        spk = getattr(t, 'speaker_tag', None) or 'Unknown'
        lines.append("{0}: {1}".format(spk, text))
    if not lines:
        return json_response({'summary': None, 'message': 'No transcript to summarize.'})
    convo = "\n".join(lines)[:12000]  # cap prompt size
    prompt = (
        "You are analyzing a small-group student discussion. From the diarized "
        "transcript below, return ONLY a JSON object with keys: "
        "\"summary\" (2-3 sentences on what the group discussed), "
        "\"key_moments\" (up to 4 short strings), "
        "\"participation\" (1 sentence on how balanced participation was), "
        "\"suggestions\" (up to 3 short actionable suggestions for the group).\n\n"
        "Transcript:\n" + convo
    )
    try:
        response = call_gemini_with_retry(prompt)
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)
    except Exception as e:
        logging.error("discussion summary failed: %s", e)
        return json_response({'summary': None, 'message': 'Summary generation failed.'}, 502)
    return json_response(data)


def call_gemini_with_retry(prompt, max_retries=5):
    models = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3-flash-preview",
    "gemini-flash-latest",
    ]
    iter = 0
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=models[iter],
                contents=prompt
            )
            return response
        except Exception as e:
            if "503" in str(e):
                wait = (2 ** attempt) + np.random.uniform(0, 1)
                logging.error(f"Retrying in llm prompting for session analysis {wait:.2f}s...")
                time.sleep(wait)
                iter = (iter+1)%len(models)
            else:
                raise
    raise Exception("Max retries exceeded")
        

    
        
    

