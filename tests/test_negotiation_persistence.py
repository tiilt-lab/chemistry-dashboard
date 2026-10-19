"""What the paired merge decided about a line is stored with its codes, so
the read-back (panel, exports) and the re-roll (PUT /teams) agree with the
summary the run computed (2026-10-19 sweep P1 #3).

Before: negotiation_code held only the dimension values; code_row rebuilt
speaker, team and start from the raw transcript row and the devices' current
sides. A cluster reconcile_clusters had renamed to the partner's student
came back under its old name, a far-side row _unflag_unplaceable had given
to its own laptop came back on the other team, and a laptop whose clock was
minutes off came back with its lines sorted after the whole conversation.

Fixtures and the app stub come from test_negotiation_coding."""
import json
import os
import re
import sys
import types
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_negotiation_coding import env, _paired_session, _session, _pod  # noqa: E402

__all__ = ["env"]   # the imported fixture is used by name in the tests below


def _code_indices(messages):
    user = next(m["content"] for m in reversed(messages) if m["role"] == "user" and "CODE (" in m["content"])
    return [int(m) for m in re.findall(r"^\[(\d+)\]", user[user.index("CODE ("):], re.M)]


def neutral_llm(messages):
    return json.dumps([{"i": i, "emotion": "neutral", "rip": "interest" if i % 2 else "none",
                        "frame": "none", "listening": []} for i in _code_indices(messages)])


def add(env, device, start, text, tag, cluster, sim=None, far_side=False, length=5):
    conf = {"cluster": cluster}
    if sim is not None:
        conf.update(sim=sim, margin=0.2, percent=100, named_by="prints")
    if far_side:
        conf["far_side"] = True
    env.database.add_transcript(device.id, start, length, text, False, 0, 0, 0, 0, 0, 0, -1, tag, -1,
                                voice_features={"confidence": conf})


def _run_pair(env, session, pat):
    first, partner = env.engine.resolve_pair(pat.id)
    run = env.engine.queue_coding_run(session.id, first, partner_device_id=partner)
    return env.engine.run_coding(pat.id, llm=neutral_llm, run_id=run.id)


def _team_counts(summary, codes):
    by_run = {t: summary["by_team"][t]["utterances"] for t in ("Pat", "Sandy")}
    by_read = {t: sum(1 for c in codes if c["team"] == t) for t in ("Pat", "Sandy")}
    return by_run, by_read


def test_a_reconciled_speaker_keeps_its_name_and_team_in_the_read_back_and_the_reroll(env):
    # The Pat laptop heard a Sandy-side voice (cluster S03) that the Sandy
    # laptop named Sand1; reconcile_clusters renames the Pat copies, and the
    # one line only the Pat laptop heard moves to Sandy's side with them.
    session, (pat, sandy) = _paired_session(env, group="Persist 1")
    add(env, pat, 0, "you went on vacation and left alex in charge", "Pat1", "S02", sim=0.968)
    add(env, pat, 10, "we were just talking to alex under confidence", "Pat2", "S03", sim=0.904)
    add(env, pat, 16, "but kinda wanna take the middleman out of this", "Pat2", "S03", sim=0.904)
    add(env, pat, 22, "get to some terms that are mutually beneficial", "Pat2", "S03", sim=0.904)
    add(env, pat, 28, "because this relationship is really important to us", "Pat2", "S03", sim=0.904)
    add(env, pat, 100, "yes we can agree to that", "Pat2", "S04", sim=0.80)
    add(env, sandy, 10.3, "we were just talking to alex under confidence", "Sand1", "S03", sim=0.943)
    add(env, sandy, 16.2, "but kinda wanna take the middleman out of this", "Sand1", "S03", sim=0.943)
    add(env, sandy, 22.1, "get to some terms that are mutually beneficial", "Sand1", "S03", sim=0.943)
    add(env, sandy, 100.4, "yes we can agree to that", None, "S05")
    run = _run_pair(env, session, pat)
    summary = run.summary_dict()
    codes = env.engine.run_payload(run)["codes"]

    by_run, by_read = _team_counts(summary, codes)
    assert by_run == {"Pat": 2, "Sandy": 2} and by_read == by_run
    assert summary["by_speaker"]["Sand1"]["utterances"] == 2
    assert Counter(c["speaker_tag"] for c in codes)["Sand1"] == 2
    lone = next(c for c in codes if c["text"].startswith("because this relationship"))
    assert (lone["speaker_tag"], lone["team"]) == ("Sand1", "Sandy")

    # PUT /teams re-rolls the stored codes: the same numbers, not the raw rows'
    after = env.engine.recompute_summary(run, {}).summary_dict()
    assert {t: after["by_team"][t]["utterances"] for t in ("Pat", "Sandy")} == by_run
    assert after["by_speaker"]["Sand1"]["utterances"] == 2


