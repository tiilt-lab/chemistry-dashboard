import logging
import threading
import numpy as np
import cv2
import os
import torch
import torch.nn.functional as F
from tqdm import tqdm
from .model.encoder.align_all_parallel import align_face
from .util import  get_video_crop_parameter
from moviepy.editor import *
from scipy.io import wavfile
import logging
import callbacks
import time

class VideoProcessor:
    def __init__(self,cartoon_model,video_queue,frame_queue,cartoon_image_queue,config,vid_img_dir,video_filename,aud_filename,sample_rate,depth,channels):
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
        self.lock = threading.Lock()
        
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
        with self.lock:
            device = "cpu" if self.cartoon_model.cpu else "cuda"
            kernel_1d = np.array([[0.125],[0.375],[0.375],[0.125]])
            for frame_index, frame in enumerate(frames):
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                #logging.info('variable name device has value  {0}'.format(device))
                if self.cartoon_model.scale_image:
                    try:
                        paras,h,w,scale = get_video_crop_parameter(cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY), self.cartoon_model.landmarkpredictor, self.cartoon_model.face_detector_model,self.cartoon_model.padding)
                        
                        if paras is not None:
                            if scale <= 0.75:
                                frame = cv2.sepFilter2D(frame, -1, kernel_1d, kernel_1d)
                            if scale <= 0.375:
                                frame = cv2.sepFilter2D(frame, -1, kernel_1d, kernel_1d) 

                            resized_frame = cv2.resize(frame, (w, h),interpolation=cv2.INTER_AREA)

                            for index, para in enumerate(paras):
                                top,bottom,left,right,lm = para
                                
                                face = resized_frame[top:bottom, left:right]       
                                try:
                                    with torch.no_grad():
                                        I = align_face(face,lm)
                                        I = self.cartoon_model.transform(I).unsqueeze(dim=0).to(device)
                                        s_w = self.cartoon_model.pspencoder(I)
                                        s_w = self.cartoon_model.vtoonify.zplus2wplus(s_w)
                                        if self.cartoon_model.vtoonify.backbone == 'dualstylegan':
                                            if self.cartoon_model.color_transfer:
                                                s_w = self.cartoon_model.exstyle
                                            else:
                                                s_w[:,:7] = self.cartoon_model.exstyle[:,:7]

                                        x = self.cartoon_model.transform(face).unsqueeze(dim=0).to(device)
                                        # parsing network works best on 512x512 images, so we predict parsing maps on upsmapled frames
                                        # followed by downsampling the parsing maps
                                        x_p = F.interpolate(self.cartoon_model.parsingpredictor(2*(F.interpolate(x, scale_factor=2, mode='bilinear', align_corners=False)))[0], 
                                                            scale_factor=0.5, recompute_scale_factor=False).detach()
                                        # we give parsing maps lower weight (1/16)
                                        inputs = torch.cat((x, x_p/16.), dim=1)
                                        # d_s has no effect when backbone is toonify
            
                                        y_tilde = self.cartoon_model.vtoonify(inputs, s_w.repeat(inputs.size(0), 1, 1), d_s = self.cartoon_model.style_degree)        
                                    
                                        y_tilde = torch.clamp(y_tilde, -1, 1)
                                        

                                        cartooned_image =((y_tilde[0].cpu().cpu().numpy().transpose(1, 2, 0) + 1.0) * 127.5).astype(np.uint8) 
                                        
                                        resized_img = cv2.resize(cartooned_image, (face.shape[1], face.shape[0]), interpolation = cv2.INTER_AREA)
                                        
                                        resized_frame[top:bottom, left:right,:] = resized_img

                                except Exception as e: 
                                    logging.info('exception occured while converting video to cartoon: {0}'.format(e))
                                    continue   

                            if savetopath is None:
                                success, encoded_frame =  cv2.imencode('.png', resized_frame)
                                if success:
                                    callbacks.post_cartoonized_image(self.config.auth_key,self.config.sessionId,self.config.deviceId, encoded_frame.tobytes())       
                            
                            if savetopath is not None:
                                cv2.imwrite(savetopath[frame_index],cv2.resize(resized_frame, (width,height), interpolation = cv2.INTER_AREA))
                        else:
                            if savetopath is not None:
                                cv2.imwrite(savetopath[frame_index],cv2.resize(frame, (width,height), interpolation = cv2.INTER_AREA))

                    except Exception as e: 
                        logging.info('exception occured in the entire convert image: {0}'.format(e))  
            if savetopath is not None:
                # Check if this was the final process of the transmission.
                self.running_processes -= 1
                if (not self.running) and self.running_processes == 0 and self.video_queue.empty():
                    logging.info('i eventually called complete_callback from convert_image')
                    self.__complete_callback()  
                    # logging.info('i am done with the lock')           
      

    def processing(self):
        logging.info('frame cartoonization thread started for {0}.'.format(self.config.auth_key))
        frame_processing_thread = None
        while self.running or not self.video_queue.empty():
            try:
                subclip_frames = None if self.video_queue.empty() else self.video_queue.get(block=False)
            
                if subclip_frames is not None:
                    subclib_frame_count = 0
                    frame_batch = []
                    for frame in subclip_frames:
                        subclib_frame_count =  subclib_frame_count + 1
                        # if frame_shape[1] > frame_shape[0]:
                        #     dim = (500,375)
                        # else:
                        #      dim = (375,500)   
                        frame = cv2.resize(frame, (500,375),interpolation=cv2.INTER_AREA)
                        self.frame_array.append(frame)
                        if self.frame_count % 29 == 0:
                            frame_batch.append(frame)
                            if (len(frame_batch) >= 9):
                                frame_processing_thread = threading.Thread(target=self.convert_image, args=(frame_batch,None,500,375))
                                frame_processing_thread.daemon = True
                                frame_processing_thread.start()
                                frame_batch = []
                                

                        self.frame_count = self.frame_count + 1  

                        # we just need 290 frames of the 10 sec chunks, and break if the frames capture  is more than 290    
                        if  subclib_frame_count > 300:
                            break

            
            except Exception as e:
                logging.warning('Exception thrown while extracting image subclib {0} {1}'.format(e, self.config.auth_key))

        logging.info('frame cartoonization thread stopped for {0}.'.format(self.config.auth_key))

        # end the tr
        if frame_processing_thread is not None:
            frame_processing_thread.join()
        # convert all image to cartoon and save
        Post_frame_batch = []
        post_frame_name = []
        for index,  s_frame in enumerate(self.frame_array):
            Post_frame_batch.append(s_frame)
            post_frame_name.append(os.path.join(self.vid_img_dir, "{0}.{1}".format(index+1,'png')))
            if (len(Post_frame_batch) >= 20):
                self.running_processes += 1
                save_frame_thread = threading.Thread(target=self.convert_image, args=(Post_frame_batch,post_frame_name,500,375))
                save_frame_thread.daemon = True
                save_frame_thread.start()
                Post_frame_batch =  [] 
                post_frame_name = []     
     
        # logging.info('i eventually called complete_callback')
        # self.__complete_callback() 
        logging.info('frame cartoonization thread stopped for {0}.'.format(self.config.auth_key))
          