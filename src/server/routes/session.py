from flask import Blueprint, Response, request, abort, session, make_response, send_file
import glob
import subprocess
import threading
from utility import sanitize, string_to_bool, json_response
from tables.session_device import SessionDevice
from redis_helper import RedisSessions
from tables.session import Session
from utility import json_response,batch_video_metrics,batch_transcript_metrics,batch_transcript_video_metrics,synthesized_transcript_video_metrics_by_window
from app import socketio
import logging
import database
import json
from datetime import datetime, timedelta
from handlers import session_handler
import wrappers
import config as cf
import socketio_helper
import posthoc_state
import posthoc_queue
import string
import csv
import io
import os
import base64
import queue

api_routes = Blueprint('session', __name__)
image_queue_dict = {}

@api_routes.route('/api/v1/sessions', methods=['GET'])
@wrappers.verify_login(public=True)
def get_sessions(user, **kwargs):
    sessions = database.get_sessions(owner_id=user['id'])
    video_ids = database.get_session_ids_with_video(owner_id=user['id'])
    posthoc_ids = database.get_session_ids_with_posthoc(owner_id=user['id'])
    pod_counts = database.get_session_device_counts(owner_id=user['id'])
    participant_counts = database.get_session_participant_counts(owner_id=user['id'])
    running_session_ids = database.get_session_ids_for_devices(posthoc_state.running_device_ids())
    result = []
    for session in sessions:
        data = session.json()
        data['has_video'] = session.id in video_ids
        data['has_posthoc'] = session.id in posthoc_ids
        data['pod_count'] = pod_counts.get(session.id, 0)
        data['participant_count'] = participant_counts.get(session.id, 0)
        data['analysis_running'] = session.id in running_session_ids
        result.append(data)
    return json_response(result)

@api_routes.route('/api/v1/sessions/<int:session_id>', methods=['GET'])
@wrappers.verify_login(public=True)
@wrappers.verify_session_access
def get_session(session, **kwargs):
    return json_response(session.json())

@api_routes.route('/api/v1/sessions/student/passcode/<string:passcode>', methods=['GET'])
def get_session_by_passcode(passcode, **kwargs):
    sessions = database.get_sessions(passcode=passcode, active=True)
    if sessions:
        return json_response([session.json() for session in sessions])
    else:
        return json_response({'message': 'Session  not found.'}, 400)

@api_routes.route('/api/v1/sessions/student/sessionid/<int:session_id>', methods=['GET'])
def get_session_by_id(session_id, **kwargs):
    session = database.get_sessions(id=session_id)
    if session:
        return json_response(session.json())
    else:
        return json_response({'message': 'Session  not found.'}, 400)

@api_routes.route('/api/v1/sessions/student/alias/<string:alias>', methods=['GET'])
def get_sessions_by_alias(alias, **kwargs):
    sessions = database.get_Session_by_alias(alias=alias)
    if sessions:
         return json_response([session.json() for session in sessions])
    else:
        return json_response({'message': 'Session  not found.'}, 400)
    
@api_routes.route('/api/v1/sessions/sessionid/<int:session_id>/student/alias/<string:alias>', methods=['GET'])
def get_session_device_by_alias(session_id,alias, **kwargs):
    sessionsDevices = database.get_Session_device_by_alias(session_id=session_id,alias=alias)
    if sessionsDevices:
         return json_response([device.json() for device in sessionsDevices])
    else:
        return json_response({'message': 'Session  not found.'}, 400)

@api_routes.route('/api/v1/sessions/<int:session_id>', methods=['PUT'])
@wrappers.verify_login(public=True)
@wrappers.verify_session_access
def update_session(session_id, user, **kwargs):
    name = request.json.get('name', None)
    folder= request.json.get('folder', None)
    if name:
        valid, message = Session.verify_fields(name=name)
        if not valid:
            return json_response({'message': message}, 400)
    if folder != -1:
        owned_folder = database.get_folders(id=folder, owner_id=user['id'], first =True)
        if not owned_folder:
            return json_response({'message': 'Either the folder does not exist or invalid access'}, 404)
    session = database.update_session(session_id, name, folder)
    # Analysis-time settings (applied by the next posthoc run).
    keyword_list_id = sanitize(request.json.get('keywordListId', None))
    topic_model_id = sanitize(request.json.get('topicModelId', None))
    if keyword_list_id is not None or topic_model_id is not None:
        session = database.set_session_analysis_config(
            session_id, user['id'], keyword_list_id, topic_model_id)
    return json_response(session.json())

@api_routes.route('/api/v1/sessions/<int:session_id>', methods=['DELETE'])
@wrappers.verify_login(public=True)
@wrappers.verify_session_access
def delete_session(session_id, **kwargs):
    success =False
    try:
        success = database.delete_session(session_id) 
    except Exception as e:
        logging.info("error occured while deleting session: {0}".format(e))    
    if success:
        return json_response()
    else:
        return json_response({'message': 'Failed to delete session.'}, 400)

@api_routes.route('/api/v1/sessions', methods=['POST'])
@wrappers.verify_login(public=True)
def create_session(user, **kwargs):
    name = request.json.get('name', 'Session')
    valid, message = Session.verify_fields(name=name)
    if not valid:
        return json_response({'message': message}, 400)
    devices = request.json.get('devices', [])
    keyword_list_id = sanitize(request.json.get('keywordListId', None))
    topic_model_id = sanitize(request.json.get('topicModelId', None))
    byod = request.json.get('byod', False)
    features = request.json.get('features', True)
    doa = request.json.get('doa', False)
    folder = request.json.get('folder', None)
    if folder == -1:
        folder = None
    if folder:
        owned_folder = database.get_folders(id=folder, owner_id=user['id'], first =True)
        if not owned_folder:
            return json_response({'message': 'Either the folder does not exist or invalid access'}, 404)
    new_session = session_handler.create_session(user['id'], name, devices, keyword_list_id, topic_model_id, byod, features, doa, folder)
    return json_response(new_session.json())