def test_aligned_clocks_are_persisted_so_the_read_back_is_the_conversation(env):
    session, (pat, sandy) = _paired_session(env, group="Persist 2", sides=("Pat", "Sandy"))
    speech = [
        "You went on vacation and left Alex in charge of the whole account",
        "That is ridiculous you signed off on the change order yourself",
        "Do you understand that I need the money by Friday or we are done",
        "If you force me into bankruptcy you may not recover the money at all",
        "I can call the loan whenever I want and you know that perfectly well",
        "Fine then tell me what is bothering you most about this arrangement",
        "What has to happen in the next fifteen days for both of us to survive",
        "How can we structure this so you can make the investment on time",
    ]
    # Pat laptop (the reference) on time; Sandy laptop stamped 191 s late
    for k, text in enumerate(speech):
        t = 100 + 20 * k
        near, far = (pat, sandy) if k % 2 == 0 else (sandy, pat)
        tag = "Pat1" if near is pat else "Sand1"
        env.database.add_transcript(near.id, t + (0.0 if near is pat else 191.0), 6, text, False,
                                    0, 0, 0, 0, 0, 0, -1, tag, -1,
                                    voice_features={"confidence": {"sim": 0.85, "margin": 0.2, "percent": 90}})
        env.database.add_transcript(far.id, t + (0.0 if far is pat else 191.0) + 0.4, 6, text, False,
                                    0, 0, 0, 0, 0, 0, -1, tag, -1,
                                    voice_features={"confidence": {"sim": 0.5, "margin": 0.1, "percent": 50,
                                                                   "closed_world": True}})
    run = _run_pair(env, session, pat)
    summary = run.summary_dict()
    assert summary["cross_talk"]["alignment"]["method"] == "text"
    codes = env.engine.run_payload(run)["codes"]
    # the lines alternate as spoken, on one clock (the 191 s taken out)
    assert [c["team"] for c in codes] == ["Pat", "Sandy"] * 4
    starts = [c["start_time"] for c in codes]
    assert starts == sorted(starts) and max(starts) < 300
    # the opening moves the run reported survive a re-roll
    keys = ("opening_move", "first_interest_question")
    before = {t: tuple(summary["by_team"][t][k] for k in keys) for t in ("Pat", "Sandy")}
    rerolled = env.engine.recompute_summary(run, {}).summary_dict()
    assert {t: tuple(rerolled["by_team"][t][k] for k in keys) for t in ("Pat", "Sandy")} == before


def test_a_laptop_that_named_nobody_keeps_its_rows_on_its_own_side_in_the_read_back(env):
    session, (pat, sandy) = _paired_session(env, group="Persist 3")
    add(env, pat, 0, "We need the money by Friday or the deal is off", None, "S01", far_side=True, length=4)
    add(env, pat, 20, "That is not what the contract says at all", None, "S01", far_side=True, length=4)
    add(env, pat, 40, "Fine, we can slow this down for a minute", "Sandy 1", "S02", sim=0.7, far_side=True, length=4)
    add(env, sandy, 0.5, "We need the money by Friday", None, "S05", length=3)
    add(env, sandy, 40.2, "Fine, we can slow this down for a minute", "Sandy 1", "S02", sim=0.9, length=4)
    run = _run_pair(env, session, pat)
    summary = run.summary_dict()
    codes = env.engine.run_payload(run)["codes"]
    by_run, by_read = _team_counts(summary, codes)
    assert by_run["Pat"] == 2 and by_read == by_run


def test_a_single_pod_run_is_still_re_teamed_by_the_assignment_at_read_time(env):
    # Unpaired: the instructor assigns speaker tags to teams after the run,
    # so the team stored at coding time must not freeze the read-back.
    session = _session(env)
    pod = _pod(env, session)
    run = env.engine.queue_coding_run(session.id, pod.id)
    run = env.engine.run_coding(pod.id, llm=neutral_llm, run_id=run.id)
    names = env.engine.run_names(run)
    tags = sorted({c["speaker_tag"] for c in env.engine.run_payload(run)["codes"] if c["speaker_tag"]})
    assert len(tags) >= 2
    for flip in (0, 1):
        teams = {tag: names[(i + flip) % 2] for i, tag in enumerate(tags)}
        run = env.engine.recompute_summary(run, teams)
        codes = env.engine.run_payload(run)["codes"]
        assert codes and all(c["team"] == teams.get(c["speaker_tag"], "unassigned") for c in codes)
        counted = sum(run.summary_dict()["by_team"][n]["utterances"] for n in names)
        assert counted == sum(1 for c in codes if c["speaker_tag"] in teams)


def test_code_row_falls_back_to_the_transcript_row_for_runs_stored_before_the_attribution(env):
    # Rows written before 2026-10-19 carry only the dimension values.
    engine = env.engine
    transcript = types.SimpleNamespace(id=7, session_device_id=3, start_time=12.5, length=4.0,
                                       speaker_tag="Pat2", transcript="the stored words", voice_features=None)
    old = types.SimpleNamespace(values=lambda: {"emotion": "neutral", "rip": "none", "frame": "none", "listening": []})
    row = engine.code_row(old, transcript, teams={"Pat2": "Pat"}, sides={3: "Pat"}, names=("Pat", "Sandy"))
    assert (row["speaker_tag"], row["team"], row["start_time"], row["text"]) == ("Pat2", "Pat", 12.5, "the stored words")
    new = types.SimpleNamespace(values=lambda: {"emotion": "neutral", "rip": "none", "frame": "none", "listening": [],
                                                "_speaker_tag": "Sand1", "_team": "Sandy", "_start": 203.5,
                                                "_length": 4.0, "_device": 3, "_text": "the words the model saw"})
    row = engine.code_row(new, transcript, teams={"Pat2": "Pat"}, sides={3: "Pat"}, names=("Pat", "Sandy"))
    assert (row["speaker_tag"], row["team"], row["start_time"], row["text"]) == \
        ("Sand1", "Sandy", 203.5, "the words the model saw")
    assert "_team" not in row and "_start" not in row
