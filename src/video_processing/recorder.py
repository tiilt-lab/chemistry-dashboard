import logging
import os
try:
    from moviepy.editor import *  # moviepy 1.x
except ImportError:
    from moviepy import *  # moviepy 2.x dropped the .editor module

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
        # logging.error, not print(): under systemd print went nowhere, so a
        # full disk dropped every chunk invisibly while bytes_received kept
        # counting — neither the no-video nor the lag alarm ever fired.
        try:
            with open(self.dat_filename, "ab") as f:
                f.write(data)
            return True
        except Exception:
            logging.exception('RECORDING LOSS: unable to write audio to %s', self.dat_filename)
            return False

    def write(self, data,path):
        try:
            with open(path, "ab") as f:
                f.write(data)
            return True
        except Exception:
            logging.exception('RECORDING LOSS: unable to write video to %s', path)
            return False

    def close(self,path):
        if not self.closed:
            try:
                if not self.save_video and  os.path.isfile(path):
                    os.remove(path)        
            except Exception as e:
              logging.info('Unable to delete video file: {0}'.format(e))         
            
            self.closed = True