@api_routes.route('/api/v1/sessions/byod', methods=['POST'])
def byod_join_session(**kwargs):
    name = request.json.get('name', None)
    passcode = sanitize(request.json.get('passcode', None))
    collaborators = request.json.get('collaborators', None)
    if not name or not passcode:
        return json_response({'message': 'Must supply name and passcode.'}, 400)
    valid, message = SessionDevice.verify_fields(name=name)
    if not valid:
        return json_response({'message': message}, 400)
    success, data = session_handler.byod_join_session(name, passcode, collaborators)
    if success:
        return json_response(data)
    else:
        return json_response({'message': data}, 400)

# Same as /api/sessions/byod but bypasses the passcode.
@api_routes.route('/api/v1/sessions/<int:session_id>/devices', methods=['POST'])
@wrappers.verify_login(public=True)
def device_join_session(session_id, **kwargs):
    name = request.json.get('name', None)
    valid, message = SessionDevice.verify_fields(name=name)
    if not valid:
        return json_response({'message': message}, 400)
    success, data = database.create_session_device(session_id, name)
    if success:
        RedisSessions.create_device_key(data.processing_key, session_id)
        return json_response({'session_device': data.json(), 'key': data.processing_key})
    else:
        return json_response({'message': data}, 400)

# Lazy remux cache for pod recordings. MediaRecorder .webm files carry no
# duration or seek cues (players show 24:00:00 and cannot scrub), so on first
# request the original is stream-copied through ffmpeg — which writes both —
# into a cache directory, evicted LRU above the size cap.
VIDEO_CACHE_CAP_BYTES = 12 * 1024 ** 3


def _video_dirs():
    base = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        '..', 'video_processing')
    return (os.path.join(base, 'videorecordings'),
            os.path.join(base, 'videorecordings_fixed'))


def _find_original_video(session_device_id):
    recordings_dir, _ = _video_dirs()
    matches = (
        glob.glob(os.path.join(recordings_dir, '{0}-*_orig.webm'.format(session_device_id)))
        or glob.glob(os.path.join(recordings_dir, '{0}-*.webm'.format(session_device_id)))
        or glob.glob(os.path.join(recordings_dir, '{0}-*.mp4'.format(session_device_id)))
    )
    return os.path.realpath(matches[0]) if matches else None


def _evict_video_cache(cache_dir, incoming_bytes):
    try:
        entries = [(os.path.join(cache_dir, f), os.stat(os.path.join(cache_dir, f)))
                   for f in os.listdir(cache_dir)]
        entries.sort(key=lambda e: e[1].st_atime)  # oldest access first
        total = sum(st.st_size for _, st in entries) + incoming_bytes
        for path, st in entries:
            if total <= VIDEO_CACHE_CAP_BYTES:
                break
            os.remove(path)
            total -= st.st_size
    except Exception as e:
        logging.warning('video cache eviction failed: %s', e)


_remux_locks = {}
_remux_locks_guard = threading.Lock()


def _fixed_video_path(session_device_id):
    # Returns the remuxed (duration+cues fixed) copy, creating it on demand.
    # The remux writes to a temp name and renames atomically, and concurrent
    # requests for the same device serialize on a lock — so a request can never
    # be served a partially written file.
    original = _find_original_video(session_device_id)
    if original is None:
        return None
    _, cache_dir = _video_dirs()
    os.makedirs(cache_dir, exist_ok=True)
    ext = '.mp4' if original.lower().endswith('.mp4') else '.webm'
    fixed = os.path.join(cache_dir, '{0}{1}'.format(session_device_id, ext))
    if os.path.exists(fixed):
        return fixed
    with _remux_locks_guard:
        lock = _remux_locks.setdefault(session_device_id, threading.Lock())
    with lock:
        if os.path.exists(fixed):  # a concurrent request already remuxed it
            return fixed
        _evict_video_cache(cache_dir, os.path.getsize(original))
        tmp = '{0}.tmp{1}'.format(fixed, ext)
        try:
            result = subprocess.run(
                ['ffmpeg', '-y', '-v', 'error', '-i', original, '-c', 'copy', tmp],
                capture_output=True, timeout=300)
            if result.returncode != 0:
                logging.warning('ffmpeg remux failed for %s: %s', original, result.stderr[-500:])
                return original  # fall back to the raw file
            os.replace(tmp, fixed)  # atomic: readers see nothing or all of it
        except Exception as e:
            logging.warning('remux error for %s: %s', original, e)
            return original
        finally:
            try:
                os.remove(tmp)
            except OSError:
                pass
    return fixed


def _video_start_offset(session_id, session_device_id):
    # Seconds between session start and recording start, parsed from the
    # recording filename's "(...)" timestamp — needed to align video time with
    # transcript start_time (both are session-relative).
    original = _find_original_video(session_device_id)
    session_model = database.get_sessions(id=session_id, first=True)
    if original is None or session_model is None:
        return 0.0
    try:
        stamp = original.split('(')[1].split(')')[0]
        recording_start = datetime.strptime(stamp, '%a %b %d %H:%M:%S %Y')
        return max((recording_start - session_model.creation_date).total_seconds(), 0.0)
    except Exception:
        return 0.0


def prewarm_video_cache():
    # Remux every pod recording into the fixed cache in the background at
    # server start (newest first, within the LRU cap), so the first viewer of
    # any video never waits behind "Preparing video...".
    def _worker():
        try:
            recordings_dir, _ = _video_dirs()
            files = sorted(glob.glob(os.path.join(recordings_dir, '*-*.webm')),
                           key=os.path.getmtime, reverse=True)
            _, cache_dir = _video_dirs()
            done = 0
            for path in files:
                # Stop once the cache is ~80% full — remuxing more would only
                # churn the LRU eviction.
                try:
                    used = sum(os.path.getsize(os.path.join(cache_dir, f))
                               for f in os.listdir(cache_dir))
                except OSError:
                    used = 0
                if used > VIDEO_CACHE_CAP_BYTES * 0.8:
                    break
                name = os.path.basename(path)
                device_part = name.split('-', 1)[0]
                if not device_part.isdigit():
                    continue
                _fixed_video_path(int(device_part))
                done += 1
            logging.info('video cache pre-warm finished (%d recordings considered)', done)
        except Exception as e:
            logging.warning('video cache pre-warm failed: %s', e)
    t = threading.Thread(target=_worker, daemon=True, name='video-cache-prewarm')
    t.start()


