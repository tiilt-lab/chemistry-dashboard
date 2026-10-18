"""Negotiation coding per pod (negotiation_coding.py): start a run, read the
latest one with its codes and summary, re-assign teams, export CSV, set a
pod's breakout group and side (paired sessions), and the per-session
overview. Gated like the other per-pod routes: session write access to
start, re-assign or set the role, read access to look; the pod must belong
to the session in the URL (ids are sequential).

In a paired session (one device per team) the two pods of a breakout group
share one run: POST on either pod queues it for the pair, GET on either pod
returns it.

Two session-wide CSV exports: every group's coded transcript in one file
(export.csv) and every transcript row of every pod with what the coding
did with it (transcript.csv: coded, stitched into another line, dropped
and why, or never coded).
"""
import csv
import importlib
import io
import json

from flask import Blueprint, request, make_response, session as flask_session
from app import limiter, socketio
from utility import json_response, sanitize
from tables.session_device import SessionDevice
import authz
import database
import wrappers

# The engine, src/server/negotiation_coding.py. Loaded by name because a plain
# `import negotiation_coding` in a file of the same name reads as a self-import
# to the sibling-import sweep (tests/test_sibling_imports.py), although Python
# resolves it to the top-level module.
negotiation_coding = importlib.import_module('negotiation_coding')

api_routes = Blueprint('negotiation_coding', __name__)

POD = '/api/v1/sessions/<int:session_id>/devices/<int:session_device_id>/negotiation_coding'
CSV_BASE = ('transcript_id', 'start_time', 'length', 'speaker_tag', 'team', 'pod', 'text')
TRANSCRIPT_COLUMNS = ('group', 'pod', 'side', 'team', 'speaker_tag', 'named', 'far_side', 'closed_world', 'match_sim',
                      'transcript_id', 'start_time', 'clock', 'length', 'text', 'status', 'kept_as', 'run_id')


def _caller_key():
    # Per signed-in account (as the ticket route does), not per IP.
    return str((flask_session.get('user') or {}).get('id', 'anon'))


def _pod_or_404(session_device_id, session_id):
    if authz.device_in_session(session_device_id, session_id) is None:
        return json_response({'message': 'Does not exist.'}, 404)
    return None


def _teams_from_body(session_device_id):
    # Team names come from the session's pod setup.
    body = request.get_json(silent=True) or {}
    teams, error = negotiation_coding.validate_teams(
        body.get('teams'), negotiation_coding.device_team_names(session_device_id))
    if error:
        return None, json_response({'message': error}, 400)
    return teams, None


@api_routes.route(POD, methods=['POST'])
@wrappers.verify_login(public=True)
@limiter.limit("30 per hour", key_func=_caller_key)
@wrappers.verify_session_access
def start_negotiation_coding(session_id, session_device_id, **kwargs):
    missing = _pod_or_404(session_device_id, session_id)
    if missing:
        return missing
    teams, bad = _teams_from_body(session_device_id)
    if bad:
        return bad
    # Paired session: one run for the pod and its partner, hung off the
    # group's first device whichever pod the instructor clicked.
    first, partner = negotiation_coding.resolve_pair(session_device_id)
    run = negotiation_coding.queue_coding_run(session_id, first, teams, partner_device_id=partner)
    return json_response({'run_id': run.id, 'status': run.status, 'session_device_id': first,
                          'partner_device_id': partner}, 202)


@api_routes.route(POD, methods=['GET'])
@wrappers.verify_login(public=True)
@wrappers.verify_session_read_access
def get_negotiation_coding(session_id, session_device_id, **kwargs):
    missing = _pod_or_404(session_device_id, session_id)
    if missing:
        return missing
    run = database.get_latest_negotiation_run(session_device_id)
    if run is None:
        return json_response({'message': 'No negotiation coding run for this pod.'}, 404)
    return json_response(negotiation_coding.run_payload(run))


@api_routes.route(POD + '/teams', methods=['PUT'])
@wrappers.verify_login(public=True)
@wrappers.verify_session_access
def set_negotiation_teams(session_id, session_device_id, **kwargs):
    missing = _pod_or_404(session_device_id, session_id)
    if missing:
        return missing
    run = database.get_latest_negotiation_run(session_device_id)
    if run is None:
        return json_response({'message': 'No negotiation coding run for this pod.'}, 404)
    teams, bad = _teams_from_body(session_device_id)
    if bad:
        return bad
    # Stored codes re-rolled under the new teams; no LLM call.
    run = negotiation_coding.recompute_summary(run, teams)
    return json_response(negotiation_coding.run_payload(run))


