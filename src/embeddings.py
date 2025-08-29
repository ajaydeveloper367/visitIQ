"""embeddings.py
Example code to compute embeddings for patient notes/records.

This uses sentence-transformers. For a very lightweight demo, you may switch to 'all-MiniLM-L6-v2'.
"""
from sentence_transformers import SentenceTransformer
import pandas as pd
import numpy as np
import os
import json

MODEL_NAME = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

def load_data(csv_path):
    return pd.read_csv(csv_path)

def build_corpus(df):
    # build textual documents per patient to embed
    docs = []
    for _, row in df.iterrows():
        text = f"Patient {row['patient_id']} - {row['name']}. Age {row['age']}. Condition: {row['condition']}.\nVitals: Glucose {row['glucose_mg_dL']} mg/dL; BP {int(row['bp_systolic'])}/{int(row['bp_diastolic'])}; HR {int(row['heart_rate'])}.\nHistory: {row.get('history','')}. Notes: {row.get('notes','')}.\n"
        docs.append({'patient_id': row['patient_id'], 'text': text})
    return docs

def compute_embeddings(docs, model_name=MODEL_NAME):
    model = SentenceTransformer(model_name)
    texts = [d['text'] for d in docs]
    embs = model.encode(texts, show_progress_bar=True)
    for i,d in enumerate(docs):
        d['embedding'] = embs[i].tolist()
    return docs

def save_embeddings(docs, out_path):
    with open(out_path, 'w') as f:
        json.dump(docs, f, indent=2)

if __name__ == '__main__':
    df = load_data('data/patients.csv')
    docs = build_corpus(df)
    docs = compute_embeddings(docs)
    save_embeddings(docs, 'data/patient_embeddings.json')
    print('Saved embeddings to data/patient_embeddings.json')