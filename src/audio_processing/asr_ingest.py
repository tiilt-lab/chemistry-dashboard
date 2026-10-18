"""Reactor-side ASR ingest bookkeeping (no Twisted, nothing on the GPU).

The audio protocol hands every resampled mono chunk to the ASR thread through
a bounded queue. The reactor must never wait on that queue, so chunks can be
dropped when the consumer stalls; three small pieces make a drop harmless and
visible, and they live here so they can be unit-tested without a reactor:

  * StampedChunk — PCM bytes carrying the absolute offset (in samples) of
    their first sample, counted over ALL audio received on the connection.
    Window timestamps derive from this rather than from what survived the
    queue, so they stay on the same clock as AudioBuffer (which keeps every
    byte) and ``extract()`` returns the audio the words were spoken in.
  * IngestCounter — received/dropped totals plus the rate-limited WARNING.
  * WindowAssembler — turns stamped chunks into windows cut at pauses (see
    "window cuts" below), zero-filling a short gap left by dropped chunks
    and restarting on a long one.

The voice-activity gate lives here too (applied by the connector's flush
thread, before a window is submitted to the GPU pool):

  * EnergyGate / SileroDetector — decide whether a window holds any speech,
    and score single frames for the assembler's cut search.
  * SpeechGate — per-connection wrapper: warm-up, counters, the INFO line.
  * make_speech_gate — picks the detector from DC_ASR_VAD (off|energy|silero).
  * make_frame_scorer / window_settings — the assembler's own detector and
    the DC_ASR_WINDOW_* cut settings.

A skipped window never touches the timeline: window start times come from
the absolute sample offsets above, so window k+1 starts exactly where it
would have had window k been transcribed.
"""
import logging
import os
import time
from collections import deque

import numpy as np

SAMPLE_RATE = 16000
DEPTH = 2  # bytes per sample (16-bit PCM)

# Live chunks are ~85 ms (4096 float32 samples at 48 kHz -> ~2.7 KB mono
# int16), so this is ~20 s of slack before anything is lost. The old maxsize=3
# was a quarter of a second — one GIL hiccup away from evicting audio.
QUEUE_CHUNKS = 256


class StampedChunk(bytes):
    """PCM bytes plus the absolute sample offset of their first sample.

    A ``bytes`` subclass on purpose: consumers that only join and measure
    chunks keep working unchanged, and the offset rides along for
    consumers that need the clock (CrisperWhisper windows).
    """

    def __new__(cls, data, sample_offset):
        self = super().__new__(cls, data)
        self.sample_offset = int(sample_offset)
        return self


class IngestCounter:
    """Per-connection received/dropped accounting for the ASR ingest queue.

    ``received`` returns the sample offset to stamp the chunk with; ``dropped``
    records a loss and returns the WARNING text when one is due — the first
    drop immediately, then at most once per ``log_interval`` seconds with the
    running totals, so a stalled consumer can't flood the log.
    """

    def __init__(self, sample_rate=SAMPLE_RATE, depth=DEPTH, log_interval=30.0):
        self.sample_rate = sample_rate
        self.depth = depth
        self.log_interval = log_interval
        self.samples_received = 0
        self.chunks_received = 0
        self.samples_dropped = 0
        self.chunks_dropped = 0
        self._since_log_chunks = 0
        self._since_log_samples = 0
        self._last_log = None

    def received(self, nbytes):
        offset = self.samples_received
        self.samples_received += nbytes // self.depth
        self.chunks_received += 1
        return offset

    def seconds(self, samples):
        return samples / float(self.sample_rate)

    def dropped(self, nbytes, now=None):
        now = time.time() if now is None else now
        samples = nbytes // self.depth
        self.samples_dropped += samples
        self.chunks_dropped += 1
        self._since_log_chunks += 1
        self._since_log_samples += samples
        if self._last_log is not None and now - self._last_log < self.log_interval:
            return None
        text = ("ASR ingest queue full: dropped %d chunks (%.1fs) since last report; "
                "%d of %d chunks (%.1fs of %.1fs) dropped on this connection" % (
                    self._since_log_chunks, self.seconds(self._since_log_samples),
                    self.chunks_dropped, self.chunks_received,
                    self.seconds(self.samples_dropped), self.seconds(self.samples_received)))
        self._last_log = now
        self._since_log_chunks = 0
        self._since_log_samples = 0
        return text


