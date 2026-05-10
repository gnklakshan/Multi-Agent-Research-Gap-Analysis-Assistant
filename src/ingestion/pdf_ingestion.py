from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import fitz  # PyMuPDF
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
import re


def _iter_pdf_pages(pdf_path: str) -> Iterable[Tuple[int, str]]:
    doc = fitz.open(pdf_path)
    try:
        for i in range(len(doc)):
            page = doc.load_page(i)
            text = page.get_text("text") or ""
            yield i + 1, text
    finally:
        doc.close()


def ingest_pdfs_to_documents(
    pdf_paths: List[str],
    papers_metadata: List[Dict[str, Any]],
    *,
    chunk_size: int = 1200,
    chunk_overlap: int = 200,
) -> List[Document]:
    meta_by_path = {str(Path(p.get("local_pdf_path") or "").resolve()): p for p in papers_metadata if p.get("local_pdf_path")}
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    all_docs: List[Document] = []
    for path in pdf_paths:
        p = Path(path)
        meta = meta_by_path.get(str(p.resolve()), {})
        authors = meta.get("authors")
        if isinstance(authors, list) and authors and isinstance(authors[0], dict):
            authors = [a.get("name") for a in authors if isinstance(a, dict) and a.get("name")]
        if authors is None:
            authors = []

        base_meta = {
            "paper_id": meta.get("paper_id"),
            "title": meta.get("title"),
            "authors": authors,
            "year": meta.get("year"),
            "venue": meta.get("venue"),
            "doi": (meta.get("externalIds") or {}).get("DOI") if isinstance(meta.get("externalIds"), dict) else meta.get("doi"),
            "source_url": meta.get("url"),
            "pdf_url": meta.get("pdf_url"),
            "local_pdf_path": str(p),
        }
        for page_number, text in _iter_pdf_pages(str(p)):
            text = re.sub(r"\s+", " ", text).strip()
            if not text:
                continue
            page_doc = Document(page_content=text, metadata={**base_meta, "page_number": page_number})
            chunks = splitter.split_documents([page_doc])
            for idx, ch in enumerate(chunks):
                ch.metadata = dict(ch.metadata)
                ch.metadata["chunk_id"] = f"{base_meta.get('paper_id') or p.stem}:{page_number}:{idx}"
            all_docs.extend(chunks)
    return all_docs
