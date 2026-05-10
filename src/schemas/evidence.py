from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    claim: str = Field(description="Short claim supported by evidence")
    paper_id: str
    title: Optional[str] = None
    year: Optional[int] = None
    page_number: Optional[int] = None
    quoted_text: str = Field(description="Quoted text snippet from the source passage")
    doi: Optional[str] = None
