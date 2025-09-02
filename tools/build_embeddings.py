#!/usr/bin/env python3
"""
Build embeddings (vectorstore) from application data.

Sources:
- data/patients.csv
- data/practitioners.json
- data/slots.json

Outputs:
- chroma_db/embeddings.npy
- chroma_db/docs.json
- chroma_db/ids.json

Usage:
  python tools/build_embeddings.py --data-dir data --persist chroma_db
"""

import argparse
import os
import sys
from typing import Dict, List, Optional
import numpy as _np

# Ensure src is importable when run from installed app directory
ROOT = os.path.dirname(os.path.dirname(__file__))
SRC_PATH = os.path.join(ROOT, 'src')
if SRC_PATH not in sys.path:
    sys.path.append(SRC_PATH)

from prioritizer import build_vectorstore_from_sources
from config import DATA_DIR as _DATA_DIR_DEFAULT, CHROMA_DIR as _CHROMA_DIR_DEFAULT, OLLAMA_URL as _OLLAMA_URL_DEFAULT, OLLAMA_MODEL as _OLLAMA_MODEL_DEFAULT
try:
    from medical_document_processor import MedicalDocumentProcessor
except Exception:
    MedicalDocumentProcessor = None

# LLM normalization (optional)
import json as _json
import os as _os
import requests as _requests

OLLAMA_URL = _os.getenv("OLLAMA_URL", _OLLAMA_URL_DEFAULT)
OLLAMA_MODEL = _os.getenv("OLLAMA_MODEL", _OLLAMA_MODEL_DEFAULT)
EMBEDDING_MODEL = _os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")


def _noop():
    return None


def _normalize_with_llm(text: str) -> Optional[Dict[str, any]]:
    """Ask local LLM to extract a canonical JSON. Returns dict or None."""
    try:
        prompt = f"""
You are a medical scribe. Extract the following JSON from the report text.
Return ONLY valid JSON with these fields:
{{
  "patient_id": string | null,
  "patient_name": string | null,
  "physician": string | null,
  "visit_date": string | null,
  "vitals": {{
    "glucose_mg_dL": number | null,
    "bp_systolic": number | null,
    "bp_diastolic": number | null,
    "heart_rate": number | null,
    "temperature": number | null,
    "oxygen_saturation": number | null,
    "hba1c": number | null
  }},
  "primary_condition": string | null,
  "secondary_conditions": [string],
  "risk_level": "Emergency"|"High"|"Medium"|"Low" | null,
  "risk_score": number | null,
  "medical_reasons": [string]
}}

Report:
"""
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt + text,
            "stream": False,
            "options": {"temperature": 0.1, "num_ctx": 4096}
        }
        r = _requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=60)
        if r.status_code != 200:
            return None
        resp = r.json().get("response", "")
        # greedy JSON extract
        start = resp.find('{')
        end = resp.rfind('}') + 1
        if start >= 0 and end > start:
            return _json.loads(resp[start:end])
    except Exception:
        return None
    return None