# --- window cuts ---------------------------------------------------------------
#
# A window used to close every 12 s of samples, blind to the speech in it. A
# word under the cut was heard in halves, one in each window, and the
# recognizer dropped it: on session 434, laptop 1436, 60 of 481 rows ran to
# the 12 s cap and "you guys have taken" vanished at the 81868 s cut while
# the partner laptop, whose clock cut half a second later, kept it.
#
# The assembler now scores every quarter-second frame as it arrives (the
# same detectors as the gate, on an instance of its own; a frame is quiet
# only when all of it is) and closes the window in front of the first quiet
# frame once it is WINDOW seconds long. A talker who never
# pauses is cut when the window reaches CAP seconds, at the quietest frame
# seen since WINDOW, and the last CARRY seconds before that cut are heard
# again at the head of the next window, so the word under the cut is whole
# there; the connector drops the duplicate words at the seam by their
# timestamps (crisperwhisper_asr._seam_words). Windows are never trimmed and
# every window's start is the true offset of its first sample, carried
# audio included.
#
#   DC_ASR_WINDOW_SECONDS        shortest window; the pause search starts here (10)
#   DC_ASR_WINDOW_CAP_SECONDS    longest window (16)
#   DC_ASR_WINDOW_CARRY_SECONDS  audio heard again after a cap cut (1.0)
#   DC_ASR_WINDOW_QUIET          a frame scoring at or below this is a pause (0.5)
#
# WINDOW = CAP = 12 with CARRY = 0 is the old blind cut, so a rollback is
# three environment values. With DC_ASR_VAD=off nothing scores the frames
# and the window closes at WINDOW seconds, blind, as before.

WINDOW_ENV = "DC_ASR_WINDOW_SECONDS"
WINDOW_CAP_ENV = "DC_ASR_WINDOW_CAP_SECONDS"
WINDOW_CARRY_ENV = "DC_ASR_WINDOW_CARRY_SECONDS"
WINDOW_QUIET_ENV = "DC_ASR_WINDOW_QUIET"
WINDOW_SECONDS_DEFAULT = 10.0
WINDOW_CAP_DEFAULT = 16.0
WINDOW_CARRY_DEFAULT = 1.0
WINDOW_QUIET_DEFAULT = 0.5
CUT_FRAME_SECONDS = 0.25   # the cut search's frame: a pause this long can take the cut
FRAME_SECONDS = 0.5        # the gate's frame: speech in any frame keeps the window


class Window(tuple):
    """A ``(start_seconds, pcm)`` window that also says how it was cut.

    ``overlap`` seconds at its head were already in the previous window (the
    carry after a cap cut); ``capped`` means this window ended at the cap and
    its last CARRY seconds are heard again in the next one. A plain tuple
    consumer (the queue, the gate, the flush) sees no difference.
    """

    def __new__(cls, start_seconds, pcm, overlap=0.0, capped=False):
        self = super().__new__(cls, (start_seconds, pcm))
        self.overlap = float(overlap)
        self.capped = bool(capped)
        return self

    @property
    def start(self):
        return self[0]

    @property
    def pcm(self):
        return self[1]


