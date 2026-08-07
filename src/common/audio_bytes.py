"""PCM byte-wrangling helpers shared by the audio and video services.

These existed as three diverging method copies across the four WS servers
(one of which lost its `return` in the copy); the protocol classes now
delegate here with their config values as arguments.
"""
import numpy as np
import scipy.signal


# Changes the bit depth and encoding type.
def reformat_data(in_data, encoding):
    if encoding == 'pcm_f32le':
        out_data = np.frombuffer(in_data, np.float32, -1)
        return (out_data * 32767.0).astype(np.int16, copy=False).tobytes()
    return in_data


# Resampling leads to clicking in the output audio (scipy.signal.resample)
def resample_data(in_data, sample_rate):
    if sample_rate != 16000:
        out_data = np.frombuffer(in_data, np.int16, -1)
        secs = len(out_data) / sample_rate
        samps = int(secs * 16000)
        return scipy.signal.resample(out_data, samps).astype(np.int16, copy=False).tobytes()
    return in_data


# Reduces number of channels down to the desired amount.
def reduce_channels(channels_wanted, in_data, channels):
    if channels_wanted < channels:
        out_data = np.frombuffer(in_data, np.int16, -1)
        return out_data[channels_wanted::channels].tobytes()
    return in_data


def read_bytes_from_wav(wav):
    wav.setpos(0)
    sdata = wav.readframes(wav.getnframes())
    data = np.frombuffer(sdata, dtype=np.dtype('int16'))
    return data.tobytes()


def reduce_wav_channel(channels_wanted, wav, channels):
    if channels_wanted < channels:
        nch = wav.getnchannels()
        wav.setpos(0)
        sdata = wav.readframes(wav.getnframes())
        data = np.frombuffer(sdata, dtype=np.dtype('int16'))
        return data[0::nch].tobytes()
    return read_bytes_from_wav(wav)
