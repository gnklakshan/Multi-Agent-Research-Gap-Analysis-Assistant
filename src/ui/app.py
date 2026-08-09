from __future__ import annotations

import asyncio
from pathlib import Path
import threading
from typing import Any, Dict, List

from nicegui import app, ui

from ..agents.graph import build_graph
from ..config.settings import (
    FAISS_INDEX_PATH,
    MAX_PAPERS,
    OPENAI_API_KEY,
    OUTPUT_DIR,
)
from ..utils.json_io import read_json

# High-level pipeline phases grouping the 14 graph nodes for intuitive UX
PIPELINE_PHASES = [
    {
        "phase_id": 1,
        "name": "Discovery & Retrieval",
        "icon": "travel_explore",
        "nodes": {"expand_queries", "search_papers", "rank_papers", "resolve_versions", "download_pdfs"},
        "desc": "Searching Semantic Scholar, ranking papers, resolving open-access versions & fetching PDFs",
    },
    {
        "phase_id": 2,
        "name": "Parsing & RAG Indexing",
        "icon": "auto_stories",
        "nodes": {"ingest_pdfs", "build_index"},
        "desc": "Extracting full text via PyMuPDF, chunking, and embedding into FAISS vector store",
    },
    {
        "phase_id": 3,
        "name": "Multi-Agent Synthesis",
        "icon": "psychology",
        "nodes": {"read_papers", "critique_papers", "analyze_gaps", "compare_papers"},
        "desc": "Structured paper summarization, methodological critiques, and gap clustering",
    },
    {
        "phase_id": 4,
        "name": "Writing & Citation Audit",
        "icon": "verified_user",
        "nodes": {"write_related_work", "verify_citations", "finalize_report"},
        "desc": "Drafting manuscript with inline citations and auditing claims against RAG evidence",
    },
]

# Mapping individual nodes to friendly descriptions
NODE_DESCRIPTIONS = {
    "expand_queries": "🔍 Expanding topic into multi-query search strings...",
    "search_papers": "🌐 Querying Semantic Scholar Academic API...",
    "rank_papers": "🏆 Scoring papers by relevance, recency, and venue...",
    "resolve_versions": "📑 Checking Unpaywall & published OA versions...",
    "download_pdfs": "📥 Downloading open-access PDF full texts...",
    "ingest_pdfs": "📄 Parsing PDF layout & generating chunks...",
    "build_index": "🧠 Embedding chunks into FAISS vector store...",
    "read_papers": "📖 Extracting methodologies, datasets & findings...",
    "critique_papers": "🧐 Identifying methodological limitations & risks...",
    "analyze_gaps": "💡 Clustering open research gaps & challenges...",
    "compare_papers": "📊 Synthesizing comparative analysis matrix...",
    "write_related_work": "✍️ Drafting citation-grounded manuscript...",
    "verify_citations": "⚖️ Auditing claim markers against vector store...",
    "finalize_report": "🚀 Assembling executive final report...",
}

# Modern UI Theme Stylesheet
UI_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --bg-dark: #07090e;
    --card-bg: rgba(15, 23, 42, 0.7);
    --border-color: rgba(255, 255, 255, 0.08);
    --accent-indigo: #6366f1;
    --accent-cyan: #06b6d4;
    --accent-emerald: #10b981;
}

body {
    font-family: 'Plus Jakarta Sans', sans-serif;
    background-color: var(--bg-dark);
    color: #f8fafc;
}

.hero-card {
    background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.85) 100%);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(99, 102, 241, 0.2);
    box-shadow: 0 20px 50px -10px rgba(0, 0, 0, 0.5);
    border-radius: 20px;
}

