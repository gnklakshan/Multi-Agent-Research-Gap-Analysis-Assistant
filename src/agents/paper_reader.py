from __future__ import annotations

from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from ..config import get_llm
from ..schemas.paper_summary import PaperSummary
from ..prompts.paper_reader_prompt import PAPER_READER_SYSTEM_PROMPT


def _format_evidence_docs(docs: List[Any]) -> str:
    lines: List[str] = []
    for d in docs:
        md = getattr(d, "metadata", {}) or {}
        header = (
            f"[paper_id: {md.get('paper_id')} | title: {md.get('title')} | year: {md.get('year')} | "
            f"page: {md.get('page_number')} | doi: {md.get('doi')}]"
        )
        lines.append(header)
        lines.append((getattr(d, "page_content", "") or "")[:1200])
        lines.append("")
    return "\n".join(lines).strip()


def summarize_paper(
    paper: Dict[str, Any],
    *,
    vectorstore=None,
    k: int = 8,
) -> PaperSummary:
    llm = get_llm().with_structured_output(PaperSummary, method="function_calling")
    paper_id = paper["paper_id"]
    title = paper.get("title") or "unknown title"

    evidence_text = ""
    if vectorstore is not None:
        # Query with metadata filter to focus on this paper
        q = f"{title}. Extract method, datasets, metrics, results, limitations, privacy, deployment, future work."
        docs: List[Any] = []
        try:
            docs = vectorstore.similarity_search(q, k=k, filter={"paper_id": paper_id}, fetch_k=max(30, k * 6))
        except TypeError:
            # Some vectorstores do not support metadata filter; retrieve more and filter locally.
            cand = vectorstore.similarity_search(q, k=max(40, k * 10))
            docs = [d for d in cand if (getattr(d, "metadata", {}) or {}).get("paper_id") == paper_id][:k]
        evidence_text = _format_evidence_docs(docs)
    else:
        abs_text = paper.get("abstract") or ""
        evidence_text = f"[paper_id: {paper_id} | title: {title} | year: {paper.get('year')}]\nABSTRACT:\n{abs_text}"

    ext = paper.get("externalIds") or {}
    doi = ext.get("DOI") if isinstance(ext, dict) else paper.get("doi")
    user_prompt = f"""METADATA (may be incomplete):
paper_id: {paper_id}
title: {title}
year: {paper.get('year')}
venue: {paper.get('venue')}
doi: {doi}
selected_version: {paper.get('selected_version') or 'unknown'}

EVIDENCE PASSAGES:
{evidence_text}
"""

    resp = llm.invoke([SystemMessage(content=PAPER_READER_SYSTEM_PROMPT), HumanMessage(content=user_prompt)])
    return resp


def summarize_papers(
    papers: List[Dict[str, Any]],
    *,
    vectorstore=None,
    k: int = 8,
) -> List[PaperSummary]:
    out: List[PaperSummary] = []
    for p in papers:
        out.append(summarize_paper(p, vectorstore=vectorstore, k=k))
    return out
