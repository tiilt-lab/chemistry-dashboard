"""Attribution data-quality audit: per pod, how trustworthy are the speaker
labels? Drives the decision of which sessions need offline re-attribution
(raw _orig.wav recordings are retained) vs which are fine as-is.

Read-only. Reports, per ended session and pod:
  - speech seconds attributed vs unattributed (NULL speaker_tag)
  - roster vs how many roster members ever got attributed speech
  - enrollment quality of each roster member (the .check.json verdicts)
  - confusable voice pairs WITHIN the pod (same cosine check the Students
    page uses, but restricted to people actually sitting together)
  - whether the raw recording survives on disk for reprocessing
"""
import glob
import os

import numpy as np
from flask import Blueprint

import database
import wrappers
from utility import json_response
from routes.student import _enrollment_fields, _VOICE_DIR
from analytics import pairwise_voice_overlaps

api_routes = Blueprint('data_quality', __name__)

_RECORDINGS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'audio_processing', 'recordings')

CONFUSABLE_THRESHOLD = 0.50


def _voice_grade(fields):
    # Same three grades the Students page uses (weak / short / ok), computed
    # server-side from the enrollment sidecar.
    if not fields['voice_enrolled']:
        return 'missing'
    c = fields.get('voice_check')
    if not c:
        return 'unchecked'
    if (c.get('net_speech_seconds') or 0) < 5 or \
            (c.get('self_similarity') is not None and c['self_similarity'] < 0.45):
        return 'weak'
    if c.get('ok') is False:
        return 'short'
    return 'ok'


def _pod_report(device):
    from tables.transcript import Transcript
    from app import db
    from sqlalchemy.sql.expression import func

    did = device.id
    attributed, unattributed = 0.0, 0.0
    tags = {}
    for tag, sec in db.session.query(
            Transcript.speaker_tag, func.sum(Transcript.length)) \
            .filter(Transcript.session_device_id == did) \
            .group_by(Transcript.speaker_tag).all():
        if tag:
            tags[tag] = float(sec or 0)
            attributed += float(sec or 0)
        else:
            unattributed += float(sec or 0)
    total = attributed + unattributed

    roster = sorted({s.alias for s in device.speakers if s.alias})
    enrollment = {}
    embeddings = {}
    for alias in roster:
        fields = _enrollment_fields(alias)
        enrollment[alias] = _voice_grade(fields)
        emb_path = os.path.join(_VOICE_DIR, alias + '.emb.npy')
        if os.path.isfile(emb_path):
            try:
                embeddings[alias] = np.load(emb_path)
            except Exception:
                pass
    collisions = pairwise_voice_overlaps(embeddings,
                                         threshold=CONFUSABLE_THRESHOLD)

    wav = glob.glob(os.path.join(_RECORDINGS_DIR, '%d-*_orig.wav' % did))
    silent_roster = [a for a in roster if a not in tags]

    unattr_share = round(unattributed / total, 3) if total else None
    # Triage: is this pod's attribution trustworthy as-is?
    if total == 0:
        verdict = 'no_speech'
    elif (unattr_share or 0) > 0.5 or (roster and len(silent_roster) > len(roster) / 2):
        verdict = 'poor'
    elif (unattr_share or 0) > 0.2 or collisions or \
            any(g in ('weak', 'missing') for g in enrollment.values()):
        verdict = 'fair'
    else:
        verdict = 'good'

    return {
        'session_device_id': did,
        'group_name': device.name,
        'speech_seconds': round(total, 1),
        'attributed_seconds': round(attributed, 1),
        'unattributed_share': unattr_share,
        'roster_size': len(roster),
        'roster_with_speech': len([a for a in roster if a in tags]),
        'silent_roster': silent_roster,
        'tags_outside_roster': sorted(set(tags) - set(roster)),
        'enrollment': enrollment,
        'confusable_pairs': collisions,
        'raw_audio_retained': bool(wav),
        'verdict': verdict,
    }


@api_routes.route('/api/v1/data_quality', methods=['GET'])
@wrappers.verify_login(roles=['admin', 'super'])
def data_quality(**kwargs):
    sessions = [s for s in database.get_sessions()
                if s.end_date is not None]
    report = []
    for s in sessions:
        devices = database.get_session_devices(session_id=s.id) or []
        pods = [_pod_report(d) for d in devices]
        pods = [p for p in pods if p['verdict'] != 'no_speech']
        if not pods:
            continue
        report.append({
            'session_id': s.id,
            'session_name': s.name,
            'date': str(s.creation_date) + ' UTC',
            'pods': pods,
        })
    counts = {}
    for entry in report:
        for p in entry['pods']:
            counts[p['verdict']] = counts.get(p['verdict'], 0) + 1
    return json_response({'verdict_counts': counts, 'sessions': report})
