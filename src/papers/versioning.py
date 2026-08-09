from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List, Optional, Tuple

from ..utils.paths import safe_filename


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



PUBLISHED_TYPES = {
    "JournalArticle": "journal",
    "Conference": "conference",
    "Review": "journal",
    "Book": "published",
    "BookSection": "published",
    "Dataset": "published",
}


def classify_version(paper: Dict[str, Any]) -> Tuple[str, str]:
    """
    Returns (selected_version, reason).
    """
    venue = (paper.get("venue") or "").strip()
    url = (paper.get("url") or "").strip()
    title = (paper.get("title") or "").strip()
    external_ids = paper.get("externalIds") or {}
    doi = external_ids.get("DOI") if isinstance(external_ids, dict) else None

    pub_types: List[str] = paper.get("publicationTypes") or []
    if isinstance(pub_types, str):
        pub_types = [pub_types]

    for t in pub_types:
        if t in PUBLISHED_TYPES:
            kind = PUBLISHED_TYPES[t]
            return kind, f"publicationTypes contains {t}"

    # Heuristics
    if doi and venue:
        return "published", "DOI and venue present"

    arxivish = bool(re.search(r"\barxiv\b", venue, flags=re.I)) or "arxiv" in url.lower() or "arxiv" in title.lower()
    if arxivish and not doi:
        return "preprint", "arXiv-like venue/url and no DOI"

    if arxivish and doi:
        return "preprint", "arXiv-like venue/url (DOI present but venue suggests preprint)"

    return "unknown", "insufficient signals"


def choose_pdf_candidate(paper: Dict[str, Any]) -> Tuple[Optional[str], str, str]:
    """
    Returns (pdf_url, pdf_source, reason).
    pdf_source values:
    - unpaywall_publisher
    - semantic_scholar_oa
    - arxiv
    - none
    """
    if paper.get("unpaywall_pdf_url") and (
        paper.get("unpaywall_version") == "publishedVersion" or paper.get("unpaywall_host_type") == "publisher"
    ):
        return paper["unpaywall_pdf_url"], "unpaywall_publisher", "Unpaywall best_oa_location publishedVersion/publisher"

    oa = paper.get("openAccessPdf") or {}
    if isinstance(oa, dict) and oa.get("url"):
        return oa["url"], "semantic_scholar_oa", "Semantic Scholar openAccessPdf"

    url = (paper.get("url") or "").lower()
    if "arxiv" in url:
        if url.endswith(".pdf"):
            return paper.get("url"), "arxiv", "arXiv PDF URL"
        if "/abs/" in url:
            return paper.get("url", "").replace("/abs/", "/pdf/") + ".pdf", "arxiv", "constructed arXiv PDF URL"

    return None, "none", "no OA PDF candidate"


def resolve_versions(papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for p in papers:
        version, reason = classify_version(p)
        pdf_url, pdf_source, pdf_reason = choose_pdf_candidate(p)
        p2 = dict(p)
        p2["paper_id"] = _paper_id(p)
        p2["selected_version"] = version
        p2["version_reason"] = reason
        p2["pdf_candidate_url"] = pdf_url
        p2["pdf_source"] = pdf_source
        p2["pdf_reason"] = pdf_reason
        out.append(p2)
    return out
