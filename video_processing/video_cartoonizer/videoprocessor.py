import logging
import threading
import numpy as np
import cv2
import os
import torch
import torch.nn.functional as F
from tqdm import tqdm
from .model.encoder.align_all_parallel import align_face
from .util import  get_video_crop_parameter,get_facial_landmark,tensor2cv2
from moviepy.editor import *
from scipy.io import wavfile
import logging
import copy
import json

class VideoProcessor:
    def __init__(self,cartoon_model,facial_emotion_detector,image_object_detection,attention_detection, \
                video_queue,frame_queue,cartoon_image_queue,config,vid_img_dir,video_filename,aud_filename,sample_rate,depth,channels):
        
        self.config = config
        self.video_queue = video_queue
        self.frame_queue = frame_queue
        self.cartoon_image_queue = cartoon_image_queue
        self.vid_img_dir = vid_img_dir
        self.dat_filename = aud_filename + '.dat'
        self.wav_filename = aud_filename + '.wav'
        self.cart_vid = video_filename+'_caart'+'.mp4'
        self.depth = depth
        self.channels = channels
        self.sample_rate = sample_rate
        self.frame_count = 1
        self.running_processes = 0
        self.frame_array = []
        self.cartoon_model = cartoon_model
        self.facial_emotion_detector = facial_emotion_detector
        self.image_object_detection = image_object_detection
        self.attention_detection = attention_detection
        self.lock = threading.Lock()
        self.batch_size = cartoon_model.batch_size
        self.batch_track = 1
        self.first_valid_frame = True
        self.paras = None
        self.h = None
        self.w = None
        self.scale= None
        self.s_w = []
        self.frame_batch = []
        self.web_socket_connection = None

        self.object_of_interest = [1,63,67,68]
        self.persons_attention_track = {}
        self.person_object_focus_track = {}
        self.object_by_id_in_frame_track = {}
        self.object_by_class_track = {}
        self.person_attention_focus_count = {}

        self.attention_detection.set_persistent_variables(self.object_of_interest,self.persons_attention_track,self.person_object_focus_track, \
                                                          self.object_by_id_in_frame_track,self.object_by_class_track, self.person_attention_focus_count)
        
        if self.cartoon_model.video and self.cartoon_model.parsing_map_path is not None:
            self.x_p_hat = torch.tensor(np.load(self.cartoon_model.parsing_map_path))

        self.non_cartoon_emotions = {"Extremely afraid":0,"Extremely alarmed":0,"Extremely annoyed":0,"Extremely aroused":0,"Extremely astonished":0,
                        "Extremely bored":0,"Extremely calm":0,"Extremely content":0,"Extremely delighted":0,"Extremely depressed":0,
                        "Extremely distressed":0,"Extremely droopy":0,"Extremely excited":0,"Extremely frustrated":0,"Extremely gloomy":0,
                        "Extremely happy":0,"Extremely miserable":0,"Extremely pleased":0,"Extremely sad":0,"Extremely satisfied":0,
                        "Extremely serene":0,"Extremely sleepy":0,"Extremely tensed":0,"Extremely tired":0,"Moderately afraid":0,
                        "Moderately alarmed":0,"Moderately annoyed":0,"Moderately aroused":0,"Moderately astonished":0,"Moderately bored":0,
                        "Moderately calm":0,"Moderately content":0,"Moderately delighted":0,"Moderately depressed":0,"Moderately distressed":0,
                        "Moderately droopy":0,"Moderately excited":0,"Moderately frustrated":0,"Moderately gloomy":0,"Moderately happy":0,"Moderately miserable":0,
                        "Moderately pleased":0,"Moderately sad":0,"Moderately satisfied":0,"Moderately serene":0,"Moderately sleepy":0,"Moderately tensed":0,
                        "Moderately tired":0," Neutral":0,"Slightly afraid":0,"Slightly alarmed":0,"Slightly annoyed":0,"Slightly aroused":0,"Slightly astonished":0,
                        "Slightly bored":0,"Slightly calm":0,"Slightly content":0,"Slightly delighted":0,"Slightly depressed":0,"Slightly distressed":0,
                        "Slightly droopy":0,"Slightly excited":0,"Slightly frustrated":0,"Slightly gloomy":0,"Slightly happy":0,"Slightly miserable":0,"Slightly pleased":0,
                        "Slightly sad":0,"Slightly satisfied":0,"Slightly serene":0,"Slightly sleepy":0,"Slightly tensed":0,"Slightly tired":0,"Very afraid":0,
                        "Very alarmed":0,"Very annoyed":0,"Very aroused":0,"Very astonished":0,"Very bored":0,"Very calm":0,"Very content":0,"Very delighted":0,
                        "Very depressed":0,"Very distressed":0,"Very droopy":0,"Very excited":0,"Very frustrated":0,"Very gloomy":0,"Very happy":0,"Very miserable":0,
                        "Very pleased":0,"Very sad":0,"Very satisfied":0,"Very serene":0,"Very sleepy":0,"Very tensed":0,"Very tired":0}
        self.cartoon_emotions = {"Extremely afraid":0,"Extremely alarmed":0,"Extremely annoyed":0,"Extremely aroused":0,"Extremely astonished":0,
                        "Extremely bored":0,"Extremely calm":0,"Extremely content":0,"Extremely delighted":0,"Extremely depressed":0,
                        "Extremely distressed":0,"Extremely droopy":0,"Extremely excited":0,"Extremely frustrated":0,"Extremely gloomy":0,
                        "Extremely happy":0,"Extremely miserable":0,"Extremely pleased":0,"Extremely sad":0,"Extremely satisfied":0,
                        "Extremely serene":0,"Extremely sleepy":0,"Extremely tensed":0,"Extremely tired":0,"Moderately afraid":0,
                        "Moderately alarmed":0,"Moderately annoyed":0,"Moderately aroused":0,"Moderately astonished":0,"Moderately bored":0,
                        "Moderately calm":0,"Moderately content":0,"Moderately delighted":0,"Moderately depressed":0,"Moderately distressed":0,
                        "Moderately droopy":0,"Moderately excited":0,"Moderately frustrated":0,"Moderately gloomy":0,"Moderately happy":0,"Moderately miserable":0,
                        "Moderately pleased":0,"Moderately sad":0,"Moderately satisfied":0,"Moderately serene":0,"Moderately sleepy":0,"Moderately tensed":0,
                        "Moderately tired":0," Neutral":0,"Slightly afraid":0,"Slightly alarmed":0,"Slightly annoyed":0,"Slightly aroused":0,"Slightly astonished":0,
                        "Slightly bored":0,"Slightly calm":0,"Slightly content":0,"Slightly delighted":0,"Slightly depressed":0,"Slightly distressed":0,
                        "Slightly droopy":0,"Slightly excited":0,"Slightly frustrated":0,"Slightly gloomy":0,"Slightly happy":0,"Slightly miserable":0,"Slightly pleased":0,
                        "Slightly sad":0,"Slightly satisfied":0,"Slightly serene":0,"Slightly sleepy":0,"Slightly tensed":0,"Slightly tired":0,"Very afraid":0,
                        "Very alarmed":0,"Very annoyed":0,"Very aroused":0,"Very astonished":0,"Very bored":0,"Very calm":0,"Very content":0,"Very delighted":0,
                        "Very depressed":0,"Very distressed":0,"Very droopy":0,"Very excited":0,"Very frustrated":0,"Very gloomy":0,"Very happy":0,"Very miserable":0,
                        "Very pleased":0,"Very sad":0,"Very satisfied":0,"Very serene":0,"Very sleepy":0,"Very tensed":0,"Very tired":0}
        
        logging.info('vid directory is {0}'.format(self.vid_img_dir))
        if not os.path.exists(self.vid_img_dir):
            os.mkdir(self.vid_img_dir)
        
        
    def start(self):
        self.running = True
        self.vid_pro_thread = threading.Thread(target=self.processing, name="vdeo-data-cartoonization")
        self.vid_pro_thread.daemon = True
        self.vid_pro_thread.start()
        

    def stop(self):
        self.running = False
        self.vid_pro_thread.join()

    def add_websocket_connection(self,web_socket):
        self.web_socket_connection = web_socket

    def send_json(self, message):
        payload = json.dumps(message).encode('utf8')
        self.web_socket_connection.sendMessage(payload, isBinary = False)
        
    def __complete_callback(self):
        try:
            self.convert_dat_to_wav()
            sortedfiles = [int(f.split(".")[0]) for f in os.listdir(self.vid_img_dir)]
            sortedfiles.sort()
            file_path = [os.path.join(self.vid_img_dir,str(fp)+".png") for fp in sortedfiles] 
            video = ImageSequenceClip(file_path,fps=29)
            audio_clip = AudioFileClip(self.wav_filename)
            new_audio_clip = CompositeAudioClip([audio_clip])
            video.audio = new_audio_clip
            video.write_videofile(self.cart_vid)

            for file in os.listdir(self.vid_img_dir):
                os.remove(os.path.join(self.vid_img_dir,file))
            os.rmdir(self.vid_img_dir)
            os.remove(self.wav_filename)
        
        except Exception as e:
            logging.info('Unable to build cartoonized frames into video or delete video file: {0}'.format(e))



    def convert_dat_to_wav(self):
        with open(self.dat_filename, "rb") as f:
            all_data = f.read()
            all_data = np.frombuffer(all_data, np.float32 if self.depth == 4 else np.int16, -1)
            chunk_length = int(len(all_data) / self.channels)
            all_data = np.reshape(all_data, (chunk_length, self.channels))
        wavfile.write(self.wav_filename, self.sample_rate, all_data)
        os.remove(self.dat_filename)


    def convert_image(self,frames,savetopath,width,height):
        device = "cpu" if self.cartoon_model.cpu else "cuda"
        kernel_1d = np.array([[0.125],[0.375],[0.375],[0.125]])
        frame_faces_accumulator = []
        faces_in_frame = {}
        processed_frame_track = []
        for frame_index, frame in enumerate(frames):
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            if self.cartoon_model.scale_image:
                try:
                    if self.first_valid_frame:
                        self.paras,self.h,self.w,self.scale = get_video_crop_parameter(cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY), self.cartoon_model.landmarkpredictor, self.cartoon_model.face_detector_model,self.cartoon_model.padding)
                        if self.paras is not None:
                            if self.scale <= 0.75:
                                frame = cv2.sepFilter2D(frame, -1, kernel_1d, kernel_1d)
                            if self.scale <= 0.375:
                                frame = cv2.sepFilter2D(frame, -1, kernel_1d, kernel_1d) 

                            resized_frame = cv2.resize(frame, (self.w, self.h),interpolation=cv2.INTER_AREA)

                            for index, para in enumerate(self.paras):
                                top,bottom,left,right,lm,face_lm = para
                                face = resized_frame[top:bottom, left:right] 
                                
                                with torch.no_grad():
                                    I = align_face(face,lm)
                                    I = self.cartoon_model.transform(I).unsqueeze(dim=0).to(device)
                                    inner_s_w = self.cartoon_model.pspencoder(I)
                                    inner_s_w = self.cartoon_model.vtoonify.zplus2wplus(inner_s_w)
                                    if self.cartoon_model.vtoonify.backbone == 'dualstylegan':
                                        if self.cartoon_model.color_transfer:
                                            inner_s_w = self.cartoon_model.exstyle
                                        else:
                                            inner_s_w[:,:7] = self.cartoon_model.exstyle[:,:7]

                                    self.s_w.append(inner_s_w)
                                    #append a particular face across frames in the key corresponding to the paras index
                                    if index in faces_in_frame:
                                        faces_in_frame[index]+= [self.cartoon_model.transform(face).unsqueeze(dim=0).to(device)]
                                    else:
                                        faces_in_frame[index] = [self.cartoon_model.transform(face).unsqueeze(dim=0).to(device)]

                            # frame_faces_accumulator.append(torch.stack(faces))
                            processed_frame_track.append(resized_frame)
                            self.first_valid_frame = False
                    #this means the first valid frame have been detected and paras has value        
                    elif  self.paras is not None:
                        if self.scale <= 0.75:
                            frame = cv2.sepFilter2D(frame, -1, kernel_1d, kernel_1d)
                        if self.scale <= 0.375:
                            frame = cv2.sepFilter2D(frame, -1, kernel_1d, kernel_1d) 

                    resized_frame = cv2.resize(frame, (self.w, self.h),interpolation=cv2.INTER_AREA)
                    for index, para in enumerate(self.paras):
                        top,bottom,left,right,lm,face_lm = para
                        face = resized_frame[top:bottom, left:right] 

                        #append a particular face across frames in the key corresponding to the paras index
                        if index in faces_in_frame:
                            faces_in_frame[index]+= [self.cartoon_model.transform(face).unsqueeze(dim=0).to(device)]
                        else:
                            faces_in_frame[index] = [self.cartoon_model.transform(face).unsqueeze(dim=0).to(device)]
                        
                    processed_frame_track.append(resized_frame)
                        
                except Exception as e: 
                    logging.info('exception occured while converting video to cartoon: {0}'.format(e))
                    continue  
                           
        cartoonized_faces = [] 
        for key, face_across_frame in faces_in_frame.items():   
            x = torch.cat(face_across_frame, dim=0)
            with torch.no_grad():
                if self.cartoon_model.video and self.cartoon_model.parsing_map_path is not None:
                    len_frames = len(frame_faces_accumulator)     
                    x_p = self.x_p_hat[len_frames+1-x.size(0):len_frames+1].to(device)
                else:
                    x_p = F.interpolate(self.cartoon_model.parsingpredictor(2*(F.interpolate(x, scale_factor=2, mode='bilinear', align_corners=False)))[0], 
                                    scale_factor=0.5, recompute_scale_factor=False).detach()
                # we give parsing maps lower weight (1/16)
                inputs = torch.cat((x, x_p/16.), dim=1)
                # d_s has no effect when backbone is toonify

                y_tilde = self.cartoon_model.vtoonify(inputs, self.s_w[key].repeat(inputs.size(0), 1, 1), d_s = self.cartoon_model.style_degree)        
            
                y_tilde = torch.clamp(y_tilde, -1, 1)
                cartoonized_faces.append(y_tilde)                    

        reversed_face_across_frame = zip(*cartoonized_faces)

        for j, faces_in_frame in enumerate(reversed_face_across_frame):
            for k, cart_face in enumerate(faces_in_frame):
                i_top = self.paras[k][0]
                i_bottom = self.paras[k][1]
                i_left = self.paras[k][2]
                i_right = self.paras[k][3]
                H =  i_bottom - i_top
                W =  i_right - i_left
                cartooned_image = tensor2cv2(cart_face.cpu())
                # logging.info('shape of cartoon image {0} {1}'.format(cartooned_image.shape,(W,H)))
                # save_to = os.path.join(self.vid_img_dir, "{0}_{1}.{2}".format(j,k,'png'))
                # cv2.imwrite(save_to,cartooned_image)
                resized_img = cv2.resize(cartooned_image, (W, H), interpolation = cv2.INTER_AREA)
                processed_frame_track[j][i_top:i_bottom, i_left:i_right,:] = resized_img

            if savetopath is None:
                success, encoded_frame =  cv2.imencode('.jpeg', processed_frame_track[j])
                if success:
                    payload = encoded_frame.tobytes() #base64.b64encode() 
                    self.web_socket_connection.sendMessage(payload, isBinary = True)
                    # callbacks.post_cartoonized_image(self.config.auth_key,self.config.sessionId,self.config.deviceId, encoded_frame.tobytes())
                           
        
        if savetopath is not None:
            for i, processed_frame in enumerate(processed_frame_track):
                save_to = os.path.join(self.vid_img_dir, "{0}.{1}".format(i+1,'png'))
                cv2.imwrite(save_to,cv2.resize(processed_frame, (width,height), interpolation = cv2.INTER_AREA))

                  
    def processing(self):
        logging.info('frame cartoonization thread started for {0}.'.format(self.config.auth_key))
        frame_processing_thread = None
        while self.running or not self.video_queue.empty():
            try:
                subclip_frames = None if self.video_queue.empty() else self.video_queue.get(block=False)
            
                if subclip_frames is not None:
                    subclib_frame_count = 0
                    for frame in subclip_frames:
                        subclib_frame_count =  subclib_frame_count + 1
                        # if frame_shape[1] > frame_shape[0]:
                        #     dim = (500,375)
                        # else:
                        #      dim = (375,500)   
                        # frame = cv2.resize(frame, (500,375),interpolation=cv2.INTER_AREA)
                        self.frame_array.append(frame)
                        self.frame_batch.append(frame)
                        if (len(self.frame_batch) == self.batch_size):
                            logging.info('total appended per batch {0}'.format(len(self.frame_batch)))
                            frames_batch_copy = copy.deepcopy(self.frame_batch)
                            self.convert_image(self.frame_batch,None,500,375)

                            #start attention tracking
                            all_frames,face_object_detected = self.image_object_detection.detection(frames_batch_copy,self.batch_track)
                            self.attention_detection.attention_tracking(face_object_detected,all_frames)
                            self.frame_batch = []
                            self.batch_track+=1
                            logging.info('printing output of attentions')
                            logging.info(self.persons_attention_track)
                            payload = {'type': 'attention_data', 'data': self.persons_attention_track}
                            self.send_json(payload)

                                

                        self.frame_count = self.frame_count + 1  

                        # we just need 290 frames of the 10 sec chunks, and break if the frames capture  is more than 290    
                        if  subclib_frame_count > 300:
                            break

            
            except Exception as e:
                logging.warning('Exception thrown while extracting image subclib {0} {1}'.format(e, self.config.auth_key))

        logging.info('frame cartoonization thread stopped for {0}.'.format(self.config.auth_key))

        # Processing after session has ended (post hoc processing)
        if frame_processing_thread is not None:
            frame_processing_thread.join()
        # convert all image to cartoon and save
        Post_frame_batch = []
        post_frame_name = []
        for index,  s_frame in enumerate(self.frame_array):
            Post_frame_batch.append(s_frame)
            post_frame_name.append(os.path.join(self.vid_img_dir, "{0}.{1}".format(index+1,'png')))
            if (len(Post_frame_batch) == self.batch_size):
                self.running_processes += 1
                self.convert_image(Post_frame_batch,post_frame_name,500,375)
                Post_frame_batch =  [] 
                post_frame_name = []     
     
        # logging.info('i eventually called complete_callback')
        # self.__complete_callback() 
        logging.info('frame cartoonization thread stopped for {0}.'.format(self.config.auth_key))
          