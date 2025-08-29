"""vectorstore.py
Placeholder wrapper for storing and querying embeddings.
This example uses Chromadb (local) style API.
"""
import chromadb
from chromadb.config import Settings
import os
import json

CHROMA_DIR = os.getenv('CHROMA_DIR', 'chroma_db')

def create_client():
    client = chromadb.Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory=CHROMA_DIR))
    return client

def load_embeddings_from_file(client, collection_name, embeddings_json_path):
    with open(embeddings_json_path, 'r') as f:
        docs = json.load(f)
    # create collection
    coll = client.create_collection(name=collection_name)
    ids = [str(d['patient_id']) for d in docs]
    metadatas = [{'name': d.get('patient_id')} for d in docs]
    documents = [d['text'] for d in docs]
    embeddings = [d['embedding'] for d in docs]
    coll.add(ids=ids, metadatas=metadatas, documents=documents, embeddings=embeddings)
    client.persist()
    return coll

def query_collection(client, collection_name, query_emb, n=3):
    coll = client.get_collection(collection_name)
    results = coll.query(query_embeddings=[query_emb], n_results=n)
    return results