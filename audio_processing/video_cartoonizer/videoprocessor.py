import logging
import threading
import numpy as np
import cv2
import os
import dlib
import torch
from torchvision import transforms
import torch.nn.functional as F
from tqdm import tqdm
from .model.vtoonify import VToonify
from .model.bisenet.model import BiSeNet
from .model.encoder.align_all_parallel import align_face
from .util import save_image, load_image, visualize, load_psp_standalone, get_video_crop_parameter, tensor2cv2
from moviepy.editor import *
from scipy.io import wavfile
import logging

class VideoProcessor:
    def __init__(self,video_queue,config,vid_img_dir,video_filename,aud_filename,sample_rate,depth,channels):
        self.config = config
        self.video_queue = video_queue
        self.vid_img_dir = vid_img_dir
        self.dat_filename = aud_filename + '.dat'
        self.wav_filename = aud_filename + '.wav'
        self.cart_vid = video_filename+'_caart'+'.mp4'
        self.depth = depth
        self.channels = channels
        self.sample_rate = sample_rate
        self.frame_count = 1
        self.running_processes = 0
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.style_id = 26
        self.style_degree = 0.5
        self.color_transfer = False
        self.ckpt = os.path.join( self.base_path,'checkpoint/vtoonify_d_cartoon/vtoonify_s_d.pt')
        self.scale_image = True
        self.style_encoder_path = os.path.join(self.base_path,'checkpoint/encoder.pt')
        self.exstyle_path =None
        self.faceparsing_path = os.path.join( self.base_path,'checkpoint/faceparsing.pth')
        self.cpu = False
        self.backbone = 'dualstylegan' #"dualstylegan | toonify"
        self.padding = [120,120,120,120]
        self.batch_sizet = 4
        self.lock = threading.Lock()
        

    def initialize(self):
       
        if not os.path.exists(self.vid_img_dir):
            os.mkdir(self.vid_img_dir)
        if self.exstyle_path is None:
            self.exstyle_path = os.path.join( self.base_path,'checkpoint/vtoonify_d_cartoon', 'exstyle_code.npy')

        self.scale_image = True
        device = "cpu" if self.cpu else "cuda"
    
        self.transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.5, 0.5, 0.5],std=[0.5,0.5,0.5]),])
    
        self.vtoonify = VToonify(backbone = self.backbone)
        self.vtoonify.load_state_dict(torch.load(self.ckpt, map_location=lambda storage, loc: storage)['g_ema'])
        self.vtoonify.to(device)
        self.parsingpredictor = BiSeNet(n_classes=19)
        self.parsingpredictor.load_state_dict(torch.load(self.faceparsing_path, map_location=lambda storage, loc: storage))
        self.parsingpredictor.to(device).eval()

        modelname = os.path.join( self.base_path,'checkpoint/shape_predictor_68_face_landmarks.dat')
        self.face_detector_model = os.path.join( self.base_path,'checkpoint/mmod_human_face_detector.dat')

        if not os.path.exists(modelname):
            import wget, bz2
            wget.download('http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2', modelname+'.bz2')
            zipfile = bz2.BZ2File(modelname+'.bz2')
            data = zipfile.read()
            open(modelname, 'wb').write(data) 
        self.landmarkpredictor = dlib.shape_predictor(modelname)

        self.pspencoder = load_psp_standalone(self.style_encoder_path, device)

        if self.backbone == 'dualstylegan':
            self.exstyles = np.load(self.exstyle_path, allow_pickle='TRUE').item()
            stylename = list(self.exstyles.keys())[self.style_id]
            self.exstyle = torch.tensor(self.exstyles[stylename]).to(device)
            with torch.no_grad(): 
                self.exstyle = self.vtoonify.zplus2wplus(self.exstyle)    

    def start(self):
        self.running = True
        self.vid_pro_thread = threading.Thread(target=self.processing, name="vdeo-data-cartoonization")
        self.vid_pro_thread.daemon = True
        self.vid_pro_thread.start()
        

    def stop(self):
        self.running = False

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


    def convert_image(self,frame,savetopath,width,height):
        with self.lock:
            logging.info('i have the lock')
            device = "cpu" if self.cpu else "cuda"
            kernel_1d = np.array([[0.125],[0.375],[0.375],[0.125]])
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            #logging.info('variable name device has value  {0}'.format(device))
            if self.scale_image:
                try:
                    paras,h,w,scale = get_video_crop_parameter(cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY), self.landmarkpredictor, self.face_detector_model,self.padding)
                    
                    if paras is not None:
                        if scale <= 0.75:
                            frame = cv2.sepFilter2D(frame, -1, kernel_1d, kernel_1d)
                        if scale <= 0.375:
                            frame = cv2.sepFilter2D(frame, -1, kernel_1d, kernel_1d) 

                        resized_frame = cv2.resize(frame, (w, h),interpolation=cv2.INTER_AREA)

                        for index, para in enumerate(paras):
                            top,bottom,left,right = para
                            
                            face = resized_frame[top:bottom, left:right] #cv2.resize(frame, (w, h),interpolation=cv2.INTER_AREA)[top:bottom, left:right]        
                            try:
                                with torch.no_grad():
                                    I = align_face(face,self.landmarkpredictor,self.face_detector_model)
                                    I = self.transform(I).unsqueeze(dim=0).to(device)
                                    s_w = self.pspencoder(I)
                                    s_w = self.vtoonify.zplus2wplus(s_w)
                                    if self.vtoonify.backbone == 'dualstylegan':
                                        if self.color_transfer:
                                            s_w = self.exstyle
                                        else:
                                            s_w[:,:7] = self.exstyle[:,:7]

                                    x = self.transform(face).unsqueeze(dim=0).to(device)
                                    # parsing network works best on 512x512 images, so we predict parsing maps on upsmapled frames
                                    # followed by downsampling the parsing maps
                                    x_p = F.interpolate(self.parsingpredictor(2*(F.interpolate(x, scale_factor=2, mode='bilinear', align_corners=False)))[0], 
                                                        scale_factor=0.5, recompute_scale_factor=False).detach()
                                    # we give parsing maps lower weight (1/16)
                                    inputs = torch.cat((x, x_p/16.), dim=1)
                                    # d_s has no effect when backbone is toonify
        
                                    y_tilde = self.vtoonify(inputs, s_w.repeat(inputs.size(0), 1, 1), d_s = self.style_degree)        
                                
                                    y_tilde = torch.clamp(y_tilde, -1, 1)
                                    

                                    cartooned_image =((y_tilde[0].cpu().cpu().numpy().transpose(1, 2, 0) + 1.0) * 127.5).astype(np.uint8) 
                                    
                                    resized_img = cv2.resize(cartooned_image, (face.shape[1], face.shape[0]), interpolation = cv2.INTER_AREA)
                                    
                                    resized_frame[top:bottom, left:right,:] = resized_img

                            except Exception as e: 
                                logging.info('exception occured while converting video to cartoon: {0}'.format(e))
                                continue   

                        cv2.imwrite(savetopath,cv2.resize(resized_frame, (width,height), interpolation = cv2.INTER_AREA))
                        #logging.info('cartoonized image saved to : {}'.format(savetopath)) 
                    else:
                        cv2.imwrite(savetopath,cv2.resize(frame, (width,height), interpolation = cv2.INTER_AREA))
                        #logging.info('original image saved to : {}'.format(savetopath)) 

                except Exception as e: 
                    logging.info('exception occured in the entire convert image: {0}'.format(e))  

            # Check if this was the final process of the transmission.
            self.running_processes -= 1
            if (not self.running) and self.running_processes == 0:
                logging.info('i eventually called complete_callback from convert_image')
                self.__complete_callback()  
            logging.info('i am done with the lock')           

    def processing(self):
        logging.info('frame cartoonization thread started for {0}.'.format(self.config.auth_key))
       
        while self.running:
            try:
                subclip_frames = None if self.video_queue.empty() else self.video_queue.get(block=False)
                
                if subclip_frames is not None:
                    logging.info('sublic frames is {0}'.format(subclip_frames))
                    for frame in subclip_frames:
                        frame = cv2.resize(frame, (500,375),interpolation=cv2.INTER_AREA)
                        frame_name = os.path.join(self.vid_img_dir, "{0}".format(self.frame_count))
                        self.running_processes += 1
                        #self.convert_image(frame,frame_name+".png",500,375)
                        transcript_thread = threading.Thread(target=self.convert_image, args=(frame,frame_name+".png",500,375))
                        transcript_thread.daemon = True
                        transcript_thread.start()
                        self.frame_count = self.frame_count + 1
            except Exception as e:
                logging.warning('Exception thrown while extracting video byte data {0} {1}'.format(e, self.config.auth_key))

     
        logging.info('frame cartoonization thread stopped for {0}.'.format(self.config.auth_key))
          