import threading

class AudioBuffer:
    BUFFER_SIZE = 180 # Max amount of audio data stored in seconds.

    def __init__(self, config, max_seconds=None):
        self.audio_buffer = bytearray()
        self.buffer_start = 0
        self.buffer_end = 0
        self.config = config
        self.sample_rate = 16000
        self.channels = self.config.channels
        self.depth = 2
        # Batch ASRs (WhisperX post-hoc) emit results only after the whole
        # file is transcribed, so the buffer must hold the full recording —
        # the default 180s window is only right for streaming recognizers.
        self.max_seconds = max_seconds or AudioBuffer.BUFFER_SIZE
        self.lock = threading.Lock()

    def append(self, data):
        with self.lock:
            self.audio_buffer.extend(data)
            self.buffer_end += len(data) / (self.sample_rate * self.channels * self.depth)
            if self.buffer_end - self.buffer_start > self.max_seconds:
                extra_time = self.buffer_end - self.buffer_start - self.max_seconds
                extra_samples = int(extra_time * self.sample_rate)
                extra_data = extra_samples * (self.channels * self.depth)
                self.audio_buffer = self.audio_buffer[extra_data:]
                # Advance by exactly what was trimmed. Advancing by the float
                # extra_time while trimming int(extra_time*sr) samples skewed
                # start by up to a sample per trim (~0.5s/hour on long live
                # sessions), slowly misaligning extracts vs word timings.
                self.buffer_start += extra_samples / self.sample_rate

    def extract(self, start_time, end_time):
        with self.lock:
            # Clamp: a stale/late timestamp older than the retention window
            # produced NEGATIVE byte offsets, silently returning audio from
            # the wrong end of the buffer.
            start_byte = int((start_time - self.buffer_start) * self.sample_rate) * (self.channels * self.depth)
            end_byte = int((end_time - self.buffer_start) * self.sample_rate) * (self.channels * self.depth)
            start_byte = max(0, start_byte)
            end_byte = max(start_byte, end_byte)
            return self.audio_buffer[start_byte: end_byte]
