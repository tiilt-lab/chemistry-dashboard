from collections import defaultdict
import pandas as pd

"""
    Term frequency: number of times term occurs in a document. 
        TF = occurence of term in a document/ the number of words in a document
        For example, word 'cat' occurs 5 times and there are 100 words in a document. So it's 5/100 = 0.5

    Inverse document frequency: how common or rare words is accross all documents in the collection.
        IDF = log (total number of documents/(the number of documents containing the word+1)
        low IDF score = means words that are the most occuring has a low IDF score
        high IDF score = means words that are the least occuring

"""
df = pd.read_csv("cstalk (1).csv")

# Term Frequency
word_freq_in_doc = defaultdict
for word in df.Transcript:
    word_freq_in_doc[word] += 1
print(word_freq_in_doc)

