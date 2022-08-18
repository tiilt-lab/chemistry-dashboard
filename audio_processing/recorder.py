from genericpath import isfile
import numpy as np
from scipy.io import wavfile
import os

class WaveRecorder:

    def __init__(self, filename, sample_rate, depth, channels):
        self.dat_filename = filename + '.dat'
        self.wav_filename = filename + '.wav'
        self.sample_rate = sample_rate
        self.depth = depth
        self.channels = channels
        self.closed = False

    def write(self, data):
        try:
            with open(self.dat_filename, "ab") as f:
                f.write(data)
        except Exception as e:
            print('Unable to write data to file: {0}'.format(e))

    def close(self):
        if not self.closed:
            with open(self.dat_filename, "rb") as f:
                all_data = f.read()
                all_data = np.frombuffer(all_data, np.float32 if self.depth == 4 else np.int16, -1)
                chunk_length = int(len(all_data) / self.channels)
                all_data = np.reshape(all_data, (chunk_length, self.channels))
            wavfile.write(self.wav_filename, self.sample_rate, all_data)
            os.remove(self.dat_filename)
            self.closed = True

class VidRecorder:

    def __init__(self, filename):
        self.dat_filename = filename + '.dat'
        self.vid_filename = filename + '.mp4'
        self.closed = False

    def write(self, data):
        try:
            with open(self.dat_filename, "ab") as f:
                f.write(data)
        except Exception as e:
            print('Unable to write data to file: {0}'.format(e))

    def close(self):
        if not self.closed:
            with open(self.dat_filename, "rb") as f:
                all_data = f.read()
            
            if os.path.isfile(self.vid_filename):
                os.remove(self.vid_filename)

            with open(self.vid_filename, "wb") as out_file:
                out_file.write(all_data)  
                  
            os.remove(self.dat_filename)
            self.closed = True