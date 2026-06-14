import logging
import threading
import time
import config as cf
import traceback
import moviepy.editor as mp
import os
import warnings
import logging
import json
import cv2
import tempfile
import subprocess

import callbacks
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from queue import Queue,Empty, Full
from global_singleton_lock import attention_emotion_predictor_lock, object_detector_lock
from concurrent.futures import TimeoutError

WAIT_TIMEOUT = 0.05   # 50 ms (tune this)

class VideoProcessorPosthoc:
    def __init__(self,facial_emotion_detector,image_object_detection,attention_detection,video_metric_analytics,video_file,config,running_video_processes,video_interval,batch_size,vid_img_dir,STOP_SIGNAL,save_gaze_annotation=False):
        
        self.facial_emotion_detector = facial_emotion_detector
        self.image_object_detection = image_object_detection
        self.attention_detection = attention_detection
        self.video_metric_analytics = video_metric_analytics
        self.video_file = video_file
        self.config = config
        self.running_video_processes = running_video_processes
        self.video_interval = video_interval
        self.STOP = STOP_SIGNAL
        self.batch_size = batch_size
        self.frame_batch = []
        self.time_marker = []
        self.vid_img_dir = vid_img_dir

        self.frame_count = 1
        self.frame_array = []
        self.lock = threading.Lock()
        self.batch_track = 0
       
        self.web_socket_connection = None
        self.facialEmbeddings = None
        self.video_chunk_count = -1

        if save_gaze_annotation and not os.path.exists(self.vid_img_dir):
            os.mkdir(self.vid_img_dir)
       
    def start(self):
        self.running = True
        self.vid_pro_thread = threading.Thread(target=self.processing, name="video_posthoc_processing")
        self.vid_pro_thread.daemon = True
        self.vid_pro_thread.start()
        
    def stop(self):
        self.running = False
        # self.vid_pro_thread.join()

    def add_websocket_connection(self,web_socket):
        self.web_socket_connection = web_socket

    def setParticpantFacialEmbeddings(self,facialEmbeddings):
        self.facialEmbeddings = facialEmbeddings

    def send_json(self, message):
        payload = json.dumps(message).encode('utf8')
        self.web_socket_connection.sendMessage(payload, isBinary = False)
        

    def adjust_time(self,frame_sec_mark):
        offset = self.config.start_offset
        return round(offset+ (frame_sec_mark + (self.video_interval * self.video_chunk_count)))
    
    def processing(self):
        try:
            #uncomment later
            # if self.image_object_detection.running == False:
            #     self.image_object_detection.start()

            # if self.video_metric_analytics.running == False:
            #     self.video_metric_analytics.start()

            with tempfile.TemporaryDirectory() as tmpdir:
                logging.info("temp dir is {0}".format(tmpdir))
                warming_error_count  = 0 
                vidclip = mp.VideoFileClip(self.video_file)

                current_dir = Path(__file__).resolve().parent
                # Go up two level (parent)
                parent_dir = current_dir.parent.parent
                # Go into sibling directory
                target_dir = parent_dir / "video_processing" / "videorecordings"
                final_audio_file = os.path.join(target_dir, "{0} ({1})_audio.wav".format(self.config.auth_key, str(time.ctime())))
                chunk_files = []
                for start in range(0, int(vidclip.duration), self.video_interval):
                    end = min(start + self.video_interval, vidclip.duration)
                    dur = end-start

                    if self.running == False:
                        logging.info("Video processor posthoc thread stop initiated")
                        break
                    try:
                        with warnings.catch_warnings():
                            warnings.simplefilter("error", UserWarning)

                            subclip = vidclip.subclip(start, end)

                            #use this to extract audio incase of incomplete audio in the original audio file
                            chunk_path = os.path.join(tmpdir, f"chunk_{start:04d}.wav")

                            subprocess.run([
                                            "ffmpeg",
                                            "-y",
                                            "-ss", str(start),
                                            "-t", str(dur),
                                            "-i", self.video_file,
                                            "-vn",
                                            "-ar", "16000",
                                            "-ac", "1",
                                            "-acodec", "pcm_f32le",
                                            chunk_path
                                        ], check=True)
                            chunk_files.append(chunk_path)

                            self.video_chunk_count+=1
                            subclib_frame_count = 0
                            for ts, frame in subclip.iter_frames(fps=12, dtype="uint8", with_times=True):
                                subclib_frame_count =  subclib_frame_count + 1
                                # self.frame_batch.append(frame)
                                self.frame_batch.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                                self.time_marker.append(self.adjust_time(ts))
                                # logging.info("frame size is {0}, dtype is {1}, min is {2}, max is {3}".format(frame.shape, frame.dtype, frame.min(), frame.max()))
                                if len(self.frame_batch) == self.batch_size:
                                    logging.info(f"batch being inserted is {self.batch_track}")
                                    payload = [self.frame_batch, self.facialEmbeddings, self.batch_track, self.time_marker, self.vid_img_dir, self.config.auth_key,False]
                                    accumulator_load = self.image_object_detection.worker_posthoc(payload)  
                                    self.video_metric_analytics.worker_posthoc(accumulator_load)
                                
                                    self.frame_batch = []
                                    self.time_marker = []
                                
                                    self.batch_track += 1
                                #if i read 300 frames from this chunk then break
                                if subclib_frame_count == 300:
                                    break

                            subclip.close() 
                    except UserWarning as e:
                        warming_error_count += 1
                        logging.info(f"Frame read warning turned error: {e}")
                        if warming_error_count > 2:
                            break
                            # self.stop()

                # push the rest of the batched frames adjtime to queue
                payload = [self.frame_batch, self.facialEmbeddings, self.batch_track, self.time_marker, self.vid_img_dir, self.config.auth_key,False]
                
                accumulator_load = self.image_object_detection.worker_posthoc(payload)  
                self.video_metric_analytics.worker_posthoc(accumulator_load)

                # create ffmpeg concat list
                list_file = os.path.join(tmpdir, "chunks.txt")
                with open(list_file, "w") as f:
                    for path in chunk_files:
                        f.write(f"file '{path}'\n")

                # concatenate into one final wav
                subprocess.run([
                                "ffmpeg",
                                "-y",
                                "-f", "concat",
                                "-safe", "0",
                                "-i", list_file,
                                "-ar", "16000",
                                "-ac", "1",
                                "-acodec", "pcm_f32le",
                                final_audio_file
                            ], check=True)
                vidclip.close()
        except Exception as e:
            error_str = traceback.format_exc()
            logging.warning('Exception thrown while Processing video posthoc video image extraction {0} {1}'.format(error_str, self.config.auth_key))
        finally:
                try:
                    logging.info("called finally after thread stop initiated")
                    self.running_video_processes.pop(self.config.auth_key,None)
                    payload = [self.frame_batch, self.facialEmbeddings, self.batch_track, self.time_marker, self.vid_img_dir, self.config.auth_key,True]
                    
                    accumulator_load = self.image_object_detection.worker_posthoc(payload) 
                    self.video_metric_analytics.worker_posthoc(accumulator_load)
                    
                    logging.info('Video Processor Posthoc  stopped for {0}.'.format(self.config.auth_key))
                    self.send_json({'type': 'process_completed', 'message': "Video posthoc analytics completed"})  
                except Full:
                    pass    
        