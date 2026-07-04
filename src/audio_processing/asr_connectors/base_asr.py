"""Common contract for ASR connectors.

Every connector consumes raw PCM audio chunks from ``audio_queue`` and pushes
recognition results onto ``transcript_queue``, terminating with a ``None``
sentinel. Downstream (``processor.py``) reads results in Google Cloud Speech's
object shape:

    result.alternatives[0].transcript
    result.alternatives[0].words[i].word
    result.alternatives[0].words[i].start_time.seconds / .nanos
    result.alternatives[0].words[i].end_time.seconds / .nanos

The adapter classes below reproduce that shape so a non-Google connector can
emit results without any change to the consumer. GoogleASR already emits native
protobuf objects of this shape, so it does not need the adapters.
"""

NANO = 1_000_000_000


class AsrTime:
    def __init__(self, total_seconds):
        total_seconds = max(0.0, float(total_seconds))
        self.seconds = int(total_seconds)
        self.nanos = int(round((total_seconds - self.seconds) * NANO))


class AsrWord:
    def __init__(self, word, start_time, end_time):
        self.word = word
        self.start_time = AsrTime(start_time)
        self.end_time = AsrTime(end_time)


class AsrAlternative:
    def __init__(self, transcript, words):
        self.transcript = transcript
        self.words = words


class AsrResult:
    """Google-compatible result. ``words`` is a list of (text, start_s, end_s)."""

    def __init__(self, transcript, words):
        self.alternatives = [
            AsrAlternative(
                transcript,
                [AsrWord(w, s, e) for (w, s, e) in words],
            )
        ]


class BaseASR:
    """Base for ASR connectors. Subclasses implement start()/stop().

    Constructor signature is fixed so connectors are interchangeable via the
    factory:
        (audio_queue, transcript_queue, config, media_type, interval)
    """

    SAMPLE_RATE = 16000
    DEPTH = 2  # bytes per sample (16-bit PCM)

    def __init__(self, audio_queue, transcript_queue, config, media_type, interval):
        self.audio_queue = audio_queue
        self.transcript_queue = transcript_queue
        self.config = config
        self.media_type = media_type
        self.audio_interval = interval
        self.running = False

    def start(self):
        raise NotImplementedError

    def stop(self):
        self.running = False
