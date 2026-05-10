from __future__ import annotations

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from .settings import EMBEDDING_MODEL, OPENAI_API_KEY, OPENAI_MODEL


def get_llm(model_name: str | None = None, temperature: float = 0):
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is required to create the LLM client.")
    return ChatOpenAI(
        model=model_name or OPENAI_MODEL,
        temperature=temperature,
        api_key=OPENAI_API_KEY,
    )


def get_embeddings(model_name: str | None = None):
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is required to create the embeddings client.")
    return OpenAIEmbeddings(api_key=OPENAI_API_KEY, model=model_name or EMBEDDING_MODEL)
