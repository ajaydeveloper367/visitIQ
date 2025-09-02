"""
Central configuration for VisitIQ.

All modules should import settings from here instead of hardcoding
defaults or re-reading environment variables independently.
"""

import os
from pathlib import Path

# Project root (app directory when installed)
_SRC_DIR = Path(__file__).resolve().parent
_APP_DIR = _SRC_DIR.parent

# Directories
DATA_DIR = os.getenv("VISITIQ_DATA_DIR", str(_APP_DIR / "data"))
CHROMA_DIR = os.getenv("CHROMA_DIR", str(_APP_DIR / "chroma_db"))

# LLM configuration
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

# RAG configuration
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "3"))

def get_config() -> dict:
    return {
        "DATA_DIR": DATA_DIR,
        "CHROMA_DIR": CHROMA_DIR,
        "OLLAMA_URL": OLLAMA_URL,
        "OLLAMA_MODEL": OLLAMA_MODEL,
        "RAG_TOP_K": RAG_TOP_K,
    }


