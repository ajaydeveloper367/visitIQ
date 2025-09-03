# VisitIQ Project Documentation

## 1. Overview
VisitIQ is an AI‑enhanced healthcare scheduling and assistance application built on Streamlit. It combines a FHIR‑style slot/appointment engine with a vector database (Chroma) and a local LLM (Ollama llama3) to deliver a privacy‑preserving, demo‑ready experience.

## 2. Architecture (High‑Level)
- UI: Streamlit single‑page app (`app.py`)
- Chat: `src/smart_llm_chatbot.py` (vector‑only RAG + LLM)
- Scheduling: `src/slot_manager.py` (FHIR slots, schedules, appointments)
- Vector store: Chroma (DuckDB+Parquet), persisted under `~/.visitiq/app/chroma_db`
- Ingestion: `tools/build_embeddings.py` (docs‑only mode, patient_documents ingestion, optional LLM normalization)
- LLM: Ollama (model: llama3)

```mermaid
flowchart TD
  U[User] --> UI[Streamlit app.py]
  UI --> CH[SmartLLMHealthcareChatbot]
  CH --> R{Route}
  R -->|Available patients today| AP[SlotManager Appointments]
  R -->|Available patients (all)| PV[Chroma patients]
  R -->|Physicians / Specialties| PH[Chroma physicians]
  R -->|Other queries| VEC[RAG + LLM]
  VEC --> ENC[SentenceTransformer]
  ENC --> DB[Chroma query_embeddings]
  DB --> K[Top‑k snippets]
  K --> PROMPT[Focused prompt]
  PROMPT --> LLM[Ollama llama3]
  LLM --> RES{JSON?}
  RES -->|Yes| SD[add_structured_data]
  RES -->|No| FB[fallback]
  SD --> OUT[UI render]
  FB --> OUT
```

## 3. Setup (Local)
1. Start Ollama and pull `llama3` (if not present).
2. Build or ingest vectors:
   - `~/.visitiq/venv/bin/python ~/.visitiq/app/tools/build_embeddings.py \
      --data-dir ~/.visitiq/app/data --persist ~/.visitiq/app/chroma_db \
      --ingest-docs --normalize-with-llm`
3. Run UI (visitIQ root): `./visitiq start` or `streamlit run app.py`

## 4. Demo Script (Use these scenarios)
- A. List physicians (vector‑only) — Query: “list cardiologists”
- B. Patient insights (vector RAG) — Query: “show available patients”
- C. Today’s appointments — Query: “available patients for today”
- D. Slots overview — Query: “available slots today”

## 5. Screenshots (Place files under docs/screenshots)
- docs/screenshots/01_home.png — Home/landing
- docs/screenshots/02_chat_list_physicians.png — Chat listing physicians
- docs/screenshots/03_chat_available_patients.png — Available patients (all)
- docs/screenshots/04_chat_patients_today.png — Patients scheduled today
- docs/screenshots/05_slots.png — Slots view
- docs/screenshots/06_prioritization.png — Prioritization view

## 6. Operations
- Vector rebuild (docs‑only): use `--docs-only` flag to init empty store then `--ingest-docs` to append
- Environment: `CHROMA_DIR`, `OLLAMA_URL`, `OLLAMA_MODEL`

## 7. Security/Privacy
Local‑first: vectors and LLM run locally; no external API calls required by default. PHI stays on disk.

## 8. Appendices
- HLD deck: `VisitIQ_HLD.pptx`
- This guide: `docs/PROJECT_DOCUMENTATION.md`
