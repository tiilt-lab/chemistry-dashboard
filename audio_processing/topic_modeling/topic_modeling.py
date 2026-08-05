import os
import re
from unittest.util import _count_diff_all_purpose
import numpy as np
from pprint import pprint
from collections import defaultdict
#from tf_idf import tfidf

# Gensim
import gensim
import gensim.corpora as corpora
from gensim.utils import simple_preprocess
from gensim.models import CoherenceModel
from collections import Counter
from sklearn.feature_extraction.text import CountVectorizer

# spacy for lemmatization
import spacy


from nltk.corpus import stopwords
stop_words = []#stopwords.words('english')


mallet_path = '~/mallet-2.0.8/bin/mallet' # update this path
def add_stop_words(words):
    stop_words.extend(words)

def sent_to_words(sentences):
    for sentence in sentences:
        yield(gensim.utils.simple_preprocess(str(sentence), deacc=True))  # deacc=True removes punctuations

def generate_bigram(data_words):
    bigram = gensim.models.Phrases(data_words, min_count=5, threshold=100) # higher threshold fewer phrases.
    bigram_mod = gensim.models.phrases.Phraser(bigram)

    return [bigram_mod[doc] for doc in data_words]

def generate_trigram(data_words, bigram):
    trigram = gensim.models.Phrases(bigram[data_words], threshold=100)
    trigram_mod = gensim.models.phrases.Phraser(trigram)

    return trigram, trigram_mod

def preprocess_transcript(transcript, extra_stop_words):
    stop_words = ['from', 'subject', 're', 'edu', 'use']
    extra_stop_words = add_stop_words(stop_words)
    if extra_stop_words:
      stop_words = stop_words + extra_stop_words

    transcript = re.sub('\S*@\S*\s?', '', transcript)

    # Remove new line characters
    transcript = re.sub('\s+', ' ', transcript)

    # Remove distracting single quotes
    transcript = re.sub("\'", "", transcript)

    add_stop_words(stop_words)

    data = [transcript]

    def lemmatization(texts, allowed_postags=['NOUN', 'ADJ', 'VERB', 'ADV']):
        """https://spacy.io/api/annotation"""
        texts_out = []
        for sent in texts:
            doc = nlp(" ".join(sent))
            texts_out.append([token.lemma_ for token in doc if token.pos_ in allowed_postags])
        return texts_out

    data_words_nostops = [[word for word in simple_preprocess(str(transcript)) if word not in stop_words]]
    data_words_bigrams = generate_bigram(data_words_nostops)

    nlp = spacy.load("en_core_web_sm", disable=['parser', 'ner'])
    data_lemmatized = lemmatization(data_words_bigrams, allowed_postags=['NOUN', 'ADJ', 'VERB', 'ADV'])
    texts = data_lemmatized


    frequency = defaultdict(int)
    for text in texts:
        for token in text:
            frequency[token] += 1
    texts = [[token for token in text if frequency[token] > 1]for text in texts]

    return texts[0]
