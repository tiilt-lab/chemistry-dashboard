"""Pure analytics computations — no DB, no Flask, so they can be unit-tested in
isolation. The DB wrappers in database.py fetch rows and delegate here.
"""


def compute_conversation_dynamics(rows):
    """Turn-taking dynamics over an ordered list of
    (speaker_tag, start_time, length) tuples.

    A "turn" is a maximal run of consecutive utterances by the same speaker;
    transitions capture who follows whom (the response network). Returns
    per-speaker turns/utterances/speaking-seconds/share, the speaking-time Gini
    (0 = perfectly equal), total turns, total speaking seconds.
    """
    speakers = {}
    transitions = {}
    prev_speaker = None
    for tag, start, length in rows:
        s = speakers.setdefault(tag, {'turns': 0, 'utterances': 0, 'seconds': 0})
        s['utterances'] += 1
        s['seconds'] += (length or 0)
        if tag != prev_speaker:
            s['turns'] += 1
            if prev_speaker is not None:
                key = (prev_speaker, tag)
                transitions[key] = transitions.get(key, 0) + 1
            prev_speaker = tag
    total_sec = sum(v['seconds'] for v in speakers.values()) or 1
    speaker_list = [
        {'name': k, 'turns': v['turns'], 'utterances': v['utterances'],
         'speaking_seconds': v['seconds'], 'share': round(v['seconds'] / total_sec, 4)}
        for k, v in sorted(speakers.items(), key=lambda x: -x[1]['seconds'])]
    gini = gini_coefficient([v['seconds'] for v in speakers.values()])
    transition_list = [
        {'from': f, 'to': t, 'count': c}
        for (f, t), c in sorted(transitions.items(), key=lambda x: -x[1])]
    return {
        'speakers': speaker_list,
        'transitions': transition_list,
        'total_turns': sum(v['turns'] for v in speakers.values()),
        'total_speaking_seconds': total_sec,
        'gini': gini,
    }


def gini_coefficient(values):
    """Gini coefficient of a list of non-negative values (0 = perfectly equal,
    ->1 = fully concentrated). Empty / all-zero -> 0.0."""
    vals = sorted(v for v in values if v is not None)
    n = len(vals)
    total = sum(vals)
    if not n or not total:
        return 0.0
    cum = sum((i + 1) * x for i, x in enumerate(vals))
    return round((2 * cum) / (n * total) - (n + 1) / n, 4)


def on_task_pct(focus_values, off_task=None, away=None):
    """Fraction (0-100) of gaze samples that are on-task: not a phone (off-task)
    and not 'nothing'/absent (away). Returns None for no samples."""
    off_task = off_task or {"cell phone", "phone", "cellphone"}
    away = away or {"nothing", "none", ""}
    on = total = 0
    for v in focus_values:
        v = (v or "").lower()
        total += 1
        if v not in off_task and v not in away:
            on += 1
    return round(on / total * 100) if total else None


# ---------------------------------------------------------------------------
# Tier-1 talk metrics: transparent, countable measures educators trust.
# Everything below is derived only from utterance timing, the question flag,
# and (for question type) an openly-stated first-words heuristic.

_OPEN_STARTERS = (
    'why', 'how', 'what if', 'what do', 'what does', 'what would',
    'what happens', 'what could', 'explain', 'in what way', 'to what extent',
    'what makes', 'what about')
_CLOSED_STARTERS = (
    'is ', 'are ', 'was ', 'were ', 'do ', 'does ', 'did ', 'can ',
    'could ', 'will ', 'would ', 'should ', 'have ', 'has ', 'am ', 'ok', 'okay', 'right')


def classify_question(text):
    """'open' (invites explanation), 'closed' (yes/no or procedural), or
    'other'. Heuristic on the first words of the sentence ending in '?' —
    deliberately simple and inspectable rather than model-based."""
    if not text:
        return 'other'
    sentence = text
    for part in str(text).split('?'):
        part = part.strip()
        if part:
            sentence = part  # last non-empty part before a '?'
            break
    s = sentence.strip().lower()
    if s.startswith(_OPEN_STARTERS):
        return 'open'
    if s.startswith(_CLOSED_STARTERS):
        return 'closed'
    return 'other'


