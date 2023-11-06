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
from sklearn.metrics.pairwise import cosine_similarity
import scipy.spatial as sp

def embedSignal(x, verification):

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

def getSpectralEmbeddings(embeddings_list):
  embeddings = np.array([])
  for emb in embeddings_list:
    if not np.any(embeddings):
      embeddings = np.array(emb['embedding'])
    else:
      embeddings = np.append(embeddings, emb['embedding'], axis=0)

  logging.info("Embeddings shape")
  logging.info(embeddings.shape)
  cos_sim = sp.distance.cdist(embeddings, embeddings, "cosine")
  r = []
  U = []
  S = []
  e = []

  logging.info("cos_sim calculated")
  #attempt to find best p
  for p in range(1, max(2,int(cos_sim.shape[0]/4))):

    Ap = np.zeros(cos_sim.shape)

    #p-neighbor row-binarization
    for row in range(0, cos_sim.shape[0]):
      indices = np.argsort(cos_sim[row])[-p:]
      Ap[row][indices] = 1

    # Symmetrization
    avgAp = np.divide(np.add(Ap, Ap.T), 2)

    # Laplacian
    Dp = np.diag(np.sum(cos_sim, axis=1))
    Lp = np.subtract(Dp, avgAp)

    # Singular Value Decomposition
    Up, Sp, Vhp = np.linalg.svd(Lp)
    U.append(Up)
    # Ascending order
    Sp = np.flip(Sp)
    S.append(Sp)


    # eigengap Vector
    ep = []
    for i in range(1, len(Sp)):
      ep.append(Sp[i] - Sp[i - 1])

    e.append(ep)
    # Normalized Maximum Eigengap(NME)
    gp = np.max(ep) / Sp[-1]
    rp = p / gp
    r.append(rp)

  bestP = np.argmin(r)
  n_speakers = np.argmax(e[bestP])

  spectralEmbeddings = U[bestP][:, :n_speakers].T

  logging.info("got spectral embeddings")
  return spectralEmbeddings, n_speakers

def clusterSpectralEmbeddings(embeddings, n_speakers):
  cluster_labels = []
  sil_all = []
  cluster_centers = []


  k_means = sklearn.cluster.KMeans(n_clusters=n_speakers, n_init=10, init='random')
  k_means.fit(embeddings.T)
  cls = k_means.labels_
  means = k_means.cluster_centers_

  cluster_labels.append(cls)
  cluster_centers.append(means)

  class_names = ["speaker{0:d}".format(c) for c in range(n_speakers)]

  return cls, class_names, cluster_centers

