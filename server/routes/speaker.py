from flask import Blueprint, request
import logging
import database
import json
from utility import json_response
import wrappers
from tables.speaker import Speaker

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
