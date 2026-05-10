from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel

from .evidence import EvidenceItem


class ResearchGap(BaseModel):
    gap_id: str
    gap_name: str
    description: str
    papers_supporting_gap: List[str]
    evidence_items: List[EvidenceItem]
    why_it_matters: str
    possible_research_opportunity: str
    strength_of_evidence: str


class GapAnalysisReport(BaseModel):
    topic: str
    common_gaps: List[ResearchGap]
    overall_summary: str
