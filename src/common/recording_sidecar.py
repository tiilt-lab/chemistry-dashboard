"""The sidecar next to a recording: how its samples map to the session clock.

A pod's recording (``<key> (<start>)_redu.wav``) begins at the first audio
frame the service received on that connection. The service stamps that
moment ``start_offset`` seconds into the session (processing_config.py), and
may move the clock later (clock_anchor.py: a late start, discarded replay
audio, a stall). Nothing of this was written down, so a recording could not
be placed on the session clock afterwards, only its wall-clock start
guessed from the file name.

The sidecar is JSON beside the recording, same base name plus ``.clock.json``:

    {"processing_key": ..., "session_id": ..., "device_id": ...,
     "sample_rate": 16000, "channels": 1,
     "start_offset": 63729.4,           # session seconds of sample 0
     "moves": [{"at": 12.3, "delta": 18.0}, ...]}   # clock moves, at audio seconds

session_time(info, s) is the session clock at ``s`` seconds into the
recording. Import-light (json, os) so both services and the server share it.
"""
import json
import os
import tempfile

SUFFIX = '.clock.json'
_RECORDING_SUFFIXES = ('.wav', '.dat')


def base_of(path):
    """The recording's base path (no .wav/.dat, no sidecar suffix)."""
    if path.endswith(SUFFIX):
        return path[:-len(SUFFIX)]
    for suffix in _RECORDING_SUFFIXES:
        if path.endswith(suffix):
            return path[:-len(suffix)]
    return path


def path_for(recording_path):
    return base_of(recording_path) + SUFFIX


def write(recording_path, info):
    """Write the sidecar atomically (a reader never sees a half file)."""
    target = path_for(recording_path)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(target) or '.', prefix='.clock-', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(info, f)
        os.replace(tmp, target)
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def read(recording_path):
    """The sidecar's dict, or None when there is none (recordings from
    before the sidecar existed) or it is unreadable."""
    try:
        with open(path_for(recording_path)) as f:
            info = json.load(f)
    except (OSError, ValueError):
        return None
    return info if isinstance(info, dict) and 'start_offset' in info else None


def session_time(info, audio_seconds):
    """Session clock at ``audio_seconds`` into the recording: the start
    offset plus every clock move made before that point."""
    t = float(info.get('start_offset') or 0.0) + float(audio_seconds)
    for move in info.get('moves') or []:
        if float(move.get('at', 0.0)) <= float(audio_seconds):
            t += float(move.get('delta') or 0.0)
    return t
