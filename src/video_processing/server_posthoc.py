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
import traceback
import scipy.signal
import config as cf
import cv2
import numpy as np
import torch
# torch>=2.6 defaults weights_only=True, which rejects several of the local
# model checkpoints (yolov4/crowdhuman pickles, gaze weights with numpy
# globals). These files ship with the deployment and are trusted.
_torch_load_original = torch.load
def _torch_load_permissive(*args, **kwargs):
    kwargs.setdefault('weights_only', False)
    return _torch_load_original(*args, **kwargs)
torch.load = _torch_load_permissive
import torch.backends.cudnn as cudnn
import moviepy.editor as mp
import face_recognition
# import ffmpeg

from pathlib import Path
from recorder import VidRecorder
from processing_config import ProcessingConfig
from connection_manager import ConnectionManager
from video_cartoonizer.videoprocessor_posthoc import VideoProcessorPosthoc
from datetime import datetime
from twisted.internet import reactor, task
from autobahn.twisted.websocket import WebSocketServerFactory
from autobahn.twisted.websocket import WebSocketServerProtocol
from queue import Full, Empty
from video_cartoonizer.video_cartoonify_loader import VideoCartoonifyLoader
from facial_biometric_processing_service import FacialBiometricProcessor
from emotion_detector.emotion_detection_model import EmotionDetectionModelV1
from attention_tracking.detect import ImageObjectDetection
from attention_tracking.attention_tracking import AttentionDetection
from video_cartoonizer.VideoMetricProcessor import VideoMetricAnalytics

STOP_SIGNAL = object()
cm = ConnectionManager()
# Gaze backend is config-selected: Gaze-LLE (open SOTA) or GazeFollow.
if cf.attention_model() == 'gazelle':
    from attention_tracking.gazelle_attention import GazeLLEAttentionDetection
    attention_detection = GazeLLEAttentionDetection()
else:
    attention_detection = AttentionDetection()
# Emotion backend is config-selected: 'hsemotion' (AffectNet-8, open SOTA)
# or the original ResMaskingNet.
if cf.emotion_model() == 'hsemotion':
    from emotion_detector.hsemotion_model import EmotionDetectionModelV2
    facial_emotion_detector = EmotionDetectionModelV2()
else:
    facial_emotion_detector = EmotionDetectionModelV1()
image_object_detection = ImageObjectDetection(STOP_SIGNAL,source="post_hoc")
video_metric_analytics = VideoMetricAnalytics(attention_detection, facial_emotion_detector, image_object_detection,STOP_SIGNAL,source="post_hoc")
batch_size = 40
running_video_processes = {}

