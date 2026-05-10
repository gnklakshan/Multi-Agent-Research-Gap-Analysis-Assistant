from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from ..utils.json_io import write_json
from ..utils.paths import ensure_dir


def finalize_run(state: Dict[str, Any], *, output_dir: Path) -> Tuple[str, Dict[str, Any]]:
    ensure_dir(output_dir)

    topic = state.get("topic", "")
    queries = state.get("expanded_queries") or []
    selected = state.get("selected_papers") or []
    downloaded = state.get("downloaded_papers") or []
    summaries = state.get("paper_summaries") or []
    gap_report = state.get("gap_report")
    comparison = state.get("comparison_table") or ""
    related_work = state.get("related_work") or ""
    verification = state.get("verification_report")
    errors = state.get("errors") or []
    warnings = state.get("warnings") or []

    ts = datetime.utcnow().isoformat() + "Z"
    run_summary: Dict[str, Any] = {
        "timestamp_utc": ts,
        "topic": topic,
        "expanded_queries": queries,
        "candidate_papers_count": len(state.get("candidate_papers") or []),
        "selected_papers_count": len(selected),
        "downloaded_pdfs_count": sum(1 for p in downloaded if p.get("downloaded")),
        "parsed_chunks_count": len(state.get("parsed_chunks") or []),
        "paper_summaries_count": len(summaries),
        "errors": errors,
        "warnings": warnings,
    }
    write_json(output_dir / "run_summary.json", run_summary)

    lines: List[str] = []
    lines.append("# Research Topic")
    lines.append(topic)
    lines.append("")

    lines.append("# Search Strategy")
    lines.append("Expanded queries used:")
    for q in queries:
        lines.append(f"- {q}")
    lines.append("")

    lines.append("# Selected Papers")
    for p in selected:
        ext = p.get("externalIds") or {}
        doi = ext.get("DOI") if isinstance(ext, dict) else None
        lines.append(f"- {p.get('title')} ({p.get('year')}) — {p.get('venue') or 'venue n/a'} — DOI: {doi or 'n/a'} — score: {p.get('final_score', 0):.3f}")
    lines.append("")

    lines.append("# Version and PDF Retrieval Summary")
    for p in downloaded:
        lines.append(
            f"- {p.get('title')} — version: {p.get('selected_version')} — pdf_source: {p.get('pdf_source')} — downloaded: {p.get('downloaded')} "
            f"{('— error: ' + p.get('download_error')) if p.get('download_error') else ''}"
        )
    lines.append("")

    lines.append("# Paper Summary Table")
    lines.append("| Paper | Year | Venue | Key Contribution | Main Limitation |")
    lines.append("|---|---:|---|---|---|")
    for s in summaries:
        contrib = (getattr(s, "main_contributions", None) or ["not reported"])[0].replace("|", "/")
        lim = (
            (getattr(s, "author_limitations", None) or [])
            or (getattr(s, "inferred_limitations", None) or [])
            or ["not reported"]
        )[0].replace("|", "/")
        lines.append(f"| {s.title} | {s.year or 'n/a'} | {s.venue or 'n/a'} | {contrib} | {lim} |")
    lines.append("")

    lines.append("# Common Research Gaps")
    if gap_report:
        for g in gap_report.common_gaps:
            lines.append(f"## {g.gap_name}")
            lines.append(g.description)
            lines.append("")
            lines.append(f"- Strength of evidence: {g.strength_of_evidence}")
            lines.append(f"- Why it matters: {g.why_it_matters}")
            lines.append(f"- Opportunity: {g.possible_research_opportunity}")
            lines.append(f"- Papers: {', '.join(g.papers_supporting_gap)}")
            lines.append("")
    else:
        lines.append("Gap analysis not available.")
        lines.append("")

    lines.append("# Cross-Paper Comparison")
    lines.append(comparison)
    lines.append("")

    lines.append("# Related Work Draft")
    lines.append(related_work)
    lines.append("")

    lines.append("# Citation Verification Summary")
    if verification:
        lines.append(f"- Total claims: {verification.total_claims}")
        lines.append(f"- Supported: {verification.supported_claims}")
        lines.append(f"- Partially supported: {verification.partially_supported_claims}")
        lines.append(f"- Unsupported: {verification.unsupported_claims}")
        lines.append(f"- Too strong: {verification.too_strong_claims}")
    else:
        lines.append("Verification report not available.")
    lines.append("")

    lines.append("# Unsupported or Weak Claims")
    if verification:
        for c in verification.claims:
            if c.status in {"unsupported", "too_strong", "partially_supported"}:
                lines.append(f"- {c.status}: {c.claim}")
                if c.suggested_revision:
                    lines.append(f"  - suggested: {c.suggested_revision}")
    lines.append("")

    lines.append("# Limitations of This Automated Review")
    lines.append("- Ranking and version resolution are heuristic; results may omit relevant papers.")
    lines.append("- PDF parsing is best-effort text extraction and may miss tables/figures.")
    lines.append("- Citation verification reduces hallucinations but is not a formal proof of correctness.")
    lines.append("")

    lines.append("# Suggested Next Steps")
    lines.append("- Increase `--max-papers` and rerun for broader coverage.")
    lines.append("- Add section-aware parsing (Abstract/Methods/Experiments/Limitations) for stronger extraction.")
    lines.append("- Add a persistent paper cache and incremental indexing for repeated runs.")
    lines.append("")

    if warnings:
        lines.append("# Warnings")
        lines.extend([f"- {w}" for w in warnings])
        lines.append("")
    if errors:
        lines.append("# Errors")
        lines.extend([f"- {e}" for e in errors])
        lines.append("")

    report_path = output_dir / "final_report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return str(report_path), run_summary

