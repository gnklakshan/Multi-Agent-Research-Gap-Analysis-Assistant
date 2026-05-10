from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from .evidence import EvidenceItem


class PaperSummary(BaseModel):
    paper_id: str
    title: str
    year: Optional[int] = None
    venue: Optional[str] = None
    doi: Optional[str] = None
    selected_version: Optional[str] = None

    problem: str = Field(description="What problem is addressed?")
    proposed_method: str
    input_type: str = Field(description="e.g., RGB video, depth, skeleton, inertial, multimodal")
    model_or_algorithm: str = Field(description="Model/algorithm name or description; 'not reported' if missing")

    datasets: List[str]
    metrics: Dict[str, str]
    main_results: List[str]
    main_contributions: List[str]

    author_limitations: List[str]
    inferred_limitations: List[str]
    privacy_notes: List[str]
    deployment_notes: List[str]
    future_work: List[str]

    evidence_items: List[EvidenceItem]