class WindowAssembler:
    """Assemble stamped chunks into windows cut at pauses.

    Each window is ``(start_seconds, pcm_bytes)`` (a Window) where
    ``start_seconds`` is the absolute offset of the window's first sample.
    A window closes at the first quiet frame once it holds ``window_seconds``
    of audio, at the quietest frame seen when it reaches ``cap_seconds`` (the
    last ``carry_seconds`` then open the next window too), or at
    ``window_seconds`` exactly when nothing scores the frames. ``frame_scorer``
    is an object with ``frame_score(pcm) -> [0, 1]`` (EnergyGate,
    SileroDetector); ``scorer_factory`` builds one lazily on the thread that
    adds audio, and a scorer that cannot be built or that fails later is
    dropped with a WARNING: blind cuts, never lost audio. A gap shorter than a
    window (a few dropped chunks) is zero-filled so the audio stays on the
    clock; a longer gap closes the current window and starts a new one at the
    new offset. Unstamped ``bytes`` are assumed contiguous with the previous
    chunk.
    """

    def __init__(self, sample_rate=SAMPLE_RATE, depth=DEPTH, window_seconds=12.0,
                 cap_seconds=None, carry_seconds=0.0, quiet=WINDOW_QUIET_DEFAULT,
                 frame_scorer=None, scorer_factory=None, frame_seconds=CUT_FRAME_SECONDS):
        self.sample_rate = sample_rate
        self.depth = depth
        self.frame_samples = max(1, int(frame_seconds * sample_rate))
        self.window_samples = int(window_seconds * sample_rate)
        cap = window_seconds if cap_seconds is None else max(float(cap_seconds), float(window_seconds))
        # Cuts and the carry sit on the frame grid so the scores stay aligned
        # with the buffer across a cut: the cap rounds down to whole frames
        # (never below the shortest window), the carry to the nearest frame.
        self.cap_samples = max(self.window_samples,
                               int(cap * sample_rate) // self.frame_samples * self.frame_samples)
        carry = int(round(float(carry_seconds or 0.0) / frame_seconds)) * self.frame_samples
        self.carry_samples = max(0, min(carry, self.cap_samples - self.frame_samples))
        self.quiet = float(quiet)
        self._scorer = frame_scorer
        self._scorer_factory = scorer_factory
        self._scorer_failed = False
        self._buffer = bytearray()
        self._start = None  # sample offset of self._buffer[0]
        self._scores = []   # one speech score per complete frame of the buffer
        self._overlap = 0   # samples at the buffer's head the previous window also held

    @property
    def scoring(self):
        return self._scorer is not None

    def _expected(self):
        return (self._start or 0) + len(self._buffer) // self.depth

    def add(self, chunk):
        offset = getattr(chunk, "sample_offset", None)
        windows = []
        if self._start is None:
            self._start = self._expected() if offset is None else offset
        elif offset is not None:
            gap = offset - self._expected()
            if gap >= self.window_samples:
                tail = self.flush()
                if tail:
                    windows.append(tail)
                self._start = offset
            elif gap > 0:
                self._buffer.extend(bytes(gap * self.depth))
        self._buffer.extend(chunk)
        self._score_new_frames()
        while True:
            cut = self._cut()
            if cut is None:
                break
            windows.append(self._emit(*cut))
        return windows

    def flush(self):
        """Emit whatever is buffered (the final partial window), or None."""
        if len(self._buffer) < self.depth:
            self._buffer = bytearray()
            self._scores = []
            self._overlap = 0
            return None
        window = Window(self._start / float(self.sample_rate), bytes(self._buffer),
                        overlap=self._overlap / float(self.sample_rate))
        self._start += len(self._buffer) // self.depth
        self._buffer = bytearray()
        self._scores = []
        self._overlap = 0
        return window

    # -- scoring and the cut --------------------------------------------------

    def _build_scorer(self):
        if self._scorer_factory is None or self._scorer_failed:
            return
        try:
            self._scorer = self._scorer_factory()
        except Exception as e:
            # Blind cuts are only the old behaviour, never lost audio.
            logging.warning("ASR windows: frame scorer unavailable, cutting every "
                            "%.1fs blind: %s", self.window_samples / float(self.sample_rate), e)
            self._scorer_failed = True
            return
        self._scorer_factory = None
        self._log_mode()

    def _log_mode(self):
        sr = float(self.sample_rate)
        if self._scorer is None:
            logging.info("ASR windows: fixed %.1fs cuts (no frame scorer)", self.window_samples / sr)
        else:
            logging.info("ASR windows: cut at pauses (%s) between %.1fs and %.1fs, carry %.1fs",
                         getattr(self._scorer, "name", type(self._scorer).__name__),
                         self.window_samples / sr, self.cap_samples / sr, self.carry_samples / sr)

    def _score_new_frames(self):
        if self._scorer is None:
            self._build_scorer()
            if self._scorer is None:
                return
        frame_bytes = self.frame_samples * self.depth
        complete = len(self._buffer) // frame_bytes
        while len(self._scores) < complete:
            i = len(self._scores)
            frame = bytes(self._buffer[i * frame_bytes:(i + 1) * frame_bytes])
            try:
                self._scores.append(float(self._scorer.frame_score(frame)))
            except Exception as e:
                logging.warning("ASR windows: frame scorer (%s) failed, cutting every %.1fs "
                                "blind from now on: %s", getattr(self._scorer, "name", "?"),
                                self.window_samples / float(self.sample_rate), e)
                self._scorer = None
                self._scorer_failed = True
                self._scores = []
                return

    def _cut(self):
        """(samples into the buffer to cut at, carry samples) or None."""
        n = len(self._buffer) // self.depth
        if n < self.window_samples:
            return None
        if self._scorer is None:
            return n, 0                                          # blind: the whole buffer, as before
        first = -(-self.window_samples // self.frame_samples)   # first frame starting at/after WINDOW
        for i in range(first, len(self._scores)):
            if self._scores[i] <= self.quiet:
                return i * self.frame_samples, 0                 # a pause: cut in front of it
        if n < self.cap_samples:
            return None
        band = self._scores[first:]
        if band:
            quietest = first + min(range(len(band)), key=band.__getitem__)
            return quietest * self.frame_samples, self.carry_samples
        return n, self.carry_samples                             # WINDOW = CAP: the old cut, whole buffer

    def _emit(self, cut, carry):
        sr = float(self.sample_rate)
        window = Window(self._start / sr, bytes(self._buffer[:cut * self.depth]),
                        overlap=self._overlap / sr, capped=carry > 0)
        keep = cut - carry
        del self._buffer[:keep * self.depth]
        self._start += keep
        self._overlap = carry
        # Cuts and the carry are frame multiples whenever frames are scored.
        self._scores = self._scores[keep // self.frame_samples:] if keep % self.frame_samples == 0 else []
        return window


def _env_float(environ, name, default, low, high=None):
    raw = (environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        logging.warning("%s=%r is not a number; using %g", name, raw, default)
        return default
    if value < low or (high is not None and value > high):
        logging.warning("%s=%g is outside [%g, %s]; using %g", name, value, low,
                        "inf" if high is None else "%g" % high, default)
        return default
    return value


def window_settings(environ=os.environ):
    """WindowAssembler keyword arguments from DC_ASR_WINDOW_* (defaults
    10 / 16 / 1.0 / 0.5). The cap never falls below the shortest window."""
    window = _env_float(environ, WINDOW_ENV, WINDOW_SECONDS_DEFAULT, 1.0)
    cap = _env_float(environ, WINDOW_CAP_ENV, WINDOW_CAP_DEFAULT, 1.0)
    if cap < window:
        logging.warning("%s=%g is below %s=%g; the cap is the window", WINDOW_CAP_ENV, cap, WINDOW_ENV, window)
        cap = window
    return {"window_seconds": window, "cap_seconds": cap,
            "carry_seconds": _env_float(environ, WINDOW_CARRY_ENV, WINDOW_CARRY_DEFAULT, 0.0),
            "quiet": _env_float(environ, WINDOW_QUIET_ENV, WINDOW_QUIET_DEFAULT, 0.0, 1.0)}


# --- voice-activity gate -----------------------------------------------------
#
# Most classroom pods are silent much of the time, yet every 12 s window used
# to cost ~1 s of GPU. The gate decides, on the CPU, whether a window holds
# any speech at all; a window with speech in ANY 0.5 s frame is transcribed
# whole (never trimmed, so word timestamps stay exact) and a silent one is
# dropped before it reaches the pool.
#
# DC_ASR_VAD selects the detector:
#   off     transcribe every window (the pre-gate behaviour)
#   energy  RMS level per frame against an adaptive noise floor (EnergyGate)
#   silero  Silero VAD, ONNX on the CPU (SileroDetector) — the default when
#           the silero-vad package imports, else energy.

VAD_ENV = "DC_ASR_VAD"
VAD_MODES = ("off", "energy", "silero")
# FRAME_SECONDS (above): decision granularity, speech in any frame keeps the window
WARMUP_WINDOWS = 2      # a connection's first windows are always transcribed
SILENCE_DB = -120.0     # level reported for an all-zero frame (log10(0) guard)


def pcm_to_float(pcm, depth=DEPTH):
    """16-bit little-endian PCM bytes -> float32 samples in [-1, 1)."""
    if depth != DEPTH:
        raise ValueError("only 16-bit PCM is supported (depth=%d)" % depth)
    count = len(pcm) // depth
    return np.frombuffer(bytes(pcm), dtype="<i2", count=count).astype(np.float32) / 32768.0


def frame_levels_db(samples, sample_rate=SAMPLE_RATE, frame_seconds=FRAME_SECONDS):
    """RMS level in dBFS of every complete frame (a partial tail is ignored)."""
    frame = max(1, int(frame_seconds * sample_rate))
    n = len(samples) // frame
    if n == 0:
        return np.zeros(0, dtype=np.float32)
    frames = np.asarray(samples[:n * frame], dtype=np.float32).reshape(n, frame)
    rms = np.sqrt(np.mean(frames * frames, axis=1))
    with np.errstate(divide="ignore"):
        db = 20.0 * np.log10(rms)
    return np.maximum(db, SILENCE_DB).astype(np.float32)


class EnergyGate:
    """RMS-energy speech detector with hysteresis and an adaptive noise floor.

    Each 0.5 s frame's level (dBFS) is compared with an "on" threshold of
    noise floor + ``margin_db``; the floor is the ``floor_percentile`` (20th)
    of this pod's frame levels over the last ``history_seconds``, so the
    gate learns the room it is in. Once a frame is in speech the next frame
    only has to clear a lower "off" threshold, ``hysteresis_db`` below on,
    so a quiet trailing syllable keeps its window; off never drops below
    floor + ``hysteresis_db`` (or the room's own noise would hold the speech
    state forever). The on threshold is clamped to [``floor_min_db``,
    ``ceiling_db``]: any frame louder than ``ceiling_db`` (-38 dBFS) counts
    as speech whatever the room is doing — in a loud room the gate fails
    OPEN rather than ever suppressing clear speech — and a room quieter than
    ``floor_min_db`` gets no further credit. What it cannot do is tell a
    steady tone or hum louder than the floor from speech; that is what
    SileroDetector is for.
    """

    name = "energy"

    def __init__(self, sample_rate=SAMPLE_RATE, depth=DEPTH, frame_seconds=FRAME_SECONDS,
                 history_seconds=60.0, margin_db=6.0, hysteresis_db=3.0,
                 floor_percentile=20.0, floor_min_db=-60.0, ceiling_db=-38.0):
        self.sample_rate = sample_rate
        self.depth = depth
        self.frame_seconds = frame_seconds
        self.margin_db = float(margin_db)
        self.hysteresis_db = float(hysteresis_db)
        self.floor_percentile = float(floor_percentile)
        self.floor_min_db = float(floor_min_db)
        self.ceiling_db = float(ceiling_db)
        self._levels = deque(maxlen=max(1, int(history_seconds / frame_seconds)))
        self._in_speech = False

    @property
    def noise_floor_db(self):
        if not self._levels:
            return None
        return float(np.percentile(np.fromiter(self._levels, dtype=np.float32), self.floor_percentile))

    def thresholds(self):
        """(on, off) in dBFS for the next frame, given the history so far."""
        floor = self.noise_floor_db
        if floor is None:
            return self.ceiling_db, self.ceiling_db
        on = min(self.ceiling_db, max(self.floor_min_db, floor + self.margin_db))
        off = min(on, max(on - self.hysteresis_db, floor + self.hysteresis_db))
        return on, off

    def has_speech(self, pcm):
        levels = frame_levels_db(pcm_to_float(pcm, self.depth), self.sample_rate, self.frame_seconds)
        if levels.size == 0:
            return True  # shorter than one frame: nothing to judge, never suppress
        self._levels.extend(levels.tolist())
        on, off = self.thresholds()
        state, speech = self._in_speech, False
        for level in levels:
            state = level > (off if state else on)
            speech = speech or state
        self._in_speech = state
        return speech

    def frame_score(self, pcm):
        """Speech score of one frame (whatever its length) for the window cut
        search, in [0, 1]: 1 at or above the on threshold, 0 at or below off,
        linear between. The frame's level joins the history (this instance
        belongs to the assembler, which hands it every frame once), so the
        room is learned here too. Empty: 1, never a cut point."""
        samples = pcm_to_float(pcm, self.depth)
        if samples.size == 0:
            return 1.0
        levels = frame_levels_db(samples, self.sample_rate, samples.size / float(self.sample_rate))
        if levels.size == 0:
            return 1.0
        on, off = self.thresholds()
        self._levels.extend(levels.tolist())
        level = float(levels.max())
        if level >= on:
            return 1.0
        if level <= off or on <= off:
            return 0.0
        return (level - off) / (on - off)


_silero = {}  # import cache: {"module": silero_vad} or {"error": text}


def _import_silero():
    """Import silero_vad without its side effect: ``silero_vad.model`` calls
    ``torch.set_num_threads(1)`` at import, which would throttle every other
    torch user in this process (ECAPA and friends), so the count is restored."""
    if "module" in _silero:
        return _silero["module"]
    if "error" in _silero:
        raise ImportError(_silero["error"])
    try:
        import onnxruntime  # noqa: F401 — the session backend load_silero_vad(onnx=True) needs
        import torch
        threads = torch.get_num_threads()
        try:
            import silero_vad
        finally:
            torch.set_num_threads(threads)
    except Exception as e:
        _silero["error"] = "%s: %s" % (type(e).__name__, e)
        raise ImportError(_silero["error"])
    _silero["module"] = silero_vad
    return silero_vad


def silero_available():
    """True when silero-vad (and onnxruntime) import in this venv; cached."""
    try:
        _import_silero()
        return True
    except ImportError:
        return False


def load_silero_model():
    """The ONNX Silero VAD bundled with the package, on the CPU (no download)."""
    return _import_silero().load_silero_vad(onnx=True)


class SileroDetector:
    """Silero VAD over 32 ms chunks: speech if any chunk's probability reaches
    ``threshold`` (0.5, the upstream default).

    Every window is judged on its own (model state reset per window, as the
    upstream ``audio_forward`` does) and the scan stops at the first speech
    chunk, so a talking pod costs a few ms of CPU per window and a silent
    one the full pass (~130 ms per 12 s on one core). ``chunk_prob`` lets
    tests supply the probability function instead of a model.
    """

    name = "silero"
    CHUNK = 512  # samples per Silero step at 16 kHz

    def __init__(self, threshold=0.5, sample_rate=SAMPLE_RATE, depth=DEPTH,
                 model=None, chunk_prob=None):
        if sample_rate != 16000:
            raise ValueError("Silero VAD needs 16 kHz audio, got %d" % sample_rate)
        self.threshold = float(threshold)
        self.sample_rate = sample_rate
        self.depth = depth
        if chunk_prob is None:
            model = model or load_silero_model()
            import torch  # already loaded by silero_vad; the wrapper wants tensors

            def chunk_prob(chunk):
                return float(model(torch.from_numpy(chunk), sample_rate).item())

            self._reset = model.reset_states
        else:
            self._reset = lambda: None
        self._chunk_prob = chunk_prob

    def has_speech(self, pcm):
        samples = pcm_to_float(pcm, self.depth)
        if len(samples) < self.CHUNK:
            return True  # nothing to judge, never suppress
        self._reset()
        end = len(samples) // self.CHUNK * self.CHUNK
        for i in range(0, end, self.CHUNK):
            chunk = np.ascontiguousarray(samples[i:i + self.CHUNK])
            if self._chunk_prob(chunk) >= self.threshold:
                return True
        return False

    def frame_score(self, pcm):
        """The highest speech probability over the frame's 512-sample chunks,
        for the window cut search. Streaming: the model state carries from
        frame to frame (this instance belongs to the assembler and never
        judges whole windows). Shorter than a chunk: 1, never a cut point."""
        samples = pcm_to_float(pcm, self.depth)
        end = len(samples) // self.CHUNK * self.CHUNK
        if end == 0:
            return 1.0
        best = 0.0
        for i in range(0, end, self.CHUNK):
            best = max(best, float(self._chunk_prob(np.ascontiguousarray(samples[i:i + self.CHUNK]))))
        return best


class SpeechGate:
    """Per-connection window gate around a detector: warm-up, counters and
    the once-a-minute INFO line.

    ``admit(pcm)`` -> ``(transcribe, log_text)``. The first ``warmup_windows``
    windows are always transcribed (the detector still sees them, so the
    energy floor learns the room), as is any window shorter than one frame.
    Skipping never moves the timeline: the connector keeps the window's
    absolute start for the next one (WindowAssembler), it just does not
    spend a GPU second on this one.
    """

    def __init__(self, detector, warmup_windows=WARMUP_WINDOWS, log_interval=60.0,
                 frame_seconds=FRAME_SECONDS, sample_rate=SAMPLE_RATE, depth=DEPTH):
        self.detector = detector
        self.name = getattr(detector, "name", type(detector).__name__)
        self.warmup_windows = int(warmup_windows)
        self.log_interval = float(log_interval)
        self.windows_seen = 0
        self.windows_skipped = 0
        self._frame_bytes = int(frame_seconds * sample_rate) * depth
        self._since_log_seen = 0
        self._since_log_skipped = 0
        self._last_log = None

    @property
    def skip_ratio(self):
        return self.windows_skipped / float(self.windows_seen) if self.windows_seen else 0.0

    def admit(self, pcm, now=None):
        now = time.time() if now is None else now
        self.windows_seen += 1
        self._since_log_seen += 1
        transcribe = True
        if len(pcm) >= self._frame_bytes:
            speech = self.detector.has_speech(pcm)
            transcribe = speech or self.windows_seen <= self.warmup_windows
        if not transcribe:
            self.windows_skipped += 1
            self._since_log_skipped += 1
        text = None
        if self._last_log is None:
            self._last_log = now
        elif now - self._last_log >= self.log_interval:
            text = ("ASR VAD (%s): skipped %d of %d windows in the last %.0fs (%.0f%%); "
                    "%d of %d on this connection (%.0f%%)" % (
                        self.name, self._since_log_skipped, self._since_log_seen,
                        now - self._last_log,
                        100.0 * self._since_log_skipped / max(1, self._since_log_seen),
                        self.windows_skipped, self.windows_seen, 100.0 * self.skip_ratio))
            self._last_log = now
            self._since_log_seen = self._since_log_skipped = 0
        return transcribe, text


def vad_mode(environ=os.environ, available=None):
    """The detector DC_ASR_VAD asks for: 'off', 'energy' or 'silero'.

    Unset -> silero when it imports, else energy. An unknown value gets the
    same default (with a WARNING); 'silero' without the package falls back
    to energy (with a WARNING) rather than transcribing everything.
    """
    available = silero_available() if available is None else bool(available)
    default = "silero" if available else "energy"
    raw = (environ.get(VAD_ENV) or "").strip().lower()
    if not raw:
        return default
    if raw not in VAD_MODES:
        logging.warning("%s=%r is not one of %s; using %s", VAD_ENV, raw, "|".join(VAD_MODES), default)
        return default
    if raw == "silero" and not available:
        logging.warning("%s=silero but silero-vad is not importable (%s); using energy",
                        VAD_ENV, _silero.get("error", "unknown"))
        return "energy"
    return raw


def make_speech_gate(mode=None, environ=os.environ, **gate_kw):
    """A SpeechGate for one connection per DC_ASR_VAD, or None when 'off'."""
    mode = vad_mode(environ) if mode is None else mode
    if mode == "off":
        return None
    if mode == "silero":
        detector = SileroDetector()
    elif mode == "energy":
        detector = EnergyGate()
    else:
        raise ValueError("unknown VAD mode %r" % (mode,))
    return SpeechGate(detector, **gate_kw)


def make_frame_scorer(mode=None, environ=os.environ):
    """The assembler's frame scorer per DC_ASR_VAD (a detector of its own, on
    the thread that adds audio), or None when 'off': the cut is then blind."""
    mode = vad_mode(environ) if mode is None else mode
    if mode == "off":
        return None
    if mode == "silero":
        return SileroDetector()
    if mode == "energy":
        return EnergyGate()
    raise ValueError("unknown VAD mode %r" % (mode,))
