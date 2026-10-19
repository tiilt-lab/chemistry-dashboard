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

Since 2026-10-14 the voice print is all that is kept: once a recording has
passed the gate and its embedding is cached, server.py deletes the WAV
(drop_wav_after_embedding). Cross-matching therefore reads the .emb.npy
files directly; a legacy WAV without a print is embedded on the fly.

Run `python enrollment_check.py --warm` (from this directory, service venv) to
pre-compute the cache for existing enrollments.

Expedited enrollment (enroll_take, 2026-10-19): a take recorded on a speaker
card of the BYOD join page is kept as the student's voice print when the
card's name is a registered username with no print yet. The same gate
decides, with a lower speech floor (JOIN_MIN_NET_SPEECH_SECONDS: the join
page asks for a 10 s take, the sign-up page for a coached 15 s); the sidecar
says ``"source": "join"``. An existing print is never replaced this way.
"""

import json
import logging
import os
import wave

import numpy as np
import torch

MIN_NET_SPEECH_SECONDS = 15.0
JOIN_MIN_NET_SPEECH_SECONDS = 8.0
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
                        nearest_sim=None, min_speech_seconds=None):
    """Pure verdict logic: given measured quantities, decide ok/reasons and
    build the sidecar dict. Kept separate from all I/O and the ECAPA model so
    the thresholds are unit-testable. `similar_to` is the already-computed
    list of {username, similarity} above SIMILAR_VOICE_THRESHOLD;
    `nearest_sim` is the closest other voice (may be below threshold).
    `min_speech_seconds` overrides the net-speech floor (the join page's
    expedited enrollment uses JOIN_MIN_NET_SPEECH_SECONDS)."""
    floor = MIN_NET_SPEECH_SECONDS if min_speech_seconds is None else float(min_speech_seconds)
    reasons = []
    still_needed = max(0.0, floor - speech_seconds)
    if speech_seconds < floor:
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


def enrolled_aliases(folder):
    """Every alias with a voice print (<alias>.emb.npy) or a legacy recording
    (<alias>.wav), in name order; partial takes and backups are not
    enrollments."""
    found = set()
    for name in os.listdir(folder):
        if name.endswith(_CACHE_SUFFIX):
            alias = name[:-len(_CACHE_SUFFIX)]
        elif name.endswith(".wav"):
            alias = name[:-4]
        else:
            continue
        if alias.endswith(".partial") or alias.endswith(".combined.tmp") or ".bak" in name:
            continue
        found.add(alias)
    return sorted(found)


def enrolled_embeddings(folder, model, skip_alias=None):
    """{alias: embedding} for every enrollment in ``folder``: the cached print
    where there is one, else embedded from the legacy WAV (and cached). An
    unreadable entry is logged and skipped."""
    out = {}
    for other in enrolled_aliases(folder):
        if other == skip_alias:
            continue
        cache = os.path.join(folder, other + _CACHE_SUFFIX)
        wav = os.path.join(folder, other + ".wav")
        try:
            if os.path.isfile(cache) and (not os.path.isfile(wav)
                                          or os.path.getmtime(cache) >= os.path.getmtime(wav)):
                out[other] = np.load(cache)
            elif os.path.isfile(wav):
                out[other] = _cached_embedding(wav, model)
        except Exception as e:
            logging.warning("enrollment check: skip %s: %s", other, e)
    return out


def drop_wav_after_embedding(wav_path, model=None):
    """Delete an enrollment recording once its voice print exists (computing
    the print first when it is missing and a model is given). Returns True
    when the WAV is gone; False, with the WAV kept, when no print could be
    made (the recording is then still the only copy of the enrollment)."""
    cache = os.path.splitext(wav_path)[0] + _CACHE_SUFFIX
    if not os.path.isfile(wav_path):
        return True
    if not os.path.isfile(cache):
        if model is None:
            return False
        try:
            _cached_embedding(wav_path, model)
        except Exception as e:
            logging.warning("enrollment: could not embed %s, keeping the recording: %s", wav_path, e)
            return False
        if not os.path.isfile(cache):
            return False
    try:
        os.remove(wav_path)
    except OSError as e:
        logging.warning("enrollment: could not delete %s: %s", wav_path, e)
        return False
    logging.info("enrollment: recording deleted, voice print kept for %s", os.path.basename(cache))
    return True


def drop_wavs(folder, model=None, partial_max_age_seconds=3600):
    """One-off and housekeeping: delete every enrollment WAV whose print
    exists (or can be computed when ``model`` is given) and every partial
    take older than ``partial_max_age_seconds``. Returns
    {deleted, kept, partials_deleted, kept_aliases}."""
    import time
    deleted, kept, partials, kept_aliases = 0, 0, 0, []
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".wav"):
            continue
        path = os.path.join(folder, name)
        if name.endswith(".partial.wav") or name.endswith(".combined.tmp.wav"):
            if time.time() - os.path.getmtime(path) > partial_max_age_seconds:
                os.remove(path)
                partials += 1
                stale_cache = os.path.splitext(path)[0] + _CACHE_SUFFIX
                if os.path.isfile(stale_cache):
                    os.remove(stale_cache)
            continue
        if drop_wav_after_embedding(path, model):
            deleted += 1
        else:
            kept += 1
            kept_aliases.append(name[:-4])
    return {"deleted": deleted, "kept": kept, "partials_deleted": partials, "kept_aliases": kept_aliases}


def check_enrollment(wav_path, alias, model, biometric_dir=None, min_speech_seconds=None, source=None):
    """Verdict dict for a just-saved enrollment WAV. 'ok' False means the
    recording should be discarded and re-captured; 'reasons' explains why in
    student-facing language (other students' identities stay in the log).
    ``min_speech_seconds`` lowers the speech floor (join-page takes);
    ``source`` is recorded in the sidecar ("join" for those)."""
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
    nearest_sim = None
    similar_to = []
    if full_emb is not None:
        for other_alias, other in enrolled_embeddings(biometric_dir, model, skip_alias=alias).items():
            sim = _cosine(full_emb, other)
            if nearest_sim is None or sim > nearest_sim:
                nearest_sim = sim
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
        duration_seconds=len(x) / float(sr), nearest_sim=nearest_sim,
        min_speech_seconds=min_speech_seconds)
    if source:
        verdict["source"] = source
    # Sidecar verdict so the web app can show enrollment quality without
    # loading ECAPA (the Students page reads these).
    try:
        with open(os.path.splitext(wav_path)[0] + ".check.json", "w") as f:
            json.dump(verdict, f)
    except Exception as e:
        logging.warning("enrollment check: could not write sidecar for %s: %s", alias, e)
    logging.info("enrollment check for %s: %s", alias, verdict)
    return verdict


def has_print(folder, alias):
    """Whether ``alias`` is enrolled: a voice print (<alias>.emb.npy) or a
    legacy recording (<alias>.wav) in ``folder``."""
    base = os.path.join(folder, alias)
    return os.path.isfile(base + _CACHE_SUFFIX) or os.path.isfile(base + ".wav")


def write_take_wav(path, pcm16, sample_rate):
    """A 16-bit mono WAV of raw int16 bytes (the join socket's fingerprint
    take after reformat_data)."""
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(int(sample_rate))
        w.writeframes(bytes(pcm16))


def enroll_take(alias, pcm16, sample_rate, folder, model, min_speech_seconds=JOIN_MIN_NET_SPEECH_SECONDS):
    """Expedited enrollment: keep a join-page take as ``alias``'s voice print
    when there is none. Returns {saved, reason?, verdict?}: ``exists`` when a
    print or recording is already on file (never replaced from a pod),
    ``quality`` when the gate rejected the take (nothing is left on disk),
    or saved=True with the print cached and the sidecar written, the WAV
    dropped like a sign-up enrollment's."""
    base = os.path.join(folder, alias)
    if has_print(folder, alias):
        return {"saved": False, "reason": "exists"}
    wav = base + ".wav"
    artefacts = (wav, base + _CACHE_SUFFIX, base + ".check.json")
    write_take_wav(wav, pcm16, sample_rate)
    try:
        verdict = check_enrollment(wav, alias, model, folder,
                                   min_speech_seconds=min_speech_seconds, source="join")
    except Exception:
        for p in artefacts:
            if os.path.isfile(p):
                os.remove(p)
        raise
    if verdict["ok"]:
        drop_wav_after_embedding(wav, model)
        return {"saved": True, "verdict": verdict}
    for p in artefacts:
        if os.path.isfile(p):
            os.remove(p)
    return {"saved": False, "reason": "quality", "verdict": verdict}


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
    parser.add_argument("--drop-wavs", action="store_true",
                        help="delete every enrollment recording whose voice print "
                             "exists (computing missing prints first) and stale "
                             "partial takes; keeps only <alias>.emb.npy + .check.json")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    if args.drop_wavs:
        model = SpeakerRecognition.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            savedir="pretrained_models/pretrained_ecapa")
        print(json.dumps(drop_wavs(cf.biometric_folder(), model)))
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
