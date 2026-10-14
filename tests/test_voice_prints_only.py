"""Only the voice print (<alias>.emb.npy) is kept after enrollment; the
recording is deleted once the print exists (src/audio_processing/
enrollment_check.py), and every consumer tolerates a print-only enrollment."""
import os
import sys
import time
import wave

import numpy as np
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "audio_processing"))

try:
    import enrollment_check as ec
except Exception as e:  # pragma: no cover
    pytest.skip("enrollment_check deps unavailable: %s" % e, allow_module_level=True)


class _Model:
    # Embeds by signal energy so two different recordings get different prints.
    def encode_batch(self, x):
        import torch
        v = torch.zeros(1, 1, 4)
        v[0, 0, 0] = float(x.abs().mean())
        v[0, 0, 1] = 1.0
        return v


def _wav(path, level=0.3, seconds=2.0):
    sr = 16000
    t = np.arange(int(sr * seconds)) / sr
    x = (level * np.sin(2 * np.pi * 220 * t) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(x.tobytes())


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def test_enrolled_aliases_come_from_prints_or_legacy_wavs_never_partials(tmp_path):
    np.save(tmp_path / "ann.emb.npy", np.ones(4))
    _wav(str(tmp_path / "bob.wav"))
    np.save(tmp_path / "cat.partial.emb.npy", np.ones(4))
    _wav(str(tmp_path / "dan.partial.wav"))
    _wav(str(tmp_path / "eve.combined.tmp.wav"))
    np.save(tmp_path / "fay.emb.npy.bak-20260720", np.ones(4))
    (tmp_path / "gus.check.json").write_text("{}")
    assert ec.enrolled_aliases(str(tmp_path)) == ["ann", "bob"]


def test_enrolled_embeddings_prefer_the_print_and_embed_a_legacy_wav(tmp_path):
    folder = str(tmp_path)
    np.save(tmp_path / "ann.emb.npy", np.array([0.5, 0.5, 0, 0]))
    _wav(os.path.join(folder, "bob.wav"))
    embs = ec.enrolled_embeddings(folder, _Model(), skip_alias="zed")
    assert set(embs) == {"ann", "bob"}
    assert np.allclose(embs["ann"], [0.5, 0.5, 0, 0])
    assert (tmp_path / "bob.emb.npy").exists()         # the legacy WAV got its print cached
    assert embs["bob"][1] == 1.0 and embs["bob"][0] > 0
    assert set(ec.enrolled_embeddings(folder, _Model(), skip_alias="ann")) == {"bob"}


def test_drop_wav_after_embedding_keeps_the_recording_only_when_no_print_can_be_made(tmp_path):
    wav = str(tmp_path / "ann.wav")
    _wav(wav)
    assert ec.drop_wav_after_embedding(wav, model=None) is False      # no print, no model: kept
    assert os.path.exists(wav)
    assert ec.drop_wav_after_embedding(wav, model=_Model()) is True    # print computed, then deleted
    assert not os.path.exists(wav) and (tmp_path / "ann.emb.npy").exists()
    assert ec.drop_wav_after_embedding(wav, model=None) is True        # already gone
    _wav(wav)
    assert ec.drop_wav_after_embedding(wav, model=None) is True        # print exists: deleted straight away
    assert not os.path.exists(wav)


def test_drop_wavs_sweeps_the_folder_and_stale_partials(tmp_path):
    folder = str(tmp_path)
    _wav(os.path.join(folder, "ann.wav"))
    np.save(tmp_path / "ann.emb.npy", np.ones(4))
    _wav(os.path.join(folder, "bob.wav"))                       # no print, no model: kept
    _wav(os.path.join(folder, "old.partial.wav"))
    np.save(tmp_path / "old.partial.emb.npy", np.ones(4))
    stale = time.time() - 7200
    os.utime(os.path.join(folder, "old.partial.wav"), (stale, stale))
    _wav(os.path.join(folder, "fresh.partial.wav"))
    report = ec.drop_wavs(folder, model=None, partial_max_age_seconds=3600)
    assert report == {"deleted": 1, "kept": 1, "partials_deleted": 1, "kept_aliases": ["bob"]}
    assert sorted(os.listdir(folder)) == ["ann.emb.npy", "bob.wav", "fresh.partial.wav"]
    report = ec.drop_wavs(folder, model=_Model(), partial_max_age_seconds=3600)
    assert report["deleted"] == 1 and report["kept"] == 0
    assert sorted(os.listdir(folder)) == ["ann.emb.npy", "bob.emb.npy", "fresh.partial.wav"]


def test_every_consumer_tolerates_a_print_only_enrollment():
    server = _read("src", "audio_processing", "server.py")
    assert "enrollment_check.drop_wav_after_embedding(audio_fingerprint_file, diarization_model)" in server
    assert "if os.path.isfile(audio_fingerprint_file + '.emb.npy'):\n                    byte_audio_data = b''" in server
    posthoc = _read("src", "audio_processing", "server_posthoc.py")
    assert "if os.path.isfile(audio_fingerprint_file + '.emb.npy'):\n                                    byte_audio_data = b''" in posthoc
    reconcile = _read("src", "audio_processing", "asr_connectors", "cluster_reconcile.py")
    assert "pyd._print_embedding(alias, None, speaker_model)" in reconcile
    assert "if emb is None and info.get('data'):" in reconcile
    check = _read("src", "audio_processing", "enrollment_check.py")
    assert "enrolled_embeddings(biometric_dir, model, skip_alias=alias)" in check
    assert '"--drop-wavs"' in check
    student = _read("src", "server", "routes", "student.py")
    assert "'voice_enrolled': os.path.isfile(_voice_print_path(safe)) or os.path.isfile(wav)" in student
    assert "'voice_sample_available': os.path.isfile(wav)" in student
    assert "Voice recordings are not kept; only the voice print is stored." in student
    card = _read("frontend", "src", "components", "voice-quality.jsx")
    assert "student.voice_sample_available ? (" in card
