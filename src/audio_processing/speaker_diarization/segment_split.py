"""Interruption handling for live attribution.

Tier 1 — split at the speaker changes: most classroom "interruption" is
rapid alternation, not sustained double-talk. A short embedding window
slides across the segment. Where the voice on one side of a point stops
resembling the voice on the other (the cosine distance between the mean
embeddings of the windows just before and just after rises past
CHANGE_DISTANCE), the segment is split at the nearest word boundary and
each part is attributed independently -- clean rows instead of one smeared
name. The detection reads the embeddings themselves, not the roster, so it
finds any number of turns and finds the other team's speaker even though
no enrolled print matches them (that part is left unnamed rather than
given the nearest own-team name). A sustained flip of the best-matching
print is still taken as a boundary too.

Tier 2 — name the overlap: when two participants BOTH score strongly across
the same span (true simultaneous speech), the span is marked contested with
both names instead of silently abstaining. For collaboration analytics an
overlap is signal, not noise.

Pure logic; depends only on pyDiarization's print scoring so it can be tested
offline against retained recordings.
"""
import logging

import numpy as np
import torch

from . import pyDiarization as pyd

SR = 16000
WIN_S = 1.0          # sliding embedding window — must be SHORTER than a
                     # conversational turn or every window mixes two voices
HOP_S = 0.5
MIN_SPLIT_S = 3.0    # segments shorter than this are single-decision
MIN_PART_S = 1.5     # never emit a fragment shorter than this (a name needs that much voice)
WIN_FLOOR = 0.15     # a window vote needs at least this sim to count
CONTEST_FLOOR = 0.25   # both voices at/above this across the span -> contested
CONTEST_SHARE = 0.25   # each contested voice must win >= this share of windows
CHANGE_CONTEXT = 2     # windows on each side of a point that are compared ...
CHANGE_DISTANCE = 0.4  # ... and the cosine distance between their means that marks a change
# Measured on 2026-10-16's recordings (ECAPA, 1 s windows, 0.5 s hop): within
# ONE speaker the boundary score has a median of 0.37 and reaches 0.84; a real
# change peaks at 0.85-0.99. The distributions overlap, so no threshold tells
# them apart and the roster-free cut chopped sentences into one-second pieces
# that were then named unreliably (test session 436: 1.7 s average piece
# against 4.6 s before). Off until a trained segmentation model replaces it
# (pyannote segmentation 3.0 or NeMo Sortformer, both in the post-hoc venvs).
EMBEDDING_CHANGE_POINTS = False


def _embed(int16_audio, verification):
    sig = torch.tensor(int16_audio.astype(np.float32) / 32768.0)
    emb = verification.encode_batch(sig)[0, 0].detach().cpu().numpy()
    return emb / (np.linalg.norm(emb) + 1e-9)


def _embed_batch(clips, verification):
    """Unit embeddings for a list of clips in ONE encode_batch call when they
    are equal length (the sliding windows always are; audit B.4: ~30 separate
    encodes per segment). ECAPA's per-utterance feature norm and length-masked
    pooling make rows independent, so this equals per-clip encodes up to float
    rounding. Unequal lengths (a lone short clip) fall back to per-clip."""
    if not clips:
        return []
    if len({len(c) for c in clips}) == 1:
        sig = torch.tensor(np.stack([c.astype(np.float32) / 32768.0 for c in clips]))
        embs = verification.encode_batch(sig)[:, 0].detach().cpu().numpy()
        return [e / (np.linalg.norm(e) + 1e-9) for e in embs]
    return [_embed(c, verification) for c in clips]


def _score_prints(utt, fingerprints, verification):
    """[(sim, alias, speaker_id)] against the pod's prints, including any
    session-adapted references (same logic the whole-segment matcher uses)."""
    scored = []
    for speaker in fingerprints:
        info = fingerprints[speaker]
        alias = info.get('alias')
        ref = pyd._print_embedding(alias, info.get('data'), verification)
        if ref is None:
            continue
        sim = float(np.dot(utt, ref))
        acc = pyd._SESSION_ACC.get(alias)
        if acc and len(acc) >= pyd.ADAPT_MIN_SAMPLES:
            sref = np.mean(acc, axis=0)
            sref = sref / (np.linalg.norm(sref) + 1e-9)
            sim = max(sim, float(np.dot(utt, sref)))
        scored.append((sim, alias, speaker))
    scored.sort(reverse=True, key=lambda s: s[0])
    return scored


