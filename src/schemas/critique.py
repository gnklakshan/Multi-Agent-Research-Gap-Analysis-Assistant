from __future__ import annotations

from typing import List

from pydantic import BaseModel

from .evidence import EvidenceItem


class PaperCritique(BaseModel):
    paper_id: str
    title: str
    strengths: List[str]
    weaknesses: List[str]
    missing_evaluations: List[str]
    possible_research_gaps: List[str]
    evidence_items: List[EvidenceItem]
