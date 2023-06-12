#pip install speechbrain
import speechbrain as sb
import torchaudio
import numpy as np
import torch
import soundfile as sf
from speechbrain.pretrained import SepformerSeparation as separator

# input: raw data
file_path = '/Users/azizamirsaidova/Downloads/M1F1-Alaw-AFsp.wav'
separation_model = separator.from_hparams(source="speechbrain/sepformer-wsj03mix", savedir='pretrained_models/sepformer-wsj03mix')

# est_sources = model.separate_file(path=file_path) 

# Define the sample rate and number of channels of the raw audio data
sample_rate = 16000
num_channels = 2

# Generate some example raw audio data
raw_data = np.random.rand(10 * sample_rate * num_channels)

# Convert raw data to a PyTorch tensor and normalize
audio_tensor = torch.from_numpy(raw_data).float().view(-1, num_channels)
audio_tensor = separation_model.audio_normalizer(audio_tensor)

# Separate sources
with torch.no_grad():
    estimated_sources = separation_model.forward(audio_tensor)

# Save the separated sources as WAV files
for i, source in enumerate(estimated_sources):
    source = source.squeeze(0).cpu().numpy()
    sf.write(f"output_source_{i}.wav", source, sample_rate)


