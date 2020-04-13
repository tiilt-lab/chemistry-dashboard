from pyDiarization import speakerDiarization
import numpy
import sys
import os
from pyAudioAnalysis import audioBasicIO

prev_mt_feats_norm = numpy.array([])
prev_mt_feats_norm_or = numpy.array([])
prev_mt_feats = numpy.array([])
prev_cls = numpy.array([])
class_names = ""


[fs, x] = audioBasicIO.readAudioFile("test.wav")
x = x.flatten()

cls, curr_mt_feats, class_names, centers = speakerDiarization(x, fs, 0, 1.0, .2, .05, 0, False)
#print(aS.speakerDiarization("{}.wav".format(dir) , 0 , 1.0, .2, .05, 0, True))

print(cls)

