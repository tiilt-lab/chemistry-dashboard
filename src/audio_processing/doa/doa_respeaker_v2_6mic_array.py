"""
Time Difference of Arrival for ReSpeaker V2 6mic array
"""

import collections
import math
import numpy as np
import time
import logging

from .element import Element
from .gcc_phat import gcc_phat

SOUND_SPEED = 340.0

MIC_DISTANCE_6 = 0.09218
MAX_TDOA_6 = MIC_DISTANCE_6 / float(SOUND_SPEED)


class DOA(Element):
    def __init__(self, rate=16000, chunks=50):
        super(DOA, self).__init__()

        self.queue = collections.deque(maxlen=chunks)
        self.sample_rate = rate

        self.pair = [[0, 3], [1, 4], [2, 5]]

    def put(self, data):
        self.queue.append(data)

        super(DOA, self).put(data)

    def get_direction(self):
        tau = [0, 0, 0]
        theta = [0, 0, 0]

        buf = b''.join(self.queue)
        buf = np.fromstring(buf, dtype='int16')
        for i, v in enumerate(self.pair):
            tau[i], _ = gcc_phat(buf[v[0]::6], buf[v[1]::6], fs=self.sample_rate, max_tau=MAX_TDOA_6, interp=1)
            theta[i] = np.arcsin(tau[i] / MAX_TDOA_6) * 180 / np.pi

        min_index = np.argmin(np.abs(tau))
        if (min_index != 0 and theta[min_index - 1] >= 0) or (min_index == 0 and theta[len(self.pair) - 1] < 0):
            best_guess = (theta[min_index] + 360) % 360
        else:
            best_guess = (180 - theta[min_index])

        best_guess = (best_guess + 30 + min_index * 60) % 360

        return best_guess

# Calculates DoA of a transcript.
# Currently configured to only process the first word of transcript.
def calculateDOA(audio_start_time, audio_data, word_timings, sample_rate, channels, byte_depth):
    try:
        y = 0
        x = 0
        for word in word_timings:
            doa = DOA()
            start, end = word
            start = int((start - audio_start_time) * sample_rate) * channels * byte_depth
            end = int((end - audio_start_time) * sample_rate) * channels * byte_depth
            word_audio = audio_data[start: end]
            if len(word_audio) == 0:
                continue
            doa.queue.append(bytes(word_audio))
            direction = doa.get_direction()
            y += math.sin(math.radians(direction))
            x += math.cos(math.radians(direction))
        result = math.degrees(math.atan2(y, x))
        if result < 0.0:
            result += 360.0
        return result
    except Exception as e:
        logging.critical('Direction of arrival calculation failed: {0}'.format(e))
        return -1