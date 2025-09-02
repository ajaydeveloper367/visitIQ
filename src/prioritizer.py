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

# Performance optimization: Cache loaded models and vectorstore
_model_cache = None
_vectorstore_cache = None
_embedding_cache = {}

# Try to import OllamaLLM (langchain-ollama). If not present, we'll fallback.
try:
    from langchain_ollama.llms import OllamaLLM
except Exception:
    OllamaLLM = None
try:
    import requests as _requests
except Exception:
    _requests = None

# -----------------------
# Config
# -----------------------
# Support both package and script imports
try:
    from .config import CHROMA_DIR as PERSIST_DIR, RAG_TOP_K, OLLAMA_URL as CFG_OLLAMA_URL, OLLAMA_MODEL as CFG_OLLAMA_MODEL
except Exception:
    from config import CHROMA_DIR as PERSIST_DIR, RAG_TOP_K, OLLAMA_URL as CFG_OLLAMA_URL, OLLAMA_MODEL as CFG_OLLAMA_MODEL
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
EMBEDDINGS_FILE = os.path.join(PERSIST_DIR, "embeddings.npy")
DOCS_FILE = os.path.join(PERSIST_DIR, "docs.json")
IDS_FILE = os.path.join(PERSIST_DIR, "ids.json")
TOP_K = int(os.getenv("RAG_TOP_K", str(RAG_TOP_K)))
OLLAMA_BASE_URL = os.getenv("OLLAMA_URL", CFG_OLLAMA_URL)
OLLAMA_MODEL_NAME = os.getenv("OLLAMA_MODEL", CFG_OLLAMA_MODEL)

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
    Legacy helper: Build vectorstore ONLY from patients CSV.
    Prefer build_vectorstore_from_sources for full ingestion.
    """
    return build_vectorstore_from_sources(data_dir=os.path.dirname(csv_path) or ".", persist_directory=persist_directory)

def _read_json_safely(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def build_vectorstore_from_sources(data_dir: str = "data", persist_directory: str = PERSIST_DIR) -> Dict[str, Any]:
    """
    Build embeddings from ALL core sources into a single lightweight local vectorstore.
    Sources:
      - patients.csv
      - practitioners.json (physicians)
      - slots.json (available slots)
      - schedules.json (optional)
    Output:
      - chroma_db/embeddings.npy
      - chroma_db/docs.json
      - chroma_db/ids.json
    """
    # Ensure custom persist directory exists
    os.makedirs(persist_directory, exist_ok=True)

    docs: List[str] = []
    ids: List[str] = []
    metadatas: List[Dict[str, Any]] = []

    # Patients
    patients_csv = os.path.join(data_dir, "patients.csv")
    if os.path.exists(patients_csv):
        df = pd.read_csv(patients_csv)
        for _, row in df.iterrows():
            pid = str(row.get("patient_id", ""))
            txt = (
                f"[PATIENT] ID:{pid}; Name:{row.get('name','')}; Age:{row.get('age','')}; "
                f"Condition:{row.get('condition','')}; Glucose:{row.get('glucose_mg_dL','')}; "
                f"BP:{row.get('bp_systolic','')}/{row.get('bp_diastolic','')}; HR:{row.get('heart_rate','')}; "
                f"History:{row.get('history','')}; Notes:{row.get('notes','')}"
            )
            ids.append(f"patient:{pid}")
            docs.append(txt)
            metadatas.append({
                "type": "patient",
                "patient_id": pid,
                "name": row.get('name',''),
                "age": row.get('age',''),
                "condition": row.get('condition',''),
                "glucose_mg_dL": row.get('glucose_mg_dL',''),
                "bp_systolic": row.get('bp_systolic',''),
                "bp_diastolic": row.get('bp_diastolic',''),
                "heart_rate": row.get('heart_rate',''),
                "history": row.get('history',''),
                "notes": row.get('notes','')
            })

    # Physicians / Practitioners
    practitioners_json = os.path.join(data_dir, "practitioners.json")
    practitioners = _read_json_safely(practitioners_json) or []
    for p in practitioners:
        pid = str(p.get("id", ""))
        name = p.get("name", "")
        specialty = p.get("specialty", p.get("department", ""))
        dept = p.get("department", specialty)
        txt = f"[PHYSICIAN] ID:{pid}; Name:{name}; Specialty:{specialty}; Department:{dept}"
        ids.append(f"physician:{pid}")
        docs.append(txt)
        metadatas.append({
            "type": "physician",
            "id": pid,
            "name": name,
            "specialty": specialty,
            "department": dept
        })

    # Slots (optional)
    slots_json = os.path.join(data_dir, "slots.json")
    slots = _read_json_safely(slots_json) or []
    for s in slots:
        sid = str(s.get("id", ""))
        practitioner_id = s.get("practitioner_id", "")
        start = s.get("start", "")
        end = s.get("end", "")
        status = s.get("status", "")
        specialty = s.get("specialty", "")
        txt = (
            f"[SLOT] ID:{sid}; PractitionerID:{practitioner_id}; Specialty:{specialty}; "
            f"Start:{start}; End:{end}; Status:{status}"
        )
        ids.append(f"slot:{sid}")
        docs.append(txt)
        metadatas.append({
            "type": "slot",
            "id": sid,
            "practitioner_id": practitioner_id,
            "specialty": specialty,
            "start": start,
            "end": end,
            "status": status
        })

    if len(docs) == 0:
        return {"n": 0, "persist_directory": persist_directory}

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
    with open(os.path.join(persist_directory, "metadatas.json"), "w", encoding="utf-8") as f:
        json.dump(metadatas, f, ensure_ascii=False, indent=2)

    # Clear caches so new vectorstore is picked up
    clear_caches()
    return {"n": len(docs), "persist_directory": persist_directory}

def _get_cached_model():
    """Get cached SentenceTransformer model for performance"""
    global _model_cache
    if _model_cache is None:
        if not _import_heavy_dependencies():
            return None
        _model_cache = SentenceTransformer(EMBEDDING_MODEL)
    return _model_cache

def _load_local_vectorstore(persist_directory: str = PERSIST_DIR):
    """
    Returns (docs:list[str], embeddings:np.ndarray) or (None,None) if not present.
    Uses caching for performance on repeated access.
    """
    global _vectorstore_cache
    
    # Check cache first
    if _vectorstore_cache is not None:
        return _vectorstore_cache
    
    docs_path = os.path.join(persist_directory, "docs.json")
    emb_path = os.path.join(persist_directory, "embeddings.npy")
    if not os.path.exists(docs_path) or not os.path.exists(emb_path):
        return None, None
    with open(docs_path, "r", encoding="utf-8") as f:
        docs = json.load(f)
    emb = np.load(emb_path)
    
    # Cache for next time
    _vectorstore_cache = (docs, emb)
    return docs, emb

def _query_similar_docs(query_text: str, k: int = TOP_K, persist_directory: str = PERSIST_DIR) -> List[str]:
    """
    Compute embedding for query and return top-k docs (as texts).
    Optimized with caching.
    """
    global _embedding_cache
    
    # Check cache first
    cache_key = f"{query_text}:{k}:{persist_directory}"
    if cache_key in _embedding_cache:
        return _embedding_cache[cache_key]
    
    docs, emb = _load_local_vectorstore(persist_directory)
    if docs is None or emb is None or len(docs) == 0:
        return []

    # Use cached model
    model = _get_cached_model()
    if model is None:
        return []
    
    q_emb = model.encode([query_text], show_progress_bar=False)
    
    # Use cached NN instance if available
    if not hasattr(_query_similar_docs, '_nn_instance') or _query_similar_docs._nn_instance is None:
        if not _import_heavy_dependencies():
            return []
        _query_similar_docs._nn_instance = NearestNeighbors(n_neighbors=min(k, len(docs)), metric="cosine")
        _query_similar_docs._nn_instance.fit(emb)
    
    dists, idxs = _query_similar_docs._nn_instance.kneighbors(q_emb, return_distance=True)
    idxs = idxs[0].tolist()
    result = [docs[i] for i in idxs]
    
    # Cache the result
    _embedding_cache[cache_key] = result
    return result

# Initialize NN instance cache
_query_similar_docs._nn_instance = None

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

def _call_ollama(prompt: str, model_name: str = OLLAMA_MODEL_NAME, base_url: str = OLLAMA_BASE_URL, timeout: int = 20):
    """Call Ollama LLM.
    1) Try langchain_ollama if available
    2) Fallback to direct HTTP POST /api/generate (non-stream)
    Raises if both paths fail.
    """
    last_err: Exception | None = None
    # Path 1: langchain_ollama
    if OllamaLLM is not None:
        try:
            try:
                llm = OllamaLLM(model=model_name, base_url=base_url)
            except TypeError:
                llm = OllamaLLM(model=model_name)
            out = llm.invoke(prompt)
            if isinstance(out, (dict, list)):
                return json.dumps(out)
            return str(out)
        except Exception as e:
            last_err = e
    # Path 2: direct HTTP to Ollama
    if _requests is not None:
        try:
            resp = _requests.post(
                f"{base_url}/api/generate",
                json={"model": model_name, "prompt": prompt, "stream": False, "options": {"temperature": 0.1, "num_ctx": 4096}},
                timeout=timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            text = data.get("response") or data.get("message") or ""
            return str(text)
        except Exception as e:
            last_err = e
    raise RuntimeError(f"LLM call failed: {last_err}")

# -----------------------
# RAG prioritization entrypoint
# -----------------------
def rag_prioritize_batch(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    OPTIMIZED: Process multiple patients in batch for significant performance improvement.
    Uses vectorized operations and async processing where possible.
    """
    if not rows:
        return []
    
    # Quick rule-based processing first (vectorized where possible)
    rule_results = [rule_based_priority_row(row) for row in rows]
    
    # Batch process text creation
    patient_texts = []
    for row in rows:
        patient_text = (
            f"Name: {row.get('name','')}. Age: {row.get('age','')}. "
            f"Condition: {row.get('condition','')}. "
            f"Vitals: Glucose {row.get('glucose_mg_dL','')}; BP {row.get('bp_systolic','')}/{row.get('bp_diastolic','')}; HR {row.get('heart_rate','')}. "
            f"History: {row.get('history','')}. Notes: {row.get('notes','')}"
        )
        patient_texts.append(patient_text)
    
    # 🔁 TRUE RAG: Retrieve similar cases from vectorstore per patient
    # Falls back gracefully to empty context if vectorstore missing
    retrieved_contexts: List[str] = []
    for patient_text in patient_texts:
        sims = _query_similar_docs(patient_text, k=TOP_K)
        retrieved_contexts.append("\n".join(sims) if sims else "")
    
    # ⚡ OPTIMIZED: Single batch LLM call for all patients instead of individual calls
    try:
        # Streamlined prompt for better JSON parsing
        batch_prompt = "Medical triage for multiple patients. Return JSON array only.\n\n"
        
        # Add patients in compact format
        for i, patient_text in enumerate(patient_texts):
            ctx = retrieved_contexts[i]
            if ctx:
                batch_prompt += f"{i+1}. {patient_text}\nSimilar Cases:\n{ctx}\n\n"
            else:
                batch_prompt += f"{i+1}. {patient_text}\nSimilar Cases:\n(none)\n\n"
        
        batch_prompt += (
            f"\nReturn JSON array with {len(rows)} objects: "
            '[{"priority_level": "Emergency/High/Medium/Low", "score": number, "reasons": ["reason1"]}]\n'
            "JSON:"
        )
        
        # Single LLM call for all patients - MAJOR performance boost!
        # Ensure we propagate configured base URL and model explicitly
        llm_text = _call_ollama(batch_prompt, model_name=OLLAMA_MODEL_NAME, base_url=OLLAMA_BASE_URL)
        
        # Parse the batch response
        batch_parsed = _parse_json_from_text(llm_text)
        
        if isinstance(batch_parsed, list) and len(batch_parsed) >= len(rows):
            results = []
            for i, (rule_result, llm_result) in enumerate(zip(rule_results, batch_parsed[:len(rows)])):
                if isinstance(llm_result, dict) and llm_result.get("priority_level"):
                    # Process LLM result
                    if "reasons" in llm_result and isinstance(llm_result["reasons"], str):
                        llm_result["reasons"] = [llm_result["reasons"]]
                    
                    # Preserve rule-based score if LLM doesn't provide one or provides a low one
                    if not llm_result.get("score") or llm_result.get("score", 0) < rule_result.get("score", 0):
                        llm_result["score"] = rule_result.get("score", 0)
                    
                    # Debug info for UI transparency
                    try:
                        llm_result["debug_context"] = retrieved_contexts[i]
                    except Exception:
                        llm_result["debug_context"] = ""
                    llm_result["reasoning_source"] = llm_result.get("reasoning_source", "🧠 LLM Medical Analysis")

                    # Combine reasons efficiently
                    rag_reasons = llm_result.get("reasons", [])
                    rule_reasons = rule_result.get("reasons", [])
                    if rag_reasons and rule_reasons:
                        all_reasons = list(rag_reasons)
                        for reason in rule_reasons:
                            if not any(reason.lower() in r.lower() for r in rag_reasons):
                                all_reasons.append(f"Rule-based: {reason}")
                        llm_result["reasons"] = all_reasons
                    
                    results.append(llm_result)
                else:
                    # Fallback case gets debug markers
                    rule_result["debug_context"] = ""
                    rule_result["reasoning_source"] = "📋 Clinical Rules (LLM Batch Failed)"
                    results.append(rule_result)
        else:
            print(f"⚠️ Batch LLM parsing failed, using rule-based for all {len(rows)} patients")
            results = []
            for rr in rule_results:
                rr["debug_context"] = ""
                rr["reasoning_source"] = "📋 Clinical Rules (LLM Batch Failed)"
                results.append(rr)
            
    except Exception as e:
        print(f"⚠️ Batch LLM call failed: {e}, using rule-based for all {len(rows)} patients")
        results = rule_results
    
    return results

