from __future__ import annotations

import re
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage

from ..config import get_llm
from ..schemas.citation_verification import VerificationReport
from ..schemas.paper_summary import PaperSummary
from ..prompts.citation_verifier_prompt import CITATION_VERIFIER_SYSTEM_PROMPT


def _extract_candidate_claims(text: str) -> List[str]:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    claims: List[str] = []
    for l in lines:
        if l.startswith("#") or l.startswith("```"):
            continue
        # split long sentences conservatively
        if len(l) > 240:
            parts = re.split(r"(?<=[.!?])\s+", l)
            claims.extend([p.strip() for p in parts if p.strip()])
        else:
            claims.append(l)
    # keep manageable number
    return claims[:60]


def verify_citations(
    related_work_md: str,
    *,
    vectorstore=None,
    summaries: List[PaperSummary],
    k: int = 6,
) -> VerificationReport:
    llm = get_llm().with_structured_output(VerificationReport, method="function_calling")
    claims = _extract_candidate_claims(related_work_md)

    evidence_blocks: List[str] = []
    if vectorstore is not None:
        for c in claims[:20]:
            try:
                docs = vectorstore.similarity_search(c, k=k, fetch_k=max(20, k * 3))
            except TypeError:
                docs = vectorstore.similarity_search(c, k=k)
            block = []
            for d in docs:
                md = getattr(d, "metadata", {}) or {}
                block.append(f"[Paper: {md.get('title')} | Year: {md.get('year')} | Page: {md.get('page_number')} | DOI: {md.get('doi')}]")
                block.append((getattr(d, 'page_content', '') or '')[:900])
                block.append("")
            evidence_blocks.append("\n".join(block))
    else:
        # fallback evidence is summaries only
        evidence_blocks.append("No PDF index available; verify against summaries only.")

    prompt = f"""RELATED WORK (markdown):
{related_work_md}

EXTRACTED CLAIM CANDIDATES:
{claims}

PAPER SUMMARIES (JSON):
{[s.model_dump() for s in summaries]}

RETRIEVED EVIDENCE BLOCKS:
{evidence_blocks[:20]}
"""
    return llm.invoke([SystemMessage(content=CITATION_VERIFIER_SYSTEM_PROMPT), HumanMessage(content=prompt)])
