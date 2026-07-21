from flask import Blueprint, request
import logging
import database
import json
from utility import json_response
import wrappers
from tables.speaker import Speaker
from tables.speaker_transcript_metrics import SpeakerTranscriptMetrics

api_routes = Blueprint('speaker', __name__)

# Create a speaker slot on a device after joining. Byod clients can join with
# a collaborator count of 0 ("detect automatically"), so the fingerprint
# screen needs a way to add slots; same open trust level as the rename route.
@api_routes.route('/api/v1/devices/<int:session_device_id>/speakers', methods=['GET', 'POST'])
def create_speaker(session_device_id, **kwargs):
    # GET: the pod's roster (used by the transcript speaker picker).
    if request.method == 'GET':
        speakers = database.get_speakers(session_device_id=session_device_id)
        return json_response([s.json() for s in speakers])
    alias = (request.json or {}).get('alias', '') or ''
    if alias:
        valid, message = Speaker.verify_fields(alias=alias)
        if not valid:
            return json_response({'message': message}, 400)
    speaker = database.create_speaker(session_device_id, alias)
    if speaker is None:
        return json_response({'message': 'Session device not found.'}, 404)
    return json_response(speaker.json())


@api_routes.route('/api/speakers/<int:speaker_id>', methods=['POST'])
def update_speaker(speaker_id, **kwargs):
    alias = request.json.get('alias', None)
    if alias:
        valid, message = Speaker.verify_fields(alias=alias)
        if not valid:
            return json_response({'message': message}, 400)
    speaker = database.update_speaker(speaker_id, alias)
    return json_response(speaker.json())


@api_routes.route('/api/v1/transcripts/<int:transcript_id>/speaker_metrics', methods=['GET'])
def get_transcript_speaker_metrics(transcript_id, **kwargs):
    speaker_metrics = database.get_speaker_transcript_metrics(transcript_id=transcript_id)
    return json_response([speaker_metric.json() for speaker_metric in speaker_metrics])


# Human correction of who a transcript segment is from ("this section is from
# X"). Signed-in users; the alias must be someone actually on that pod so a
# correction can't invent a speaker — UNLESS allow_guest is set, in which
# case an unlisted name (a TA, an instructor, a visitor who really did speak)
# is first added as a Speaker slot on the pod, so the roster stays the source
# of truth. With apply_to_tag, one confirmation relabels every segment
# sharing the current (often diarization-cluster) tag.
@api_routes.route('/api/v1/transcripts/<int:transcript_id>/reassign', methods=['POST'])
@wrappers.verify_login()
def reassign_transcript_speaker(transcript_id, **kwargs):
    body = request.json or {}
    alias = (body.get('alias') or '').strip()
    if not alias:
        return json_response({'message': 'An alias is required.'}, 400)
    valid, message = Speaker.verify_fields(alias=alias)
    if not valid:
        return json_response({'message': message}, 400)

    # scope check: the row must belong to a pod the caller can see, and the
    # alias must be a real roster member of that pod.
    from tables.transcript import Transcript
    from app import db
    row = db.session.query(Transcript).filter(Transcript.id == transcript_id).first()
    if row is None:
        return json_response({'message': 'Transcript not found.'}, 404)
    roster = {s.alias for s in database.get_speakers(
        session_device_id=row.session_device_id) if s.alias}
    if alias not in roster:
        if not body.get('allow_guest'):
            return json_response({
                'message': 'That name is not a participant in this group.'}, 400)
        speaker = database.create_speaker(row.session_device_id, alias)
        if speaker is None:
            return json_response({'message': 'Could not add the guest speaker.'}, 400)
        logging.info("guest speaker %s added to pod %s by %s",
                     alias, row.session_device_id,
                     kwargs.get('user', {}).get('email'))

    n, did = database.reassign_transcript_speaker(
        transcript_id, alias, apply_to_tag=bool(body.get('apply_to_tag')))
    logging.info("manual speaker reassign: transcript %s -> %s (%s rows) by %s",
                 transcript_id, alias, n, kwargs.get('user', {}).get('email'))
    return json_response({'reassigned': n, 'alias': alias,
                          'session_device_id': did})


# Human correction of WHAT was said. Signed-in users; updates the text (and
# word count / question flag) of one transcript row. The original ASR text is
# recorded once in voice_features.asr_text the first time a row is edited, so
# corrections never silently destroy the machine transcript.
@api_routes.route('/api/v1/transcripts/<int:transcript_id>/edit_text', methods=['POST'])
@wrappers.verify_login()
def edit_transcript_text(transcript_id, **kwargs):
    body = request.json or {}
    text = (body.get('transcript') or '').strip()
    if not text:
        return json_response({'message': 'Transcript text is required.'}, 400)
    if len(text) > 5000:
        return json_response({'message': 'Transcript text too long.'}, 400)
    ok = database.update_transcript_text(transcript_id, text)
    if not ok:
        return json_response({'message': 'Transcript not found.'}, 404)
    logging.info("manual transcript edit: row %s by %s", transcript_id,
                 kwargs.get('user', {}).get('email'))
    return json_response({'id': transcript_id, 'transcript': text})
