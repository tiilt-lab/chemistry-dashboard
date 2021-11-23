from os import PRIO_PGRP
from pyannote.core import Segment
from pyannote.audio.features import RawAudio
import torch
from pyAudioAnalysis import audioBasicIO
import numpy as np
from pydub import AudioSegment
from scipy.io.wavfile import read
import soundfile as sf
import csv
import time


def newSpeakerDiarization(data, sample_width, sample_rate, n_channels, path, chunk_num, chunk_length=120):
    '''
        ARGUMENTS:
            - data             the audio signal as a byte array (np ndarray)
            - sample_width  the sample_width (bytes) of the audio signal
            - sample_rate   the sampling rate (Hz) of the audio signal
            - n_channels     the number of channels of the audio signal
            - path          the path of the WAV file to store the audio
            - chunk_num      the number of times the audio has already been processed;
                            initiate at 0, pass in returned value afterwards
            - chunk_length   the interval in seconds between each time the audio is processed
    '''
    # writes new audio file if it's the first chunk
    if chunk_num == 0:
        newAudio = AudioSegment(data=data,
                           sample_width=sample_width,
                           frame_rate=sample_rate,
                           channels=n_channels)
        newAudio.export(path, format='wav')
        print(f"data_0 :{data}")
    audio = AudioSegment.from_file(path, format='wav')

    # append new audio to old audio stored on file
    if chunk_num != 0:
        new = AudioSegment(data=data,
                           sample_width=audio.sample_width,
                           frame_rate=audio.frame_rate,
                           channels=audio.channels)
        print(f"data_1 :{data}")
        audio = audio + new
        audio.export(path, format='wav')

    chunk_num = 1 if chunk_num == 0 else chunk_num
    duration = audio.duration_seconds

    # no processing occurs if interval is not reached, audio is stored as wav file
    if duration < chunk_length * chunk_num:
        print("Need more audio first!")
        return -1, -1, chunk_num

    # diarization begins
    pipeline = torch.hub.load('pyannote/pyannote-audio', 'dia')  # can use 'dia' or 'dia_ami'
    diarization = pipeline(dict(audio=path))

    speakers = set()
    timings = []

    for turn, _, speaker in diarization.itertracks(yield_label=True):
        speakers.add(speaker)   # speakers represented as 'A','B',...,'Z','AA','AB',...
        timings.append({
            'speaker ': speaker,
            'start': turn.start,
            'end': turn.end
        })
    # print(f"timings: {timings[0]}")
    return len(speakers), timings, (chunk_num + 1)  


# testing code
if __name__ == "__main__":

    audio_file = AudioSegment.from_file(
        "../dia_2021-11-18 23:34:52.959396.wav", format='wav')

    chunkNum = 0
    for i in range(1):
        print(f'--ROUND {i}--')
        start_time = time.time()
        # f_name = f'chunks/chunk{i}.wav'
        f_name = "../dia_2021-11-18 23:34:52.959396.wav"
        rate, signal = read(f_name)
        speakers, timings, chunkNum = newSpeakerDiarization(signal, 2, 16000, 1, 'CANDELETETHIS.wav', chunkNum, 60)

        print(f'chunk no.: {chunkNum}\nspeakers: {speakers}\n{timings}\n')
        print("--- %s seconds ---" % (time.time() - start_time))

        if speakers != -1:
            with open('CANDELETE.csv', 'w') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=['speaker', 'start', 'end'])
                writer.writeheader()
                for data in timings:
                    writer.writerow(data)
