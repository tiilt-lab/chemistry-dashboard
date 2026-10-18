"""Fragment-aware post-hoc recording lookup (audit E.2).

A BYOD reconnect starts a new recording file, so a pod can have several

    <key> (<start ctime>)_orig.wav

fragments (172 pods do). The post-hoc lookup used to take ``files[0]`` of an
unsorted glob — an arbitrary fragment, sometimes the derived ``_redu`` twin.
This module orders the raw ``_orig`` fragments by the start time in their
name and, when there is more than one, joins them in order with ffmpeg's
concat demuxer into a ``_joined.wav`` cache next to them (rebuilt only when a
fragment is newer than the cache). The cache is named so
``parse_recording_filename`` yields the pod key and the FIRST fragment's start,
which is the run's time origin.

choose_recording() is what the post-hoc service calls: the pod's session-
timeline recording (timeline_recorder.py: one track on the session clock,
gaps as silence, an exact clock sidecar) when the live service wrote one,
converted once to the float wav the post-hoc reader expects; else the
fragments stitched onto the session clock with their gaps (from each one's
sidecar, or its name stamp against the session's start) and a sidecar
written for the result; else the single fragment and its sidecar. The
clock info it returns is what stamps the run's rows (processing_config,
processor_posthoc) and what the MOSS naming cuts its prints by, so the
rows land where the audio player (routes/session.py) puts the sound.

The join of butted fragments (join_fragments) remains for callers that
need it; the selection logic is pure and tested without ffmpeg.
"""
import logging
import os
import subprocess
import time

from recording_filename import parse_recording_filename
import recording_sidecar

TIME_FORMAT = '%a %b %d %H:%M:%S %Y'
ORIGINAL_SUFFIX = '_orig'
JOINED_TAG = '_joined'
JOIN_TIMEOUT = 1800


def fragment_time(path):
    """Epoch seconds from the '(<ctime>)' in a recording name, or None."""
    _, stamp = parse_recording_filename(str(path))
    try:
        return time.mktime(time.strptime(stamp, TIME_FORMAT))
    except (ValueError, OverflowError):
        return None


def _stem(path):
    return os.path.splitext(os.path.basename(str(path)))[0]


def is_joined(path):
    # Also matches the '.part' / list files a join in progress leaves behind.
    return JOINED_TAG in os.path.basename(str(path))


def is_original(path):
    return _stem(path).endswith(ORIGINAL_SUFFIX)


def ordered_fragments(paths):
    """The pod's recording fragments, oldest first. Prefers the raw ``_orig``
    captures (``_redu`` is derived from them), ignores earlier join caches,
    orders by the start time in the name (name as tie-break; a nameless-time
    file sorts last)."""
    paths = [str(p) for p in paths if not is_joined(p)]
    originals = [p for p in paths if is_original(p)]
    chosen = originals or paths
    return sorted(chosen, key=lambda p: (fragment_time(p) is None,
                                         fragment_time(p) or 0.0,
                                         os.path.basename(p)))


def joined_path(fragments):
    """Cache file for a join, next to the fragments."""
    first = fragments[0]
    key, stamp = parse_recording_filename(first)
    return os.path.join(os.path.dirname(first), '%s (%s)%s.wav' % (key, stamp, JOINED_TAG))


def cache_is_fresh(cache, fragments, mtime=os.path.getmtime, exists=os.path.exists):
    if not exists(cache):
        return False
    return mtime(cache) >= max(mtime(f) for f in fragments)


def select_recording(paths, mtime=os.path.getmtime, exists=os.path.exists):
    """(path to analyse, fragments to join into it). The second item is None
    when no join is needed: a single recording, or a cache newer than every
    fragment. (None, None) when the pod has no recording."""
    fragments = ordered_fragments(paths)
    if not fragments:
        return None, None
    if len(fragments) == 1:
        return fragments[0], None
    wavs = [f for f in fragments if f.lower().endswith('.wav')]
    if len(wavs) != len(fragments):
        logging.warning('ignoring %d non-wav fragment(s) of %s',
                        len(fragments) - len(wavs), os.path.basename(fragments[0]))
    if len(wavs) <= 1:
        return (wavs[0] if wavs else fragments[0]), None
    cache = joined_path(wavs)
    if cache_is_fresh(cache, wavs, mtime=mtime, exists=exists):
        return cache, None
    return cache, wavs


