from genericpath import isfile
import logging
import numpy as np
from scipy.io import wavfile
import os
import numpy as np
import cv2
from moviepy.editor import *
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

    def __init__(self, filename,aud_filename,vid_img_dir, is_save,sample_rate,depth,channels):
        self.vid_filename = filename + '.webm'
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
        os.mkdir(self.vid_img_dir)

    def write_audio(self, data):
        try:
            with open(self.dat_filename, "ab") as f:
                f.write(data)
        except Exception as e:
            print('Unable to write data to file: {0}'.format(e))

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

    def convert_dat_to_wav(self):
        with open(self.dat_filename, "rb") as f:
            all_data = f.read()
            all_data = np.frombuffer(all_data, np.float32 if self.depth == 4 else np.int16, -1)
            chunk_length = int(len(all_data) / self.channels)
            all_data = np.reshape(all_data, (chunk_length, self.channels))
        wavfile.write(self.wav_filename, self.sample_rate, all_data)
        os.remove(self.dat_filename)

    def convert_video_to_cartoon(self,path):
        # convert audio to wav
        self.convert_dat_to_wav()

        #start cartoonization
        video_capture = cv2.VideoCapture(path)
        video_capture.set(cv2.CAP_PROP_FRAME_WIDTH,640)
        video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT,480)
        #out = cv2.VideoWriter(self.cart_vid, cv2.VideoWriter_fourcc(*'mp4v'), 20, (640, 480),True)
        currentframe = 1
        while (video_capture.isOpened()):   
            still_reading, image = video_capture.read()
            if still_reading:
                frame_name = os.path.join(self.vid_img_dir, "{0}".format(currentframe))
                img=caart(image)
                cv2.imwrite(frame_name+".png",img)
                # vidout=cv2.resize(img,(640,480))
                # out.write(vidout)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            else:
                break  
            currentframe+=1
        video_capture.release()
        #out.release()
        cv2.destroyAllWindows()

        sortedfiles = [int(f.split(".")[0]) for f in os.listdir(self.vid_img_dir)]
        sortedfiles.sort()
    
        file_path = [os.path.join(self.vid_img_dir,str(fp)+".png") for fp in sortedfiles] 
        video = ImageSequenceClip(file_path,fps=29)
        audio_clip = AudioFileClip(self.wav_filename)
        new_audio_clip = CompositeAudioClip([audio_clip])
        video.audio = new_audio_clip
        video.write_videofile(self.cart_vid)


    def close(self):
        if not self.closed:
            try:
                if not self.save_video and  os.path.isfile(self.vid_filename):
                    os.remove(self.vid_filename)
                else:
                    self.convert_video_to_cartoon(self.vid_filename)
                    #rmove all the imgae frames
                    for file in os.listdir(self.vid_img_dir):
                        os.remove(os.path.join(self.vid_img_dir,file))
                    os.rmdir(self.vid_img_dir)
                    os.remove(self.wav_filename)
                    
            except Exception as e:
              logging.info('Unable to delete video file: {0}'.format(e))         
            
            self.closed = True