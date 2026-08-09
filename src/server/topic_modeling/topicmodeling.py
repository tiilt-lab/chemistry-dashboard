import os
import re
import pandas as pd
from collections import defaultdict

# Gensim
import gensim
import gensim.corpora as corpora
from gensim.utils import simple_preprocess

# spacy for lemmatization
import spacy

import PyPDF2

# Enable logging for gensim - optional
import logging
logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.ERROR)

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

BASE_STOP_WORDS = ('from', 'subject', 're', 'edu', 'use')

# Loaded once per process — spacy.load is ~1s and used to run on every
# /api/v1/topics request, on the request thread.
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


def process_file(file_url):
    data = []
    if file_url.endswith(".pdf"):
      pdf = PyPDF2.PdfReader(file_url)
      for page in pdf.pages:
              text = page.extract_text()
              text.rstrip('\n')
              data.append(text)

    elif file_url.endswith(".csv"):
      df = pd.read_csv(file_url)
      data = list(df['Transcript'])

    else:
      with open (file_url, "r") as myfile:
            #add the line without any newline characters
            for line in myfile:
                currentLine = line.rstrip('\n')
                if currentLine != "" and currentLine != " ":
                    data.append(currentLine)


    data = [re.sub('\S*@\S*\s?', '', sent) for sent in data]

    # Remove new line characters
    data = [re.sub('\s+', ' ', sent) for sent in data]

    # Remove distracting single quotes
    data = [re.sub("\'", "", sent) for sent in data]

    return data;


def generate_corpus(file_url, extra_stop_words):
    # Local list. The old code kept a module-global that grew on every
    # request, and its add_stop_words() dance (which returns None) silently
    # discarded the caller's extra stop words.
    stop_words = list(BASE_STOP_WORDS) + [w for w in (extra_stop_words or []) if w]

    data = []

    if (os.path.isdir(file_url)):
        for subdir, dirs, files in os.walk(file_url):
            for file in files:
                filepath = subdir + os.sep + file
                if filepath.endswith(".txt") or filepath.endswith(".pdf"):
                    data = data + process_file(filepath)
    else:
        data = process_file(file_url)

    def lemmatization(texts, allowed_postags=['NOUN', 'ADJ', 'VERB', 'ADV']):
        """https://spacy.io/api/annotation"""
        texts_out = []
        for sent in texts:
            doc = nlp(" ".join(sent))
            texts_out.append([token.lemma_ for token in doc if token.pos_ in allowed_postags])
        return texts_out

    data_words_nostops = [[word for word in simple_preprocess(str(doc)) if word not in stop_words] for doc in data]
    data_words_bigrams = generate_bigram(data_words_nostops)

    nlp = _get_nlp()
    data_lemmatized = lemmatization(data_words_bigrams, allowed_postags=['NOUN', 'ADJ', 'VERB', 'ADV'])
    texts = data_lemmatized


    frequency = defaultdict(int)
    for text in texts:
        for token in text:
            frequency[token] += 1
    texts = [[token for token in text if frequency[token] > 1]for text in texts]

    # Create Dictionary
    id2word = corpora.Dictionary(data_lemmatized)

    # Term Document Frequency
    corpus = [id2word.doc2bow(text) for text in texts]

    return id2word, texts, corpus


def generate_topic_model(id2word, texts, corpus, number_of_topics):

    [[(id2word[id], freq) for id, freq in cp] for cp in corpus[:1]]

    lda_model = gensim.models.ldamodel.LdaModel(corpus=corpus, num_topics=number_of_topics, id2word=id2word)
    return lda_model