@api_routes.route('/api/v1/sessions/<int:session_id>/device/<int:session_device_id>/video', methods=['GET'])
def get_session_device_video(session_id, session_device_id, **kwargs):
    # Stream a pod's recorded video for playback beside the transcript.
    # conditional=True lets Flask honor HTTP Range requests so the player can
    # seek. Access mirrors the pod's other media (the /client metric +
    # transcript routes are not owner-gated).
    path = _fixed_video_path(session_device_id)
    if path is None:
        abort(404)
    mimetype = 'video/mp4' if path.lower().endswith('.mp4') else 'video/webm'
    return send_file(path, mimetype=mimetype, conditional=True)


@api_routes.route('/api/v1/sessions/<int:session_id>/device/<int:session_device_id>/video/info', methods=['GET'])
def get_session_device_video_info(session_id, session_device_id, **kwargs):
    # Playback metadata: real duration (ffprobe of the remuxed copy) and the
    # session-relative start offset, so the player can map video time <->
    # transcript time and build subtitle cues.
    path = _fixed_video_path(session_device_id)
    if path is None:
        return json_response({'message': 'No recording.'}, 404)
    duration = None
    try:
        probe = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', path],
            capture_output=True, timeout=60)
        duration = float(probe.stdout.strip())
    except Exception as e:
        logging.warning('ffprobe failed for %s: %s', path, e)
    return json_response({
        'duration': duration,
        'offset': _video_start_offset(session_id, session_device_id),
    })


@api_routes.route('/api/v1/sessions/<int:session_id>/device/<int:session_device_id>/posthoc_completed', methods=['POST'])
@wrappers.verify_login(public=True)
def mark_posthoc_completed(session_id, session_device_id, user, **kwargs):
    # Recorded when a post-hoc re-analysis finishes for a pod, so the sessions
    # list can show which discussions have been re-analyzed. Owner-gated.
    owned = database.get_sessions(id=session_id, owner_id=user['id'], first=True)
    if owned is None:
        return json_response({'message': 'Session not found.'}, 404)
    # Optional per-run model provenance blob (e.g. {asr, embedder, diarizer,
    # scorer, emotion, attention, ...}); absent for older callers.
    from flask import request as _request
    body = _request.get_json(silent=True) or {}
    models = body.get('models')
    if database.mark_session_device_posthoc(session_device_id, models=models):
        return json_response({'ok': True})
    return json_response({'message': 'Device not found.'}, 404)


@api_routes.route('/api/v1/sessions/pod', methods=['POST'])
@wrappers.verify_login(public=True)
@wrappers.verify_session_access_json
def pod_join_session(**kwargs):
    session_id = request.json.get('sessionId', None)
    pod_id = request.json.get('podId', None)
    if not session_id or not pod_id:
        return json_response({'message': 'Must supply sessionId and PodId.'}, 400)
    success, response = session_handler.pod_join_session(session_id, pod_id)
    if success:
        return json_response(response)
    else:
        return json_response(response, 400)

@api_routes.route('/api/v1/sessions/<int:session_id>/stop', methods=['POST'])
@wrappers.verify_login(public=True)
@wrappers.verify_session_access
def end_session(session_id, **kwargs):
    success, data = session_handler.end_session(session_id)
    if success:
        return json_response(data.json())
    else:
        return json_response({'message': data}, 400)

@api_routes.route('/api/v1/sessions/<int:session_id>/devices/<int:device_id>/transcripts', methods=['GET'])
@wrappers.verify_login(public=True)
@wrappers.verify_session_access
def session_device_transcripts(session_id, device_id, **kwargs):
    transcripts = database.get_transcripts(session_device_id=device_id)
    return json_response([transcript.json() for transcript in transcripts])

@api_routes.route('/api/v1/sessions/devices/<int:device_id>/speakers/<int:speaker_id>/transcripts', methods=['GET'])
@wrappers.verify_login(public=True)
@wrappers.verify_session_access
def speaker_id_transcripts_for(device_id, speaker_id, **kwargs):
    transcripts = database.get_transcripts(speaker_id=speaker_id)
    return json_response([transcript.json() for transcript in transcripts])

@api_routes.route('/api/v1/sessions/devices/<int:device_id>/speaker_tags', methods=['GET'])
#@wrappers.verify_login(public=True)
#@wrappers.verify_session_access
def speaker_tags_for(device_id, **kwargs):
    tags = database.get_speaker_tags(session_device_id=device_id)
    return json_response({"Speakers": tags})

@api_routes.route('/api/v1/devices/<int:device_id>/transcripts/client', methods=['GET'])
# @wrappers.verify_login(public=True)
# @wrappers.verify_session_access
def session_device_transcripts_for_client(device_id, **kwargs):
    transcript_speaker_metrics = []
    transcripts = database.get_transcripts(session_device_id=device_id)
    
    return json_response([transcript.json() for transcript in transcripts])

@api_routes.route('/api/v1/devices/<int:device_id>/transcriptspeakermetrics/client', methods=['GET'])
# @wrappers.verify_login(public=True)
# @wrappers.verify_session_access
def session_device_transcript_speaker_metrics_for_client(device_id, **kwargs):
    transcript_speaker_metrics = []
    transcripts = database.get_transcripts(session_device_id=device_id)
    for transcript in transcripts:
        speaker_metrics = database.get_speaker_transcript_metrics(transcript_id=transcript.id)
        transcript_speaker_metrics.append({'transcript': transcript.json(),
                                            'speaker_metrics': [speaker_metric.json() for speaker_metric in speaker_metrics]})
    return json_response(transcript_speaker_metrics)

@api_routes.route('/api/v1/devices/<int:device_id>/videometrics/client', methods=['GET'])
# @wrappers.verify_login(public=True)
# @wrappers.verify_session_access
def session_device_videometrics_for_client(device_id, **kwargs):
    videometrics = database.get_speaker_video_metrics(session_device_id=device_id)
    return json_response([videometric.json() for videometric in videometrics])


