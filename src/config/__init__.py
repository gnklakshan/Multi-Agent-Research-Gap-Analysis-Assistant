from .settings import (
    EMBEDDING_MODEL,
    FAISS_INDEX_PATH,
    MAX_PAPERS,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    SEMANTIC_SCHOLAR_API_KEY,
    UNPAYWALL_EMAIL,
    OUTPUT_DIR,
    settings,
)
from .openai import get_embeddings, get_llm

__all__ = [
    "OPENAI_API_KEY",
    "SEMANTIC_SCHOLAR_API_KEY",
    "UNPAYWALL_EMAIL",
    "OPENAI_MODEL",
    "EMBEDDING_MODEL",
    "MAX_PAPERS",
    "FAISS_INDEX_PATH",
    "OUTPUT_DIR",
    "settings",
    "get_llm",
    "get_embeddings",
]
