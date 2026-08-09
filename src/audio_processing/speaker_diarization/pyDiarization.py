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
  # FLOAT domain, like every other embedding path here: raw-int16 embeddings
  # are measurably degraded (see cluster_reconcile's -0.08 vs 0.39 note), and
  # the clustering merge gate below is calibrated on float-domain centroids.
  signal = torch.tensor(
      np.frombuffer(x, dtype=np.int16).astype(np.float32) / 32768.0)

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
# Closed-world assignment: a pod's fingerprint set IS its roster — nobody
# else can be speaking. When every participant has a usable reference, an
# utterance that fails the confidence gates is still assigned to the best
# match (there is no fourth person), except genuine non-speech: below the
# noise floor (whisper hallucinations on silence, keyboard noise) stays None.
CLOSED_WORLD = True
NOISE_FLOOR = 0.08

# Turn a raw cosine similarity into a 0-100 confidence for display. Raw cosine
# is not intuitive here: enrolment prints score ~0.2-0.45 against live audio, so
# 0.45 already means "sure" and showing it as 45% would read as a coin toss.
# Anchor the scale on the accept gates above so the number matches how the
# diarizer actually treats the match, and lift it slightly when the winner
# leads the runner-up by a clear margin.
_CONF_ANCHORS = [
    (NOISE_FLOOR, 0),   # 0.08 -> nothing worth attributing
    (ACCEPT_LOW, 35),   # 0.20 -> weak, only taken with a dominant margin
    (ACCEPT_SIM, 60),   # 0.30 -> mid floor
    (ACCEPT_SURE, 88),  # 0.45 -> confident on its own
    (0.60, 98),
    (1.0, 100),
]


def part_voice_features(part):
    """Assemble the transcript's voice_features payload from an attributed part,
    or None when there is nothing to record. Carries the diarization confidence
    and any contested-overlap flag so the UI can show both."""
    vf = {}
    if part.get('contested'):
        vf['contested'] = part['contested']
    if part.get('confidence'):
        vf['confidence'] = part['confidence']
    return vf or None


def confidence_percent(sim, margin=0.0):
    """0-100 attribution confidence from a cosine similarity and the winner's
    lead over the runner-up. Piecewise-linear on the accept gates, clamped."""
    if sim is None:
        return None
    base = 0.0
    if sim <= _CONF_ANCHORS[0][0]:
        base = 0.0
    elif sim >= _CONF_ANCHORS[-1][0]:
        base = 100.0
    else:
        for (x0, y0), (x1, y1) in zip(_CONF_ANCHORS, _CONF_ANCHORS[1:]):
            if x0 <= sim <= x1:
                base = y0 + (y1 - y0) * (sim - x0) / (x1 - x0)
                break
    # A clear lead adds a little certainty; a photo-finish subtracts none.
    base += max(0.0, min(margin, 0.10)) * 60
    return int(max(0, min(100, round(base))))

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


def reset_speaker_session_state(aliases):
  """Called when a pod (re)sets its roster. Those speakers are starting a
  fresh session: their mic-adaptation samples from an earlier session (other
  room, other phone) must not carry over, and a re-recorded enrollment print
  must be re-read from disk instead of served stale from the process cache."""
  for alias in aliases:
    if alias:
      _SESSION_ACC.pop(alias, None)
      _PRINT_CACHE.pop(alias, None)


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
    return None, -1, None
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
    return None, -1, None
  scored.sort(reverse=True, key=lambda s: s[0])
  best_sim, best_alias, best_id = scored[0]
  runner_up = scored[1][0] if len(scored) > 1 else -1.0
  margin = best_sim - runner_up
  # Confidence travels with the assignment so the transcript can show how sure
  # the match was. 'closed_world' flags a below-gate best-of-roster pick, which
  # is the one most likely to need a human's eye.
  conf = {'percent': confidence_percent(best_sim, margin),
          'sim': round(float(best_sim), 3),
          'margin': round(float(margin), 3)}

  accepted = (best_sim >= ACCEPT_SURE
              or (best_sim >= ACCEPT_SIM and margin >= ACCEPT_MARGIN)
              or (best_sim >= ACCEPT_LOW and margin >= ACCEPT_LOW_MARGIN))
  if not accepted and CLOSED_WORLD and len(scored) == len(fingerprints) \
      and best_sim >= NOISE_FLOOR:
    # roster is complete: best-of-roster beats "unknown". Low-confidence
    # (below the gates) — logged as such, and deliberately NOT fed to
    # session adaptation.
    logging.info('closed-world assign %s (sim %.3f, next %.3f)',
                 best_alias, best_sim, runner_up)
    conf['closed_world'] = True
    return best_alias, best_id, conf
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
    return best_alias, best_id, conf
  logging.info('speaker abstain (best %s %.3f, next %.3f)',
               best_alias, best_sim, runner_up)
  return None, -1, None




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

# Auto-tuned spectral clustering (NME-SC, Park et al. 2019) for the
# no-fingerprint fallback: build a p-nearest-neighbor similarity graph over
# the per-utterance embeddings, read the speaker count from the eigengap of
# the graph Laplacian's ascending spectrum, and k-means the corresponding
# low eigenvectors. p is auto-tuned by the Normalized Maximum Eigengap.
#
# The eigengap search is capped: a pod is a handful of people around a
# table, so a "gap" suggesting dozens of speakers is a degenerate graph,
# not signal (an unbounded search once yielded 146 "speakers" for 148
# utterances).
MAX_AUTO_SPEAKERS = 8

