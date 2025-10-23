from genericpath import isfile
import logging
import numpy as np
from scipy.io import wavfile
import os
import numpy as np
import cv2
from moviepy.editor import *

class VidRecorder:

    def __init__(self,filename,aud_filename,vid_img_dir, is_save,sample_rate,depth,channels,mediaExt):
        self.vid_filename = filename + '.'+mediaExt
        self.cart_vid = filename+'_caart'+'.mp4'
        self.img_file = filename
        self.closed = False
        self.save_video = is_save
        self.vid_img_dir = vid_img_dir
        self.dat_filename = aud_filename + '.dat'
        self.wav_filename = aud_filename + '.wav'
        self.sample_rate = sample_rate
        self.depth = depth
        self.channels = channels

    def write_audio(self, data):
        try:
            with open(self.dat_filename, "ab") as f:
                f.write(data)
        except Exception as e:
            print('Unable to write data to file: {0}'.format(e))

    def write(self, data,path):
        try:
            with open(path, "ab") as f:
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

    def convert_dat_to_wav(self):
        with open(self.dat_filename, "rb") as f:
            all_data = f.read()
            all_data = np.frombuffer(all_data, np.float32 if self.depth == 4 else np.int16, -1)
            chunk_length = int(len(all_data) / self.channels)
            all_data = np.reshape(all_data, (chunk_length, self.channels))
        wavfile.write(self.wav_filename, self.sample_rate, all_data)
        os.remove(self.dat_filename)

    def close(self,path):
        if not self.closed:
            try:
                if not self.save_video and  os.path.isfile(path):
                    os.remove(path)        
            except Exception as e:
              logging.info('Unable to delete video file: {0}'.format(e))         
            
            self.closed = True