from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel

from .evidence import EvidenceItem


class ClaimVerification(BaseModel):
    claim: str
    status: Literal["supported", "partially_supported", "unsupported", "too_strong"]
    supporting_evidence: List[EvidenceItem]
    explanation: str
    suggested_revision: Optional[str] = None


class VerificationReport(BaseModel):
    total_claims: int
    supported_claims: int
    partially_supported_claims: int
    unsupported_claims: int
    too_strong_claims: int
    claims: List[ClaimVerification]

