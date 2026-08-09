from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from .evidence import EvidenceItem


class ResearchPath(BaseModel):
    """A concrete actionable research direction spawned from this gap."""
    title: str = Field(description="Short title for this research direction")
    description: str = Field(description="2–4 sentence description of what to investigate and how")
    methodology_hint: str = Field(description="Key method/approach recommended (e.g. federated learning, transformer, RCT, etc.)")
    expected_contribution: str = Field(description="What novel contribution this path would make to the field")


class ResearchGap(BaseModel):
    gap_id: str
    gap_name: str
    description: str
    papers_supporting_gap: List[str]
    evidence_items: List[EvidenceItem]
    why_it_matters: str
    possible_research_opportunity: str
    strength_of_evidence: str  # "low" | "medium" | "high"

    # --- NEW enrichment fields ---
    research_paths: List[ResearchPath] = Field(
        default_factory=list,
        description="2–3 concrete actionable research directions stemming from this gap",
    )
    publication_level: Literal["journal", "conference", "either"] = Field(
        default="either",
        description=(
            "Recommended publication venue type: 'journal' for incremental/applied work "
            "needing rigorous peer review, 'conference' for novel ideas/systems work, "
            "'either' for both."
        ),
    )
    academic_depth: Literal["BSc/MSc", "MSc/PhD", "PhD/Postdoc"] = Field(
        default="MSc/PhD",
        description=(
            "Appropriate academic depth: 'BSc/MSc' for well-scoped implementable projects, "
            "'MSc/PhD' for research requiring significant literature + original experiments, "
            "'PhD/Postdoc' for deeply unsolved problems requiring multi-year original research."
        ),
    )
    novelty_score: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Estimated novelty of addressing this gap (1=incremental, 10=highly novel breakthrough)",
    )
    key_challenges: List[str] = Field(
        default_factory=list,
        description="2–4 main technical or methodological challenges a researcher would face",
    )
    suggested_datasets_or_benchmarks: List[str] = Field(
        default_factory=list,
        description="Relevant datasets or benchmarks the researcher should look for or create",
    )


class GapAnalysisReport(BaseModel):
    topic: str
    common_gaps: List[ResearchGap]
    overall_summary: str