@api_routes.route(POD + '/export.csv', methods=['GET'])
@wrappers.verify_login(public=True)
@wrappers.verify_session_read_access
def export_negotiation_coding(session_id, session_device_id, **kwargs):
    missing = _pod_or_404(session_device_id, session_id)
    if missing:
        return missing
    run = database.get_latest_negotiation_run(session_device_id)
    if run is None:
        return json_response({'message': 'No negotiation coding run for this pod.'}, 404)
    payload = negotiation_coding.run_payload(run)
    pod_names = {p['id']: p['name'] or 'Pod %s' % p['id'] for p in payload['pods']}
    dims = [d['key'] for d in payload['codebook']['dimensions']]
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(CSV_BASE + tuple(dims))
    for c in payload['codes']:
        values = [';'.join(c[d]) if isinstance(c.get(d), list) else (c.get(d) or '') for d in dims]
        writer.writerow([c['transcript_id'], c['start_time'], c['length'], c['speaker_tag'],
                         c['team'], pod_names.get(c['session_device_id'], ''), c['text']] + values)
    output = make_response(buf.getvalue().encode('utf-8'))
    output.headers['Content-Type'] = 'text/csv; charset=utf-8'
    output.headers['Content-Disposition'] = 'attachment; filename=negotiation_coding_session%d_pod%d.csv' % (
        session_id, session_device_id)
    return output


@api_routes.route(POD + '/role', methods=['PUT'])
@wrappers.verify_login(public=True)
@wrappers.verify_session_access
def set_negotiation_role(session_id, session_device_id, **kwargs):
    """Paired sessions: which breakout group this pod belongs to and which
    side of the table it records ({"group": "Table 3", "side": "<team>"}; blank
    clears). Fixes a mis-entered join; the next run picks it up."""
    missing = _pod_or_404(session_device_id, session_id)
    if missing:
        return missing
    body = request.get_json(silent=True) or {}
    ok, error, group, side = SessionDevice.verify_negotiation(sanitize(body.get('group') or '') or '',
                                                              body.get('side'),
                                                              negotiation_coding.device_team_names(session_device_id))
    if not ok:
        return json_response({'message': error}, 400)
    device = database.set_session_device_negotiation(session_device_id, group, side)
    if device is None:
        return json_response({'message': 'Does not exist.'}, 404)
    socketio.emit('device_update', json.dumps(device.json()), room=str(session_id), namespace='/session')
    first, partner = negotiation_coding.resolve_pair(session_device_id)
    return json_response({'session_device': device.json(), 'partner_device_id': partner,
                          'first_device_id': first})


def _latest_runs(session_id):
    """{device id: its newest run} for the session (a paired run on both of
    its pods)."""
    latest = {}
    for run in database.get_negotiation_runs(session_id):   # newest first
        for device_id in run.device_ids():
            latest.setdefault(device_id, run)
    return latest


def _csv_response(buf, filename):
    output = make_response(buf.getvalue().encode('utf-8'))
    output.headers['Content-Type'] = 'text/csv; charset=utf-8'
    output.headers['Content-Disposition'] = 'attachment; filename=%s' % filename
    return output


def _session_dims(session_id):
    import coding_schemes as coding_scheme
    session = database.get_sessions(id=session_id)
    codebook = negotiation_coding.codebook_for_session(session)
    return [d['key'] for d in coding_scheme.panel_json(codebook)['dimensions']]


@api_routes.route('/api/v1/sessions/<int:session_id>/negotiation_coding/export.csv', methods=['GET'])
@wrappers.verify_login(public=True)
@wrappers.verify_session_read_access
def export_session_negotiation_coding(session_id, **kwargs):
    """Every group's coded transcript in one CSV: the latest finished run of
    each pod, one row per coded utterance, groups in natural order and each
    in time order. Columns: negotiation_coding.EXPORT_COLUMNS then the
    scheme's dimensions."""
    dims = _session_dims(session_id)
    runs = {run.id: run for run in _latest_runs(session_id).values() if run.status == 'done'}
    rows = []
    for run in runs.values():
        payload = negotiation_coding.run_payload(run)
        pods = {p['id']: {'name': p['name'] or 'Pod %s' % p['id'], 'group': p['group'], 'side': p['side']}
                for p in payload['pods']}
        group = next((p['group'] for p in payload['pods'] if p['group']), None) or ''
        for c in payload['codes']:
            rows.append((negotiation_coding.group_sort_key(group), float(c['start_time'] or 0), c['transcript_id'],
                         negotiation_coding.export_row(c, pods, dims, run.id)))
    rows.sort(key=lambda r: r[:3])
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(negotiation_coding.EXPORT_COLUMNS + tuple(dims))
    for _g, _t, _i, row in rows:
        writer.writerow(row)
    return _csv_response(buf, 'negotiation_coding_session%d.csv' % session_id)


