import numpy as np
import torch
import torch.utils.data as data_utils
import librosa.display as lrd
import speechbrain as sb
import torch.nn as nn
from functools import partial

# install speechbrain
# %%capture
# !pip install speechbrain


# source 1 is a sinusoid with a random frequency smaller
# than f_threshold, and source 2 is a sinusoid with frequency larger than f_threshold.
N = 100
f_th = 200
fs = 8000

T = 10000
t = torch.arange(0, T).unsqueeze(0)
f1 = torch.randint(5, f_th, (N, 1))
f2 = torch.randint(f_th, 400, (N, 1))
batch_size = 10

source1 = torch.sin(2 * np.pi * (f1 / fs) * t)
source2 = torch.sin(2 * np.pi * (f2 / fs) * t)
mixture = source1 + source2
N_train = 90

# train_dataset = data_utils.TensorDataset(source1[:N_train], source2[:N_train], mixture[:N_train])
# test_dataset = data_utils.TensorDataset(source1[N_train:], source2[N_train:], mixture[N_train:])

# train_loader = data_utils.DataLoader(train_dataset, batch_size=batch_size)
# test_loader = data_utils.DataLoader(test_dataset, batch_size=batch_size)


# construct a simple model with pytorch and speechbrain for source separation.
# define the model
class simpleseparator(nn.Module):
    def __init__(self, fft_size, hidden_size, num_sources=2):
        super(simpleseparator, self).__init__()
        self.masking = nn.LSTM(input_size=fft_size // 2 + 1, hidden_size=hidden_size, batch_first=True,
                               bidirectional=True)
        self.output_layer = nn.Linear(in_features=hidden_size * 2, out_features=num_sources * (fft_size // 2 + 1))
        self.fft_size = fft_size
        self.hidden_size = hidden_size
        self.num_sources = num_sources

    def forward(self, inp):
        # batch x freq x time x realim
        y = torch.stft(inp, n_fft=self.fft_size)

        # batch X freq x time
        mag = torch.sqrt((y ** 2).sum(-1))
        phase = torch.atan2(y[:, :, :, 1], y[:, :, :, 0])

        # batch x time x freq
        mag = mag.permute(0, 2, 1)

        # batch x time x feature
        rnn_out = self.masking(mag)[0]

        # batch x time x (nfft*num_sources)
        lin_out = self.output_layer(rnn_out)

        # batch x time x nfft x num_sources
        lin_out = nn.functional.relu(lin_out.reshape(lin_out.size(0), lin_out.size(1), -1, self.num_sources))

        # reconstruct in time domain
        sources = []
        all_masks = []
        for n in range(self.num_sources):
            sourcehat_mask = (lin_out[:, :, :, n])
            all_masks.append(sourcehat_mask)

            # multiply with mask and magnitude
            sourcehat_dft = (sourcehat_mask * mag).permute(0, 2, 1) * torch.exp(1j * phase)

            # reconstruct in time domain with istft
            sourcehat = torch.istft(sourcehat_dft, n_fft=self.fft_size)
            sources.append(sourcehat)
        return sources, all_masks, mag


# test_forwardpass
model = simpleseparator(fft_size=250, hidden_size=300)
est_sources, _, _ = model.forward(mixture[:5])


class SeparationBrain(sb.Brain):
    def __init__(self, train_loss, modules, opt_class):
        super(SeparationBrain, self).__init__(modules=modules, opt_class=opt_class)
        self.train_loss = train_loss

    def compute_forward(self, mix):
        """Forward computations from the mixture to the separated signals."""

        # Get the estimates for the sources
        est_sources, _, _ = self.modules.mdl(mix)

        est_sources = torch.stack(est_sources, dim=-1)

        # T changed after conv1d in encoder, fix it here
        T_origin = mix.size(1)
        T_est = est_sources.size(1)
        if T_origin > T_est:
            est_sources = nn.functional.pad(est_sources, (0, 0, 0, T_origin - T_est))
        else:
            est_sources = est_sources[:, :T_origin, :]

        return est_sources

    def compute_objectives(self, targets, est_sources):
        """Computes the loss functions between estimated and ground truth sources"""
        if self.train_loss == 'l1':
            return (est_sources - targets).abs().mean()
        elif self.train_loss == 'si-snr':
            return sb.nnet.losses.get_si_snr_with_pitwrapper(targets, est_sources).mean()

    def fit_batch(self, batch):
        """Trains one batch"""
        # Unpacking batch list
        source1, source2, mix = batch
        targets = torch.stack([source1, source2], dim=-1)

        est_sources = self.compute_forward(mix)
        loss = self.compute_objectives(targets, est_sources)

        loss.backward()
        self.optimizer.step()
        self.optimizer.zero_grad()
        return loss.detach().cpu()

    def evaluate_batch(self, batch, stage):
        """Computations needed for test batches"""

        source1, source2, mix = batch
        targets = torch.stack([source1, source2], dim=-1)

        est_sources = self.compute_forward(mix)

        si_snr = sb.nnet.losses.get_si_snr_with_pitwrapper(targets, est_sources)
        si_snr_mean = si_snr.mean().item()
        print('VALID SI-SNR = {}'.format(-si_snr_mean))
        return si_snr.mean().detach()


optimizer = lambda x: torch.optim.Adam(x, lr=0.0001)
N_epochs = 10
epoch_counter = sb.utils.epoch_loop.EpochCounter(limit=N_epochs)

separator = SeparationBrain(
    train_loss='l1',
    modules={'mdl': model},
    opt_class=optimizer
)

separator.fit(
    epoch_counter,
    train_loader,
    test_loader)