class ServerProtocol(WebSocketServerProtocol):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_message = time.time()
        self.stream_data = False
        self.facial_emotion_detector = facial_emotion_detector
        self.image_object_detection = image_object_detection
        self.attention_detection = attention_detection
        self.video_metric_analytics = video_metric_analytics
        self.interval = 10
        self.batch_size = batch_size
        # Consulted by the connection manager's periodic key check and by
        # signal_end cleanup; post-hoc connections aren't live-key gated.
        self.running = False
        self.config = None

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

    def onClose(self, wasClean, code, reason):
        logging.info("close was trigered externally..... wasclean {0}, code {1}, reason {2}".format( wasClean, code, reason))
        self.signal_end()

    def process_json(self, data):
        if not 'type' in data:
            logging.warning('Message does not contain "type".')
            return
        
        if data['type'] == 'save-audio-video-fingerprinting':
            self.currStudent = data['id']
            self.stream_data = data['streamdata']
            self.mediaExt = data['mimeextension']
            self.currAlias = data['alias']
            if self.stream_data == 'audio-video-fingerprint':
                    self.video_file = os.path.join(cf.video_recordings_folder(), "{0}".format(self.currAlias))
                    self.vid_recorder = VidRecorder(self.video_file,"none","none",cf.video_record_original(),16000, 2, 1,self.mediaExt)
                    facial_biometric_file = os.path.join(cf.facial_embedding_folder(), "{0}".format(self.currAlias))
                    self.facial_processor = FacialBiometricProcessor(facial_biometric_file,self.video_file,self.mediaExt,self.currAlias)
                    self.facial_processor.add_websocket_connection(self)
                    
            logging.info('save-audio-video-fingerprinting: video process connected')
            self.send_json({'type':'saveaudiovideo'})

        if data['type'] == 'Initialize_video_processing_analytics':
            self.sessionid = data['sessionid']
            self.session_device_id = data['sessiondeviceid']
            self.server_start= data['server_start']
            self.facial_embeddings = dict()
            self.sample_rate = 16000
            self.video_file = self.get_video_file_path(self.session_device_id)

            if not self.video_file:
                self.send_json({'type': 'error', 'message': 'No video captured for this group.'})
            else:
                self.video_file = str(self.video_file)
                file_path_split = self.video_file.split("(")
                key = file_path_split[0].split("/")[-1].split("_")[0]
                off_set_date = file_path_split[1].split(")")[0]
                logging.info("key is {} and offset date is {}".format(key,off_set_date))

                #keep track of currently running posthoc video analytics
                if key in running_video_processes:
                    self.send_json({'type': 'error', 'message': 'Video posthoc analytics for this group is already running'})

                running_video_processes[key] = "running"

                conf_val = {'key':key,'encoding': "pcm_f16le", 'sample_rate': self.sample_rate,'channels': 2,'sessionid': self.sessionid,'deviceid': self.session_device_id,
                            'server_start':self.server_start,'off_set_date':off_set_date}
                valid, result = ProcessingConfig.from_json(conf_val,source="posthoc processing")
                if not valid:
                    logging.info("Confgiration setting failed for video posthoc processing")
                else:    
                    self.config = result
                    self.frame_dir = os.path.join(cf.video_recordings_folder(), "vid_img_frames_{0}_{1}_{2}_({3})".format(self.config.auth_key,self.config.sessionId,self.config.deviceId,  str(time.ctime())))
                    #start processing
                    for speaker in data['speakers']:
                        facial_embedding_file = os.path.join(cf.facial_embedding_folder(), "{0}".format(speaker["alias"]))
                        try:
                            facials = np.load(facial_embedding_file+".npy", allow_pickle=True).item()
                            self.facial_embeddings[speaker["id"]] = {"alias": speaker["alias"], "data": facials[speaker["alias"]]}
                        # except Exception as e:
                        #     try:
                        #         data_d = facials.pop("ro.kludy")
                        #         facials[speaker["alias"]] = data_d
                        #         self.facial_embeddings[speaker["id"]] = {"alias": speaker["alias"], "data": data_d}
                        #         # save back
                        #         np.save(facial_embedding_file+".npy", facials)
                        except Exception as e:
                            error_str = traceback.format_exc()
                            logging.info("error loading facial embedding for {} : {}".format(speaker["alias"],error_str))

                    self.signal_start()
                    self.video_processor.setParticpantFacialEmbeddings(self.facial_embeddings)

                    self.send_json({'type':'init posthoc analytics completed','message':"Starting Video Analytics Processing"})
                    logging.info('Video Posthoc analytics initiated')

        if data['type'] == 'start_posthoc_video_processing':
            self.send_json({'type':'video posthoc analytics started','message':"Processing Video posthoc Analytics"})
            self.video_processor.add_websocket_connection(self)
            self.video_processor.start()     

        if data['type'] == 'heartbeat':
            auth_key = data.get('key', None)
            logging.info("Recieved Heartbeat from client with authkey {0}".format(auth_key))
        if data['type'] == 'heartbeat_from_posthoc_processing':
            auth_key = data.get('key', None)
            logging.info("Recieved Heartbeat from client with authkey {0}".format(auth_key))   


    def process_binary(self, data):
        if self.stream_data == 'audio-video-fingerprint':
            self.vid_recorder.write(data,self.video_file+"."+self.mediaExt)

            self.facial_processor.start()     
        else:
            self.send_json({'type': 'error', 'message': 'Binary audio data sent before start message.'})

    def get_video_file_path(self,sessionDeviceId):
        current_dir = Path(__file__).resolve().parent
        # Go up one level (parent)
        parent_dir = current_dir.parent
        # Go into sibling directory
        target_dir = parent_dir / "video_processing" / "videorecordings"
        # Find file starting with prefix
        prefix = str(sessionDeviceId)
        files = list(target_dir.glob(f"{prefix}*.webm"))

        if files:
            file_path = files[-1]
            logging.info("Found: {}".format(file_path))
            return file_path
            # with open(file_path, "r") as f:
            #     content = f.read()
        else:
            logging.info("No file found")
            return None
    


    def send_json(self, message):
        payload = json.dumps(message).encode('utf8')
        self.sendMessage(payload, isBinary = False)

    def signal_start(self):
        self.video_processor = VideoProcessorPosthoc(self.facial_emotion_detector,self.image_object_detection,self.attention_detection,self.video_metric_analytics,
                                                     self.video_file,self.config,running_video_processes,self.interval,self.batch_size,self.frame_dir,STOP_SIGNAL,save_gaze_annotation=True)
    def signal_end(self):
        if self.video_processor:
            self.video_processor.stop()   


if __name__ == '__main__':
    cf.initialize()
    # Initialize Logger
    dir_path = os.path.dirname(os.path.realpath(__file__))
    log_format = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    log_file = logging.FileHandler(os.path.join(dir_path, 'video_posthoc_processing_service.log'))
    log_file.setFormatter(log_format)
    logger.addHandler(log_file)
    log_console = logging.StreamHandler()
    log_console.setFormatter(log_format)
    logger.addHandler(log_console)

    # Init and load share model resources
    image_object_detection.init_model(batch_size) 
    attention_detection.init_model(batch_size) 
    facial_emotion_detector.load_model() 
    # image_object_detection.start()
    # video_metric_analytics.start() 

    # Run Server
    logging.info('Starting Video Posthoc Processing Service...')
    poll_connections = task.LoopingCall(cm.check_connections)
    poll_connections.start(10.0)
    auth_connections = task.LoopingCall(cm.check_connection_authentication)
    auth_connections.start(5.0)
    factory = WebSocketServerFactory()
    factory.protocol = ServerProtocol
    reactor.listenTCP(int(os.environ.get("DC_VIDEO_POSTHOC_WS_PORT", 9004)), factory)
    logging.info('Video Posthoc Processing Service started.')
    reactor.run()
    logging.info('Video Posthoc Processing Service ended.')