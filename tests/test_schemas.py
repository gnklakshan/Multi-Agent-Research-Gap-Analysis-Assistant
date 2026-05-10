from src.schemas.evidence import EvidenceItem
from src.schemas.paper_summary import PaperSummary
from src.schemas.critique import PaperCritique
from src.schemas.research_gap import GapAnalysisReport, ResearchGap
from src.schemas.citation_verification import VerificationReport, ClaimVerification


def test_evidence_item_validates():
    e = EvidenceItem(
        claim="Uses skeleton inputs",
        paper_id="p1",
        title="Test",
        year=2024,
        page_number=3,
        doi="10.1/x",
        quoted_text="We use skeleton keypoints ...",
    )
    assert e.paper_id == "p1"


def test_paper_summary_validates():
    s = PaperSummary(
        paper_id="p1",
        title="Test",
        year=2024,
        venue="CVPR",
        doi="10.1/x",
        selected_version="conference",
        problem="fall detection",
        proposed_method="transformer",
        input_type="skeleton",
        model_or_algorithm="transformer",
        datasets=["URFD"],
        metrics={"F1": "0.9"},
        main_results=["F1=0.9"],
        main_contributions=["privacy-friendly representation"],
        author_limitations=["not reported"],
        inferred_limitations=["small dataset"],
        privacy_notes=["uses skeleton"],
        deployment_notes=["not reported"],
        future_work=["not reported"],
        evidence_items=[],
    )
    assert s.doi == "10.1/x"


def test_critique_validates():
    c = PaperCritique(
        paper_id="p1",
        title="Test",
        strengths=["good accuracy"],
        weaknesses=["no edge eval"],
        missing_evaluations=["latency"],
        possible_research_gaps=["edge deployment gap"],
        evidence_items=[],
    )
    assert "latency" in c.missing_evaluations


def test_gap_report_validates():
    g = ResearchGap(
        gap_id="g1",
        gap_name="Edge deployment gap",
        description="Few papers report latency.",
        papers_supporting_gap=["p1"],
        evidence_items=[],
        why_it_matters="deployment requires latency bounds",
        possible_research_opportunity="measure real-time inference on devices",
        strength_of_evidence="low",
    )
    r = GapAnalysisReport(topic="t", common_gaps=[g], overall_summary="summary")
    assert r.common_gaps[0].gap_id == "g1"


def test_verification_report_validates():
    claim = ClaimVerification(
        claim="Several papers evaluate on edge devices.",
        status="too_strong",
        supporting_evidence=[],
        explanation="Only one paper mentions edge testing.",
        suggested_revision="Some papers discuss deployment constraints.",
    )
    rep = VerificationReport(
        total_claims=1,
        supported_claims=0,
        partially_supported_claims=0,
        unsupported_claims=0,
        too_strong_claims=1,
        claims=[claim],
    )
    assert rep.too_strong_claims == 1

