"""Unit tests for the pure analytics computations (no DB / Flask needed).

Run from src/server:  ../venv-unified/bin/python -m pytest tests/ -q
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analytics import (  # noqa: E402
    compute_conversation_dynamics,
    compute_joint_attention,
    gini_coefficient,
    on_task_pct,
)


def test_dynamics_basic_turns_and_transitions():
    # A,A,B,A -> 3 turns (A opens, B, A again); transitions A->B and B->A once.
    rows = [("A", 0, 5), ("A", 5, 3), ("B", 8, 2), ("A", 10, 4)]
    d = compute_conversation_dynamics(rows)
    assert d["total_turns"] == 3
    trans = {(t["from"], t["to"]): t["count"] for t in d["transitions"]}
    assert trans == {("A", "B"): 1, ("B", "A"): 1}
    a = next(s for s in d["speakers"] if s["name"] == "A")
    assert a["utterances"] == 3 and a["turns"] == 2
    assert a["speaking_seconds"] == 12  # 5+3+4


def test_dynamics_shares_sum_to_one():
    rows = [("A", 0, 6), ("B", 6, 2), ("C", 8, 2)]
    d = compute_conversation_dynamics(rows)
    assert d["total_speaking_seconds"] == 10
    assert abs(sum(s["share"] for s in d["speakers"]) - 1.0) < 1e-9
    # sorted most-talkative first
    assert d["speakers"][0]["name"] == "A"


def test_dynamics_empty():
    d = compute_conversation_dynamics([])
    assert d["total_turns"] == 0
    assert d["speakers"] == []
    assert d["gini"] == 0.0


def test_dynamics_handles_none_length():
    rows = [("A", 0, None), ("B", 1, None)]
    d = compute_conversation_dynamics(rows)
    assert d["total_turns"] == 2  # still two turns even with 0/None seconds


def test_gini_equal_is_zero():
    assert gini_coefficient([5, 5, 5, 5]) == 0.0


def test_gini_concentrated_is_high():
    # one person holds all the time -> close to (n-1)/n
    g = gini_coefficient([0, 0, 0, 100])
    assert g > 0.6


def test_gini_empty_and_zero():
    assert gini_coefficient([]) == 0.0
    assert gini_coefficient([0, 0, 0]) == 0.0


def test_on_task_pct():
    # person/laptop on-task, phone off-task, Nothing away
    vals = ["person", "laptop", "cell phone", "Nothing", "book"]
    assert on_task_pct(vals) == 60  # 3 of 5 on-task
    assert on_task_pct([]) is None
    assert on_task_pct(["cell phone", "Nothing"]) == 0


def test_joint_attention_basic():
    # t=0: A,B both on laptop (joint); t=1: A laptop, B book (not joint);
    # t=2: only A tracked (not a moment).
    rows = [
        ("A", 0, "laptop"), ("B", 0, "laptop"),
        ("A", 1, "laptop"), ("B", 1, "book"),
        ("A", 2, "laptop"),
    ]
    d = compute_joint_attention(rows)
    assert d["total_moments"] == 2
    assert d["joint_moments"] == 1
    assert d["joint_share"] == 0.5
    assert d["top_targets"][0] == {"target": "laptop", "moments": 1}
    assert d["pairs"] == [{"a": "A", "b": "B", "moments": 1}]


def test_joint_attention_idle_targets_not_joint():
    # Both idle ("Nothing") is a tracked moment but never joint attention.
    rows = [("A", 0, "Nothing"), ("B", 0, "Nothing")]
    d = compute_joint_attention(rows)
    assert d["total_moments"] == 1
    assert d["joint_moments"] == 0 and d["joint_share"] == 0.0


def test_joint_attention_peer_gaze_and_person_target():
    # A and B both look at person C: joint attention on C plus directed
    # peer-gaze edges A->C and B->C.
    rows = [("A", 0, "person:C"), ("B", 0, "person:C")]
    d = compute_joint_attention(rows)
    assert d["joint_moments"] == 1
    edges = {(e["from"], e["to"]): e["moments"] for e in d["peer_gaze"]}
    assert edges == {("A", "C"): 1, ("B", "C"): 1}


def test_joint_attention_timeline_buckets():
    rows = [
        ("A", 0, "laptop"), ("B", 0, "laptop"),
        ("A", 31, "book"), ("B", 31, "laptop"),
    ]
    d = compute_joint_attention(rows, bucket_seconds=30)
    assert d["timeline"] == [
        {"start": 0, "moments": 1, "joint": 1, "share": 1.0},
        {"start": 30, "moments": 1, "joint": 0, "share": 0.0},
    ]


def test_joint_attention_empty():
    d = compute_joint_attention([])
    assert d["empty"] is True and d["joint_share"] == 0.0
