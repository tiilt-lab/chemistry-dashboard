import os
import argparse
import numpy as np
import cv2
import dlib
import torch
from torchvision import transforms
import torch.nn.functional as F
from tqdm import tqdm
from .model.vtoonify import VToonify
from .model.bisenet.model import BiSeNet
from .model.encoder.align_all_parallel import align_face
from .util import save_image, load_image, visualize, load_psp_standalone, get_video_crop_parameter, tensor2cv2
import logging

class Videotoonify():
    def __init__(self):
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.parser = argparse.ArgumentParser(description="Style Transfer")
        #self.parser.add_argument("--content", type=str, default='./data/077436.jpg', help="path of the content image/video")
        self.parser.add_argument("--style_id", type=int, default=26, help="the id of the style image")
        self.parser.add_argument("--style_degree", type=float, default=0.5, help="style degree for VToonify-D")
        self.parser.add_argument("--color_transfer", action="store_true", help="transfer the color of the style")
        self.parser.add_argument("--ckpt", type=str, default=os.path.join( self.base_path,'checkpoint/vtoonify_d_cartoon/vtoonify_s_d.pt'), help="path of the saved model")
        self.parser.add_argument("--output_path", type=str, default='./output/', help="path of the output images")
        self.parser.add_argument("--scale_image", action="store_true", help="resize and crop the image to best fit the model")
        self.parser.add_argument("--style_encoder_path", type=str, default=os.path.join(self.base_path,'checkpoint/encoder.pt'), help="path of the style encoder")
        self.parser.add_argument("--exstyle_path", type=str, default=None, help="path of the extrinsic style code")
        self.parser.add_argument("--faceparsing_path", type=str, default=os.path.join( self.base_path,'checkpoint/faceparsing.pth'), help="path of the face parsing model")
        self.parser.add_argument("--video", action="store_true", help="if true, video stylization; if false, image stylization")
        self.parser.add_argument("--cpu", action="store_true", help="if true, only use cpu")
        self.parser.add_argument("--backbone", type=str, default='dualstylegan', help="dualstylegan | toonify")
        self.parser.add_argument("--padding", type=int, nargs=4, default=[120,120,120,120], help="left, right, top, bottom paddings to the face center")
        self.parser.add_argument("--batch_size", type=int, default=4, help="batch size of frames when processing video")
        self.parser.add_argument("--parsing_map_path", type=str, default=None, help="path of the refined parsing map of the target video")
      
    
    def initialize(self):
        self.args = self.parser.parse_args()
        
        if self.args.exstyle_path is None:
            self.args.exstyle_path = os.path.join( self.base_path,'checkpoint/vtoonify_d_cartoon', 'exstyle_code.npy')

        self.args.scale_image = True
        device = "cpu" if self.args.cpu else "cuda"
    
        self.transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.5, 0.5, 0.5],std=[0.5,0.5,0.5]),])
    
        self.vtoonify = VToonify(backbone = self.args.backbone)
        self.vtoonify.load_state_dict(torch.load(self.args.ckpt, map_location=lambda storage, loc: storage)['g_ema'])
        self.vtoonify.to(device)
        self.parsingpredictor = BiSeNet(n_classes=19)
        self.parsingpredictor.load_state_dict(torch.load(self.args.faceparsing_path, map_location=lambda storage, loc: storage))
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

        self.pspencoder = load_psp_standalone(self.args.style_encoder_path, device)

        if self.args.backbone == 'dualstylegan':
            self.exstyles = np.load(self.args.exstyle_path, allow_pickle='TRUE').item()
            stylename = list(self.exstyles.keys())[self.args.style_id]
            self.exstyle = torch.tensor(self.exstyles[stylename]).to(device)
            with torch.no_grad(): 
                self.exstyle = self.vtoonify.zplus2wplus(self.exstyle)       

      
    def convert_image(self,frame,savetopath,width,height):
        logging.info('i called the convert_image 1')
        device = "cpu" if self.args.cpu else "cuda"
        kernel_1d = np.array([[0.125],[0.375],[0.375],[0.125]])
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        if self.args.scale_image:
            logging.info('i called the convert_image 2')
            try:
                paras,h,w,scale = get_video_crop_parameter(cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY), self.landmarkpredictor, self.face_detector_model,self.args.padding)
                logging.info('i called the convert_image 3')
                if paras is not None:
                    logging.info('i called the convert_image 4')
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
                                    if self.args.color_transfer:
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
                                
                                y_tilde = self.vtoonify(inputs, s_w.repeat(inputs.size(0), 1, 1), d_s = self.args.style_degree)        
                            
                                y_tilde = torch.clamp(y_tilde, -1, 1)
                                

                                cartooned_image =((y_tilde[0].cpu().cpu().numpy().transpose(1, 2, 0) + 1.0) * 127.5).astype(np.uint8) 
                                
                                resized_img = cv2.resize(cartooned_image, (face.shape[1], face.shape[0]), interpolation = cv2.INTER_AREA)
                                
                                resized_frame[top:bottom, left:right,:] = resized_img

                        except Exception as e: 
                            logging.info('exception occured while converting video to cartoon: {0}'.format(e))
                            continue   

                    cv2.imwrite(savetopath,cv2.cvtColor(cv2.resize(resized_frame, (width,height), interpolation = cv2.INTER_AREA), cv2.COLOR_RGB2BGR))
                    #logging.info('image saved to : {}'.format(savetopath)) 
                else:
                    cv2.imwrite(savetopath,cv2.resize(frame, (width,height), interpolation = cv2.INTER_AREA))

            except Exception as e: 
                logging.info('exception occured in the entire convert image: {0}'.format(e))        



# import cv2
# from cv2 import COLOR_BGR2BGR555
# from cv2 import COLOR_BGR2RGB
# import scipy
# from scipy import stats
# import numpy as np
# from collections import defaultdict

# def caart(img):
#     img_col = cv2.cvtColor(img,COLOR_BGR2RGB)
#     gray = cv2.cvtColor(img_col, cv2.COLOR_BGR2GRAY)
#     gray = cv2.medianBlur(gray,5)
#     edge = cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY,9,9)
#     color = cv2.bilateralFilter(img_col,9,300,300)
#     cartoon = cv2.bitwise_and(color,color,mask=edge)
#     return cartoon
