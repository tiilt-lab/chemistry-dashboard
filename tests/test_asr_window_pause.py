"""Pause-aligned live ASR windows (src/audio_processing/asr_ingest.py
WindowAssembler, and the carry seam in asr_connectors/crisperwhisper_asr.py).

The old assembler closed a window every 12 s of samples, blind to speech, so
a word under the cut was heard in halves and dropped: on session 434, laptop
1436, 60 of 481 rows ran to the 12 s cap and "you guys have taken" vanished
at the 81868 s cut while the partner laptop, cutting half a second later,
kept it. The assembler now scores every 0.5 s frame as it arrives and cuts
at the first pause once the window is WINDOW seconds long; a talker who never
pauses is cut at CAP seconds, at the quietest frame, and the last CARRY
seconds are heard again by the next window, whose seam duplicates the
connector drops by word end time. Legacy settings (WINDOW = CAP, CARRY 0)
are the old blind cut.
"""
import logging
import os
import queue
import sys
import wave

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "audio_processing"))

import asr_ingest as ai  # noqa: E402
from asr_ingest import (EnergyGate, SileroDetector, StampedChunk, Window, WindowAssembler,  # noqa: E402
                        make_frame_scorer, window_settings)
from asr_connectors import crisperwhisper_asr as cw  # noqa: E402

SR = 16000
F = 4000            # samples per cut-search frame (0.25 s)
S = lambda seconds: int(seconds * SR)  # noqa: E731


def pcm(seconds, value=0):
    return value.to_bytes(2, "little", signed=True) * S(seconds)


class LoudnessScorer:
    """1 for a frame holding any non-zero sample, 0 for digital silence."""
    name = "loudness"

    def __init__(self):
        self.frames = 0

    def frame_score(self, frame):
        self.frames += 1
        return 1.0 if any(frame) else 0.0


class ScheduledScorer:
    """Scores by frame index (then 1.0): a stand-in for a talker's profile."""
    name = "scheduled"

    def __init__(self, scores):
        self.scores = list(scores)
        self.frames = 0

    def frame_score(self, frame):
        i = self.frames
        self.frames += 1
        return self.scores[i] if i < len(self.scores) else 1.0


def assembler(scorer=None, **kw):
    settings = dict(window_seconds=10.0, cap_seconds=16.0, carry_seconds=1.0, quiet=0.5)
    settings.update(kw)
    return WindowAssembler(SR, 2, frame_scorer=scorer, **settings)


