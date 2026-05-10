from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

from ..utils.json_io import write_json
from ..utils.paths import ensure_dir, safe_filename


def _paper_id(p: Dict[str, Any]) -> str:
    ext = p.get("externalIds") or {}
    doi = ext.get("DOI") if isinstance(ext, dict) else None
    if doi:
        return safe_filename(doi)
    pid = p.get("paperId")
    if pid:
        return safe_filename(str(pid))
    title = p.get("title") or "paper"
    return hashlib.sha1(title.encode("utf-8")).hexdigest()[:12]


def choose_pdf_url(p: Dict[str, Any]) -> Tuple[Optional[str], str, str]:
    """
    Returns (pdf_url, source, reason_selected).
    Priority:
    1) Unpaywall publishedVersion (if available)
    2) Semantic Scholar openAccessPdf
    3) arXiv PDF only if no better OA exists
    """
    if p.get("pdf_candidate_url") and p.get("pdf_source"):
        return p.get("pdf_candidate_url"), p.get("pdf_source"), p.get("pdf_reason") or "pre-resolved candidate"

    if p.get("unpaywall_pdf_url") and (p.get("unpaywall_version") == "publishedVersion" or p.get("unpaywall_host_type") == "publisher"):
        return p["unpaywall_pdf_url"], "unpaywall_publisher", "best_oa_location publishedVersion/publisher"

    oa = p.get("openAccessPdf") or {}
    if isinstance(oa, dict) and oa.get("url"):
        return oa["url"], "semantic_scholar_oa", "openAccessPdf provided"

    url = (p.get("url") or "").lower()
    if "arxiv" in url:
        # Semantic Scholar sometimes returns landing page. Try appending .pdf when safe.
        if url.endswith(".pdf"):
            return p.get("url"), "arxiv", "fallback arXiv PDF"
        if "abs" in url:
            return p.get("url", "").replace("/abs/", "/pdf/") + ".pdf", "arxiv", "constructed arXiv PDF URL"
    return None, "none", "no OA pdf url"


def _download_pdf(url: str, dest: Path, *, timeout_s: int = 30) -> None:
    resp = requests.get(url, timeout=timeout_s, stream=True, headers={"Accept": "application/pdf"})
    resp.raise_for_status()
    ctype = (resp.headers.get("Content-Type") or "").lower()
    if "pdf" not in ctype and not url.lower().endswith(".pdf"):
        raise ValueError(f"unexpected content-type: {ctype}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as f:
        for chunk in resp.iter_content(chunk_size=1024 * 256):
            if chunk:
                f.write(chunk)


def download_pdfs(
    papers: List[Dict[str, Any]],
    *,
    papers_dir: str = "data/papers",
    metadata_path: str = "data/metadata/downloaded_papers.json",
    timeout_s: int = 30,
) -> List[Dict[str, Any]]:
    ensure_dir(papers_dir)
    ensure_dir(Path(metadata_path).parent)

    out: List[Dict[str, Any]] = []
    for p in papers:
        pid = _paper_id(p)
        pdf_url, pdf_source, reason = choose_pdf_url(p)
        filename = f"{pid}.pdf"
        local_path = str(Path(papers_dir) / filename)

        record = dict(p)
        record["paper_id"] = pid
        ext = record.get("externalIds") or {}
        record["doi"] = ext.get("DOI") if isinstance(ext, dict) else record.get("doi")
        record["pdf_url"] = pdf_url
        record["local_pdf_path"] = local_path if pdf_url else None
        record["pdf_source"] = pdf_source
        record["reason_selected"] = reason
        record["selected_version"] = record.get("selected_version") or "unknown"
        record["downloaded"] = False
        record["download_error"] = None

        if not pdf_url:
            out.append(record)
            continue

        try:
            _download_pdf(pdf_url, Path(local_path), timeout_s=timeout_s)
            record["downloaded"] = True
        except Exception as e:
            record["download_error"] = f"{type(e).__name__}: {e}"
        out.append(record)

    write_json(metadata_path, out)
    return out
