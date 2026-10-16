"""One recording per pod on the session clock, across reconnects.

The per-connection recordings (recorder.WaveRecorder) start a new file at
every connection, so a pod that reconnected is three files with gaps and
replays between them. When the browser stamps its frames (audio-frame.js),
the service knows where each frame sits on the session clock, and this
recorder writes a single 16 kHz mono track per pod: silence is written for
a gap, a frame that starts before the track's end (a replay overlapping
what was already written) is skipped past the overlap, and a reconnect
simply appends. The .dat holds raw int16 samples; finalize() writes the
.wav beside it without removing the .dat, so the next connection appends
and the .wav is refreshed at every disconnect.

Pure file I/O, no Twisted; the registry keeps one recorder per processing
key for the life of the process.
"""
import logging
import os

import numpy as np
from scipy.io import wavfile

SAMPLE_RATE = 16000
GAP_MIN_SECONDS = 0.05      # gaps shorter than this are jitter, not silence
MAX_GAP_SECONDS = 4 * 3600  # a gap this long is a broken clock, not silence: start a new track


class TimelineRecorder(object):
    def __init__(self, base, sample_rate=SAMPLE_RATE):
        self.base = base
        self.dat = base + '.dat'
        self.wav = base + '.wav'
        self.sample_rate = int(sample_rate)
        self.start = None        # session seconds of sample 0
        self.samples = 0         # samples written so far
        if os.path.exists(self.dat):
            self.samples = os.path.getsize(self.dat) // 2

    @property
    def end(self):
        return None if self.start is None else self.start + self.samples / float(self.sample_rate)

    def write(self, pcm16, session_time):
        """Append int16 mono bytes whose first sample sits at ``session_time``."""
        if not pcm16:
            return
        n = len(pcm16) // 2
        if self.start is None:
            self.start = float(session_time)
        gap = float(session_time) - self.end
        if gap > MAX_GAP_SECONDS:
            logging.warning('timeline %s: %.0f s gap looks like a clock fault; skipping the padding', self.base, gap)
            gap = 0.0
        with open(self.dat, 'ab') as f:
            if gap >= GAP_MIN_SECONDS:
                pad = int(round(gap * self.sample_rate))
                f.write(np.zeros(pad, dtype='<i2').tobytes())
                self.samples += pad
            elif gap < -GAP_MIN_SECONDS:
                # Overlaps what is already on the track: keep the written
                # part, append only what reaches past the end.
                skip = int(round(-gap * self.sample_rate))
                if skip >= n:
                    return
                pcm16 = pcm16[skip * 2:]
                n -= skip
            f.write(pcm16)
            self.samples += n

    def finalize(self):
        """Refresh the .wav from the .dat (kept for the next connection)."""
        try:
            if self.samples == 0:
                return
            raw = np.memmap(self.dat, dtype='<i2', mode='r')
            wavfile.write(self.wav, self.sample_rate, raw[:self.samples])
            del raw
        except Exception:
            logging.exception('timeline %s: could not write the wav', self.base)


_registry = {}


def for_pod(directory, processing_key, sample_rate=SAMPLE_RATE):
    """The pod's timeline recorder, created on first use."""
    rec = _registry.get(processing_key)
    if rec is None:
        rec = TimelineRecorder(os.path.join(directory, '%s_timeline_redu' % processing_key), sample_rate)
        _registry[processing_key] = rec
    return rec
