import os
import scipy
import librosa
import datetime
import numpy as np
from colorama import Fore
from collections import OrderedDict
from sklearn.metrics.pairwise import cosine_similarity

def array_to_matix(a, L, S ): 
	nrows = ((a.size-L)//S)+1
	n = a.strides[0]
	matri = (np.lib.stride_tricks.as_strided(a, shape=(nrows,L), strides=(S*n,n)))
	return matri

def remove_noise_from_signal(a, L, S ):
	a = np.pad(a,2,'edge')
	matri = array_to_matix(a,L,S)
	return(np.median(matri,axis=1))

def tsec(time_in_seconds,time_in_miliseconds = 0):
	# TODO add milisec accuracy if the window size reduces in future
	t = datetime.timedelta(seconds=time_in_seconds,milliseconds=0)
	return t

def crop_signal(R, points, sr, cleaned_signal):
	count = 0
	output_data = []
	x = [0] + points[0].tolist()[:-1]
	y = points[0].tolist()
	offset = 0
	mean = []
	for i,(start,end) in enumerate(zip(x,y)):
		if abs(start-end) == 1 or abs(start-end) == 2:
			continue
		count += 1
		output_data.append("speaker_{}: start {}, end {}".format(str(count).zfill(3), tsec(start+offset), tsec(end+offset)))
		new_signal = R[int(sr*(start + offset)):int(sr*(end + offset))]
		mean.append(np.median(cleaned_signal[start+1 : end+1]))
	output_data.append("speaker_{}: start {}, end {}".format(str(count +1).zfill(3), tsec(end+offset),tsec(int(len(R)/sr))))
	mean.append(np.median(cleaned_signal[ end+offset:int(len(R)/sr)]))
	new_signal = R[int(sr*(end + offset)):]
	return output_data,mean

def synchronize(signal1, signal2,sr,window1,window2, synchronization_stride):
	# calculate the similar points in the both the speech signals 
	# returns the index of the matching common point btw the two signals
	cut_win_sr = sr
	cut_win = signal2[cut_win_sr * 2:(cut_win_sr * 2)+ (cut_win_sr)]
	similar_old = 0
	for i in range(len(signal1)):
		# print('sig_1: ',signal1[i : i+len(cut_win)].reshape(1,-1).shape)
		# print('sig_2: ',cut_win.reshape(1,-1).shape)
		try:
			similar = cosine_similarity(signal1[i : i+len(cut_win)].reshape(1,-1), cut_win.reshape(1,-1))
		except Exception as e:
			continue
		if similar_old < similar[0][0]:
			latest = i
			similar_old = similar[0][0]
		if i == sr * window2:
			break
	latest_R = latest
	return latest

'''
# faster vectorised syncronization. needs ,more memory to run.
def synchronize(signal1, signal2,sr,window1,window2, synchronization_stride):
	cut_win_sr = sr
	signal1 = array_to_matix(signal1, sr, synchronization_stride) 
	signal1 = signal1[:sr * window2]
	cropped_signal1 = signal1.T
	cut_win = signal2[cut_win_sr * 2:(cut_win_sr * 2)+ (cut_win_sr)]
	cropped_signal2 = np.array(cut_win).reshape(1,-1)
	similarity_vector = np.dot(cropped_signal2, cropped_signal1)
	return np.argmax(similarity_vector)
'''

def cross_correlation(signal1, signal2, sr, mode):
	correlate = scipy.signal.correlate
	td = []
	count = 0
	sr = int(sr)
	wind = np.hanning(sr-1)
	for i in range(int(len(signal1)/(sr))):
		S1 = signal1[i*sr:((i+1)*sr) -1] 
		S2 = signal2[i*sr:((i+1)*sr) -1]
		try:
			if mode != 'calib':
				S1 = S1 * wind
				S2 = S2 * wind
			else:
				pass
			autocorr_S1 = correlate(S1, S1, mode='full',method='fft')
			autocorr_S1_S2 = correlate(S1, S2, mode='full',method='fft')			
			td.append(np.argmax(np.abs(autocorr_S1)) - np.argmax(np.abs(autocorr_S1_S2)))
			count += 1
		except Exception as e:
			return e
			pass
	return td


def create_bins(mean_val):
    creat_list = True
    person = 0
    DIST_THRESH = 15
    g = OrderedDict()
    for i,m in zip(mean_val,range(len(mean_val))):
        present = False
        if m == 0:
            person += 1
            g['person_{0}'.format(person)] = []
            g['index_{0}'.format(person)] = []
            g['person_{0}'.format(person)].append(i)
            g['index_{0}'.format(person)].append(m)
            continue
        for j in range(person):
            if abs(i - g['person_{0}'.format(j+1)][0]) < DIST_THRESH:
                g['person_{0}'.format(j+1)].append(i)
                g['index_{0}'.format(j+1)].append(m)
                present = True
            if present == True:
                break
        if present == False:
            person += 1
            g['person_{0}'.format(person)] = []
            g['index_{0}'.format(person)] = []
            g['person_{0}'.format(person)].append(i)
            g['index_{0}'.format(person)].append(m)  
    person_list = [0]*len(mean_val)     
    for p in range(person):
        for  kk in g['index_{0}'.format(p+1)]:
            person_list[kk] = p+1
    return mean_val, person_list

def tag_similar_speakers(output_data,mean):
	_,person_list = create_bins(mean)
	new_output_data = []
	# temporary format
	new_data_format = {}
	# print(output_data)
	for i,line in enumerate(output_data):
		new_output_data.append(
			line.replace(
				'speaker_'+ str(i+1).zfill(3),
				'person_' + str(person_list[i]).zfill(3)
				)
			)
	for tag in new_output_data:
		speaker_id = tag.split(':')[0]
		if speaker_id not in new_data_format.keys():
			new_data_format[speaker_id] = []
		new_data_format[speaker_id].append(tag.replace(speaker_id + ': ','').replace('start','').replace(' end','').split(','))
	# return new_output_data
	return new_data_format

def calibration(signal1):
	calibration_window = 30
	try:
		signal, sr  = librosa.load(signal1, sr=44100, mono=False)
		# signal2, sr1 = librosa.load(signal2, sr=44100)
	except Exception as e:
		return('[Calibration] error while loading audio signals: ', e)
		exit(0)

	signal1 = signal[0]
	signal2 = signal[1]

	# Synchronization signals for different starting time delay
	synchronization_stride = 1
	similarity_vector = synchronize(signal1, signal2,sr,0,6, synchronization_stride)

	if similarity_vector * synchronization_stride <= 2 * sr :
		# signal1 remains as it
		delay = 2 * sr - similarity_vector * synchronization_stride
		signal2 = signal2[delay:]
	else:
		delay = similarity_vector * synchronization_stride - 2 * sr
		signal1 = signal1[delay:]

	signal1 = signal1[:sr * calibration_window]
	signal2 = signal2[:sr * calibration_window]

	td = cross_correlation(signal1, signal2, sr, 'calib')

	cleaned_signal = remove_noise_from_signal(np.array(td),5,1)	
	cleaned_signal = remove_noise_from_signal(np.array(cleaned_signal),5,1)
	
	max_td = np.max(cleaned_signal)
	min_td = np.min(cleaned_signal)

	audio_length = len(signal1)/sr
	shift = (max_td - min_td)/audio_length

	return	shift