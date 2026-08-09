import os
import sys
import re
from collections import defaultdict
#from tf_idf import tfidf

# Gensim
import gensim
from gensim.utils import simple_preprocess

# spacy for lemmatization



# Shared spaCy loader / bigram builder / base stop words (see common).
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'common')))
from topic_modeling_common import BASE_STOP_WORDS, _get_nlp, generate_bigram  # noqa: E402


mallet_path = '~/mallet-2.0.8/bin/mallet' # update this path

def sent_to_words(sentences):
    for sentence in sentences:
        yield(gensim.utils.simple_preprocess(str(sentence), deacc=True))  # deacc=True removes punctuations

def generate_trigram(data_words, bigram):
    trigram = gensim.models.Phrases(bigram[data_words], threshold=100)
    trigram_mod = gensim.models.phrases.Phraser(trigram)

    return trigram, trigram_mod

def preprocess_transcript(transcript, extra_stop_words):
    # Local list: the old module-global grew on every utterance, and the
    # add_stop_words dance (returns None) discarded the caller's extras.
    stop_words = list(BASE_STOP_WORDS) + [w for w in (extra_stop_words or []) if w]

    transcript = re.sub('\S*@\S*\s?', '', transcript)

    # Remove new line characters
    transcript = re.sub('\s+', ' ', transcript)

    # Remove distracting single quotes
    transcript = re.sub("\'", "", transcript)

    data = [transcript]

    def lemmatization(texts, allowed_postags=('NOUN', 'ADJ', 'VERB', 'ADV')):
        """https://spacy.io/api/annotation"""
        texts_out = []
        for sent in texts:
            doc = nlp(" ".join(sent))
            texts_out.append([token.lemma_ for token in doc if token.pos_ in allowed_postags])
        return texts_out

    data_words_nostops = [[word for word in simple_preprocess(str(transcript)) if word not in stop_words]]
    data_words_bigrams = generate_bigram(data_words_nostops)

    nlp = _get_nlp()
    data_lemmatized = lemmatization(data_words_bigrams, allowed_postags=['NOUN', 'ADJ', 'VERB', 'ADV'])
    texts = data_lemmatized


    frequency = defaultdict(int)
    for text in texts:
        for token in text:
            frequency[token] += 1
    texts = [[token for token in text if frequency[token] > 1]for text in texts]

    return texts[0]