def concat_list_text(fragments):
    # concat-demuxer list; a quote in a name is closed, escaped, reopened.
    return ''.join("file '%s'\n" % f.replace("'", "'\\''") for f in fragments)


def join_fragments(fragments, out_path, run=subprocess.run, timeout=JOIN_TIMEOUT):
    """Concatenate wav fragments in order into ``out_path`` with ffmpeg's
    concat demuxer, re-encoded to what the post-hoc reader expects (16 kHz
    float PCM; the first fragment's channel layout). Written to a temp name
    and renamed, so a killed ffmpeg never leaves a truncated cache that
    passes the freshness check."""
    list_path = out_path + '.txt'
    part_path = out_path[:-4] + '.part.wav'
    with open(list_path, 'w') as f:
        f.write(concat_list_text(fragments))
    try:
        run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', list_path,
             '-ar', '16000', '-acodec', 'pcm_f32le', part_path],
            check=True, timeout=timeout)
        os.replace(part_path, out_path)
    finally:
        for p in (list_path, part_path):
            try:
                os.remove(p)
            except OSError:
                pass
    return out_path


TIMELINE_TAG = '_timeline_redu'
F32_TAG = '_timeline_f32'
STITCHED_TAG = '_stitched'


def timeline_path(paths):
    """The pod's session-timeline wav among ``paths``, or None."""
    for p in sorted(str(x) for x in paths):
        if p.lower().endswith(TIMELINE_TAG + '.wav'):
            return p
    return None


def pod_key(path):
    """The processing key a recording belongs to, from any of its names:
    '<key> (<stamp>)_orig.wav', '<key>_timeline_redu.wav', '<key> (<stamp>)_joined.wav'."""
    name = os.path.basename(str(path))
    for tag in (TIMELINE_TAG, F32_TAG, STITCHED_TAG):
        name = name.split(tag)[0]
    return parse_recording_filename(name)[0]


def f32_path(timeline):
    return os.path.join(os.path.dirname(timeline), pod_key(timeline) + F32_TAG + '.wav')


def convert_to_f32(src, out_path, run=subprocess.run, timeout=JOIN_TIMEOUT):
    """The recording as 16 kHz mono float PCM (what the post-hoc reader
    expects), with its clock sidecar copied beside the result."""
    part_path = out_path[:-4] + '.part.wav'
    run(['ffmpeg', '-y', '-v', 'error', '-i', src, '-ar', '16000', '-ac', '1', '-acodec', 'pcm_f32le', part_path],
        check=True, timeout=timeout)
    os.replace(part_path, out_path)
    info = recording_sidecar.read(src)
    if info:
        recording_sidecar.write(out_path, info)
    return out_path


def stamp_offset(path, server_start):
    """Session seconds of a fragment's start from its name stamp, against
    the session's start (a datetime); None when either is missing."""
    _, stamp = parse_recording_filename(str(path))
    if not stamp or server_start is None:
        return None
    try:
        started = time.strptime(stamp, TIME_FORMAT)
    except ValueError:
        return None
    import datetime
    return max((datetime.datetime(*started[:6]) - server_start).total_seconds(), 0.0)


def fragment_clock(path, server_start):
    """{start_offset, moves} of a fragment: its sidecar, else its name stamp."""
    info = recording_sidecar.read(str(path))
    if info:
        return {'start_offset': float(info.get('start_offset') or 0.0), 'moves': list(info.get('moves') or [])}
    offset = stamp_offset(path, server_start)
    return None if offset is None else {'start_offset': offset, 'moves': []}


def stitched_path(fragments):
    first = fragments[0]
    key, stamp = parse_recording_filename(first)
    return os.path.join(os.path.dirname(first), '%s (%s)%s.wav' % (key, stamp, STITCHED_TAG))


