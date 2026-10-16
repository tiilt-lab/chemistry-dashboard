"""Batched window embeddings in segment_split (audit B.4).

_window_votes used to call encode_batch once per 1 s window (~30 per
segment). The equal-length windows now go through ONE encode_batch call;
rows are independent in ECAPA so the result matches per-window encodes.
Uses a fake encoder (no model, no GPU).
"""
import os
import sys

import pytest

np = pytest.importorskip("numpy")
torch = pytest.importorskip("torch")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "audio_processing"))

from speaker_diarization import segment_split as ss  # noqa: E402

SR = ss.SR


class FakeEcapa:
    """Deterministic per-row embedding [mean, std, max]; (T,) or (B, T) in,
    (B, 1, 3) out — the shape contract of speechbrain's encode_batch."""

    def __init__(self, fail_batched=False):
        self.calls = []
        self.fail_batched = fail_batched

    def encode_batch(self, sig):
        self.calls.append(tuple(sig.shape))
        if sig.dim() == 1:
            sig = sig.unsqueeze(0)
        elif self.fail_batched:
            raise RuntimeError("CUDA error: out of memory")
        emb = torch.stack([sig.mean(dim=1), sig.std(dim=1), sig.max(dim=1).values], dim=1)
        return emb.unsqueeze(1)


def _audio(seconds, seed=0):
    rng = np.random.RandomState(seed)
    return (rng.randn(int(seconds * SR)) * 3000).astype(np.int16)


def test_batched_embeddings_equal_per_clip_embeddings():
    m = FakeEcapa()
    clips = [_audio(1.0, s) for s in range(5)]
    batched = ss._embed_batch(clips, m)
    assert m.calls == [(5, SR)]
    single = [ss._embed(c, FakeEcapa()) for c in clips]
    for b, s in zip(batched, single):
        assert np.allclose(b, s, atol=1e-6)
        assert abs(np.linalg.norm(b) - 1.0) < 1e-5


def test_unequal_lengths_fall_back_to_per_clip():
    m = FakeEcapa()
    out = ss._embed_batch([_audio(1.0), _audio(0.9)], m)
    assert len(out) == 2 and m.calls == [(SR,), (int(0.9 * SR),)]
    assert ss._embed_batch([], m) == []


def test_window_votes_make_one_encode_call_for_all_windows(monkeypatch):
    m = FakeEcapa()
    monkeypatch.setattr(ss, "_score_prints", lambda utt, fp, v: [(0.9, "ann", "1")])
    votes = ss._window_votes(_audio(6.0), {"1": {"alias": "ann"}}, m)
    # 1 s windows at a 0.5 s hop over 6 s -> 11 windows, ONE batched encode
    assert len(votes) == 11
    assert m.calls == [(11, SR)]
    assert [v[1] for v in votes] == ["ann"] * 11
    assert [round(v[0], 2) for v in votes][:3] == [0.5, 1.0, 1.5]


def test_a_failed_batch_degrades_to_per_window_encodes(monkeypatch):
    m = FakeEcapa(fail_batched=True)
    monkeypatch.setattr(ss, "_score_prints", lambda utt, fp, v: [(0.9, "ann", "1")])
    votes = ss._window_votes(_audio(3.0), {"1": {"alias": "ann"}}, m)
    assert len(votes) == 5
    assert m.calls[0] == (5, SR) and m.calls[1:] == [(SR,)] * 5
    assert all(v[1] == "ann" for v in votes)


def test_a_window_whose_scoring_fails_abstains_alone(monkeypatch):
    m = FakeEcapa()
    n = {"i": 0}

    def scorer(utt, fp, v):
        n["i"] += 1
        if n["i"] == 2:
            raise ValueError("boom")
        return [(0.9, "ann", "1")]

    monkeypatch.setattr(ss, "_score_prints", scorer)
    votes = ss._window_votes(_audio(2.0), {"1": {"alias": "ann"}}, m)
    assert [v[1] for v in votes] == ["ann", None, "ann"]
    assert votes[1][2] == 0.0


# ---------------------------------------------------------------- changes

def _voice(seconds, mean, scale, seed):
    """A 'speaker' for FakeEcapa: noise with its own mean and spread, so its
    windows embed to one direction and another speaker's to another."""
    rng = np.random.RandomState(seed)
    return (rng.randn(int(seconds * SR)) * scale + mean).astype(np.int16)


def _words(seg_start, seconds, every=0.5):
    n = int(seconds / every)
    return [("w%d" % i, seg_start + i * every, seg_start + (i + 1) * every - 0.05) for i in range(n)]


def test_change_points_find_every_turn_without_the_roster():
    # A (4 s), B (4 s), A (4 s): two boundaries near 4 and 8 s, found from
    # the embeddings alone.
    clip = np.concatenate([_voice(4, 3000, 800, 1), _voice(4, -6000, 300, 2), _voice(4, 3000, 800, 3)])
    centers, embs = ss._window_embeddings(clip, FakeEcapa())
    cps = ss._change_points(centers, embs)
    assert len(cps) == 2, cps
    assert abs(cps[0] - 4.0) <= 0.6 and abs(cps[1] - 8.0) <= 0.6, cps
    # one voice throughout: nothing
    one = _voice(12, 3000, 800, 4)
    assert ss._change_points(*ss._window_embeddings(one, FakeEcapa())) == []


