import os
import time
import json
import librosa
import argparse
import numpy as np
import logging
from speaker_tagging.utils import *
# from utils import *

def speaker_tagging(signal):

	GRAD_THRESH = 5

	# calibrating the input signal for any frequency drift
	shift = calibration(signal)
	# shift = 0

	try:
		signal_1, sr  = librosa.load(signal, sr=44100  + shift, mono=False)
		signal_2, sr1 = librosa.load(signal, sr=44100, mono=False)
	except Exception as e:
		return('error while loading file: ', e)
		exit(0)

	signal1 = signal_1[0]
	signal2 = signal_2[1]
	logging.info('length of signal: {},{}'.format(len(signal1),len(signal2)))

	logging.info('Processing for speaker tagging has started...')
	# Synchronization signals for different starting time delay
	synchronization_stride = 1
	similarity_vector = synchronize(signal1, signal2,int(sr),0,6, synchronization_stride)
	logging.info('similarity_vector {}'.format(similarity_vector))
	# Preserving maximum part of the signal
	if similarity_vector * synchronization_stride <= 2 * sr:
		delay = 2 * int(sr) - similarity_vector * synchronization_stride
		signal2 = signal2[int(delay):]

	else:
		delay = similarity_vector * synchronization_stride - 2 * sr
		signal1 = signal1[int(delay):]
	logging.info('length of signal: {},{}'.format(len(signal1),len(signal2)))

	# calculate cross correlation
	td = cross_correlation(signal1, signal2, sr, 'calib')
	logging.info(td)

	# Removing noise from signal
	cleaned_signal = remove_noise_from_signal(np.array(td),5,1)
	cleaned_signal = remove_noise_from_signal(np.array(td),5,1)

	# Finding speaker seperation points
	matri = array_to_matix(cleaned_signal,2,1)
	points = np.where(np.abs(np.gradient(matri,axis=1))[:,1] > GRAD_THRESH)
	final = np.zeros(np.shape(cleaned_signal))
	final[points] = 1

	try:
		json_data,mean = crop_signal(signal2, points, sr,cleaned_signal)
		tagged_json_data = tag_similar_speakers(json_data,mean)
		return tagged_json_data
	except Exception as e:
	    return {"error in TDOA: ", e}

if __name__ == "__main__":

	parser = argparse.ArgumentParser(description='Speaker tagging demo')
	parser.add_argument('--audio', type=str, help='First Audio Signal')
	# parser.add_argument('--audio2', type=str, help='Second Audio Signal')
	parser.add_argument('--plot', '-p', action='store_true', help='plot tdoa and filtering graphs')
	args = parser.parse_args()
	signal = args.audio
	# sig2 = args.audio2
	plot = args.plot
	print(Fore.GREEN + 'Speaker tagging data: ',speaker_tagging(signal))
