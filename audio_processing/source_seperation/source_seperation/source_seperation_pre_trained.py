#pip install speechbrain
import wave
import speechbrain as sb
import torchaudio
import numpy as np
import torch
from speechbrain.pretrained import SepformerSeparation as separator


def source_seperation(file_path):
    separation_model = separator.from_hparams(source="speechbrain/sepformer-wsj03mix", savedir='pretrained_models/sepformer-wsj03mix')
    sources = separation_model.separate_file(file_path)
    return torchaudio.save("seperated_2022_3.wav", sources[:, :, 0].detach().cpu(), 8000, encoding="PCM_S", bits_per_sample=16)

if __name__=="__main__":
    file_path = "file_name.wav"
    source_seperation(file_path)




