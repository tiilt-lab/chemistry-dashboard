"""Negotiation coding (src/server/negotiation_coding.py and its plumbing).

A Kellogg negotiation class (the "Viking" case, Pat's team vs Sandy's team)
wants every utterance of a pod's transcript coded on four dimensions by the
local llama-server, rolled up per team and per speaker, plus a de-escalation
timeline. Covered here:

  * the LLM contract (thinking disabled in the request AND /no_think in the
    prompt, temperature 0, codebook text, chunk/context boundaries, stable
    indices, retries);
  * parse and repair of the model's answer (prose, fences, truncation,
    unknown codes -> defaults counted as invalid_codes);
  * rollup and timeline on the 14-line synthetic exchange from the trial;
  * run_coding, the routes and persistence on the in-memory SQLite app stub
    (the pattern of test_api_phase1_ingest.py) with a fake LLM;
  * the post-hoc queue's "coding" leg (FakeRedis) and its idle rules;
  * the session flag, the end-of-session hook and the migration (source).
"""
import ast
import csv
import importlib.util
import io
import itertools
import json
import os
import re
import sys
import textwrap
import types

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
SERVER = os.path.join(SRC, "server")
sys.path.insert(0, SERVER)
sys.path.insert(0, os.path.join(SRC, "common"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

sys.modules.setdefault('posthoc_state', types.SimpleNamespace(is_running=lambda d: False))

import negotiation_coding as nc  # noqa: E402  (import-light: no Flask, no DB)
from fake_redis import FakeRedis  # noqa: E402
import redis_sync  # noqa: E402
import posthoc_queue as q  # noqa: E402

CODEBOOK = nc.load_codebook()
_seq = itertools.count(1)


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def _func_source(text, name):
    tree = ast.parse(text)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return textwrap.dedent(ast.get_source_segment(text, node))
    raise AssertionError("%s not found" % name)


# The 14-line synthetic Viking exchange from the trial, one line every 15 s,
# with the codes a human would give (the fake LLM answers with these).
VIKING = [
    ("Pat", "You went on vacation and left Alex in charge, and now the supplier is unpaid.",
     dict(emotion="neutral", rip="none", frame="past_blame", listening=[])),
    ("Sandy", "That's ridiculous. You're the one who signed off on the change order.",
     dict(emotion="escalating", rip="none", frame="past_blame", listening=[])),
    ("Pat", "Don't you understand that I need the money by Friday?",
     dict(emotion="escalating", rip="interest", frame="none", listening=["closed_question"])),
    ("Sandy", "If you force me into bankruptcy, you may not recover the money.",
     dict(emotion="escalating", rip="power", frame="none", listening=[])),
    ("Pat", "I can call the loan whenever I want.",
     dict(emotion="escalating", rip="power", frame="none", listening=[])),
    ("Sandy", "Can we slow this down for a minute?",
     dict(emotion="defusing", rip="none", frame="none", listening=["closed_question"])),
    ("Pat", "Fine. Tell me what is bothering you most.",
     dict(emotion="defusing", rip="none", frame="none", listening=["open_question"])),
    ("Sandy", "I need to avoid bankruptcy and keep the supplier on board.",
     dict(emotion="neutral", rip="interest", frame="none", listening=[])),
    ("Pat", "So your main concern is getting enough cash quickly for the lakefront property—is that right?",
     dict(emotion="neutral", rip="interest", frame="none", listening=["paraphrase", "check_understanding"])),
    ("Sandy", "Yes. The contract says changes must be in writing, but we both let that slide.",
     dict(emotion="neutral", rip="right", frame="none", listening=[])),
    ("Pat", "What has to happen in the next 15 days?",
     dict(emotion="neutral", rip="none", frame="future_problem_solving", listening=["open_question", "ask_constraint"])),
    ("Sandy", "Which of these three issues matters most to you?",
     dict(emotion="neutral", rip="none", frame="none", listening=["ask_priority", "open_question"])),
    ("Pat", "How can we structure this so you can make the investment and I can pay the supplier?",
     dict(emotion="neutral", rip="interest", frame="future_problem_solving", listening=["open_question"])),
    ("Sandy", "I can see why you're frustrated. Let's write up a schedule.",
     dict(emotion="defusing", rip="none", frame="future_problem_solving", listening=["acknowledge"])),
]
TEAMS = {"Pat": "Pat", "Sandy": "Sandy"}
VIKING_NAMES = ("Pat", "Sandy")   # the Viking case's sides, as a session's pod setup would name them
VIKING_SETUP_SINGLE = {"group_size": 6, "teams": [{"name": "Pat", "size": 3}, {"name": "Sandy", "size": 3}],
                       "devices_per_group": "group", "groups": []}


def _utterances(n=None):
    lines = VIKING if n is None else [VIKING[i % len(VIKING)] for i in range(n)]
    return [{"index": i, "transcript_id": 100 + i, "start_time": 15 * i, "length": 10,
             "speaker_tag": tag, "text": text} for i, (tag, text, _) in enumerate(lines)]


def _gold_codes():
    return [dict(u, **VIKING[u["index"]][2]) for u in _utterances()]


def _code_indices(messages):
    # The indices the prompt asks to code, read off its CODE section.
    user = messages[-1]["content"]
    code_part = user[user.index("CODE ("):]
    return [int(m) for m in re.findall(r"^\[(\d+)\]", code_part, re.M)]


def gold_llm(messages):
    """Answers with the fixture's codes for exactly the indices asked."""
    return json.dumps([dict(i=i, **VIKING[i % len(VIKING)][2]) for i in _code_indices(messages)])


# ------------------------------------------------------------ codebook

def test_codebook_is_viking_v2_with_the_four_dimensions_and_examples():
    assert CODEBOOK["version"] == "viking-v2"
    dims = CODEBOOK["dimensions"]
    assert list(dims) == ["emotion", "rip", "frame", "listening"]
    assert set(dims["emotion"]["codes"]) == {"escalating", "defusing", "neutral"}
    assert set(dims["rip"]["codes"]) == {"interest", "right", "power", "none"}
    assert set(dims["frame"]["codes"]) == {"past_blame", "future_problem_solving", "none"}
    assert set(dims["listening"]["codes"]) == {
        "open_question", "closed_question", "paraphrase", "summarize", "acknowledge",
        "check_understanding", "ask_why", "ask_priority", "ask_constraint", "interrupt"}
    assert dims["listening"]["multi"] is True and dims["listening"]["default"] == []
    assert (dims["emotion"]["default"], dims["rip"]["default"], dims["frame"]["default"]) == ("neutral", "none", "none")
    assert "That's ridiculous." in dims["emotion"]["codes"]["escalating"]["examples"]
    assert "I can call the loan." in dims["rip"]["codes"]["power"]["examples"]
    assert "What has to happen in the next 15 days?" in dims["frame"]["codes"]["future_problem_solving"]["examples"]
    assert "Don't you understand that I need the money?" in dims["listening"]["notes"]["weak"]


def test_codebook_carries_wangs_definitions_and_the_case_facts():
    facts = "\n".join(CODEBOOK["case_facts"])
    for fact in ("developer and landlord", "carpentry", "$1.4M", "15 days", "$200K", "lakefront", "hotel",
                 "Fawn", "Alex", "based on past practice", "changes must be in writing", "first 10 minutes"):
        assert fact in facts
    rip = CODEBOOK["dimensions"]["rip"]
    assert "coerce and harm the other side's interests" in rip["codes"]["power"]["definition"]
    assert "raised voices, insults, table pounding" in rip["codes"]["power"]["definition"]
    assert "If you do not ____, then I will ____." in rip["codes"]["power"]["definition"]
    assert "Independent standards with perceived legitimacy or fairness: contracts, legal rights, precedent, norms" \
        in rip["codes"]["right"]["definition"]
    assert "Needs, desires, concerns, motivations, priorities: WHY someone wants what they want" in rip["codes"]["interest"]["definition"]
    emotion = CODEBOOK["dimensions"]["emotion"]
    for irritator in ("telling the other side what to do", "'unfair', 'unreasonable'", "intentional violations", "blaming",
                      "large demands", "without a counterpoint", "interrupting", "raised intensity"):
        assert irritator in emotion["codes"]["escalating"]["definition"], irritator
    defusing = emotion["codes"]["defusing"]
    assert "I can see that you're angry, and I'm sorry we're in this situation. Tell me what's on your mind." in defusing["examples"]
    assert "What do you want going forward?" in defusing["examples"]
    assert "What would help to put this behind us?" in defusing["examples"]
    assert "taking a break" in defusing["definition"]
    assert "'Calm down' is NOT defusing" in emotion["guidance"]
    listening = CODEBOOK["dimensions"]["listening"]
    for move in ("not interrupting", "'Tell me more'", "'Help me understand'", "paraphrasing", "summing up", "offering solutions"):
        assert move in listening["guidance"], move
    assert len(listening["conventions"]) == 4


# -------------------------------------------------------------- prompt

def test_prompt_carries_the_codebook_the_context_and_ends_with_no_think():
    us = _utterances()
    messages = nc.build_prompt(CODEBOOK, us[5:8], us[:5])
    assert [m["role"] for m in messages] == ["system", "user"]
    system, user = messages[0]["content"], messages[1]["content"]
    for code in ("escalating", "defusing", "interest", "right", "power", "past_blame",
                 "future_problem_solving", "check_understanding", "interrupt"):
        assert code in system
    assert "That's ridiculous." in system and "I can call the loan." in system
    assert "Which of these three issues matters most to you?" in system
    assert "JSON array" in system and '"i"' in system
    assert system.index("CONTEXT FACTS") < system.index("$1.4M") < system.index("emotion (exactly one code)")
    assert "Team A's team versus Team B's team" in system and "4 dimensions" in system
    assert '"emotion": "<code>"' in system and '"listening": ["<code>", ...]' in system
    assert "- Fawn" not in system and "Fawn (some materials call this person Alex" in system
    assert "* Every question gets its form label" in system and "'Calm down' is NOT defusing" in system
    assert "(examples of strong listening moves, not codes:" in system
    assert user.rstrip().endswith("/no_think")
    assert user.index("CONTEXT") < user.index("CODE (")
    context_part = user[user.index("CONTEXT"):user.index("CODE (")]
    assert [int(m) for m in re.findall(r"^\[(\d+)\]", context_part, re.M)] == [0, 1, 2, 3, 4]
    assert _code_indices(messages) == [5, 6, 7]
    assert "[5] Sandy: Can we slow this down for a minute?" in user


def test_first_chunk_has_no_context_section():
    user = nc.build_prompt(CODEBOOK, _utterances()[:3], [])[1]["content"]
    assert "CONTEXT" not in user and user.startswith("CODE (")


def test_chunks_are_40_with_5_read_only_predecessors_and_global_indices():
    us = _utterances(100)
    parts = list(nc.chunks(us))
    assert [len(c) for _, c in parts] == [40, 40, 20]
    assert [len(ctx) for ctx, _ in parts] == [0, 5, 5]
    assert [u["index"] for u in parts[1][0]] == [35, 36, 37, 38, 39]
    assert parts[1][1][0]["index"] == 40 and parts[2][1][-1]["index"] == 99
    seen = []
    coded, invalid = nc.code_utterances(CODEBOOK, us, lambda m: seen.append(_code_indices(m)) or gold_llm(m))
    assert seen == [list(range(0, 40)), list(range(40, 80)), list(range(80, 100))]
    assert [c["index"] for c in coded] == list(range(100)) and invalid == 0
    assert coded[42]["transcript_id"] == 142 and coded[42]["emotion"] == VIKING[42 % 14][2]["emotion"]


class _Response:
    def __init__(self, content):
        self.body = json.dumps({"choices": [{"message": {"content": content}}]}).encode()

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_call_llm_request_disables_thinking_at_temperature_0(monkeypatch):
    calls = []

    def urlopen(req, timeout=None):
        calls.append((req, timeout))
        return _Response("[]")

    monkeypatch.setattr(nc.urllib.request, "urlopen", urlopen)
    monkeypatch.delenv("NEGOTIATION_LLM_URL", raising=False)
    monkeypatch.delenv("NEGOTIATION_LLM_MODEL", raising=False)
    messages = nc.build_prompt(CODEBOOK, _utterances()[:2], [])
    assert nc.call_llm(messages) == "[]"
    req, timeout = calls[0]
    body = json.loads(req.data.decode())
    assert req.full_url == "http://127.0.0.1:8080/v1/chat/completions"
    assert req.get_method() == "POST" and req.get_header("Content-type") == "application/json"
    assert timeout == 300
    assert body["model"] == "qwen3.8-27b-uncensored"
    assert body["temperature"] == 0
    assert body["chat_template_kwargs"] == {"enable_thinking": False}
    assert body["messages"][-1]["content"].rstrip().endswith("/no_think")
    assert body["messages"] == messages


def test_call_llm_honours_the_env_overrides(monkeypatch):
    seen = {}
    monkeypatch.setattr(nc.urllib.request, "urlopen",
                        lambda req, timeout=None: seen.update(url=req.full_url, body=json.loads(req.data)) or _Response("x"))
    monkeypatch.setenv("NEGOTIATION_LLM_URL", "http://10.0.0.9:9999/v1/chat/completions")
    monkeypatch.setenv("NEGOTIATION_LLM_MODEL", "other-model")
    nc.call_llm([{"role": "user", "content": "hi /no_think"}])
    assert seen["url"] == "http://10.0.0.9:9999/v1/chat/completions" and seen["body"]["model"] == "other-model"


def test_call_llm_retries_twice_then_gives_up(monkeypatch):
    attempts = []
    monkeypatch.setattr(nc.time, "sleep", lambda s: attempts.append(("sleep", s)))

    def flaky(req, timeout=None):
        attempts.append("call")
        if attempts.count("call") < 3:
            raise nc.urllib.error.URLError("connection refused")
        return _Response("ok")

    monkeypatch.setattr(nc.urllib.request, "urlopen", flaky)
    assert nc.call_llm([]) == "ok"
    assert attempts == ["call", ("sleep", 2), "call", ("sleep", 4), "call"]

    attempts.clear()

    def down(req, timeout=None):
        attempts.append("call")
        raise OSError("timed out")

    monkeypatch.setattr(nc.urllib.request, "urlopen", down)
    with pytest.raises(RuntimeError, match="after 3 attempt"):
        nc.call_llm([])
    assert attempts.count("call") == 3


# ------------------------------------------------------ parse and repair

GOOD = [{"i": 0, "emotion": "escalating", "rip": "power", "frame": "past_blame", "listening": ["interrupt"]},
        {"i": 1, "emotion": "defusing", "rip": "none", "frame": "none", "listening": []}]


def test_extract_array_takes_the_outermost_array_through_prose_and_fences():
    assert nc.extract_array(json.dumps(GOOD)) == GOOD
    wrapped = "Sure! Here are the codes [as requested]:\n```json\n%s\n```\nLet me know." % json.dumps(GOOD, indent=1)
    assert nc.extract_array(wrapped) == GOOD
    assert nc.extract_array("no json here") == []
    assert nc.extract_array("") == []


def test_truncated_answer_keeps_the_whole_objects_and_defaults_the_rest():
    text = json.dumps(GOOD)[:-25]          # cut inside the second object
    items = nc.extract_array(text)
    assert items == GOOD[:1]
    by_index, invalid = nc.validate_codes(items, CODEBOOK, [0, 1])
    assert by_index[0] == {"emotion": "escalating", "rip": "power", "frame": "past_blame", "listening": ["interrupt"]}
    assert by_index[1] == {"emotion": "neutral", "rip": "none", "frame": "none", "listening": []}
    assert invalid == 1                     # one skipped utterance


def test_unknown_codes_are_coerced_and_counted():
    items = [{"i": 0, "emotion": "Angry", "rip": "leverage", "frame": "blame",
              "listening": ["nod", "Open Question", "open_question", 7]}]
    by_index, invalid = nc.validate_codes(items, CODEBOOK, [0])
    assert by_index[0] == {"emotion": "neutral", "rip": "none", "frame": "none", "listening": ["open_question"]}
    assert invalid == 5                     # angry, leverage, blame, nod, 7
    # a bare string for the multi dimension is tolerated; a number is not
    assert nc.validate_codes([{"i": 0, "emotion": "Defusing", "rip": "Interest", "frame": "Past-Blame",
                               "listening": "acknowledge"}], CODEBOOK, [0]) == \
        ({0: {"emotion": "defusing", "rip": "interest", "frame": "past_blame", "listening": ["acknowledge"]}}, 0)
    assert nc.validate_codes([{"i": 0, "emotion": "neutral", "rip": "none", "frame": "none", "listening": 3}],
                             CODEBOOK, [0])[1] == 1


def test_index_key_variants_and_foreign_indices():
    items = [{"index": "1", "emotion": "defusing", "rip": "none", "frame": "none", "listening": []},
             {"i": 9, "emotion": "escalating", "rip": "none", "frame": "none", "listening": []},
             "garbage", {"i": "x"}]
    by_index, invalid = nc.validate_codes(items, CODEBOOK, [0, 1])
    assert by_index[1]["emotion"] == "defusing" and by_index[0]["emotion"] == "neutral"
    assert invalid == 1 and 9 not in by_index


def test_code_utterances_fails_loudly_on_an_unparseable_chunk():
    with pytest.raises(RuntimeError, match="no parseable codes for utterances 0-13"):
        nc.code_utterances(CODEBOOK, _utterances(), lambda m: "I cannot do that.")


# --------------------------------------------------- rollup and timeline

def test_rollup_counts_every_code_per_team_and_speaker():
    r = nc.rollup(_gold_codes(), TEAMS, CODEBOOK, VIKING_NAMES)
    assert set(r["by_team"]) == {"Pat", "Sandy", "unassigned"}
    pat, sandy, none = r["by_team"]["Pat"], r["by_team"]["Sandy"], r["by_team"]["unassigned"]
    assert (pat["utterances"], sandy["utterances"], none["utterances"]) == (7, 7, 0)
    assert pat["emotion"] == {"escalating": 2, "defusing": 1, "neutral": 4}
    assert sandy["emotion"] == {"escalating": 2, "defusing": 2, "neutral": 3}
    assert pat["rip"] == {"interest": 3, "right": 0, "power": 1, "none": 3}
    assert sandy["rip"] == {"interest": 1, "right": 1, "power": 1, "none": 4}
    assert pat["frame"] == {"past_blame": 1, "future_problem_solving": 2, "none": 4}
    assert pat["listening"]["open_question"] == 3 and pat["listening"]["check_understanding"] == 1
    assert sandy["listening"]["ask_priority"] == 1 and sandy["listening"]["summarize"] == 0
    assert set(pat["listening"]) == set(CODEBOOK["dimensions"]["listening"]["codes"])
    assert r["by_speaker"]["Pat"]["team"] == "Pat" and r["by_speaker"]["Sandy"]["team"] == "Sandy"
    assert r["by_speaker"]["Pat"]["emotion"] == pat["emotion"]


def test_unassigned_speakers_roll_into_unassigned():
    r = nc.rollup(_gold_codes(), {"Pat": "Pat"}, CODEBOOK, VIKING_NAMES)
    assert r["by_team"]["Sandy"]["utterances"] == 0
    assert r["by_team"]["unassigned"]["utterances"] == 7
    assert r["by_speaker"]["Sandy"]["team"] == "unassigned"
    assert nc.rollup([], None, CODEBOOK, VIKING_NAMES)["by_team"]["Pat"]["utterances"] == 0
    assert set(nc.rollup([], None, CODEBOOK)["by_team"]) == {"Team A", "Team B", "unassigned"}   # placeholder names


def test_timeline_landmarks_on_the_fixture():
    t = nc.timeline(_gold_codes())
    assert t == {"first_escalating": 15, "peak_escalation_window_start": 15, "peak_escalation_count": 4,
                 "first_sustained_deescalation": 75, "first_future_move": 150}
    calm = [dict(c, emotion="neutral") for c in _gold_codes()]
    assert nc.timeline(calm)["first_escalating"] is None
    assert nc.timeline(calm)["first_sustained_deescalation"] is None
    assert nc.timeline(calm)["peak_escalation_count"] == 0
    # escalation recurring inside the window pushes the calm start past it;
    # a flare-up long after the first calm window does not move it
    recur = [dict(c, emotion="escalating" if c["index"] in (1, 7) else "neutral") for c in _gold_codes()]
    assert nc.timeline(recur)["first_sustained_deescalation"] == 120
    late = [dict(c, emotion="escalating" if c["index"] in (1, 12) else "neutral") for c in _gold_codes()]
    assert nc.timeline(late)["first_sustained_deescalation"] == 30
    assert nc.timeline(late)["peak_escalation_window_start"] == 15


def test_summarize_has_the_three_sections():
    s = nc.summarize(_gold_codes(), TEAMS, CODEBOOK, names=VIKING_NAMES)
    assert set(s) == {"by_team", "by_speaker", "timeline"}


def test_team_dynamics_answer_the_debrief_questions():
    dyn = nc.team_dynamics(_gold_codes(), TEAMS, VIKING_NAMES)
    assert dyn["Pat"] == {"opening_move": "interest", "rip_sequence": ["interest", "power", "interest"],
                          "last_escalating": 60, "first_interest_question": 30}
    # Sandy's first three minutes: one power, one interest, one right -> the one reached for first
    assert dyn["Sandy"] == {"opening_move": "power", "rip_sequence": ["power", "interest", "right"],
                            "last_escalating": 45, "first_interest_question": None}
    assert dyn["unassigned"] == {"opening_move": "none", "rip_sequence": [], "last_escalating": None,
                                 "first_interest_question": None}
    assert nc.team_dynamics([], TEAMS, VIKING_NAMES)["Pat"]["opening_move"] == "none"
    s = nc.summarize(_gold_codes(), TEAMS, CODEBOOK, names=VIKING_NAMES)
    assert s["by_team"]["Sandy"]["opening_move"] == "power" and s["by_team"]["Pat"]["last_escalating"] == 60
    assert "opening_move" not in s["by_speaker"]["Pat"]


def test_validate_teams():
    assert nc.validate_teams(None, VIKING_NAMES) == ({}, None)
    assert nc.validate_teams({"A": "pat", "B": "SANDY", "C": None, "D": ""}, VIKING_NAMES) == ({"A": "Pat", "B": "Sandy"}, None)
    assert nc.validate_teams({"A": "Coach"}, VIKING_NAMES)[0] is None
    assert nc.validate_teams(["Pat"], VIKING_NAMES)[0] is None
    assert nc.validate_teams({"A": "Pat"})[1] == "team for speaker 'A' must be Team A or Team B."   # no setup: placeholders
    assert nc.team_of("A", {"A": "Pat"}, VIKING_NAMES) == "Pat" and nc.team_of("B", {"A": "Pat"}, VIKING_NAMES) == "unassigned"


# ------------------------------------- run_coding, routes and persistence

flask = pytest.importorskip("flask")
flask_sqlalchemy = pytest.importorskip("flask_sqlalchemy")


class _Recorder:
    def __init__(self, result=None):
        self.calls = []
        self.result = result

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.result


def _stub_module(name, **attrs):
    module = types.ModuleType(name)
    module._phase1_stub = True
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _ours(module):
    path = getattr(module, "__file__", None) or ""
    return getattr(module, "_phase1_stub", False) or os.path.abspath(path).startswith(SRC)


@pytest.fixture(scope="module")
def env():
    loaded = sys.modules.get("app")
    if loaded is not None and not getattr(loaded, "_phase1_stub", False):
        pytest.skip("the real app module is loaded in this process")
    before = dict(sys.modules)

    flask_app = flask.Flask("negotiation")
    flask_app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
    flask_app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app_stub = _stub_module(
        "app", app=flask_app, db=flask_sqlalchemy.SQLAlchemy(flask_app),
        limiter=types.SimpleNamespace(limit=lambda *a, **k: (lambda f: f)),
        socketio=types.SimpleNamespace(emit=_Recorder()))
    identity = lambda f: f  # noqa: E731
    _stub_module("wrappers", verify_login=lambda public=False: identity,
                 verify_session_access=identity, verify_session_read_access=identity,
                 ADMIN_ROLES=("admin", "super"))
    _stub_module("config")
    enqueue_coding = _Recorder(True)
    _stub_module("posthoc_queue", enqueue_coding=enqueue_coding)

    for name in ("database", "negotiation_coding"):
        sys.modules.pop(name, None)  # rebound to the stub app below
    import database  # noqa: E402
    import authz
    authz.configure(authz.Deps(get_device=lambda did: database.get_session_devices(id=did),
                               get_transcript=database.get_transcript,
                               session_access=lambda sid, user, write: True,
                               key_grants=lambda device: False))
    spec = importlib.util.spec_from_file_location(
        "negotiation_routes", os.path.join(SERVER, "routes", "negotiation_coding.py"))
    routes = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(routes)
    spec2 = importlib.util.spec_from_file_location(
        "coding_scheme_routes", os.path.join(SERVER, "routes", "coding_scheme.py"))
    scheme_routes = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(scheme_routes)
    engine = sys.modules["negotiation_coding"]

    ctx = flask_app.app_context()
    ctx.push()
    tables = [t for t in app_stub.db.metadata.sorted_tables
              if not any(type(c.type).__module__.startswith("sqlalchemy.dialects.mysql") for c in t.columns)]
    app_stub.db.metadata.create_all(app_stub.db.engine, tables=tables)
    yield types.SimpleNamespace(database=database, routes=routes, scheme_routes=scheme_routes, engine=engine,
                                flask_app=flask_app, db=app_stub.db, enqueue_coding=enqueue_coding)
    app_stub.db.session.remove()
    ctx.pop()
    for name, module in list(sys.modules.items()):
        if name not in before and _ours(module):
            del sys.modules[name]
    for name, module in before.items():
        if sys.modules.get(name) is not module and _ours(sys.modules.get(name, module)):
            sys.modules[name] = module


def _session(env):
    from tables.session import Session
    from tables.user import User
    n = next(_seq)
    user = User("nego-%d@example.org" % n, "user", password="Abcdef1!")
    env.db.session.add(user)
    env.db.session.flush()
    session = Session(user.id, "S%d" % n)
    # Every test session names its sides through the pod setup, as a real
    # negotiation session does (nothing in the code knows Pat and Sandy).
    session.pod_config = json.dumps(VIKING_SETUP_SINGLE)
    env.db.session.add(session)
    env.db.session.commit()
    return session


def _pod(env, session, with_transcripts=True):
    from tables.session_device import SessionDevice
    device = SessionDevice(session.id, None, "Pod %d" % next(_seq))
    env.db.session.add(device)
    env.db.session.flush()
    device.create_key()
    env.db.session.commit()
    if with_transcripts:
        for i, (tag, text, _) in enumerate(VIKING):
            env.database.add_transcript(device.id, 15 * i, 10, text, False, 0, 0, 0, 0, 0, 0, -1, tag, -1)
    return device


@pytest.fixture
def pod(env):
    return _pod(env, _session(env))


def _call(env, view, method, json_body=None, **kwargs):
    with env.flask_app.test_request_context("/api/v1/x", method=method, json=json_body):
        return view(**kwargs)


def test_run_coding_persists_codes_and_summary(env, pod):
    from tables.negotiation_code import NegotiationCode
    calls = []
    run = env.engine.run_coding(pod.id, TEAMS, llm=lambda m: calls.append(m) or gold_llm(m))
    assert len(calls) == 1
    assert run.status == "done" and run.error is None
    assert run.started_at is not None and run.finished_at >= run.started_at
    assert (run.utterances_coded, run.invalid_codes) == (14, 0)
    assert run.model == "qwen3.8-27b-uncensored" and run.codebook_version == "viking-v2"
    rows = env.db.session.query(NegotiationCode).filter_by(run_id=run.id).all()
    assert len(rows) == 14
    transcripts = env.database.get_transcripts(session_device_id=pod.id)
    assert {r.transcript_id for r in rows} == {t.id for t in transcripts}
    summary = run.summary_dict()
    assert summary["by_team"]["Pat"]["utterances"] == 7
    assert summary["timeline"]["first_escalating"] == 15
    assert run.teams_dict() == TEAMS
    assert run.json()["created_at"].endswith(" UTC") and run.json()["status"] == "done"


def test_run_coding_marks_the_run_error_and_reraises(env, pod):
    def broken(messages):
        raise RuntimeError("llama-server down")

    with pytest.raises(RuntimeError, match="llama-server down"):
        env.engine.run_coding(pod.id, TEAMS, llm=broken)
    run = env.database.get_latest_negotiation_run(pod.id)
    assert run.status == "error" and "llama-server down" in run.error and run.finished_at is not None
    with pytest.raises(RuntimeError, match="does not exist"):
        env.engine.run_coding(pod.id, TEAMS, llm=gold_llm, run_id=999999)


def test_run_coding_reports_to_the_given_run_and_reads_its_latest_teams(env, pod):
    d = env.database
    run = d.create_negotiation_run(pod.id, "m", "viking-v2", {"Pat": "Pat"})
    d.add_negotiation_codes(run.id, [])  # nothing yet

    def llm(messages):
        # a PUT /teams while the model is busy: the summary must use it
        d.update_negotiation_run(run.id, teams=TEAMS)
        return gold_llm(messages)

    out = env.engine.run_coding(pod.id, llm=llm, run_id=run.id)
    assert out.id == run.id and out.status == "done"
    assert out.summary_dict()["by_team"]["Sandy"]["utterances"] == 7
    # a second attempt (coordinator restart re-queues the job) replaces, not doubles
    env.engine.run_coding(pod.id, llm=gold_llm, run_id=run.id)
    assert len(d.get_negotiation_codes(run.id)) == 14
    assert d.get_latest_negotiation_run(pod.id).id == run.id


def test_routes_post_get_put_export_and_session_list(env):
    d, r, session = env.database, env.routes, _session(env)
    pod = _pod(env, session)
    empty = _pod(env, session, with_transcripts=False)
    stranger = _pod(env, _session(env))
    ids = dict(session_id=session.id, session_device_id=pod.id)

    assert _call(env, r.get_negotiation_coding, "GET", **ids).status_code == 404
    assert _call(env, r.start_negotiation_coding, "POST", {}, session_id=session.id,
                 session_device_id=stranger.id).status_code == 404
    assert _call(env, r.start_negotiation_coding, "POST", {"teams": {"Pat": "Coach"}}, **ids).status_code == 400

    env.enqueue_coding.calls.clear()
    resp = _call(env, r.start_negotiation_coding, "POST", {"teams": {"Pat": "Pat"}}, **ids)
    assert resp.status_code == 202
    body = resp.get_json()
    assert body["status"] == "queued" and isinstance(body["run_id"], int)
    assert env.enqueue_coding.calls == [((session.id, pod.id, body["run_id"]), {})]
    # queued again with new teams: the same run, teams updated, no second row
    resp2 = _call(env, r.start_negotiation_coding, "POST", {"teams": TEAMS}, **ids)
    assert resp2.get_json()["run_id"] == body["run_id"]
    assert d.get_latest_negotiation_run(pod.id).teams_dict() == TEAMS
    assert len(d.get_negotiation_runs(session.id)) == 1
    assert len(env.enqueue_coding.calls) == 2

    # GET while queued: the run, no codes, no summary
    payload = _call(env, r.get_negotiation_coding, "GET", **ids).get_json()
    assert payload["run"]["status"] == "queued" and payload["codes"] == [] and payload["summary"] is None

    # the coding leg runs
    env.engine.run_coding(pod.id, llm=gold_llm, run_id=body["run_id"])
    payload = _call(env, r.get_negotiation_coding, "GET", **ids).get_json()
    assert set(payload) == {"run", "mode", "codebook", "team_names", "pods", "teams", "codes", "summary"}
    assert payload["team_names"] == ["Pat", "Sandy"]
    assert payload["codebook"]["ref"] == "builtin:negotiation"
    assert [d["key"] for d in payload["codebook"]["dimensions"]] == ["emotion", "rip", "frame", "listening"]
    assert payload["codebook"]["dimensions"][1]["label"] == "Interests, rights, power"
    assert payload["codebook"]["dimensions"][3]["multi"] is True
    assert payload["codebook"]["analytics"] == {"timeline": True, "future_move": True, "dynamics": True}
    assert set(payload["run"]) == {"id", "session_device_id", "partner_device_id", "status", "model",
                                   "codebook_version", "created_at", "started_at", "finished_at", "error",
                                   "utterances_coded", "invalid_codes"}
    assert payload["run"]["status"] == "done" and payload["teams"] == TEAMS
    assert payload["mode"] == "single" and payload["run"]["partner_device_id"] is None
    assert payload["pods"] == [{"id": pod.id, "name": pod.name, "group": None, "side": None}]
    assert len(payload["codes"]) == 14
    first = payload["codes"][0]
    assert set(first) == {"transcript_id", "session_device_id", "start_time", "length", "speaker_tag", "team",
                          "text", "emotion", "rip", "frame", "listening"}
    assert (first["start_time"], first["speaker_tag"], first["team"], first["frame"]) == (0, "Pat", "Pat", "past_blame")
    assert first["session_device_id"] == pod.id
    assert payload["codes"][8]["listening"] == ["paraphrase", "check_understanding"]
    assert set(payload["summary"]) == {"by_team", "by_speaker", "timeline", "pods"}
    assert payload["summary"]["timeline"]["first_future_move"] == 150

    # PUT teams: recomputed from the stored codes, no LLM
    resp = _call(env, r.set_negotiation_teams, "PUT", {"teams": {"Pat": "Sandy", "Sandy": "Pat"}}, **ids)
    assert resp.status_code == 200
    swapped = resp.get_json()
    assert swapped["teams"] == {"Pat": "Sandy", "Sandy": "Pat"}
    assert swapped["summary"]["by_team"]["Sandy"]["frame"]["past_blame"] == 1
    assert swapped["summary"]["by_speaker"]["Pat"]["team"] == "Sandy"
    assert swapped["run"]["status"] == "done" and len(swapped["codes"]) == 14
    assert swapped["codes"][0]["team"] == "Sandy"   # rows follow the new assignment
    assert _call(env, r.set_negotiation_teams, "PUT", {"teams": "x"}, **ids).status_code == 400
    assert _call(env, r.set_negotiation_teams, "PUT", {}, session_id=session.id,
                 session_device_id=empty.id).status_code == 404

    # CSV export
    resp = _call(env, r.export_negotiation_coding, "GET", **ids)
    assert resp.status_code == 200
    assert resp.headers["Content-Type"] == "text/csv; charset=utf-8"
    assert resp.headers["Content-Disposition"] == "attachment; filename=negotiation_coding_session%d_pod%d.csv" % (session.id, pod.id)
    rows = list(csv.reader(io.StringIO(resp.data.decode("utf-8"))))
    assert rows[0] == ["transcript_id", "start_time", "length", "speaker_tag", "team", "pod", "text",
                       "emotion", "rip", "frame", "listening"]
    assert len(rows) == 15
    assert rows[9][1:] == ["120", "10", "Pat", "Sandy", pod.name, VIKING[8][1],
                           "neutral", "interest", "none", "paraphrase;check_understanding"]
    assert int(rows[9][0]) == payload["codes"][8]["transcript_id"]

    # per-session overview: every pod, no codes
    resp = _call(env, r.list_negotiation_coding, "GET", session_id=session.id)
    overview = {e["device_id"]: e for e in resp.get_json()}
    assert set(overview) == {pod.id, empty.id}
    assert set(overview[pod.id]) == {"device_id", "device_name", "negotiation_group", "negotiation_side",
                                     "run", "mode", "codebook", "team_names", "pods", "teams", "summary"}
    assert overview[pod.id]["mode"] == "single"
    assert overview[pod.id]["run"]["status"] == "done" and overview[pod.id]["summary"]["timeline"]["first_escalating"] == 15
    assert overview[empty.id]["run"] is None and overview[empty.id]["summary"] is None
    assert _call(env, r.export_negotiation_coding, "GET", session_id=session.id,
                 session_device_id=empty.id).status_code == 404


def test_cancel_run_marks_only_pending_runs(env, pod):
    d = env.database
    queued = d.create_negotiation_run(pod.id, "m", "viking-v2")
    env.engine.cancel_run(queued.id, "queue cleared")
    assert d.get_negotiation_run(queued.id).status == "error"
    assert d.get_negotiation_run(queued.id).error == "cancelled: queue cleared"
    done = env.engine.run_coding(pod.id, TEAMS, llm=gold_llm)
    env.engine.cancel_run(done.id, "queue cleared")
    assert d.get_negotiation_run(done.id).status == "done"
    assert d.session_device_transcript_count(pod.id) == 14


def test_queue_coding_run_reuses_a_queued_run_else_creates_one(env, pod):
    d = env.database
    env.enqueue_coding.calls.clear()
    a = env.engine.queue_coding_run(pod.session_id, pod.id, {"Pat": "Pat"})
    b = env.engine.queue_coding_run(pod.session_id, pod.id, None)
    assert a.id == b.id and b.teams_dict() == {"Pat": "Pat"} and b.status == "queued"
    d.update_negotiation_run(a.id, status="running")
    c = env.engine.queue_coding_run(pod.session_id, pod.id)
    assert c.id != a.id and c.status == "queued" and c.codebook_version == "viking-v2"
    assert [call[0][2] for call in env.enqueue_coding.calls] == [a.id, a.id, c.id]


# ------------------------------------------------ the queue's coding leg

@pytest.fixture
def fake(monkeypatch):
    r = FakeRedis()
    monkeypatch.setattr(redis_sync, "_client", r)
    monkeypatch.delenv("NEGOTIATION_CODING_WAIT_FOR_IDLE", raising=False)
    return r


class _AppStub:
    class app:
        @staticmethod
        def app_context():
            import contextlib
            return contextlib.nullcontext()


def _stub_engine(monkeypatch, **attrs):
    monkeypatch.setitem(sys.modules, "app", _AppStub)
    engine = types.SimpleNamespace(**attrs)
    monkeypatch.setitem(sys.modules, "negotiation_coding", engine)
    return engine


def test_enqueue_coding_carries_the_run_id_and_queues_beside_analysis_jobs(fake):
    assert q.enqueue_coding(1, 5, 77) is True
    assert q.enqueue_coding(1, 5, 77) is False            # the same run, once
    assert q.enqueue(1, [5]) == [5]                        # the pod's GPU job still queues
    assert q.enqueue_coding(1, 5, 78) is True
    assert q.enqueue(1, [5]) == []                         # but only one GPU job per pod
    with pytest.raises(ValueError, match="enqueue_coding"):
        q.enqueue(1, [6], legs=("coding",))
    jobs = q._all_jobs()
    assert [(j["device_id"], j.get("legs"), j.get("run_id")) for j in jobs] == \
        [(5, ["coding"], 77), (5, None, None), (5, ["coding"], 78)]
    assert q.status(1)[0] == {"session_id": 1, "device_id": 5, "state": "queued",
                              "error": None, "started_at": None, "finished_at": None}
    assert q._legs_extra(("coding",)) == {"legs": ["coding"]}
    assert q._legs_extra(("coding", "audio")) == {"legs": ["audio", "coding"]}


def test_coding_leg_runs_in_process_without_socket_ticket_or_base(fake, monkeypatch):
    ran = _Recorder()
    _stub_engine(monkeypatch, run_coding=ran)
    for name in ("_run_leg", "_mint", "_job_base", "_cancel"):
        monkeypatch.setattr(q, name, lambda *a, **k: pytest.fail("%s must not run for a coding leg" % name))
    job = {"session_id": 1, "device_id": 5, "state": "running", "legs": ["coding"], "run_id": 77}
    q._run_job(job)
    assert ran.calls == [((5,), {"run_id": 77})]
    assert job["done_legs"] == ["coding"]
    # a failure in the engine fails the job (the run row was marked error by run_coding)
    def boom(*a, **k):
        raise RuntimeError("LLM refused")
    _stub_engine(monkeypatch, run_coding=boom)
    with pytest.raises(RuntimeError, match="LLM refused"):
        q._run_job({"session_id": 1, "device_id": 5, "state": "running", "legs": ["coding"], "run_id": 78})


def test_needs_idle_only_for_gpu_legs_unless_the_env_says_otherwise(fake, monkeypatch):
    assert q._needs_idle({"legs": ["audio", "video"]}) is True
    assert q._needs_idle({}) is True
    assert q._needs_idle({"legs": ["audio", "coding"]}) is True
    assert q._needs_idle({"legs": ["coding"]}) is False
    monkeypatch.setenv("NEGOTIATION_CODING_WAIT_FOR_IDLE", "1")
    assert q._needs_idle({"legs": ["coding"]}) is True
    assert q._job_legs({}) == ["audio", "video"]           # a legacy job never gains the coding leg


class _Stop(Exception):
    pass


def _driven_loop(monkeypatch, live):
    # The runner on the test thread: a live class that never ends; the
    # first idle sleep stops the loop.
    monkeypatch.setattr(q, "_live_pods", lambda: live)
    monkeypatch.setattr(q, "_maybe_recycle_audio_service", lambda: pytest.fail("no recycle for coding jobs"))
    monkeypatch.setattr(q, "_job_base", lambda job: pytest.fail("no trigger base while the class is on"))

    def stop(s):
        raise _Stop()
    monkeypatch.setattr(q.time, "sleep", stop)
    ran = _Recorder()
    _stub_engine(monkeypatch, run_coding=ran)
    return ran


def test_coding_jobs_run_beside_a_live_class_while_gpu_jobs_hold(fake, monkeypatch, caplog):
    ran = _driven_loop(monkeypatch, live=2)
    q.enqueue(1, [10])                 # the GPU job at the head must hold
    q.enqueue_coding(1, 11, 5)
    q.enqueue_coding(1, 12, 6)
    with pytest.raises(_Stop):
        q._worker_loop()
    assert ran.calls == [((11,), {"run_id": 5}), ((12,), {"run_id": 6})]
    states = {(j["device_id"], j.get("run_id")): j["state"] for j in q._all_jobs()}
    assert states == {(10, None): "queued", (11, 5): "done", (12, 6): "done"}
    done = [j for j in q._all_jobs() if j["state"] == "done"]
    assert all(j["finished_at"] and j["started_at"] and j["error"] is None for j in done)


def test_wait_for_idle_env_holds_coding_jobs_like_the_rest(fake, monkeypatch):
    ran = _driven_loop(monkeypatch, live=1)
    monkeypatch.setenv("NEGOTIATION_CODING_WAIT_FOR_IDLE", "1")
    q.enqueue_coding(1, 11, 5)
    with pytest.raises(_Stop):
        q._worker_loop()
    assert ran.calls == [] and q._all_jobs()[0]["state"] == "queued"


def test_coding_job_needs_no_class_check_when_nothing_is_live(fake, monkeypatch):
    ran = _driven_loop(monkeypatch, live=0)
    q.enqueue_coding(1, 11, 5)
    q._worker_loop()
    assert ran.calls == [((11,), {"run_id": 5})] and q._all_jobs()[0]["state"] == "done"


def test_clear_pending_marks_dropped_coding_runs_cancelled(fake, monkeypatch):
    cancelled = _Recorder()
    _stub_engine(monkeypatch, cancel_run=cancelled)
    q.enqueue_coding(1, 11, 5)
    q.enqueue(1, [10])
    assert q.clear_pending() == 2
    assert cancelled.calls == [((5, "queue cleared"), {})]
    assert q._all_jobs() == []


def test_queue_leg_source_contracts():
    s = _read("src", "server", "posthoc_queue.py")
    assert 'LEGS = ("audio", "video", "coding")' in s and 'DEFAULT_LEGS = ("audio", "video")' in s
    leg = _func_source(s, "_run_coding_leg")
    for forbidden in ("_mint(", "websockets", "gpu_lease", "_run_leg(", "RedisPosthocTicket"):
        assert forbidden not in leg
    assert "negotiation_coding.run_coding(job[\"device_id\"], run_id=job.get(\"run_id\"))" in leg
    loop = _func_source(s, "_worker_loop")
    assert "beside_class = _needs_idle(job) and not _wait_for_class_to_end()" in loop
    assert "if _needs_gpu(job):" in loop and "_maybe_recycle_audio_service()" in loop
    assert "and _needs_gpu(j)}" in _func_source(s, "enqueue")
    assert "NEGOTIATION_CODING_WAIT_FOR_IDLE" in _func_source(s, "_needs_idle")
    run_job = _func_source(s, "_run_job")
    assert run_job.index('if scope == "coding":') < run_job.index("base = _job_base(job)")


# ---------------------------------------- session flag, end hook, migration

HANDLER = ("src", "server", "handlers", "session_handler.py")


def test_prompt_names_the_sides_as_the_session_does():
    messages = nc.build_prompt(CODEBOOK, _utterances()[:2], [], ("Buyer", "Seller"))
    assert "Buyer's team versus Seller's team" in messages[0]["content"]
    assert "Pat's team versus" not in messages[0]["content"]
    default = nc.build_prompt(CODEBOOK, _utterances()[:2], [])
    assert "Team A's team versus Team B's team" in default[0]["content"]
    src = _read("src", "server", "negotiation_coding.py")
    assert 'DEFAULT_TEAMS = ("Team A", "Team B")' in src
    assert '"Pat"' not in src and "Sandy" not in src.replace("Table 3 Pat 2", "")


def test_create_session_route_reads_negotiation_coding_defaulting_off():
    create = _func_source(_read("src", "server", "routes", "session.py"), "create_session")
    assert "request.json.get('negotiationCoding', False)" in create
    assert "if not isinstance(negotiation_coding, bool):" in create
    assert "negotiation_coding_enabled=negotiation_coding" in create
    assert create.index("negotiationCoding") < create.index("session_handler.create_session(")


def test_handler_stores_the_flag_and_queues_coding_at_session_end():
    s = _read(*HANDLER)
    create = _func_source(s, "create_session")
    assert "negotiation_coding_enabled=False" in create.splitlines()[0]
    assert "session.negotiation_coding = bool(negotiation_coding_enabled)" in create
    end = _func_source(s, "end_session")
    assert "if session.negotiation_coding:" in end
    assert end.index("database.save_changes()") < end.index("queue_negotiation_coding(session, session_devices)") \
        < end.index("# Ping pod devices")
    queue = _func_source(s, "queue_negotiation_coding")
    assert "negotiation_coding.queue_coding_run(session.id, device_id, partner_device_id=partner_id)" in queue
    assert "database.session_device_transcript_count(session_device.id)" in queue
    assert "negotiation_coding.resolve_pair(session_device.id)" in queue
    assert "negotiation_paired=False" in create.splitlines()[0]
    assert "session.negotiation_paired = bool(negotiation_paired)" in create


def test_queue_negotiation_coding_skips_empty_pods_and_is_best_effort():
    src = _read(*HANDLER)
    queued = []

    def queue_coding_run(session_id, device_id, teams=None, partner_device_id=None):
        if device_id == 3:
            raise RuntimeError("redis down")
        queued.append((device_id, partner_device_id))
        return types.SimpleNamespace(id=100 + device_id)

    # Paired session: pods 1+4 are one breakout group (Pat = 4, so 4 is the
    # run's first device); 2 is empty; 3 blows up; 5 has no partner yet.
    pairs = {1: (4, 1), 4: (4, 1), 2: (2, None), 3: (3, None), 5: (5, None)}
    ns = {"logging": __import__("logging"),
          "database": types.SimpleNamespace(session_device_transcript_count=lambda d: 0 if d == 2 else 5),
          "negotiation_coding": types.SimpleNamespace(queue_coding_run=queue_coding_run,
                                                      resolve_pair=lambda d: pairs[d])}
    exec(_func_source(src, "queue_negotiation_coding"), ns)
    session = types.SimpleNamespace(id=9)
    pods = [types.SimpleNamespace(id=i) for i in (1, 2, 3, 4)]
    assert ns["queue_negotiation_coding"](session, pods) == [(1, 101), (4, 104)]
    assert queued == [(1, None), (4, None)]

    queued.clear()
    paired = types.SimpleNamespace(id=9, negotiation_paired=True)
    pods = [types.SimpleNamespace(id=i) for i in (1, 2, 3, 4, 5)]
    assert ns["queue_negotiation_coding"](paired, pods) == [(4, 104), (5, 105)]
    assert queued == [(4, 1), (5, None)]   # one run for the pair, 4 never queued twice


def test_session_model_column_json_and_blueprint_registration():
    s = _read("src", "server", "tables", "session.py")
    assert "negotiation_coding = db.Column(db.Boolean, nullable=True)" in s
    assert "negotiation_coding=bool(self.negotiation_coding)" in s
    assert "self.negotiation_coding = bool(negotiation_coding)" in s
    assert "negotiation_paired = db.Column(db.Boolean, nullable=True)" in s
    assert "negotiation_paired=bool(self.negotiation_paired)" in s
    sd = _read("src", "server", "tables", "session_device.py")
    assert "negotiation_group = db.Column(db.String(32), nullable=True)" in sd
    assert "negotiation_side = db.Column(db.String(16), nullable=True)" in sd
    assert "NEGOTIATION_SIDES" not in sd and "'Pat'" not in sd   # team names come from the pod setup
    dc = _read("src", "server", "discussion_capture.py")
    assert "from routes.negotiation_coding import api_routes as negotiation_coding_api" in dc
    assert "app.register_blueprint(negotiation_coding_api)" in dc


def test_routes_are_guarded_and_rate_limited():
    s = _read("src", "server", "routes", "negotiation_coding.py")
    tree = ast.parse(s)
    guards = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name.endswith("negotiation_coding") or \
                isinstance(node, ast.FunctionDef) and node.name == "set_negotiation_teams":
            guards[node.name] = [ast.unparse(d) for d in node.decorator_list]
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "set_negotiation_role":
            guards[node.name] = [ast.unparse(d) for d in node.decorator_list]
    assert "wrappers.verify_session_access" in guards["start_negotiation_coding"]
    assert "wrappers.verify_session_access" in guards["set_negotiation_teams"]
    assert "wrappers.verify_session_access" in guards["set_negotiation_role"]
    for name in ("get_negotiation_coding", "export_negotiation_coding", "list_negotiation_coding"):
        assert "wrappers.verify_session_read_access" in guards[name]
    assert any("limiter.limit('30 per hour'" in d for d in guards["start_negotiation_coding"])
    assert all(any(d.startswith("wrappers.verify_login(") for d in ds) for ds in guards.values())
    assert s.count("missing = _pod_or_404(session_device_id, session_id)") == 5
    assert "authz.device_in_session(session_device_id, session_id)" in s


def test_models_cascade_from_pod_run_and_transcript():
    run = _read("src", "server", "tables", "negotiation_coding_run.py")
    assert "db.ForeignKey('session_device.id', ondelete='CASCADE')" in run
    assert "STATUSES = ('queued', 'running', 'done', 'error')" in run
    code = _read("src", "server", "tables", "negotiation_code.py")
    assert "db.ForeignKey('negotiation_coding_run.id', ondelete='CASCADE')" in code
    assert "db.ForeignKey('transcript.id', ondelete='CASCADE')" in code
    d = _read("src", "server", "database.py")
    for helper in ("create_negotiation_run", "get_negotiation_run", "get_latest_negotiation_run",
                   "get_negotiation_runs", "update_negotiation_run", "add_negotiation_codes",
                   "get_negotiation_codes", "session_device_transcript_count"):
        assert "def %s(" % helper in d


def test_migration_chains_after_live_video_and_is_guarded_both_ways():
    versions = os.path.join(ROOT, "src", "server", "migrations", "versions")
    fn = [f for f in os.listdir(versions) if f.startswith("4c5d6e7f8091_")]
    assert len(fn) == 1, fn
    s = _read("src", "server", "migrations", "versions", fn[0])
    assert "revision = '4c5d6e7f8091'" in s and "down_revision = '3b4c5d6e7f80'" in s
    up = s[s.index("def upgrade():"):s.index("def downgrade():")]
    down = s[s.index("def downgrade():"):]
    assert "if not _has_column('session', 'negotiation_coding'):" in up
    assert "op.add_column('session', sa.Column('negotiation_coding', sa.Boolean(), nullable=True))" in up
    for table in ("negotiation_coding_run", "negotiation_code"):
        assert "if not _has_table('%s'):" % table in up
        assert "op.create_table(\n            '%s'," % table in up
        assert "if _has_table('%s'):" % table in down and "op.drop_table('%s')" % table in down
    assert "sa.ForeignKeyConstraint(['session_device_id'], ['session_device.id'], ondelete='CASCADE')" in up
    assert "sa.ForeignKeyConstraint(['run_id'], ['negotiation_coding_run.id'], ondelete='CASCADE')" in up
    assert "sa.ForeignKeyConstraint(['transcript_id'], ['transcript.id'], ondelete='CASCADE')" in up
    assert "op.drop_column('session', 'negotiation_coding')" in down
    assert down.index("negotiation_code'") < down.index("negotiation_coding_run'")   # child first


# ------------------------------------------------ paired devices (one per team)

def _row(i, device, start, text, tag=None, sim=None, closed_world=False, length=8):
    conf = None
    if sim is not None:
        conf = {"percent": 80, "sim": sim, "margin": 0.2}
        if closed_world:
            conf["closed_world"] = True
    return types.SimpleNamespace(
        id=i, session_device_id=device, start_time=start, length=length, speaker_tag=tag, transcript=text,
        _voice_features_json=lambda: {"confidence": conf} if conf else None)


SIDES = {1: "Pat", 2: "Sandy"}


def test_text_similarity_and_same_moment():
    assert nc.text_similarity("I need the money by Friday", "I need the money by Friday.") == 1.0
    assert nc.text_similarity("I need the money by Friday", "need money Friday") > 0.5
    assert nc.text_similarity("Let's slow down", "The supplier is unpaid") < 0.3
    assert nc.text_similarity("", "anything") == 0.0
    a = {"start_time": 10, "length": 8}
    assert nc.same_moment(a, {"start_time": 11.4, "length": 8})          # starts within 1.5 s
    assert nc.same_moment(a, {"start_time": 14, "length": 8})            # 4 s of an 8 s utterance overlap
    assert not nc.same_moment(a, {"start_time": 15, "length": 8})        # 3 of 8: below half
    assert not nc.same_moment(a, {"start_time": 30, "length": 8})
    assert nc.same_moment({"start_time": 10, "length": 0}, {"start_time": 11, "length": 0})
    assert not nc.same_moment({"start_time": 10, "length": 0}, {"start_time": 13, "length": 0})


def test_match_strength_prefers_the_devices_own_confident_speakers():
    assert nc.match_strength({"speaker_tag": None}) == 0.0
    assert nc.match_strength({"speaker_tag": "Pat"}) == 0.5
    assert nc.match_strength({"speaker_tag": "Pat", "confidence": {"sim": 0.8}}) == 0.8
    assert nc.match_strength({"speaker_tag": "Pat", "confidence": {"sim": 0.8, "closed_world": True}}) == pytest.approx(0.5)
    assert nc.match_strength({"speaker_tag": "Pat", "confidence": {"sim": "junk"}}) == 0.5


def test_merge_paired_keeps_one_copy_of_each_utterance_on_its_own_side():
    # Both microphones hear the whole table. The Pat laptop (device 1) hears
    # its own speakers confidently and Sandy's faintly (closed-world picks or
    # no match); the Sandy laptop (device 2) the reverse.
    pat = [
        _row(1, 1, 0, "You went on vacation and left Alex in charge", "Pat", sim=0.82),
        _row(2, 1, 15.5, "That's ridiculous you signed off on the change order", "Jordan", sim=0.62, closed_world=True),
        _row(3, 1, 30, "Don't you understand I need the money by Friday", "Pat", sim=0.79),
        _row(4, 1, 45.2, "mumble bankruptcy recover", None),                    # far side, unmatched, different words
        _row(5, 1, 60, "I can call the loan whenever I want", "Jordan", sim=0.7),
        _row(6, 1, 75, "Fine tell me what is bothering you most", "Sam", sim=0.9),
    ]
    sandy = [
        _row(11, 2, 0.4, "You went on vacation and left Alex in charge", "Riley", sim=0.55, closed_world=True),
        _row(12, 2, 15, "That's ridiculous. You're the one who signed off on the change order.", "Sandy", sim=0.88),
        _row(13, 2, 45, "If you force me into bankruptcy you may not recover the money", "Sandy", sim=0.84),
        _row(14, 2, 60.3, "I can call the loan whenever I want", None),           # far side, unmatched copy
        _row(15, 2, 75.5, "Can we slow this down for a minute", "Riley", sim=0.8),   # both talking at once: kept
    ]
    kept, dropped = nc.merge_paired({1: pat, 2: sandy}, SIDES)
    assert [u["transcript_id"] for u in kept] == [1, 12, 3, 13, 5, 6, 15]
    assert [u["index"] for u in kept] == list(range(7))
    assert [u["team"] for u in kept] == ["Pat", "Sandy", "Pat", "Sandy", "Pat", "Pat", "Sandy"]
    assert [u["session_device_id"] for u in kept] == [1, 2, 1, 2, 1, 1, 2]
    assert {d["transcript_id"]: (d["kept_transcript_id"], d["reason"]) for d in dropped} == {
        11: (1, "duplicate"),     # Pat's own words, stronger on the Pat laptop
        2: (12, "duplicate"),     # Sandy's words: closed-world pick on Pat's laptop loses to Sandy's 0.88
        4: (13, "bleed"),         # unmatched garble against a matched utterance at the same moment
        14: (5, "duplicate"),     # unmatched but word-for-word: the text match decides first
    }
    assert all(0 <= d["similarity"] <= 1 for d in dropped)
    assert kept[0]["confidence"]["sim"] == 0.82


def test_merge_paired_ties_go_to_the_fuller_text_then_the_earlier_row():
    a = _row(1, 1, 0, "we both let that slide", "Pat", sim=0.7)
    b = _row(2, 2, 0.5, "the contract says changes must be in writing but we both let that slide", "Sandy", sim=0.72)
    kept, dropped = nc.merge_paired({1: [a], 2: [b]}, SIDES)
    assert [u["transcript_id"] for u in kept] == [2] and dropped[0]["reason"] == "duplicate"
    c = _row(3, 1, 0, "same words here", "Pat")
    d = _row(4, 2, 0, "same words here", "Sandy")
    kept, _ = nc.merge_paired({1: [c], 2: [d]}, SIDES)
    assert [u["transcript_id"] for u in kept] == [3]
    # one device, nothing to merge against; unsided device gets no team
    kept, dropped = nc.merge_paired({1: [a, c]}, {}) if False else nc.merge_paired({1: [a], 2: []}, {1: "Pat"})
    assert dropped == [] and kept[0]["team"] == "Pat" and kept[0]["index"] == 0
    kept, _ = nc.merge_paired({1: [a]}, {})
    assert "team" not in kept[0]


def test_team_of_code_prefers_the_stamped_team_and_rollup_keys_shared_tags_apart():
    assert nc.team_of_code({"speaker_tag": "Pat", "team": "Sandy"}, TEAMS, VIKING_NAMES) == "Sandy"
    assert nc.team_of_code({"speaker_tag": "Pat", "team": "nonsense"}, TEAMS, VIKING_NAMES) == "Pat"
    assert nc.team_of_code({"speaker_tag": "Coach"}, TEAMS, VIKING_NAMES) == nc.UNASSIGNED
    assert nc.other_team("Pat", VIKING_NAMES) == "Sandy" and nc.other_team("Sandy", VIKING_NAMES) == "Pat"
    codes = [dict(u, team=("Pat" if u["index"] % 2 == 0 else "Sandy"), speaker_tag=None, **VIKING[u["index"]][2])
             for u in _utterances()]
    summary = nc.summarize(codes, {}, CODEBOOK, extra={"cross_talk": {"dropped": 3}, "pods": None}, names=VIKING_NAMES)
    assert summary["by_team"]["Pat"]["utterances"] == 7 and summary["by_team"]["Sandy"]["utterances"] == 7
    assert summary["by_team"][nc.UNASSIGNED]["utterances"] == 0
    assert set(summary["by_speaker"]) == {"", " (Sandy)"}   # the untagged voice on both sides, kept apart
    assert summary["by_speaker"][""]["team"] == "Pat" and summary["by_speaker"][" (Sandy)"]["team"] == "Sandy"
    assert summary["cross_talk"] == {"dropped": 3} and "pods" not in summary


def _paired_session(env, group="Table 1", sides=("Pat", "Sandy")):
    from tables.session_device import SessionDevice
    session = _session(env)
    session.negotiation_coding = True
    session.negotiation_paired = True
    session.pod_config = json.dumps(dict(VIKING_SETUP_SINGLE, devices_per_group="team"))
    env.db.session.commit()
    pods = []
    for side in sides:
        device = SessionDevice(session.id, None, "%s %s" % (group, side) if side else "Lone")
        device.negotiation_group = group
        device.negotiation_side = side
        env.db.session.add(device)
        env.db.session.flush()
        device.create_key()
        pods.append(device)
    env.db.session.commit()
    return session, pods


def _add(env, device, start, text, tag, sim=None, closed_world=False):
    vf = None
    if sim is not None:
        vf = {"confidence": {"percent": 80, "sim": sim, "margin": 0.2}}
        if closed_world:
            vf["confidence"]["closed_world"] = True
    env.database.add_transcript(device.id, start, 10, text, False, 0, 0, 0, 0, 0, 0, -1, tag, -1, voice_features=vf)


def test_paired_run_codes_both_pods_merged_with_teams_by_side(env):
    d, r = env.database, env.routes
    session, (pat, sandy) = _paired_session(env)
    # the 14-line exchange heard by both laptops: each side hears its own
    # lines confidently and the other side's as a weak closed-world pick
    for i, (tag, text, _) in enumerate(VIKING):
        near, far = (pat, sandy) if tag == "Pat" else (sandy, pat)
        _add(env, near, 15 * i, text, tag, sim=0.85)
        _add(env, far, 15 * i + 1, text, tag, sim=0.5, closed_world=True)
    assert env.engine.resolve_pair(sandy.id) == (pat.id, sandy.id)
    assert env.engine.resolve_pair(pat.id) == (pat.id, sandy.id)

    env.enqueue_coding.calls.clear()
    resp = _call(env, r.start_negotiation_coding, "POST", {}, session_id=session.id, session_device_id=sandy.id)
    assert resp.status_code == 202
    body = resp.get_json()
    assert (body["session_device_id"], body["partner_device_id"]) == (pat.id, sandy.id)
    assert env.enqueue_coding.calls == [((session.id, pat.id, body["run_id"]), {})]
    run = d.get_negotiation_run(body["run_id"])
    assert run.partner_device_id == sandy.id and run.is_paired() and run.device_ids() == [pat.id, sandy.id]
    # either pod finds the run; POST again on the other pod reuses it
    assert d.get_latest_negotiation_run(sandy.id).id == run.id
    again = _call(env, r.start_negotiation_coding, "POST", {}, session_id=session.id, session_device_id=pat.id).get_json()
    assert again["run_id"] == run.id

    env.engine.run_coding(pat.id, llm=gold_llm, run_id=run.id)
    for pod in (pat, sandy):
        payload = _call(env, r.get_negotiation_coding, "GET", session_id=session.id, session_device_id=pod.id).get_json()
        assert payload["run"]["id"] == run.id and payload["mode"] == "paired"
        assert payload["pods"] == [{"id": pat.id, "name": "Table 1 Pat", "group": "Table 1", "side": "Pat"},
                                   {"id": sandy.id, "name": "Table 1 Sandy", "group": "Table 1", "side": "Sandy"}]
    assert len(payload["codes"]) == 14 and payload["run"]["utterances_coded"] == 14
    assert [c["team"] for c in payload["codes"]] == [tag for tag, _, _ in VIKING]
    assert [c["session_device_id"] for c in payload["codes"]] == [pat.id if tag == "Pat" else sandy.id for tag, _, _ in VIKING]
    assert [c["start_time"] for c in payload["codes"]] == [15 * i for i in range(14)]   # the near copies
    assert payload["summary"]["cross_talk"]["dropped"] == 14 and payload["summary"]["cross_talk"]["kept"] == 14
    assert all(x["reason"] == "duplicate" for x in payload["summary"]["cross_talk"]["detail"])
    assert payload["summary"]["pods"][0]["side"] == "Pat"
    assert payload["summary"]["by_team"]["Pat"]["utterances"] == 7
    assert payload["summary"]["by_team"]["Sandy"]["utterances"] == 7
    assert payload["summary"]["timeline"]["first_escalating"] == 15
    # 14 codes stored, none for the dropped far copies
    from tables.negotiation_code import NegotiationCode
    assert env.db.session.query(NegotiationCode).filter(NegotiationCode.run_id == run.id).count() == 14

    # a speaker-tag assignment cannot override the device's side
    swapped = _call(env, r.set_negotiation_teams, "PUT", {"teams": {"Pat": "Sandy"}},
                    session_id=session.id, session_device_id=sandy.id).get_json()
    assert swapped["codes"][0]["team"] == "Pat" and swapped["summary"]["by_team"]["Pat"]["utterances"] == 7
    assert swapped["summary"]["cross_talk"]["dropped"] == 14

    # CSV names the pod of every line
    resp = _call(env, r.export_negotiation_coding, "GET", session_id=session.id, session_device_id=sandy.id)
    rows = list(csv.reader(io.StringIO(resp.data.decode("utf-8"))))
    assert rows[1][3:6] == ["Pat", "Pat", "Table 1 Pat"] and rows[2][3:6] == ["Sandy", "Sandy", "Table 1 Sandy"]

    # the session overview shows the run on both pods
    overview = {e["device_id"]: e for e in _call(env, r.list_negotiation_coding, "GET", session_id=session.id).get_json()}
    assert overview[pat.id]["run"]["id"] == overview[sandy.id]["run"]["id"] == run.id
    assert overview[sandy.id]["negotiation_side"] == "Sandy" and overview[sandy.id]["mode"] == "paired"


def test_run_sides_fills_in_a_missing_or_clashing_side(env):
    d = env.database
    session, (a, b) = _paired_session(env, group="Table 2", sides=(None, None))
    run = d.create_negotiation_run(a.id, "m", "viking-v2", partner_device_id=b.id)
    assert env.engine.run_sides(run) == {a.id: "Pat", b.id: "Sandy"}
    b.negotiation_side = "Pat"
    env.db.session.commit()
    assert env.engine.run_sides(run) == {a.id: "Sandy", b.id: "Pat"}
    a.negotiation_side = "Pat"
    env.db.session.commit()
    assert env.engine.run_sides(run) == {a.id: "Pat", b.id: "Sandy"}   # the partner yields
    # a lone sided pod: its utterances are its side; an unsided lone pod: nothing stamped
    lone = d.create_negotiation_run(a.id, "m", "viking-v2")
    assert env.engine.run_sides(lone) == {a.id: "Pat"}
    a.negotiation_side = None
    env.db.session.commit()
    assert env.engine.run_sides(lone) == {}
    assert env.engine.run_pods(run, {a.id: "Pat"})[1] == {"id": b.id, "name": "Lone", "group": "Table 2", "side": None}


def test_resolve_pair_after_the_session_ended(env):
    # end_session marks every pod removed before it queues the coding (the
    # flag means "not in the live session any more"); the pairing must still
    # see the whole group, or no class is ever coded at its end.
    from datetime import datetime
    d = env.database
    session, (pat, sandy) = _paired_session(env, group="Table 5")
    session.end_date = datetime(2026, 10, 16, 15, 10)
    pat.removed = sandy.removed = True
    pat.connected = sandy.connected = False
    env.db.session.commit()
    assert d.get_negotiation_partner(pat).id == sandy.id
    assert env.engine.resolve_pair(pat.id) == (pat.id, sandy.id)
    assert env.engine.resolve_pair(sandy.id) == (pat.id, sandy.id)


def test_resolve_pair_keeps_a_removed_pod_in_its_own_group_while_live(env):
    # A pod that left the live session still resolves (manual "Run coding"
    # on it) instead of raising on its own missing side.
    session, (pat, sandy) = _paired_session(env, group="Table 6")
    pat.removed = True
    env.db.session.commit()
    assert env.engine.resolve_pair(pat.id) == (pat.id, sandy.id)


def test_resolve_pair_partner_lookup_and_lone_pods(env):
    d = env.database
    session, (pat, sandy) = _paired_session(env, group="Table 3")
    lone = _pod(env, session, with_transcripts=False)
    assert env.engine.resolve_pair(lone.id) == (lone.id, None)          # no group
    lone.negotiation_group = "Table 9"
    env.db.session.commit()
    assert env.engine.resolve_pair(lone.id) == (lone.id, None)          # no partner yet
    assert d.get_negotiation_partner(pat).id == sandy.id
    sandy.removed = True
    env.db.session.commit()
    assert d.get_negotiation_partner(pat) is None and env.engine.resolve_pair(pat.id) == (pat.id, None)
    sandy.removed = False
    env.db.session.commit()
    # two pods on the same side never pair: the second is an extra laptop,
    # coded alone, and the first waits for the other side; an unpaired
    # session never pairs
    sandy.negotiation_side = "Pat"
    env.db.session.commit()
    assert env.engine.resolve_pair(sandy.id) == (sandy.id, None)
    assert env.engine.resolve_pair(pat.id) == (pat.id, None)
    session.negotiation_paired = False
    env.db.session.commit()
    assert env.engine.resolve_pair(sandy.id) == (sandy.id, None)
    assert env.engine.resolve_pair(999999) == (999999, None)


def test_role_route_sets_group_and_side_with_validation(env):
    d, r = env.database, env.routes
    session, (pat, sandy) = _paired_session(env, group="Table 4")
    ids = dict(session_id=session.id, session_device_id=sandy.id)
    assert _call(env, r.set_negotiation_role, "PUT", {"group": "Table 4", "side": "Coach"}, **ids).status_code == 400
    assert _call(env, r.set_negotiation_role, "PUT", {"group": "x" * 33, "side": "Pat"}, **ids).status_code == 400
    assert _call(env, r.set_negotiation_role, "PUT", {"group": "Table <4>", "side": "Pat"}, **ids).status_code == 400
    resp = _call(env, r.set_negotiation_role, "PUT", {"group": " Table 5 ", "side": "pat"}, **ids)
    assert resp.status_code == 200
    body = resp.get_json()
    assert (body["session_device"]["negotiation_group"], body["session_device"]["negotiation_side"]) == ("Table 5", "Pat")
    assert body["partner_device_id"] is None and body["first_device_id"] == sandy.id   # moved to a table of its own
    assert d.get_session_devices(id=sandy.id).negotiation_side == "Pat"
    cleared = _call(env, r.set_negotiation_role, "PUT", {"group": "", "side": None}, **ids).get_json()
    assert cleared["session_device"]["negotiation_group"] is None and cleared["session_device"]["negotiation_side"] is None
    assert _call(env, r.set_negotiation_role, "PUT", {"group": "T", "side": "Pat"}, session_id=session.id,
                 session_device_id=_pod(env, _session(env), with_transcripts=False).id).status_code == 404


def test_first_group_to_join_starts_the_session_clock(env):
    # A session created days ahead (QR code on a slide) counts from its
    # first join; later joins, re-joins and extra devices leave it alone.
    from datetime import datetime, timedelta, timezone
    d = env.database
    session = _session(env)
    session.passcode = "VIKING%d" % session.id
    ahead = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=2)
    session.creation_date = ahead
    env.db.session.commit()
    assert session.get_length() > 2 * 24 * 3600 - 5
    ok, first, _ = d.create_byod_session_device(session.passcode, "", 0, "Table 1", "Pat")
    assert ok and session.get_length() < 5
    started = session.creation_date
    ok, second, _ = d.create_byod_session_device(session.passcode, "", 0, "Table 2", "Pat")
    assert ok and second.id != first.id and session.creation_date == started
    ok, again, _ = d.create_byod_session_device(session.passcode, first.name, 0, "Table 1", "Pat")
    assert ok and again.id == first.id and session.creation_date == started
    # A session whose pods were registered at creation never resets.
    other = _session(env)
    other.passcode = "VIKING%d" % other.id
    other.creation_date = ahead
    env.db.session.commit()
    _pod(env, other, with_transcripts=False)
    ok, _dev, _ = d.create_byod_session_device(other.passcode, "", 0)
    assert ok and other.creation_date == ahead


def test_the_team_on_a_speakers_profile_assigns_them(env):
    # Enrolling asks for a group and team; the coding pass reads the team
    # off the profile (case-insensitive) before falling back to the name.
    from tables.student import Student
    d = env.database
    for username, team in (("buyerone", "buyer"), ("sellertwo", "Seller "), ("nobody1", None), ("elsewhere", "Judge")):
        ok, _ = d.add_student(username, group_name="Group 1", team_name=team)
        assert ok
    names = ("Buyer", "Seller")
    assert d.student_teams({"buyerone", "sellertwo", "nobody1", "elsewhere", "ghost", None}, names) == {
        "buyerone": "Buyer", "sellertwo": "Seller"}
    s = d.get_students(username="buyerone")
    assert s.name == "buyerone" and s.json()["group_name"] == "Group 1"
    # re-enrollment proof: the group and team typed again, loosely compared
    assert s.identity_matches("group  1", "BUYER")
    assert not s.identity_matches("Group 2", "buyer") and not s.identity_matches("Group 1", "")
    # a record from the old name-based form shows its name and accepts a blank group and team
    legacy = Student("oldtimer", firstname="Jane", lastname="Doe")
    env.db.session.add(legacy)
    env.db.session.commit()
    assert legacy.name == "Jane Doe" and legacy.identity_matches("", None) and not legacy.identity_matches("Group 1", "")
    # a second sign-up with the same username is refused, not overwritten
    ok, again = d.add_student("buyerone", group_name="Group 9", team_name="Seller")
    assert not ok and again.id == s.id and again.group_name == "Group 1"


def test_byod_join_stores_the_role_and_names_the_pod_after_it(env):
    from tables.session_device import SessionDevice
    d = env.database
    session = _session(env)
    session.passcode = "VIKING%d" % session.id
    env.db.session.commit()
    ok, device, speakers = d.create_byod_session_device(session.passcode, "", 0, "Table 7", "Sandy")
    assert ok and device.name == "Table 7 Sandy" and (device.negotiation_group, device.negotiation_side) == ("Table 7", "Sandy")
    ok, named, _ = d.create_byod_session_device(session.passcode, "Window table", 0, "Table 7", "Pat")
    assert ok and named.name == "Window table" and named.negotiation_side == "Pat"
    assert d.get_negotiation_partner(device).id == named.id
    # rejoining the same pod with a corrected role updates it
    ok, again, _ = d.create_byod_session_device(session.passcode, "Window table", 0, "Table 8", "Pat")
    assert ok and again.id == named.id and again.negotiation_group == "Table 8"
    ok, same, _ = d.create_byod_session_device(session.passcode, "Window table", 0, None, None)
    assert ok and same.id == named.id and same.negotiation_group == "Table 8"   # blank keeps the role
    ok, plain, _ = d.create_byod_session_device(session.passcode, "", 0)
    assert ok and plain.name.startswith("Group ") and plain.negotiation_group is None
    assert SessionDevice.verify_negotiation("Table 1", "SANDY", VIKING_NAMES) == (True, None, "Table 1", "Sandy")
    assert SessionDevice.verify_negotiation("Table 1", "SANDY") == (False, "Side must be Team A or Team B.", None, None)
    assert SessionDevice.verify_negotiation("", "") == (True, None, None, None)
    assert SessionDevice.verify_negotiation(None, None) == (True, None, None, None)
    assert SessionDevice.verify_negotiation("Table 1", 3, VIKING_NAMES)[0] is False
    assert SessionDevice.verify_negotiation(3, "Pat", VIKING_NAMES)[0] is False
    assert device.negotiation_label() == "Table 7 \u00b7 Sandy" and plain.negotiation_label() is None


def test_create_session_and_join_routes_read_the_pairing_fields():
    src = _read("src", "server", "routes", "session.py")
    create = _func_source(src, "create_session")
    assert "negotiationPaired" not in create   # pairing follows the pod setup, no separate flag
    assert "negotiation_paired = bool(pod_config) and pod_setup.paired(pod_config)" in create
    assert "negotiation_paired=negotiation_paired and negotiation_coding" in create
    join = _func_source(src, "byod_join_session")
    assert "SessionDevice.verify_negotiation(" in join
    assert "request.json.get('negotiationGroup')" in join and "request.json.get('negotiationSide')" in join
    assert "negotiation_group=negotiation_group" in join and "negotiation_side=negotiation_side" in join
    handler = _func_source(_read(*HANDLER), "byod_join_session")
    assert "negotiation_group=negotiation_group, negotiation_side=negotiation_side" in handler


def test_pairs_migration_chains_after_negotiation_coding_and_is_guarded():
    versions = os.path.join(ROOT, "src", "server", "migrations", "versions")
    fn = [f for f in os.listdir(versions) if f.startswith("5d6e7f809102_")]
    assert len(fn) == 1, fn
    s = _read("src", "server", "migrations", "versions", fn[0])
    assert "revision = '5d6e7f809102'" in s and "down_revision = '4c5d6e7f8091'" in s
    up = s[s.index("def upgrade():"):s.index("def downgrade():")]
    down = s[s.index("def downgrade():"):]
    for table, column in (("session", "negotiation_paired"), ("session_device", "negotiation_group"),
                          ("session_device", "negotiation_side"), ("negotiation_coding_run", "partner_device_id")):
        assert "if not _has_column('%s', '%s'):" % (table, column) in up
        assert "op.drop_column('%s', '%s')" % (table, column) in down
    assert "op.create_foreign_key('fk_negotiation_coding_run_partner', 'negotiation_coding_run',\n" \
           "                              'session_device', ['partner_device_id'], ['id'], ondelete='SET NULL')" in up
    assert down.index("drop_constraint") < down.index("partner_device_id")
    run = _read("src", "server", "tables", "negotiation_coding_run.py")
    assert "partner_device_id = db.Column(db.Integer, db.ForeignKey('session_device.id', ondelete='SET NULL'), nullable=True)" in run


# ------------------------------------------- team names from the pod setup

VIKING_SETUP = {"group_size": 6, "teams": [{"name": "Buyer", "size": 3}, {"name": "Seller", "size": 3}],
                "devices_per_group": "team", "groups": ["Table 1", "Table 2"]}


def test_engine_rolls_up_under_the_sessions_own_team_names():
    names = ("Buyer", "Seller")
    assert nc.team_of("a", {"a": "Seller"}, names) == "Seller"
    assert nc.team_of("a", {"a": "Pat"}, names) == nc.UNASSIGNED
    assert nc.team_of_code({"team": "Buyer"}, {}, names) == "Buyer"
    assert nc.other_team("Buyer", names) == "Seller" and nc.other_team("Seller", names) == "Buyer"
    assert nc.validate_teams({"x": "seller", "y": " BUYER "}, names) == ({"x": "Seller", "y": "Buyer"}, None)
    assert nc.validate_teams({"x": "Pat"}, names)[1] == "team for speaker 'x' must be Buyer or Seller."
    three = ("Red", "Green", "Blue")
    assert nc.validate_teams({"x": "Pat"}, three)[1] == "team for speaker 'x' must be Red, Green or Blue."
    codes = [dict(u, team=("Buyer" if u["index"] % 2 == 0 else "Seller"), **VIKING[u["index"]][2]) for u in _utterances()]
    summary = nc.summarize(codes, {}, CODEBOOK, names=names)
    assert set(summary["by_team"]) == {"Buyer", "Seller", nc.UNASSIGNED}
    assert summary["by_team"]["Buyer"]["utterances"] == 7 and summary["by_team"]["Seller"]["opening_move"] in ("none", "power", "interest", "right")
    # placeholder names apply when nothing names the teams
    assert set(nc.rollup(codes, {}, CODEBOOK)["by_team"]) == {"Team A", "Team B", nc.UNASSIGNED}


def test_paired_run_uses_the_setups_team_names(env):
    import pod_config
    d, r = env.database, env.routes
    session, (a, b) = _paired_session(env, group="Table 1", sides=(None, None))
    session.pod_config = pod_config.dumps(VIKING_SETUP)
    env.db.session.commit()
    assert session.team_names() == ("Buyer", "Seller")
    assert session.json()["pod_config"]["teams"][1]["name"] == "Seller"
    assert env.engine.device_team_names(a.id) == ("Buyer", "Seller")
    # the role route validates against the setup's names and canonicalises case
    ids = dict(session_id=session.id, session_device_id=a.id)
    assert _call(env, r.set_negotiation_role, "PUT", {"group": "Table 1", "side": "Pat"}, **ids).status_code == 400
    assert _call(env, r.set_negotiation_role, "PUT", {"group": "Table 1", "side": "seller"}, **ids).status_code == 200
    assert d.get_session_devices(id=a.id).negotiation_side == "Seller"
    for i, (tag, text, _) in enumerate(VIKING):
        _add(env, b if tag == "Pat" else a, 15 * i, text, tag, sim=0.9)
    # a has a side (Seller), b has none: a sided pod ranks first, b takes the other team
    assert env.engine.resolve_pair(a.id) == (a.id, b.id)
    resp = _call(env, r.start_negotiation_coding, "POST", {"teams": {"Pat": "Pat"}}, **ids)
    assert resp.status_code == 400   # Pat is not a team here
    resp = _call(env, r.start_negotiation_coding, "POST", {}, **ids)
    run = d.get_negotiation_run(resp.get_json()["run_id"])
    assert env.engine.run_sides(run, ("Buyer", "Seller")) == {a.id: "Seller", b.id: "Buyer"}
    env.engine.run_coding(a.id, llm=gold_llm, run_id=run.id)
    payload = _call(env, r.get_negotiation_coding, "GET", **ids).get_json()
    assert payload["team_names"] == ["Buyer", "Seller"]
    assert {c["team"] for c in payload["codes"]} == {"Buyer", "Seller"}
    assert payload["summary"]["by_team"]["Buyer"]["utterances"] == 7
    assert [p["side"] for p in payload["pods"]] == ["Seller", "Buyer"]
    swapped = _call(env, r.set_negotiation_teams, "PUT", {"teams": {"Pat": "buyer"}}, **ids)
    assert swapped.status_code == 200 and swapped.get_json()["teams"] == {"Pat": "Buyer"}


def test_join_validates_the_team_against_the_setup_and_presizes_the_roster(env):
    import pod_config
    from tables.session_device import SessionDevice
    d = env.database
    session = _session(env)
    session.passcode = "SETUP%d" % session.id
    session.pod_config = pod_config.dumps(VIKING_SETUP)
    env.db.session.commit()
    names = session.team_names()
    assert SessionDevice.verify_negotiation("Table 1", "seller", names) == (True, None, "Table 1", "Seller")
    assert SessionDevice.verify_negotiation("Table 1", "Pat", names) == (False, "Side must be Buyer or Seller.", None, None)
    assert SessionDevice.verify_negotiation("Table 1", "Pat") == (False, "Side must be Team A or Team B.", None, None)   # no setup: placeholders
    ok, device, speakers = d.create_byod_session_device(session.passcode, "", 0, "Table 1", "Seller")
    assert ok and device.name == "Table 1 Seller"
    device.connected = True
    env.db.session.commit()
    ok, message, _ = d.create_byod_session_device(session.passcode, "", 0, "Table 1", "Seller")
    assert not ok and message == "Table 1 Seller " + d.SLOT_TAKEN_SUFFIX
    ok, message, _ = d.create_byod_session_device(session.passcode, "Table 1 Seller", 0)
    assert not ok and message == "Name already in use."
    # the route pre-sizes the roster from the slot: its team's size, else the group's
    src = _read("src", "server", "routes", "session.py")
    join = _func_source(src, "byod_join_session")
    assert "target = database.get_sessions(active=True, passcode=passcode, first=True)" in join
    assert "names = target.team_names() if target is not None else None" in join
    assert "collaborators = pod_setup.speaker_slots(target.pod_config_dict(), negotiation_side)" in join
    create = _func_source(src, "create_session")
    assert "pod_setup.normalize(request.json.get('podConfig'))" in create
    assert "negotiation_paired = bool(pod_config) and pod_setup.paired(pod_config)" in create
    assert "pod_config=pod_config" in create and "negotiationPaired" not in create
    handler = _func_source(_read(*HANDLER), "create_session")
    assert "session.pod_config = pod_setup.dumps(pod_config)" in handler
    assert "negotiation_paired = pod_setup.paired(pod_config)" in handler


def test_extra_laptop_for_a_slot_is_coded_alone_and_the_pair_stays_the_first_devices(env):
    from tables.session_device import SessionDevice
    d = env.database
    session, (pat, sandy) = _paired_session(env, group="Table 5")
    extra = SessionDevice(session.id, None, "Table 5 Pat 2")
    extra.negotiation_group, extra.negotiation_side = "Table 5", "Pat"
    env.db.session.add(extra)
    env.db.session.commit()
    assert [x.id for x in d.get_negotiation_group_devices(pat)] == [pat.id, sandy.id, extra.id]
    assert env.engine.resolve_pair(pat.id) == (pat.id, sandy.id)
    assert env.engine.resolve_pair(sandy.id) == (pat.id, sandy.id)     # never paired with the extra
    assert env.engine.resolve_pair(extra.id) == (extra.id, None)       # coded alone, side stamped
    run = d.create_negotiation_run(extra.id, "m", "viking-v2")
    assert env.engine.run_sides(run) == {extra.id: "Pat"}


def test_join_as_extra_laptop_takes_the_next_free_suffix(env):
    d = env.database
    session = _session(env)
    session.passcode = "EXTRA%d" % session.id
    env.db.session.commit()
    ok, first, _ = d.create_byod_session_device(session.passcode, "", 0, "Table 1", "Pat")
    first.connected = True
    env.db.session.commit()
    ok, message, _ = d.create_byod_session_device(session.passcode, "", 0, "Table 1", "Pat")
    assert not ok and message.endswith(d.SLOT_TAKEN_SUFFIX)
    ok, second, _ = d.create_byod_session_device(session.passcode, "", 0, "Table 1", "Pat", join_as_extra=True)
    assert ok and second.name == "Table 1 Pat 2" and (second.negotiation_group, second.negotiation_side) == ("Table 1", "Pat")
    second.connected = True
    env.db.session.commit()
    ok, third, _ = d.create_byod_session_device(session.passcode, "", 0, "Table 1", "Pat", join_as_extra=True)
    assert ok and third.name == "Table 1 Pat 3"
    # a disconnected extra is resumed rather than skipped
    second.connected = False
    env.db.session.commit()
    ok, again, _ = d.create_byod_session_device(session.passcode, "", 0, "Table 1", "Pat", join_as_extra=True)
    assert ok and again.id == second.id
    # without the flag the slot stays refused; a free slot never needs it
    ok, message, _ = d.create_byod_session_device(session.passcode, "", 0, "Table 1", "Pat")
    assert not ok
    ok, other, _ = d.create_byod_session_device(session.passcode, "", 0, "Table 1", "Sandy", join_as_extra=True)
    assert ok and other.name == "Table 1 Sandy"
    src = _read("src", "server", "routes", "session.py")
    join = _func_source(src, "byod_join_session")
    assert "join_as_extra = request.json.get('joinAsExtra', False) is True" in join
    assert "'slot_taken': True}, 409)" in join


# ------------------------------------------------- coding schemes (any case)

LIVELINESS = {
    "name": "Discussion liveliness",
    "description": "Who keeps the conversation moving.",
    "context": ["The group is designing a bridge out of spaghetti."],
    "dimensions": [
        {"label": "Move", "guidance": "What the utterance does for the group.",
         "codes": [{"code": "proposes", "definition": "Offers an idea or a plan."},
                   {"code": "builds", "label": "Builds on", "definition": "Extends someone else's idea."},
                   {"code": "blocks", "definition": "Rejects without an alternative."},
                   {"code": "other", "definition": "Anything else."}]},
        {"label": "Tone", "multi": True,
         "codes": [{"code": "playful", "definition": "Jokes, laughter."},
                   {"code": "tense", "definition": "Irritation, impatience."}]},
    ],
}


def liveliness_llm(messages):
    moves = ["proposes", "builds", "blocks", "other"]
    return json.dumps([{"i": i, "move": moves[i % 4], "tone": ["playful"] if i % 3 == 0 else []}
                       for i in _code_indices(messages)])


def test_a_session_codes_with_the_scheme_it_chose(env):
    import coding_schemes as cs
    d, r, sr = env.database, env.routes, env.scheme_routes
    session = _session(env)
    pod = _pod(env, session)
    user = {"id": session.owner_id, "role": "user"}
    # the scheme is made in the Library, then the session points at it
    resp = _call(env, sr.create_coding_scheme, "POST", LIVELINESS, user=user)
    assert resp.status_code == 200, resp.get_json()
    stored = resp.get_json()
    assert stored["ref"].startswith("scheme:") and stored["name"] == "Discussion liveliness"
    assert [dim["key"] for dim in stored["dimensions"]] == ["move", "tone"]
    assert stored["dimensions"][0]["default"] == "other" and stored["dimensions"][1]["default"] is None
    assert stored["dimensions"][0]["codes"][1] == {"code": "builds", "label": "Builds on", "definition": "Extends someone else's idea.", "examples": []}
    session.coding_scheme = stored["ref"]
    session.negotiation_coding = True
    env.db.session.commit()
    assert session.json()["coding_scheme"] == stored["ref"]
    book = env.engine.codebook_for_device(pod.id)
    assert list(book["dimensions"]) == ["move", "tone"] and book["case_facts"] == LIVELINESS["context"]
    assert book["version"] == "Discussion liveliness" and book["ref"] == stored["ref"]
    assert cs.analytics(book) == {"timeline": False, "future_move": False, "dynamics": False}
    prompt = env.engine.build_prompt(book, _utterances()[:2], [])[0]["content"]
    assert "spaghetti" in prompt and '"move": "<code>"' in prompt and '"tone": ["<code>", ...]' in prompt
    assert "2 dimensions" in prompt and "Who keeps the conversation moving." in prompt

    ids = dict(session_id=session.id, session_device_id=pod.id)
    run_id = _call(env, r.start_negotiation_coding, "POST", {"teams": TEAMS}, **ids).get_json()["run_id"]
    assert d.get_negotiation_run(run_id).codebook_version == "Discussion liveliness"
    env.engine.run_coding(pod.id, llm=liveliness_llm, run_id=run_id)
    payload = _call(env, r.get_negotiation_coding, "GET", **ids).get_json()
    assert payload["codebook"]["name"] == "Discussion liveliness"
    assert [dim["key"] for dim in payload["codebook"]["dimensions"]] == ["move", "tone"]
    assert payload["codebook"]["dimensions"][0]["codes"][1]["label"] == "Builds on"
    assert set(payload["codes"][0]) == {"transcript_id", "session_device_id", "start_time", "length", "speaker_tag",
                                        "team", "text", "move", "tone"}
    assert payload["codes"][0]["move"] == "proposes" and payload["codes"][0]["tone"] == ["playful"]
    assert payload["codes"][1]["tone"] == []
    by_team = payload["summary"]["by_team"]
    assert set(by_team["Pat"]) == {"utterances", "move", "tone"}        # no opening_move: not a negotiation scheme
    assert by_team["Pat"]["move"]["proposes"] == 4 and by_team["Pat"]["tone"]["playful"] == 3
    assert payload["summary"]["timeline"] is None
    resp = _call(env, r.export_negotiation_coding, "GET", **ids)
    rows = list(csv.reader(io.StringIO(resp.data.decode("utf-8"))))
    assert rows[0] == ["transcript_id", "start_time", "length", "speaker_tag", "team", "pod", "text", "move", "tone"]
    assert rows[1][7:] == ["proposes", "playful"] and rows[2][7:] == ["builds", ""]
    # a stored row carries its codes as JSON; the Viking columns stay empty
    from tables.negotiation_code import NegotiationCode
    row = env.db.session.query(NegotiationCode).filter(NegotiationCode.run_id == run_id).first()
    assert row.values() == {"move": "proposes", "tone": ["playful"]} and row.emotion is None

    # Library routes: list (built-in first), get by ref or id, update, delete; others' schemes are invisible
    listing = _call(env, sr.list_coding_schemes, "GET", user=user).get_json()
    assert listing[0]["ref"] == "builtin:negotiation" and listing[0]["builtin"] is True
    assert [x["name"] for x in listing[1:]] == ["Discussion liveliness"] and listing[1]["owned"] is True
    assert _call(env, sr.get_coding_scheme, "GET", user=user, ref=stored["ref"]).get_json()["dimension_count"] == 2
    assert _call(env, sr.get_coding_scheme, "GET", user=user, ref=str(stored["id"])).status_code == 200
    builtin = _call(env, sr.get_coding_scheme, "GET", user=user, ref="builtin:negotiation").get_json()
    assert [dim["key"] for dim in builtin["dimensions"]] == ["emotion", "rip", "frame", "listening"]
    assert _call(env, sr.get_coding_scheme, "GET", user=user, ref="builtin:nope").status_code == 404
    stranger = {"id": session.owner_id + 1000, "role": "user"}
    assert _call(env, sr.get_coding_scheme, "GET", user=stranger, ref=stored["ref"]).status_code == 404
    assert _call(env, sr.update_coding_scheme, "PUT", dict(LIVELINESS, name="Renamed"), user=stranger, scheme_id=stored["id"]).status_code == 404
    admin = {"id": 1, "role": "admin"}
    assert _call(env, sr.update_coding_scheme, "PUT", dict(LIVELINESS, name="Renamed"), user=admin, scheme_id=stored["id"]).get_json()["name"] == "Renamed"
    assert _call(env, sr.update_coding_scheme, "PUT", {"name": ""}, user=user, scheme_id=stored["id"]).status_code == 400
    assert _call(env, sr.validate_coding_scheme, "POST", {"name": "x", "dimensions": []}, user=user).get_json() == \
        {"ok": False, "message": "A scheme needs at least one dimension."}
    assert _call(env, sr.delete_coding_scheme, "DELETE", user=stranger, scheme_id=stored["id"]).status_code == 404
    assert _call(env, sr.delete_coding_scheme, "DELETE", user=user, scheme_id=stored["id"]).status_code == 200
    # the session's coded results survive; a new run would use the built-in scheme
    assert len(_call(env, r.get_negotiation_coding, "GET", **ids).get_json()["codes"]) == 14
    assert env.engine.codebook_for_device(pod.id)["ref"] == "builtin:negotiation"


def test_create_session_route_takes_live_video_analyses():
    create = _func_source(_read("src", "server", "routes", "session.py"), "create_session")
    assert "live_video_analyses = request.json.get('liveVideoAnalyses')" in create
    assert "live_video_analytics = len(live_video_analyses) > 0" in create
    assert "live_video_analyses=live_video_analyses" in create
    handler = _func_source(_read(*HANDLER), "create_session")
    assert "session.live_video_analyses = ','.join(live_video_analyses)" in handler
    assert "'live_video_analyses': list(live_video_analyses)" in handler
    table = _read("src", "server", "tables", "session.py")
    assert "LIVE_VIDEO_ANALYSES = ('attention', 'emotion')" in table
    assert "live_video_analyses=self.live_video_analyses_list()" in table


def test_session_live_video_analyses_json(env):
    session = _session(env)
    assert session.json()["live_video_analyses"] == ["attention", "emotion"]   # NULL = both
    session.live_video_analyses = "emotion"
    assert session.json()["live_video_analyses"] == ["emotion"]
    session.live_video_analyses = ""
    assert session.json()["live_video_analyses"] == []
    session.live_video_analyses = None
    session.live_video_analytics = False
    assert session.json()["live_video_analyses"] == []


def test_create_session_route_takes_a_scheme_ref():
    create = _func_source(_read("src", "server", "routes", "session.py"), "create_session")
    assert "coding_scheme = request.json.get('codingScheme') or None" in create
    assert "coding_scheme_lib.resolve(coding_scheme, database.get_coding_scheme_dict) is None" in create
    assert "negotiation_coding = True" in create and "coding_scheme=coding_scheme" in create
    assert "coding_scheme_lib.BUILTIN_PREFIX + coding_scheme_lib.BUILTIN_NEGOTIATION" in create
    handler = _func_source(_read(*HANDLER), "create_session")
    assert "session.coding_scheme = coding_scheme" in handler and "negotiation_coding_enabled = True" in handler
    dc = _read("src", "server", "discussion_capture.py")
    assert "app.register_blueprint(coding_scheme_api)" in dc


def test_teams_are_read_off_speaker_names_when_nobody_assigned(env):
    assert nc.infer_teams(["Pat1", "pat 2", "SANDY-3", "Coach", "", None, "Patsy"], ("Pat", "Sandy")) == {
        "Pat1": "Pat", "pat 2": "Pat", "SANDY-3": "Sandy", "Patsy": "Pat"}
    assert nc.infer_teams(["Buyer A", "seller_b", "x"], ("Buyer", "Seller")) == {"Buyer A": "Buyer", "seller_b": "Seller"}
    assert nc.infer_teams(["Team A1", "teamb2", "Team"], ("Team A", "Team B")) == {"Team A1": "Team A", "teamb2": "Team B"}
    d = env.database
    session = _session(env)
    pod = _pod(env, session, with_transcripts=False)
    for i, (tag, text, _) in enumerate(VIKING):
        _add(env, pod, 15 * i, text, tag + str(i % 3 + 1))      # Pat1, Sandy2, Pat3 ...
    run = env.engine.run_coding(pod.id, llm=gold_llm)
    assert run.teams_dict() == {"Pat1": "Pat", "Sandy2": "Sandy", "Pat3": "Pat", "Sandy1": "Sandy", "Pat2": "Pat", "Sandy3": "Sandy"}
    assert run.summary_dict()["by_team"]["Pat"]["utterances"] == 7
    # an explicit assignment, even partial, is respected as given
    run2 = env.engine.run_coding(pod.id, {"Pat1": "Sandy"}, llm=gold_llm)
    assert run2.teams_dict() == {"Pat1": "Sandy"}
    # the team on an enrolled speaker's profile wins over what the name says
    ok, _ = d.add_student("Pat1", group_name="Group 4", team_name="sandy")
    assert ok
    run3 = env.engine.run_coding(pod.id, llm=gold_llm)
    assert run3.teams_dict()["Pat1"] == "Sandy" and run3.teams_dict()["Pat2"] == "Pat"
