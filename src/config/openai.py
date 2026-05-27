from __future__ import annotations

from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from .settings import (
    EMBEDDING_MODEL,
    EMBEDDING_PROVIDER,
    LLM_PROVIDER,
    OLLAMA_BASE_URL,
    OLLAMA_EMBEDDING_MODEL,
    OLLAMA_MODEL,
    OPENAI_API_KEY,
    OPENAI_MODEL,
)


def get_llm(model_name: str | None = None, temperature: float = 0):
    provider = LLM_PROVIDER.lower()
    if provider == "openai":
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai.")
        return ChatOpenAI(
            model=model_name or OPENAI_MODEL,
            temperature=temperature,
            api_key=OPENAI_API_KEY,
        )
    if provider == "ollama":
        return ChatOllama(
            model=model_name or OLLAMA_MODEL,
            temperature=temperature,
            base_url=OLLAMA_BASE_URL,
        )
    raise ValueError(f"Unsupported LLM_PROVIDER: {LLM_PROVIDER}. Use 'openai' or 'ollama'.")


def get_embeddings(model_name: str | None = None):
    provider = EMBEDDING_PROVIDER.lower()
    if provider == "openai":
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai.")
        return OpenAIEmbeddings(api_key=OPENAI_API_KEY, model=model_name or EMBEDDING_MODEL)
    if provider == "ollama":
        return OllamaEmbeddings(
            model=model_name or OLLAMA_EMBEDDING_MODEL,
            base_url=OLLAMA_BASE_URL,
        )
    raise ValueError(
        f"Unsupported EMBEDDING_PROVIDER: {EMBEDDING_PROVIDER}. Use 'openai' or 'ollama'."
    )