@api_routes.route('/api/v1/sessions/<int:session_id>/negotiation_coding/transcript.csv', methods=['GET'])
@wrappers.verify_login(public=True)
@wrappers.verify_session_read_access
def export_session_transcript(session_id, **kwargs):
    """Every transcript row of every pod, as recorded, with what the latest
    finished coding run did with it: ``status`` coded (its codes follow),
    stitched (joined into the line ``kept_as``), dropped:<reason> (a copy
    of ``kept_as``, a far-side hearing, a fragment, non-speech) or uncoded
    (no finished run, or left out after the run's record filled up). The
    audit trail for the merge of a group's two laptops."""
    dims = _session_dims(session_id)
    latest = _latest_runs(session_id)
    names = negotiation_coding._session_names(database.get_sessions(id=session_id))
    devices = database.get_session_devices(session_id=session_id)
    devices.sort(key=lambda d: (negotiation_coding.group_sort_key(getattr(d, 'negotiation_group', None)),
                                str(getattr(d, 'negotiation_side', None) or ''), d.id))
    # Per run: the fate of every transcript id it covered.
    fates = {}
    for run in {r.id: r for r in latest.values() if r.status == 'done'}.values():
        payload = negotiation_coding.run_payload(run)
        fate = {}
        for c in payload['codes']:
            fate[c['transcript_id']] = ('coded', None, c)
            for tid in c.get('stitched_from') or []:
                fate.setdefault(tid, ('stitched', c['transcript_id'], None))
        detail = ((payload.get('summary') or {}).get('cross_talk') or {}).get('detail') or []
        for d in detail:
            fate.setdefault(d['transcript_id'], ('dropped:%s' % d.get('reason', ''), d.get('kept_transcript_id'), None))
        fates[run.id] = fate
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(TRANSCRIPT_COLUMNS + tuple(dims))
    for device in devices:
        run = latest.get(device.id)
        fate = fates.get(run.id) if run is not None else None
        sides = negotiation_coding.run_sides(run, names) if run is not None else {}
        side = getattr(device, 'negotiation_side', None) or ''
        for t in database.get_transcripts(session_device_id=device.id):
            conf = negotiation_coding._attribution_confidence(t) or {}
            status, kept_as, code = (fate.get(t.id) if fate is not None else None) or ('uncoded', None, None)
            team = negotiation_coding.line_team(t, sides, run.teams_dict() if run is not None else None, names) \
                if run is not None else ''
            values = [';'.join(code[d]) if isinstance(code.get(d), list) else (code.get(d) or '') for d in dims] \
                if code else [''] * len(dims)
            writer.writerow([getattr(device, 'negotiation_group', None) or '', device.name or 'Pod %s' % device.id,
                             side, team, t.speaker_tag or '', 'yes' if t.speaker_tag else 'no',
                             'yes' if conf.get('far_side') else '', 'yes' if conf.get('closed_world') else '',
                             '' if conf.get('sim') is None else conf.get('sim'), t.id, t.start_time,
                             negotiation_coding.clock_text(t.start_time), t.length, t.transcript or '', status,
                             '' if kept_as is None else kept_as, run.id if run is not None else ''] + values)
    return _csv_response(buf, 'negotiation_transcript_session%d.csv' % session_id)


@api_routes.route('/api/v1/sessions/<int:session_id>/negotiation_coding', methods=['GET'])
@wrappers.verify_login(public=True)
@wrappers.verify_session_read_access
def list_negotiation_coding(session_id, **kwargs):
    # Every pod of the session with its latest run (no codes), run = null
    # where nothing was ever queued. A paired run shows on both of its pods.
    latest = _latest_runs(session_id)
    result = []
    for device in database.get_session_devices(session_id=session_id):
        run = latest.get(device.id)
        entry = {'device_id': device.id, 'device_name': device.name,
                 'negotiation_group': device.negotiation_group, 'negotiation_side': device.negotiation_side,
                 'run': None, 'mode': None, 'pods': [], 'teams': {}, 'summary': None}
        if run is not None:
            entry.update(negotiation_coding.run_payload(run, with_codes=False))
        result.append(entry)
    return json_response(result)
