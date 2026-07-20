"""Unit tests for the pure analytics functions (no DB, no Flask)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "server"))

from analytics import (  # noqa: E402
    compute_conversation_dynamics,
    compute_talk_metrics,
    classify_question,
    gini_coefficient,
)


ROWS = [
    # (speaker, start, length, question, transcript)
    ('A', 0, 8, False, 'Let me start us off with the plan.'),
    ('B', 9, 3, True, 'Why does the reaction slow down?'),
    ('A', 14, 10, False, 'Because the concentration drops over time.'),
    ('C', 22, 2, False, 'Right.'),          # overlaps A by 2s -> interruption
    ('A', 40, 6, False, 'Moving on after a pause.'),   # 16s silence before
    ('B', 47, 2, True, 'Is that correct?'),
    ('A', 120, 5, False, 'Wrapping up.'),   # 71s hanging gap after question
]


def test_talk_metrics_end_to_end():
    m = compute_talk_metrics(ROWS, enrolled=['A', 'B', 'C', 'D'])
    assert m['never_spoke'] == ['D']
    assert m['silences']['count'] == 2
    assert m['silences']['longest']['seconds'] == 71.0
    assert m['turn_taking']['interruptions'] == 1
    assert m['turn_taking']['interruptions_by'] == {'C': 1}
    assert m['questions']['total'] == 2
    assert m['questions']['open'] == 1
    assert m['questions']['closed'] == 1
    assert m['questions']['hanging'] == 1
    # timeline buckets conserve total speaking time
    total = sum(sum(b.values()) for b in m['timeline']['buckets'])
    assert abs(total - 36.0) < 0.5


def test_talk_metrics_empty():
    assert compute_talk_metrics([]) == {'empty': True}


def test_talk_metrics_unattributed_bucket():
    rows = [(None, 0, 5, False, 'hello there everyone')]
    m = compute_talk_metrics(rows)
    assert m['per_speaker'][0]['name'] == 'Unattributed'


def test_classify_question():
    assert classify_question('How would you explain this?') == 'open'
    assert classify_question('Why is the sky blue?') == 'open'
    assert classify_question('Did you finish?') == 'closed'
    assert classify_question('Is that correct?') == 'closed'
    assert classify_question('') == 'other'


def test_conversation_dynamics_shares_sum_to_one():
    d = compute_conversation_dynamics(
        [(t, s, l) for (t, s, l, _q, _x) in ROWS])
    assert abs(sum(s['share'] for s in d['speakers']) - 1.0) < 0.01
    assert d['total_turns'] >= len(d['speakers'])


def test_gini_bounds():
    assert gini_coefficient([]) == 0.0
    assert gini_coefficient([5, 5, 5]) == 0.0
    assert gini_coefficient([0, 0, 10]) > 0.6


def test_classify_question_edges():
    from analytics import classify_question
    # trailing context after the '?' must not confuse it
    assert classify_question("What if we tried X? Just a thought.") == "open"
    # capitalization + leading whitespace
    assert classify_question("   should we?") == "closed"
    # a statement with no question words
    assert classify_question("The reaction proceeds.") == "other"
    assert classify_question(None) == "other"


def test_live_alerts():
    from analytics import compute_live_alerts
    # dominated: A holds all recent talk; recent activity -> not silent
    a = compute_live_alerts(
        [('A', 0, 50, False), ('B', 60, 5, True), ('A', 120, 100, False),
         ('A', 250, 40, False)], session_now=300)
    assert a['silent'] is False
    assert a['dominated_by'] and a['dominated_by']['name'] == 'A'
    # hanging question: last utterance is a question, unanswered 38s
    h = compute_live_alerts([('A', 0, 50, False), ('B', 260, 2, True)],
                            session_now=300)
    assert h['hanging_question'] is True
    # silent: last activity long ago
    assert compute_live_alerts([('A', 0, 50, False)], session_now=300)['silent'] is True
    assert compute_live_alerts([], session_now=100)['silent'] is True


def test_speaker_alias_accepts_usernames():
    # Regression: usernames with . _ - were rejected, breaking add-speaker by
    # username + saved-fingerprint attach. Read NAME_CHARS from source (the
    # model needs a Flask/db context to import).
    import re, os
    src = os.path.join(os.path.dirname(__file__), "..", "src", "server",
                       "tables", "speaker.py")
    m = re.search(r'NAME_CHARS = (["\'])(.*?)\1', open(src).read())
    assert m, "NAME_CHARS not found"
    pat = r'^[{0}]+\Z'.format(m.group(2))
    for u in ['ainee.witt', 'i_orlyse', 'KalebC-21', 'domisky200', "O'Brien"]:
        assert re.search(pat, u), u
    for bad in ['drop;table', 'a<b', 'x/y']:
        assert not re.search(pat, bad), bad


def test_engagement_emotion_map_is_total():
    # Regression: 'angry' was missing from the facial_expression weights, so
    # any analysis window whose dominant facial emotion was angry KeyError'd
    # the synthesized-metrics computation and 500'd the reflection dashboard
    # for that pod. The map must cover the emotion model's labels and lookups
    # must be .get() so unknown future labels degrade instead of crash.
    import re, os
    src = open(os.path.join(os.path.dirname(__file__), "..", "src", "server",
                            "utility.py")).read()
    m = re.search(r"facial_expression = \{(.*?)\}", src)
    assert m, "facial_expression map not found"
    for label in ['serious', 'neutral', 'surprise', 'happy', 'sad', 'angry',
                  'fear', 'disgust']:
        assert "'%s'" % label in m.group(1), "missing emotion label: " + label
    assert "facial_expression[" not in src, \
        "bare indexing crashes on unknown emotion labels — use .get()"


def test_triage_session_now_is_timezone_independent():
    # Regression: get_session_triage feeds session_now into compute_live_alerts.
    # creation_date is stored naive-UTC (datetime.utcnow), so calling
    # .timestamp() on it treats it as LOCAL time and skews every silence/alert
    # threshold by the server's tz offset on any non-UTC host. The delta must be
    # a naive utcnow subtraction (source-level check; database.py needs a
    # Flask/db context to import).
    import re, os
    src = os.path.join(os.path.dirname(__file__), "..", "src", "server",
                       "database.py")
    body = open(src).read()
    m = re.search(r'def get_session_triage\(.*?\n(?=def )', body, re.DOTALL)
    assert m, "get_session_triage not found"
    # drop comment lines so the anti-pattern named in a comment doesn't trip us
    fn = "\n".join(l for l in m.group(0).splitlines()
                   if not l.lstrip().startswith("#"))
    assert "creation_date).total_seconds()" in fn, \
        "session_now must use naive utcnow - creation_date subtraction"
    assert "creation_date.timestamp()" not in fn, \
        "creation_date.timestamp() is tz-fragile on naive UTC datetimes"
