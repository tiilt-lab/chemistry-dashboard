import json
import os

import cv2
import torch
from torchvision.transforms import transforms

from .models.resmasking import resmasking_dropout1
from .utils.utils import ensure_gray, ensure_color

from .emotions_dlib import EmotionsDlib

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

    def predict_facial_emotion(self,image,x, y, w, h):
        try:
            gray = ensure_gray(image)
            # cv2.rectangle(image, (x, y), (x + w, y + h), (179, 255, 179), 2)
            face = gray[y : y + h, x : x + w]
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
        except Exception as e:
            logging.info('exception occured while predicting facial emotion: {0}'.format(e))
        return emo_label  

class EmotionDetectionModel:
    def __init__(self):
        self.base_path = os.path.dirname(os.path.abspath(__file__))

    def load_model(self):
        self.emotion_estimator = EmotionsDlib(
                                        file_emotion_model=os.path.join( self.base_path,'facial_expression_model/model_emotion_pls=30_fullfeatures=False.joblib'), 
                                        file_frontalization_model=os.path.join( self.base_path,'facial_expression_model/model_frontalization.npy')
                                        )

    def predict_facial_emotion(self,landmarks_object):
        
        try:
            dict_emotions = self.emotion_estimator.get_emotions( landmarks_object )
            emotion_name = dict_emotions['emotions']['name'] 
        except Exception as e:
            logging.info('exception occured while predicting facial emotion: {0}'.format(e))
        return emotion_name        