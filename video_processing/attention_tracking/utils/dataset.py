import torch
from torch.utils.data.dataset import Dataset
from torchvision import transforms
import torchvision.transforms.functional as TF

import numpy as np
from PIL import Image, ImageFilter, ImageDraw
import pandas as pd

# import matplotlib as mpl

# mpl.use('Agg')
# from matplotlib import cm
# import matplotlib.pyplot as plt
# from scipy.misc import imresize
import cv2
import os
import glob
import csv

from .imutils import get_head_box_channel
from config import *
from pathlib import Path
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)


class AttentionFlow(Dataset):
    def __init__(self, frames, head_bboxes, transform, input_size=224, output_size=64):        
        self.head_bboxes = head_bboxes
        self.length = len(head_bboxes)
    
        
        self.frames = frames
        self.transform = transform

        self.input_size = input_size
        self.output_size = output_size
  
    def __getitem__(self, index):
        face = self.head_bboxes[index]
        img = Image.fromarray(np.uint8(self.frames[int(face[0])]))#.detach().clone().numpy()
        frame_name = face[0]
        person_id = face[1]
        x_min = face[2]
        y_min = face[3]
        x_max = face[4]
        y_max = face[5]
        headbox = torch.IntTensor([x_min,y_min,x_max,y_max])
        # expand face bbox a bit
        k = 0.1
        x_min -= k * abs(x_max - x_min)
        y_min -= k * abs(y_max - y_min)
        x_max += k * abs(x_max - x_min)
        y_max += k * abs(y_max - y_min)
        width, height = img.size
        img = img.convert('RGB')
       
        x_min, y_min, x_max, y_max = map(float, [x_min, y_min, x_max, y_max])

        
        imsize = torch.IntTensor([width, height])
        

        head_channel = get_head_box_channel(x_min, y_min, x_max, y_max, width, height,
                                                    resolution=self.input_size, coordconv=False).unsqueeze(0)

        # Crop the face
        face  = img.crop((int(x_min), int(y_min), int(x_max), int(y_max))) 

        if self.transform is not None:
            img = self.transform(img)
            face = self.transform(face)

        return img, face, head_channel,headbox, imsize, frame_name, person_id
        

    def __len__(self):
        return self.length