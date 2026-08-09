import logging
from queue import Queue,Empty
import threading
import time
import torch
import os;
import traceback
import callbacks
from collections import Counter
# This module is imported as video_cartoonizer.VideoMetricProcessor, so its own
# directory isn't on sys.path for the bare sibling import below — add it.
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from metric_post_policy import should_post_metrics

class VideoMetricAnalytics:
    def __init__(self, AttentionTracking,EmotionDetection, ImageDetection,stop_signal,num_workers=4,source="real_time"):
        self.AttentionTracking = AttentionTracking
        self.EmotionDetection = EmotionDetection
        self.Imagedetection = ImageDetection
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.num_workers = num_workers
        self.source = source
        self.work_queue = Queue(maxsize=10)
        self.workers = []
        self.worker_loop_t = None
        self.running = False
        self.hasreceivedjob = False
        # First overlay post of a run replaces the pod's stored overlay file
        # (reset), later ones append. Reset per VideoMetricAnalytics instance
        # == per post-hoc run, since server_posthoc builds a fresh instance.
        self._overlays_posted = False
        self.STOP = stop_signal  # sentinel
        


    def start(self):
        self.running = True
        self.hasreceivedjob = False

        # for _ in range(self.num_workers):
        #     t = threading.Thread(target=self.worker_loop, daemon=True)
        #     t.start()
        #     self.workers.append(t)
        self.worker_loop_t = threading.Thread(target=self.worker_loop, daemon=True)
        self.worker_loop_t.start()

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
            # Idle briefly between rounds — with skip-on-empty below, a round
            # over all-empty queues completes instantly and would hot-spin.
            time.sleep(0.05)
            candidate_turn = 0
            candidate_unique_ids = list(self.Imagedetection.accumulator_queue_manager.keys())
            len_candidate_unique_ids = len(candidate_unique_ids)

            if len_candidate_unique_ids != 0:
                self.hasreceivedjob = True

            while candidate_turn < len_candidate_unique_ids:
                # The reactor thread evicts a pod's queue on disconnect; the
                # key snapshot above may be stale, so tolerate a missing key.
                candidate_queue = self.Imagedetection.accumulator_queue_manager.get(candidate_unique_ids[candidate_turn])
                if candidate_queue is None:
                    candidate_turn += 1
                    continue
                try:
                    payload = candidate_queue.get_nowait() #get(timeout=0.25)

                except Empty:
                    # Advance past an empty queue instead of retrying it —
                    # same starvation bug as the image-detection scheduler:
                    # live sessions never send last_batch, so dead sessions'
                    # empty queues would otherwise pin the round-robin forever.
                    candidate_turn += 1
                    continue
                
                self.work_queue.put(payload) 

                auth_key,_,_,_,last_batch = payload

                if last_batch:
                    self.Imagedetection.accumulator_queue_manager.pop(auth_key,None)
                    break

                # self.worker(self.Imagedetection.accumulator_queue_manager[candidate_unique_ids[candidate_turn]],candidate_unique_ids[candidate_turn])
                # logging.info("proceesed emotion and attention work for client {0} of {1} with key {2} ".format(candidate_turn+1,len_candidate_unique_ids,candidate_unique_ids[candidate_turn]))
                candidate_turn += 1

                # if the last candiate have been scheduled, then break so that a fresh candiadates_id is fetched
                # possible a new candiate may have added its queue to the elf.frame_queue_manager
                if candidate_turn == len_candidate_unique_ids:
                    break

            if  self.source != "real_time" and self.hasreceivedjob and  len(self.Imagedetection.accumulator_queue_manager) == 0:
                logging.info("finished video metric procesaor thread scheduler") 
                break #self.stop() 
                  

    def worker_loop(self):
        while self.running:
            try:
                payload = self.work_queue.get(timeout=0.05)
            except Empty:
                # for posthoc processing use this to exit the thread
                if  self.source != "real_time" and self.hasreceivedjob and  len(self.Imagedetection.accumulator_queue_manager) == 0:
                    self.stop()
                    break
                continue
            
            logging.info("Inside Videometricprocesor: just read from worker queue") 
            # worker_thread = threading.Thread(target=self.worker,args=(payload), daemon=True)
            # worker_thread.start()      
            self.worker(payload)

    def worker(self, payload, post_always=False):
        # post_always replaces the old worker_posthoc fork: that method was a
        # near-verbatim copy whose only difference was forcing can_post=True.
        auth_key,all_frames,accumulator,batch_track,last_batch = payload
        processing_timer = time.monotonic()
        torch.cuda.synchronize()
        t1 = time.time()
        video_metrics, overlay_records = self.compute_videoMetrics(all_frames,accumulator,batch_track)
        torch.cuda.synchronize()
        t2 = time.time()
        logging.info(f"Inside VideoMetricProcessor: procesing attention and emotion dectection took {t2 - t1:.6f}s for {auth_key}")

        logging.info("Alloc {0}: after Attention and emotion detection for batch {1}".format((torch.cuda.memory_allocated() / 1024**2), batch_track))
        logging.info("reserved {0}: after Attention and emotion detection for batch {1}".format((torch.cuda.memory_reserved() / 1024**2), batch_track))

        can_post = should_post_metrics(video_metrics, self.source, post_always)
        logging.info("insert {0} into DB for batch {1} and {2}".format(video_metrics,batch_track,can_post))

        if can_post:

            success = callbacks.post_video_metrics(auth_key, video_metrics)

            processing_time = time.monotonic() - processing_timer
            if success:
                logging.info( f"Video processing results posted successfully for client {auth_key} (Processing time: {processing_time})")

        if overlay_records:
            callbacks.post_gaze_overlays(auth_key, overlay_records,
                                         reset=not self._overlays_posted)
            self._overlays_posted = True

    def compute_videoMetrics(self,frames,face_object_detected,batch_track=None):
        video_metrics = {}
        # Overlay geometry (head boxes, gaze points, focused-object boxes) so
        # the dashboard can draw the gaze model's output on top of the video.
        # Post-hoc only: the live path stays lean. Coordinates are normalized
        # to [0,1] so the frontend can scale to any rendered size.
        overlay_records = []
        try:
            for person_id, persons_detail in face_object_detected['head'].items():
                # with attention_emotion_det_lock:
                torch.cuda.synchronize()
                t1 = time.time()
                val_imgs, val_faces, val_head_channels, headboxes, imsizes, frame_ids, _ = self.AttentionTracking.get_batched_facial_data(persons_detail,frames)
                val_gaze_heatmap_preds, val_attmaps, val_inout_preds = self.AttentionTracking.compute_gaze_direction(val_imgs, val_faces, val_head_channels)
                # torch.cuda.synchronize()
                # t2 = time.time()
                # logging.info(f"Inside VideoMetricProcessor: batching and gaze detection took {t2 - t1:.6f}s for {len(val_gaze_heatmap_preds)} heads")
                for index in range(len(val_gaze_heatmap_preds)): 
                    pred_attention_level = 0
                    pred_object_focused_on = "Nothing"
                    closest_object_index = None
                    overlay_obj_box = None
                    frame_index,person_alias,h_bbox,time_stamp = persons_detail[index]
                    
                    #guarding code
                    if frame_index != int(frame_ids[index]):
                        logging.Info("in File VideoMetricAnalytics: Persons data from face detection and gaze detections messed up, please review...")
                        return None
                    frame_raw = frames[frame_index]

                    # with attention_emotion_det_lock:
                    torch.cuda.synchronize()
                    t1 = time.time()
                    pred_emotion = self.EmotionDetection.predict_facial_emotion_for_single_participant(frames[frame_index], h_bbox,person_alias,frame_index,self.Imagedetection.crop_face_from_frame_with_bbox)
                    gaze_x, gaze_y = self.AttentionTracking.get_gaze_direction_point(val_gaze_heatmap_preds[index], val_inout_preds[index], imsizes[index])
                    # torch.cuda.synchronize()
                    # t2 = time.time()
                    # logging.info(f"Inside VideoMetricProcessor: emotion and gaze point estimation  took {t2 - t1:.6f}s")
                
                    if gaze_x is not  None or gaze_y is not None:
                        other_objects_in_frame = face_object_detected['other_objects'][frame_index]
                        frame_width, frame_height = imsizes[index]
                        # logging.info("For person_id: {0}, frame_index: {1}, predicted emotion is {2}, gaze point is ({3},{4}), other objects in frame length {5} frame_width: {6}, frame_height: {7}, head bbox: {8}".format(person_id, frame_index, pred_emotion, gaze_x, gaze_y, len(other_objects_in_frame), frame_width, frame_height, h_bbox))
                        # t1 = time.time()
                        closest_object_index = self.AttentionTracking.find_closest_object_of_focus(h_bbox,(gaze_x, gaze_y), person_id,other_objects_in_frame,frame_width, frame_height,expand_margin=10)
                        # t2 = time.time()
                        # logging.info(f"Inside VideoMetricProcessor: object of focus took {t2 - t1:.6f}s")
                        if closest_object_index is not None:
                            object_class_id,object_class_name,object_id,oo_bbox, t_stamp = other_objects_in_frame[closest_object_index]
                            overlay_obj_box = oo_bbox
                            #if head gaze is focused on other object
                            pred_attention_level = self.AttentionTracking.track_person_level_of_attention(object_class_id,person_id)
                            pred_object_focused_on = object_class_name
                            # #7 mutual gaze: a recognized head target carries the
                            # looked-at person's alias in object_class_name (head
                            # class == 1). Tag it as person:<alias> so the UI can
                            # build a who-looks-at-whom network. Config-gated.
                            try:
                                import config as _cf
                                if _cf.person_of_focus() and object_class_id == 1 \
                                        and object_class_name and str(object_class_name) != 'head':
                                    pred_object_focused_on = "person:" + str(object_class_name)
                            except Exception:
                                pass
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
                    
                    if self.source != "real_time":
                        try:
                            # imsizes/bbox values arrive as torch tensors from
                            # the DataLoader collation — cast to float before
                            # arithmetic (round(tensor) raises TypeError).
                            f_w = float(imsizes[index][0])
                            f_h = float(imsizes[index][1])
                            norm_box = lambda b, f_w=f_w, f_h=f_h: [round(float(b[0])/f_w,4), round(float(b[1])/f_h,4), round(float(b[2])/f_w,4), round(float(b[3])/f_h,4)]
                            overlay_records.append({
                                't': float(time_stamp),
                                'p': str(person_alias),
                                'head': norm_box(h_bbox),
                                'gaze': [round(float(gaze_x)/f_w,4), round(float(gaze_y)/f_h,4)]
                                        if gaze_x is not None and gaze_y is not None else None,
                                'obj': norm_box(overlay_obj_box) if overlay_obj_box is not None else None,
                                'label': str(pred_object_focused_on) if pred_object_focused_on != "Nothing" else None,
                            })
                        except Exception:
                            # Overlay capture must never break metric
                            # computation, but a silent pass hid a per-record
                            # TypeError for an entire run — log the first one.
                            if not getattr(self, '_overlay_warned', False):
                                self._overlay_warned = True
                                logging.exception("gaze overlay capture failed (first occurrence; suppressing further)")

                    if person_id not in video_metrics:
                        video_metrics[person_id] = [[time_stamp,pred_emotion,pred_attention_level,pred_object_focused_on]]
                    else:
                        video_metrics[person_id].append([time_stamp,pred_emotion,pred_attention_level,pred_object_focused_on])
                
                # logging.info("Bfeore Aggregate {0} into DB for batch {1}".format(video_metrics,batch_track))
                #aggregate data in same time stamp
                for person_id, persons_detail in video_metrics.items():
                    data = self.aggregate_all_metrics_in_same_timestamp(persons_detail)
                    video_metrics[person_id] = data
        except Exception:
            error_str = traceback.format_exc()
            logging.info("Error in computing video metrics: {0}".format(error_str))
        
        return video_metrics, overlay_records

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
                    total_attention_level = int(sum(attention_level)/len(attention_level)) if len(attention_level) > 0 else 0
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
            total_attention_level = int(sum(attention_level)/len(attention_level)) if len(attention_level) > 0 else 0
            data.append([old_time_stamp, most_common_emotion, total_attention_level, most_common_object])
        return data 