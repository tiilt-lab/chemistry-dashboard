"""Vocal (speech) emotion recognition from an utterance's audio — the tone-of-
voice affect channel that complements facial emotion and text sentiment.

Lazy-loads a wav2vec2 speech-emotion model (downloaded on first use); enabled
via [processing] vocal_emotion=true with vocal_emotion_model. Best-effort: any
failure returns None rather than breaking the pipeline.
"""

import logging
import numpy as np

_MODEL = None
_MODEL_ID = None
DEFAULT_MODEL = "superb/wav2vec2-base-superb-er"


def _get_model(model_id):
    global _MODEL, _MODEL_ID
    if _MODEL is None or _MODEL_ID != model_id:
        from transformers import pipeline  # lazy: only when enabled
        _MODEL = pipeline("audio-classification", model=model_id)
        _MODEL_ID = model_id
        logging.info("Vocal-emotion model loaded (%s)", model_id)
    return _MODEL


def classify_vocal_emotion(pcm_int16_bytes, sr=16000, model_id=None):
    """Return {'label', 'score'} for an int16 PCM segment, or None."""
    try:
        x = np.frombuffer(pcm_int16_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        if x.size < sr // 5:  # < 200 ms is too short
            return None
        clf = _get_model(model_id or DEFAULT_MODEL)
        preds = clf({"array": x, "sampling_rate": sr}, top_k=1)
        if not preds:
            return None
        return {"label": preds[0]["label"], "score": round(float(preds[0]["score"]), 3)}
    except Exception as e:
        logging.warning("vocal emotion failed: %s", e)
        return None