@api_routes.route('/api/v1/session/<int:session_id>/transcripts/student/<string:alias>', methods=['GET'])
def session_transcripts_for_client(session_id, alias, **kwargs):
    transcript_speaker_metrics = []
    transcripts = database.get_transcripts_by_session_alias(session_id=session_id,speaker_tag=alias)
    for transcript in transcripts:
        speaker_metrics = database.get_speaker_transcript_metrics(transcript_id=transcript.id)
        transcript_speaker_metrics.append({'transcript': transcript.json(),
                                            'speaker_metrics': [speaker_metric.json() for speaker_metric in speaker_metrics]})
    
    return json_response(transcript_speaker_metrics) 
    
@api_routes.route('/api/v1/session/<int:session_id>/sessiondevice/<int:device_id>/transcripts/student/<string:alias>', methods=['GET'])
def session_device_transcripts_by_alias(session_id,device_id, alias, **kwargs):
    transcript_speaker_metrics = []
    transcripts = database.get_transcripts_by_session_alias(session_id=session_id,speaker_tag=alias,device_id=device_id)
    for transcript in transcripts:
        speaker_metrics = database.get_speaker_transcript_metrics(transcript_id=transcript.id)
        transcript_speaker_metrics.append({'transcript': transcript.json(),
                                            'speaker_metrics': [speaker_metric.json() for speaker_metric in speaker_metrics]})
    
    return json_response(transcript_speaker_metrics) 


@api_routes.route('/api/v1/session/<int:session_id>/videometrics/student/<string:alias>', methods=['GET'])
def session_videometrics_for_client(session_id,alias, **kwargs):
    videoMetrics = database.get_speaker_video_metrics_by_session_alias(session_id=session_id,student_username=alias)
    return json_response([videometric.json() for videometric in videoMetrics])

@api_routes.route('/api/v1/session/<int:session_id>/sessiondevice/<int:device_id>/videometrics/student/<string:alias>', methods=['GET'])
def session_device_videometrics_by_alias(session_id,device_id,alias, **kwargs):
    videoMetrics = database.get_speaker_video_metrics_by_session_alias(session_id=session_id,student_username=alias,device_id=device_id)
    return json_response([videometric.json() for videometric in videoMetrics])


@api_routes.route('/api/v1/devices/<int:device_id>/transcripts/speaker_metrics', methods=['GET'])
def session_device_speaker_metrics(device_id, **kwargs):
    speaker_metrics = database.get_speaker_transcript_metrics(session_device_id=device_id)
    # logging.info(f'Received speaker metrics from database{speaker_metrics}')
    return json_response([speaker_metric.json() for speaker_metric in speaker_metrics])

@api_routes.route('/api/v1/sessions/<int:session_id>/transcripts/speaker_metrics', methods=['POST'])
def session_transcript_speaker_metrics(session_id):
    transcripts = database.get_transcripts(session_id=session_id)
    transcripts_metrics = []
    for transcript in transcripts:
        speaker_metrics = database.get_speaker_transcript_metrics(transcript_id=transcript.id)
        transcripts_metrics.append({'transcript' : transcript.json(),
                                    'speaker_metrics' : [speaker_metric.json() for speaker_metric in speaker_metrics]})
    return json_response(json.dumps(transcripts_metrics))

@api_routes.route('/api/v1/sessions/devices/<int:device_id>/speakers/<int:speaker_id>/transcripts/client', methods=['GET'])
# @wrappers.verify_login(public=True)
# @wrappers.verify_session_access
def speaker_id_transcripts_for_client(device_id, speaker_id, **kwargs):
    transcripts = database.get_transcripts(speaker_id=speaker_id)
    return json_response([transcript.json() for transcript in transcripts])

@api_routes.route('/api/v1/sessions/<int:session_id>/devices/<int:device_id>/speakers', methods=['GET'])
@wrappers.verify_login(public=True)
@wrappers.verify_session_access
def session_device_speakers(session_id, device_id, **kwargs):
    speakers = database.get_speakers(session_device_id=device_id)
    return json_response([speaker.json() for speaker in speakers])

@api_routes.route('/api/v1/sessions/<int:session_id>/speakers', methods=['GET'])
@wrappers.verify_login(public=True)
@wrappers.verify_session_access
def session_speakers(session_id, **kwargs):
    speakers = database.get_speakers(session_id=session_id)
    return json_response([speaker.json() for speaker in speakers])

@api_routes.route('/api/v1/sessions/<int:session_id>/devices/<int:device_id>/keywords', methods=['GET'])
@wrappers.verify_login(public=True)
@wrappers.verify_session_access
def session_device_keywords(session_id, device_id, **kwargs):
    keywords = database.get_keyword_usages(session_device_id=device_id)
    return json_response([keyword.json() for keyword in keywords])

@api_routes.route('/api/v1/sessions/<int:session_id>/devices/<int:session_device_id>', methods=['GET'])
@wrappers.verify_login(public=True)
@wrappers.verify_session_access
def session_device(session_id, session_device_id, processing_key, **kwargs):
        if session_device_id:
          session_device = database.get_session_devices(id=session_device_id)
        elif processing_key:
          session_device = database.get_session_devices(processing_key=processing_key)
        return json_response(session_device.json())

@api_routes.route('/api/v1/sessions/<int:session_id>/devices', methods=['GET'])
@wrappers.verify_login(public=True)
@wrappers.verify_session_access
def session_devices(session_id, **kwargs):
        devices = database.get_session_devices(session_id=session_id)
        # Per-pod duration (seconds, derived from transcript timestamps since
        # session_device stores no start/end) + participant count.
        durations = database.get_pod_durations(session_id)
        speaker_counts = database.get_pod_speaker_counts(session_id)
        video_pods = database.get_pod_video_presence(session_id)
        result = []
        for device in devices:
            data = device.json()
            data['duration'] = durations.get(device.id)
            if data['duration'] is None:
                data['duration'] = posthoc_state.last_duration(device.id)
            data['speaker_count'] = speaker_counts.get(device.id, 0)
            # True if the pod captured any usable data (transcript or video);
            # ~17% of pods recorded nothing and should be flagged, not analyzed.
            data['has_data'] = (durations.get(device.id) is not None) or (device.id in video_pods)
            data['has_video'] = device.id in video_pods
            data['analysis_running'] = posthoc_state.is_running(device.id)
            result.append(data)
        return json_response(result)


