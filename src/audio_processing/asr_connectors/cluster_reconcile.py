"""Map pyannote diarization clusters to a pod's enrolled voice prints.

When a pod's participants are known (enrolled fingerprints), we can collapse
generic SPEAKER_NN clusters onto real people: for each cluster, embed its audio
with the same ECAPA model used for fingerprinting and match it to the nearest
enrolled voice. Used only when [processing] diarization_constrain_to_enrolled is
on. Best-effort — any failure leaves the original cluster label untouched.
"""

import logging
import numpy as np
import torch


def _cosine(a, b):
    a = a / (np.linalg.norm(a) + 1e-9)
    b = b / (np.linalg.norm(b) + 1e-9)
    return float(np.dot(a, b))


def _embed_int16(pcm_bytes, speaker_model):
    # int16 PCM bytes -> float32 [-1,1] tensor. Embedding from an integer-read
    # of a float32-wav degraded to noise (verified: sim -0.08 vs 0.39 float),
    # so all reconciliation embedding happens in ECAPA's native float domain.
    sig = torch.tensor(np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0)
    emb = speaker_model.encode_batch(sig)
    return emb[0, 0].detach().cpu().numpy()


def _embed_float(audio_f32, speaker_model):
    emb = speaker_model.encode_batch(torch.tensor(np.ascontiguousarray(audio_f32)))
    return emb[0, 0].detach().cpu().numpy()


def build_cluster_to_enrolled_map(audio_file, turns, enrolled, speaker_model,
                                  min_similarity=0.25):
    """Return {cluster_label: enrolled_alias} for clusters whose aggregate voice
    matches an enrolled speaker above min_similarity. Unmatched clusters are
    omitted (callers keep the original SPEAKER_NN label).

    turns:    iterable of (start_seconds, end_seconds, cluster_label)
    enrolled: {id: {'alias': str, 'data': int16 PCM bytes}}
    """
    if not enrolled or speaker_model is None:
        return {}
    try:
        import soundfile as sf
    except Exception as e:
        logging.warning("cluster reconcile: soundfile unavailable (%s)", e)
        return {}

    # Enrolled reference embeddings, keyed by alias.
    ref = {}
    for info in enrolled.values():
        alias = info.get('alias')
        try:
            ref[alias] = _embed_int16(info['data'], speaker_model)
        except Exception as e:
            logging.warning("cluster reconcile: enrolled embed failed for %s: %s", alias, e)
    if not ref:
        return {}

    try:
        audio, sr = sf.read(audio_file, dtype='float32', always_2d=False)
    except Exception as e:
        logging.warning("cluster reconcile: could not read %s: %s", audio_file, e)
        return {}
    if getattr(audio, 'ndim', 1) > 1:
        audio = audio[:, 0]

    # Concatenate each cluster's audio.
    by_cluster = {}
    for start, end, label in turns:
        i0, i1 = int(start * sr), int(end * sr)
        if i1 > i0:
            by_cluster.setdefault(label, []).append(audio[i0:i1])

    mapping = {}
    for label, segs in by_cluster.items():
        try:
            emb = _embed_float(np.concatenate(segs), speaker_model)
        except Exception as e:
            logging.warning("cluster reconcile: cluster embed failed for %s: %s", label, e)
            continue
        best_alias, best_sim = None, -1.0
        for alias, r in ref.items():
            s = _cosine(emb, r)
            if s > best_sim:
                best_alias, best_sim = alias, s
        if best_alias is not None and best_sim >= min_similarity:
            mapping[label] = best_alias
            logging.info("diarization: cluster %s -> %s (sim %.3f)", label, best_alias, best_sim)
        else:
            logging.info("diarization: cluster %s left generic (best sim %.3f)", label, best_sim)
    return mapping
