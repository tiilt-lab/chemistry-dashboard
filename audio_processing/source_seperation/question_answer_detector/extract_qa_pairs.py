import csv
import torch
from transformers import AutoTokenizer, AutoModel
from scipy.spatial.distance import cosine

# Load pre-trained model tokenizer and model
tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
model = AutoModel.from_pretrained("bert-base-uncased")

def embed_text(text):
    tokens = tokenizer(text, padding=True, truncation=True, return_tensors="pt")
    with torch.no_grad():
        embeddings = model(**tokens).last_hidden_state.mean(dim=1)
    return embeddings.numpy()

def extract_qa_pairs(filename):
    qa_pairs = []
    
    with open(filename, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        
        for row in reader:
            transcript = row['Transcript']
            sentences = transcript.split(". ")
            
            for i in range(len(sentences)-1):
                question_embedding = embed_text(sentences[i])
                answer_embedding = embed_text(sentences[i+1])
                
                similarity_score = 1 - cosine(question_embedding, answer_embedding)
                
                if "?" in sentences[i]:  # Basic way to identify questions
                    qa_pairs.append({
                        'question': sentences[i],
                        'answer': sentences[i+1],
                        'relevance_score': similarity_score
                    })
                    
    return qa_pairs

# Extract question-answer pairs and print them
qa_pairs = extract_qa_pairs('cstalk (1).csv')

for i, pair in enumerate(qa_pairs, 1):
    print(f"Pair {i}")
    print(f"Question: {pair['question']}")
    print(f"Answer: {pair['answer']}")
    print(f"Relevance Score: {pair['relevance_score']}\n")
