import gensim
from gensim.summarization import keywords
from gensim.summarization import summarize
import logging
import re
import nltk
import os

# Setting limit lower will increase load times but will weaken results.
# In total, this model has about 3,000,000 words.
# Setting limit will take the N most frequent words from that model.
def initialize(limit=100000):
    global KEYWORD_MODEL    
    print('Unpacking keyword model...')
    model_path = os.path.dirname(os.path.abspath(__file__)) + '/models/GoogleNews-vectors-negative300.bin'
    KEYWORD_MODEL = gensim.models.KeyedVectors.load_word2vec_format(model_path, binary=True, limit=limit)
    print('Model unpacked.')

def detect_keywords(transcript, keywords, threshold=0.6):
    # Split transcript by word and remove special characters.
    words = re.sub("[.,!?]", '', transcript).split()

    # Reduce transcript words and keywords down to words in model.
    words = [word for word in words if word in KEYWORD_MODEL.vocab]
    keywords = [keyword for keyword in keywords if keyword in KEYWORD_MODEL.vocab]

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