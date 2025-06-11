import argparse
import time
from pathlib import Path
import os
import cv2
import torch
import torch.backends.cudnn as cudnn
from numpy import random
import sys
import numpy as np
import pickle
import supervision as sv
from ultralytics import YOLO
from ultralytics.engine.results import Results
sys.path.insert(0,'./yolo_head')
print(sys.path)
from yolo_head.models.experimental import attempt_load
from yolo_head.utils.datasets import LoadStreams, LoadImages, LoadImageDataset
from yolo_head.utils.general import check_img_size, check_requirements, check_imshow, non_max_suppression, apply_classifier, \
    scale_coords, xyxy2xywh, strip_optimizer, set_logging, increment_path
from yolo_head.utils.plots import plot_one_box
from yolo_head.utils.torch_utils import select_device, load_classifier, time_synchronized


def detect(opt,save_img=False):
    source, weights, view_img, save_txt, imgsz, root_path,head_width_threshold,batch_size = opt.source, opt.weights, opt.view_img, opt.save_txt, opt.img_size, opt.root_path,opt.heads_width_threshold,opt.batch_size
    save_txt = True
    webcam = False
    tracker = sv.ByteTrack(frame_rate = 29)#track_activation_threshold=0.2,lost_track_buffer=30,minimum_matching_threshold=0.70,minimum_consecutive_frames=1
    
    # Directories
    save_dir = Path(root_path+'/data/demo')  # increment run
    # (save_dir / 'labels' if save_txt else save_dir).mkdir(parents=True, exist_ok=True)  # make dir
    # Initialize
    set_logging()
    device = select_device(opt.device)
    half = device.type != 'cpu'  # half precision only supported on CUDA

    # Load model
    model = attempt_load(weights[0], map_location=device)  # load FP32 model for head and person detection
    model2 = attempt_load(weights[1], map_location=device)  # load FP32 model for person and other object detection

    #prep model 1
    stride = int(model.stride.max())  # model stride
    imgsz = check_img_size(imgsz, s=stride)  # check img_size
    if half:
        model.half()  # to FP16 

   
   #prep model 2
    stride2 = int(model2.stride.max())  # model stride
    # print(stride2)
    imgsz2 = check_img_size(imgsz, s=stride2)  # check img_size
    if half:
        model2.half()  # to FP16   


    # Run inference
    if device.type != 'cpu':
        model(torch.zeros(batch_size, 3, imgsz, imgsz).to(device).type_as(next(model.parameters())))  # run once
   
    # Run inference
        model2(torch.zeros(batch_size, 3, imgsz2, imgsz2).to(device).type_as(next(model2.parameters())))  # run once
        # sudo_img =torch.zeros((batch_size, 3, imgsz2, imgsz2), device=device)
        # _ = model2(sudo_img.half() if half else sudo_img) if device.type != 'cpu' else None  # run once # model2(torch.zeros(1, 3, imgsz2, imgsz2).to(device).type_as(next(model.parameters())))  # run once
    
    # Second-stage classifier
    classify = False
    if classify:
        modelc = load_classifier(name='resnet101', n=2)  # initialize
        modelc.load_state_dict(torch.load('weights/resnet101.pt', map_location=device)['model']).to(device).eval()

    # Set Dataloader
    vid_path, vid_writer = None, None
    if webcam:
        view_img = check_imshow()
        cudnn.benchmark = True  # set True to speed up constant image size inference
        dataset = LoadStreams(source, img_size=imgsz, stride=stride)
    else:
        save_img = True
        val_dataset = LoadImageDataset(source, img_size=imgsz, stride=stride)
        dataset = torch.utils.data.DataLoader(dataset=val_dataset,
                                               batch_size=batch_size,
                                               shuffle=False,
                                               num_workers=0)

    # Get names  for pred 1
    names_model_1 = model.module.names if hasattr(model, 'module') else model.names
    # Get names for pred 2
    names= model2.module.names if hasattr(model2, 'module') else model2.names
    #change the value of the name in key 1 to the value of name in names_model_1[1]
    names[1] = names_model_1[1]

    if  isinstance(names,list):
         names_V_K = {}
         names_K_V = {}
         for k, v in enumerate(names):
            names_V_K[v] =  k 
            names_K_V[k] =  v
    elif isinstance(names,dict):
        names_K_V = names
        names_V_K = {v: k for k, v in names.items()}

    colors = [[random.randint(0, 255) for _ in range(3)] for _ in range(len(names))]
 
    t0 = time.time()
    print(names_K_V)

    # tracks = {"head": []}
    accumulator = {'head':dict(), 'other_objects':dict()}
    all_frames = []
    for val_batch, (path, img, im0s) in enumerate(dataset): #path, img, im0s, vid_cap in dataset:
        # all_frames.extend(im0s)
        # img = torch.from_numpy(img).to(device)
        img = img.to(device)
        img = img.half() if half else img.float()  # uint8 to fp16/32
        img /= 255.0  # 0 - 255 to 0.0 - 1.0
        if img.ndimension() == 3:
            img = img.unsqueeze(0)

        # Inference
        t1 = time_synchronized()
        pred = model(img, augment=opt.augment)[0]
        pred2 = model2(img, augment=opt.augment)[0]
        
        # Apply NMS
        pred = non_max_suppression(pred, opt.model1_conf_thres, opt.model1_iou_thres, classes=opt.classes, agnostic=opt.agnostic_nms)
        pred2 = non_max_suppression(pred2, opt.model2_conf_thres, opt.model2_iou_thres, classes=opt.classes, agnostic=opt.agnostic_nms)
        t2 = time_synchronized()

        # Apply Classifier
        if classify:
            pred = apply_classifier(pred, modelc, img, im0s)
            pred2 = apply_classifier(pred2, modelc, img, im0s)


        

        #combine pred and pred 2, filter out all cls 0 (person) detection for pred. keep only head (cls 1) detection 
        # and filter out all cls 1 (bicycle)  detection  pred 2
        combined_pred = [torch.cat((pred[i][pred[i][:,5] >= 1],pred2[i][pred2[i][:,5] != 1])) for i in range(len(pred2))]
        
        for i, det in enumerate(combined_pred):  # detections per image
            face_bbox = [] # accumulate all the faces detected in the frame
            other_objects = [] #accumulate other including faces detected in the frame
            if webcam:  # batch_size >= 1
                p, s, im0, frame = path[i], '%g: ' % i, im0s[i].copy(), dataset.count
            else:
                p, s, im0 = path[i], '', im0s[i].numpy()

            all_frames.append(im0)
            p = Path(p)  # to Path
            save_path = str(save_dir / p.name)  # img.jpg
            # txt_path = str(save_dir / 'labels' / p.stem) + ('' if dataset.mode == 'image' else f'_{frame}')  # img.txt
            txt_path = str(save_dir /'heads')
            s += '%gx%g ' % img.shape[2:]  # print string
            gn = torch.tensor(im0.shape)[[1, 0, 1, 0]]  # normalization gain whwh
            if len(det):
                # Rescale boxes from img_size to im0 size
                det[:, :4] = scale_coords(img.shape[2:], det[:, :4], im0.shape).round()
                
                no_of_head = 0
                for *xyxy, conf, cls in reversed(det):
                    if cls == names_V_K.get('head', None):
                        no_of_head = no_of_head+1
                    
                

                # print(det[det[:,5] == 1])
                result = Results(orig_img=im0, path=p, names=names_K_V, boxes=det)
                # Tracking Mechanism
                detection_supervision = sv.Detections.from_ultralytics(result)
                detection_with_tracks = tracker.update_with_detections(detection_supervision)
                # tracks["head"].append({})
               
                # Write results
                no_of_head = 0
                for frame_detection in detection_with_tracks:
                    bbox = frame_detection[0].tolist()
                    confs = frame_detection[2]
                    clss = frame_detection[3]
                    person_id = frame_detection[4]
                    if clss == names_V_K.get('head', None):
                        no_of_head = no_of_head+1
                    # print(frame_detection)
                    accumulate_head_track(bbox,confs,clss,person_id,names_V_K,names_K_V,accumulator,im0,p,colors,root_path)
                
                

                      
                                
            
            print(f'{s}Done. ({t2 - t1:.3f}s)')

    print(f'Done. ({time.time() - t0:.3f}s)')
    return all_frames,accumulator