# Initialize NN instance cache for batch processing
rag_prioritize_batch._nn_instance = None

def rag_prioritize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Given one patient row, run RAG -> Ollama to return priority JSON.
    NOW OPTIMIZED: Uses batch processing even for single items for better performance.
    """
    # Use optimized batch function even for single items
    batch_results = rag_prioritize_batch([row])
    return batch_results[0] if batch_results else rule_based_priority_row(row)

def rag_prioritize(df_row):
    if hasattr(df_row, "to_dict"):
        row = df_row.to_dict()
    else:
        row = dict(df_row)
    return rag_prioritize_row(row)


# -----------------------
# Performance optimization functions
# -----------------------
def preload_models():
    """
    Preload models and cache for faster first-run performance.
    Call this during app initialization for best hackathon demo experience.
    """
    try:
        # Preload sentence transformer
        model = _get_cached_model()
        if model is not None:
            print("✅ SentenceTransformer model cached")
        
        # Preload vectorstore
        docs, emb = _load_local_vectorstore()
        if docs is not None and emb is not None:
            print(f"✅ Vectorstore cached: {len(docs)} documents")
            
            # Initialize NN instances
            if _import_heavy_dependencies():
                nn_instance = NearestNeighbors(n_neighbors=min(TOP_K, len(docs)), metric="cosine")
                nn_instance.fit(emb)
                _query_similar_docs._nn_instance = nn_instance
                rag_prioritize_batch._nn_instance = nn_instance
                print("✅ NearestNeighbors instances cached")
        
        return True
    except Exception as e:
        print(f"Warning: Model preloading failed: {e}")
        return False

def clear_caches():
    """Clear all caches to free memory"""
    global _model_cache, _vectorstore_cache, _embedding_cache
    _model_cache = None
    _vectorstore_cache = None
    _embedding_cache.clear()
    
    # Clear NN instances
    if hasattr(_query_similar_docs, '_nn_instance'):
        _query_similar_docs._nn_instance = None
    if hasattr(rag_prioritize_batch, '_nn_instance'):
        rag_prioritize_batch._nn_instance = None

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
