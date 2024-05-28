from collections import Counter
import numpy as np

def tfidf(text):
    """
    term frequency: number of words occurence in documents 
                    / 
                    number of total words in document

    """

    # document frequency
    df = {}
    for i in range(len(text)):
        tokens = text[i]
        for w in tokens:
            try:
                df[w].add(i)
            except:
                df[w] = {i}

    # get the unique words in term frequency
    for i in df:
        df[i] = len(df[i])
    
    # total vocobulary
    total_vocab = [x for x in df]

    # calculating the tf*idf
    tf_idf = {}
    doc = 0 
    for i in range(len(text)):
        tokens = text[i]
        counter = Counter(tokens)
        words_count = len(tokens)
        count = 0
        for token in np.unique(tokens):
            tf = counter[token] / words_count
            d_f = df[token]
            idf = np.log(len(text)/d_f+1)
            tf_idf[doc, token] = tf * idf
        doc += 1
    
def cosine_similarity(a, b):
    cos_sim = np.dot(a, b)/np.linalg.norm(a)*np.linalg.norm(b)
    return cos_sim