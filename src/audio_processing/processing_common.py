"""Shared pipeline logic for the live and post-hoc audio processors.

processor.py (live) and processor_posthoc.py (post-hoc) are near-identical
forks. When a bug lives in both copies, a fix lands in one and the other
drifts — this session fixed the SAME bug twice in each of: the topic-argmax
selection, the embeddings save (object array), and the embeddings load
(allow_pickle). Those pieces now live here once, so a fix can't drift.

Kept deliberately pure (no self, no I/O beyond the two file helpers) so both
processors call the same function and the behavior is unit-testable.
"""
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
