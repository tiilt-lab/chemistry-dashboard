"""Tests for the de-forked live/posthoc pipeline helpers
(src/audio_processing/processing_common.py, architecture fix #4).

These three pieces were maintained in two copies (processor.py and
processor_posthoc.py) and drifted: today the SAME bug was fixed twice in each
of the topic-argmax loop, the embeddings save (dtype=object), and the load
(allow_pickle). They now live once; these tests pin the behavior.
"""
import os
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "audio_processing"))

from processing_common import select_topic_id, save_embeddings, load_embeddings  # noqa: E402


def test_select_topic_id_picks_argmax_not_last_positive():
    # The historical bug: never updating the running max, so the LAST topic
    # with p>0 won, not the most probable.
    topics = [(7, 0.1), (3, 0.8), (5, 0.2)]
    assert select_topic_id(topics) == 3


def test_select_topic_id_empty_returns_default():
    assert select_topic_id([]) == -1
    assert select_topic_id([], default=None) is None


def test_select_topic_id_all_zero_returns_default():
    assert select_topic_id([(1, 0.0), (2, 0.0)]) == -1


def test_select_topic_id_single():
    assert select_topic_id([(9, 0.5)]) == 9


def test_embeddings_roundtrip_object_array():
    # The utterance embeddings are dicts of varied shape -> object array; a
    # naive np.load (no allow_pickle) refuses them, which silently dropped
    # every resume. save/load must round-trip.
    embeddings = [
        {"embedding": np.zeros(4, dtype=np.float32), "start": 0.0, "end": 1.0},
        {"embedding": np.ones(4, dtype=np.float32), "start": 1.0, "end": 2.5},
    ]
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "emb.npy")
        save_embeddings(path, embeddings)
        loaded = load_embeddings(path)
    assert len(loaded) == 2
    assert loaded[0]["start"] == 0.0 and loaded[1]["end"] == 2.5
    assert np.array_equal(loaded[1]["embedding"], np.ones(4, dtype=np.float32))


def test_load_embeddings_missing_file_raises():
    # Callers wrap this in try/except and restart from []; it must raise (not
    # silently return []) so that contract is explicit.
    import pytest
    with pytest.raises(Exception):
        load_embeddings("/nonexistent/does/not/exist.npy")


def test_both_processors_use_the_shared_helpers_not_inline_copies():
    # Contract: neither processor may re-inline the drift-prone logic; both
    # must call processing_common. Guards against the fork reopening.
    src = os.path.join(os.path.dirname(__file__), "..", "src", "audio_processing")
    for mod in ("processor.py", "processor_posthoc.py"):
        with open(os.path.join(src, mod)) as f:
            text = f.read()
        assert "from processing_common import" in text, f"{mod}: must import shared helpers"
        assert "select_topic_id(" in text, f"{mod}: must use shared topic argmax"
        assert "save_embeddings(" in text, f"{mod}: must use shared embeddings save"
        assert "load_embeddings(" in text, f"{mod}: must use shared embeddings load"
        # The inline copies (drift sources) must be gone.
        assert "dtype=object" not in text, f"{mod}: inline object-array save re-appeared"
        assert "allow_pickle" not in text.replace(
            "allow_pickle required", ""), f"{mod}: inline allow_pickle load re-appeared"
