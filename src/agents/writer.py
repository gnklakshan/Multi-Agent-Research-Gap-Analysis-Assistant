from __future__ import annotations

from typing import List, Tuple

from langchain_core.messages import HumanMessage, SystemMessage

from ..config import get_llm
from ..prompts.writer_prompt import WRITER_SYSTEM_PROMPT
from ..schemas.paper_summary import PaperSummary
from ..schemas.research_gap import GapAnalysisReport


def write_related_work(topic: str, summaries: List[PaperSummary], gap_report: GapAnalysisReport) -> Tuple[str, str, str, str]:
    llm = get_llm()
    prompt = f"""Topic:
{topic}

PaperSummaries JSON:
{[s.model_dump() for s in summaries]}

GapAnalysisReport JSON:
{gap_report.model_dump()}

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
