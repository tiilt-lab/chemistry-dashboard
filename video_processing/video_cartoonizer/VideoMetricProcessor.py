import logging
from queue import Empty
import threading
import time
import cv2
import os;
import traceback
import callbacks
from collections import Counter
from yolo_head.utils.datasets import LoadImageDataset
from yolo_head.utils.general import scale_coords
from ultralytics.engine.results import Results

class VideoMetricAnalytics:
    def __init__(self, AttentionTracking,EmotionDetection, ImageDetection):
        self.AttentionTracking = AttentionTracking
        self.EmotionDetection = EmotionDetection
        self.Imagedetection = ImageDetection
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.STOP = object()  # sentinel


    def start(self):
        self.running = True
        self.attention_emotion_detection_thread = threading.Thread(target=self.scheduler, name="attention_emotion_detection-thread")
        self.attention_emotion_detection_thread.daemon = True
        self.attention_emotion_detection_thread.start()

    def stop(self):
        self.running = False
        logging.info("Stopping video metric analytics thread...")

    # this schedule will go through each candiate's queue added to frame_queue_manager
    # and get the added job. This goes tune by turn to ensure each candiate job is process round robbingly
    # regardless of when they join. This solve the issue of using one queue for all candiadate, which result to
    # candidates that join later having to wait longer till it gets to their turn
    def scheduler(self):
        while self.running:
            candidate_turn = 0
            candidate_unique_ids = list(self.Imagedetection.accumulator_queue_manager.keys())
            len_candidate_unique_ids = len(candidate_unique_ids)

            if len_candidate_unique_ids == 0:
                time.sleep(0.05)
                continue

            while candidate_turn < len_candidate_unique_ids:
                # logging.info("about to start processing  emotion and attention  work for client {0} of {1} with key {2} ".format(candidate_turn,len_candidate_unique_ids,candidate_unique_ids[candidate_turn]))
                self.worker(self.Imagedetection.accumulator_queue_manager[candidate_unique_ids[candidate_turn]],candidate_unique_ids[candidate_turn])
                logging.info("proceesed emotion and attention work for client {0} of {1} with key {2} ".format(candidate_turn+1,len_candidate_unique_ids,candidate_unique_ids[candidate_turn]))
                candidate_turn += 1

                # if the last candiate have been scheduled, then break so that a fresh candiadates_id is fetched
                # possible a new candiate may have added its queue to the elf.frame_queue_manager
                if candidate_turn == len_candidate_unique_ids:
                    break

    def worker(self,candidate_queue,candidate_queue_id):
        try:
            # block briefly to avoid CPU spin; adjust timeout for latency needs
            payload = candidate_queue.get_nowait() #get(timeout=0.25)
        except Empty:
            logging.debug("Video metric analytics thread waiting for data...")
            return

        if payload is self.STOP:
            logging.info("Received stop signal for video metric analytics thread.")
            return  
          
        logging.info("i just read from queue accumulator for client {0}".format(candidate_queue_id))
        auth_key,all_frames,accumulator,batch_track = payload
        processing_timer = time.monotonic()
        video_metrics = self.compute_videoMetrics(all_frames,accumulator)
        logging.info("insert {0} into DB for batch {1}".format(video_metrics,batch_track))
        if video_metrics: 
            
            success = callbacks.post_video_metrics(auth_key, video_metrics)

            processing_time = time.monotonic() - processing_timer
            if success:
                logging.info( f"Video processing results posted successfully for client {auth_key} (Processing time: {processing_time})")



    def compute_videoMetrics(self,frames,face_object_detected):
        video_metrics = {}
        try:
            for person_id, persons_detail in face_object_detected['head'].items():
                # with attention_emotion_det_lock:
                val_imgs, val_faces, val_head_channels, headboxes, imsizes, frame_ids, _ = self.AttentionTracking.get_batched_facial_data(persons_detail,frames)
                val_gaze_heatmap_preds, val_attmaps, val_inout_preds = self.AttentionTracking.compute_gaze_direction(val_imgs, val_faces, val_head_channels)
                for index in range(len(val_gaze_heatmap_preds)): 
                    pred_attention_level = 0
                    pred_object_focused_on = "Nothing"
                    closest_object_index = None
                    frame_index,person_alias,h_bbox,time_stamp = persons_detail[index]
                    
                    #guarding code
                    if frame_index != int(frame_ids[index]):
                        logging.Info("in File VideoMetricAnalytics: Persons data from face detection and gaze detections messed up, please review...")
                        return None
                    frame_raw = frames[frame_index]

                    # with attention_emotion_det_lock:
                    pred_emotion = self.EmotionDetection.predict_facial_emotion_for_single_participant(frames[frame_index], h_bbox,person_alias,frame_index,self.Imagedetection.crop_face_from_fame_with_bbox)
                    gaze_x, gaze_y = self.AttentionTracking.get_gaze_direction_point(val_gaze_heatmap_preds[index], val_inout_preds[index], imsizes[index])
                    
                    if gaze_x is not  None or gaze_y is not None:
                        other_objects_in_frame = face_object_detected['other_objects'][frame_index]
                        frame_width, frame_height = imsizes[index]
                        # logging.info("For person_id: {0}, frame_index: {1}, predicted emotion is {2}, gaze point is ({3},{4}), other objects in frame length {5} frame_width: {6}, frame_height: {7}, head bbox: {8}".format(person_id, frame_index, pred_emotion, gaze_x, gaze_y, len(other_objects_in_frame), frame_width, frame_height, h_bbox))
                        closest_object_index = self.AttentionTracking.find_closest_object_of_focus(h_bbox,(gaze_x, gaze_y), person_id,other_objects_in_frame,frame_width, frame_height,expand_margin=10)
                        if closest_object_index is not None:
                            object_class_id,object_class_name,object_id,oo_bbox, t_stamp = other_objects_in_frame[closest_object_index]
                            #if head gaze is focused on other object
                            pred_attention_level = self.AttentionTracking.track_person_level_of_attention(object_class_id,person_id)
                            pred_object_focused_on = object_class_name
                            # logging.info("For person_id: {0}, frame_index: {1}, predicted emotion is {2}, predicted attention level is {3} and predicted object focused on is {4}".format(person_id, frame_index, pred_emotion, pred_attention_level, pred_object_focused_on))
                            # frame_raw = cv2.circle(frame_raw, (gaze_x, gaze_y), int(frame_height/50.0), (255, 0, 0), 2) 
                            # cv2.arrowedLine(frame_raw,(int((h_bbox[0]+h_bbox[2])/2),int((h_bbox[1]+h_bbox[3])/2)),(gaze_x, gaze_y), (230,253,11),thickness=3)
                            # cv2.imwrite(os.path.join(self.base_path,'annotated_frames', str(frame_index)+'.jpg'), frame_raw) 
                        else:
                            # print("no closer object: ")
                            #the gaze is not focused on any object detected 
                            pred_attention_level = self.AttentionTracking.track_person_level_of_attention(None,person_id,action="N")
                    else:
                        pred_attention_level = self.AttentionTracking.track_person_level_of_attention(None,person_id,action="N")
                    
                    if person_id not in video_metrics:
                        video_metrics[person_id] = [[time_stamp,pred_emotion,pred_attention_level,pred_object_focused_on]]
                    else:
                        video_metrics[person_id].append([time_stamp,pred_emotion,pred_attention_level,pred_object_focused_on])   

                #aggregate data in same time stamp
                for person_id, persons_detail in video_metrics.items():
                    data = self.aggregate_all_metrics_in_same_timestamp(persons_detail)
                    video_metrics[person_id] = data
        except Exception as e:
            error_str = traceback.format_exc()
            logging.info("Error in computing video metrics: {0}".format(error_str))
        
        return video_metrics
    
    def aggregate_all_metrics_in_same_timestamp(self,persons_detail):
        data = []
        facial_emotion = []
        object_on_focus = []
        attention_level = []
        len_detail = len(persons_detail)
        if len_detail > 0:
            old_time_stamp, pred_emotion, pred_attention_level, pred_object_focused_on = persons_detail[0]
            facial_emotion.append(pred_emotion)
            object_on_focus.append(pred_object_focused_on)
            attention_level.append(pred_attention_level)
            for index in range(1,len_detail):
                time_stamp, pred_emotion, pred_attention_level, pred_object_focused_on = persons_detail[index]
                if old_time_stamp == time_stamp:
                    facial_emotion.append(pred_emotion)
                    object_on_focus.append(pred_object_focused_on)
                    attention_level.append(pred_attention_level)
                else:
                    most_common_emotion = Counter(facial_emotion).most_common(1)[0][0] if facial_emotion else 'neutral'
                    most_common_object = Counter(object_on_focus).most_common(1)[0][0] if object_on_focus else 'nothing'
                    total_attention_level = sum(attention_level)
                    data.append([old_time_stamp, most_common_emotion, total_attention_level, most_common_object])

                    facial_emotion = []
                    object_on_focus = []
                    attention_level = []
                    old_time_stamp, pred_emotion, pred_attention_level, pred_object_focused_on = persons_detail[index]
                    facial_emotion.append(pred_emotion)
                    object_on_focus.append(pred_object_focused_on)
                    attention_level.append(pred_attention_level)
                    
            most_common_emotion = Counter(facial_emotion).most_common(1)[0][0] if facial_emotion else 'neutral'
            most_common_object = Counter(object_on_focus).most_common(1)[0][0] if object_on_focus else 'nothing'
            total_attention_level = sum(attention_level)
            data.append([old_time_stamp, most_common_emotion, total_attention_level, most_common_object])
        return data 