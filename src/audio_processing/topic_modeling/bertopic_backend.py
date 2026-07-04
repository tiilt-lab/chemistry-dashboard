"""BERTopic topic-modeling backend — a modern replacement for the dormant
per-owner gensim-LDA path.

Selected via [processing] topic_backend=bertopic (config.py topic_backend()).
Default is 'lda' (the existing pre-trained per-owner LDA model, which is only
active when a run supplies topic_model). BERTopic instead *fits on the session's
own transcripts* at the end of a run, so it needs no pre-trained per-owner
model — that is what makes it a practical re-enable of topic modeling.

It reuses the BGE sentence embeddings the audio server already loads (pass them
in) so no extra model is downloaded for embedding; BERTopic only adds UMAP +
HDBSCAN + c-TF-IDF on top.

Requires: pip install bertopic  (pulls umap-learn + hdbscan). Imported lazily so
its absence never affects the default LDA/None path.
"""

import logging


class BERTopicBackend:
    def __init__(self, embedder=None, min_topic_size=5):
        # embedder: an already-loaded SentenceTransformer (e.g. the server's BGE
        # model) so BERTopic embeds with the same model used elsewhere.
        from bertopic import BERTopic  # lazy: only when topic_backend=bertopic
        self._embedder = embedder
        self._model = BERTopic(embedding_model=embedder,
                               min_topic_size=min_topic_size,
                               calculate_probabilities=True,
                               verbose=False)
        self._fitted = False
        logging.info("BERTopic backend initialised (min_topic_size=%d)", min_topic_size)

    def fit_transform(self, transcripts):
        """Fit on a list of transcript strings; return (topic_ids, topic_info).

        topic_ids[i] is the assigned topic for transcripts[i] (-1 == outlier).
        topic_info is BERTopic's per-topic summary (id, count, name, top words).
        """
        if not transcripts:
            return [], []
        # Precompute embeddings with the shared embedder when available so the
        # same representation is used across the pipeline.
        embeddings = None
        if self._embedder is not None:
            embeddings = self._embedder.encode(transcripts, show_progress_bar=False)
        topics, _ = self._model.fit_transform(transcripts, embeddings=embeddings)
        self._fitted = True
        return topics, self._model.get_topic_info().to_dict(orient='records')

    def top_words(self, topic_id, n=10):
        if not self._fitted:
            return []
        words = self._model.get_topic(topic_id) or []
        return [w for w, _ in words[:n]]
