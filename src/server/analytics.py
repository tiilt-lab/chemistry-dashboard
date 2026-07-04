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
