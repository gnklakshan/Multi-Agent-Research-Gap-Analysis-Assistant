from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.tools import Tool

from .config import get_embeddings


def build_vector_store_from_chunks(chunks: List[Document]) -> FAISS:
    embeddings = get_embeddings()
    return FAISS.from_documents(documents=chunks, embedding=embeddings)


# Backwards-compatible alias
build_vector_store_from_documents = build_vector_store_from_chunks


def save_vector_store(vectorstore: FAISS, index_path: str) -> None:
    Path(index_path).parent.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(index_path)


def load_vector_store(index_path: str) -> FAISS:
    embeddings = get_embeddings()
    return FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)


def _format_retrieved_docs(docs: List[Document]) -> str:
    blocks: List[str] = []
    for d in docs:
        md = d.metadata or {}
        header = (
            f"[paper_id: {md.get('paper_id')} | title: {md.get('title')} | year: {md.get('year')} | "
            f"page: {md.get('page_number')} | doi: {md.get('doi')}]"
        )
        blocks.append(header)
        blocks.append(d.page_content)
        blocks.append("")
    return "\n".join(blocks).strip()


def get_retriever_tool(vectorstore: FAISS, *, k: int = 8, use_mmr: bool = True) -> Tool:
    """
    Tool returns formatted evidence passages with citation-style headers.
    """

    def _retrieve(query: str, paper_id: Optional[str] = None) -> str:
        search_kwargs: Dict[str, Any] = {"k": k, "fetch_k": max(40, k * 6)}
        if paper_id:
            search_kwargs["filter"] = {"paper_id": paper_id}
        try:
            if use_mmr:
                docs = vectorstore.max_marginal_relevance_search(query, **search_kwargs)
            else:
                docs = vectorstore.similarity_search(query, **search_kwargs)
        except TypeError:
            # Fallback for vectorstores without metadata filter support.
            base_docs = (
                vectorstore.max_marginal_relevance_search(query, k=max(60, k * 10))
                if use_mmr
                else vectorstore.similarity_search(query, k=max(60, k * 10))
            )
            if paper_id:
                base_docs = [d for d in base_docs if (d.metadata or {}).get("paper_id") == paper_id]
            docs = base_docs[:k]
        return _format_retrieved_docs(docs)

    return Tool.from_function(
        func=_retrieve,
        name="retrieve_research_evidence",
        description="Retrieve evidence passages from research papers, including title, page number, DOI, and source metadata.",
    )
