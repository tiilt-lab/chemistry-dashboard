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

import callbacks
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
            vidclip = mp.VideoFileClip(self.video_file)
            for start in range(0, int(vidclip.duration), self.video_interval):
                end = min(start + self.video_interval, vidclip.duration)

                if self.running == False:
                    logging.info("Video processor posthoc thread stop initiated")
                    break
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("error", UserWarning)

                        subclip = vidclip.subclip(start, end) 
                        self.video_chunk_count+=1
                        subclib_frame_count = 0
                        for ts, frame in subclip.iter_frames(fps=12, dtype="uint8", with_times=True):
                            subclib_frame_count =  subclib_frame_count + 1
                            self.frame_batch.append(frame)
                            self.time_marker.append(self.adjust_time(ts))
                            if len(self.frame_batch) == self.batch_size:
                                #pass to consumer frame
                                payload = [self.frame_batch, self.facialEmbeddings, self.batch_track, self.time_marker, self.vid_img_dir, self.config.auth_key]
                                self.enqueue_latest_frame_payload(payload,self.config.auth_key)

                                self.frame_batch = []
                                self.time_marker = []
                            
                                self.batch_track += 1
                            #if i read 300 frames from this chunk then break
                            if subclib_frame_count == 300:
                                break
                except UserWarning as e:
                    logging.info(f"Frame read warning turned error: {e}")
                    self.stop()

                
                # push the rest of the batched frames adjtime to queue
                payload = [self.frame_batch, self.facialEmbeddings, self.batch_track, self.time_marker, self.vid_img_dir, self.config.auth_key]
                self.enqueue_latest_frame_payload(payload,self.config.auth_key)

        except Exception as e:
            error_str = traceback.format_exc()
            logging.warning('Exception thrown while Processing video posthoc video image extraction {0} {1}'.format(error_str, self.config.auth_key))
        finally:
                try:
                    logging.info("called finally after thread stop initiated")
                    self.image_object_detection.user_completed.add(self.config.auth_key)
                    self.running_video_processes.pop(self.config.auth_key,None)
                    logging.info('Video Processor Posthoc  stopped for {0}.'.format(self.config.auth_key))
                    self.send_json({'type': 'process_completed', 'message': "Video posthoc analytics completed"})  
                except Full:
                    pass    


    def enqueue_latest_frame_payload(self, payload,candidate_queue_id, timeout=0.6):
        """
        Keep only the most recent chunk in the queue.
        If the queue is full, remove the stale queued chunk and replace it.
        """
        if candidate_queue_id not in self.image_object_detection.frame_queue_manager:
            self.image_object_detection.frame_queue_manager[candidate_queue_id] = Queue()#maxsize=3
        try:
            self.image_object_detection.frame_queue_manager[candidate_queue_id].put(payload, timeout=timeout)
            # logging.info("i just inserted frames into the queue for candidate  {0}".format(candidate_queue_id))
            return True
        except Full:
            logging.warning("Frame queue for {0} is full; attempting to replace stale payload with latest payload.".format(candidate_queue_id))
            pass

        # Queue is full: drop the old queued item
        try:
            old_item =  self.image_object_detection.frame_queue_manager[candidate_queue_id].get_nowait()
            # optional: if you use task_done semantics elsewhere, call task_done here
            # self.frame_queue.task_done()
        except Empty:
            logging.warning("Frame queue for {0} was full but is now empty; failed to replace payload.".format(candidate_queue_id))
            old_item = None

        # Try again to insert the latest chunk
        try:
            self.image_object_detection.frame_queue_manager[candidate_queue_id].put_nowait(payload)
            logging.debug("Replaced stale frame payload with latest payload.")
            return True
        except Full:
            logging.warning("Could not enqueue latest frame payload for {0}; dropping it.".format(candidate_queue_id))
            return False   
        