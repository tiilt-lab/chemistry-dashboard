import logging
import os
import torch
import numpy as np
import cv2
from torchvision import datasets, transforms
from scipy.spatial import distance

from .models.model import ModelSpatial
from .utils.evaluation import argmax_pts
from .utils.dataset import AttentionFlow
from .utils.intersection_point import find_best_gaze_target_V1, find_best_gaze_target_V2

class AttentionDetection:
    def __init__(self):
        self.device = torch.device('cuda', 0)
        self.out_threshold = 200
        self.input_resolution = 224
        self.output_resolution = 64
        self.model = None
        self.object_of_interest = [0,1,63,64,66,73]
        self.person_attention_focus_count = {}

    def init_model(self,batch_size):
        self.batch_size = batch_size
        base_path = os.path.dirname(os.path.abspath(__file__))
        model_weights = os.path.join(base_path,'pretrained-models/model_gazefollow.pt')
        self.model = ModelSpatial()
        self.model.cuda().to(self.device)
        model_dict = self.model.state_dict()
        pretrained_dict = torch.load(model_weights)
        pretrained_dict = pretrained_dict['model']
        model_dict.update(pretrained_dict)
        self.model.load_state_dict(model_dict)
        self.model.train(False)
        self.transform = self._get_transform()


    def _get_transform(self):
        transform_list = []
        transform_list.append(transforms.Resize((self.input_resolution, self.input_resolution)))
        transform_list.append(transforms.ToTensor())
        transform_list.append(transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]))
        return transforms.Compose(transform_list)           
    

    def find_closest_object_of_focus(self,head_bbox,gaze_point,person_id, other_objects_on_frame, frame_width, frame_height, expand_margin=None):
        object_of_index = None
        try:
            object_of_index = find_best_gaze_target_V1(head_bbox, gaze_point, other_objects_on_frame, frame_width, frame_height, expand_margin)
        except Exception as e:
            logging.error("Error occurred while finding closest object of focus: {0}".format(e))

        #if the other object is same same as the person, return None
        if object_of_index is not None and person_id == other_objects_on_frame[object_of_index][2] :
            return None
        
        return object_of_index

    def track_person_level_of_attention(self, object_focused_on,person_id,action="Y"):
        # this means the attention level was neither distracted or focus so just return the last count
        if action == "N":
            if person_id in self.person_attention_focus_count:
                return self.person_attention_focus_count[person_id]
            else:
                return 0
        else:
            if  object_focused_on in self.object_of_interest:
                #increment the count if its within object of focus
                if person_id not in self.person_attention_focus_count:
                    self.person_attention_focus_count[person_id] = 1  
                else:
                    self.person_attention_focus_count[person_id] = self.person_attention_focus_count[person_id] +1
            else:
                #decrement the count
                if person_id not in self.person_attention_focus_count:
                    self.person_attention_focus_count[person_id] = 0  
                else:    
                    self.person_attention_focus_count[person_id] = self.person_attention_focus_count[person_id] - 1 if self.person_attention_focus_count[person_id] - 1 > 0 else 0
        
            return self.person_attention_focus_count[person_id]

    
    def get_batched_facial_data(self,person_detail,frames):
        # Prepare data
        val_dataset = AttentionFlow(frames, person_detail,self.transform, input_size=self.input_resolution, output_size=self.output_resolution)
        val_loader = torch.utils.data.DataLoader(dataset=val_dataset,
                                            batch_size=self.batch_size,
                                            shuffle=False,
                                            num_workers=0)
    
    
        val_img, val_face, val_head_channel, headbox, imsize, frame_id, time_stamp = next(iter(val_loader))

        return val_img, val_face, val_head_channel, headbox, imsize, frame_id, time_stamp
    
    def compute_gaze_direction(self,val_img, val_face, val_head_channel):
        
        with torch.no_grad():
            val_images = val_img.cuda().to(self.device)
            val_head = val_head_channel.cuda().to(self.device)
            val_faces = val_face.cuda().to(self.device)
            val_gaze_heatmap_pred, val_attmap, val_inout_pred = self.model(val_images, val_head, val_faces)
        
        return val_gaze_heatmap_pred, val_attmap, val_inout_pred
    
    def get_gaze_direction_point(self,val_gaze_heatmap_pred, val_inout_pred, imsize):

        with torch.no_grad():
            raw_hm = val_gaze_heatmap_pred.cpu().detach().numpy() * 255
            raw_hm = raw_hm.squeeze()
            inout = val_inout_pred.cpu().detach().numpy()
            inout = 1 / (1 + np.exp(-inout))
            inout = (1 - inout) * 255
            width, height = int(imsize[0]), int(imsize[1])
            if inout < self.out_threshold: # in-frame gaze
                pred_x, pred_y = argmax_pts(raw_hm)
                norm_p = [pred_x/self.output_resolution, pred_y/self.output_resolution]
                return int(norm_p[0]*width), int(norm_p[1]*height)
            else:
                return None,None   