def feed(a, pieces, chunk=0.5, offset=0):
    """Contiguous ``[(seconds, value)]`` audio fed in stamped half-second
    chunks from sample ``offset``; returns the windows the assembler emitted."""
    data = b"".join(pcm(s, v) for s, v in pieces)
    out, step = [], S(chunk) * 2
    for i in range(0, len(data), step):
        out += a.add(StampedChunk(data[i:i + step], offset + i // 2))
    return out


def shape(windows):
    return [(w[0], len(w[1]) / 2 / SR, getattr(w, "overlap", 0.0), getattr(w, "capped", False))
            for w in windows]


# --- the cut -------------------------------------------------------------------

def test_the_cut_lands_in_the_pause_once_the_window_is_long_enough():
    a = assembler(LoudnessScorer())
    out = feed(a, [(10.4, 1000), (1.2, 0), (10.4, 1000)])
    # frame [10.0, 10.5) still holds speech; [10.5, 11.0) is the pause
    assert shape(out) == [(0.0, 10.5, 0.0, False)]
    assert out[0][1] == pcm(10.4, 1000) + pcm(0.1)
    tail = a.flush()
    assert shape([tail]) == [(10.5, 11.5, 0.0, False)]      # starts where the first ended
    assert tail[1] == pcm(1.1) + pcm(10.4, 1000)


def test_a_pause_before_the_shortest_window_does_not_cut():
    a = assembler(LoudnessScorer())
    out = feed(a, [(5.0, 1000), (0.5, 0), (7.5, 1000), (0.5, 0), (6.5, 1000)])
    assert shape(out) == [(0.0, 13.0, 0.0, False)]        # the pause at 5.0 is too early


def test_a_cut_is_never_earlier_than_the_shortest_window_with_a_pause_frame_straddling_it():
    a = assembler(LoudnessScorer(), window_seconds=10.25)
    out = feed(a, [(9.9, 1000), (0.5, 0), (4.6, 1000)])
    # the silent frame [10.0, 10.25) starts before 10.25: not a candidate; [10.25, 10.5)
    # holds speech again from 10.4, and 15 s is short of the cap, so nothing closes
    assert out == []
    assert a.flush() == (0.0, pcm(9.9, 1000) + pcm(0.5) + pcm(4.6, 1000))


def test_no_pause_cuts_at_the_cap_at_the_quietest_frame_and_carries_a_second():
    scores = [0.9] * 64
    scores[50] = 0.7                                     # frame [12.5, 12.75): least speech, not a pause
    a = assembler(ScheduledScorer(scores))
    out = feed(a, [(24.0, 1000)])
    # the cap (16 s) is reached without a pause: cut in front of the quietest frame, carry 1 s
    assert shape(out) == [(0.0, 12.5, 0.0, True)]
    tail = a.flush()
    assert shape([tail]) == [(11.5, 12.5, 1.0, False)]   # starts 1 s before the cut; the cut's last second again
    assert out[0][1] == pcm(12.5, 1000) and tail[1] == pcm(12.5, 1000)


def test_evenly_loud_speech_is_cut_at_the_shortest_window_with_a_carry():
    a = assembler(ScheduledScorer([0.9] * 200))
    out = feed(a, [(40.0, 1000)])
    assert shape(out) == [(0.0, 10.0, 0.0, True), (9.0, 10.0, 1.0, True), (18.0, 10.0, 1.0, True)]
    assert shape([a.flush()]) == [(27.0, 13.0, 1.0, False)]
    # every window starts at the true offset of its first sample, carry included
    assert out[1][1] == pcm(10.0, 1000)


def test_cut_points_and_carry_sit_on_the_frame_grid():
    a = assembler(LoudnessScorer(), cap_seconds=15.7, carry_seconds=0.7)
    assert a.cap_samples == S(15.5) and a.carry_samples == S(0.75)  # cap rounds down, carry to the nearest frame
    a = assembler(LoudnessScorer(), window_seconds=12.0, cap_seconds=12.0, carry_seconds=11.9)
    assert a.carry_samples == S(11.75)                              # a carry never swallows the whole window


def test_legacy_settings_are_the_old_blind_cut():
    a = assembler(LoudnessScorer(), window_seconds=12.0, cap_seconds=12.0, carry_seconds=0.0)
    out = feed(a, [(10.0, 1000), (2.0, 0), (26.0, 1000)])
    assert shape(out) == [(0.0, 12.0, 0.0, False), (12.0, 12.0, 0.0, False), (24.0, 12.0, 0.0, False)]
    assert a.flush() == (36.0, pcm(2.0, 1000))


def test_without_a_scorer_the_window_closes_at_the_shortest_length_blind():
    a = assembler(None)
    out = feed(a, [(10.0, 1000), (2.0, 0), (20.0, 1000)])
    assert shape(out) == [(0.0, 10.0, 0.0, False), (10.0, 10.0, 0.0, False), (20.0, 10.0, 0.0, False)]
    assert not a.scoring


def test_a_scorer_that_cannot_be_built_falls_back_to_blind_cuts(caplog):
    def boom():
        raise ImportError("no silero here")

    a = WindowAssembler(SR, 2, window_seconds=10.0, cap_seconds=16.0, carry_seconds=1.0,
                        scorer_factory=boom)
    with caplog.at_level(logging.WARNING):
        out = feed(a, [(20.0, 1000)])
    assert shape(out) == [(0.0, 10.0, 0.0, False), (10.0, 10.0, 0.0, False)]
    assert any("no silero here" in r.getMessage() for r in caplog.records)
    assert not a.scoring


def test_a_scorer_that_fails_later_falls_back_to_blind_cuts(caplog):
    class Broken:
        name = "broken"

        def __init__(self):
            self.calls = 0

        def frame_score(self, frame):
            self.calls += 1
            if self.calls > 3:
                raise RuntimeError("onnx exploded")
            return 1.0

    a = assembler(Broken())
    with caplog.at_level(logging.WARNING):
        out = feed(a, [(20.0, 1000)])
    assert shape(out) == [(0.0, 10.0, 0.0, False), (10.0, 10.0, 0.0, False)]
    assert any("onnx exploded" in r.getMessage() for r in caplog.records)


def test_the_scorer_is_built_lazily_on_the_first_chunk_and_sees_every_frame_once():
    built = []

    def factory():
        s = LoudnessScorer()
        built.append(s)
        return s

    a = WindowAssembler(SR, 2, window_seconds=10.0, cap_seconds=16.0, carry_seconds=1.0,
                        scorer_factory=factory)
    assert not built
    feed(a, [(10.4, 1000), (1.2, 0), (10.4, 1000)])
    assert len(built) == 1 and built[0].frames == 88        # 22 s = 88 frames, none rescored after the cut


# --- gaps (unchanged) ------------------------------------------------------------

def test_a_short_gap_is_zero_filled_and_is_a_fine_place_to_cut():
    a = assembler(LoudnessScorer())
    a.add(StampedChunk(pcm(10.5, 1000), 0))
    out = a.add(StampedChunk(pcm(10.0, 1000), S(11.0)))     # the chunk at [10.5, 11.0) was dropped
    # the zero-filled frame scores silent: the window ends in front of it, on the clock
    assert shape(out) == [(0.0, 10.5, 0.0, False)]
    assert a.flush() == (10.5, pcm(0.5) + pcm(10.0, 1000))


def test_a_long_gap_closes_the_window_and_restarts_at_the_new_offset():
    a = assembler(LoudnessScorer())
    a.add(StampedChunk(pcm(3.0, 1000), 0))
    out = a.add(StampedChunk(pcm(0.5, 1000), S(30.0)))      # 27 s missing
    assert shape(out) == [(0.0, 3.0, 0.0, False)]
    assert a.flush() == (30.0, pcm(0.5, 1000))


def test_a_long_gap_after_a_cap_cut_flushes_the_carried_audio_marked_as_overlap():
    a = assembler(ScheduledScorer([0.9] * 200))
    out = feed(a, [(16.0, 1000)])                            # the cap: cut at 10 s with a 1 s carry
    assert shape(out) == [(0.0, 10.0, 0.0, True)]
    out = a.add(StampedChunk(pcm(0.5, 1000), S(40.0)))       # 24 s missing
    assert shape(out) == [(9.0, 7.0, 1.0, False)]            # the carry and what followed, still marked
    assert a.flush() == (40.0, pcm(0.5, 1000))


def test_unstamped_bytes_are_treated_as_contiguous():
    a = assembler(LoudnessScorer())
    a.add(pcm(10.4, 1000))
    out = a.add(pcm(1.2))
    assert shape(out) == [(0.0, 10.5, 0.0, False)]


# --- settings -------------------------------------------------------------------

def test_window_settings_defaults_and_legacy_values():
    assert window_settings({}) == {"window_seconds": 10.0, "cap_seconds": 16.0,
                                   "carry_seconds": 1.0, "quiet": 0.5}
    legacy = window_settings({"DC_ASR_WINDOW_SECONDS": "12", "DC_ASR_WINDOW_CAP_SECONDS": "12",
                              "DC_ASR_WINDOW_CARRY_SECONDS": "0"})
    assert legacy == {"window_seconds": 12.0, "cap_seconds": 12.0, "carry_seconds": 0.0, "quiet": 0.5}


def test_window_settings_rejects_nonsense_with_a_warning(caplog):
    with caplog.at_level(logging.WARNING):
        s = window_settings({"DC_ASR_WINDOW_SECONDS": "ten", "DC_ASR_WINDOW_CAP_SECONDS": "4",
                             "DC_ASR_WINDOW_CARRY_SECONDS": "-1", "DC_ASR_WINDOW_QUIET": "1.5"})
    assert s == {"window_seconds": 10.0, "cap_seconds": 10.0, "carry_seconds": 1.0, "quiet": 0.5}
    messages = [r.getMessage() for r in caplog.records]
    assert any("DC_ASR_WINDOW_SECONDS='ten'" in m for m in messages)
    assert any("DC_ASR_WINDOW_CAP_SECONDS=4 is below" in m for m in messages)
    assert any("DC_ASR_WINDOW_CARRY_SECONDS=-1" in m for m in messages)
    assert any("DC_ASR_WINDOW_QUIET=1.5" in m for m in messages)


def test_the_connector_reads_the_settings_and_builds_the_scorer_lazily(monkeypatch):
    monkeypatch.setenv("DC_ASR_WINDOW_SECONDS", "8")
    monkeypatch.setenv("DC_ASR_WINDOW_CAP_SECONDS", "14")
    asr = cw.CrisperWhisperASR(queue.Queue(), queue.Queue(), None, "audio", 0.25)
    assert asr.WINDOW_SECONDS == 8.0                         # the caption-lag proxy sees the configured window
    assert asr._assembler.window_samples == S(8) and asr._assembler.cap_samples == S(14)
    assert asr._assembler.carry_samples == S(1.0) and not asr._assembler.scoring
    assert asr._assembler._scorer_factory is ai.make_frame_scorer


# --- frame scores ---------------------------------------------------------------

def to_pcm(x):
    return (np.clip(np.asarray(x, dtype=np.float32), -1, 1) * 32767).astype("<i2").tobytes()


def at_db(x, db):
    rms = np.sqrt(np.mean(np.square(x))) or 1.0
    return (x / rms * 10 ** (db / 20.0)).astype(np.float32)


def burst(seconds=0.5, db=-25.0):
    t = np.arange(S(seconds)) / SR
    return at_db(np.sin(2 * np.pi * 150 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 4 * t)), db)


def test_energy_frame_score_is_one_for_speech_zero_for_silence_and_between_in_the_middle():
    g = EnergyGate()
    assert g.frame_score(to_pcm(np.zeros(F, np.float32))) == 0.0
    assert g.frame_score(to_pcm(burst())) == 1.0              # -25 dBFS clears the ceiling whatever the room
    assert g.frame_score(to_pcm(burst(0.25))) == 1.0          # the cut search's quarter-second frame
    assert g.frame_score(b"") == 1.0                          # nothing to judge: never a cut point
    for _ in range(40):                                        # a -55 dBFS room: floor learned
        g.frame_score(to_pcm(burst(db=-55.0)))
    on, off = g.thresholds()
    mid = g.frame_score(to_pcm(burst(db=(on + off) / 2)))
    assert 0.0 < mid < 1.0


def test_energy_frame_score_feeds_the_level_history():
    g = EnergyGate()
    assert g.noise_floor_db is None
    g.frame_score(to_pcm(burst(db=-50.0)))
    assert g.noise_floor_db is not None


def test_silero_frame_score_is_the_highest_chunk_probability_and_streams_without_a_reset():
    seen = []

    def prob(chunk):
        seen.append(len(chunk))
        return [0.1, 0.2, 0.8, 0.3][len(seen) % 4]

    d = SileroDetector(chunk_prob=prob)
    assert d.frame_score(to_pcm(np.zeros(F, np.float32))) == 0.8
    assert len(seen) == 7 and set(seen) == {512}              # 7 whole chunks of a quarter-second frame
    assert d.frame_score(to_pcm(np.zeros(100, np.float32))) == 1.0  # shorter than a chunk


def test_make_frame_scorer_follows_the_vad_mode():
    assert make_frame_scorer("off") is None
    assert make_frame_scorer(environ={"DC_ASR_VAD": "off"}) is None
    assert make_frame_scorer("energy").name == "energy"
    if ai.silero_available():
        assert make_frame_scorer("silero").name == "silero"
    with pytest.raises(ValueError):
        make_frame_scorer("loud")


# --- the carry seam in the connector -------------------------------------------

def test_seam_words_split_the_carry_by_where_a_word_ends():
    words = [["that", 15.5, 15.7], ["you", 15.8, 16.05]]
    capped = Window(0.0, b"", capped=True)
    assert cw._seam_words(words, capped, 16.0) == [["that", 15.5, 15.7]]   # "you" may be clipped
    following = Window(15.0, b"", overlap=1.0)
    words = [["that", 0.5, 0.7], ["you", 0.8, 1.0], ["guys", 1.05, 1.3]]
    assert cw._seam_words(words, following, 12.0) == [["you", 0.8, 1.0], ["guys", 1.05, 1.3]]
    assert cw._seam_words(words, (15.0, b""), 12.0) == words   # a plain tuple: nothing known, nothing dropped
    assert cw._seam_words(words, Window(15.0, b""), 12.0) == words


class WordedPool:
    """A pool whose results are scripted per call (window-relative words)."""

    def __init__(self, results):
        self.results = list(results)
        self.lengths = []

    def transcribe(self, wav_path):
        with wave.open(wav_path, "rb") as w:
            self.lengths.append(w.getnframes())
        return {"words": self.results.pop(0)}


def run_flush(monkeypatch, windows, results):
    pool = WordedPool(results)
    monkeypatch.setattr(cw, "_pool", pool)
    transcripts = queue.Queue()
    asr = cw.CrisperWhisperASR(queue.Queue(), transcripts, None, "audio", 0.25)
    asr.gate_factory = lambda: None
    for w in windows:
        asr._window_queue.put(w)
    asr._window_queue.put(None)
    asr._transcribing()
    out = []
    while True:
        r = transcripts.get_nowait()
        if r is None:
            break
        alt = r.alternatives[0]
        out.append((alt.transcript, [(w.word, round(w.start_time.seconds + w.start_time.nanos / 1e9, 2))
                                     for w in alt.words]))
    return pool, out


def test_the_word_under_a_cap_cut_is_emitted_once_whole_from_the_window_that_heard_it(monkeypatch):
    # laptop 1436 at the 81868 s cut: "...ill-intent actions that | you guys have taken"
    windows = [Window(81852.0, pcm(16.0, 1000), capped=True),
               Window(81867.0, pcm(12.0, 1000), overlap=1.0)]
    results = [[["ill-intent", 14.0, 14.8], ["actions", 14.9, 15.4], ["that", 15.5, 15.7], ["you", 15.85, 16.0]],
               [["that", 0.5, 0.7], ["you", 0.85, 1.0], ["guys", 1.05, 1.3], ["have", 1.35, 1.5],
                ["taken", 1.55, 1.9]]]
    pool, out = run_flush(monkeypatch, windows, results)
    assert pool.lengths == [S(16.0), S(12.0)]
    assert [text for text, _ in out] == ["ill-intent actions that", "you guys have taken"]
    assert out[1][1][0] == ("you", 81867.85)                  # on the session clock, from the second window


def test_a_plain_tuple_window_is_transcribed_as_before(monkeypatch):
    pool, out = run_flush(monkeypatch, [(12.0, pcm(12.0, 1000))], [[["hi", 0.0, 0.5], ["there", 0.6, 1.0]]])
    assert out == [("hi there", [("hi", 12.0), ("there", 12.6)])]
