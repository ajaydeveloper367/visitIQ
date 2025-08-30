"""
src/prioritizer.py - robust local-vectorstore RAG prioritizer

- Uses sentence-transformers to compute embeddings
- Persists embeddings and docs to disk (np.save + json)
- Uses sklearn.NearestNeighbors (cosine) to retrieve top-k similar docs
- Calls OllamaLLM when available; otherwise falls back to rule-based priority
"""

import os
import re
import json
import numpy as np
import pandas as pd
from typing import Dict, Any, List

# Defer heavy imports to speed up app startup
def _import_heavy_dependencies():
    """Import heavy ML dependencies only when needed"""
    global SentenceTransformer, NearestNeighbors
    try:
        from sentence_transformers import SentenceTransformer
        from sklearn.neighbors import NearestNeighbors
        return True
    except ImportError as e:
        print(f"Warning: Heavy ML dependencies not available: {e}")
        return False

# Global variables to hold classes after import
SentenceTransformer = None
NearestNeighbors = None

# Try to import OllamaLLM (langchain-ollama). If not present, we'll fallback.
try:
    from langchain_ollama.llms import OllamaLLM
except Exception:
    OllamaLLM = None

# -----------------------
# Config
# -----------------------
PERSIST_DIR = os.getenv("CHROMA_DIR", "chroma_db")  # reused name for compatibility
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
EMBEDDINGS_FILE = os.path.join(PERSIST_DIR, "embeddings.npy")
DOCS_FILE = os.path.join(PERSIST_DIR, "docs.json")
IDS_FILE = os.path.join(PERSIST_DIR, "ids.json")
TOP_K = int(os.getenv("RAG_TOP_K", "3"))
OLLAMA_BASE_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
OLLAMA_MODEL_NAME = os.getenv("OLLAMA_MODEL", "llama3")

# -----------------------
# Simple rule-based fallback (same logic as before)
# -----------------------
EMERGENCY_GLUCOSE = 400
HIGH_GLUCOSE = 300
HIGH_BP_SYS = 180
HIGH_BP_DIA = 110

def rule_based_priority_row(row: Dict[str, Any]) -> Dict[str, Any]:
    reasons = []
    score = 0
    # glucose
    try:
        g = float(row.get("glucose_mg_dL", 0) or 0)
    except Exception:
        g = 0.0
    if g >= EMERGENCY_GLUCOSE:
        reasons.append(f"Glucose {g} >= {EMERGENCY_GLUCOSE} (hyperglycemic crisis risk)")
        score += 50
    elif g >= HIGH_GLUCOSE:
        reasons.append(f"Glucose {g} >= {HIGH_GLUCOSE} (very high)")
        score += 25
    elif g >= 200:
        reasons.append(f"Glucose {g} >= 200 (elevated)")
        score += 10

    # BP
    try:
        sys = float(row.get("bp_systolic", 0) or 0)
        dia = float(row.get("bp_diastolic", 0) or 0)
    except Exception:
        sys = dia = 0.0
    if sys >= HIGH_BP_SYS or dia >= HIGH_BP_DIA:
        reasons.append(f"BP {int(sys)}/{int(dia)} >= {HIGH_BP_SYS}/{HIGH_BP_DIA} (hypertensive emergency)")
        score += 40
    elif sys >= 160 or dia >= 100:
        reasons.append(f"BP {int(sys)}/{int(dia)} elevated")
        score += 20

    # HR
    try:
        hr = float(row.get("heart_rate", 0) or 0)
    except Exception:
        hr = 0.0
    if hr >= 120:
        reasons.append(f"HR {int(hr)} >= 120 (tachycardia)")
        score += 10

    # age & comorbidity
    try:
        age = int(row.get("age", 0) or 0)
    except Exception:
        age = 0
    if age >= 65:
        reasons.append("Age >= 65")
        score += 5

    history = str(row.get("history", "")).lower()
    if any(x in history for x in ["ckd", "kidney", "stroke", "cardiac", "heart"]):
        reasons.append("High-risk history (CKD/stroke/heart)")
        score += 20

    if score >= 60:
        level = "Emergency"
    elif score >= 35:
        level = "High"
    elif score >= 15:
        level = "Medium"
    else:
        level = "Low"

    return {"priority_level": level, "score": int(score), "reasons": reasons}

