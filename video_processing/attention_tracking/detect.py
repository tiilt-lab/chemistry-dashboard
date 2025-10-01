import argparse
import time
from pathlib import Path
import os
import sys
import cv2
import torch
import torch.backends.cudnn as cudnn
from numpy import random
import os
import numpy as np
import supervision as sv
import face_recognition
from ultralytics.engine.results import Results
sys.path.insert(0,'./yolo_head')
from yolo_head.models.experimental import attempt_load
from yolo_head.utils.datasets import LoadStreams, LoadImages, LoadImageDataset
from yolo_head.utils.general import check_img_size, non_max_suppression, scale_coords
from yolo_head.utils.torch_utils import select_device


class ImageObjectDetection:
    def __init__(self):
        self.imgsz =  640
        self.head_width_threshold = 50
        self.model_1 = None
        self.model_2 = None
        self.stride = None
        self.half = None
        self.device = None
        self.model1_conf_thres = 0.25
        self.model1_iou_thres = 0.45
        self.model2_conf_thres = 0.4
        self.model2_iou_thres = 0.5
        self.agnostic_nms=False
        self.augment=False
        self.classes=None
        self.object_names_V_K = {}
        self.object_names_K_V = {}
        self.tracker = sv.ByteTrack()
    

    def init_model(self,batch_size):
        self.batch_size = batch_size
        base_path = os.path.dirname(os.path.abspath(__file__))
        weight_1 = os.path.join( base_path,'pretrained-models/crowdhuman_yolov5m.pt')

        weight_2 = os.path.join( base_path,'pretrained-models/yolov4-p7.pt')
        self.device = select_device('')
        self.half = self.device.type != 'cpu'  # half precision only supported on CUDA
        # Load model
        self.model_1 = attempt_load(weight_1, map_location=self.device)  # load FP32 model for head and person detection
        self.model_2 = attempt_load(weight_2, map_location=self.device)  # load FP32 model for person and other object detection
        #prep model 1
        self.stride = int(self.model_1.stride.max())  # model stride
        imgsz_1 = check_img_size(self.imgsz, s=self.stride)  # check img_size
        if self.half:
            self.model_1.half()  # to FP16 

        #prep model 2
        stride2 = int(self.model_2.stride.max())  # model stride
        # print(stride2)
        imgsz_2 = check_img_size(self.imgsz, s=stride2)  # check img_size
        if self.half:
            self.model_2.half()  # to FP16   


        # Run inference
        if self.device.type != 'cpu':
            self.model_1(torch.zeros(self.batch_size, 3, imgsz_1, imgsz_1).to(self.device).type_as(next(self.model_1.parameters())))  # run once
    
        # Run inference
            self.model_2(torch.zeros(self.batch_size, 3, imgsz_2, imgsz_2).to(self.device).type_as(next(self.model_2.parameters())))  # run once
        
        # Get names  for pred 1
        names_model_1 = self.model_1.module.names if hasattr(self.model_1, 'module') else self.model_1.names
        # Get names for pred 2
        names_model_2 = self.model_2.module.names if hasattr(self.model_2, 'module') else self.model_2.names
        #change the value of the name in key 1 to the value of name in names_model_1[1]
        names_model_2[1] = names_model_1[1]

        if  isinstance(names_model_2,list):
            for k, v in enumerate(names_model_2):
                self.object_names_V_K[v] =  k 
                self.object_names_K_V[k] =  v
        elif isinstance(names_model_2,dict):
            self.object_names_K_V = names_model_2
            self.object_names_V_K = {v: k for k, v in names_model_2.items()}

    def detection(self,images,batch_track):
        val_dataset = LoadImageDataset(images, batch_track, self.batch_size,img_size=self.imgsz, stride=self.stride)
        dataset = torch.utils.data.DataLoader(dataset=val_dataset,
                                               batch_size=self.batch_size,
                                               shuffle=False,
                                               num_workers=0)
        
        accumulator = {'head':dict(), 'other_objects':dict()}
        all_frames = {}
        for val_batch, (img_index, img, im0s) in enumerate(dataset): #path, img, im0s, vid_cap in dataset:
            # all_frames.extend(im0s)
            # img = torch.from_numpy(img).to(device)
            img = img.to(self.device)
            img = img.half() if self.half else img.float()  # uint8 to fp16/32
            img /= 255.0  # 0 - 255 to 0.0 - 1.0
            if img.ndimension() == 3:
                img = img.unsqueeze(0)

            # Inference
            pred = self.model_1(img, augment=self.augment)[0]
            pred2 = self.model_2(img, augment=self.augment)[0]
            
            # Apply NMS
            pred = non_max_suppression(pred, self.model1_conf_thres, self.model1_iou_thres, classes=self.classes, agnostic=self.agnostic_nms)
            pred2 = non_max_suppression(pred2, self.model2_conf_thres, self.model2_iou_thres, classes=self.classes, agnostic=self.agnostic_nms)
            
            #combine pred and pred 2, filter out all cls 0 (person) detection for pred. keep only head (cls 1) detection 
            # and filter out all cls 1 (bicycle)  detection  pred 2
            combined_pred = [torch.cat((pred[i][pred[i][:,5] >= 1],pred2[i][pred2[i][:,5] != 1])) for i in range(len(pred2))]
            
            for i, det in enumerate(combined_pred):  # detections per image
                p, im0 = img_index[i], im0s[i].numpy()

                all_frames[int(p)] = im0
                # gn = torch.tensor(im0.shape)[[1, 0, 1, 0]]  # normalization gain whwh
                if len(det):
                    # Rescale boxes from img_size to im0 size
                    det[:, :4] = scale_coords(img.shape[2:], det[:, :4], im0.shape).round()
                    
                    result = Results(orig_img=im0, path=str(int(p)), names=self.object_names_K_V, boxes=det)
                    # Tracking Mechanism
                    detection_supervision = sv.Detections.from_ultralytics(result)
                    detection_with_tracks = self.tracker.update_with_detections(detection_supervision)
                    # tracks["head"].append({})
                
                    # Write results
                    for frame_detection in detection_with_tracks:
                        bbox = frame_detection[0].tolist()
                        confs = frame_detection[2]
                        clss = frame_detection[3]
                        person_id = frame_detection[4]
                        self.accumulate_head_and_otherobject_track(bbox,confs,clss,int(person_id),accumulator,im0,int(p))
                    
        return all_frames,accumulator

    def detection_with_facial_regonition(self,images,facial_embeddings,batch_track,vid_img_dir):
        val_dataset = LoadImageDataset(images, batch_track, self.batch_size,img_size=self.imgsz, stride=self.stride)
        dataset = torch.utils.data.DataLoader(dataset=val_dataset,
                                               batch_size=self.batch_size,
                                               shuffle=False,
                                               num_workers=0)
        
        accumulator = {'head':dict(), 'other_objects':dict()}
        all_frames = {}
        for val_batch, (img_index, img, im0s) in enumerate(dataset): #path, img, im0s, vid_cap in dataset:
            # all_frames.extend(im0s)
            # img = torch.from_numpy(img).to(device)
            img = img.to(self.device)
            img = img.half() if self.half else img.float()  # uint8 to fp16/32
            img /= 255.0  # 0 - 255 to 0.0 - 1.0
            if img.ndimension() == 3:
                img = img.unsqueeze(0)

            # Inference
            pred = self.model_1(img, augment=self.augment)[0]
            pred2 = self.model_2(img, augment=self.augment)[0]
            
            # Apply NMS
            pred = non_max_suppression(pred, self.model1_conf_thres, self.model1_iou_thres, classes=self.classes, agnostic=self.agnostic_nms)
            pred2 = non_max_suppression(pred2, self.model2_conf_thres, self.model2_iou_thres, classes=self.classes, agnostic=self.agnostic_nms)
            
            #combine pred and pred 2, filter out all cls 0 (person) detection for pred. keep only head (cls 1) detection 
            # and filter out all cls 1 (bicycle)  detection  pred 2
            combined_pred = [torch.cat((pred[i][pred[i][:,5] >= 1],pred2[i][pred2[i][:,5] != 1])) for i in range(len(pred2))]
            
            for i, det in enumerate(combined_pred):  # detections per image
                p, im0 = img_index[i], im0s[i].numpy()

                all_frames[int(p)] = im0
                # gn = torch.tensor(im0.shape)[[1, 0, 1, 0]]  # normalization gain whwh
                if len(det):
                    # Rescale boxes from img_size to im0 size
                    det[:, :4] = scale_coords(img.shape[2:], det[:, :4], im0.shape).round()
                    
                    row = 0
                    for *xyxy, conf, cls in reversed(det):
                        int_cls = int(cls)
                        if int_cls == self.object_names_V_K.get('head', None):
                            face = self.crop_from_bbox(im0,xyxy, "xyxy", False, 0.0, False)
                           
                            x1, y1, x2, y2 = xyxy
                            face_location = (y1, x2, y2, x1)
                            face_embedding  = face_recognition.face_encodings(face, [face_location])
                            match, score = self.identify_student(face_embedding, facial_embeddings, threshold=0.5)
                            print(f"Match: {match}, Confidence: {score:.3f}")
                            # save_to = os.path.join(vid_img_dir, "{0}.{1}".format(row+1,'png'))
                            # cv2.imwrite(save_to,face)
                        # self.accumulate_head_track(bbox,confs,clss,int(person_id),accumulator,im0,int(p))


                    # result = Results(orig_img=im0, path=str(int(p)), names=self.object_names_K_V, boxes=det)
                    # # Tracking Mechanism
                    # detection_supervision = sv.Detections.from_ultralytics(result)
                    # detection_with_tracks = self.tracker.update_with_detections(detection_supervision)
                    # # tracks["head"].append({})
                
                    # # Write results
                    # for frame_detection in detection_with_tracks:
                    #     bbox = frame_detection[0].tolist()
                    #     confs = frame_detection[2]
                    #     clss = frame_detection[3]
                    #     person_id = frame_detection[4]
                    #     self.accumulate_head_track(bbox,confs,clss,int(person_id),accumulator,im0,int(p))
                    
        return all_frames,accumulator
    
    def cosine_similarity(self,vec1, vec2):
        """Compute cosine similarity between two vectors."""
        return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))

    def identify_student(self,face_embedding, store_facial_embeddings, threshold=0.5):
        """
        Identify student by comparing a new face embedding against stored gallery.
        :param face_embedding: embedding vector of the new face
        :param student_gallery: dict {student_name: avg_embedding}
        :param threshold: similarity threshold (tune ~0.4–0.6 depending on model)
        :return: (best_match, score) or ("Unknown", None)
        """
        best_match = "Unknown"
        best_score = -1  # cosine similarity ranges -1 to 1
        for person in store_facial_embeddings:
            stored_embedding = store_facial_embeddings[person]["data"]
            student = store_facial_embeddings[person]["alias"]
            print("student is ......"+student)
            score = self.cosine_similarity(face_embedding, stored_embedding)
            if score > best_score:
                best_score = score
                best_match = student

        if best_score >= threshold:
            return best_match, best_score
        else:
            return "Unknown", best_score
    
    def accumulate_head_and_otherobject_track_V2(self,bbox,conf,cls,person_id,accumulator,im0,p):
       
        if cls == self.object_names_V_K.get('head', None): #only track the head 
            if person_id in accumulator['head']:
                accumulator['head'][person_id].append([p,person_id,bbox ])
            else:
                accumulator['head'][person_id] = [[p,person_id,bbox]]    
            # also add the persion detected as an object, since another person gaze can be on this person
            #, we append all the objects in a frame (based on fame id , p) together 
            if p in accumulator['other_objects']:
                accumulator['other_objects'][p].append([cls,self.object_names_K_V[int(cls)],person_id,bbox ])
            else:
                accumulator['other_objects'][p] = [[cls,self.object_names_K_V[int(cls)],person_id,bbox ]]    
            
        #accumulate all other objects except person    
        elif cls != self.object_names_V_K.get('person', None):
            if p in accumulator['other_objects']:
                accumulator['other_objects'][p].append([cls,self.object_names_K_V[int(cls)],person_id,bbox ])
            else:
                accumulator['other_objects'][p] = [[cls,self.object_names_K_V[int(cls)],person_id,bbox ]]  

    def accumulate_head_and_otherobject_track(self,bbox,conf,cls,person_id,accumulator,im0,p):
        if cls == self.object_names_V_K.get('head', None): #only track the head 
            if person_id in accumulator['head']:
                accumulator['head'][person_id].append([p,person_id,int(bbox[0]),int(bbox[1]),int(bbox[2]),int(bbox[3]) ])
            else:
                accumulator['head'][person_id] = [[p,person_id,int(bbox[0]),int(bbox[1]),int(bbox[2]),int(bbox[3])]]    
            # also add the persion detected as an object, since another person gaze can be on this person
            #, we append all the objects in a frame (based on fame id , p) together 
            if p in accumulator['other_objects']:
                accumulator['other_objects'][p].append([cls,self.object_names_K_V[int(cls)],person_id,int(bbox[0]),int(bbox[1]),int(bbox[2]),int(bbox[3]) ])
            else:
                accumulator['other_objects'][p] = [[cls,self.object_names_K_V[int(cls)],person_id,int(bbox[0]),int(bbox[1]),int(bbox[2]),int(bbox[3]) ]]    
            
        #accumulate all other objects except person    
        elif cls != self.object_names_V_K.get('person', None):
            if p in accumulator['other_objects']:
                accumulator['other_objects'][p].append([cls,self.object_names_K_V[int(cls)],person_id,int(bbox[0]),int(bbox[1]),int(bbox[2]),int(bbox[3]) ])
            else:
                accumulator['other_objects'][p] = [[cls,self.object_names_K_V[int(cls)],person_id,int(bbox[0]),int(bbox[1]),int(bbox[2]),int(bbox[3]) ]]  
   
    def crop_from_bbox(self,
        img: np.ndarray,
        bbox,
        fmt: str = "xyxy",          # "xyxy" (xmin,ymin,xmax,ymax) or "xywh" (x,y,w,h)
        normalized: bool = False,   # True if bbox values are in [0,1] relative to width/height
        margin: float = 0.0,        # extra border around the face; if normalized, treat as ratio of diag
        square: bool = False        # pad to a square crop
        ):
        """
        Returns a cropped image as a NumPy array.

        img: HxWxC (uint8 or float); works with grayscale too (HxW)
        bbox: tuple/list of 4 numbers
        margin: if >0, adds padding around bbox. If normalized=True, it's fraction of the bbox size.
        """
        h, w = img.shape[:2]

        # Convert bbox to pixel xyxy
        if fmt == "xyxy":
            x1, y1, x2, y2 = bbox
            if normalized:
                x1, y1, x2, y2 = x1 * w, y1 * h, x2 * w, y2 * h
        elif fmt == "xywh":
            x, y, bw, bh = bbox
            if normalized:
                x, y, bw, bh = x * w, y * h, bw * w, bh * h
            x1, y1, x2, y2 = x, y, x + bw, y + bh
        else:
            raise ValueError("fmt must be 'xyxy' or 'xywh'")

        # Ensure proper ordering
        x1, x2 = float(min(x1, x2)), float(max(x1, x2))
        y1, y2 = float(min(y1, y2)), float(max(y1, y2))

        # Add margin
        if margin > 0:
            if normalized:
                # margin is treated as a fraction of bbox size
                mx = margin * (x2 - x1)
                my = margin * (y2 - y1)
            else:
                mx = my = margin
            x1 -= mx
            y1 -= my
            x2 += mx
            y2 += my

        # Make square if requested (by symmetric padding)
        if square:
            bw = x2 - x1
            bh = y2 - y1
            side = max(bw, bh)
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2
            x1 = cx - side / 2
            x2 = cx + side / 2
            y1 = cy - side / 2
            y2 = cy + side / 2

        # Clamp to image bounds and cast to int for slicing
        x1 = max(0, int(round(x1)))
        y1 = max(0, int(round(y1)))
        x2 = min(w, int(round(x2)))
        y2 = min(h, int(round(y2)))

        # Guard against empty or invalid crops
        if x2 <= x1 or y2 <= y1:
            raise ValueError("Invalid bbox after processing; no area to crop.")

        return img[y1:y2, x1:x2].copy()

# if __name__ == '__main__':
#     imge_detect = ImageObjectDetection()
#     imge_detect.init_model()