def compute_talk_metrics(rows, enrolled=None, silence_threshold=10.0,
                         hanging_wait=30.0, interruption_slack=1.0):
    """Tier-1 talk metrics over ordered utterances.

    rows: ordered (speaker_tag, start_time, length, question, transcript)
    enrolled: optional list of speaker aliases expected in the pod, used to
        report who never spoke.

    Returns equity timeline buckets, silences, handoffs vs interruptions,
    question counts/types/wait times, and per-speaker rollups. speaker_tag
    None is reported as 'Unattributed' — hiding it would overstate equity.
    """
    utts = [((tag or 'Unattributed'), float(start or 0), float(length or 0),
             bool(question), text or '')
            for tag, start, length, question, text in rows]
    if not utts:
        return {'empty': True}

    t0 = utts[0][1]
    t1 = max(s + l for _, s, l, _, _ in utts)
    span = max(t1 - t0, 1.0)

    # --- equity timeline -------------------------------------------------
    n_buckets = max(4, min(12, int(span // 60) or 4))
    bucket_seconds = span / n_buckets
    buckets = [{} for _ in range(n_buckets)]
    for tag, start, length, _q, _x in utts:
        end = start + length
        b0 = int((start - t0) / bucket_seconds)
        b1 = int(max(end - t0 - 1e-9, 0) / bucket_seconds)
        for b in range(max(b0, 0), min(b1, n_buckets - 1) + 1):
            bs = t0 + b * bucket_seconds
            be = bs + bucket_seconds
            overlap = max(0.0, min(end, be) - max(start, bs))
            if overlap > 0:
                buckets[b][tag] = buckets[b].get(tag, 0.0) + overlap
    timeline = {
        'start': round(t0, 1),
        'bucket_seconds': round(bucket_seconds, 1),
        'buckets': [
            {k: round(v, 1) for k, v in b.items()} for b in buckets],
    }

    # --- silences & turn-taking -----------------------------------------
    silences = []
    handoffs = 0
    interruptions = 0
    interruptions_by = {}
    for i in range(1, len(utts)):
        p_tag, p_start, p_len, _pq, _px = utts[i - 1]
        n_tag, n_start, _nl, _nq, _nx = utts[i]
        gap = n_start - (p_start + p_len)
        if gap >= silence_threshold:
            silences.append({'at': round(p_start + p_len, 1),
                             'seconds': round(gap, 1)})
        if n_tag != p_tag:
            if gap < -interruption_slack:
                interruptions += 1
                interruptions_by[n_tag] = interruptions_by.get(n_tag, 0) + 1
            else:
                handoffs += 1
    silences.sort(key=lambda s: -s['seconds'])
    total_silence = sum(s['seconds'] for s in silences)

    # --- questions & wait time ------------------------------------------
    q_total = q_open = q_closed = 0
    waits = []
    hanging = 0
    per_speaker_q = {}
    for i, (tag, start, length, question, text) in enumerate(utts):
        if not question:
            continue
        q_total += 1
        kind = classify_question(text)
        if kind == 'open':
            q_open += 1
        elif kind == 'closed':
            q_closed += 1
        sq = per_speaker_q.setdefault(tag, {'asked': 0, 'open': 0})
        sq['asked'] += 1
        if kind == 'open':
            sq['open'] += 1
        if i + 1 < len(utts):
            wait = max(0.0, utts[i + 1][1] - (start + length))
            if wait > hanging_wait:
                hanging += 1
            else:
                waits.append(wait)
        else:
            hanging += 1

    # --- per-speaker rollup + never spoke -------------------------------
    spoke = {}
    for tag, _s, length, _q, _x in utts:
        spoke[tag] = spoke.get(tag, 0.0) + length
    per_speaker = [
        {'name': k, 'speaking_seconds': round(v, 1),
         'questions': per_speaker_q.get(k, {}).get('asked', 0),
         'open_questions': per_speaker_q.get(k, {}).get('open', 0),
         'interruptions': interruptions_by.get(k, 0)}
        for k, v in sorted(spoke.items(), key=lambda x: -x[1])]
    never_spoke = sorted(set(a for a in (enrolled or []) if a)
                         - set(spoke.keys()))

    return {
        'timeline': timeline,
        'silences': {
            'count': len(silences),
            'longest': silences[0] if silences else None,
            'total_seconds': round(total_silence, 1),
            'pct_of_session': round(100 * total_silence / span, 1),
            'top': silences[:5],
            'threshold_seconds': silence_threshold,
        },
        'turn_taking': {
            'clean_handoffs': handoffs,
            'interruptions': interruptions,
            'interruptions_by': interruptions_by,
        },
        'questions': {
            'total': q_total,
            'open': q_open,
            'closed': q_closed,
            'other': q_total - q_open - q_closed,
            'avg_wait_seconds': round(sum(waits) / len(waits), 1) if waits else None,
            'hanging': hanging,
            'hanging_wait_seconds': hanging_wait,
        },
        'per_speaker': per_speaker,
        'never_spoke': never_spoke,
        'span_seconds': round(span, 1),
    }


def pairwise_voice_overlaps(embeddings, threshold=0.50):
    """Which enrolled voices sound alike. `embeddings` is {username: vector}
    (numpy arrays or lists). Returns pairs with cosine >= threshold, sorted
    by descending similarity. Pure (numpy only) so it is unit-testable and
    reusable between the live endpoint and any batch report."""
    import numpy as np
    names = sorted(embeddings)
    normed = {}
    for n in names:
        v = np.asarray(embeddings[n], dtype=float).ravel()
        normed[n] = v / (np.linalg.norm(v) + 1e-9)
    pairs = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            sim = float(np.dot(normed[a], normed[b]))
            if sim >= threshold:
                pairs.append({'a': a, 'b': b, 'similarity': round(sim, 3)})
    pairs.sort(key=lambda p: -p['similarity'])
    return pairs


def compute_live_alerts(rows, session_now, window=600.0,
                        silent_after=180.0, dominated_share=0.70,
                        hanging_after=30.0):
    """Real-time triage flags for one pod, from its ordered utterances and
    the session's current elapsed time (session_now, seconds since start).
    rows: (speaker_tag, start_time, length, question). Pure/testable.

    - silent: no utterance ended within silent_after seconds
    - dominated: one speaker holds >= dominated_share of the last `window`
    - hanging_question: last utterance is a question, unanswered for
      hanging_after seconds
    """
    utts = [(t or 'Unattributed', float(s or 0), float(l or 0), bool(q))
            for t, s, l, q in rows]
    if not utts:
        return {'silent': True, 'dominated_by': None, 'hanging_question': False,
                'last_activity_age': None}

    last_end = max(s + l for _t, s, l, _q in utts)
    age = max(0.0, session_now - last_end)

    # speaking time per speaker within the recent window
    win_start = session_now - window
    share = {}
    for tag, s, l, _q in utts:
        end = s + l
        overlap = max(0.0, min(end, session_now) - max(s, win_start))
        if overlap > 0:
            share[tag] = share.get(tag, 0.0) + overlap
    total = sum(share.values())
    dominated_by = None
    if total > 30:  # need enough recent talk to judge
        top, sec = max(share.items(), key=lambda kv: kv[1])
        if sec / total >= dominated_share:
            dominated_by = {'name': top, 'share': round(sec / total, 2)}

    last_tag, last_s, last_l, last_q = utts[-1]
    hanging = bool(last_q) and (session_now - (last_s + last_l)) >= hanging_after

    return {
        'silent': age >= silent_after,
        'dominated_by': dominated_by,
        'hanging_question': hanging,
        'last_activity_age': round(age, 1),
    }
