from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from rich.console import Console

from ..config import FAISS_INDEX_PATH, MAX_PAPERS, OUTPUT_DIR, SEMANTIC_SCHOLAR_API_KEY, UNPAYWALL_EMAIL
from ..ingestion import ingest_pdfs_to_documents
from ..papers.query_expansion import expand_queries
from ..papers.search import dedupe_papers, search_papers
from ..papers.ranking import rank_and_select_papers
from ..papers.versioning import resolve_versions
from ..papers.unpaywall import fetch_unpaywall_pdf_url
from ..papers.pdf_downloader import download_pdfs
from ..retriever import build_vector_store_from_documents, get_retriever_tool, save_vector_store
from ..utils.json_io import write_json
from ..utils.paths import ensure_dir

from .paper_reader import summarize_papers
from .critic import critique_papers
from .gap_analyzer import analyze_gaps
from .comparison import build_comparison_table
from .writer import write_related_work
from .citation_verifier import verify_citations
from .finalizer import finalize_run


console = Console()


def create_expand_queries_node():
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        topic = state["topic"]
        console.log(f"[bold]expand_queries[/bold]: {topic}")
        queries = expand_queries(topic)
        return {"expanded_queries": queries}

    return node


def create_search_papers_node():
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        queries: List[str] = state.get("expanded_queries") or [state["topic"]]
        output_dir = Path(state.get("output_dir") or OUTPUT_DIR)
        console.log(f"[bold]search_papers[/bold]: queries={len(queries)}")
        raw = search_papers(queries, api_key=SEMANTIC_SCHOLAR_API_KEY, limit_per_query=20)

        good = [p for p in raw if p.get("title")]
        if not good:
            raise RuntimeError("Semantic Scholar search failed or returned no usable papers (check network / API key / query).")

        deduped = dedupe_papers(good)
        ensure_dir(output_dir)
        write_json(output_dir / "candidate_papers.json", deduped)
        return {"candidate_papers": deduped}

    return node


def create_rank_papers_node():
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        topic = state["topic"]
        max_papers = int(state.get("max_papers") or MAX_PAPERS)
        output_dir = Path(state.get("output_dir") or OUTPUT_DIR)
        console.log(f"[bold]rank_papers[/bold]: selecting top {max_papers}")
        ranked = rank_and_select_papers(
            topic,
            state.get("candidate_papers") or [],
            top_n=max_papers,
            expanded_queries=state.get("expanded_queries") or [],
        )
        for p in ranked:
            parts = p.get("ranking") or {}
            p["final_score"] = parts.get("final_score", 0.0)
            p["relevance_score"] = parts.get("relevance_score", 0.0)
            p["recency_score"] = parts.get("recency_score", 0.0)
            p["citation_score"] = parts.get("citation_score", 0.0)
            p["venue_score"] = parts.get("venue_score", 0.0)
            p["pdf_score"] = parts.get("pdf_score", 0.0)
            p["publication_type_score"] = parts.get("publication_type_score", 0.0)
            p["reason_selected"] = "ranked by composite score (relevance/recency/citations/venue/pdf/type/doi)"
        ensure_dir(output_dir)
        write_json(output_dir / "selected_papers.json", ranked)
        return {"selected_papers": ranked}

    return node


def create_resolve_versions_node():
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        console.log("[bold]resolve_versions[/bold]")
        output_dir = Path(state.get("output_dir") or OUTPUT_DIR)
        papers = resolve_versions(state.get("selected_papers") or [])

        if UNPAYWALL_EMAIL:
            for p in papers:
                ext = p.get("externalIds") or {}
                doi = ext.get("DOI") if isinstance(ext, dict) else None
                if not doi:
                    continue
                try:
                    info = fetch_unpaywall_pdf_url(doi, email=UNPAYWALL_EMAIL)
                    if info:
                        p.update(info)
                except Exception as e:
                    warns = state.get("warnings") or []
                    warns.append(f"unpaywall_failed for DOI {doi}: {type(e).__name__}: {e}")
                    state["warnings"] = warns

        ensure_dir(output_dir)
        write_json(output_dir / "version_resolution.json", papers)
        return {"selected_papers": papers}

    return node


