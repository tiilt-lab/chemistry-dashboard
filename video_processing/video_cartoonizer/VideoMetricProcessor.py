import logging
import cv2
import os
from collections import Counter

class VideoMetricAnalytics:
    def __init__(self, AttentionTracking,EmotionDetection, ImageDection):
        self.AttentionTracking = AttentionTracking
        self.EmotionDetection = EmotionDetection
        self.ImageDection = ImageDection
        self.base_path = os.path.dirname(os.path.abspath(__file__))

    def compute_videoMetrics(self,frames,face_object_detected):
        video_metrics = {}
        for person_id, persons_detail in face_object_detected['head'].items():
            val_imgs, val_faces, val_head_channels, headboxes, imsizes, frame_ids, _ = self.AttentionTracking.get_batched_facial_data(persons_detail,frames)
            val_gaze_heatmap_preds, val_attmaps, val_inout_preds = self.AttentionTracking.compute_gaze_direction(val_imgs, val_faces, val_head_channels)
            for index in range(len(val_gaze_heatmap_preds)): 
                pred_attention_level = 0
                pred_object_focused_on = "Nothing"
                frame_index,person_alias,h_bbox,time_stamp = persons_detail[index]
                
                #guarding code
                if frame_index != int(frame_ids[index]):
                    logging.Info("in File VideoMetricAnalytics: Persons data from face detection and gaze detections messed up, please review...")
                    return None
                frame_raw = frames[frame_index]
                pred_emotion = self.EmotionDetection.predict_facial_emotion_for_single_participant(frames[frame_index], h_bbox,person_alias,frame_index,self.ImageDection.crop_face_from_fame_with_bbox)
                gaze_x, gaze_y = self.AttentionTracking.get_gaze_direction_point(val_gaze_heatmap_preds[index], val_inout_preds[index], imsizes[index])
                if gaze_x is not  None or gaze_y is not None:
                    other_objects_in_frame = face_object_detected['other_objects'][frame_index]
                    frame_width, frame_height = imsizes[index]
                    closest_object_index = self.AttentionTracking.find_closest_object_of_focus(h_bbox,(gaze_x, gaze_y), person_id,other_objects_in_frame,frame_width, frame_height,expand_margin=10)
                    if closest_object_index is not None:
                        object_class_id,object_class_name,object_id,oo_bbox, t_stamp = other_objects_in_frame[closest_object_index]
                        #if head gaze is focused on other object
                        pred_attention_level = self.AttentionTracking.track_person_level_of_attention(object_class_id,person_id)
                        pred_object_focused_on = object_class_name
                        logging.info("For person_id: {0}, frame_index: {1}, predicted emotion is {2}, predicted attention level is {3} and predicted object focused on is {4}".format(person_id, frame_index, pred_emotion, pred_attention_level, pred_object_focused_on))
                        frame_raw = cv2.circle(frame_raw, (gaze_x, gaze_y), int(frame_height/50.0), (255, 0, 0), 2) 
                        cv2.arrowedLine(frame_raw,(int((h_bbox[0]+h_bbox[2])/2),int((h_bbox[1]+h_bbox[3])/2)),(gaze_x, gaze_y), (230,253,11),thickness=3)
                        # plot_one_box([int(other_objects[object_index][3]),int(other_objects[object_index][4]),int(other_objects[object_index][5]),int(other_objects[object_index][6])], frame_raw, label=str(other_objects[object_index][1]), color=(0,0,0), line_thickness=3)
                        # cv2.putText(frame_raw, str(other_objects[object_index][2]), (int(other_objects[object_index][5]), int(other_objects[object_index][6]) + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.9,(0,0,255) , 2)
                        cv2.imwrite(os.path.join(self.base_path,'annotated_frames', str(frame_index)+'.jpg'), frame_raw) 
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
            data.append([old_time_stamp, facial_emotion, attention_level, object_on_focus])
        return data 