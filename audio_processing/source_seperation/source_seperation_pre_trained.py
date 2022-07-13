#pip install speechbrain
from speechbrain.pretrained import SepformerSeparation as separator
import torchaudio

file_path = 'add wav file.wav'
model = separator.from_hparams(source="speechbrain/sepformer-wsj03mix", savedir='pretrained_models/sepformer-wsj03mix')

#est_sources = model.separate_file(path=file_path) 

#torchaudio.save("source1hat.wav", est_sources[:, :, 0].detach().cpu(), 8000)
#torchaudio.save("source2hat.wav", est_sources[:, :, 1].detach().cpu(), 8000)
#torchaudio.save("source3hat.wav", est_sources[:, :, 2].detach().cpu(), 8000)
