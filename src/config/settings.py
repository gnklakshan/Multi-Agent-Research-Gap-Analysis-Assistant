from __future__ import annotations

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central configuration.

    Note: OPENAI_API_KEY is not validated at import-time so unit tests can run without it.
    The OpenAI client factory functions validate it when invoked.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    OPENAI_API_KEY: Optional[str] = None
    SEMANTIC_SCHOLAR_API_KEY: Optional[str] = None
    UNPAYWALL_EMAIL: Optional[str] = None

    LLM_PROVIDER: str = "openai"
    EMBEDDING_PROVIDER: str = "openai"

    OPENAI_MODEL: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "gemma4:3b"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"

    SEMANTIC_SCHOLAR_MAX_QUERIES: int = 4
    SEMANTIC_SCHOLAR_LIMIT_PER_QUERY: int = 20
    SEMANTIC_SCHOLAR_MIN_INTERVAL_S: float = 2.0

    MAX_PAPERS: int = 10
    FAISS_INDEX_PATH: str = "data/index/faiss_research_papers"
    OUTPUT_DIR: str = "outputs"


settings = Settings()

# Backwards-compatible module-level exports
OPENAI_API_KEY = settings.OPENAI_API_KEY
SEMANTIC_SCHOLAR_API_KEY = settings.SEMANTIC_SCHOLAR_API_KEY
UNPAYWALL_EMAIL = settings.UNPAYWALL_EMAIL
LLM_PROVIDER = settings.LLM_PROVIDER
EMBEDDING_PROVIDER = settings.EMBEDDING_PROVIDER
OPENAI_MODEL = settings.OPENAI_MODEL
EMBEDDING_MODEL = settings.EMBEDDING_MODEL
OLLAMA_BASE_URL = settings.OLLAMA_BASE_URL
OLLAMA_MODEL = settings.OLLAMA_MODEL
OLLAMA_EMBEDDING_MODEL = settings.OLLAMA_EMBEDDING_MODEL
SEMANTIC_SCHOLAR_MAX_QUERIES = settings.SEMANTIC_SCHOLAR_MAX_QUERIES
SEMANTIC_SCHOLAR_LIMIT_PER_QUERY = settings.SEMANTIC_SCHOLAR_LIMIT_PER_QUERY
SEMANTIC_SCHOLAR_MIN_INTERVAL_S = settings.SEMANTIC_SCHOLAR_MIN_INTERVAL_S
MAX_PAPERS = settings.MAX_PAPERS
FAISS_INDEX_PATH = settings.FAISS_INDEX_PATH
OUTPUT_DIR = settings.OUTPUT_DIR
