import logging
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
                extra_data = int(extra_time * self.sample_rate) * (self.channels * self.depth)
                self.audio_buffer = self.audio_buffer[extra_data:]
                self.buffer_start += extra_time

    def extract(self, start_time, end_time):
        with self.lock:
            start_byte = int((start_time - self.buffer_start) * self.sample_rate) * (self.channels * self.depth)
            end_byte = int((end_time - self.buffer_start) * self.sample_rate) * (self.channels * self.depth)
            return self.audio_buffer[start_byte: end_byte]
