import os
import sys
import config
import requests
import logging

# Shared payloads + retry policy live in src/common/callbacks_common.py
# (same shim pattern as connection_manager.py / redis_helper.py).
_COMMON = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
import callbacks_common  # noqa: E402


def _callback_base():
    # .../api/v1/callback — derived from the transcript callback URL.
    return callbacks_common.callback_base(config.processing_callback())


def post_transcripts(source, start_time, end_time, transcript, doa, questions, keywords, features, topic_id, speaker_tag, speaker_id, voice_features=None):
    result = {
        'source': source,
        'start_time': start_time,
        'end_time': end_time
    }
    if voice_features:
        result['voice_features'] = voice_features
    if transcript:
        result['transcript'] = transcript
        result['questions'] = questions
    if doa:
        result['direction'] = doa
    if keywords:
        result['keywords'] = keywords
    if features:
        result['features'] = features
    if topic_id:
        result['topic_id'] = topic_id
    if speaker_tag:
        result['speaker_tag'] = speaker_tag
    if speaker_id:
        result['speaker_id'] = speaker_id
    try:
        response = requests.post(config.processing_callback(), json=result, timeout=callbacks_common.CALLBACK_TIMEOUT)
        transcript_id = response.json()['transcript_id'] if response.status_code == 200 else -1
        return response.status_code == 200, transcript_id
    except Exception as e:
        logging.warning('Transcript callback failed: {0}'.format(e))
        return False, -1


def post_posthoc_reset(source, scope):
    callbacks_common.post_posthoc_reset(_callback_base(), source, scope)


def post_posthoc_completed(source, models=None, scope='audio'):
    callbacks_common.post_posthoc_completed(_callback_base(), source, models, scope)


def post_service_restarted(scope='audio'):
    callbacks_common.post_service_restarted(_callback_base(), scope)


def post_tagging(source, tag, embeddingsFile):
    result = {
        'source': source,
        'tagging': tag,
        'embeddingsFile': embeddingsFile
    }
    return callbacks_common.post_json_ok(config.tagging_callback(), result, 'Tagging')


def post_connect(source):
    return callbacks_common.post_connect(config.connect_callback(), source)


def post_transcript_features(source, updates):
    # Persist re-scored E&T feature values onto existing transcript rows
    # (post-hoc style recomputation). `updates` = [{id, features:{...}}].
    payload = {'source': source, 'updates': updates}
    return callbacks_common.post_json_ok(_callback_base() + '/transcript_features',
                                         payload, 'transcript features')


def post_disconnect(source):
    return callbacks_common.post_disconnect(config.disconnect_callback(), source)


#Post speaker metrics with transcript data
def post_speaker_transcript_metrics(transcript_data, speakers, participation_scores, internal_cohesion, responsivity, social_impact, newness, communication_density):
    result = {
        'source': transcript_data['source'],
        'start_time': transcript_data['start_time'],
        'end_time': transcript_data['end_time'],
        'transcript': transcript_data['transcript'],
        'direction': transcript_data['doa'],
        'questions': transcript_data['questions'],
        'keywords': transcript_data['keywords'],
        'features': transcript_data['features'],
        'topic_id': transcript_data['topic_id'],
        'speaker_tag': transcript_data['speaker_tag'],
        'speaker_id':transcript_data['speaker_id'],
        # optional passthrough (e.g. {'contested': [aliases]} on overlap)
        'voice_features': transcript_data.get('voice_features'),
        'speakers':speakers,
        'participation_scores': participation_scores,
        'internal_cohesion': internal_cohesion,
        'responsivity': responsivity,
        'social_impact': social_impact,
        'newness': newness,
        'communication_density': communication_density
    }
    return callbacks_common.post_json_ok(config.speaker_metrics_callback(), result, 'Speaker Metrics')
