import gensim
import logging
import re
import nltk
import os

# Keyword semantic matching supports two backends, selected via
# [processing] keyword_backend in config.ini (read through config.py):
#   * 'word2vec'  (default) -- the 2013 GoogleNews-300 static vectors. Kept as
#                  the default so existing behaviour is unchanged.
#   * 'embedding' -- a modern SentenceTransformer (e.g. BGE). Encodes each word
#                  and keyword and scores by cosine distance, so it is not
#                  limited to a fixed vocabulary and reflects contextual meaning
#                  far better than word2vec.
# Both expose the same public API: initialize(limit) + detect_keywords(...).

KEYWORD_MODEL = None      # gensim KeyedVectors (word2vec backend)
_EMBED_MODEL = None       # SentenceTransformer (embedding backend)
_BACKEND = 'word2vec'


def _backend():
    # Resolve the backend lazily so this module can be imported before
    # config.initialize() has run (mirrors keyword_model_limit usage).
    try:
        import config as cf
        return cf.keyword_backend()
    except Exception:
        return 'word2vec'


def initialize(limit=100000):
    # Setting limit lower will increase load times but will weaken results.
    # In total, the word2vec model has about 3,000,000 words; limit takes the N
    # most frequent. limit is ignored by the embedding backend.
    global KEYWORD_MODEL, _EMBED_MODEL, _BACKEND
    _BACKEND = _backend()

    if _BACKEND == 'embedding':
        from sentence_transformers import SentenceTransformer
        import config as cf
        model_name = cf.keyword_embedding_model()
        print(f'Loading keyword embedding model ({model_name})...')
        _EMBED_MODEL = SentenceTransformer(model_name)
        print('Embedding model loaded.')
        return

    print('Unpacking keyword model...')
    model_path = os.path.dirname(os.path.abspath(__file__)) + '/models/GoogleNews-vectors-negative300.bin'
    KEYWORD_MODEL = gensim.models.KeyedVectors.load_word2vec_format(model_path, binary=True, limit=limit)
    print('Model unpacked.')


def _detect_keywords_embedding(words, keywords, threshold):
    from sentence_transformers import util
    if not words or not keywords:
        return []
    # Encode once; cosine distance = 1 - cosine similarity, matching the
    # gensim .distance() semantics used by the word2vec path (lower = closer).
    word_emb = _EMBED_MODEL.encode(words, normalize_embeddings=True, convert_to_tensor=True)
    kw_emb = _EMBED_MODEL.encode(keywords, normalize_embeddings=True, convert_to_tensor=True)
    sims = util.cos_sim(word_emb, kw_emb)  # (len(words), len(keywords))
    results = []
    for i, word in enumerate(words):
        for j, keyword in enumerate(keywords):
            distance = 1.0 - float(sims[i][j])
            if distance < threshold:
                results.append({
                    'word': word,
                    'keyword': keyword,
                    'similarity': distance
                })
    return results


def detect_keywords(transcript, keywords, threshold=None):
    # Split transcript by word and remove special characters.
    words = re.sub("[.,!?]", '', transcript).split()

    if _BACKEND == 'embedding':
        # BGE-style cosine distances sit in a tighter, higher band than
        # word2vec's, so the 0.6 word2vec cutoff would match almost everything.
        # Use a backend-appropriate default (config-tunable) unless the caller
        # passed an explicit threshold.
        if threshold is None:
            try:
                import config as cf
                threshold = cf.keyword_embedding_threshold()
            except Exception:
                threshold = 0.28
        return _detect_keywords_embedding(words, keywords, threshold)

    if threshold is None:
        threshold = 0.6

    # Reduce transcript words and keywords down to words in model.
    words = [word for word in words if word in KEYWORD_MODEL.key_to_index]
    keywords = [keyword for keyword in keywords if keyword in KEYWORD_MODEL.key_to_index]

    results = []
    for word in words:
        for keyword in keywords:
            distance = KEYWORD_MODEL.distance(keyword, word)
            if (distance < threshold):
                results.append({
                    'word': word,
                    'keyword': keyword,
                    'similarity': distance
                })
    return results

if __name__ == '__main__':
    initialize(100000)
    results = detect_keywords('apple banana fruit', ['fruit'])
    print(results)
