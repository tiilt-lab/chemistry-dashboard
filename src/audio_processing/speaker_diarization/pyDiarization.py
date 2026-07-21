#from __future__ import print_function
import logging
import numpy as np
import sklearn.cluster
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
from sklearn.metrics import silhouette_score
import torchaudio
from speechbrain.inference import SpeakerRecognition
from sklearn.metrics.pairwise import cosine_similarity
import scipy.spatial as sp

def embedSignal(x, verification):

  signal = torch.tensor(np.frombuffer(x, dtype=np.dtype('int16')))

  embedding = verification.encode_batch(signal)
  # The model may live on CUDA; numpy conversion requires host memory.
  return [embedding[0, 0].detach().cpu().numpy()]

# Live-attribution accept gates, in cosine-similarity space (float-domain
# ECAPA embeddings). Enrollment prints score lower against live session audio
# than against themselves (mic/room domain gap), so acceptance is tiered:
# high-sim alone, mid-sim with a margin, or low-sim with a DOMINANT margin.
ACCEPT_SURE = 0.45     # this high alone: accept
ACCEPT_SIM = 0.30      # mid floor, needs margin...
ACCEPT_MARGIN = 0.05
ACCEPT_LOW = 0.20      # low floor, needs a dominant lead over the runner-up
ACCEPT_LOW_MARGIN = 0.06
# Session adaptation: only utterances this confident teach the session print
# (guards against a wrong accept poisoning the wrong person's reference).
ADAPT_MIN_SIM = 0.40
ADAPT_MAX_SAMPLES = 12
ADAPT_MIN_SAMPLES = 3  # use the adapted print only once it's stable

# alias -> normalized reference embedding, for the life of the process. A
# speaker's enrollment reference never changes mid-session, so embed it
# exactly once (the old code re-embedded every print for every utterance).
_PRINT_CACHE = {}
# alias -> list of confidently-accepted utterance embeddings from live
# sessions. Bridges the enrollment-mic vs session-mic domain gap: after a few
# clear utterances, the speaker is matched against how they sound TODAY.
_SESSION_ACC = {}


def _print_embedding(alias, raw_bytes, verification):
  """Reference embedding for one speaker. Prefers the cached enrollment
  embedding (<alias>.emb.npy — where minted v2 voice prints live), falling
  back to embedding the provided fingerprint audio in FLOAT domain (raw-int16
  embeddings are degraded; see cluster_reconcile's measurement)."""
  if alias in _PRINT_CACHE:
    return _PRINT_CACHE[alias]
  emb = None
  try:
    import config as cf
    path = os.path.join(cf.biometric_folder(), '{0}.emb.npy'.format(alias))
    if os.path.isfile(path):
      emb = np.load(path).astype(np.float32)
      logging.info('live print for %s: cached enrollment embedding', alias)
  except Exception as e:
    logging.warning('live print cache read failed for %s: %s', alias, e)
  if emb is None and raw_bytes:
    try:
      sig = torch.tensor(
          np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0)
      emb = verification.encode_batch(sig)[0, 0].detach().cpu().numpy()
      logging.info('live print for %s: embedded join-time recording', alias)
    except Exception as e:
      logging.warning('live print embed failed for %s: %s', alias, e)
  if emb is not None:
    emb = emb / (np.linalg.norm(emb) + 1e-9)
    _PRINT_CACHE[alias] = emb
  return emb


def checkFingerprints(x, fingerprints, verification):
  """Assign an utterance to one of THIS POD's participants, or abstain.

  The utterance is embedded once (float domain) and scored by cosine against
  each participant's reference print. Accept only a clear winner: above the
  floor AND ahead of the runner-up by a margin (or high enough to be sure on
  its own). Anything murky stays unassigned for the post-hoc sweep instead of
  being guessed wrong."""
  try:
    sig = torch.tensor(
        np.frombuffer(x, dtype=np.int16).astype(np.float32) / 32768.0)
    utt = verification.encode_batch(sig)[0, 0].detach().cpu().numpy()
  except Exception as e:
    logging.info('utterance embed failed: {0}'.format(e))
    return None, -1
  utt = utt / (np.linalg.norm(utt) + 1e-9)

  scored = []
  for speaker in fingerprints:
    info = fingerprints[speaker]
    alias = info.get('alias')
    ref = _print_embedding(alias, info.get('data'), verification)
    if ref is None:
      continue
    sim = float(np.dot(utt, ref))
    # Session-adapted reference: how this person sounds through TODAY's mic.
    acc = _SESSION_ACC.get(alias)
    if acc and len(acc) >= ADAPT_MIN_SAMPLES:
      sref = np.mean(acc, axis=0)
      sref = sref / (np.linalg.norm(sref) + 1e-9)
      sim = max(sim, float(np.dot(utt, sref)))
    scored.append((sim, alias, speaker))
  if not scored:
    return None, -1
  scored.sort(reverse=True, key=lambda s: s[0])
  best_sim, best_alias, best_id = scored[0]
  runner_up = scored[1][0] if len(scored) > 1 else -1.0
  margin = best_sim - runner_up

  accepted = (best_sim >= ACCEPT_SURE
              or (best_sim >= ACCEPT_SIM and margin >= ACCEPT_MARGIN)
              or (best_sim >= ACCEPT_LOW and margin >= ACCEPT_LOW_MARGIN))
  if accepted:
    if best_sim >= ADAPT_MIN_SIM:
      acc = _SESSION_ACC.setdefault(best_alias, [])
      acc.append(utt)
      if len(acc) > ADAPT_MAX_SAMPLES:
        acc.pop(0)
      if len(acc) == ADAPT_MIN_SAMPLES:
        logging.info('session-adapted print active for %s', best_alias)
    logging.info('Selected speaker is %s (sim %.3f, next %.3f)',
                 best_alias, best_sim, runner_up)
    return best_alias, best_id
  logging.info('speaker abstain (best %s %.3f, next %.3f)',
               best_alias, best_sim, runner_up)
  return None, -1




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

