from __future__ import annotations

from typing import List, Tuple

from langchain_core.messages import HumanMessage, SystemMessage

from ..config import get_llm
from ..prompts.writer_prompt import WRITER_SYSTEM_PROMPT
from ..schemas.paper_summary import PaperSummary
from ..schemas.research_gap import GapAnalysisReport
from ..schemas.citation_verification import VerificationReport


def write_related_work(
    topic: str,
    summaries: List[PaperSummary],
    gap_report: GapAnalysisReport,
    verification_report: VerificationReport | None = None,
) -> Tuple[str, str, str, str]:
    llm = get_llm()
    
    feedback_clause = ""
    if verification_report is not None:
        feedback_clause = f"""
---
CRITICAL: The previous draft had citation verification issues. You MUST revise the draft to address the following issues:
Total claims analyzed: {verification_report.total_claims}
Unsupported claims: {verification_report.unsupported_claims}
Too strong claims: {verification_report.too_strong_claims}

Please look at the specific claims that failed verification below, and correct them (either tone down, rewrite to align with the evidence, or remove them):
"""
        for c in verification_report.claims:
            if c.status in {"unsupported", "too_strong", "partially_supported"}:
                feedback_clause += f"- Claim: \"{c.claim}\"\n  Status: {c.status}\n  Reason: {c.explanation}\n"
                if c.suggested_revision:
                    feedback_clause += f"  Suggested revision: {c.suggested_revision}\n"
        feedback_clause += "\nMake sure all claims in the revised output are strictly supported by the evidence.\n"

    prompt = f"""Topic:
{topic}

PaperSummaries JSON:
{[s.model_dump() for s in summaries]}

GapAnalysisReport JSON:
{gap_report.model_dump()}
{feedback_clause}
Write:
1) related work section (markdown)
2) research gaps summary (markdown)
3) novelty justification paragraph (markdown)
4) contribution bullets for a new paper (markdown)

Remember: use citation markers like [paper_id:page_number] for claims grounded in evidence.
"""
    resp = llm.invoke([SystemMessage(content=WRITER_SYSTEM_PROMPT), HumanMessage(content=prompt)])
    text = resp.content if hasattr(resp, "content") else str(resp)
    # Split on Markdown horizontal rule line.
    parts = [p.strip() for p in text.split("\n---\n") if p.strip()]
    related = parts[0] if len(parts) > 0 else text.strip()
    gaps = parts[1] if len(parts) > 1 else ""
    novelty = parts[2] if len(parts) > 2 else ""
    contrib = parts[3] if len(parts) > 3 else ""
    return related, gaps, novelty, contrib
