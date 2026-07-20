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
