# VisitIQ High-Level Design (HLD)

## Overview
VisitIQ is a Streamlit-based healthcare scheduling and intelligence platform. It provides:
- AI chatbot with vector RAG and LLM (Ollama llama3)
- FHIR-compliant slot/appointment management
- Smart patient prioritization and analytics

## Architecture
- UI: Streamlit (app.py)
- Backend Services:
  - SlotManager (FHIR slots, schedules, appointments)
  - SmartLLMHealthcareChatbot (vector-only chat, RAG+LLM)
- Vector Store: Chroma (duckdb+parquet) in ~/.visitiq/app/chroma_db
- LLM: Ollama (llama3)
- Data Ingestion: tools/build_embeddings.py (docs-only, ingest patient documents)

## Data Flow (Chat)
1. User submits query in Streamlit
2. Chatbot routes intent (patients/physicians/scheduling/other)
3. Retrieves top-k context from Chroma (SentenceTransformer embeddings)
4. Builds focused prompt and calls Ollama
5. Parses JSON response or falls back to intelligent handler
6. Returns structured data and formatted response to UI

## Key Modules
- src/slot_manager.py: FHIR models and operations
- src/smart_llm_chatbot.py: chat logic, RAG, LLM integration
- tools/build_embeddings.py: vector store build + patient document ingestion

## Environments
- CHROMA_DIR: vector store directory
- OLLAMA_URL / OLLAMA_MODEL: LLM endpoint/model

## Security & Privacy
- Local-only vector DB and LLM (no external data egress by default)
- PII confined to local filesystem

## Scalability Considerations
- Chroma persistent store; can move to server-backed DuckDB/Parquet
- Batch embedding rebuilds
- Streaming LLM inference via Ollama

## Future Enhancements
- Appointments mirrored into vector DB for vector-only scheduling queries
- Role-based access control
- Audit logging and PHI redaction helpers
