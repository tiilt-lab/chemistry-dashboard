from genericpath import isfile
import logging
import numpy as np
from scipy.io import wavfile
import os
import numpy as np


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
        except Exception:
            # print() went nowhere under systemd; a full disk was invisible.
            logging.exception('Unable to write audio data to %s', self.dat_filename)

    def close(self):
        if self.closed:
            return
        try:
            dtype = np.float32 if self.depth == 4 else np.int16
            if os.path.getsize(self.dat_filename) == 0:
                all_data = np.zeros((0, self.channels), dtype=dtype)
            else:
                # memmap instead of read(): a multi-hour multi-channel .dat is
                # GBs, and this runs at teardown — pages stream through the
                # page cache instead of being materialized in RAM.
                raw = np.memmap(self.dat_filename, dtype=dtype, mode='r')
                # A disconnect mid-write can truncate the final frame; trim to
                # whole frames instead of letting reshape abort the close.
                chunk_length = len(raw) // self.channels
                all_data = raw[:chunk_length * self.channels].reshape(
                    (chunk_length, self.channels))
            wavfile.write(self.wav_filename, self.sample_rate, all_data)
            del all_data
            os.remove(self.dat_filename)
            self.closed = True
        except Exception:
            logging.exception('WaveRecorder close failed for %s', self.dat_filename)

class VidRecorder:

    def __init__(self, filename,sample_rate,depth,channels,mediaExt):
        self.vid_filename = filename + '.'+mediaExt
        self.cart_vid = filename+'_caart'+'.mp4'
        self.img_file = filename
        self.closed = False
        self.sample_rate = sample_rate
        self.depth = depth
        self.channels = channels

    def write(self, data):
        try:
            with open(self.vid_filename, "ab") as f:
                f.write(data)
        except Exception as e:
            print('Unable to write data to file: {0}'.format(e))

    def read_temp_wav(self,filename):
        try:
            with open(filename, "rb") as f:
                byteAudio = f.read()
                return byteAudio
        except Exception as e:
            print('Unable to read temp audio data to file: {0}'.format(e))  

    def close(self):
        if not self.closed:
            try:
                if os.path.isfile(self.vid_filename):
                    os.remove(self.vid_filename)        
            except Exception as e:
              logging.info('Unable to delete video file: {0}'.format(e))         
            
            self.closed = True
            