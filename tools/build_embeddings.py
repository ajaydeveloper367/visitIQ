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
from typing import Dict, List

# Ensure src is importable when run from installed app directory
ROOT = os.path.dirname(os.path.dirname(__file__))
SRC_PATH = os.path.join(ROOT, 'src')
if SRC_PATH not in sys.path:
    sys.path.append(SRC_PATH)

from prioritizer import build_vectorstore_from_sources
try:
    from medical_document_processor import MedicalDocumentProcessor
except Exception:
    MedicalDocumentProcessor = None


def _ensure_doc_patients(data_dir: str):
    """If patient_documents exist, ensure document-only patients will be represented.
    We simply make sure a minimal patients.csv exists comprised of any folders
    like patient_XXX that were not present in patients.csv; the builder will
    read both patients.csv and practitioners/slots to produce metadatas.
    """
    import csv
    from pathlib import Path

    root = Path(data_dir)
    docs_dir = root / 'patient_documents'
    csv_path = root / 'patients.csv'
    if not docs_dir.exists():
        return

    existing_ids: List[str] = []
    if csv_path.exists():
        try:
            import pandas as pd
            df = pd.read_csv(csv_path)
            existing_ids = [str(x).zfill(3) for x in df.get('patient_id', []).astype(str)]
        except Exception:
            existing_ids = []

    # Gather patient ids from document folders
    doc_ids: List[str] = []
    for p in docs_dir.glob('patient_*'):
        if p.is_dir():
            pid = p.name.split('patient_')[-1]
            pid = str(pid).zfill(3)
            if pid not in existing_ids:
                doc_ids.append(pid)

    if not doc_ids:
        return

    # Append minimal rows to patients.csv so they are embedded
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    header = ['patient_id','name','age','condition','glucose_mg_dL','bp_systolic','bp_diastolic','heart_rate','history','notes']
    write_header = not csv_path.exists()
    with open(csv_path, 'a', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=header)
        if write_header:
            w.writeheader()
        for pid in doc_ids:
            w.writerow({
                'patient_id': pid,
                'name': f'DocPatient {pid}',
                'age': 50,
                'condition': 'From Documents',
                'glucose_mg_dL': '',
                'bp_systolic': '',
                'bp_diastolic': '',
                'heart_rate': '',
                'history': 'generated from docs',
                'notes': ''
            })


def _ingest_documents_into_vectors(data_dir: str, persist: str) -> int:
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
    root = Path(data_dir) / "patient_documents"
    if not root.exists():
        print("ℹ️ No patient_documents directory found; skipping doc ingestion")
        return 0

    appended = 0
    for pdir in sorted(root.glob("patient_*")):
        if not pdir.is_dir():
            continue
        pid = pdir.name.split("patient_")[-1]
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

                snip = text if len(text) < 2000 else text[:2000] + "…"
                doc_str = (
                    f"[PATIENT_DOC] PatientID:{pid}; Category:{category}; File:{os.path.basename(file_path)};\n"
                    f"Content:\n{snip}"
                )
                docs.append(doc_str)
                ids.append(f"patient_doc:{pid}:{os.path.basename(file_path)}")
                metadatas.append({
                    "type": "patient_doc",
                    "patient_id": pid,
                    "category": category,
                    "filename": os.path.basename(file_path),
                    "path": file_path
                })
                appended += 1

    with open(docs_path, "w", encoding="utf-8") as f:
        _json.dump(docs, f, ensure_ascii=False, indent=2)
    with open(ids_path, "w", encoding="utf-8") as f:
        _json.dump(ids, f, ensure_ascii=False, indent=2)
    with open(metas_path, "w", encoding="utf-8") as f:
        _json.dump(metadatas, f, ensure_ascii=False, indent=2)

    print(f"📄 Ingested {appended} patient documents into vectorstore inputs")
    return appended


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data", help="Directory with patients.csv, practitioners.json, slots.json")
    parser.add_argument("--persist", default=os.getenv("CHROMA_DIR", "chroma_db"), help="Vectorstore directory")
    parser.add_argument("--ingest-docs", action="store_true", help="Also parse patient_documents (PDFs/images/txt/json) and add to vectors")
    args = parser.parse_args()

    # Ensure document-only patients are represented
    _ensure_doc_patients(args.data_dir)

    summary: Dict[str, str] = build_vectorstore_from_sources(args.data_dir, args.persist)
    n = summary.get("n", 0)
    print(f"✅ Built vectorstore with {n} base documents at {summary.get('persist_directory')}")

    # Optional: ingest patient_documents
    if args.ingest_docs:
        try:
            added = _ingest_documents_into_vectors(args.data_dir, args.persist)
            print(f"✅ Document ingestion complete (+{added} docs)")
        except Exception as e:
            print(f"⚠️ Document ingestion failed: {e}")


if __name__ == "__main__":
    main()


