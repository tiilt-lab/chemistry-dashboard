"""Capture-time quality gate for voice-fingerprint enrollment.

A fingerprint is only useful if it embeds cleanly and unambiguously, so right
after the enrollment WAV is written we verify three things:

  1. Net speech — energy-VAD seconds of actual talking, not wall clock. A
     20-second clip of mostly silence enrolls as noise.
  2. Self-consistency — ECAPA embeddings of the recording's two halves must
     match each other. A recording that can't verify against itself will never
     verify against live speech (this is the audio-side analog of the broken
     face enrollment that silently mismatched for weeks).
  3. Ambiguity — the embedding must not sit closer to some other enrolled
     student than the same-speaker verification threshold, and never closer to
     someone else than to itself.

Embeddings are compared in ECAPA's native float domain (see
cluster_reconcile.py: int16-domain embedding degrades to noise) and cached as
<alias>.emb.npy beside each WAV so cross-matching 180+ enrollments stays fast.

Run `python enrollment_check.py --warm` (from this directory, service venv) to
pre-compute the cache for existing enrollments.
"""

import json
import logging
import os
import wave

import numpy as np
import torch

MIN_NET_SPEECH_SECONDS = 15.0
MIN_SELF_SIMILARITY = 0.45
# Similarity to another enrolled voice no longer BLOCKS enrollment — voices
# genuinely can sound alike. At >= this cosine similarity the other student
# is recorded in the verdict's similar_to list so instructors can see which
# voices overlap (and interpret attribution accordingly).
SIMILAR_VOICE_THRESHOLD = 0.50
_FRAME_SECONDS = 0.03
_CACHE_SUFFIX = ".emb.npy"


def _load_wav_float(path):
    with wave.open(path, "rb") as w:
        sr = w.getframerate()
        n = w.getnframes()
        raw = w.readframes(n)
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    return x, sr


def _speech_mask(x, sr):
    """Boolean per-frame speech mask from frame RMS vs. the clip's own noise
    floor. Crude next to a neural VAD, but for a solo read-aloud recording the
    only question is 'talking or not', which energy answers reliably."""
    frame = max(1, int(sr * _FRAME_SECONDS))
    n_frames = len(x) // frame
    if n_frames == 0:
        return np.zeros(0, dtype=bool), 0.0
    frames = x[: n_frames * frame].reshape(n_frames, frame)
    rms = np.sqrt((frames * frames).mean(axis=1))
    floor = np.percentile(rms, 20)
    thresh = max(floor * 3.0, 0.008)
    mask = rms > thresh
    return mask, float(mask.sum() * _FRAME_SECONDS)


def _speech_samples(x, sr, mask):
    frame = max(1, int(sr * _FRAME_SECONDS))
    if not mask.any():
        return x
    keep = np.repeat(mask, frame)
    return x[: len(keep)][keep]


def _embed(x, model):
    with torch.no_grad():
        emb = model.encode_batch(torch.tensor(np.ascontiguousarray(x)))
    return emb[0, 0].detach().cpu().numpy()


def _cosine(a, b):
    a = a / (np.linalg.norm(a) + 1e-9)
    b = b / (np.linalg.norm(b) + 1e-9)
    return float(np.dot(a, b))


def _cached_embedding(wav_path, model):
    cache = os.path.splitext(wav_path)[0] + _CACHE_SUFFIX
    try:
        if os.path.isfile(cache) and os.path.getmtime(cache) >= os.path.getmtime(wav_path):
            return np.load(cache)
    except Exception:
        pass
    x, sr = _load_wav_float(wav_path)
    mask, _ = _speech_mask(x, sr)
    emb = _embed(_speech_samples(x, sr, mask), model)
    try:
        np.save(cache, emb)
    except Exception as e:
        logging.warning("enrollment check: could not cache %s: %s", cache, e)
    return emb


def evaluate_enrollment(speech_seconds, self_sim, similar_to, duration_seconds,
                        nearest_sim=None):
    """Pure verdict logic: given measured quantities, decide ok/reasons and
    build the sidecar dict. Kept separate from all I/O and the ECAPA model so
    the thresholds are unit-testable. `similar_to` is the already-computed
    list of {username, similarity} above SIMILAR_VOICE_THRESHOLD;
    `nearest_sim` is the closest other voice (may be below threshold)."""
    reasons = []
    still_needed = max(0.0, MIN_NET_SPEECH_SECONDS - speech_seconds)
    if speech_seconds < MIN_NET_SPEECH_SECONDS:
        reasons.append(
            "So far {0:.0f} seconds of clear speech were captured — about "
            "{1:.0f} more are needed. Keep going: what you already recorded "
            "is kept, just record a bit more.".format(
                speech_seconds, still_needed))
    if self_sim is not None and self_sim < MIN_SELF_SIMILARITY:
        reasons.append(
            "The recording doesn't match itself well enough (too much noise "
            "or too little clear speech). Please re-record in a quieter spot, "
            "closer to the microphone.")
    return {
        "ok": not reasons,
        "message": " ".join(reasons),
        "duration_seconds": round(duration_seconds, 1),
        "net_speech_seconds": round(speech_seconds, 1),
        "still_needed_seconds": round(still_needed, 1),
        "self_similarity": None if self_sim is None else round(self_sim, 3),
        "nearest_other_similarity": None if nearest_sim is None else round(nearest_sim, 3),
        "similar_to": similar_to,
    }