def _window_embeddings(int16_audio, verification):
    """(centers, unit embeddings or None) for the sliding windows of a clip."""
    n = len(int16_audio)
    win, hop = int(WIN_S * SR), int(HOP_S * SR)
    clips, centers = [], []
    pos = 0
    while pos + win <= n or (pos == 0 and n >= int(MIN_PART_S * SR)):
        clips.append(int16_audio[pos:pos + win] if pos + win <= n else int16_audio)
        centers.append(pos / SR + WIN_S / 2)
        pos += hop
        if pos + win > n and pos > 0:
            break
    # One batched encode for all windows; if the batch itself fails, degrade
    # to per-window encodes so a single bad window still only costs its vote.
    try:
        embs = _embed_batch(clips, verification)
    except Exception:
        embs = []
        for clip in clips:
            try:
                embs.append(_embed(clip, verification))
            except Exception:
                embs.append(None)
    return centers, embs


def _window_votes(int16_audio, fingerprints, verification, windows=None):
    """Per-window winner labels across the clip: [(t_center, alias|None, sim)].
    ``windows``: (centers, embs) already computed, else computed here."""
    centers, embs = windows if windows is not None else _window_embeddings(int16_audio, verification)
    votes = []
    for t, utt in zip(centers, embs):
        scored = []
        if utt is not None:
            try:
                scored = _score_prints(utt, fingerprints, verification)
            except Exception:
                scored = []
        if scored and scored[0][0] >= WIN_FLOOR:
            votes.append((t, scored[0][1], scored[0][0]))
        else:
            votes.append((t, None, 0.0))
    return votes


def _change_points(centers, embs, context=CHANGE_CONTEXT, distance=CHANGE_DISTANCE,
                   min_part_s=MIN_PART_S):
    """Times (clip-relative) where the voice changes: the cosine distance
    between the mean embedding of ``context`` windows before a point and
    ``context`` after it peaks above ``distance``. Peaks closer than
    ``min_part_s`` keep the stronger one. Roster-free: a voice no print
    matches still changes the embedding."""
    pairs = [(t, e) for t, e in zip(centers, embs) if e is not None]
    if len(pairs) < 2 * context + 1:
        return []
    times = [t for t, _ in pairs]
    vecs = np.stack([e for _, e in pairs])
    scores = []
    for i in range(context, len(pairs) - context + 1):
        left = vecs[i - context:i].mean(axis=0)
        right = vecs[i:i + context].mean(axis=0)
        cos = float(np.dot(left, right) / ((np.linalg.norm(left) * np.linalg.norm(right)) + 1e-9))
        scores.append((i, 1.0 - cos))
    peaks = []
    for k, (i, d) in enumerate(scores):
        if d < distance:
            continue
        prev_d = scores[k - 1][1] if k > 0 else -1.0
        next_d = scores[k + 1][1] if k + 1 < len(scores) else -1.0
        if d >= prev_d and d >= next_d:
            peaks.append(((times[i - 1] + times[i]) / 2.0, d))
    kept = []
    for t, d in sorted(peaks, key=lambda p: -p[1]):
        if all(abs(t - u) >= min_part_s for u, _ in kept):
            kept.append((t, d))
    return sorted(t for t, _ in kept)


def _change_point(votes):
    """Time of a single sustained flip in the window winners, or None.
    'Sustained' = the label before and after the flip each hold >=2 windows,
    so a single noisy window can't split the segment."""
    labels = [v[1] for v in votes if v[1] is not None]
    if len(set(labels)) < 2:
        return None
    for i in range(1, len(votes)):
        a, b = votes[i - 1][1], votes[i][1]
        if a is None or b is None or a == b:
            continue
        before = [v[1] for v in votes[:i] if v[1] is not None]
        after = [v[1] for v in votes[i:] if v[1] is not None]
        if before.count(a) >= 2 and after.count(b) >= 2 and \
                a not in after[2:] and b not in before[:-2]:
            return (votes[i - 1][0] + votes[i][0]) / 2
    return None


