from __future__ import annotations

import argparse
from typing import Any, Dict

from rich.console import Console

from .agents import build_graph
from .config import MAX_PAPERS, OUTPUT_DIR
from .utils.paths import ensure_dir
from .utils.logging import setup_logging


console = Console()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="Citation-Grounded Multi-Agent Research Gap Analysis Assistant",
        description="Runs a research-paper RAG workflow: search -> download OA PDFs -> index -> summarize -> critique -> gap analysis -> write -> verify.",
    )
    parser.add_argument("--topic", type=str, default=None, help="Research topic (quoted string).")
    parser.add_argument("--max-papers", type=int, default=None, help="Max papers to select (default from settings).")
    parser.add_argument("--output-dir", type=str, default=None, help="Directory to write outputs (default from settings).")
    parser.add_argument("--index-path", type=str, default=None, help="Override FAISS index path.")
    parser.add_argument("--abstract-only", action="store_true", help="Skip downloads/indexing; use abstracts+metadata only.")
    parser.add_argument("--skip-download", action="store_true", help="Skip PDF downloading (keeps rest of pipeline best-effort).")
    parser.add_argument("--verbose", action="store_true", help="Verbose logs.")
    return parser.parse_args()


def _interactive_fallback(args: argparse.Namespace) -> argparse.Namespace:
    if not args.topic:
        args.topic = input("Enter research topic: ").strip()
    if not args.max_papers:
        raw = input(f"Enter max number of papers [{MAX_PAPERS}]: ").strip()
        args.max_papers = int(raw) if raw else MAX_PAPERS
    if not args.output_dir:
        args.output_dir = OUTPUT_DIR
    return args


def run(
    topic: str,
    *,
    max_papers: int,
    output_dir: str,
    index_path: str | None = None,
    abstract_only: bool = False,
    skip_download: bool = False,
    verbose: bool = False,
) -> str:
    setup_logging(verbose=verbose)
    ensure_dir(output_dir)
    app = build_graph()
    inputs: Dict[str, Any] = {
        "topic": topic,
        "max_papers": max_papers,
        "output_dir": output_dir,
        "abstract_only": abstract_only,
        "skip_download": skip_download,
        "verbose": verbose,
        "errors": [],
        "warnings": [],
    }
    if index_path:
        inputs["faiss_index_path"] = index_path

    last_state: Dict[str, Any] = {}
    for update in app.stream(inputs):
        for node_name, state_update in update.items():
            console.log(f"[cyan]node[/cyan] {node_name}")
            last_state = {**last_state, **state_update}

    report_path = last_state.get("final_report_path") or "outputs/final_report.md"
    return report_path


def main() -> None:
    args = _interactive_fallback(_parse_args())
    console.print("\n[bold]Citation-Grounded Multi-Agent Research Gap Analysis Assistant[/bold]\n")
    report_path = run(
        args.topic,
        max_papers=args.max_papers,
        output_dir=args.output_dir or OUTPUT_DIR,
        index_path=args.index_path,
        abstract_only=bool(args.abstract_only),
        skip_download=bool(args.skip_download),
        verbose=bool(args.verbose),
    )
    console.print(f"\nDone. Final report: {report_path}\n")


if __name__ == "__main__":
    main()
