#from __future__ import print_function
import logging
import numpy as np
import sklearn.cluster
from pyAudioAnalysis import MidTermFeatures as mtf
from pyAudioAnalysis import ShortTermFeatures as stf
from pyAudioAnalysis import audioTrainTest as at
from pyAudioAnalysis import audioBasicIO
from scipy.spatial import distance
import scipy.signal
import sklearn.discriminant_analysis
import os.path
import hmmlearn.hmm
import json
import scipy
import torch
import numpy as np
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
from sklearn.metrics import silhouette_score
import torchaudio
from speechbrain.pretrained import SpeakerRecognition

def embedSignal(x):
  store_embeddings = False
  verification = SpeakerRecognition.from_hparams(source="speechbrain/spkrec-ecapa-voxceleb", savedir="./pretrained_ecapa")

  np_signal = np.frombuffer(x, dtype=np.dtype('int16'))
  signal = torch.from_numpy(np_signal)

  embedding = verification.encode_batch(signal)
  return [embedding[0, 0].numpy()]




def clusterEmbeddings(embeddings_list, max_speakers = 10, n_speakers = 0):
  embeddings = np.array([])
  for emb in embeddings_list:
    if not np.any(embeddings):
      embeddings = np.array(emb['embedding'])
    else:
      embeddings = np.append(embeddings, emb['embedding'], axis=0)

  dist_all = np.sum(distance.squareform(distance.pdist(embeddings)), axis=0)
  m_dist_all = np.mean(dist_all)
  i_non_outliers = np.nonzero(dist_all < 1.2 * m_dist_all)[0]

  s_range = []
  if n_speakers <= 0:
      s_range = range(2, min(max_speakers, embeddings.shape[0] - 1))
  else:
      s_range = [n_speakers]
  cluster_labels = []
  cluster_centers = []

  silhouette_coefficients = []

  for speakers in s_range:
    k_means = sklearn.cluster.KMeans(n_clusters=speakers, n_init=10, init='random')
    k_means.fit(embeddings)
    cls = k_means.labels_
    means = k_means.cluster_centers_

    cluster_labels.append(cls)
    cluster_centers.append(means)
    score = silhouette_score(embeddings, cls)
    silhouette_coefficients.append(score)

  imax = int(np.argmax(silhouette_coefficients))
  # optimal number of clusters
  num_speakers = s_range[imax]
  cls = cluster_labels[imax]

  n_wins = embeddings.shape[0]
  for index in range(n_wins):
      cls = np.zeros((n_wins,))
      j = np.argmin(np.abs(index - i_non_outliers))
      cls[index] = cluster_labels[imax][j]

  class_names = ["speaker{0:d}".format(c) for c in range(num_speakers)]

  return cls, class_names, cluster_centers