def accumulate_head_track(bbox,conf,cls,person_id,names_V_K,names_K_V,accumulator,im0,p,colors,root_path):
    if cls == names_V_K.get('head', None): #only track the head 
        #skip faces that are too small to be part of the participants
        # if int(bbox[2]) - int(bbox[0]) <= head_width_threshold and int(bbox[3]) - int(bbox[1]) <= head_width_threshold:
        #     continue
        if person_id in accumulator['head']:
            accumulator['head'][person_id].append([int(p.stem),person_id,int(bbox[0]),int(bbox[1]),int(bbox[2]),int(bbox[3]) ])
        else:
            accumulator['head'][person_id] = [[int(p.stem),person_id,int(bbox[0]),int(bbox[1]),int(bbox[2]),int(bbox[3])]]    

        if int(p.stem) in accumulator['other_objects']:
            accumulator['other_objects'][int(p.stem)].append([cls,names_K_V[int(cls)],person_id,int(bbox[0]),int(bbox[1]),int(bbox[2]),int(bbox[3]) ])
        else:
            accumulator['other_objects'][int(p.stem)] = [[cls,names_K_V[int(cls)],person_id,int(bbox[0]),int(bbox[1]),int(bbox[2]),int(bbox[3]) ]]    
        
        # tracks["head"][i][track_id] = {"bbox": bbox}
        label = f'{names_K_V[int(cls)] } {conf:.2f}'
        plot_one_box([int(bbox[0]),int(bbox[1]),int(bbox[2]),int(bbox[3])], im0, label=label, color=colors[int(cls)], line_thickness=3)
       
        cv2.putText(im0, str(person_id), (int(bbox[0]), int(bbox[3]) + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.9,(255,0,0) , 2)#colors[int(cls)]
        # cv2.imwrite(root_path+'/data/demo/annotated_frames/'+str(p.stem)+'.jpg' , im0)
        # face_bbox.append([int(bbox[0]),int(bbox[1]),int(bbox[2]),int(bbox[3])])
        # other_objects.append([int(cls),int(bbox[0]),int(bbox[1]),int(bbox[2]),int(bbox[3])]) 
    #accumulate all other objects except person    
    elif cls != names_V_K.get('person', None):
        if int(p.stem) in accumulator['other_objects']:
            accumulator['other_objects'][int(p.stem)].append([cls,names_K_V[int(cls)],person_id,int(bbox[0]),int(bbox[1]),int(bbox[2]),int(bbox[3]) ])
        else:
            accumulator['other_objects'][int(p.stem)] = [[cls,names_K_V[int(cls)],person_id,int(bbox[0]),int(bbox[1]),int(bbox[2]),int(bbox[3]) ]]  
            


def det_head(img,root_path):
    parser = argparse.ArgumentParser()
    parser.add_argument('--weights', nargs='+', type=str, default='crowdhuman_yolov5m.pt', help='model.pt path(s)')
    parser.add_argument('--source', type=str, default=img, help='source')  # file/folder, 0 for webcam
    parser.add_argument('--root-path', type=str, default=root_path, help='source') #root path
    parser.add_argument('--img-size', type=int, default=640, help='inference size (pixels)')
    parser.add_argument('--model1-conf-thres', type=float, default=0.25, help='object confidence threshold')
    parser.add_argument('--model1-iou-thres', type=float, default=0.45, help='IOU threshold for NMS')
    parser.add_argument('--model2-conf-thres', type=float, default=0.4, help='object confidence threshold')
    parser.add_argument('--model2-iou-thres', type=float, default=0.5, help='IOU threshold for NMS')
    parser.add_argument('--device', default='', help='cuda device, i.e. 0 or 0,1,2,3 or cpu')
    parser.add_argument('--view-img', action='store_true', help='display results')
    parser.add_argument('--save-txt', action='store_true', help='save results to *.txt')
    parser.add_argument('--save-conf', action='store_true', help='save confidences in --save-txt labels')
    parser.add_argument('--classes', nargs='+', type=int, help='filter by class: --class 0, or --class 0 2 3')
    parser.add_argument('--agnostic-nms', action='store_true', help='class-agnostic NMS')
    parser.add_argument('--augment', action='store_true', help='augmented inference')
    parser.add_argument('--update', action='store_true', help='update all models')
    parser.add_argument('--project', default='runs/detect', help='save results to project/name')
    parser.add_argument('--name', default='exp', help='save results to project/name')
    parser.add_argument('--exist-ok', action='store_true', help='existing project/name ok, do not increment')
    parser.add_argument('--person', action='store_true', help='displays only person')
    parser.add_argument('--heads', action='store_true', help='displays only person')
    parser.add_argument('--heads-width-threshold', type=int, default=50, help='head box width should be greater than this threshold')
    parser.add_argument('--batch-size', type=int, default=40,help='the batch size of images to tom processed at once')

    opt = parser.parse_args()
    opt.heads = True
    opt.person = True
    base_path = os.path.dirname(os.path.abspath(__file__))
    # opt.weights = os.path.join(base_path,opt.weights) 
    opt.weights = [os.path.join(base_path,opt.weights),os.path.join(base_path,'yolov4-p7.pt')
                   ,os.path.join(base_path,'yolov8n.pt'),os.path.join(base_path,'yolov8n-face.pt')
                   ,os.path.join(base_path,'yolov5su.pt')] 
    print(opt)

    with torch.no_grad():
        if opt.update:  # update all models (to fix SourceChangeWarning)
            for opt.weights in ['yolov5s.pt', 'yolov5m.pt', 'yolov5l.pt', 'yolov5x.pt']:
                detect(opt)
                strip_optimizer(opt.weights)
        else:
            # use_yolo_ultralytic(opt)
           all_frames,accumulator = detect(opt)
    return all_frames,accumulator