@api_routes.route('/api/v1/sessions/<int:session_id>/device/<int:session_device_id>/dynamics', methods=['GET'])
def get_pod_dynamics(session_id, session_device_id, **kwargs):
    # Conversation dynamics for a pod: per-speaker turns/speaking-share (equity)
    # + the who-follows-whom response network.
    return json_response(database.get_conversation_dynamics(session_device_id))


@api_routes.route('/api/v1/sessions/upload_video', methods=['POST'])
@wrappers.verify_login(public=True)
def upload_video_session(user, **kwargs):
    # Analyze a user-provided recording: create a session + one pod, place the
    # video (and an extracted 16k mono f32 wav) exactly where the post-hoc
    # services look for pod recordings, then auto-queue the full analysis.
    # No enrolled speakers, so diarization yields generic SPEAKER_NN labels.
    import time as _time
    f = request.files.get('video')
    if f is None:
        return json_response({'message': 'video file required'}, 400)
    name = sanitize(request.form.get('name') or 'Uploaded video')[:60]
    session_obj = session_handler.create_session(user['id'], name, [], None, None, True, True, False, None)
    ok, device = database.create_session_device(session_obj.id, 'Uploaded')
    if not ok:
        return json_response({'message': str(device)}, 400)
    key = device.processing_key
    ctime = _time.ctime()
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..')
    vid_dir = os.path.join(base, 'video_processing', 'videorecordings')
    aud_dir = os.path.join(base, 'audio_processing', 'recordings')
    ext = (f.filename or '').rsplit('.', 1)[-1].lower()
    ext = ext if ext in ('webm', 'mp4') else 'webm'
    vid_path = os.path.join(vid_dir, '{0}_{1}_{2}_({3})_orig.{4}'.format(key, session_obj.id, device.id, ctime, ext))
    f.save(vid_path)
    wav_path = os.path.join(aud_dir, '{0}({1})_orig.wav'.format(key, ctime))
    try:
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', vid_path, '-vn',
                        '-ar', '16000', '-ac', '1', '-acodec', 'pcm_f32le', wav_path],
                       check=True, timeout=600)
    except Exception as e:
        return json_response({'message': 'audio extraction failed: %s' % e}, 400)
    # close the session (uploads are not live) and queue the analysis
    database.update_session_status(session_obj.id) if hasattr(database, 'update_session_status') else None
    import posthoc_queue
    posthoc_queue.enqueue(session_obj.id, [device.id])
    return json_response({'session_id': session_obj.id, 'device_id': device.id, 'queued': True})


@api_routes.route('/api/v1/sessions/<int:session_id>/posthoc_queue', methods=['POST'])
@wrappers.verify_login(public=True)
@wrappers.verify_session_access
def enqueue_posthoc(session_id, **kwargs):
    # Queue full analyses for several pods; they run one pod at a time.
    body = request.get_json(silent=True) or {}
    device_ids = body.get('device_ids') or []
    if not device_ids:
        return json_response({'message': 'device_ids required'}, 400)
    added = posthoc_queue.enqueue(session_id, device_ids, models=body.get('models'))
    return json_response({'queued': added, 'status': posthoc_queue.status(session_id)})


@api_routes.route('/api/v1/sessions/<int:session_id>/posthoc_queue/stop', methods=['POST'])
@wrappers.verify_login(public=True)
@wrappers.verify_session_access
def stop_posthoc_queue(session_id, **kwargs):
    # Cancel: drop queued jobs and tell the services to stop this session's
    # running pods (best-effort; services also apply on their next restart).
    import posthoc_queue, posthoc_state, json as _json, os as _os
    cleared = posthoc_queue.clear_pending()
    cancelled = 0
    try:
        import asyncio, websockets
        async def _cancel(port, did):
            async with websockets.connect('ws://127.0.0.1:%s' % port, open_timeout=5) as ws:
                await ws.send(_json.dumps({'type': 'cancel_posthoc', 'sessiondeviceid': did}))
                await asyncio.wait_for(ws.recv(), timeout=5)
        for did in list(posthoc_state.running_device_ids()):
            for port in (_os.getenv('DC_AUDIO_POSTHOC_WS_PORT', '9015'), _os.getenv('DC_VIDEO_POSTHOC_WS_PORT', '9014')):
                try:
                    asyncio.run(_cancel(port, did)); cancelled += 1
                except Exception:
                    pass
            posthoc_state.mark_done(did)
    except Exception as e:
        logging.warning('stop_posthoc_queue cancel pass failed: %s', e)
    return json_response({'cleared': cleared, 'cancel_signals': cancelled})


@api_routes.route('/api/v1/sessions/<int:session_id>/posthoc_queue', methods=['GET'])
@wrappers.verify_login(public=True)
@wrappers.verify_session_access
def posthoc_queue_status(session_id, **kwargs):
    return json_response(posthoc_queue.status(session_id))


@api_routes.route('/api/v1/students/<username>/longitudinal', methods=['GET'])
@wrappers.verify_login(public=True)
def get_student_longitudinal(username, **kwargs):
    # A student's per-session speaking share + attention across the term.
    return json_response(database.get_student_longitudinal(username))

@api_routes.route('/api/v1/devices/<int:session_device_id>/session_device', methods=['GET'])
def session_device_by_id(session_device_id, **kwargs):
    device = database.get_session_devices(id=session_device_id)
    return json_response(device.json())


def _face_thumb_path(alias):
    # Representative face crop saved by the video pipeline (per student alias).
    base = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        '..', 'video_processing', 'facial_embeddings', 'thumbnails')
    safe = os.path.basename(str(alias))  # prevent path traversal
    return os.path.join(base, "{0}.jpg".format(safe))


@api_routes.route('/api/v1/sessions/<int:session_id>/device/<int:session_device_id>/facethumb/<alias>', methods=['GET'])
def get_face_thumbnail(session_id, session_device_id, alias, **kwargs):
    # Face crop for a recognized student, scoped to a session+device path (same
    # access model as the pod video). 404 until the pod is (re)processed.
    path = _face_thumb_path(alias)
    if not os.path.exists(path):
        return ('', 404)
    resp = make_response(send_file(path, mimetype='image/jpeg'))
    resp.headers['Cache-Control'] = 'public, max-age=300'
    return resp