def create_download_pdfs_node():
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        console.log("[bold]download_pdfs[/bold]")
        output_dir = Path(state.get("output_dir") or OUTPUT_DIR)
        if state.get("skip_download") or state.get("abstract_only"):
            console.log("[yellow]Skipping downloads (abstract-only/skip-download enabled)[/yellow]")
            warns = state.get("warnings") or []
            warns.append("PDF downloading skipped; results will be metadata/abstract-grounded only.")
            state["warnings"] = warns
            downloaded = [dict(p, downloaded=False, download_error="skipped") for p in (state.get("selected_papers") or [])]
        else:
            downloaded = download_pdfs(
                state.get("selected_papers") or [],
                papers_dir=str(Path("data") / "papers"),
                metadata_path=str(Path("data") / "metadata" / "downloaded_papers.json"),
            )
        ensure_dir(output_dir)
        write_json(output_dir / "download_report.json", downloaded)
        return {"downloaded_papers": downloaded}

    return node


def create_ingest_pdfs_node():
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        console.log("[bold]ingest_pdfs[/bold]")
        output_dir = Path(state.get("output_dir") or OUTPUT_DIR)
        downloaded = state.get("downloaded_papers") or []
        pdf_paths = [p["local_pdf_path"] for p in downloaded if p.get("downloaded") and p.get("local_pdf_path")]
        if not pdf_paths:
            warns = state.get("warnings") or []
            warns.append("No PDFs downloaded; continuing with abstracts-only mode.")
            state["warnings"] = warns
            state["abstract_only"] = True
            return {"ingested_documents": [], "parsed_chunks": [], "abstract_only": True}
        docs = ingest_pdfs_to_documents(pdf_paths, downloaded)
        ensure_dir(output_dir)
        # Save parsed chunks for transparency/debug (can be large)
        parsed = [{"page_content": d.page_content, "metadata": d.metadata} for d in docs]
        write_json(output_dir / "parsed_chunks.json", parsed)
        console.log(f"ingested chunks: {len(docs)}")
        return {"ingested_documents": docs, "parsed_chunks": parsed}

    return node


def create_build_index_node():
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        console.log("[bold]build_index[/bold]")
        docs = state.get("ingested_documents") or []
        if not docs:
            return {"vector_index_path": None, "vectorstore": None, "retriever_tool": None}
        vectorstore = build_vector_store_from_documents(docs)
        index_path = state.get("faiss_index_path") or FAISS_INDEX_PATH
        save_vector_store(vectorstore, index_path)
        tool = get_retriever_tool(vectorstore, k=8)
        return {"vector_index_path": index_path, "vectorstore": vectorstore, "retriever_tool": tool}

    return node


def create_read_papers_node():
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        console.log("[bold]read_papers[/bold]")
        output_dir = Path(state.get("output_dir") or OUTPUT_DIR)
        papers = state.get("downloaded_papers") or state.get("selected_papers") or []
        vectorstore = state.get("vectorstore")
        if state.get("abstract_only"):
            vectorstore = None
        summaries = summarize_papers(papers, vectorstore=vectorstore, k=8)
        ensure_dir(output_dir)
        write_json(output_dir / "paper_summaries.json", [s.model_dump() for s in summaries])
        return {"paper_summaries": summaries}

    return node


def create_critique_papers_node():
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        console.log("[bold]critique_papers[/bold]")
        output_dir = Path(state.get("output_dir") or OUTPUT_DIR)
        summaries = state.get("paper_summaries") or []
        critiques = critique_papers(summaries)
        ensure_dir(output_dir)
        write_json(output_dir / "critiques.json", [c.model_dump() for c in critiques])
        return {"critiques": critiques}

    return node


