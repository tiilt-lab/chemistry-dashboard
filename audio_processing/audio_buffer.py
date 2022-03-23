import threading

class AudioBuffer:
    BUFFER_SIZE = 180 # Max amount of audio data stored in seconds.

    def __init__(self, config):
        self.audio_buffer = bytearray()
        self.buffer_start = 0
        self.buffer_end = 0
        self.config = config
        self.sample_rate = 16000 #self.config.sample_rate
        self.channels = self.config.channels
        self.depth = 2 # self.config.depth
        self.lock = threading.Lock()

    def append(self, data):
        with self.lock:
            self.audio_buffer.extend(data)
            self.buffer_end += len(data) / (self.sample_rate * self.channels * self.depth)
            if self.buffer_end - self.buffer_start > AudioBuffer.BUFFER_SIZE:
                extra_time = self.buffer_end - self.buffer_start - AudioBuffer.BUFFER_SIZE
                extra_data = int(extra_time * self.sample_rate) * (self.channels * self.depth)
                self.audio_buffer = self.audio_buffer[extra_data:]
                self.buffer_start += extra_time
            # print(f"sr: {self.sample_rate}")
                

    def extract(self, start_time, end_time):
        with self.lock:
            start_byte = int((start_time - self.buffer_start) * self.sample_rate) * (self.channels * self.depth)
            end_byte = int((end_time - self.buffer_start) * self.sample_rate) * (self.channels * self.depth)
            print(f"buffer start/end: {self.buffer_start}/{self.buffer_end}")
            print(f"audio buffer start/end time: {start_time}/{end_time}")
            print(f"audio buffer len: {len(self.audio_buffer)}")
            print(f"audio buffer start/end byte: {start_byte}/{end_byte}")
            print(f"audio buffer extracted len: {len(self.audio_buffer[start_byte: end_byte])}")
            return self.audio_buffer[start_byte: end_byte]
            # return self.audio_buffer