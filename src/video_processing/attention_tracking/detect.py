import argparse
import queue
import threading
import time
import traceback
from pathlib import Path
import os
import sys
from queue import Empty, Full
import cv2
import torch
import logging
import torch.backends.cudnn as cudnn
from numpy import random
import os
import numpy as np
import supervision as sv
import face_recognition
from ultralytics.engine.results import Results
from .utils.dataset import AttentionFlow
sys.path.insert(0,'./yolo_head')
from yolo_head.models.experimental import attempt_load
from yolo_head.utils.datasets import LoadStreams, LoadImages, LoadImageDataset,letterbox2
from yolo_head.utils.general import check_img_size, non_max_suppression, scale_coords
from yolo_head.utils.torch_utils import select_device
from yolo_head.utils.plots import plot_one_box


class ImageObjectDetection:
    def __init__(self,stop_signal,num_workers=1,source="real_time"):
        self.frame_queue_manager = {}
        self.accumulator_queue_manager = {}
        self.work_queue = queue.Queue(maxsize=10)
        self.workers = []
        self.worker_loop_t = None
        self.num_workers = num_workers
        self.source = source
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
        self.lock = threading.Lock()
        self.STOP = stop_signal  # sentinel
        self.user_completed = set()
        self.running = False
        self.hasreceivedjob = False
    

    def _predict_objects(self, img):
        # pred2-equivalent detections as a list of (N,6) [x1,y1,x2,y2,conf,cls]
        # tensors in the SAME letterboxed coordinate space as model_1's
        # predictions, so the downstream cat + scale_coords is unchanged.
        if self.model_2v2 is not None:
            results = self.model_2v2(img.float(), conf=self.model2_conf_thres,
                                     iou=self.model2_iou_thres, half=True, verbose=False)
            return [
                torch.cat((r.boxes.xyxy, r.boxes.conf.unsqueeze(1),
                           r.boxes.cls.unsqueeze(1)), dim=1)
                for r in results
            ]
        pred2 = self.model_2(img, augment=self.augment)[0]
        return non_max_suppression(pred2, self.model2_conf_thres, self.model2_iou_thres, classes=self.classes, agnostic=self.agnostic_nms)

    def _predict_heads(self, img):
        # Head/person detections as a list of (N,6) [x1,y1,x2,y2,conf,cls]
        # tensors in the SAME letterboxed coordinate space as the object
        # predictions, so the downstream cat + scale_coords is unchanged.
        if self.model_1v2 is not None:
            results = self.model_1v2(img.float(), conf=self.model1_conf_thres,
                                     iou=self.model1_iou_thres, half=True, verbose=False)
            out = []
            for r in results:
                # The downstream merge keeps class-id >= 1 as "head". A
                # CrowdHuman head-only model typically emits class 0, so remap
                # every detection to class 1 to preserve heads.
                # NOTE: confirm the class layout of your chosen checkpoint — if
                # it also emits 'person', filter to the head class before remap.
                cls = torch.ones((r.boxes.xyxy.shape[0], 1), device=r.boxes.xyxy.device)
                out.append(torch.cat((r.boxes.xyxy, r.boxes.conf.unsqueeze(1), cls), dim=1))
            return out
        pred = self.model_1(img, augment=self.augment)[0]
        return non_max_suppression(pred, self.model1_conf_thres, self.model1_iou_thres, classes=self.classes, agnostic=self.agnostic_nms)

    def init_model(self,batch_size):
        self.batch_size = batch_size
        base_path = os.path.dirname(os.path.abspath(__file__))
        weight_1 = os.path.join( base_path,'pretrained-models/crowdhuman_yolov5m.pt')

        weight_2 = os.path.join( base_path,'pretrained-models/yolov4-p7.pt')
        self.device = select_device('')
        self.half = self.device.type != 'cpu'  # half precision only supported on CUDA
        # Load model
        import config as _cf
        from facial_recognition_backend import get_face_backend
        self.face_backend = get_face_backend()  # dlib (default) or insightface, per config.face_model()
        # One representative face crop per recognized student, so the UI can show
        # a real face thumbnail (keyed by alias, first good match per run wins).
        self._thumb_dir = os.path.join(_cf.facial_embedding_folder(), 'thumbnails')
        self._saved_thumbs = {}  # alias -> best (lowest) match distance this run
        # Head detector is config-selected: the vendored yolo_head CrowdHuman
        # YOLOv5m pickle (default) or an ultralytics YOLO11/YOLOv8 head model.
        # Moving to 'ultralytics' is the path to retiring the vendored yolo_head/.
        self.model_1v2 = None
        if _cf.head_model() == 'ultralytics':
            from ultralytics import YOLO as _YOLO
            self.model_1v2 = _YOLO(os.path.join(base_path, _cf.head_weights()))
            self.model_1 = None
        else:
            self.model_1 = attempt_load(weight_1, map_location=self.device)  # load FP32 model for head and person detection
        # Object detector is config-selected: YOLO11 (open SOTA; default) or the
        # original YOLOv4-P7 pickle (requires the legacy mish_cuda package).
        self.model_2v2 = None
        if _cf.object_model() == 'yolo11':
            from ultralytics import YOLO as _YOLO
            self.model_2v2 = _YOLO(os.path.join(base_path, 'yolo11m.pt'))
            self.model_2 = None
        else:
            self.model_2 = attempt_load(weight_2, map_location=self.device)  # load FP32 model for person and other object detection
        #prep model 1 (legacy yolov5 head path only; ultralytics manages its own)
        imgsz_1 = self.imgsz
        if self.model_1 is not None:
            self.stride = int(self.model_1.stride.max())  # model stride
            imgsz_1 = check_img_size(self.imgsz, s=self.stride)  # check img_size
            if self.half:
                self.model_1.half()  # to FP16
        else:
            self.stride = 32

        #prep model 2 (legacy yolov4 path only)
        if self.model_2 is not None:
            stride2 = int(self.model_2.stride.max())  # model stride
            imgsz_2 = check_img_size(self.imgsz, s=stride2)  # check img_size
            if self.half:
                self.model_2.half()  # to FP16


        # Run inference — warm up each legacy model independently (ultralytics
        # models manage their own warmup, so they are skipped here).
        if self.device.type != 'cpu':
            if self.model_1 is not None:
                self.model_1(torch.zeros(self.batch_size, 3, imgsz_1, imgsz_1).to(self.device).type_as(next(self.model_1.parameters())))  # run once
            if self.model_2 is not None:
                self.model_2(torch.zeros(self.batch_size, 3, imgsz_2, imgsz_2).to(self.device).type_as(next(self.model_2.parameters())))  # run once

        # Get names  for pred 1
        if self.model_1v2 is not None:
            names_model_1 = dict(self.model_1v2.names)
        else:
            names_model_1 = self.model_1.module.names if hasattr(self.model_1, 'module') else self.model_1.names
        # Get names for pred 2
        if self.model_2v2 is not None:
            names_model_2 = dict(self.model_2v2.names)
        else:
            names_model_2 = self.model_2.module.names if hasattr(self.model_2, 'module') else self.model_2.names
        #change the value of the name in key 1 to the value of name in names_model_1[1]
        # Defensive: a head-only ultralytics checkpoint may expose names {0:'head'}
        # with no index 1, so fall back to 'head' rather than KeyError/IndexError.
        try:
            names_model_2[1] = names_model_1[1]
        except (KeyError, IndexError):
            names_model_2[1] = 'head'

        if  isinstance(names_model_2,list):
            for k, v in enumerate(names_model_2):
                self.object_names_V_K[v] =  k 
                self.object_names_K_V[k] =  v
        elif isinstance(names_model_2,dict):
            self.object_names_K_V = names_model_2
            self.object_names_V_K = {v: k for k, v in names_model_2.items()}
        # {0: 'person', 1: 'head', 2: 'car', 3: 'motorcycle', 4: 'airplane', 5: 'bus', 6: 'train', 7: 'truck', 8: 'boat', 9: 'traffic light', 
        # 10: 'fire hydrant', 11: 'stop sign', 12: 'parking meter', 13: 'bench', 14: 'bird', 15: 'cat', 16: 'dog', 17: 'horse', 18: 'sheep', 
        # 19: 'cow', 20: 'elephant', 21: 'bear', 22: 'zebra', 23: 'giraffe', 24: 'backpack', 25: 'umbrella', 26: 'handbag', 27: 'tie', 28: 'suitcase',
        # 29: 'frisbee', 30: 'skis', 31: 'snowboard', 32: 'sports ball', 33: 'kite', 34: 'baseball bat', 35: 'baseball glove', 36: 'skateboard', 
        # 37: 'surfboard', 38: 'tennis racket', 39: 'bottle', 40: 'wine glass', 41: 'cup', 42: 'fork', 43: 'knife', 44: 'spoon', 45: 'bowl', 46: 'banana',
        # 47: 'apple', 48: 'sandwich', 49: 'orange', 50: 'broccoli', 51: 'carrot', 52: 'hot dog', 53: 'pizza', 54: 'donut', 55: 'cake', 56: 'chair', 57: 'couch',
        # 58: 'potted plant', 59: 'bed', 60: 'dining table', 61: 'toilet', 62: 'tv', 63: 'laptop', 64: 'mouse', 65: 'remote', 66: 'keyboard', 67: 'cell phone', 
        # 68: 'microwave', 69: 'oven', 70: 'toaster', 71: 'sink', 72: 'refrigerator', 73: 'book', 74: 'clock', 75: 'vase', 76: 'scissors', 77: 'teddy bear', 78: 'hair drier', 79: 'toothbrush'}
        # logging.info("Model 1 and Model 2 loaded successfully with object names: {0}".format(self.object_names_K_V))    
    
    def start(self):
        self.running = True
        self.hasreceivedjob = False

        
        self.worker_loop_t = threading.Thread(target=self.worker_loop, daemon=True)
        self.worker_loop_t.start()

        self.object_detection_thread = threading.Thread(target=self.scheduler, name="object-detection-thread")
        self.object_detection_thread.daemon = True
        self.object_detection_thread.start()

    def stop(self):
        self.running = False
        logging.info("Stopping object detection thread...")

    # this schedule will go through each candiate's queue added to frame_queue_manager
    # and get the added job. This goes tune by turn to ensure each candiate job is process round robbingly
    # regardless of when they join. This solve the issue of using one queue for all candiadate, which result to
    # candidates that join later having to wait longer till it gets to their turn
    def scheduler(self):
        while self.running:
            candidate_turn = 0
            candidate_unique_ids = list(self.frame_queue_manager.keys())
            len_candidate_unique_ids = len(candidate_unique_ids)
            
            if len_candidate_unique_ids != 0:
                self.hasreceivedjob = True

            while candidate_turn < len_candidate_unique_ids:
                try:
                    # block briefly to avoid CPU spin; adjust timeout for latency needs
                    payload = self.frame_queue_manager[candidate_unique_ids[candidate_turn]].get_nowait() #get(timeout=0.25)
                except Empty:
                    continue
                
                self.work_queue.put(payload) 
                _,_,_,_,_,auth_key,last_batch = payload

                if last_batch:
                    self.frame_queue_manager.pop(auth_key,None)
                    break
                
                # self.worker(self.frame_queue_manager[candidate_unique_ids[candidate_turn]],candidate_unique_ids[candidate_turn])


                # logging.info("proceesed imagedection work for client {0} of {1} with key {2} ".format(candidate_turn+1,len_candidate_unique_ids,candidate_unique_ids[candidate_turn]))
                candidate_turn += 1

                # if the last candiate have been scheduled, then break so that a fresh candiadates_id is fetched
                # possible a new candiate may have added its queue to the elf.frame_queue_manager
                if candidate_turn == len_candidate_unique_ids:
                    break

            # for posthoc processing use this to exit the thread
            if  self.source != "real_time" and self.hasreceivedjob and len(self.frame_queue_manager) == 0: #self.user_completed and len(self.user_completed) == len_candidate_unique_ids:
                logging.info("Finished image detection thread scheduler")
                break # self.stop()
                
                
                
    
    def worker_loop(self):
        while self.running:
            try:
                t0 = time.time()  
                payload = self.work_queue.get(timeout=0.1)
            except Empty:
                # for posthoc processing use this to exit the thread
                if  self.source != "real_time" and self.hasreceivedjob and  len(self.frame_queue_manager) == 0:
                    self.stop()
                    break
                continue
            t1 = time.time()  
            logging.info(f"Inside Image-dection: reading from worker queue took {t1 - t0:.6f}s")    
            # t2 = time.time()  
            self.worker(payload)
            t3 = time.time()
            # logging.info(f"Inside Image-dection:  procesing image dectection took {t3 - t2:.6f}s")

    def worker(self,payload):
        
        try:
            images,facial_embeddings,batch_track,time_marker,vid_img_dir,auth_key,last_batch = payload
            all_frames,accumulator = self.detection_with_facial_regonition(images,facial_embeddings,batch_track,time_marker,vid_img_dir,auth_key)
            logging.info("Alloc {0}: after image-detection for batch {1}".format((torch.cuda.memory_allocated() / 1024**2), batch_track))
            logging.info("reserved {0}: after image-detection for batch {1}".format((torch.cuda.memory_reserved() / 1024**2), batch_track))
            
            accumulator_load = [auth_key,all_frames,accumulator,batch_track,last_batch]
            #enque for gaze detection and attention flow processing, 

            return accumulator_load #remove later
            #uncomment later
            # self.enqueue_latest_accumulator_payload(accumulator_load,auth_key)
        except Exception as e:
            error_str = traceback.format_exc()
            logging.warning('Exception thrown while image detedction worker is running {0} {1}'.format(error_str, auth_key))

    def worker_posthoc(self,payload):
        
        try:
            images,facial_embeddings,batch_track,time_marker,vid_img_dir,auth_key,last_batch = payload
            all_frames,accumulator = self.detection_with_facial_regonition(images,facial_embeddings,batch_track,time_marker,vid_img_dir,auth_key)
            
            accumulator_load = [auth_key,all_frames,accumulator,batch_track,last_batch]

            return accumulator_load 
        except Exception as e:
            error_str = traceback.format_exc()
            logging.warning('Exception thrown while image detedction worker is running {0} {1}'.format(error_str, auth_key))

    def enqueue_latest_accumulator_payload(self, payload,candidate_queue_id, timeout=0.1):
        """
        Keep only the most recent chunk in the queue.
        If the queue is full, remove the stale queued chunk and replace it.
        """
        if candidate_queue_id not in self.accumulator_queue_manager:
            self.accumulator_queue_manager[candidate_queue_id] = queue.Queue(maxsize=3)
        
        try:
            self.accumulator_queue_manager[candidate_queue_id].put(payload, timeout=timeout)
            return True
        except Full:
            logging.warning("Accumulator queue for {0} is full; attempting to replace stale payload with latest payload.".format(candidate_queue_id))
            pass

        # Queue is full: drop the old queued item
        try:
            old_item = self.accumulator_queue_manager[candidate_queue_id].get_nowait()
            # optional: if you use task_done semantics elsewhere, call task_done here
            # self.frame_queue.task_done()
        except Empty:
            logging.warning("Accumulator queue for {0} was full but is now empty; failed to replace payload.".format(candidate_queue_id))
            old_item = None

        # Try again to insert the latest chunk
        try:
            self.accumulator_queue_manager[candidate_queue_id].put_nowait(payload)
            return True
        except Full:
            logging.warning("Could not enqueue latest frame payload for {0}; dropping it.".format(candidate_queue_id))
            return False   
        
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

            # Inference (+ NMS) — head detector, config-selected backend
            pred = self._predict_heads(img)
            pred2 = self._predict_objects(img)
            
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

    def detection_with_facial_regonition(self,images,facial_embeddings,batch_track,time_marker,vid_img_dir,auth_key):
        # t1 = time.time()
        val_dataset = LoadImageDataset(images, batch_track, self.batch_size,img_size=self.imgsz, stride=self.stride)
        dataset = torch.utils.data.DataLoader(dataset=val_dataset,
                                               batch_size=self.batch_size,
                                               shuffle=False,
                                               num_workers=0)
        # t2 = time.time()
        # logging.info(f"Inside Imagedetection: batching  took {t2 - t1:.6f}s for {len(images)} frames")
        accumulator = {'head':dict(), 'other_objects':dict()}
        all_frames = {}

        # logging.info("number of facial embeddings is "+str(len(facial_embeddings))+" number of frames "+str(len(images)))
        torch.cuda.synchronize()
        t1 = time.time()
        for val_batch, (img_index, img, im0s) in enumerate(dataset): #path, img, im0s, vid_cap in dataset:
            # all_frames.extend(im0s)
            # img = torch.from_numpy(img).to(device)
            # t3 = time.time()
            with torch.inference_mode():
                img = img.to(self.device)
                img = img.half() if self.half else img.float()  # uint8 to fp16/32
                img /= 255.0  # 0 - 255 to 0.0 - 1.0
                if img.ndimension() == 3:
                    img = img.unsqueeze(0)

                # Inference (+ NMS) — head detector, config-selected backend
                pred = self._predict_heads(img)
                pred2 = self._predict_objects(img)
                
                #combine pred and pred 2, filter out all cls 0 (person) detection for pred. keep only head (cls 1) detection 
                # and filter out all cls 1 (bicycle)  detection  pred 2
                combined_pred = [
                                    torch.cat(
                                        (pred[i][pred[i][:, 5] >= 1],
                                        pred2[i][pred2[i][:, 5] != 1])
                                    )
                                    for i in range(len(pred2))
                                ]
            # t4 = time.time()
            # logging.info(f"Inside Imagedetection: prediction only  took {t4 - t3:.6f}s for {len(img)} frames")
            for i, det in enumerate(combined_pred):  # detections per image
                p, im0 = img_index[i], im0s[i].numpy()

                all_frames[int(p)] = im0
                # gn = torch.tensor(im0.shape)[[1, 0, 1, 0]]  # normalization gain whwh
                
                if len(det):
                    # Rescale boxes from img_size to im0 size
                    det = det.clone()
                    det[:, :4] = scale_coords(img.shape[2:], det[:, :4], im0.shape).round()
                    detected_faces = 0
                    #use this for face tracking across frames
                    for *xyxy, conf, cls in reversed(det):
                        int_cls = int(cls)
                        match = "Unknown"
                        face_embedding = None
                        score = -1  # cosine similarity ranges -1 to 1
                        if int_cls == self.object_names_V_K.get('head', None):
                            detected_faces = detected_faces+1
                            # logging.info("Detected face in frame {0}".format(detected_faces))
                            face = self.crop_face_from_frame_with_bbox(im0,xyxy, "xyxy", False, 30, False)
                            # face_big = cv2.resize(face, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                            # face = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)

                            # plot_one_box(xyxy, im0, label=self.object_names_K_V.get(int_cls, None), color=[random.randint(0, 255) for _ in range(3)], line_thickness=3)
                            # save_to = os.path.join(vid_img_dir, "face_{0}_{1}_{2}.{3}".format(int(p),self.object_names_K_V.get(int_cls, None),detected_faces,'png'))
                            # cv2.imwrite(save_to,face)
                            x1, y1, x2, y2 = xyxy
                            # face_location = (int(y1), int(x2), int(y2), int(x1))
                            # logging.info("frame shape : {0}, type: {1}, min: {2} and, max: {3}".format(im0.shape, im0.dtype, im0.min(), im0.max()))
                            # logging.info("face shape : {0}, type: {1}, min: {2} and, max: {3}".format(face.shape, face.dtype, face.min(), face.max()))
                            # logging.info("face big shape : {0}, type: {1}, min: {2} and, max: {3}".format(face_big.shape, face_big.dtype, face_big.min(), face.max()))
                            
                            quality_face = self.prepare_quality_face(face,min_size=90,min_blur=50,upscale_to=320)
                            
                            if  quality_face is None:
                                continue

                            face_locations = self.face_backend.locate(quality_face, model="cnn") #hog is faster but less accurate than cnn. cnn may not work well with small faces.
                            # logging.info("Face locations for small : {0}".format(face_locations))
                            # face_locations = face_recognition.face_locations(face_big, model="cnn") #hog is faster but less accurate than cnn. cnn may not work well with small faces.
                            # logging.info("Face locations for big : {0}".format(face_locations))
                            if face_locations:
                                face_embedding  = self.face_backend.encode(quality_face, face_locations,num_jitters=2)
                                # (top, right, bottom, left) =  face_locations[0]
                                # face_2 = face_big[top:bottom, left:right]
                                # save_to = os.path.join(vid_img_dir, "face_{0}_{1}_{2}.{3}".format(int(p),self.object_names_K_V.get(int_cls, None),detected_faces,'png'))
                                # cv2.imwrite(save_to,face_2)
                            else:  
                                # logging.info("Face locations: empty")
                                h_face, w_face = quality_face.shape[:2]
                                face_embedding  = self.face_backend.encode(face,known_face_locations=[(0, w_face, h_face, 0)],num_jitters=2)
                            # logging.info("Face locations: {0}".format(face_locations))
                            if face_embedding:  
                                match, cos_score,L2_score,dist_score = self.identify_student(face_embedding[0], facial_embeddings, "face_"+str(detected_faces),cos_threshold=0.95,L2_threshold=0.3,frame_index=int(p))
                                if match != "Unknown":
                                    # plot_one_box(xyxy, im0, label=self.object_names_K_V.get(int_cls, None), color=[random.randint(0, 255) for _ in range(3)], line_thickness=3)
                                    # logging.info("Match: {0}, cos score: {1}, Euclid: {2}, Distance: {3}".format(match,cos_score,L2_score,dist_score))
                                    self._save_face_thumbnail(match, quality_face, dist_score)
                                    self.accumulate_head_and_otherobject_track_V2(xyxy,int_cls,"detected_face",match,accumulator,time_marker,im0,int(p))
                                else:
                                    pass
                                    # logging.info(f"Match: {match}, Confidence: {cos_score:.3f}")   
                                 
                        else:
                        #   logging.info("Other object dtected is: {0}".format(self.object_names_K_V.get(int_cls, None)))
                          self.accumulate_head_and_otherobject_track_V2(xyxy,int_cls,"detected_other_objects","None",accumulator,time_marker,im0,int(p)) 
                         
                    # print("number of detected faces for frame ",str(i)+" is "+str(detected_faces))
                    # save_to = os.path.join(vid_img_dir, "frame_{0}.{1}".format(int(p),'png'))
                    # cv2.imwrite(save_to,im0)

                    #use this for tracking other objects asides face
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
                    #     object_id = frame_detection[4]
                        
                    #     if int(clss) != self.object_names_V_K.get('person', None) and int(clss) != self.object_names_V_K.get('head', None):
                    #         # print("Other object detected is: ",self.object_names_K_V.get(int(clss), None))
                    #         #accumulate all other objects except person  
                    #         self.accumulate_head_and_otherobject_track_V2(bbox,int(clss),"detected_other_objects",str(object_id),accumulator,time_marker,im0,int(p))  
        # torch.cuda.synchronize()
        t2 = time.time()
        logging.info(f"Inside Imagedetection: prediction and facial matching  took {t2 - t1:.6f}s for {len(images)} frames")                       
                    
        return all_frames,accumulator
    
    
    
    def normalize(self,v):
        return v / np.linalg.norm(v)

    def cosine_similarity(self,vec1, vec2):
        """Compute cosine similarity between two vectors."""
        return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))

    def debug_embed(self,name, v):
        logging.info(f"{name}: shape={v.shape}, dtype={v.dtype}, "
            f"min={np.min(v):.6f}, max={np.max(v):.6f}, "
            f"norm={np.linalg.norm(v):.6f}, "
            f"nan?={np.isnan(v).any()}, inf?={np.isinf(v).any()}")
    
    def _save_face_thumbnail(self, alias, face_img, match_distance):
        # Persist the BEST face crop per recognized student (lowest match
        # distance), overwriting weaker earlier crops — "first match wins"
        # saved misidentified faces (a weak cross-match could claim the file
        # before a confident one arrived). A quality floor keeps marginal
        # matches from ever becoming someone's picture. Never breaks the run.
        try:
            if not alias or match_distance is None:
                return
            if match_distance > 0.45:  # only confident matches become thumbnails
                return
            best = self._saved_thumbs.get(alias)
            if best is not None and best <= match_distance:
                return
            self._saved_thumbs[alias] = match_distance
            os.makedirs(self._thumb_dir, exist_ok=True)
            path = os.path.join(self._thumb_dir, "{0}.jpg".format(os.path.basename(str(alias))))
            # face_img is RGB (face_recognition/dlib convention); cv2 writes BGR.
            cv2.imwrite(path, cv2.cvtColor(face_img, cv2.COLOR_RGB2BGR))
            logging.info("saved face thumbnail for %s (dist %.3f)", alias, match_distance)
        except Exception as e:
            logging.warning("face thumbnail save failed for %s: %s", alias, e)

    def identify_student(self,face_embedding, store_facial_embeddings,detect_img_name, cos_threshold=0.95,L2_threshold=0.3,frame_index=None):
        """
        Identify student by comparing a new face embedding against stored gallery.
        :param face_embedding: embedding vector of the new face
        :param student_gallery: dict {student_name: avg_embedding}
        :param threshold: similarity threshold (tune ~0.4–0.6 depending on model)
        :return: (best_match, score) or ("Unknown", score)
        """
        best_match = "Unknown"
        best_cos_score = -1  # cosine similarity ranges -1 to 1
        best_L2_score = 1
        best_distance = 1
        # Backend-appropriate acceptance cutoff (dlib: L2<0.5; ArcFace: cos-dist).
        max_distance = self.face_backend.match_params()["max_distance"]
        for person in store_facial_embeddings:
            stored_embedding = store_facial_embeddings[person]["data"]
            student = store_facial_embeddings[person]["alias"]
            # logging.info("student is ......{0}".format(student))
            # self.debug_embed(detect_img_name,face_embedding)
            # self.debug_embed(student,stored_embedding)
            distance = self.face_backend.distance(stored_embedding, face_embedding)
            u = self.normalize(face_embedding)
            v = self.normalize(stored_embedding)

            score = float(np.dot(u, v)) #self.cosine_similarity(face_embedding, stored_embedding)
            Euc_dist = float(np.linalg.norm(u - v))
            # logging.info(f"score are Euclidean: {Euc_dist} and cos simillarity: {score} and distance: {distance}")
            # Select by the backend's own distance metric under its calibrated
            # cutoff. The previous compound gate also required Euc_dist < 1
            # (i.e. cos > 0.5), a dlib-tuned bound that rejected valid ArcFace
            # matches (which sit around cos 0.32-0.5); score/Euc_dist are kept
            # only for logging/return.
            if distance < max_distance and distance < best_distance:
                best_cos_score = score
                best_L2_score = Euc_dist
                best_match = student
                best_distance = distance
        # if best_distance < 0.5:
        #     logging.info("distance for all embedding are {0}, but matched {1} at cos score {2} and euclid : {3} in frame {4}".format(best_distance,best_match,best_cos_score,best_L2_score,frame_index))    
        # if best_cos_score >= cos_threshold and best_L2_score <= L2_threshold:
        # logging.info(f"student is ...... {best_match} and score are cos_simmilarity: {best_cos_score} Euclidean Dist: {best_L2_score}")
        return best_match, best_cos_score, best_L2_score,best_distance
        # else:
        #     return "Unknown", best_cos_score,best_L2_score
    
    def accumulate_head_and_otherobject_track_V2(self,bbox,object_class_id,object_detected_type,object_track_id,accumulator,time_marker,frame_image,frame_index):

        time_stamp = time_marker[frame_index%self.batch_size]
        if object_detected_type == "detected_face": #only track the head 
            if object_track_id in accumulator['head']:
                accumulator['head'][object_track_id].append([frame_index,object_track_id,bbox,time_stamp ])
            else:
                accumulator['head'][object_track_id] = [[frame_index,object_track_id,bbox,time_stamp]]    
            # also add the persion detected as an object, since another person gaze can be on this person
            #, we append all the objects in a frame (based on fame id , p) together 
            if frame_index in accumulator['other_objects']:
                accumulator['other_objects'][frame_index].append([object_class_id,object_track_id,object_track_id,bbox,time_stamp ])
            else:
                accumulator['other_objects'][frame_index] = [[object_class_id,object_track_id,object_track_id,bbox,time_stamp ]]    
            
        #accumulate all other objects   
        elif object_detected_type == "detected_other_objects":
            if frame_index in accumulator['other_objects']:
                accumulator['other_objects'][frame_index].append([object_class_id,self.object_names_K_V[object_class_id],object_track_id,bbox, time_stamp])
            else:
                accumulator['other_objects'][frame_index] = [[object_class_id,self.object_names_K_V[object_class_id],object_track_id,bbox, time_stamp]]  
            # print("object detected is: ",self.object_names_K_V[object_class_id])    

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
   
    def crop_face_from_frame_with_bbox(self,
        img: np.ndarray,
        bbox,
        fmt: str = "xyxy",          # "xyxy" (xmin,ymin,xmax,ymax) or "xywh" (x,y,w,h)
        normalized: bool = False,   # True if bbox values are in [0,1] relative to width/height
        margin: float = 0.0,        # extra border around the face; if normalized, treat as ratio of diag
        square: bool = False       # pad to a square crop
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

    
    def prepare_quality_face(self,face_rgb, min_size=120, min_blur=80, upscale_to=320, sharpen_amount=1.35,blur_sigma=1.0,apply_clahe=True):
        """
        Takes an RGB face crop and returns an enhanced quality face image or None.

        Expected input:
            face_rgb: np.ndarray, RGB, uint8, shape (H, W, 3)

        Returns:
            enhanced RGB face crop or None
        """

        if face_rgb is None:
            return None

        if not isinstance(face_rgb, np.ndarray):
            return None

        if face_rgb.ndim != 3 or face_rgb.shape[2] != 3:
            return None

        if face_rgb.dtype != np.uint8:
            face_rgb = np.clip(face_rgb, 0, 255).astype(np.uint8)

        h, w = face_rgb.shape[:2]

        # reject very small faces
        if h < min_size or w < min_size:
            return None

        # reject dark/overexposed faces
        gray = cv2.cvtColor(face_rgb, cv2.COLOR_RGB2GRAY)
        mean_brightness = np.mean(gray)

        if mean_brightness < 40 or mean_brightness > 220:
            return None

        # reject blurry faces
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()

        if blur_score < min_blur:
            return None

        face_out = face_rgb.copy()

        # normalize lighting using CLAHE
        if apply_clahe:
            lab = cv2.cvtColor(face_out, cv2.COLOR_RGB2LAB)
            l, a, b = cv2.split(lab)

            clahe = cv2.createCLAHE(
                clipLimit=2.0,
                tileGridSize=(8, 8)
            )

            l = clahe.apply(l)
            lab = cv2.merge((l, a, b))
            face_out = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)

        # upscale to stable face-recognition size
        h, w = face_out.shape[:2]

        if min(h, w) < upscale_to:
            scale = upscale_to / min(h, w)

            face_out = cv2.resize(
                face_out,
                None,
                fx=scale,
                fy=scale,
                interpolation=cv2.INTER_CUBIC
            )

        # Mild sharpening
        blur = cv2.GaussianBlur(face_out, (0, 0), blur_sigma)

        face_out = cv2.addWeighted(face_out,sharpen_amount,blur,1 - sharpen_amount, 0)
        

        return face_out

# if __name__ == '__main__':
#     imge_detect = ImageObjectDetection()
#     imge_detect.init_model()
