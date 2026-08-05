"""
 Estimate time delay using GCC-PHAT
"""

import numpy as np
import time
import math


def gcc_phat(sig, refsig, fs=1, max_tau=None, interp=1):
    '''
    This function computes the offset between the signal sig and the reference signal refsig
    using the Generalized Cross Correlation - Phase Transform (GCC-PHAT)method.
    '''
    start_time = time.time()

    # This seems to increase performance as the data is a length of a power of 2.
    # sig = np.append(sig, power_two_padding(len(sig)))
    # refsig = np.append(refsig, power_two_padding(len(refsig)))

    # make sure the length for the FFT is larger or equal than len(sig) + len(refsig)
    n = sig.shape[0] + refsig.shape[0]

    # Generalized Cross Correlation Phase Transform
    SIG = np.fft.rfft(sig, n=n, axis=0)
    REFSIG = np.fft.rfft(refsig, n=n, axis=0)
    R = SIG * np.conj(REFSIG)

    cc = np.fft.irfft(R / np.abs(R), n=(interp * n))

    max_shift = int(interp * n / 2)
    if max_tau:
        max_shift = np.minimum(int(interp * fs * max_tau), max_shift)

    cc = np.concatenate((cc[-max_shift:], cc[:max_shift + 1]))

    # find max cross correlation index
    shift = np.argmax(np.abs(cc)) - max_shift
    tau = shift / float(interp * fs)
    return tau, cc

def power_two_padding(size):
    '''
    Returns padding for audio data of
    length size such that the length
    of the audio data is a power of two.
    Padding audio dramatically improves the
    performance of fft, gcc phat and DOA.
    '''
    delta = int(math.pow(2, math.ceil(math.log(size, 2)))) - size
    zeros = np.zeros(delta, dtype=np.int16)
    return zeros
