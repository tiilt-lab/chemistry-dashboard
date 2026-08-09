# Consolidates all pods (session_device rows) from every session created on a
# given date into one target session. Transcripts, speakers, and all metric
# tables key off session_device_id, so they follow their pod automatically;
# the three report tables that carry a redundant session_id are re-pointed to
# match. Keywords belong to the session row itself and stay with the source
# sessions.
#
# Dry-run by default — prints the plan and touches nothing. Re-run with
# --apply to execute.
#
#   venv-unified/bin/python consolidate_sessions.py                  # dry run, today
#   venv-unified/bin/python consolidate_sessions.py --apply          # do it
#   venv-unified/bin/python consolidate_sessions.py --date 2026-08-06 --target 385 --apply

import argparse
from datetime import datetime, timedelta, timezone

from app import db, app
import database  # noqa: F401 -- imports every table module so all mappers resolve
from tables.session import Session
from tables.session_device import SessionDevice
from tables.llm_feedback_report import LLMFeedbackReport
from tables.llm_question_answer import LLMQuestionAnswer
from tables.session_synthesized_report import SessionSynthesizedReport


def main():
    parser = argparse.ArgumentParser(description='Merge all pods from one day into a single session.')
    parser.add_argument('--date', help='UTC day to consolidate (YYYY-MM-DD), default today')
    parser.add_argument('--target', type=int, help='session id to keep; default = earliest session of the day')
    parser.add_argument('--apply', action='store_true', help='execute (default is dry run)')
    args = parser.parse_args()

    day = datetime.strptime(args.date, '%Y-%m-%d') if args.date else datetime.now(timezone.utc).replace(tzinfo=None).replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day + timedelta(days=1)

    sessions = (Session.query
                .filter(Session.creation_date >= day, Session.creation_date < day_end)
                .order_by(Session.creation_date).all())
    if not sessions:
        print('No sessions created on {0:%Y-%m-%d} (UTC).'.format(day))
        return

    target = next((s for s in sessions if s.id == args.target), None) if args.target else sessions[0]
    if args.target and target is None:
        print('Target session {0} was not created on {1:%Y-%m-%d}; refusing.'.format(args.target, day))
        return

    print('Sessions of {0:%Y-%m-%d} (UTC):'.format(day))
    moves = []
    for s in sessions:
        pods = SessionDevice.query.filter_by(session_id=s.id).all()
        marker = ' <-- TARGET' if s.id == target.id else ''
        print('  [{0}] "{1}" created {2}, ended {3}, {4} pod(s){5}'.format(
            s.id, s.name, s.creation_date, s.end_date or 'still open', len(pods), marker))
        for p in pods:
            print('        pod {0} "{1}" (device {2})'.format(p.id, p.name, p.device_id))
            if s.id != target.id:
                moves.append((p, s))

    if not moves:
        print('Nothing to move — all pods already belong to session {0}.'.format(target.id))
        return

    # The (session_id, name) unique constraint means colliding pod names in the
    # target must be renamed on the way in.
    taken = {p.name for p in SessionDevice.query.filter_by(session_id=target.id).all()}
    print('\nPlan: move {0} pod(s) into session {1} "{2}"'.format(len(moves), target.id, target.name))
    for pod, src in moves:
        new_name = pod.name
        n = 2
        while new_name in taken:
            new_name = '{0} {1}'.format(pod.name, n)
            n += 1
        taken.add(new_name)
        rename = '' if new_name == pod.name else ' (renamed to "{0}")'.format(new_name)
        print('  pod {0} "{1}": session {2} -> {3}{4}'.format(pod.id, pod.name, src.id, target.id, rename))
        if args.apply:
            pod.name = new_name
            pod.session_id = target.id
            for model in (LLMFeedbackReport, LLMQuestionAnswer, SessionSynthesizedReport):
                model.query.filter_by(session_device_id=pod.id).update({'session_id': target.id})

    # Cover the whole day so every merged pod's activity fits the timeline.
    latest_end = max((s.end_date for s in sessions if s.end_date), default=None)
    if latest_end and (target.end_date is None or target.end_date < latest_end):
        print('Extending target end_date {0} -> {1}'.format(target.end_date, latest_end))
        if args.apply:
            target.end_date = latest_end

    if args.apply:
        db.session.commit()
        print('\nDone. Source sessions were left in place (now empty); their keyword lists stay with them.')
    else:
        print('\nDry run only — nothing written. Re-run with --apply to execute.')


if __name__ == '__main__':
    with app.app_context():
        main()