# -----------------------
# Local vectorstore (embeddings + NN)
# -----------------------
def _ensure_persist_dir():
    os.makedirs(PERSIST_DIR, exist_ok=True)

def build_vectorstore_from_csv(csv_path: str, persist_directory: str = PERSIST_DIR) -> Dict[str, Any]:
    """
    Creates embeddings and stores:
      - embeddings.npy
      - docs.json (list of doc texts)
      - ids.json (list of ids)
    Returns a dict summary.
    """
    _ensure_persist_dir()
    df = pd.read_csv(csv_path)

    docs = []
    ids = []
    for _, row in df.iterrows():
        pid = str(row.get("patient_id", ""))
        txt = (
            f"Patient ID: {pid}. Name: {row.get('name','')}. Age: {row.get('age','')}. "
            f"Condition: {row.get('condition','')}. Vitals: Glucose {row.get('glucose_mg_dL','')}; "
            f"BP {row.get('bp_systolic','')}/{row.get('bp_diastolic','')}; HR {row.get('heart_rate','')}. "
            f"History: {row.get('history','')}. Notes: {row.get('notes','')}."
        )
        ids.append(pid)
        docs.append(txt)

    # embeddings (with lazy import)
    if not _import_heavy_dependencies():
        raise RuntimeError("ML dependencies not available for building vectorstore")
    
    model = SentenceTransformer(EMBEDDING_MODEL)
    emb = model.encode(docs, show_progress_bar=False)
    np.save(os.path.join(persist_directory, "embeddings.npy"), emb)
    with open(os.path.join(persist_directory, "docs.json"), "w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False, indent=2)
    with open(os.path.join(persist_directory, "ids.json"), "w", encoding="utf-8") as f:
        json.dump(ids, f, ensure_ascii=False, indent=2)

    return {"n": len(docs), "persist_directory": persist_directory}

def _load_local_vectorstore(persist_directory: str = PERSIST_DIR):
    """
    Returns (docs:list[str], embeddings:np.ndarray) or (None,None) if not present.
    """
    docs_path = os.path.join(persist_directory, "docs.json")
    emb_path = os.path.join(persist_directory, "embeddings.npy")
    if not os.path.exists(docs_path) or not os.path.exists(emb_path):
        return None, None
    with open(docs_path, "r", encoding="utf-8") as f:
        docs = json.load(f)
    emb = np.load(emb_path)
    return docs, emb

def _query_similar_docs(query_text: str, k: int = TOP_K, persist_directory: str = PERSIST_DIR) -> List[str]:
    """
    Compute embedding for query and return top-k docs (as texts).
    """
    docs, emb = _load_local_vectorstore(persist_directory)
    if docs is None or emb is None or len(docs) == 0:
        return []

    # embed query (with lazy import)
    if not _import_heavy_dependencies():
        return []  # Fallback to empty if ML dependencies not available
    
    model = SentenceTransformer(EMBEDDING_MODEL)
    q_emb = model.encode([query_text], show_progress_bar=False)
    # fit a nearest neighbor on the stored embeddings (fast enough locally)
    nn = NearestNeighbors(n_neighbors=min(k, len(docs)), metric="cosine")
    nn.fit(emb)
    dists, idxs = nn.kneighbors(q_emb, return_distance=True)
    idxs = idxs[0].tolist()
    return [docs[i] for i in idxs]

# -----------------------
# Ollama call helpers
# -----------------------
def _parse_json_from_text(text: str):
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        # greedy extract
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
    return None

def _call_ollama(prompt: str, model_name: str = OLLAMA_MODEL_NAME, base_url: str = OLLAMA_BASE_URL, timeout: int = 15):
    """
    Use OllamaLLM.invoke(prompt) if available. If OllamaLLM is missing, raise.
    """
    if OllamaLLM is None:
        raise RuntimeError("OllamaLLM is not available in the environment.")
    # instantiate; pass base_url if supported by the class (langchain-ollama versions differ)
    try:
        # OllamaLLM signature may accept model and base_url
        llm = OllamaLLM(model=model_name, base_url=base_url)
    except TypeError:
        # fallback: try without base_url
        llm = OllamaLLM(model=model_name)
    # call .invoke() which returns output text for many versions
    out = llm.invoke(prompt)
    if isinstance(out, (dict, list)):
        return json.dumps(out)
    return str(out)

# -----------------------
# RAG prioritization entrypoint
# -----------------------
def rag_prioritize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Given one patient row, run RAG -> Ollama to return priority JSON.
    Falls back to rule-based on any failure.
    """
    # create summary text
    patient_text = (
        f"Name: {row.get('name','')}. Age: {row.get('age','')}. "
        f"Condition: {row.get('condition','')}. "
        f"Vitals: Glucose {row.get('glucose_mg_dL','')}; BP {row.get('bp_systolic','')}/{row.get('bp_diastolic','')}; HR {row.get('heart_rate','')}. "
        f"History: {row.get('history','')}. Notes: {row.get('notes','')}"
    )

    # retrieve contexts
    try:
        docs = _query_similar_docs(patient_text, k=TOP_K)
    except Exception:
        docs = []

    retrieved_text = "\n\n---\n\n".join(docs) if docs else ""

    prompt = (
        "You are a clinical assistant. Use the provided patient record and relevant contexts to decide a priority level.\n\n"
        "Return ONLY valid JSON with keys: priority_level (Emergency/High/Medium/Low), score (number, optional), reasons (array of short strings).\n\n"
        "Patient Record:\n"
        f"{patient_text}\n\n"
        "Relevant Contexts:\n"
        f"{retrieved_text}\n\n"
        "Respond now with JSON only."
    )

    # Get rule-based result first as fallback and for scoring consistency
    rule_result = rule_based_priority_row(row)
    
    # attempt Ollama
    try:
        llm_text = _call_ollama(prompt, model_name=os.getenv("OLLAMA_MODEL", OLLAMA_MODEL_NAME), base_url=os.getenv("OLLAMA_URL", OLLAMA_BASE_URL))
        parsed = _parse_json_from_text(llm_text)
        if isinstance(parsed, dict) and parsed.get("priority_level"):
            if "reasons" in parsed and isinstance(parsed["reasons"], str):
                parsed["reasons"] = [parsed["reasons"]]
            
            # Preserve rule-based score if RAG doesn't provide one or provides a low one
            if not parsed.get("score") or parsed.get("score", 0) < rule_result.get("score", 0):
                parsed["score"] = rule_result.get("score", 0)
            
            # Combine reasons from both systems
            rag_reasons = parsed.get("reasons", [])
            rule_reasons = rule_result.get("reasons", [])
            if rag_reasons and rule_reasons:
                # Add rule-based reasons if they provide additional medical context
                all_reasons = list(rag_reasons)
                for reason in rule_reasons:
                    if not any(reason.lower() in r.lower() for r in rag_reasons):
                        all_reasons.append(f"Rule-based: {reason}")
                parsed["reasons"] = all_reasons
            
            return parsed
    except Exception as e:
        print("Ollama call failed or returned invalid JSON:", e)

    # fallback rule-based
    return rule_result

def rag_prioritize(df_row):
    if hasattr(df_row, "to_dict"):
        row = df_row.to_dict()
    else:
        row = dict(df_row)
    return rag_prioritize_row(row)


# -----------------------
# Simple module test
# -----------------------
if __name__ == "__main__":
    sample_csv = "data/patients.csv"
    if os.path.exists(sample_csv):
        print("Building vectorstore from", sample_csv)
        print(build_vectorstore_from_csv(sample_csv))
    else:
        print("No sample CSV found at data/patients.csv")
