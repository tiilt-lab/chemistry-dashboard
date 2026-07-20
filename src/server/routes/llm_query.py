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


# ---------------------------------------------------------------------------
# Local-first LLM. The box runs Ollama on a 46GB Quadro RTX 8000; reflections
# generate there at zero per-token cost and student transcripts never leave
# the machine. Gemini remains as fallback when the local server / model is
# unavailable — so a Gemini spend-cap outage can no longer take the feature
# down, and vice versa.
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:14b")


class _LocalResponse:
    """Duck-types the genai response (.text) so call sites don't change."""
    def __init__(self, text):
        self.text = text


def call_local_llm(prompt, timeout=600):
    import requests as _requests
    r = _requests.post(OLLAMA_URL + "/api/generate", json={
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        # long transcripts/metrics: don't silently truncate at ollama's 4k
        # default. Qwen3 thinking blocks are stripped below.
        "options": {"num_ctx": 16384, "temperature": 0.4},
    }, timeout=timeout)
    r.raise_for_status()
    text = (r.json().get("response") or "").strip()
    # qwen3 emits <think>...</think> before the answer; drop it.
    if "<think>" in text:
        import re as _re
        text = _re.sub(r"<think>.*?</think>", "", text, flags=_re.S).strip()
    if not text:
        raise RuntimeError("local llm returned empty response")
    return _LocalResponse(text)


def _local_llm_available():
    import requests as _requests
    try:
        r = _requests.get(OLLAMA_URL + "/api/tags", timeout=3)
        models = [m.get("name", "") for m in r.json().get("models", [])]
        return any(m == OLLAMA_MODEL or m.startswith(OLLAMA_MODEL + ":")
                   or m.split(":")[0] == OLLAMA_MODEL.split(":")[0]
                   for m in models)
    except Exception:
        return False


def call_llm(prompt):
    """Local first, Gemini fallback. Every reflection/Q&A/summary goes
    through here."""
    if _local_llm_available():
        try:
            return call_local_llm(prompt)
        except Exception as e:
            logging.warning("local llm failed (%s); falling back to Gemini", e)
    return call_gemini_with_retry(prompt)


def _llm_error_response(e):
    """Map raw Gemini failures to something an instructor can act on. The
    spend-cap 429 used to dump the whole error JSON into the dialog."""
    s = str(e)
    logging.error("llm error: %s", s)
    if 'RESOURCE_EXHAUSTED' in s or "'code': 429" in s or s.startswith('429'):
        return json_response({
            'message': "The monthly AI budget is used up, so generating NEW "
                       "reflections and answers is paused. Already-generated "
                       "reports still load normally. New ones resume when the "
                       "budget resets or the spend cap is raised "
                       "(ai.studio/spend).",
        }, 429)
    return json_response({
        'message': "The AI service couldn't complete this request. "
                   "Please try again in a few minutes.",
    }, 502)

@api_routes.route('/api/v1/llmqueries/generate_llm_feedback_based_on_metrics', methods=['POST'])
def generate_llm_feedback_based_on_metrics(**kwargs):
    metricObj = request.json
    raw = ""
    if not metricObj:
        return json_response({'message': 'Missing data.'}, 400)
    # Missing fields must be a clean 400, not a KeyError 500 — the student
    # dashboard sends incomplete payloads when a username has no metrics.
    missing = [k for k in ('participant_name', 'sessionid', 'sessiondeviceid',
                           'participant_level_metric')
               if not metricObj.get(k)]
    if missing:
        return json_response({'message': 'Missing fields: %s' % ', '.join(missing)}, 400)

    exisiting_feedback = database.get_speaker_session_device_llm_report(username=metricObj['participant_name'], sessionId=metricObj['sessionid'], sessionDeviceId = metricObj['sessiondeviceid'])
    
    if exisiting_feedback and metricObj['retrieve_existing_report'] == 'true':
        raw = str(exisiting_feedback.feedback_analysis)
    else:
        prompt = build_prompt(metricObj,"Session_level analysis for participant")

        try:
            response = call_llm(prompt)
            
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
            return _llm_error_response(e)
    
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, ValueError, TypeError):
        # Model returned prose, not JSON — pass it through as raw text.
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
            response = call_llm(prompt)

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
            return _llm_error_response(e)
    
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, ValueError, TypeError):
        # Model returned prose, not JSON — pass it through as raw text.
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
        response = call_llm(prompt)
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)
    except Exception as e:
        return _llm_error_response(e)
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
        

    
        
    

