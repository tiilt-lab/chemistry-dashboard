from genericpath import isfile
import logging
import numpy as np
from scipy.io import wavfile
import os
import numpy as np
import cv2
from video_cartoonizer.cartoonizer import caart


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

    def __init__(self, filename,samplevid, is_save):
        self.vid_filename = filename + '.webm'
        self.cart_vid = filename+'_caart'+'.mp4'
        self.img_file = filename
        self.read_vid = samplevid+'.mp4'
        self.closed = False
        self.save_video = is_save

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

    def convert_video_to_cartoon(self,path):
        video_capture = cv2.VideoCapture(path)
        out = cv2.VideoWriter(self.cart_vid, cv2.VideoWriter_fourcc(*'H264'), 25, (640, 480),True)
        still_reading, image = video_capture.read()
        while still_reading:
            img=caart(image)
            vidout=cv2.resize(img,(640,480))
            out.write(vidout)
            # read next image
            still_reading, image = video_capture.read()
        video_capture.release()
        cv2.destroyAllWindows()


    def close(self):
        if not self.closed:
            try:
                if not self.save_video and  os.path.isfile(self.vid_filename):
                    os.remove(self.vid_filename)
                else:
                    #self.convert_video_to_cartoon(self.vid_filename)
                    pass
            except Exception as e:
              logging.info('Unable to delete video file: {0}'.format(e))         
            
            self.closed = True