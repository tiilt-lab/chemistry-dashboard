import cv2
from cv2 import COLOR_BGR2BGR555
from cv2 import COLOR_BGR2RGB
import scipy
from scipy import stats
import numpy as np
from collections import defaultdict

def caart(img):
    img_col = cv2.cvtColor(img,COLOR_BGR2RGB)
    gray = cv2.cvtColor(img_col, cv2.COLOR_BGR2GRAY)
    gray = cv2.medianBlur(gray,5)
    edge = cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY,9,9)
    color = cv2.bilateralFilter(img_col,9,300,300)
    cartoon = cv2.bitwise_and(color,color,mask=edge)
    return cartoon