def stitch_fragments(fragments, clocks, out_path, sample_rate=16000, read=None, write=None):
    """One float wav on the session clock from fragments and their clocks
    ({start_offset, moves} each): a gap between fragments, or a forward
    clock move inside one, becomes silence; audio the clock covered twice
    (an overlapping start, a backward move) is skipped. Writes the clock
    sidecar of the result (start_offset of the first fragment, no moves)
    and returns out_path. ``read``/``write`` default to scipy's wav I/O."""
    import numpy as np
    if read is None or write is None:
        from scipy.io import wavfile

        def read(path):
            sr, data = wavfile.read(path)
            if data.ndim > 1:
                data = data[:, 0]
            if data.dtype.kind == 'i':
                data = data.astype(np.float32) / float(1 << (8 * data.dtype.itemsize - 1))
            return sr, np.asarray(data, dtype=np.float32)

        def write(path, sr, data):
            wavfile.write(path, sr, np.asarray(data, dtype=np.float32))
    pieces = []
    start = float(clocks[0]['start_offset'])
    cursor = start                      # session clock at the end of what is laid
    for frag, clock in zip(fragments, clocks):
        sr, audio = read(str(frag))
        if sr != sample_rate:
            raise ValueError('fragment %s is %d Hz, expected %d' % (frag, sr, sample_rate))
        # the fragment as (session start, samples) runs split at its clock moves
        runs, pos, session = [], 0, float(clock['start_offset'])
        for move in sorted(clock.get('moves') or [], key=lambda m: float(m.get('at') or 0.0)):
            at = int(round(float(move.get('at') or 0.0) * sr))
            if at > pos:
                runs.append((session, audio[pos:at]))
                session += (at - pos) / float(sr)
                pos = at
            session += float(move.get('delta') or 0.0)
        runs.append((session, audio[pos:]))
        for session_start, samples in runs:
            if not len(samples):
                continue
            gap = session_start - cursor
            if gap > 0:
                pieces.append(np.zeros(int(round(gap * sr)), dtype=np.float32))
            elif gap < 0:
                skip = min(int(round(-gap * sr)), len(samples))
                samples = samples[skip:]
            pieces.append(samples)
            cursor = max(cursor, session_start) + len(samples) / float(sr)
    data = np.concatenate(pieces) if pieces else np.zeros(0, dtype=np.float32)
    part_path = out_path[:-4] + '.part.wav'
    write(part_path, sample_rate, data)
    if os.path.exists(part_path):       # an injected writer may keep the audio elsewhere
        os.replace(part_path, out_path)
    recording_sidecar.write(out_path, {'processing_key': pod_key(fragments[0]), 'start_offset': round(start, 3),
                                       'moves': [], 'timeline': True,
                                       'stitched_from': [os.path.basename(str(f)) for f in fragments]})
    return out_path


def choose_recording(paths, server_start, mtime=os.path.getmtime, exists=os.path.exists,
                     convert=convert_to_f32, stitch=stitch_fragments):
    """(path to analyse, clock info or None) for a pod's recording files.
    The session timeline when there is one (as a float wav, converted once);
    else the fragments stitched onto the session clock (once, rebuilt when a
    fragment is newer); else the single fragment. The clock is the chosen
    file's sidecar, or the fragment's name stamp against ``server_start``."""
    paths = [str(p) for p in paths]
    timeline = timeline_path(paths)
    if timeline:
        cache = f32_path(timeline)
        if not cache_is_fresh(cache, [timeline], mtime=mtime, exists=exists):
            logging.info('Converting the session timeline %s to float wav', os.path.basename(timeline))
            convert(timeline, cache)
        info = recording_sidecar.read(cache) or recording_sidecar.read(timeline)
        return cache, ({'start_offset': float(info['start_offset']), 'moves': list(info.get('moves') or [])} if info else None)
    fragments = ordered_fragments([p for p in paths if STITCHED_TAG not in os.path.basename(p) and F32_TAG not in os.path.basename(p)])
    if not fragments:
        return None, None
    if len(fragments) == 1:
        return fragments[0], fragment_clock(fragments[0], server_start)
    wavs = [f for f in fragments if f.lower().endswith('.wav')]
    clocks = [fragment_clock(f, server_start) for f in wavs]
    if len(wavs) <= 1 or any(c is None for c in clocks):
        # no clock for a fragment: the plain join, timed from the first one
        chosen, to_join = select_recording(paths, mtime=mtime, exists=exists)
        if to_join:
            join_fragments(to_join, chosen)
        return chosen, fragment_clock(wavs[0] if wavs else fragments[0], server_start)
    cache = stitched_path(wavs)
    if not cache_is_fresh(cache, wavs, mtime=mtime, exists=exists):
        logging.info('Stitching %d fragments of %s onto the session clock', len(wavs), pod_key(wavs[0]))
        stitch(wavs, clocks, cache)
    info = recording_sidecar.read(cache)
    return cache, ({'start_offset': float(info['start_offset']), 'moves': []} if info else clocks[0])
