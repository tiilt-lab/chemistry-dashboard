from flask import Blueprint, request
import logging
import database
import json
from utility import json_response
import wrappers
from tables.speaker import Speaker
from tables.speaker_transcript_metrics import SpeakerTranscriptMetrics

api_routes = Blueprint('speaker', __name__)

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
