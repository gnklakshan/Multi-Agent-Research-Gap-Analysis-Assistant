from __future__ import annotations

from typing import Annotated, Any, List, Optional
from typing_extensions import TypedDict

from langgraph.graph import END, StateGraph

from .nodes import (
    create_analyze_gaps_node,
    create_build_index_node,
    create_compare_papers_node,
    create_critique_papers_node,
    create_download_pdfs_node,
    create_expand_queries_node,
    create_finalize_report_node,
    create_ingest_pdfs_node,
    create_rank_papers_node,
    create_read_papers_node,
    create_resolve_versions_node,
    create_search_papers_node,
    create_verify_citations_node,
    create_write_related_work_node,
)


class ResearchState(TypedDict, total=False):
    topic: str
    max_papers: int
    output_dir: str
    abstract_only: bool
    skip_download: bool
    verbose: bool
    expanded_queries: List[str]
    candidate_papers: List[dict]
    selected_papers: List[dict]
    downloaded_papers: List[dict]
    parsed_chunks: List[dict]
    ingested_documents: List[Any]
    vector_index_path: Optional[str]
    vectorstore: Any
    retriever_tool: Any
    paper_summaries: List[Any]
    critiques: List[Any]
    gap_report: Any
    comparison_table: Optional[str]
    related_work: Optional[str]
    verification_report: Any
    final_report_path: Optional[str]
    errors: List[str]
    warnings: List[str]


def build_graph() -> Any:
    workflow = StateGraph(ResearchState)

    workflow.add_node("expand_queries", create_expand_queries_node())
    workflow.add_node("search_papers", create_search_papers_node())
    workflow.add_node("rank_papers", create_rank_papers_node())
    workflow.add_node("resolve_versions", create_resolve_versions_node())
    workflow.add_node("download_pdfs", create_download_pdfs_node())
    workflow.add_node("ingest_pdfs", create_ingest_pdfs_node())
    workflow.add_node("build_index", create_build_index_node())
    workflow.add_node("read_papers", create_read_papers_node())
    workflow.add_node("critique_papers", create_critique_papers_node())
    workflow.add_node("analyze_gaps", create_analyze_gaps_node())
    workflow.add_node("compare_papers", create_compare_papers_node())
    workflow.add_node("write_related_work", create_write_related_work_node())
    workflow.add_node("verify_citations", create_verify_citations_node())
    workflow.add_node("finalize_report", create_finalize_report_node())

    workflow.set_entry_point("expand_queries")

    workflow.add_edge("expand_queries", "search_papers")
    workflow.add_edge("search_papers", "rank_papers")
    workflow.add_edge("rank_papers", "resolve_versions")
    workflow.add_edge("resolve_versions", "download_pdfs")
    workflow.add_edge("download_pdfs", "ingest_pdfs")
    workflow.add_edge("ingest_pdfs", "build_index")
    workflow.add_edge("build_index", "read_papers")
    workflow.add_edge("read_papers", "critique_papers")
    workflow.add_edge("critique_papers", "analyze_gaps")
    workflow.add_edge("analyze_gaps", "compare_papers")
    workflow.add_edge("compare_papers", "write_related_work")
    workflow.add_edge("write_related_work", "verify_citations")
    workflow.add_edge("verify_citations", "finalize_report")
    workflow.add_edge("finalize_report", END)

    return workflow.compile()