.glass-card {
    background: var(--card-bg);
    backdrop-filter: blur(16px);
    border: 1px solid var(--border-color);
    border-radius: 16px;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.glass-card:hover {
    border-color: rgba(255, 255, 255, 0.14);
}

.metric-card {
    background: rgba(30, 41, 59, 0.4);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 14px;
    padding: 16px;
}

.phase-step-card {
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    border-radius: 14px;
    padding: 14px 18px;
    background: rgba(30, 41, 59, 0.4);
    border: 1px solid rgba(255, 255, 255, 0.05);
}

.phase-active {
    background: rgba(99, 102, 241, 0.15) !important;
    border: 1px solid var(--accent-indigo) !important;
    box-shadow: 0 0 25px rgba(99, 102, 241, 0.3);
}

.phase-done {
    background: rgba(16, 185, 129, 0.12) !important;
    border: 1px solid var(--accent-emerald) !important;
}

.btn-primary-glow {
    background: linear-gradient(135deg, #6366f1 0%, #06b6d4 100%) !important;
    font-weight: 600;
    letter-spacing: 0.02em;
    box-shadow: 0 4px 20px rgba(99, 102, 241, 0.4);
    transition: all 0.2s ease;
}

.btn-primary-glow:hover {
    box-shadow: 0 6px 28px rgba(6, 182, 212, 0.6);
    transform: translateY(-1px);
}

/* Custom scrollbars */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: rgba(15, 23, 42, 0.5); }
::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #475569; }
"""


def create_ui():
    ui.add_head_html(f"<style>{UI_CSS}</style>")

    # Application Execution State
    app_state = {
        "is_running": False,
        "current_node": None,
        "active_phase": 0,
        "completed_nodes": set(),
        "completed_phases": set(),
        "paper_count": 0,
        "gaps_count": 0,
        "verified_ratio": "N/A",
    }

    event_queue: asyncio.Queue = asyncio.Queue()

    # UI Element Handles
    phase_cards = {}
    phase_icons = {}
    phase_badges = {}
    current_status_label = None
    
    # Inspector & Report Containers
    metrics_row = None
    papers_summary_container = None
    gaps_container = None
    final_report_md = None
    comparison_table_md = None
    verification_md = None
    logs_area = None

    def reset_app_state():
        app_state["is_running"] = True
        app_state["current_node"] = None
        app_state["active_phase"] = 1
        app_state["completed_nodes"].clear()
        app_state["completed_phases"].clear()

        for pid, card in phase_cards.items():
            card.classes(replace="phase-step-card opacity-50")
            phase_icons[pid].props("name=radio_button_unchecked color=slate-400")
            phase_badges[pid].set_text("Pending")
            phase_badges[pid].classes(replace="text-3xs bg-slate-800 text-slate-400 px-2 py-1 rounded-full")

        current_status_label.set_text("Starting research pipeline...")
        logs_area.clear()
        error_banner.classes(add="hidden")

    def _show_error_banner(message: str):
        """Display a structured, actionable error card beneath the stepper."""
        error_banner.classes(remove="hidden")
        error_banner.clear()
        with error_banner:
            with ui.row().classes("items-start gap-3"):
                ui.icon("error_outline", color="red", size="md").classes("mt-0.5 shrink-0")
                with ui.column().classes("gap-2"):
                    ui.label("Search Failed - Action Required").classes("text-sm font-bold text-red-300")
                    # Render each line of the message
                    for line in message.splitlines():
                        if line.strip():
                            ui.label(line).classes("text-xs text-slate-300 leading-relaxed")
                    with ui.row().classes("gap-2 mt-2 flex-wrap"):
                        ui.button(
                            "Get Free API Key",
                            on_click=lambda: ui.navigate.to("https://www.semanticscholar.org/product/api", new_tab=True),
                        ).props("outline size=sm icon=key").classes("text-xs text-cyan-300")
                        ui.button(
                            "Retry Now",
                            on_click=launch_analysis,
                        ).props("outline size=sm icon=refresh").classes("text-xs text-emerald-300")
        current_status_label.set_text("Search failed - see error banner below for next steps.")

    def update_phase_ui(phase_id: int, status: str):
        if phase_id not in phase_cards:
            return
        card = phase_cards[phase_id]
        icon = phase_icons[phase_id]
        badge = phase_badges[phase_id]

        if status == "active":
            card.classes(replace="phase-step-card phase-active")
            icon.props("name=sync color=cyan").classes("animate-spin")
            badge.set_text("In Progress")
            badge.classes(replace="text-3xs bg-indigo-900/80 text-cyan-200 px-2.5 py-1 rounded-full font-semibold")
        elif status == "completed":
            card.classes(replace="phase-step-card phase-done")
            icon.props("name=check_circle color=emerald").classes(remove="animate-spin")
            badge.set_text("Completed")
            badge.classes(replace="text-3xs bg-emerald-900/80 text-emerald-200 px-2.5 py-1 rounded-full font-semibold")

    def determine_phase(node_name: str) -> int:
        for p in PIPELINE_PHASES:
            if node_name in p["nodes"]:
                return p["phase_id"]
        return 1

    def populate_results_data(node_name: str, state_update: Dict[str, Any]):
        out_dir = Path(output_dir_input.value or OUTPUT_DIR)

        # Update Papers Metrics & Cards
        if node_name == "rank_papers":
            papers = state_update.get("selected_papers") or []
            app_state["paper_count"] = len(papers)
            metric_paper_count.set_text(str(len(papers)))

            papers_summary_container.clear()
            with papers_summary_container:
                ui.label("Selected Research Papers").classes("text-sm font-bold text-slate-200 mb-2")
                for idx, p in enumerate(papers, 1):
                    with ui.column().classes("glass-card p-3 w-full mb-2"):
                        with ui.row().classes("justify-between items-center w-full"):
                            ui.label(f"#{idx} {p.get('title')}").classes("text-xs font-semibold text-sky-200")
                            ui.badge(f"Score: {p.get('final_score', 0):.2f}", color="indigo").classes("text-3xs")
                        with ui.row().classes("text-3xs text-slate-400 gap-4 mt-1"):
                            ui.label(f"🗓️ {p.get('year') or 'N/A'}")
                            ui.label(f"🏛️ {p.get('venue') or 'Academic Venue'}")
                            if p.get("externalIds", {}).get("DOI"):
                                ui.label(f"🔗 DOI: {p['externalIds']['DOI']}")

        # Update Research Gaps — reads from state first, then falls back to file
        elif node_name == "analyze_gaps":
            gap_report_obj = state_update.get("gap_report")
            if gap_report_obj is not None:
                if hasattr(gap_report_obj, "model_dump"):
                    gaps_data = gap_report_obj.model_dump()
                else:
                    gaps_data = gap_report_obj
            else:
                gaps_file = out_dir / "gap_analysis_report.json"
                gaps_data = read_json(gaps_file, default={}) if gaps_file.exists() else {}

            # CORRECT KEY: schema uses "common_gaps" not "gaps"
            gap_items = gaps_data.get("common_gaps") or gaps_data.get("gaps") or []
            app_state["gaps_count"] = len(gap_items)
            metric_gap_count.set_text(str(len(gap_items)))

            gaps_container.clear()
            with gaps_container:
                ui.label(f"Research Gap Clusters ({len(gap_items)} identified)").classes(
                    "text-sm font-bold text-amber-300 mb-3"
                )
                for gap in gap_items:
                    pub_level = gap.get("publication_level", "either")
                    acad_depth = gap.get("academic_depth", "MSc/PhD")
                    novelty = gap.get("novelty_score", 5)
                    strength = gap.get("strength_of_evidence", "medium")

                    pub_color = {"journal": "cyan", "conference": "purple", "either": "indigo"}.get(pub_level, "indigo")
                    depth_color = {"BSc/MSc": "emerald", "MSc/PhD": "amber", "PhD/Postdoc": "red"}.get(acad_depth, "amber")
                    strength_color = {"high": "emerald", "medium": "amber", "low": "red"}.get(strength, "amber")

                    with ui.column().classes("glass-card p-4 border-l-4 border-l-amber-500 w-full mb-4 gap-3"):
                        # Header
                        with ui.row().classes("justify-between items-start w-full"):
                            ui.label(f"💡 {gap.get('gap_name', gap.get('title', 'Research Gap'))}").classes(
                                "text-sm font-bold text-amber-200 flex-1 mr-3"
                            )
                            with ui.row().classes("gap-1 flex-wrap shrink-0"):
                                ui.badge(pub_level.upper(), color=pub_color).classes("text-3xs font-bold")
                                ui.badge(acad_depth, color=depth_color).classes("text-3xs font-bold")
                                ui.badge(f"Evidence: {strength}", color=strength_color).classes("text-3xs")

                        ui.label(gap.get("description", "")).classes("text-xs text-slate-300 leading-relaxed")

                        if gap.get("why_it_matters"):
                            with ui.row().classes("items-start gap-2 bg-slate-900/50 p-2 rounded-lg"):
                                ui.icon("info", color="sky", size="xs").classes("shrink-0 mt-0.5")
                                ui.label(f"Why it matters: {gap['why_it_matters']}").classes(
                                    "text-3xs text-sky-200 italic"
                                )

                        # Novelty score bar
                        with ui.column().classes("gap-1 w-full"):
                            with ui.row().classes("justify-between"):
                                ui.label("Novelty Score").classes("text-3xs text-slate-400 font-semibold")
                                ui.label(f"{novelty}/10").classes("text-3xs text-amber-300 font-bold")
                            novelty_pct = novelty * 10
                            bar_color = "#ef4444" if novelty >= 8 else "#f59e0b" if novelty >= 5 else "#6366f1"
                            ui.html(
                                f'<div style="background:#1e293b;border-radius:4px;height:6px;width:100%">'
                                f'<div style="background:{bar_color};border-radius:4px;height:6px;'
                                f'width:{novelty_pct}%;transition:width 0.5s ease"></div></div>'
                            )

                        # Research Paths
                        paths = gap.get("research_paths") or []
                        if paths:
                            with ui.expansion("Research Directions & Starting Points", icon="fork_right").classes(
                                "w-full bg-slate-900/60 rounded-xl border border-slate-700/40 text-xs"
                            ):
                                with ui.column().classes("gap-3 p-2"):
                                    for i, path in enumerate(paths, 1):
                                        with ui.column().classes(
                                            "bg-indigo-950/40 border border-indigo-800/30 p-3 rounded-lg gap-1"
                                        ):
                                            ui.label(f"Path {i}: {path.get('title')}").classes(
                                                "text-xs font-bold text-indigo-200"
                                            )
                                            ui.label(path.get("description", "")).classes(
                                                "text-3xs text-slate-300 leading-relaxed"
                                            )
                                            with ui.row().classes("gap-2 mt-1 flex-wrap"):
                                                if path.get("methodology_hint"):
                                                    with ui.row().classes(
                                                        "items-center gap-1 bg-slate-800/60 px-2 py-0.5 rounded"
                                                    ):
                                                        ui.icon("build", color="cyan", size="2xs")
                                                        ui.label(f"Method: {path['methodology_hint']}").classes(
                                                            "text-3xs text-cyan-300"
                                                        )
                                                if path.get("expected_contribution"):
                                                    with ui.row().classes(
                                                        "items-center gap-1 bg-slate-800/60 px-2 py-0.5 rounded"
                                                    ):
                                                        ui.icon("star", color="amber", size="2xs")
                                                        ui.label(f"Contribution: {path['expected_contribution']}").classes(
                                                            "text-3xs text-amber-300"
                                                        )

                        # Challenges + Datasets
                        challenges = gap.get("key_challenges") or []
                        datasets = gap.get("suggested_datasets_or_benchmarks") or []
                        if challenges or datasets:
                            with ui.row().classes("gap-3 w-full"):
                                if challenges:
                                    with ui.column().classes("flex-1 gap-1"):
                                        ui.label("Key Challenges").classes(
                                            "text-3xs font-bold text-red-300 uppercase tracking-wider"
                                        )
                                        for ch in challenges:
                                            with ui.row().classes("items-start gap-1"):
                                                ui.icon("warning_amber", color="red", size="2xs").classes("shrink-0 mt-0.5")
                                                ui.label(ch).classes("text-3xs text-slate-300")
                                if datasets:
                                    with ui.column().classes("flex-1 gap-1"):
                                        ui.label("Datasets / Benchmarks").classes(
                                            "text-3xs font-bold text-emerald-300 uppercase tracking-wider"
                                        )
                                        for ds in datasets:
                                            with ui.row().classes("items-start gap-1"):
                                                ui.icon("dataset", color="emerald", size="2xs").classes("shrink-0 mt-0.5")
                                                ui.label(ds).classes("text-3xs text-slate-300")

        # Update Comparison Table
        elif node_name == "compare_papers":
            table_file = out_dir / "comparison_table.md"
            if table_file.exists():
                comparison_table_md.set_content(table_file.read_text(encoding="utf-8"))

        # Update Citation Verification
        elif node_name == "verify_citations":
            ver_file = out_dir / "citation_verification_report.md"
            if ver_file.exists():
                verification_md.set_content(ver_file.read_text(encoding="utf-8"))

            ver_json = out_dir / "citation_verification_report.json"
            if ver_json.exists():
                ver_data = read_json(ver_json, default={})
                tot = ver_data.get("total_claims", 0)
                sup = ver_data.get("supported_claims", 0)
                if tot > 0:
                    pct = int((sup / tot) * 100)
                    metric_verified_ratio.set_text(f"{pct}% ({sup}/{tot})")

        # Final Report
        elif node_name == "finalize_report":
            report_file = out_dir / "final_report.md"
            if report_file.exists():
                final_report_md.set_content(report_file.read_text(encoding="utf-8"))

    async def poll_event_queue():
        while not event_queue.empty():
            item = await event_queue.get()

            if "__DONE__" in item:
                app_state["is_running"] = False
                if app_state["active_phase"]:
                    update_phase_ui(app_state["active_phase"], "completed")
                current_status_label.set_text("Gap Analysis Complete! View full report below.")
                launch_btn.props("loading=false disabled=false")
                tabs.set_value(tab_results)
                break

            if "__ERROR__" in item:
                app_state["is_running"] = False
                err = item.get("__ERROR__")
                _show_error_banner(err)
                launch_btn.props("loading=false disabled=false")
                break

            for node_name, state_update in item.items():
                # Check if this node emitted a fatal error (e.g. rate-limited search with no cache)
                fatal = state_update.get("__fatal_error__") if isinstance(state_update, dict) else None
                if fatal:
                    app_state["is_running"] = False
                    _show_error_banner(fatal)
                    launch_btn.props("loading=false disabled=false")
                    return

                current_phase = determine_phase(node_name)

                if current_phase != app_state["active_phase"]:
                    if app_state["active_phase"]:
                        update_phase_ui(app_state["active_phase"], "completed")
                    app_state["active_phase"] = current_phase

                update_phase_ui(current_phase, "active")

                msg = NODE_DESCRIPTIONS.get(node_name, f"Running node {node_name}...")
                current_status_label.set_text(msg)

                with logs_area:
                    ui.label(f"[{node_name}] {msg}").classes("text-3xs font-mono text-cyan-400")

                populate_results_data(node_name, state_update)

    ui.timer(0.2, poll_event_queue)

    def launch_analysis():
        if not topic_input.value or not topic_input.value.strip():
            ui.notify("Please enter a research topic first!", type="warning", icon="warning")
            return

        reset_app_state()
        launch_btn.props("loading=true disabled=true")

        loop = asyncio.get_running_loop()
        topic = topic_input.value.strip()
        max_papers = int(paper_count_select.value)
        out_dir = output_dir_input.value or OUTPUT_DIR
        abstract_only = mode_toggle.value == "abstract"

        def _worker():
            try:
                graph_app = build_graph()
                inputs = {
                    "topic": topic,
                    "max_papers": max_papers,
                    "output_dir": out_dir,
                    "abstract_only": abstract_only,
                    "skip_download": abstract_only,
                    "verbose": False,
                    "errors": [],
                    "warnings": [],
                }
                for update in graph_app.stream(inputs):
                    loop.call_soon_threadsafe(event_queue.put_nowait, update)
                loop.call_soon_threadsafe(event_queue.put_nowait, {"__DONE__": True})
            except Exception as e:
                loop.call_soon_threadsafe(event_queue.put_nowait, {"__ERROR__": str(e)})

        threading.Thread(target=_worker, daemon=True).start()

    # --- TOP NAVBAR ---
    with ui.header().classes("bg-slate-950/90 border-b border-slate-800/80 px-8 py-4 items-center justify-between backdrop-blur-md sticky top-0 z-50"):
        with ui.row().classes("items-center gap-3"):
            with ui.row().classes("bg-gradient-to-r from-indigo-500 to-cyan-500 p-2 rounded-xl text-white shadow-lg"):
                ui.icon("auto_awesome", size="sm")
            with ui.column().classes("gap-0"):
                ui.label("PaperGap AI").classes("text-xl font-extrabold tracking-tight text-white")
                ui.label("Citation-Grounded Research Gap Analysis Engine").classes("text-3xs text-slate-400 font-medium")

        with ui.row().classes("items-center gap-3"):
            openai_status = "GPT-4o Ready" if OPENAI_API_KEY else "API Key Required"
            ui.badge(openai_status, color="emerald" if OPENAI_API_KEY else "amber").classes("text-xs font-semibold px-3 py-1")
            ui.badge("LangGraph Multi-Agent", color="indigo").classes("text-xs font-semibold px-3 py-1")

    # --- MAIN CONTENT CONTAINER ---
    with ui.column().classes("w-full max-w-7xl mx-auto p-6 lg:p-8 gap-8"):

        # --- STEP 1: HERO SEARCH & CONFIGURATION CARD ---
        with ui.card().classes("hero-card p-6 lg:p-8 w-full gap-6"):
            with ui.column().classes("gap-1"):
                ui.label("What research topic do you want to explore?").classes("text-lg font-bold text-white")
                ui.label("Enter any academic domain to discover research gaps, synthesize comparative matrices, and generate verified manuscripts.").classes("text-xs text-slate-400")

            topic_input = ui.textarea(
                placeholder="e.g., Privacy-preserving vision-based fall detection for elderly care",
                value="Privacy-preserving vision-based fall detection for elderly care",
            ).classes("w-full text-sm font-medium").props("outlined dense rows=2 bg-slate-900/80 text-white border-indigo-500/30")

            # Quick Topic Preset Chips
            with ui.row().classes("items-center gap-2 flex-wrap"):
                ui.label("Curated Topics:").classes("text-3xs font-semibold text-slate-400 mr-1")
                ui.chip("Elderly Fall Detection", on_click=lambda: topic_input.set_value("Privacy-preserving vision-based fall detection for elderly care"), icon="elderly").props("outline size=sm text-color=cyan")
                ui.chip("Edge AI Privacy", on_click=lambda: topic_input.set_value("Federated learning for privacy-preserving edge video analytics"), icon="security").props("outline size=sm text-color=indigo")
                ui.chip("Autonomous Driving", on_click=lambda: topic_input.set_value("Multi-agent reinforcement learning for autonomous vehicle path planning"), icon="directions_car").props("outline size=sm text-color=purple")

            with ui.row().classes("w-full justify-between items-center pt-2 border-t border-slate-800/80 gap-4 flex-wrap"):
                with ui.row().classes("items-center gap-4"):
                    ui.label("Target Papers:").classes("text-xs font-semibold text-slate-300")
                    paper_count_select = ui.select(
                        options={4: "4 Papers (Fast)", 8: "8 Papers (Recommended)", 12: "12 Papers (Deep)", 15: "15 Papers (Comprehensive)"},
                        value=8,
                    ).classes("text-xs w-48").props("dense outlined bg-slate-900/60")

                    mode_toggle = ui.toggle(
                        options={"full": "Full Pipeline (PDF Downloads)", "abstract": "Fast (Abstract Only)"},
                        value="full",
                    ).classes("text-xs").props("dense bg-slate-900/60 text-slate-300")

                output_dir_input = ui.input(value=OUTPUT_DIR).classes("hidden")

                launch_btn = ui.button("🚀 Launch Gap Analysis", on_click=launch_analysis).classes("btn-primary-glow text-white px-8 py-3 rounded-xl text-sm")

        # --- STEP 2: HIGH-LEVEL PIPELINE PROGRESS STEPPER ---
        with ui.card().classes("glass-card p-6 w-full gap-4"):
            with ui.row().classes("justify-between items-center w-full mb-1"):
                ui.label("⚡ Workflow Execution Progress").classes("text-sm font-bold text-slate-200")
                current_status_label = ui.label("Ready to launch analysis.").classes("text-xs font-medium text-sky-400")

            with ui.grid().classes("grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 w-full"):
                for phase in PIPELINE_PHASES:
                    pid = phase["phase_id"]
                    with ui.column().classes("phase-step-card opacity-50 justify-between h-full") as card:
                        with ui.row().classes("justify-between items-center w-full mb-2"):
                            with ui.row().classes("items-center gap-2"):
                                icon = ui.icon(phase["icon"], color="slate-400", size="xs")
                                ui.label(f"Phase {pid}").classes("text-3xs font-bold text-slate-400 uppercase tracking-wider")
                            badge = ui.badge("Pending", color="slate-800").classes("text-3xs text-slate-400 px-2 py-1 rounded-full")
                        
                        ui.label(phase["name"]).classes("text-xs font-bold text-slate-100 mb-1")
                        ui.label(phase["desc"]).classes("text-3xs text-slate-400 leading-normal")
                        
                        phase_cards[pid] = card
                        phase_icons[pid] = icon
                        phase_badges[pid] = badge

        # --- ERROR BANNER (hidden by default, shown on fatal pipeline error) ---
        error_banner = ui.column().classes(
            "hidden w-full glass-card p-4 border border-red-800/60 bg-red-950/30 rounded-xl"
        )

        # --- STEP 3: EXECUTIVE RESULTS HUB ---
        with ui.tabs().classes("w-full bg-slate-900/80 rounded-xl p-1.5 border border-slate-800 text-slate-300") as tabs:
            tab_results = ui.tab("📊 Executive Summary", icon="dashboard")
            tab_report = ui.tab("📄 Manuscript Report", icon="article")
            tab_matrix = ui.tab("📊 Paper Comparison Matrix", icon="table_chart")
            tab_audit = ui.tab("⚖️ Citation Verification", icon="verified")
            tab_logs = ui.tab("📜 Execution Logs", icon="terminal")

        with ui.tab_panels(tabs, value=tab_results).classes("w-full glass-panel p-6 lg:p-8 min-h-[500px]"):

            # PANEL 1: EXECUTIVE SUMMARY & TOP METRICS
            with ui.tab_panel(tab_results).classes("w-full gap-6"):
                ui.label("Executive Overview & Metrics").classes("text-base font-bold text-white mb-2")

                # Stat Cards Row
                with ui.grid().classes("grid-cols-1 sm:grid-cols-3 gap-4 w-full mb-4"):
                    with ui.column().classes("metric-card border-l-4 border-l-sky-500"):
                        ui.label("Papers Analyzed").classes("text-3xs font-semibold text-slate-400 uppercase")
                        metric_paper_count = ui.label("0").classes("text-2xl font-extrabold text-sky-400 mt-1")

                    with ui.column().classes("metric-card border-l-4 border-l-amber-500"):
                        ui.label("Research Gaps Found").classes("text-3xs font-semibold text-slate-400 uppercase")
                        metric_gap_count = ui.label("0").classes("text-2xl font-extrabold text-amber-400 mt-1")

                    with ui.column().classes("metric-card border-l-4 border-l-emerald-500"):
                        ui.label("Citation Verification Ratio").classes("text-3xs font-semibold text-slate-400 uppercase")
                        metric_verified_ratio = ui.label("N/A").classes("text-2xl font-extrabold text-emerald-400 mt-1")

                with ui.row().classes("w-full gap-6 grid grid-cols-1 lg:grid-cols-2"):
                    papers_summary_container = ui.column().classes("w-full")
                    gaps_container = ui.column().classes("w-full")

            # PANEL 2: MANUSCRIPT REPORT
            with ui.tab_panel(tab_report).classes("w-full"):
                with ui.row().classes("justify-between items-center w-full mb-4"):
                    ui.label("Generated Related Work Manuscript").classes("text-base font-bold text-white")
                    ui.button("Copy Markdown", on_click=lambda: ui.notify("Copied to clipboard!", type="info")).props("outline dense size=sm icon=content_copy")

                final_report_md = ui.markdown("*Analysis report will be rendered here once the pipeline finishes.*").classes("text-sm text-slate-200 leading-relaxed max-h-[600px] overflow-y-auto pr-3")

            # PANEL 3: COMPARISON MATRIX
            with ui.tab_panel(tab_matrix).classes("w-full"):
                ui.label("Structured Paper Comparison Matrix").classes("text-base font-bold text-white mb-4")
                comparison_table_md = ui.markdown("*Comparison matrix will appear here.*").classes("text-xs text-slate-200 overflow-x-auto")

            # PANEL 4: CITATION AUDIT
            with ui.tab_panel(tab_audit).classes("w-full"):
                ui.label("Citation Grounding Audit Report").classes("text-base font-bold text-white mb-4")
                verification_md = ui.markdown("*Verification audit report will appear here.*").classes("text-xs text-slate-200 max-h-[600px] overflow-y-auto pr-3")

            # PANEL 5: LOGS
            with ui.tab_panel(tab_logs).classes("w-full"):
                ui.label("Detailed Node Execution Logs").classes("text-base font-bold text-white mb-3")
                logs_area = ui.column().classes("w-full bg-black/80 p-4 rounded-xl font-mono text-3xs max-h-[450px] overflow-y-auto border border-slate-800")


if __name__ in {"__main__", "__mp_main__"}:
    create_ui()
    ui.run(title="PaperGap AI - Research Gap Assistant", dark=True, port=8080, reload=False)
