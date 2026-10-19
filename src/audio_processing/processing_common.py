"""Shared pipeline logic for the live and post-hoc audio processors.

processor.py (live) and processor_posthoc.py (post-hoc) are near-identical
forks. When a bug lives in both copies, a fix lands in one and the other
drifts — this session fixed the SAME bug twice in each of: the topic-argmax
selection, the embeddings save (object array), and the embeddings load
(allow_pickle). Those pieces now live here once, so a fix can't drift.

Kept deliberately pure (no self, no I/O beyond the file helpers) so both
processors call the same function and the behavior is unit-testable.
"""
import logging
import os
import uuid

import numpy as np


def select_topic_id(topics, default=-1):
    """The most probable topic id from a gensim ``[(topic_id, prob), ...]``
    distribution, or ``default`` when empty / no positive probability.

    The bug this replaces: a loop that compared each probability against a
    fixed 0 but never updated its running max, so ``topic_id`` ended up as the
    LAST topic with p>0 rather than the argmax.
    """
    best_prob = 0
    topic_id = default
    for tid, prob in topics:
        if prob > best_prob:
            best_prob = prob
            topic_id = tid
    return topic_id


def save_embeddings(path, embeddings):
    """Persist the per-utterance embeddings list. They are dicts of varied
    shape, so the array is object-typed; ``load_embeddings`` reads it back with
    allow_pickle."""
    np.save(path, np.array(embeddings, dtype=object))


def load_embeddings(path):
    """Load an embeddings file saved by ``save_embeddings``. Raises if the file
    is missing/corrupt (callers restart from an empty list on failure).

    allow_pickle is REQUIRED: the file is an object array, and np.load refuses
    object arrays without it — which silently made every session-resume
    restart from [] and drop all pre-reconnect utterances from clustering.
    """
    return np.load(path, allow_pickle=True).tolist()


def prepare_embeddings(embeddings_file, auth_key, embeddings_dir):
    """``(embeddings, embeddings_file)`` for a run, decided ONCE before any
    worker thread runs: a resume file is loaded (missing or unreadable: an
    empty list, logged), otherwise a fresh absolute file name is minted under
    ``embeddings_dir`` (auth key plus a random suffix; the old CWD-relative
    second-granular name collided when two pods started the same second).

    This replaces a per-utterance check-load-mint that ran on every pool
    thread outside the embeddings lock: the first worker minted a file that
    did not exist yet, the next ones failed to load it and assigned a fresh
    list over the one another thread was appending to (487 such errors in
    one post-hoc run on 2026-10-18), so the end-of-run tagging POST carried
    fewer embeddings than transcripts and the server refused it.
    """
    if embeddings_file is None:
        os.makedirs(embeddings_dir, exist_ok=True)
        return [], os.path.join(embeddings_dir, '{0}-{1}.npy'.format(auth_key, uuid.uuid4().hex[:8]))
    try:
        return list(load_embeddings(embeddings_file)), embeddings_file
    except FileNotFoundError:
        logging.info('Embeddings file %s does not exist yet; starting empty', embeddings_file)
    except Exception as e:
        logging.error('Unable to load embeddings file %s: %s', embeddings_file, e)
    return [], embeddings_file