def test_split_attributes_each_turn_and_leaves_the_far_side_unnamed(monkeypatch):
    # The roster knows A only; B is the other team. The segment still splits
    # at both turns, A's parts are named and B's part is left unnamed rather
    # than given A's name.
    clip = np.concatenate([_voice(4, 3000, 800, 1), _voice(4, -6000, 300, 2), _voice(4, 3000, 800, 3)])
    seg_start = 100.0
    words = _words(seg_start, 12.0)

    def fake_check(raw, fingerprints, verification):
        x = np.frombuffer(raw, dtype=np.int16)
        return ("A", 7, {"sim": 0.8}) if x.mean() > 0 else (None, -1, None)

    monkeypatch.setattr(ss.pyd, "checkFingerprints", fake_check)
    monkeypatch.setattr(ss, "_score_prints", lambda utt, fp, v: [(0.5, "A", 7)] if utt[0] > 0 else [])
    parts = ss.split_and_attribute(clip, words, seg_start, seg_start + 12.0, {7: {"alias": "A", "data": b""}}, FakeEcapa())
    assert [p["alias"] for p in parts] == ["A", None, "A"]
    # the cuts fall on the word boundaries nearest 4 s and 8 s (within a word)
    cuts = [p["text_slice"][1] for p in parts[:-1]]
    assert abs(cuts[0] - 8) <= 1 and abs(cuts[1] - 16) <= 1, cuts
    assert [p["text_slice"][0] for p in parts] == [0] + cuts and parts[-1]["text_slice"][1] == 24
    assert parts[0]["start"] == seg_start and parts[-1]["end"] == seg_start + 12.0
    assert parts[1]["start"] == words[cuts[0]][1] and parts[0]["end"] == words[cuts[0] - 1][2]


def test_split_keeps_one_part_when_the_voice_does_not_change(monkeypatch):
    clip = _voice(12, 3000, 800, 4)
    monkeypatch.setattr(ss.pyd, "checkFingerprints", lambda raw, fp, v: ("A", 7, {"sim": 0.9}))
    monkeypatch.setattr(ss, "_score_prints", lambda utt, fp, v: [(0.9, "A", 7)])
    parts = ss.split_and_attribute(clip, _words(0.0, 12.0), 0.0, 12.0, {7: {"alias": "A", "data": b""}}, FakeEcapa())
    assert len(parts) == 1 and parts[0]["alias"] == "A" and parts[0]["text_slice"] == (0, 24)


def test_a_change_too_close_to_the_edge_is_not_a_part(monkeypatch):
    # B speaks for half a second at the very end: shorter than MIN_PART_S, so
    # it folds into A's part instead of becoming a sliver.
    clip = np.concatenate([_voice(11.5, 3000, 800, 1), _voice(0.5, -6000, 300, 2)])
    monkeypatch.setattr(ss.pyd, "checkFingerprints", lambda raw, fp, v: ("A", 7, {"sim": 0.9}))
    monkeypatch.setattr(ss, "_score_prints", lambda utt, fp, v: [(0.9, "A", 7)])
    parts = ss.split_and_attribute(clip, _words(0.0, 12.0), 0.0, 12.0, {7: {"alias": "A", "data": b""}}, FakeEcapa())
    assert len(parts) == 1 and parts[0]["text_slice"] == (0, 24)
# ------------------------------------------------------------ far side

def test_a_far_side_winner_is_named_without_a_local_speaker_id(monkeypatch):
    clip = _audio(3, seed=11)
    utt = ss._embed(clip, FakeEcapa())                      # exactly what the matcher will embed
    refs = {"A": np.array([1.0, 0.0, 0.0]), "B": utt}       # B (the far side) is a perfect match
    monkeypatch.setattr(ss.pyd, "_print_embedding", lambda alias, raw, v: refs.get(alias))
    ss.pyd._SESSION_ACC.clear()
    roster = {7: {"alias": "A", "data": b"x"}, "far:B": {"alias": "B", "data": None, "far_side": True}}
    alias, sid, conf = ss.pyd.checkFingerprints(clip.tobytes(), roster, FakeEcapa())
    assert alias == "B" and sid == -1 and conf["far_side"] is True and conf["sim"] >= 0.99
    # an own-team winner keeps its local id and no far_side flag
    refs["A"], refs["B"] = utt, np.array([1.0, 0.0, 0.0])
    alias, sid, conf = ss.pyd.checkFingerprints(clip.tobytes(), roster, FakeEcapa())
    assert alias == "A" and sid == 7 and "far_side" not in conf
    ss.pyd._SESSION_ACC.clear()


def test_roster_merges_own_and_far_side_speakers():
    src = open(os.path.join(os.path.dirname(__file__), "..", "src", "audio_processing", "processor.py")).read()
    assert "def setFarSideSpeakers(self, aliases):" in src and "def roster(self):" in src
    assert src.count("self.roster()") == 2                  # split_and_attribute and checkFingerprints
    srv = open(os.path.join(os.path.dirname(__file__), "..", "src", "audio_processing", "server.py")).read()
    assert "(body or {}).get('partner_speakers')" in srv and "callbacks.get_partner_speakers" in srv
    cb = open(os.path.join(os.path.dirname(__file__), "..", "src", "audio_processing", "callbacks.py")).read()
    assert "def get_partner_speakers(source):" in cb and "'/partner_speakers/'" in cb
    route = open(os.path.join(os.path.dirname(__file__), "..", "src", "server", "routes", "callback.py")).read()
    assert "'/api/v1/callback/partner_speakers/<path:key>'" in route
    assert "json_response({'partner_speakers': database.partner_speaker_aliases(session_device)})" in route
