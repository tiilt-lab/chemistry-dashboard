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

    def __init__(self, filename, tempvidfilename, tempaudfilename):
        self.dat_filename = filename + '.dat'
        self.vid_filename = filename + '.mp4'
        self.temp_vid_filename =  tempvidfilename + '.mp4'
        self.temp_aud_filename =  tempaudfilename + '.wav'
        self.closed = False

    def write(self, data):
        try:
            with open(self.dat_filename, "ab") as f:
                f.write(data)
        except Exception as e:
            print('Unable to write data to file: {0}'.format(e))

    def write_temp_mp4(self,data):
        try:
            if os.path.isfile(self.temp_vid_filename):
                os.remove(self.temp_vid_filename)

            with open(self.temp_vid_filename, "wb") as out_file:
                out_file.write(data)
        except Exception as e:
            print('Unable to write temp video data to file: {0}'.format(e))        

    def read_temp_wav(self):
        try:
            with open(self.temp_aud_filename, "rb") as f:
                byteAudio = f.read()
                return byteAudio
        except Exception as e:
            print('Unable to read temp audio data to file: {0}'.format(e))  

    def close(self):
        if not self.closed:
            try:
                #remove all temp video and audio files
                if os.path.isfile(self.temp_vid_filename):
                    os.remove(self.temp_vid_filename)

                if os.path.isfile(self.temp_aud_filename):
                    os.remove(self.temp_aud_filename)

                #save dat binary file as mp4    
                with open(self.dat_filename, "rb") as f:
                    all_data = f.read()
                
                if os.path.isfile(self.vid_filename):
                    os.remove(self.vid_filename)

                with open(self.vid_filename, "wb") as out_file:
                    out_file.write(all_data)  
            except Exception as e:
              print('Unable to write video data to file: {0}'.format(e))         
            os.remove(self.dat_filename)
            self.closed = True