def _ollama_reachable() -> bool:
    """Return True if Ollama API responds, else False."""
    try:
        r = _requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def _ingest_documents_into_vectors(data_dir: str, persist: str, normalize_with_llm: bool = False) -> int:
    """Optional: ingest text from patient_documents (PDFs/images/txt/json) into vectorstore inputs.
    Returns number of additional docs appended. This augments the persisted docs/ids/metadatas files
    written by build_vectorstore_from_sources by appending extra entries and re-saving them.
    """
    if MedicalDocumentProcessor is None:
        print("⚠️ Skipping document ingestion: medical_document_processor not importable")
        return 0

    from pathlib import Path
    import json as _json

    docs_path = os.path.join(persist, "docs.json")
    ids_path = os.path.join(persist, "ids.json")
    metas_path = os.path.join(persist, "metadatas.json")

    if not (os.path.exists(docs_path) and os.path.exists(ids_path) and os.path.exists(metas_path)):
        print("⚠️ Vectorstore base files missing; run base build first")
        return 0

    with open(docs_path, "r", encoding="utf-8") as f:
        docs = _json.load(f)
    with open(ids_path, "r", encoding="utf-8") as f:
        ids = _json.load(f)
    with open(metas_path, "r", encoding="utf-8") as f:
        metadatas = _json.load(f)

    processor = MedicalDocumentProcessor(os.path.join(data_dir, "patient_documents"))
    if normalize_with_llm and not _ollama_reachable():
        print(f"⚠️  LLM not reachable at {OLLAMA_URL}. Proceeding without normalization.")
        normalize_with_llm = False
    root = Path(data_dir) / "patient_documents"
    if not root.exists():
        print("ℹ️ No patient_documents directory found; skipping doc ingestion")
        return 0

    appended = 0
    for pdir in sorted(root.glob("patient_*")):
        if not pdir.is_dir():
            continue
        pid = pdir.name.split("patient_")[-1]
        # Load standardized profile if present
        profile = None
        try:
            prof_path = pdir / "profile.json"
            if prof_path.exists():
                with open(prof_path, 'r', encoding='utf-8') as pf:
                    profile = _json.load(pf)
        except Exception:
            profile = None
        index = processor.organize_patient_documents(pid)
        for category, items in index.items():
            for item in items:
                file_path = item["file_path"]
                ext = os.path.splitext(file_path)[1].lower()
                # dispatch to internal processors
                if ext == ".pdf":
                    processed = processor._process_pdf(file_path, item)
                elif ext in (".jpg", ".jpeg", ".png"):
                    processed = processor._process_image(file_path, item)
                elif ext == ".dcm":
                    processed = processor._process_dicom(file_path, item)
                elif ext in (".doc", ".docx"):
                    processed = processor._process_word(file_path, item)
                elif ext == ".hl7":
                    processed = processor._process_hl7(file_path, item)
                elif ext == ".txt":
                    processed = processor._process_text(file_path, item)
                elif ext == ".json":
                    processed = processor._process_json_report(file_path, item)
                else:
                    continue

                text = processed.get("text_content")
                if not text and "json_data" in processed:
                    try:
                        text = _json.dumps(processed["json_data"], ensure_ascii=False)
                    except Exception:
                        text = None
                if not text and "dicom_metadata" in processed:
                    try:
                        text = _json.dumps(processed["dicom_metadata"], ensure_ascii=False)
                    except Exception:
                        text = None
                if not text:
                    # if we still have no text, synthesize from extracted values
                    vals = processed.get("extracted_values", {})
                    if vals:
                        text = "; ".join([f"{k}:{v}" for k, v in vals.items()])
                if not text:
                    continue

                # Extract patient-centric fields
                vals = processed.get("extracted_values", {})
                doc_patient_id = str(vals.get("patient_id") or pid)
                # Prefer standardized profile fields
                patient_name = (profile or {}).get("name") or vals.get("patient_name")
                glucose = vals.get("glucose")
                bp_sys = vals.get("bp_systolic")
                bp_dia = vals.get("bp_diastolic")
                hr = vals.get("heart_rate")
                hba1c = vals.get("hba1c")

                # Optional: LLM normalization to enrich data
                norm = None
                if normalize_with_llm and text:
                    norm = _normalize_with_llm(text)
                    if norm:
                        # Merge identity
                        doc_patient_id = str(norm.get("patient_id") or doc_patient_id)
                        patient_name = norm.get("patient_name") or patient_name
                        # Merge vitals
                        v = norm.get("vitals", {}) or {}
                        glucose = v.get("glucose_mg_dL", glucose)
                        bp_sys = v.get("bp_systolic", bp_sys)
                        bp_dia = v.get("bp_diastolic", bp_dia)
                        hr = v.get("heart_rate", hr)
                        hba1c = v.get("hba1c", hba1c)
                        # Compute fallback risk if LLM didn't provide
                        risk_level = norm.get("risk_level")
                        risk_score = norm.get("risk_score")
                        if not risk_score:
                            risk_score = 0
                            try:
                                if hba1c is not None:
                                    h = float(hba1c)
                                    if h >= 10:
                                        risk_score = max(risk_score, 90)
                                    elif h >= 8.5:
                                        risk_score = max(risk_score, 70)
                                    elif h >= 7:
                                        risk_score = max(risk_score, 40)
                                if bp_sys is not None:
                                    s = float(bp_sys)
                                    if s >= 180:
                                        risk_score = max(risk_score, 90)
                                    elif s >= 160:
                                        risk_score = max(risk_score, 70)
                                    elif s >= 140:
                                        risk_score = max(risk_score, 40)
                            except Exception:
                                pass
                            if risk_score == 0:
                                mr = norm.get("medical_reasons") or []
                                if isinstance(mr, list) and any(k in " ".join(mr).lower() for k in ["chest", "wheezing", "severe", "syncope"]):
                                    risk_score = 35
                        if not risk_level:
                            risk_level = "Low"
                            if risk_score >= 90:
                                risk_level = "Emergency"
                            elif risk_score >= 70:
                                risk_level = "High"
                            elif risk_score >= 40:
                                risk_level = "Medium"

                snip = text if len(text) < 2000 else text[:2000] + "…"
                doc_str = (
                    f"[PATIENT_DOC] PatientID:{doc_patient_id}; Name:{patient_name or ''}; Category:{category}; File:{os.path.basename(file_path)};\n"
                    f"Vitals: Glucose:{glucose or ''}; BP:{bp_sys or ''}/{bp_dia or ''}; HR:{hr or ''}; HbA1c:{hba1c or ''}\n"
                    f"Content:\n{snip}"
                )
                docs.append(doc_str)
                ids.append(f"patient_doc:{doc_patient_id}:{os.path.basename(file_path)}")
                meta = {
                    "type": "patient_doc",
                    "patient_id": doc_patient_id,
                    "name": patient_name,
                    "glucose_mg_dL": glucose,
                    "bp_systolic": bp_sys,
                    "bp_diastolic": bp_dia,
                    "heart_rate": hr,
                    "hba1c": hba1c,
                    "category": category,
                    "filename": os.path.basename(file_path),
                    "path": file_path
                }
                # Fill standardized demographics from profile
                if profile:
                    if profile.get('age') is not None:
                        meta['age'] = profile.get('age')
                    if profile.get('gender'):
                        meta['gender'] = profile.get('gender')
                    if profile.get('condition'):
                        meta['condition'] = profile.get('condition')
                # Attach triage fields from normalization if available
                if norm:
                    meta.update({
                        "condition": norm.get("primary_condition"),
                        "risk_level": norm.get("risk_level") or risk_level,
                        "risk_score": norm.get("risk_score") or risk_score,
                        "medical_reasons": norm.get("medical_reasons")
                    })
                metadatas.append(meta)
                appended += 1

    # Also ingest standalone JSON reports under data_dir (outside patient_documents)
    try:
        system_json_names = {"practitioners.json", "slots.json", "schedules.json", "appointments.json"}
        for dirpath, dirnames, filenames in os.walk(data_dir):
            # skip patient_documents subtree
            if os.path.abspath(dirpath).startswith(os.path.abspath(os.path.join(data_dir, "patient_documents"))):
                continue
            for fname in filenames:
                if not fname.lower().endswith(".json"):
                    continue
                if fname in system_json_names:
                    continue
                file_path = os.path.join(dirpath, fname)
                try:
                    processed = processor._process_json_report(file_path, {"file_path": file_path, "category": "json_report"})
                except Exception:
                    continue
                text = processed.get("text_content")
                if not text and "json_data" in processed:
                    try:
                        text = _json.dumps(processed["json_data"], ensure_ascii=False)
                    except Exception:
                        text = None
                if not text:
                    vals = processed.get("extracted_values", {})
                    if vals:
                        text = "; ".join([f"{k}:{v}" for k, v in vals.items()])
                if not text:
                    continue

                vals = processed.get("extracted_values", {})
                pid = str(vals.get("patient_id") or "unknown")
                patient_name = vals.get("patient_name")
                glucose = vals.get("glucose")
                bp_sys = vals.get("bp_systolic")
                bp_dia = vals.get("bp_diastolic")
                hr = vals.get("heart_rate")
                hba1c = vals.get("hba1c")

                norm = None
                if normalize_with_llm and text:
                    try:
                        norm = _normalize_with_llm(text)
                    except Exception:
                        norm = None
                if norm:
                    pid = str(norm.get("patient_id") or pid)
                    patient_name = norm.get("patient_name") or patient_name
                    v = norm.get("vitals", {}) or {}
                    glucose = v.get("glucose_mg_dL", glucose)
                    bp_sys = v.get("bp_systolic", bp_sys)
                    bp_dia = v.get("bp_diastolic", bp_dia)
                    hr = v.get("heart_rate", hr)
                    hba1c = v.get("hba1c", hba1c)

                snip = text if len(text) < 2000 else text[:2000] + "…"
                doc_str = (
                    f"[PATIENT_DOC] PatientID:{pid}; Name:{patient_name or ''}; Category:json_report; File:{os.path.basename(file_path)};\n"
                    f"Vitals: Glucose:{glucose or ''}; BP:{bp_sys or ''}/{bp_dia or ''}; HR:{hr or ''}; HbA1c:{hba1c or ''}\n"
                    f"Content:\n{snip}"
                )
                docs.append(doc_str)
                ids.append(f"patient_doc:{pid}:{os.path.basename(file_path)}")
                meta = {
                    "type": "patient_doc",
                    "patient_id": pid,
                    "name": patient_name,
                    "glucose_mg_dL": glucose,
                    "bp_systolic": bp_sys,
                    "bp_diastolic": bp_dia,
                    "heart_rate": hr,
                    "hba1c": hba1c,
                    "category": "json_report",
                    "filename": os.path.basename(file_path),
                    "path": file_path
                }
                if norm:
                    meta.update({
                        "condition": norm.get("primary_condition"),
                        "risk_level": norm.get("risk_level"),
                        "risk_score": norm.get("risk_score"),
                        "medical_reasons": norm.get("medical_reasons")
                    })
                metadatas.append(meta)
                appended += 1
    except Exception as _e:
        print(f"⚠️ Standalone JSON ingestion skipped: {_e}")

    with open(docs_path, "w", encoding="utf-8") as f:
        _json.dump(docs, f, ensure_ascii=False, indent=2)
    with open(ids_path, "w", encoding="utf-8") as f:
        _json.dump(ids, f, ensure_ascii=False, indent=2)
    with open(metas_path, "w", encoding="utf-8") as f:
        _json.dump(metadatas, f, ensure_ascii=False, indent=2)

    # Recompute embeddings so newly appended documents are searchable
    try:
        from sentence_transformers import SentenceTransformer as _SentenceTransformer
        _model = _SentenceTransformer(EMBEDDING_MODEL)
        _emb = _model.encode(docs, show_progress_bar=False)
        _np.save(os.path.join(persist, "embeddings.npy"), _emb)
        print(f"🧮 Rebuilt embeddings for {len(docs)} documents")
    except Exception as e:
        print(f"⚠️ Unable to rebuild embeddings for appended docs: {e}")

    print(f"📄 Ingested {appended} patient documents into vectorstore inputs")
    return appended


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default=_DATA_DIR_DEFAULT, help="Directory with patients.csv, practitioners.json, slots.json")
    parser.add_argument("--persist", default=os.getenv("CHROMA_DIR", _CHROMA_DIR_DEFAULT), help="Vectorstore directory")
    parser.add_argument("--ingest-docs", action="store_true", help="Also parse patient_documents (PDFs/images/txt/json) and add to vectors")
    parser.add_argument("--docs-only", action="store_true", help="Skip CSV synthesis and CSV ingestion; index only documents")
    parser.add_argument("--normalize-with-llm", action="store_true", help="Use local LLM to normalize report text into structured JSON")
    # removed legacy CSV synthesis entirely
    args = parser.parse_args()

    # No CSV synthesis from patient_documents; ingest docs directly

    # Build base vectors (skip CSV ingestion when docs-only)
    if args.docs_only:
        # Create empty base store so docs ingestion can append
        os.makedirs(args.persist, exist_ok=True)
        with open(os.path.join(args.persist, "docs.json"), "w", encoding="utf-8") as f:
            f.write("[]")
        with open(os.path.join(args.persist, "ids.json"), "w", encoding="utf-8") as f:
            f.write("[]")
        with open(os.path.join(args.persist, "metadatas.json"), "w", encoding="utf-8") as f:
            f.write("[]")
        # No base embeddings yet
        print("✅ Initialized empty vectorstore (docs-only mode)")
        summary = {"n": 0, "persist_directory": args.persist}
    else:
        summary: Dict[str, str] = build_vectorstore_from_sources(args.data_dir, args.persist)
    n = summary.get("n", 0)
    print(f"✅ Built vectorstore with {n} base documents at {summary.get('persist_directory')}")

    # Optional: ingest patient_documents
    if args.ingest_docs:
        try:
            added = _ingest_documents_into_vectors(args.data_dir, args.persist, normalize_with_llm=args.normalize_with_llm)
            print(f"✅ Document ingestion complete (+{added} docs)")
        except Exception as e:
            print(f"⚠️ Document ingestion failed: {e}")


if __name__ == "__main__":
    main()


