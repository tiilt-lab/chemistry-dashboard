import json
import os

import cv2
import torch
from torchvision.transforms import transforms

from .models.resmasking import resmasking_dropout1
from .utils.utils import ensure_gray, ensure_color

from .emotions_dlib import EmotionsDlib
import dlib

import logging

class EmotionDetectionModelV1:
    def __init__(self):
        self.FER_2013_EMO_DICT = {
                                        0: "angry",
                                        1: "disgust",
                                        2: "fear",
                                        3: "happy",
                                        4: "sad",
                                        5: "surprise",
                                        6: "neutral",
                                    }
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.state = torch.load(os.path.join( self.base_path,"checkpoints/Z_resmasking_dropout1_rot30_2019Nov30_13.32"))
        self.transform = transforms.Compose([transforms.ToPILImage(), transforms.ToTensor()])                            
        self.base_path = os.path.dirname(os.path.abspath(__file__))                           
        self.configs = json.load(open(os.path.join( self.base_path,"configs/fer2013_config.json")))
        self.image_size = (self.configs["image_size"], self.configs["image_size"])

    def load_model(self):
        self.model = resmasking_dropout1(in_channels=3, num_classes=7)
        self.model.cuda()
        
        self.model.load_state_dict(self.state["net"])
        self.model.eval()
        print('Emotion model loaded successfully.')

    def predict_facial_emotion(self,image):
        try:
            face = None
            gray = ensure_gray(image)
            face = gray
            face = ensure_color(face)
            face = cv2.resize(face, self.image_size)
            face = self.transform(face).cuda()
            face = torch.unsqueeze(face, dim=0)

            output = torch.squeeze(self.model(face), 0)
            proba = torch.softmax(output, 0)

            emo_proba, emo_idx = torch.max(proba, dim=0)
            emo_idx = emo_idx.item()
            emo_proba = emo_proba.item()

            emo_label = self.FER_2013_EMO_DICT[emo_idx]
            return emo_label  
        except Exception as e:
            logging.info('EmotionDetectionModelV1: exception occured while predicting facial emotion: {0}'.format(e))
       
    
    def set_persistent_variables(self,persons_emotions_detected):
        self.persons_emotions_detected = persons_emotions_detected

    def predict_facial_emotion_for_all_participants(self, frames, faces,crop_face_from_fame_with_bbox):
         for alias, person_detail in faces:
            for face_detail_by_frame in person_detail:
                frame_index,alias,bbox,time_stamp  = face_detail_by_frame 
                try:
                    face = crop_face_from_fame_with_bbox(frames[frame_index],bbox,"xyxy", False, 0.0, False) 
                    
                    emotion_name = self.predict_facial_emotion(face)
                    if alias in self.persons_emotions_detected:
                        self.persons_emotions_detected[alias].append([time_stamp,emotion_name])
                    else:
                        self.persons_emotions_detected[alias] = [[time_stamp,emotion_name]]
                except Exception as e:
                    logging.info('EmotionDetectionModelV1: exception occured while predicting facial emotion for {0} in frame {1} : {2}'.format(alias,frame_index,e))

    def predict_facial_emotion_for_single_participant(self, image, bbox,crop_face_from_fame_with_bbox):
        try:
            face = crop_face_from_fame_with_bbox(image,bbox,"xyxy", False, 0.0, False) 
            
            emotion_name = self.predict_facial_emotion(face)
            return emotion_name
        except Exception as e:
            logging.info('EmotionDetectionModelV1: exception occured while predicting facial emotion for {0} in frame {1} : {2}'.format(alias,frame_index,e))
    
         

class EmotionDetectionModel:
    def __init__(self):
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.batch_size = None
        self.landmarkpredictor = None
        self.persons_emotions_detected = None

    def load_model(self,batch_size,landmarkpredictor):
        self.batch_size = batch_size
        self.landmarkpredictor = landmarkpredictor
        self.emotion_estimator = EmotionsDlib(
                                        file_emotion_model=os.path.join( self.base_path,'facial_expression_model/model_emotion_pls=30_fullfeatures=False.joblib'), 
                                        file_frontalization_model=os.path.join( self.base_path,'facial_expression_model/model_frontalization.npy')
                                        )

    def get_facial_shape(self,img,bbox):
        x1, y1, x2, y2 = bbox
        rect = dlib.rectangle(left=x1, top=y1, right=x2, bottom=y2)
        shape =   self.landmarkpredictor(img, rect)
        return shape
    
    def set_persistent_variables(self,persons_emotions_detected):
        self.persons_emotions_detected = persons_emotions_detected

    def predict_facial_emotion_for_all_participants(self, frames, faces,crop_face_from_fame_with_bbox):
         for alias, person_detail in faces:
            for face_detail_by_frame in person_detail:
                frame_index,alias,bbox,time_stamp  = face_detail_by_frame 
                try:
                    face = crop_face_from_fame_with_bbox(frames[frame_index],bbox,"xyxy", False, 0.0, False) 
                    landmarks_object = self.get_facial_shape(face,bbox)
                    dict_emotions = self.emotion_estimator.get_emotions( landmarks_object )
                    emotion_name = dict_emotions['emotions']['name'] 
                    if alias in self.persons_emotions_detected:
                        self.persons_emotions_detected[alias].append([time_stamp,emotion_name])
                    else:
                        self.persons_emotions_detected[alias] = [[time_stamp,emotion_name]]
                except Exception as e:
                    logging.info('exception occured while predicting facial emotion for {0} in frame {1} : {2}'.format(alias,frame_index,e))
            # return emotion_name      
    
    def predict_facial_emotion(self,landmarks_object):
        
        try:
            dict_emotions = self.emotion_estimator.get_emotions( landmarks_object )
            emotion_name = dict_emotions['emotions']['name'] 
        except Exception as e:
            logging.info('exception occured while predicting facial emotion: {0}'.format(e))
        return emotion_name        