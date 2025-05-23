import os
import json
import time
import glob
import queue
import shutil
import logging
import callbacks
import threading
import weakref
import wave
import scipy.signal
import config as cf
import numpy as np
import moviepy.editor as mp
from recorder import VidRecorder
from processing_config import ProcessingConfig
from connection_manager import ConnectionManager
# from video_cartoonizer.videoprocessor import VideoProcessor
from datetime import datetime
from twisted.internet import reactor, task
from autobahn.twisted.websocket import WebSocketServerFactory
from autobahn.twisted.websocket import WebSocketServerProtocol
from video_cartoonizer.video_cartoonify_loader import VideoCartoonifyLoader
from emotion_detector.emotion_detection_model import EmotionDetectionModel

cm = ConnectionManager()
cartoon_model = VideoCartoonifyLoader()
facial_emotion_detector = EmotionDetectionModel()

class ServerProtocol(WebSocketServerProtocol):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = None
        self.running = False
        self.processor = None
        self.cartoon_model = cartoon_model
        self.facial_emotion_detector = facial_emotion_detector
        self.video_processor = None
        self.last_message = time.time()
        self.end_signaled = False
        self.interval = 10
        self.stream_data = False
        cm.add(self)
        logging.info('New client connected...')

    def onMessage(self, payload, is_binary):
        self.last_message = time.time()
        if is_binary:
            try:
                self.process_binary(payload)
            except Exception as e:
                logging.warning('Error processing binary: {0}'.format(e))
        else:
            valid_json = False
            try:
                payload = payload.decode('utf-8')
                data = json.loads(payload)
                valid_json = True
            except Exception as e:
                logging.warning('Payload is not properly formatted JSON.')
                self.send_json({'type': 'error', 'message': 'Payload is not properly formatted JSON.'})
            if valid_json:
                try:
                    self.process_json(data)
                except Exception as e:
                    logging.warning('Error processing json: {0}'.format(e))

    def onClose(self, *args, **kwargs):
        self.signal_end()

    def process_json(self, data):
        if not 'type' in data:
            logging.warning('Message does not contain "type".')
            return
        if data['type'] == 'start':
            valid, result = ProcessingConfig.from_json(data)
            if not valid:
                self.send_json({'type': 'error', 'message': result})
                self.signal_end()
            else:
                self.config = result
                cm.associate_keys(self, self.config.session_key, self.config.auth_key)
                self.stream_data = data['streamdata']
                self.video_count = 1
                if cf.video_record_original():
                    aud_filename = os.path.join(cf.video_recordings_folder(), "{0}_{1}_{2}_({3})_audio".format(self.config.auth_key,self.config.sessionId,self.config.deviceId, str(time.ctime())))
                    self.filename = os.path.join(cf.video_recordings_folder(), "{0}_{1}_{2}_({3})_orig".format(self.config.auth_key,self.config.sessionId,self.config.deviceId, str(time.ctime())))
                    self.frame_dir = os.path.join(cf.video_recordings_folder(), "vid_img_frames_{0}_{1}_{2}_({3})".format(self.config.auth_key,self.config.sessionId,self.config.deviceId,  str(time.ctime())))
                    self.orig_vid_recorder = VidRecorder(self.filename,aud_filename,self.frame_dir,cf.video_record_original(),16000, 2, 1)

                    if self.config.videocartoonify:
                        self.video_queue = queue.Queue()
                        self.frame_queue = None
                        self.cartoon_image_queue = None
                        self.video_processor = VideoProcessor(self.cartoon_model,self.facial_emotion_detector,self.video_queue,self.frame_queue,self.cartoon_image_queue,self.config,self.frame_dir,self.filename,aud_filename,16000, 2,1)
                        
                if cf.video_record_reduced():
                    aud_filename = os.path.join(cf.video_recordings_folder(), "{0}_{1}_{2}_({3})_audio".format(self.config.auth_key,self.config.sessionId,self.config.deviceId, datetime.today().strftime("%Y-%m-%d")))
                    self.filename = os.path.join(cf.video_recordings_folder(), "{0}_{1}_{2}_({3})_redu".format(self.config.auth_key,self.config.sessionId,self.config.deviceId, datetime.today().strftime("%Y-%m-%d")))
                    self.frame_dir = os.path.join(cf.video_recordings_folder(), "vid_img_frames_{0}_{1}_{2}_({3})".format(self.config.auth_key,self.config.sessionId,self.config.deviceId, datetime.today().strftime('%Y-%m-%d')))
                    self.redu_vid_recorder = VidRecorder(self.filename,aud_filename,self.frame_dir,cf.video_record_original(),16000, 2, 1)

                self.signal_start()
                self.send_json({'type':'start'})

    def process_binary(self, data):
        if self.running:
            if cf.video_record_original():
                self.orig_vid_recorder.write(data)

            temp_aud_file = os.path.join(cf.video_recordings_folder(), "{0} ({1})_tempvid".format(self.config.auth_key, str(time.ctime())))
            vidclip = mp.VideoFileClip(self.filename+'.webm')
            subclips = vidclip.subclip((self.video_count-1)*self.interval,self.video_count*self.interval)
            subclips.audio.write_audiofile(temp_aud_file+'.wav',fps=16000,bitrate='50k') #nbytes=2,codec='pcm_s16le',

            wavObj = wave.open(temp_aud_file+'.wav')
            audiobyte = self.reduce_wav_channel(1,wavObj)

            if self.config.videocartoonify:
                self.video_queue.put(subclips.iter_frames())
                logging.info('i just inserted video data  for {0}'.format(self.config.auth_key))

            # Save audio data only if cartoonization is activated.
            # as we need to merge the audio data with the carttonized video
            if self.config.videocartoonify:
                self.orig_vid_recorder.write_audio(audiobyte)

            if os.path.isfile(temp_aud_file+'.wav'):
                os.remove(temp_aud_file+'.wav')

            self.video_count = self.video_count + 1
        else:
            self.send_json({'type': 'error', 'message': 'Binary audio data sent before start message.'})

    def send_json(self, message):
        payload = json.dumps(message).encode('utf8')
        self.sendMessage(payload, isBinary = False)

    def read_bytes_from_wav(self,wav):
        wav.setpos(0)
        sdata = wav.readframes(wav.getnframes())
        data = np.frombuffer(sdata,dtype=np.dtype('int16'))
        return data.tobytes()

    def reduce_wav_channel(self,channels_wanted,wav):
        if channels_wanted < self.config.channels:
            nch = wav.getnchannels()
            wav.setpos(0)
            sdata = wav.readframes(wav.getnframes())
            data = np.frombuffer(sdata,dtype=np.dtype('int16'))
            ch_data = data[0::nch]
            return ch_data.tobytes()
        else:
            self.read_bytes_from_wav(wav)


    def signal_start(self):
        if self.video_processor:
            self.video_processor.start()
        self.running = True

    def send_close(self, message):
        self.send_json({'type': 'end', 'message': message})

    def signal_end(self):
        if self.end_signaled:
            return
        self.end_signaled = True

        if  self.video_processor:
            self.video_processor.stop()

        if self.config:
            cm.remove(self, self.config.session_key, self.config.auth_key)
        else:
            cm.remove(self, None, None)
        logging.info('Closing client connection...')
        self.transport.loseConnection()

        # Begin Post Processing
        if cf.video_record_original() and self.stream_data == 'video':
            self.orig_vid_recorder.close()

if __name__ == '__main__':
    cf.initialize()

    # Initialize Logger
    dir_path = os.path.dirname(os.path.realpath(__file__))
    log_format = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    log_file = logging.FileHandler(os.path.join(dir_path, 'video_processing_service.log'))
    log_file.setFormatter(log_format)
    logger.addHandler(log_file)
    log_console = logging.StreamHandler()
    log_console.setFormatter(log_format)
    logger.addHandler(log_console)

    # Initialize cartoonify
    if cf.video_cartoonize():
        cartoon_model.load_model()
        facial_emotion_detector.load_model()
    # Run Server
    logging.info('Starting video Processing Service...')
    poll_connections = task.LoopingCall(cm.check_connections)
    poll_connections.start(10.0)
    auth_connections = task.LoopingCall(cm.check_connection_authentication)
    auth_connections.start(5.0)
    factory = WebSocketServerFactory()
    factory.protocol = ServerProtocol
    reactor.listenTCP(9003, factory)
    logging.info('Video Processing Service started.')
    reactor.run()
    logging.info('Video Processing Service ended.')
