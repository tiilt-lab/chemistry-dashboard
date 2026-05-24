import os
import re
from unittest.util import _count_diff_all_purpose
import numpy as np
import pandas as pd
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

# plotting tools
import pyLDAvis
import pyLDAvis.gensim_models  # don't skip this
import matplotlib.pyplot as plt


import PyPDF2
#import pdfreader

# Enable logging for gensim - optional
import logging
logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.ERROR)

import warnings
warnings.filterwarnings("ignore",category=DeprecationWarning)

#TODO:
#Let the user choose topic names and percentage of the topic discusses in the conversation
#Track the usage of topic during the conversation
#Over time: the number of times, people that they have used this particular topic

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

def compute_coherence_values(dictionary, corpus, texts, limit, start=2, step=3):
        """
        Compute c_v coherence for various number of topics

        Parameters:
        ----------
        dictionary : Gensim dictionary
        corpus : Gensim corpus
        texts : List of input texts
        limit : Max num of topics

        Returns:
        -------
        model_list : List of LDA topic models
        coherence_values : Coherence values corresponding to the LDA model with respective number of topics
        """
        coherence_values = []
        model_list = []
        for num_topics in range(start, limit, step):
            model = gensim.models.wrappers.LdaMallet(mallet_path, corpus=corpus, num_topics=num_topics, id2word=dictionary)
            model_list.append(model)
            coherencemodel = CoherenceModel(model=model, texts=texts, dictionary=dictionary, coherence='c_v')
            coherence_values.append(coherencemodel.get_coherence())

        return model_list, coherence_values

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
    stop_words = ['from', 'subject', 're', 'edu', 'use']
    extra_stop_words = add_stop_words(stop_words)
    if extra_stop_words:
      stop_words = stop_words + extra_stop_words

    add_stop_words(stop_words)

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

    nlp = spacy.load("en_core_web_sm", disable=['parser', 'ner'])
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

def find_optimal_num_topics(id2word, data_lemmatized, corpus, number_of_topics):
    # Can take a long time to run.
    model_list, coherence_values = compute_coherence_values(dictionary=id2word, corpus=corpus, texts=data_lemmatized, start=2, limit=40, step=6)

    # Show graph
    limit=40; start=2; step=6;
    x = range(start, limit, step)
    plt.plot(x, coherence_values)
    plt.xlabel("Num Topics")
    plt.ylabel("Coherence score")
    plt.legend(("coherence_values"), loc='best')
    plt.show()

    # Print the coherence scores
    maxCoherence = float("-inf")
    maxM = None
    for m, cv in zip(x, coherence_values):
        print("Num Topics =", m, " has Coherence Value of", round(cv, 4))
        if cv > maxCoherence:
            maxCoherence = cv
            maxM = m

    return maxM

def visualize_topic_model(lda_model, corpus, id2word):
    pyLDAvis.enable_notebook()
    vis = pyLDAvis.gensim.prepare(lda_model, corpus, id2word)
    vis

def ntopwlst(model, features, ntopwords):
    '''Create a list of the top keywords words'''
    output = []
    for topic_idx, topic in enumerate(model.components_):
        output.append(str(topic_idx))
        output += [features[i] for i in topic.argsort()[:-ntopwords - 1:-1]]
    return output

def lsi_model(corpus,id2word,number_of_topics):
    lsi_model = gensim.models.LsiModel(corpus, id2word=id2word, num_topics=number_of_topics)  # initialize an LSI transformation
    corpus_lsi = lsi_model[corpus]
    words = 10
    print(lsi_model.print_topics(num_topics=number_of_topics, num_words=words))

def format_topics_sentences(ldamodel, corpus, texts):
    sent_topics_df = pd.DataFrame()
    for i, row in enumerate(ldamodel[corpus]):
        for j, (topic_num, prop_topic) in enumerate(row):
            if j == 0:
                wp = ldamodel.show_topic(topic_num)
                topic_keywords = ", ".join([word for word, prop in wp])
                sent_topics_df = sent_topics_df.append(pd.Series([int(topic_num), round(prop_topic,4), topic_keywords]), ignore_index=True)
            else:
                break
    sent_topics_df.columns = ['Dominant_Topic', 'Perc_Contribution', 'Topic_Keywords']
    contents = pd.Series(texts)
    sent_topics_df = pd.concat([sent_topics_df, contents], axis=1)
    return sent_topics_df
'''
ntopwords = 5
count_vect=CountVectorizer()
tf_feature_names = count_vect.get_feature_names()


pdf = process_file_pdf('Seeing the Unseen - Depression 1 Page Handout + References.pdf')
disc = process_file_csv('cstalk (1).csv')

# Get PDF data topics
id2word, texts, corpus = generate_corpus(pdf)
number_of_topics = 5
ldamodel = generate_topic_model(id2word, texts, corpus, number_of_topics)
df_topic_sents_keywords = format_topics_sentences(ldamodel=ldamodel, corpus=corpus, texts=pdf)
df_topic_pdf = df_topic_sents_keywords.reset_index()
df_topic_pdf.columns = ['Document_No', 'Dominant_Topic', 'Topic_Perc_Contrib', 'Topic_Keywords', 'Text']

# Get Dicussion data topics
id2word, texts, corpus = generate_corpus(disc)
number_of_topics = 5
ldamodel = generate_topic_model(id2word, texts, corpus, number_of_topics)

df_topic_sents_keywords = format_topics_sentences(ldamodel=ldamodel, corpus=corpus, texts=disc)
df_topic_csv = df_topic_sents_keywords.reset_index()
df_topic_csv.columns = ['Document_No', 'Dominant_Topic', 'Topic_Perc_Contrib', 'Topic_Keywords', 'Text']
'''

# Get Topics and their Prob
def get_topics_with_prob(texts):
    id2word, texts, corpus = generate_corpus(disc)
    number_of_topics = 5
    ldamodel = generate_topic_model(id2word, texts, corpus, number_of_topics)

    for i, row in enumerate(ldamodel[corpus]):
        for j, (topic_num, prop_topic) in enumerate(row):
            print(" ")
            print("Topic number: ", topic_num,", Topic probability: ", prop_topic)
            print("Topic words and their associated probability: ")
            wp = ldamodel.show_topic(topic_num)
            topic_keywords = ", ".join([word for word, prop in wp])

            for word, prop in wp:
                print(word, prop)

#print(get_topics_with_prob(texts))