@api_routes.route('/api/v1/help_button', methods=['POST'])
@wrappers.verify_login(allow_key=True)
def set_help_button(**kwargs):
    session_device_id = request.json.get('id', None)
    state = request.json.get('activated', False)
    if not session_device_id:
        return json_response({'message': 'Session device ID must be provided.'}, 400)

    session_device = database.get_session_devices(id=session_device_id)
    if session_device:
        if session_device.button_pressed != state:
            session_device.button_pressed = state
            database.save_changes()
            room_name = str(session_device.session_id)
            socketio.emit('device_update', json.dumps(session_device.json()), room=room_name, namespace="/session")
        return json_response()
    return json_response({'message': 'Session device not found.'}, 400)

@api_routes.route('/api/v1/sessions/<int:session_id>/passcode', methods=['POST'])
@wrappers.verify_login(public=True)
@wrappers.verify_session_access
def set_session_passcode(session_id, **kwargs):
    state = request.json.get('state', None)
    if not state in ['lock', 'unlock', 'refresh']:
        return json_response({'message': 'Invalid passcode state.'}, 400)
    session = database.get_sessions(id=session_id)
    if session:
        if state == 'lock':
            session.passcode = None
            database.save_changes()
        elif state in ['unlock', 'refresh']:
            database.generate_session_passcode(session.id)
        socketio_helper.update_session(session)
        return json_response(session.json())
    return json_response({'message': 'Session not found.'}, 404)

@api_routes.route('/api/v1/sessions/<int:session_id>/devices/<int:session_device_id>', methods=['DELETE'])
@wrappers.verify_login(public=True)
@wrappers.verify_session_access
def remove_device_from_session(session_id, session_device_id, **kwargs):
    delete = string_to_bool(request.args.get('delete', 'false'))
    session_handler.remove_session_device(session_device_id)
    if delete:
        database.delete_session_device(session_device_id)
        socketio_helper.remove_session_device(session_id, session_device_id)
    return json_response()


# Shared tail for the three metrics-export endpoints: wrap the accumulated
# CSV buffer / JSON dict in a download response.
def _metrics_export_response(si, json_payload, format):
    if format == 'csv':
        output = make_response(si.getvalue())
        output.headers["Content-Disposition"] = "attachment; filename=export.csv"
        output.headers["Content-type"] = "text/csv"
    elif format == 'json':
        json_data = json.dumps(json_payload, indent=2)
        output = make_response(json_data)
        output.headers["Content-Disposition"] = "attachment; filename=export.json"
        output.headers["Content-type"] = "application/json"
    return output


@api_routes.route('/api/v1/sessions/<int:session_id>/exporttranscriptmetrics/<int:windowsize>/<string:format>',methods=['GET'])
@wrappers.verify_login(public=True)
@wrappers.verify_session_access
def export_session_transcript_metrics(session_id,windowsize, format, **kwargs):
    si = io.StringIO()
    field_names = None  
    fwrite = None 
    session_devices = database.get_session_devices(session_id=session_id)
    All_particiapants_video_metrics = []
    if windowsize == 0:
        field_names = ['Device ID', 'Device Name', 'Start Time', 'Transcript Id','Transcript', 'Keywords', 'Keywords Detected', 'Similarity', 'Analytic Thinking', 'Authenticity', 'Certainty',
                    'Clout', 'Emotional Tone', 'Direction',  'participation_score', 'internal_cohesion', 'responsivity', 'social_impact','newness','communication_density','Word Count', 'Speaker Tag', 'Speaker ID', 'Topic ID']
        fwrite = csv.DictWriter(si, fieldnames = field_names)
        fwrite.writeheader()
        for session_device in session_devices:
            transcripts = database.get_all_transcript_metrics_by_session(session_device_id=session_device.id)
            keywords = database.get_keyword_usages(session_device_id=session_device.id)
            for t, sm in transcripts:
                transcript_keywords = [keyword for keyword in keywords if keyword.transcript_id == t.id]
                fwrite.writerow({'Device ID':session_device.id,
                    'Device Name':session_device.name,
                    'Start Time': str(timedelta(seconds=int(t.start_time))),
                    'Transcript Id': int(t.id),
                    'Transcript':t.transcript,
                    'Keywords': ', '.join([keyword.keyword for keyword in transcript_keywords]),
                    'Keywords Detected': ', '.join([keyword.word for keyword in transcript_keywords]),
                    'Similarity': ', '.join([str(round((1-keyword.similarity)*100,3)) for keyword in transcript_keywords]),
                    'Analytic Thinking': int(t.analytic_thinking_value),
                    'Authenticity': int(t.authenticity_value),
                    'Certainty': int(t.certainty_value),
                    'Clout': int(t.clout_value),
                    'Emotional Tone': int(t.emotional_tone_value),
                    'participation_score': int(float(sm.participation_score)*100),
                    'internal_cohesion':  int(float(sm.internal_cohesion)*100),
                    'responsivity':  int(float(sm.responsivity)*100),
                    'social_impact':  int(float(sm.social_impact)*100),
                    'newness':  int(float(sm.newness)*100), 
                    'communication_density':  int(float(sm.communication_density)*100),
                    'Word Count': int(t.word_count),
                    'Speaker Tag': t.speaker_tag,
                    'Speaker ID': int(t.speaker_id),
                    'Topic ID': int(t.topic_id)
                    })
    else:
        field_names = ['Group ID', 'Group Name', 'Time Range (s)','Transcript', 'Keywords', 'Keywords Detected', 'Similarity', 'Analytic Thinking', 'Authenticity', 'Certainty',
                    'Clout', 'Emotional Tone', 'Direction',  'participation_score', 'internal_cohesion', 'responsivity', 'social_impact','newness','Word Count', 'Speaker Tag', 'Speaker ID', 'Topic ID']
        fwrite = csv.DictWriter(si, fieldnames = field_names)
        fwrite.writeheader()     
        for session_device in session_devices:
            keywords = database.get_keyword_usages(session_device_id=session_device.id)
            speakers = database.get_speakers(session_device_id=session_device.id)
            for speaker in speakers:
                transcriptSpeakerMetric = database.get_all_transcript_metrics_by_session(session_device_id=session_device.id,speaker_id=speaker.id)
                speaker_data = batch_transcript_metrics(transcriptSpeakerMetric,windowsize,fwrite,speaker,session_device,keywords,format)
                if format == 'json':
                    All_particiapants_video_metrics[speaker.alias] = [dict(zip(field_names, row)) for row in speaker_data]
                    # All_particiapants_video_metrics.extend(speaker_data)
                        

    return _metrics_export_response(si, All_particiapants_video_metrics, format)

