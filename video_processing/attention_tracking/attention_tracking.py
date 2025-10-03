import os
import torch
import numpy as np
import cv2
from torchvision import datasets, transforms
from scipy.spatial import distance

from .models.model import ModelSpatial
from .utils.evaluation import argmax_pts
from .utils.dataset import AttentionFlow


class AttentionDetection:
    def __init__(self):
        self.device = torch.device('cuda', 0)
        self.out_threshold = 200
        self.input_resolution = 224
        self.output_resolution = 64
        self.model = None

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

    def set_persistent_variables(self,object_of_interest,persons_attention_track,person_object_focus_track,shared_attention_track,object_by_class_track,person_attention_focus_count):
        self.object_of_interest = object_of_interest
        self.persons_attention_track = persons_attention_track
        self.person_object_focus_track = person_object_focus_track
        self.shared_attention_track = shared_attention_track
        self.object_by_class_track = object_by_class_track
        self.person_attention_focus_count = person_attention_focus_count


    def _get_transform(self):
        transform_list = []
        transform_list.append(transforms.Resize((self.input_resolution, self.input_resolution)))
        transform_list.append(transforms.ToTensor())
        transform_list.append(transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]))
        return transforms.Compose(transform_list)           
    

    def find_closest_object_of_focus(self,gaze_point, other_objects_on_frame):
        min_distance = float("inf")
        object_of_index = None
        for index, objects in enumerate(other_objects_on_frame):
            _,_,_,bbox, _ = objects
            x1,y1,x2,y2 = bbox
            object_centroid = (int((x1+x2)/2),int((y1+y2)/2))
            euclid_dist = distance.euclidean(object_centroid,gaze_point)
            if euclid_dist < min_distance:
                min_distance =  euclid_dist
                object_of_index = index
        
        return object_of_index

    def track_person_level_of_attention(self,object_focused_on,person_id, timestamp):
        if  object_focused_on in self.object_of_interest:
            #increment the count if its within object of focus
            self.person_attention_focus_count[person_id] = self.person_attention_focus_count[person_id] +1
            self.persons_attention_track[person_id].append([timestamp,self.person_attention_focus_count[person_id]])
        else:
            #decrement the count
            self.person_attention_focus_count[person_id] = self.person_attention_focus_count[person_id] - 1 if self.person_attention_focus_count[person_id] - 1 > 0 else 0
            self.persons_attention_track[person_id].append([timestamp, self.person_attention_focus_count[person_id]])  
      

    def track_person_freq_of_focus_on_object(self,object_focused_on,person_id,timestamp):
        if  object_focused_on in  self.person_object_focus_track[person_id]:
            last_index =  len(self.person_object_focus_track[person_id][object_focused_on])-1
            new_count = self.person_object_focus_track[person_id][object_focused_on][last_index][1] +1
            self.person_object_focus_track[person_id][object_focused_on].append([timestamp,new_count])
        else:
             self.person_object_focus_track[person_id][object_focused_on] = [[timestamp,1]] 

    def track_shared_attention_on_an_object(self,object_by_id_in_frame,person_id,frame_id,timestamp):
        if object_by_id_in_frame in  self.shared_attention_track:
            self.shared_attention_track[object_by_id_in_frame]["persons"].append(person_id)
            self.shared_attention_track[object_by_id_in_frame]["timestamps"].append(timestamp)
        else:
            self.shared_attention_track[object_by_id_in_frame]={"persons":[person_id], "timestamps":[timestamp]}


        # if  frame_id in  self.shared_attention_track:
        #     if object_by_id_in_frame in  self.shared_attention_track[frame_id]:
        #         self.shared_attention_track[frame_id][object_by_id_in_frame].append(person_id)
        #     else:
        #         self.shared_attention_track[frame_id][object_by_id_in_frame]=[person_id] 
        # else:
        #     self.shared_attention_track[frame_id] = {}
        #     self.shared_attention_track[frame_id][object_by_id_in_frame] = [person_id]   

    def attention_tracking(self,face_object_detected,frames):
        for person_id, person_detail in sorted(face_object_detected['head'].items()):
            
            if person_id not in self.person_attention_focus_count:
                self.person_attention_focus_count[person_id] = 0

            #create the person id field to hold the attention tracking data
            if person_id not in self.persons_attention_track:
                self.persons_attention_track[person_id] = [[0,0]]

            if person_id not in self.person_object_focus_track:
                self.person_object_focus_track[person_id] = {}
            
            # Prepare data
            val_dataset = AttentionFlow(frames, person_detail,self.transform, input_size=self.input_resolution, output_size=self.output_resolution)
            val_loader = torch.utils.data.DataLoader(dataset=val_dataset,
                                                batch_size=self.batch_size,
                                                shuffle=False,
                                                num_workers=0)
        
        
            with torch.no_grad():
                for val_batch, (val_img, val_face, val_head_channel, headbox, imsize, frame_id) in enumerate(val_loader):
                    
                    val_images = val_img.cuda().to(self.device)
                    val_head = val_head_channel.cuda().to(self.device)
                    val_faces = val_face.cuda().to(self.device)
                    val_gaze_heatmap_pred, val_attmap, val_inout_pred = self.model(val_images, val_head, val_faces)
                    
                    for j in range(len(val_gaze_heatmap_pred)):
                        #heatmap modulation
                        raw_hm = val_gaze_heatmap_pred[j].cpu().detach().numpy() * 255
                        raw_hm = raw_hm.squeeze()
                        inout = val_inout_pred[j].cpu().detach().numpy()
                        inout = 1 / (1 + np.exp(-inout))
                        inout = (1 - inout) * 255
                        # print('Frame ',int(frame_id[j]), inout)
                        width, height = int(imsize[j][0]), int(imsize[j][1])
                        x1,y1,x2,y2 = int(headbox[j][0]), int(headbox[j][1]), int(headbox[j][2]), int(headbox[j][3])
                
                        norm_map = cv2.resize(raw_hm,(height, width)) - inout # imresize(raw_hm, (height, width)) - inout
                        
                
                        frame_raw = frames[int(frame_id[j])]#.detach().clone().numpy()
                        
                        
                        if inout < self.out_threshold: # in-frame gaze
                            pred_x, pred_y = argmax_pts(raw_hm)
                            norm_p = [pred_x/self.output_resolution, pred_y/self.output_resolution]
                            
                            # get all other objects in the frame
                            other_objects = face_object_detected['other_objects'][int(frame_id[j])]
                            #find the closest object of focus
                            closest_object_index = self.find_closest_object_of_focus((int(norm_p[0]*width), int(norm_p[1]*height)), other_objects)
                            if closest_object_index is not None:
                                object_class_id,object_class_name,object_id,bbox, time_stamp = other_objects[closest_object_index]
                                #if head gaze is focused on other object
                                if(person_id != object_id):
                                    self.track_person_level_of_attention(object_class_id,person_id,time_stamp)  
                                    self.track_person_freq_of_focus_on_object(object_class_id,person_id,time_stamp)
                                    self.track_shared_attention_on_an_object(object_id,person_id,int(frame_id[j]),time_stamp)
                            else:
                                #the gaze is not focused on any object detected 
                                self.track_person_level_of_attention(-1,person_id,time_stamp)        
                                # self.track_person_freq_of_focus_on_object(-1,person_id,time_stamp)
                                # self.track_shared_attention_on_an_object(-1,person_id,int(frame_id[j]),time_stamp)       
                        else: #out of frame gaze
                            self.track_person_level_of_attention(-1,person_id,time_stamp)        
                            # self.track_person_freq_of_focus_on_object(-1,person_id,time_stamp)
                            # self.track_shared_attention_on_an_object(-1,person_id,int(frame_id[j]),time_stamp)
                            
