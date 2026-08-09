from __future__ import annotations

from typing import List

from langchain_core.messages import HumanMessage, SystemMessage

from ..config import get_llm
from ..schemas.critique import PaperCritique
from ..schemas.paper_summary import PaperSummary
from ..schemas.research_gap import GapAnalysisReport
from ..prompts.gap_analysis_prompt import GAP_ANALYSIS_SYSTEM_PROMPT


def analyze_gaps(topic: str, summaries: List[PaperSummary], critiques: List[PaperCritique]) -> GapAnalysisReport:
    llm = get_llm().with_structured_output(GapAnalysisReport, method="function_calling")
    prompt = f"""Topic:
{topic}

PaperSummaries JSON:
{[s.model_dump() for s in summaries]}

PaperCritiques JSON:
{[c.model_dump() for c in critiques]}
"""
    return llm.invoke([SystemMessage(content=GAP_ANALYSIS_SYSTEM_PROMPT), HumanMessage(content=prompt)])