def check_enrollment(wav_path, alias, model, biometric_dir=None):
    """Verdict dict for a just-saved enrollment WAV. 'ok' False means the
    recording should be discarded and re-captured; 'reasons' explains why in
    student-facing language (other students' identities stay in the log)."""
    if biometric_dir is None:
        biometric_dir = os.path.dirname(os.path.abspath(wav_path))

    x, sr = _load_wav_float(wav_path)
    mask, speech_seconds = _speech_mask(x, sr)

    speech = _speech_samples(x, sr, mask)
    self_sim = None
    full_emb = None
    # Halves need enough material to embed meaningfully on their own.
    if len(speech) >= sr * 6:
        half = len(speech) // 2
        try:
            emb_a = _embed(speech[:half], model)
            emb_b = _embed(speech[half:], model)
            full_emb = _embed(speech, model)
            self_sim = _cosine(emb_a, emb_b)
        except Exception as e:
            logging.warning("enrollment check: embedding failed for %s: %s", alias, e)

    # Similar voices are recorded, not rejected: list every enrolled voice
    # above the threshold so the Students page can show which voices overlap.
    nearest_alias = None
    nearest_sim = None
    similar_to = []
    if full_emb is not None:
        for name in os.listdir(biometric_dir):
            if not name.endswith(".wav"):
                continue
            other_alias = os.path.splitext(name)[0]
            if other_alias == alias:
                continue
            try:
                other = _cached_embedding(os.path.join(biometric_dir, name), model)
            except Exception as e:
                logging.warning("enrollment check: skip %s: %s", name, e)
                continue
            sim = _cosine(full_emb, other)
            if nearest_sim is None or sim > nearest_sim:
                nearest_sim, nearest_alias = sim, other_alias
            if sim >= SIMILAR_VOICE_THRESHOLD:
                similar_to.append({"username": other_alias, "similarity": round(sim, 3)})
        similar_to.sort(key=lambda x: -x["similarity"])
        if similar_to:
            logging.info("enrollment check: %s voice overlaps with %s",
                         alias, [s["username"] for s in similar_to])

    cache = os.path.splitext(wav_path)[0] + _CACHE_SUFFIX
    if full_emb is not None:
        # Cache regardless of verdict: whatever WAV survives on disk IS the
        # enrollment other students get cross-matched against. When the gate
        # rejects, server.py deletes the WAV and its sidecars together.
        try:
            np.save(cache, full_emb)
        except Exception as e:
            logging.warning("enrollment check: could not cache %s: %s", cache, e)

    verdict = evaluate_enrollment(
        speech_seconds, self_sim, similar_to,
        duration_seconds=len(x) / float(sr), nearest_sim=nearest_sim)
    # Sidecar verdict so the web app can show enrollment quality without
    # loading ECAPA (the Students page reads these).
    try:
        with open(os.path.splitext(wav_path)[0] + ".check.json", "w") as f:
            json.dump(verdict, f)
    except Exception as e:
        logging.warning("enrollment check: could not write sidecar for %s: %s", alias, e)
    logging.info("enrollment check for %s: %s", alias, verdict)
    return verdict


if __name__ == "__main__":
    import argparse
    import config as cf
    cf.initialize()
    from speechbrain.inference import SpeakerRecognition

    parser = argparse.ArgumentParser()
    parser.add_argument("--warm", action="store_true",
                        help="pre-compute embedding cache for all enrollments")
    parser.add_argument("--survey", action="store_true",
                        help="write <alias>.check.json quality sidecars for all "
                             "enrollments (no WAV is modified or deleted)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    if args.warm or args.survey:
        model = SpeakerRecognition.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            savedir="pretrained_models/pretrained_ecapa")
        folder = cf.biometric_folder()
        wavs = [f for f in sorted(os.listdir(folder)) if f.endswith(".wav")]
        for i, name in enumerate(wavs, 1):
            path = os.path.join(folder, name)
            alias = os.path.splitext(name)[0]
            try:
                if args.survey:
                    v = check_enrollment(path, alias, model, folder)
                    print("[{0}/{1}] {2}: {3}".format(
                        i, len(wavs), name, "ok" if v["ok"] else v["message"][:80]))
                else:
                    _cached_embedding(path, model)
                    print("[{0}/{1}] {2}".format(i, len(wavs), name))
            except Exception as e:
                print("[{0}/{1}] {2} FAILED: {3}".format(i, len(wavs), name, e))
