"""NLP helpers shared by the two topic-modeling modules.

The audio processor's topic_modeling.py (per-utterance inference) and the
server's topicmodeling.py (training + inference from PDFs/CSVs) otherwise
diverge, but both kept identical copies of the spaCy loader, the gensim bigram
builder, and the base stop-word tuple. Those live here once.
"""
import gensim
import spacy

BASE_STOP_WORDS = ('from', 'subject', 're', 'edu', 'use')

# Loaded once per process: spacy.load is ~1s and runs per utterance / per
# /api/v1/topics request, so caching matters.
_nlp = None


def _get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm", disable=['parser', 'ner'])
    return _nlp


def generate_bigram(data_words):
    bigram = gensim.models.Phrases(data_words, min_count=5, threshold=100)  # higher threshold fewer phrases.
    bigram_mod = gensim.models.phrases.Phraser(bigram)
    return [bigram_mod[doc] for doc in data_words]
