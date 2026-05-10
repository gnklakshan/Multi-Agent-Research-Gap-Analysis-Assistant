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

    OPENAI_MODEL: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    MAX_PAPERS: int = 10
    FAISS_INDEX_PATH: str = "data/index/faiss_research_papers"
    OUTPUT_DIR: str = "outputs"


settings = Settings()

# Backwards-compatible module-level exports
OPENAI_API_KEY = settings.OPENAI_API_KEY
SEMANTIC_SCHOLAR_API_KEY = settings.SEMANTIC_SCHOLAR_API_KEY
UNPAYWALL_EMAIL = settings.UNPAYWALL_EMAIL
OPENAI_MODEL = settings.OPENAI_MODEL
EMBEDDING_MODEL = settings.EMBEDDING_MODEL
MAX_PAPERS = settings.MAX_PAPERS
FAISS_INDEX_PATH = settings.FAISS_INDEX_PATH
OUTPUT_DIR = settings.OUTPUT_DIR
