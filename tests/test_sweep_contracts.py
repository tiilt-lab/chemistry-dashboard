"""Source-level contract tests guarding today's fixes against regression.

These assert on the source text (like test_contracts.py) for changes whose
runtime needs a GPU, a live DB, or Flask — too heavy for CI, but the fix is a
specific line that a careless edit could silently revert. Each test names the
bug it locks in.
"""
import os
import re

SRC = os.path.join(os.path.dirname(__file__), "..", "src")


def _read(*parts):
    with open(os.path.join(SRC, *parts)) as f:
        return f.read()


# ---- audio pipeline correctness ------------------------------------------

def test_embed_signal_uses_float_domain():
    # Clustering embeddings must be float-domain (/32768.0); raw int16 was
    # measured as degraded and the merge gate is calibrated in float space.
    s = _read("audio_processing", "speaker_diarization", "pyDiarization.py")
    m = re.search(r"def embedSignal\(.*?encode_batch", s, re.S)
    assert m, "embedSignal signature changed"
    assert "/ 32768.0" in m.group(0), "embedSignal must normalize int16 to float"


def test_embeddings_loaded_with_allow_pickle():
    # The embeddings file is an object array; np.load without allow_pickle
    # raises and every session resume silently restarted from [].
    for mod in ("processor.py", "processor_posthoc.py"):
        s = _read("audio_processing", mod)
        assert "allow_pickle=True" in s, f"{mod}: embeddings load must allow_pickle"


def test_topic_selection_tracks_best_probability():
    # topic_id must be the argmax, not the last topic with p>0 (the old loop
    # never updated its running max).
    for mod in ("processor.py", "processor_posthoc.py"):
        s = _read("audio_processing", mod)
        assert "best_prob" in s, f"{mod}: topic loop must track best probability"


def test_diarization_flag_not_hardcoded_true():
    s = _read("audio_processing", "processing_config.py")
    assert "self.diarization = diarization" in s
    assert "self.diarization = True" not in s, "diarization must not be hardcoded on"


# ---- realtime / reactor safety -------------------------------------------

def test_worker_thread_sends_use_call_from_thread():
    # Twisted transports are not thread-safe; worker-thread sends must go
    # through reactor.callFromThread.
    checks = [
        ("audio_processing", "processor_posthoc.py"),
        ("audio_processing", "processor_speaker_metric.py"),
        ("audio_processing", "audio_stream_reader.py"),
        ("video_processing", "facial_biometric_processing_service.py"),
        ("server", "device_websockets.py"),
    ]
    for parts in checks:
        s = _read(*parts)
        assert "callFromThread" in s, f"{'/'.join(parts)}: send must use callFromThread"


# ---- authorization (round-3 security fixes) ------------------------------

def test_transcript_mutations_are_session_scoped():
    s = _read("server", "routes", "speaker.py")
    # both reassign and edit_text must scope through the owning session.
    assert s.count("session_write_allowed") >= 2, \
        "reassign/edit_text must both check session_write_allowed"


def test_remove_device_checks_session_membership():
    s = _read("server", "routes", "session.py")
    m = re.search(r"def remove_device_from_session\(.*?\):(.*?)def ", s, re.S)
    assert m and "session_id" in m.group(1) and "404" in m.group(1), \
        "remove_device_from_session must reject a pod from another session"


def test_updatestudent_is_no_longer_open():
    s = _read("server", "routes", "student.py")
    m = re.search(r"def update_students\(.*?\):(.*?)\n@api_routes", s, re.S)
    assert m, "update_students not found"
    body = m.group(1)
    assert "is_admin" in body and "name_ok" in body, \
        "updatestudent must gate non-admins behind a name-match"


def test_delete_user_removes_metrics_before_devices():
    # SpeakerVideoMetrics/HrMetrics FK session_device with no cascade — they
    # must be deleted before the SessionDevice bulk delete or delete_user 500s.
    s = _read("server", "database.py")
    m = re.search(r"def delete_user\(.*?db\.session\.commit\(\)", s, re.S)
    assert m, "delete_user not found"
    body = m.group(0)
    vid = body.index("SpeakerVideoMetrics")
    dev = body.index("query(SessionDevice)")
    assert vid < dev, "video metrics must be deleted before SessionDevice"


def test_connected_flag_cleared_on_session_end_and_removal():
    s = _read("server", "handlers", "session_handler.py")
    assert s.count("connected = False") >= 2, \
        "end_session and remove_session_device must both clear connected"