def create_analyze_gaps_node():
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        console.log("[bold]analyze_gaps[/bold]")
        output_dir = Path(state.get("output_dir") or OUTPUT_DIR)
        report = analyze_gaps(state["topic"], state.get("paper_summaries") or [], state.get("critiques") or [])
        ensure_dir(output_dir)
        write_json(output_dir / "gap_analysis_report.json", report.model_dump())
        return {"gap_report": report}

    return node


def create_compare_papers_node():
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        console.log("[bold]compare_papers[/bold]")
        output_dir = Path(state.get("output_dir") or OUTPUT_DIR)
        md, rows = build_comparison_table(state.get("paper_summaries") or [])
        ensure_dir(output_dir)
        (output_dir / "comparison_table.md").write_text(md, encoding="utf-8")
        write_json(output_dir / "comparison_table.json", rows)
        return {"comparison_table": md}

    return node


def create_write_related_work_node():
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        console.log("[bold]write_related_work[/bold]")
        output_dir = Path(state.get("output_dir") or OUTPUT_DIR)
        related, gaps_md, novelty, contrib = write_related_work(state["topic"], state.get("paper_summaries") or [], state["gap_report"])
        ensure_dir(output_dir)
        (output_dir / "related_work.md").write_text(related, encoding="utf-8")
        (output_dir / "research_gaps.md").write_text(gaps_md, encoding="utf-8")
        (output_dir / "novelty_justification.md").write_text(novelty, encoding="utf-8")
        (output_dir / "contributions.md").write_text(contrib, encoding="utf-8")
        return {"related_work": related}

    return node


def create_verify_citations_node():
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        console.log("[bold]verify_citations[/bold]")
        output_dir = Path(state.get("output_dir") or OUTPUT_DIR)
        related_work = state.get("related_work") or ""
        report = verify_citations(
            related_work,
            vectorstore=state.get("vectorstore"),
            summaries=state.get("paper_summaries") or [],
        )
        ensure_dir(output_dir)
        write_json(output_dir / "citation_verification_report.json", report.model_dump())
        # lightweight markdown rendering
        md_lines = [
            "# Citation Verification Report",
            "",
            f"- Total claims: {report.total_claims}",
            f"- Supported: {report.supported_claims}",
            f"- Partially supported: {report.partially_supported_claims}",
            f"- Unsupported: {report.unsupported_claims}",
            f"- Too strong: {report.too_strong_claims}",
            "",
            "## Claims",
        ]
        for c in report.claims:
            md_lines.append(f"### {c.status.upper()}")
            md_lines.append(c.claim)
            md_lines.append("")
            md_lines.append(c.explanation)
            if c.suggested_revision:
                md_lines.append("")
                md_lines.append("Suggested revision:")
                md_lines.append(c.suggested_revision)
            md_lines.append("")
        (output_dir / "citation_verification_report.md").write_text("\n".join(md_lines), encoding="utf-8")

        # One conservative revision pass if the draft is clearly problematic.
        if (report.unsupported_claims + report.too_strong_claims) > 0 and not state.get("_revised_once"):
            console.log("[yellow]Revising related work once due to unsupported/too-strong claims[/yellow]")
            revised_related, _, _, _ = write_related_work(
                state["topic"],
                state.get("paper_summaries") or [],
                state["gap_report"],
            )
            (output_dir / "related_work_verified.md").write_text(revised_related, encoding="utf-8")
            state["_revised_once"] = True
            return {"verification_report": report, "related_work": revised_related, "_revised_once": True}

        return {"verification_report": report}

    return node


def create_finalize_report_node():
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        console.log("[bold]finalize_report[/bold]")
        output_dir = Path(state.get("output_dir") or OUTPUT_DIR)
        report_path, _summary = finalize_run(state, output_dir=output_dir)
        return {"final_report_path": report_path}

    return node
