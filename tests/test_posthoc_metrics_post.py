"""The post-hoc metrics post (src/audio_processing/speaker_metrics/speaker_metrics.py,
processor_posthoc._publish, server_posthoc's roster): a roster with no voice
prints still counts its members, the metrics never carry NaN or infinity, and
the publish counts only what landed. On 2026-10-18 pod 1447's roster had no
enrolment prints, the metrics divided by zero participants, every post was
refused as non-JSON, and the run still reported 1129 of 1129 posted."""
import json
import os
import sys
import types

import numpy as np

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "src", "audio_processing"))
sys.path.insert(0, os.path.join(ROOT, "src", "common"))


class _Model:
    def encode(self, text):
        v = np.zeros(4, dtype=float); v[len(text) % 4] = 1.0
        return v

    def similarity(self, a, b):
        return float(np.dot(a, b))


def _payload(start, text, speaker_id=-1):
    return {"source": "k", "start_time": start, "end_time": start + 2, "transcript": text, "doa": None, "questions": [],
            "keywords": [], "features": None, "topic_id": -1, "speaker_tag": None, "speaker_id": speaker_id, "voice_features": None}


def test_metrics_with_an_empty_roster_stay_finite_and_report_the_post(monkeypatch):
    from speaker_metrics import speaker_metrics as sm
    posted = []
    # whichever `callbacks` module an earlier test left bound, the post goes here
    monkeypatch.setattr(sm, "callbacks", types.SimpleNamespace(
        post_speaker_transcript_metrics=lambda data, *metrics: posted.append(metrics) or True))
    proc = sm.SpeakerProcessor(types.SimpleNamespace(auth_key="k"), _Model())
    proc.setSpeakers({})
    results = [proc.process_transcript(_payload(10 * i, "line %d" % i), action="posthoc_processing") for i in range(5)]
    assert results == [True] * 5 and len(posted) == 5
    for metrics in posted:
        json.dumps(metrics, allow_nan=False)          # what requests requires of the payload
    assert all(np.isfinite(v) for v in posted[-1][3] + posted[-1][4])


def test_a_refused_post_is_reported_as_false(monkeypatch):
    from speaker_metrics import speaker_metrics as sm
    monkeypatch.setattr(sm, "callbacks", types.SimpleNamespace(post_speaker_transcript_metrics=lambda data, *metrics: False))
    proc = sm.SpeakerProcessor(types.SimpleNamespace(auth_key="k"), _Model())
    proc.setSpeakers({7: {"alias": "Ann", "data": b""}})
    assert proc.process_transcript(_payload(0, "hello", speaker_id=7), action="posthoc_processing") is False


def test_the_publish_counts_only_landed_posts_and_fails_short():
    src = open(os.path.join(ROOT, "src", "audio_processing", "processor_posthoc.py")).read()
    body = src[src.index("    def _publish(self):"):src.index("    def _abandon(")]
    # rows are built in discussion order (the metrics are cumulative), then posted in batches
    assert 'self.speaker_metrics_process.metrics_payload(payload, action="posthoc_processing")' in body
    assert "callbacks.post_transcripts_batch(self.config.auth_key, batch) is None" in body
    assert "raise RuntimeError('posted %d of %d utterances'" in body


def test_a_roster_member_without_a_print_is_kept_for_the_metrics():
    src = open(os.path.join(ROOT, "src", "audio_processing", "server_posthoc.py")).read()
    i = src.index("except (FileNotFoundError, wave.Error) as e:")
    block = src[i:i + 900]
    assert "byte_audio_data = b''" in block and "continue" not in block.split("self.speakers[speaker")[0]


def test_metrics_payload_is_what_the_post_would_send_without_posting(monkeypatch):
    from speaker_metrics import speaker_metrics as sm
    import importlib.util
    # the audio tree's callbacks by path: the video tree binds the same name
    spec = importlib.util.spec_from_file_location(
        "audio_callbacks_for_test", os.path.join(ROOT, "src", "audio_processing", "callbacks.py"))
    audio_callbacks = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audio_callbacks)
    posted = []
    monkeypatch.setattr(sm, "callbacks", types.SimpleNamespace(
        speaker_metrics_payload=audio_callbacks.speaker_metrics_payload,
        post_speaker_transcript_metrics=lambda data, *metrics: posted.append(metrics) or True))
    proc = sm.SpeakerProcessor(types.SimpleNamespace(auth_key="k"), _Model())
    proc.setSpeakers({7: {"alias": "Ann", "data": b""}})
    rows = [proc.metrics_payload(_payload(10 * i, "line %d" % i, speaker_id=7)) for i in range(3)]
    assert posted == [] and [r["start_time"] for r in rows] == [0, 10, 20]
    assert rows[-1]["speakers"] == [7] and len(rows[-1]["participation_scores"]) == 2
    json.dumps(rows, allow_nan=False)
    # the live path still computes the same arrays and posts them itself
    assert proc.process_transcript(_payload(30, "line 3", speaker_id=7)) is True and len(posted) == 1