@api_routes.route('/api/v1/sessions/<int:session_id>/exportvideometrics/<int:windowsize>/<string:format>',methods=['GET'])
@wrappers.verify_login(public=True)
@wrappers.verify_session_access
def export_session_video_metrics(session_id, windowsize, format, **kwargs):
    field_names = None
    fwrite = None  
    si = io.StringIO()
    session_devices = database.get_session_devices(session_id=session_id)
    All_particiapants_video_metrics = []
    if windowsize == 0:
        field_names = ['Device ID', 'Device Name', 'Start Time', 'Facial Emotion', 'Object Focus On', 'Attention Level', 'Speaker Tag']
        fwrite = csv.DictWriter(si, fieldnames = field_names)
        fwrite.writeheader()  
        for session_device in session_devices:
            videoMetrics = database.get_video_metrics_by_session(session_device_id=session_device.id)
            for v in videoMetrics:
                fwrite.writerow({'Device ID':session_device.id,
                    'Device Name':session_device.name,
                    'Start Time':str(timedelta(seconds=int(v.time_stamp))),
                    'Facial Emotion': str(v.facial_emotion),
                    'Object Focus On': str(v.object_on_focus),
                    'Attention Level': int(v.attention_level),
                    'Speaker Tag': v.student_username
                    })

    else:
        field_names = ['Group ID', 'Group Name', 'Time Range (s)', 'Facial Emotion', 'Object Focus On', 'Attention Level','Attention Rate',"Attention Class", 'Speaker Tag']
        fwrite = csv.DictWriter(si, fieldnames = field_names)
        fwrite.writeheader()
        for session_device in session_devices:
            speakers = database.get_speakers(session_device_id=session_device.id)
            for speaker in speakers:
                videoMetrics = database.get_speaker_video_metrics(session_device_id=session_device.id,student_username=speaker.alias)
                speaker_data = batch_video_metrics(videoMetrics,windowsize,fwrite,speaker,session_device,format)
                if format == 'json':
                    All_particiapants_video_metrics[speaker.alias] = [dict(zip(field_names, row)) for row in speaker_data]
                    # All_particiapants_video_metrics.extend(speaker_data)  
    return _metrics_export_response(si, All_particiapants_video_metrics, format)

@api_routes.route('/api/v1/sessions/<int:session_id>/exporttranscriptvideometrics/<int:windowsize>/<string:format>',methods=['GET'])
@wrappers.verify_login(public=True)
@wrappers.verify_session_access
def export_session_transcript_video_metrics(session_id,windowsize, format, **kwargs):
    si = io.StringIO()
    field_names = None
    fwrite = None
    session_devices = database.get_session_devices(session_id=session_id)
    All_particiapants_video_metrics = {}
    if windowsize == 0:
        field_names = ['Device ID', 'Device Name', 'Start Time', 'Transcript', 'Keywords', 'Keywords Detected', 'Similarity', 'Analytic Thinking', 'Authenticity', 'Certainty',
                    'Clout', 'Emotional Tone', 'Direction',  'participation_score', 'internal_cohesion', 'responsivity', 'social_impact','newness','communication_density',
                    'Word Count', 'Facial Emotion', 'Object Focus On', 'Attention Level', 'Speaker Tag', 'Speaker ID', 'Topic ID']
        fwrite = csv.DictWriter(si, fieldnames = field_names)
        fwrite.writeheader()
        for session_device in session_devices:
            all_metrics = database.get_all_metrics_by_session(session_device_id=session_device.id)
            keywords = database.get_keyword_usages(session_device_id=session_device.id)
            for t,sm,vm in all_metrics:
                transcript_keywords = [keyword for keyword in keywords if keyword.transcript_id == t.id]
                fwrite.writerow({'Device ID':session_device.id,
                    'Device Name':session_device.name,
                    'Start Time': str(t.start_time), #str(timedelta(seconds=int(t.start_time))),
                    'Transcript':t.transcript,
                    'Keywords': ', '.join([keyword.keyword for keyword in transcript_keywords]),
                    'Keywords Detected': ', '.join([keyword.word for keyword in transcript_keywords]),
                    'Similarity': ', '.join([str(round((1-keyword.similarity)*100,3)) for keyword in transcript_keywords]),
                    'Analytic Thinking': int(t.analytic_thinking_value),
                    'Authenticity': int(t.authenticity_value),
                    'Certainty': int(t.certainty_value),
                    'Clout': int(t.clout_value),
                    'Emotional Tone': int(t.emotional_tone_value),
                    'participation_score': int(float(sm.participation_score)*100),
                    'internal_cohesion':  int(float(sm.internal_cohesion)*100),
                    'responsivity':  int(float(sm.responsivity)*100),
                    'social_impact':  int(float(sm.social_impact)*100),
                    'newness':  int(float(sm.newness)*100), 
                    'communication_density':  int(float(sm.communication_density)*100),
                    'Word Count': int(t.word_count),
                    'Facial Emotion': str(vm.facial_emotion),
                    'Object Focus On': str(vm.object_on_focus),
                    'Attention Level': int(vm.attention_level),
                    'Speaker Tag': t.speaker_tag,
                    'Speaker ID': int(t.speaker_id),
                    'Topic ID': int(t.topic_id)
                    })
    else:
        field_names = ['Group ID', 'Group Name', 'Time Range (s)', 'Transcript', 'Keywords', 'Keywords Detected', 'Similarity', 'Analytic Thinking', 'Authenticity', 'Certainty',
                    'Clout', 'Emotional Tone',  'participation_score', 'internal_cohesion', 'responsivity', 'social_impact','newness',
                    'Word Count', 'Facial Emotion', 'Object Focus On', 'Attention Level','Attention Rate',"Attention Class", 'Speaker Tag', 'Speaker ID', 'Topic ID']
        fwrite = csv.DictWriter(si, fieldnames = field_names)
        fwrite.writeheader()       
        for session_device in session_devices:
            keywords = database.get_keyword_usages(session_device_id=session_device.id)
            speakers = database.get_speakers(session_device_id=session_device.id)
            for speaker in speakers:
                videoMetrics = database.get_speaker_video_metrics(session_device_id=session_device.id,student_username=speaker.alias)
                transcriptSpeakerMetric = database.get_all_transcript_metrics_by_session(session_device_id=session_device.id,speaker_id=speaker.id)
                speaker_data = batch_transcript_video_metrics(transcriptSpeakerMetric,videoMetrics,windowsize,fwrite,speaker,session_device,keywords,format)
                if format == 'json':
                    All_particiapants_video_metrics[speaker.alias] = [dict(zip(field_names, row)) for row in speaker_data]
                    # All_particiapants_video_metrics.extend(speaker_data) 
                   

    return _metrics_export_response(si, All_particiapants_video_metrics, format)