def _contested(votes):
    """[aliases] when two voices each win a solid share of windows at decent
    sims — true overlap/alternating too fast to split."""
    tally = {}
    for _t, alias, sim in votes:
        if alias is not None and sim >= CONTEST_FLOOR:
            tally[alias] = tally.get(alias, 0) + 1
    total = max(1, len(votes))
    strong = [a for a, n in tally.items() if n / total >= CONTEST_SHARE]
    return sorted(strong) if len(strong) >= 2 else None


def split_and_attribute(int16_audio, words, seg_start, seg_end,
                        fingerprints, verification):
    """Attribute one ASR segment, splitting at a speaker change if present.

    int16_audio: np.int16 mono 16k of the segment span
    words: [(word_text, abs_start_s, abs_end_s)] within the segment
    Returns a list of parts:
      [{'start','end','text_slice':(w0,w1),'alias','speaker_id','contested'}]
    text_slice indexes into `words`; a single-part result covers all words.
    """
    duration = seg_end - seg_start
    whole = {'start': seg_start, 'end': seg_end,
             'text_slice': (0, len(words)), 'alias': None,
             'speaker_id': -1, 'contested': None, 'confidence': None}

    def decide(clip):
        return pyd.checkFingerprints(clip.tobytes(), fingerprints,
                                     verification)

    if duration < MIN_SPLIT_S or len(words) < 2:
        whole['alias'], whole['speaker_id'], whole['confidence'] = decide(int16_audio)
        return [whole]

    windows = _window_embeddings(int16_audio, verification)
    votes = _window_votes(int16_audio, fingerprints, verification, windows)
    cps = _change_points(*windows) if EMBEDDING_CHANGE_POINTS else []
    flip = _change_point(votes)
    if flip is not None and all(abs(flip - t) >= MIN_PART_S for t in cps):
        cps = sorted(cps + [flip])

    if not cps:
        whole['alias'], whole['speaker_id'], whole['confidence'] = decide(int16_audio)
        # Contested = two voices each winning solid shares of the windows
        # (ping-pong too fast to split). Checked even when the whole-segment
        # gate accepted one name — the second voice is still real signal.
        # Known limit: SIMULTANEOUS same-power speech embeds like the dominant
        # voice alone and is not detectable from print sims (needs an
        # overlap-trained model); this catches rapid alternation.
        contested = _contested(votes)
        if contested and (whole['alias'] is None or
                          any(a != whole['alias'] for a in contested)):
            whole['contested'] = contested
            logging.info('contested segment: %s (assigned: %s)',
                         contested, whole['alias'])
        return [whole]

    # Each change point snaps to the nearest word boundary; a boundary that
    # would leave a part shorter than MIN_PART_S is dropped.
    cuts = []
    for cp in cps:
        cp_abs = seg_start + cp
        best_i, best_d = None, None
        for i in range(1, len(words)):
            d = abs(words[i][1] - cp_abs)
            if best_d is None or d < best_d:
                best_i, best_d = i, d
        if best_i is not None and (not cuts or best_i > cuts[-1]):
            cuts.append(best_i)
    spans = []
    lo = 0
    for i in cuts + [len(words)]:
        if i <= lo:
            continue
        s_t = seg_start if lo == 0 else words[lo][1]
        e_t = seg_end if i == len(words) else words[i - 1][2]
        spans.append([s_t, e_t, lo, i])
        lo = i
    merged = []
    for span in spans:
        if merged and (span[1] - span[0]) < MIN_PART_S:
            merged[-1][1], merged[-1][3] = span[1], span[3]
        else:
            merged.append(span)
    if len(merged) > 1 and (merged[0][1] - merged[0][0]) < MIN_PART_S:
        merged[1][0], merged[1][2] = merged[0][0], merged[0][2]
        merged.pop(0)
    if len(merged) < 2:
        whole['alias'], whole['speaker_id'], whole['confidence'] = decide(int16_audio)
        return [whole]

    parts = []
    for s_t, e_t, w0, w1 in merged:
        a0 = max(0, int((s_t - seg_start) * SR))
        a1 = min(len(int16_audio), int((e_t - seg_start) * SR))
        alias, sid, conf = decide(int16_audio[a0:a1])
        parts.append({'start': s_t, 'end': e_t, 'text_slice': (w0, w1),
                      'alias': alias, 'speaker_id': sid, 'contested': None,
                      'confidence': conf})
    logging.info('segment split at %s: %s',
                 ', '.join('%.1fs' % (seg_start + c) for c in cps),
                 ' | '.join(str(p['alias']) for p in parts))
    return parts