def getSpectralEmbeddings(embeddings_list):
  embeddings = np.array([])
  for emb in embeddings_list:
    if not np.any(embeddings):
      embeddings = np.array(emb['embedding'])
    else:
      embeddings = np.append(embeddings, emb['embedding'], axis=0)

  logging.info("Embeddings shape")
  logging.info(embeddings.shape)
  n = embeddings.shape[0]
  if n < 4:
    # Too few utterances for eigengap analysis — call it one speaker.
    return np.zeros((n, 1)), 1

  # Cosine SIMILARITY (cdist returns distance = 1 - similarity; the graph
  # below must connect the most similar utterances, not the least).
  sim = 1.0 - sp.distance.cdist(embeddings, embeddings, "cosine")
  logging.info("similarity calculated")

  best = None  # (r_p, eigengap vector, eigenvectors)
  #attempt to find best p (up to n/2 — the old n/4 cap left single-cluster
  #pods with only fragmented graphs to choose from)
  for p in range(1, max(2, int(n / 2))):

    # p-neighbor row-binarization: connect each utterance to its p MOST
    # similar peers (self included — sim[i][i] == 1 is always in the top p).
    Ap = np.zeros((n, n))
    for row in range(0, n):
      indices = np.argsort(sim[row])[-p:]
      Ap[row][indices] = 1

    # Symmetrization
    avgAp = np.divide(np.add(Ap, Ap.T), 2)

    # Graph Laplacian — the degree matrix comes from the binarized affinity
    # itself, not from the raw similarity matrix.
    Lp = np.subtract(np.diag(np.sum(avgAp, axis=1)), avgAp)

    # eigh: symmetric input, eigenvalues ASCENDING with eigenvectors
    # aligned to them — the k smallest carry the cluster structure. (The
    # old SVD returned everything descending; flipping the values but not
    # the vectors fed k-means the noise directions.)
    evals, evecs = np.linalg.eigh(Lp)

    # A graph shattered into more connected components (near-zero
    # eigenvalues) than plausible speakers is under-connected for this p —
    # its "gaps" reflect fragmentation, not cluster structure.
    if np.sum(evals < 1e-8) > MAX_AUTO_SPEAKERS:
      continue

    # Eigengap vector over the plausible speaker range: gaps[j] is the
    # jump after eigenvalue j+1, i.e. the evidence for j+1 clusters.
    gaps = np.diff(evals[:min(n, MAX_AUTO_SPEAKERS + 1)])
    if gaps.size == 0 or evals[-1] <= 1e-9:
      continue
    # Normalized Maximum Eigengap (NME)
    gp = np.max(gaps) / evals[-1]
    if gp <= 0:
      continue
    rp = p / gp
    if best is None or rp < best[0]:
      best = (rp, gaps, evecs)

  if best is None:
    # Every candidate graph was degenerate (e.g. fully disconnected).
    return np.zeros((n, 1)), 1
  _, gaps, evecs = best
  # A maximal gap after the (j+1)-th ascending eigenvalue means j+1
  # clusters (argmax alone is off by one and can return 0).
  n_speakers = int(np.argmax(gaps)) + 1

  # Rows = utterances, columns = the n_speakers smallest eigenvectors.
  spectralEmbeddings = evecs[:, :n_speakers]

  logging.info("got spectral embeddings")
  return spectralEmbeddings, n_speakers

# Same-speaker sub-clusters sit far closer in raw ECAPA space than different
# speakers do (measured on enrollment audio: centroid cosine ~0.7 within one
# voice vs ~0.04-0.2 across voices), so clusters whose raw centroids exceed
# this similarity are one voice split by within-speaker variation.
MERGE_CENTROID_SIM = 0.45

def clusterSpectralEmbeddings(embeddings, n_speakers, raw_list=None):
  # embeddings: (n_utterances, n_speakers) spectral coordinates from
  # getSpectralEmbeddings — one row per utterance, k-meaned directly.
  # raw_list: the original embeddings_list; when given, clusters that are
  # near-identical in raw space are merged (the eigengap can over-split a
  # single talkative speaker into sub-styles).
  n_speakers = max(1, int(n_speakers))

  k_means = sklearn.cluster.KMeans(n_clusters=n_speakers, n_init=10, init='random')
  k_means.fit(embeddings)
  cls = np.asarray(k_means.labels_)
  means = k_means.cluster_centers_

  if raw_list is not None and len(set(cls.tolist())) > 1:
    raw = np.vstack([np.asarray(e['embedding'][0], dtype=np.float64)
                     for e in raw_list])
    raw = raw / (np.linalg.norm(raw, axis=1, keepdims=True) + 1e-9)
    while True:
      ids = sorted(set(cls.tolist()))
      if len(ids) < 2:
        break
      cents = {}
      for c in ids:
        v = raw[cls == c].mean(axis=0)
        cents[c] = v / (np.linalg.norm(v) + 1e-9)
      best = None
      for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
          s = float(np.dot(cents[ids[i]], cents[ids[j]]))
          if best is None or s > best[0]:
            best = (s, ids[i], ids[j])
      if best[0] < MERGE_CENTROID_SIM:
        break
      logging.info('merging clusters %s and %s (centroid sim %.2f)',
                   best[1], best[2], best[0])
      cls[cls == best[2]] = best[1]
    remap = {c: i for i, c in enumerate(sorted(set(cls.tolist())))}
    cls = np.array([remap[c] for c in cls])
    n_speakers = len(remap)

  class_names = ["speaker{0:d}".format(c) for c in range(n_speakers)]

  return cls, class_names, [means]

