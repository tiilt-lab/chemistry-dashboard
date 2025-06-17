import os
from torchvision import transforms
import torch
import dlib
import numpy as np
from .model.vtoonify import VToonify
from .model.bisenet.model import BiSeNet
from .util import load_psp_standalone

class VideoCartoonifyLoader:
    def __init__(self):
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.style_id = 73
        self.style_degree = 0.4
        self.color_transfer = False
        self.ckpt = os.path.join( self.base_path,'checkpoint/vtoonify_d_illustration/vtoonify_s009_d_c.pt')
        self.scale_image = True
        self.style_encoder_path = os.path.join(self.base_path,'checkpoint/encoder.pt')
        self.exstyle_path =None
        self.faceparsing_path = os.path.join( self.base_path,'checkpoint/faceparsing.pth')
        self.cpu = False
        self.backbone = 'dualstylegan' #"dualstylegan | toonify"
        self.padding = [150,150,150,150]
        self.batch_size = 40
        self.video = True
        self.parsing_map_path = None

    def load_model(self):
        if self.exstyle_path is None:
            self.exstyle_path = os.path.join( self.base_path,'checkpoint/vtoonify_d_comic', 'exstyle_code.npy')

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