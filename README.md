# Citation-Grounded Multi-Agent Research Gap Analysis Assistant

An end-to-end **research workflow system** (not a simple PDF chatbot) that:

1. searches for relevant research papers, 2) prefers legally available open-access PDFs (published when possible), 3) downloads and parses PDFs, 4) builds a FAISS RAG index, 5) extracts structured paper summaries, 6) critiques papers, 7) clusters research gaps, 8) generates a related work draft with citations, and 9) verifies whether claims are supported by retrieved evidence.

This system only downloads **legally available open-access PDFs** (Semantic Scholar OA links and optionally Unpaywall OA links). It does not bypass paywalls.

## Problem Statement

Researchers waste time stitching together: paper search, version/PDF availability checks, PDF parsing, note-taking, cross-paper comparison, and claim verification. This project automates that workflow while keeping outputs **citation-grounded** and **auditable** (via saved intermediate artifacts and evidence retrieval).

## Why This Is Not a PDF Chatbot

- The primary output is a **research report** (`final_report.md`) with gap clusters, comparisons, and a related work draft.
- It runs a **multi-stage pipeline** (search → rank → version resolve → download → ingest/index → structured extraction → critique → gap clustering → writing → claim verification).
- It saves transparent artifacts (`candidate_papers.json`, `version_resolution.json`, `download_report.json`, `parsed_chunks.json`, summaries/critiques/gaps, and verification reports).

## Architecture (LangGraph Workflow)

```
START
  -> expand_queries
  -> search_papers (Semantic Scholar)
  -> rank_papers
  -> resolve_versions (+ optional Unpaywall)
  -> download_pdfs (OA only)
  -> ingest_pdfs (PyMuPDF)
  -> build_index (FAISS)
  -> read_papers (structured extraction)
  -> critique_papers
  -> analyze_gaps
  -> compare_papers
  -> write_related_work
  -> verify_citations
  -> finalize_report
END
```

## Tech Stack

- Orchestration: LangGraph
- LLM + tools: LangChain + OpenAI
- Vector index: FAISS
- PDF parsing: PyMuPDF
- Paper discovery: Semantic Scholar Graph API (+ optional Unpaywall)
- Structured outputs: Pydantic
- Optional API: FastAPI + Uvicorn

## Project Structure

```
src/
  api/                  # Optional FastAPI service
  agents/               # LangGraph workflow + multi-agent steps
  config/               # Settings + OpenAI clients
  ingestion/            # PDF parsing + chunking
  papers/               # Search, query expansion, ranking, versioning, download
  prompts/              # Prompt templates for each agent
  schemas/              # Pydantic schemas for structured outputs
  utils/                # Small IO helpers
  retriever.py          # FAISS store + retrieval tool
  main.py               # CLI entry point

data/
  papers/               # Downloaded PDFs
  metadata/             # Download metadata
  index/                # FAISS index
outputs/                # Reports and JSON artifacts
tests/                  # Basic unit tests
```

## Setup

Prereqs: Python 3.10+, OpenAI API key.

Install:

```bash
pip install -e .
```

Create `.env`:

```bash
OPENAI_API_KEY=...
SEMANTIC_SCHOLAR_API_KEY=...   # optional
UNPAYWALL_EMAIL=...            # optional (required by Unpaywall policy)
OPENAI_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
MAX_PAPERS=10
FAISS_INDEX_PATH=data/index/faiss_research_papers
OUTPUT_DIR=outputs
```

## Run (CLI)

```bash
python -m src.main --topic "privacy-preserving vision-based fall detection for elderly care" --max-papers 8
```

Useful flags:

- `--output-dir outputs`
- `--index-path data/index/faiss_research_papers`
- `--abstract-only` (no downloads/indexing; metadata-only)
- `--skip-download` (keeps pipeline best-effort)
- `--verbose`

Outputs are written to `OUTPUT_DIR`, including `final_report.md` and `run_summary.json`.

## Run (API, optional)

```bash
uvicorn src.api.app:app --reload
```

Endpoints:

- `POST /research/run`
- `GET /research/{run_id}/status`
- `GET /research/{run_id}/outputs`

## Limitations

- Paper selection is heuristic (no full-text relevance model yet).
- PDF parsing is best-effort and may miss figures/tables.
- Citation verification reduces hallucinations but does not guarantee perfect correctness.

## Example Outputs (files)

- `outputs/final_report.md`
- `outputs/candidate_papers.json`
- `outputs/selected_papers.json`
- `outputs/version_resolution.json`
- `outputs/download_report.json`
- `outputs/parsed_chunks.json`
- `outputs/paper_summaries.json`
- `outputs/critiques.json`
- `outputs/gap_analysis_report.json`
- `outputs/comparison_table.md`
- `outputs/related_work.md`
- `outputs/related_work_verified.md` (if revision happens)
- `outputs/citation_verification_report.md`