@api_routes.route('/api/v1/sessions/<int:session_id>/device/<int:session_device_id>/synthesized_feedback_metrics',methods=['GET'])
# @wrappers.verify_login(public=True)
# @wrappers.verify_session_access
def getSynthesizedFeedbackMetrics(session_id,session_device_id, **kwargs):
    session_device = database.get_session_devices(id=session_device_id)
    
    combine_metric_level = {'group_id': session_device.id, 'group_name': session_device.name, 'window_level':{}, 'participants_level':{}, 'session_level':{}, 'group_level':{}}
    
    exisiting_synthesis = database.get_synthesized_feedback_report(sessionId=session_id, sessionDeviceId = session_device_id)

    # if exisiting_synthesis:
    #     raw = str(exisiting_synthesis[0].synthesized_feedback)
    #     combine_metric_level = json.loads(raw)
    # else:

    keywords = database.get_keyword_usages(session_device_id=session_device_id)
    # speakers = database.get_speakers(session_device_id=session_device_id)

    videoMetrics = database.get_speaker_video_metrics(session_device_id=session_device_id)
    transcriptSpeakerMetric = database.get_all_transcript_metrics_by_session_by_timeline(session_device_id=session_device.id)
    combine_metric_level = synthesized_transcript_video_metrics_by_window(transcriptSpeakerMetric,videoMetrics,session_device,keywords,windowsize=10)#speakers,

    combine_metric_dump = json.dumps(combine_metric_level)
    # add to the database
    if exisiting_synthesis:
        #update the database
        database.update_synthesized_feedback_report(id=exisiting_synthesis[0].id,synthesized_feedback=combine_metric_dump)
    else:
        #insert to database
        database.add_synthesized_feedback_report(sessionId=session_id,sessionDeviceId=session_device_id,synthesized_feedback=json.dumps(combine_metric_level))


    return json_response(combine_metric_level)
    
@api_routes.route('/api/v1/sessions/getredissessionkey', methods=['POST'])
def get_device_key(**kwargs):
    content = request.get_json()
    redis_key = RedisSessions.get_device_key(content['auth_key'])
    if redis_key:
        return json_response({'redis_key': redis_key})
    else:
        return json_response({'message': "key cannot be authenticated"}, 400)

@api_routes.route('/api/v1/sessions/getredissessionconfig', methods=['POST'])
def get_session_config(**kwargs):
    content = request.get_json()
    redis_session = RedisSessions.get_session_config(content['session_key'])
    if redis_session:
        return json_response({'redis_session_key': redis_session})
    else:
        return json_response({'message': "Session key cannot be authenticated"}, 400)

@api_routes.route('/api/v1/session/addcartoonizedimage', methods=['POST'])
@wrappers.verify_local
def add_cartoonized_image(**kwargs):
    logging.info('Received cartoonized image ...')
    content = request.get_json()
    queue_key = '{0}_{1}_{2}'.format(content['source'],content['sessionid'],content['deviceid'])
    if queue_key in image_queue_dict.keys():
        image_queue_dict[queue_key].put(content)
    else:
        image_queue = queue.Queue()
        image_queue.put(content)
        image_queue_dict[queue_key] = image_queue
    return json_response()

@api_routes.route('/api/v1/sessions/<int:session_id>/devices/<int:device_id>/auth/<auth_id>/streamimages')
def stream_cartonized_images(session_id, device_id,auth_id, **kwargs):
    try:
        filePath  = os.path.dirname(os.path.abspath(__file__))
        os.chdir(filePath)
        os.chdir("../../video_processing/videorecordings")
        loading_img_Path = os.path.join(os.getcwd(),'loading_img')
        loading_frame = read_image(os.path.join(loading_img_Path,'loading.png'))
        queue_key = '{0}_{1}_{2}'.format(auth_id,session_id,device_id)
        return Response(gen(loading_frame,queue_key),
                        mimetype='multipart/x-mixed-replace; boundary=frame')
    except Exception as e:
        logging.error('Error occured while streaming cartoonized image: {0}'.format(e))


def gen(loading_frame,queue_key):
    start = False
    while True:
        if not start:
            if  queue_key in  image_queue_dict.keys():
                logging.info('qsize is {0}'.format(image_queue_dict[queue_key].qsize()))
                if image_queue_dict[queue_key].qsize() >= 1:
                    start = True
            yield (b'--frame\r\n'
                    b'Content-Type: image/png\r\n\r\n' + loading_frame + b'\r\n')

        elif not image_queue_dict[queue_key].empty():
            data = image_queue_dict[queue_key].get(block=False)
            yield (b'--frame\r\n'
            b'Content-Type: image/png\r\n\r\n' +  base64.b64decode(data['image']) + b'\r\n')

def read_image(filepath):
    return  open(filepath , 'rb').read()
