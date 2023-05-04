import pandas as pd
# from pycorenlp import StanfordCoreNLP
import stanfordcorenlp
from stanfordcorenlp import StanfordCoreNLP

# https://github.com/kartikn27/nlp-question-detection/blob/master/method1.py

"""
    TODO:
     1. How to track actual answers to questions in the discussion?
        get the answers to a particular questions 
        1.a understand what answers are related to questions -> answer classification
        2.a the depth of these answers -> how its close to ground truth

    Track the answers to the questions during the discussion -> so highlight the text related to the questions?

    Okay then, it's going to like something, 

    question = "text"
    assosciated answer = "text"
    similarity score = int 

"""

class isQuestionBasic():
    
    # Init Constructor
    # Initialize StanfordCore NLP local instance on port 9000
    def __init__(self):
        self.nlp = StanfordCoreNLP('/Users/azizamirsaidova/Downloads/stanford-corenlp-4.5.4/CoreNLP-to-HTML.xsl')
        
    # Input: Sentence to be predicted
    # Processing: 1. Uses Stanfors NLP's 'annotate' method to create Parse Tree
    # 2. Checks for occurence of 'SQ' or 'SBARQ' in the parse tree
    # Return: 1 - If sentence is question | 0 - If sentence is not a question
    def isQuestion(self, sentence):
        if '?' in sentence:
            return 1
        output = self.nlp.annotate(sentence, properties={
            'annotators': 'parse',
            'outputFormat': 'json',
            'timeout': 1000,
        })

        if ('SQ' or 'SBARQ') in output['sentences'][0]["parse"]:
            return 1    
        else:
            return 0

isQuestionBasic_obj = isQuestionBasic()
df = pd.read_csv("cstalk (1).csv")
df['is_question'] = df['Transcript'].apply(isQuestionBasic_obj.isQuestion)
# df.to_csv('method1_output.csv', index=False)