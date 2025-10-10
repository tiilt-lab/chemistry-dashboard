import logging

class VideoMetricAnalytics:
    def __init__(self, AttentionTracking,EmotionDetection, ImageDection):
        self.AttentionTracking = AttentionTracking
        self.EmotionDetection = EmotionDetection
        self.ImageDection = ImageDection

    def compute_videoMetrics(self,frames,face_object_detected):
        video_metrics = {}
        for person_id, persons_detail in face_object_detected['head'].items():
            val_img, val_face, val_head_channel, headbox, imsize, frame_id, _ = self.AttentionTracking.get_batched_facial_data(persons_detail,frames)

            val_gaze_heatmap_pred, val_attmap, val_inout_pred = self.AttentionTracking.compute_gaze_direction(val_img, val_face, val_head_channel)
            for index in range(len(val_gaze_heatmap_pred)): 
                pred_attention_level = 0
                pred_object_focused_on = "Nothing"
                frame_index,person_alias,bbox,time_stamp = persons_detail[index]
                
                #guarding code
                if frame_index != int(frame_id[index]):
                    logging.Info("in File VideoMetricAnalytics: Persons data from face detection and gaze detections messed up, please review...")
                    return None
                
                pred_emotion = self.EmotionDetection.predict_facial_emotion_for_single_participant(frames[frame_index], bbox,self.ImageDection.crop_face_from_fame_with_bbox)
                
                gaze_x, gaze_y = self.AttentionTracking.get_gaze_direction_point(val_gaze_heatmap_pred[index], val_inout_pred[index], imsize[index])
                if gaze_x is not  None or gaze_y is not None:
                    other_objects_in_frame = face_object_detected['other_objects'][frame_index]
                    closest_object_index = self.AttentionTracking.find_closest_object_of_focus((gaze_x, gaze_y), person_id,other_objects_in_frame)
                    
                    if closest_object_index is not None:
                        object_class_id,object_class_name,object_id,bbox, t_stamp = other_objects_in_frame[closest_object_index]
                        #if head gaze is focused on other object
                        pred_attention_level = self.AttentionTracking.track_person_level_of_attention(object_class_id,person_id)
                        pred_object_focused_on = object_class_name
                    else:
                        print("no closer object: ")
                        #the gaze is not focused on any object detected 
                        pred_attention_level = self.AttentionTracking.track_person_level_of_attention(None,person_id,action="N")
                else:
                    pred_attention_level = self.AttentionTracking.track_person_level_of_attention(None,person_id,action="N")
                
                
                if person_id not in video_metrics:
                    video_metrics[person_id] = [[time_stamp,pred_emotion,pred_attention_level,pred_object_focused_on]]
                else:
                    video_metrics[person_id].append([time_stamp,pred_emotion,pred_attention_level,pred_object_focused_on])   

        return video_metrics