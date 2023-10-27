import pandas as pd
import re
import nltk
from nltk import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

nltk.download('punkt')
nltk.download('stopwords')

def is_question_sentence(sentence):
    return sentence.strip().endswith('?')

def preprocess_text(text):
    stop_words = set(stopwords.words('english'))
    words = [word.lower() for word in word_tokenize(text) if word.isalpha()]
    words = [word for word in words if word not in stop_words]
    return ' '.join(words)

def calculate_relevance_score(questions, answers):
    vectorizer = CountVectorizer(max_df=0.75)
    question_vectors = vectorizer.fit_transform(questions)
    answer_vectors = vectorizer.transform(answers)
    print(answer_vectors)
    similarity_scores = cosine_similarity(answer_vectors, question_vectors)
    return similarity_scores.diagonal()

def extract_qa_pairs(texts):
    questions = []
    answers = []

    for text in texts:
        sentences = text.split('?')

        for i, sentence in enumerate(sentences):
            if i < len(sentences)-1:
                sentence += '?'

            if '?' in sentence:
                question = sentence.strip()
                questions.append(question)
                
                question_index = text.find(sentence)
                if i + 1 < len(sentences):
                    answer = sentences[i + 1].strip()
                    answers.append(answer)
                else:
                    answers.append(None) 
                print(question)
    return questions, answers

def create_qa_dataframe(texts):
    questions, answers = extract_qa_pairs(texts)
    relevance_scores = calculate_relevance_score(questions, answers)
    data = {'Question': questions, 'Answer': answers, 'RelevanceScore': relevance_scores}
    df = pd.DataFrame(data)
    return df

if __name__ == "__main__":
    # texts = [
    #     "The sun rises in the east. Does the sun rise in the east? Yes, the sun rises in the east.",
    #     "What is the capital of France? The capital of France is Paris.",
    #     "Roses are red. Are roses blue? No, roses are red."
    # ]
    df = pd.read_csv("cstalk (1).csv")
    texts = list(df['Transcript'])
    
    df = create_qa_dataframe(texts)
    print(df)
    df.to_csv("questions2.csv")