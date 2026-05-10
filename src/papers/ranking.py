from __future__ import annotations

import math
import re
from datetime import date
from typing import Any, Dict, List, Optional, Tuple


def _normalize_title(title: str) -> str:
    title = title.lower().strip()
    title = re.sub(r"[^a-z0-9 ]+", " ", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title


def _topic_keywords(topic: str) -> List[str]:
    tokens = re.findall(r"[a-zA-Z0-9]+", (topic or "").lower())
    stop = {"for", "and", "or", "the", "a", "an", "to", "of", "in", "on", "with", "using", "via"}
    return [t for t in tokens if t not in stop and len(t) > 2]


def _relevance_score(topic: str, paper: Dict[str, Any]) -> float:
    kws = _topic_keywords(topic)
    if not kws:
        return 0.0
    text = f"{paper.get('title') or ''} {paper.get('abstract') or ''}".lower()
    hits = sum(1 for k in kws if k in text)
    # Soft saturation: aim for ~6 keyword hits as "high relevance"
    return min(1.0, hits / 6.0)


def _recency_score(year: Optional[int]) -> float:
    if not year:
        return 0.2
    current_year = date.today().year
    age = max(0, current_year - year)
    if age <= 1:
        return 1.0
    if age <= 3:
        return 0.8
    if age <= 5:
        return 0.6
    if age <= 10:
        return 0.35
    return 0.2


def _citation_score(citations: Optional[int]) -> float:
    if citations is None:
        return 0.0
    return min(1.0, math.log1p(max(0, citations)) / math.log1p(5000))


def _venue_score(venue: Optional[str]) -> float:
    if not venue:
        return 0.2
    v = venue.lower()
    if "arxiv" in v:
        return 0.2
    if any(x in v for x in ["ieee", "acm", "springer", "elsevier", "nature", "neurips", "icml", "cvpr", "iccv", "eccv", "aaai", "ijcai"]):
        return 0.95
    return 0.8


def _pdf_score(paper: Dict[str, Any]) -> float:
    oa = paper.get("openAccessPdf") or {}
    if isinstance(oa, dict) and oa.get("url"):
        return 1.0
    if paper.get("unpaywall_pdf_url"):
        return 1.0
    return 0.0


def _publication_type_score(paper: Dict[str, Any]) -> float:
    v = (paper.get("selected_version") or paper.get("version") or "unknown").lower()
    if v == "unknown":
        pub_types = paper.get("publicationTypes") or []
        if isinstance(pub_types, str):
            pub_types = [pub_types]
        if any(t in {"JournalArticle", "Conference", "Review"} for t in pub_types):
            v = "published"
    if v in {"journal", "conference", "published"}:
        return 1.0
    if v in {"accepted_manuscript"}:
        return 0.7
    if v in {"preprint"}:
        return 0.3
    return 0.5


def _doi_bonus(paper: Dict[str, Any]) -> float:
    ext = paper.get("externalIds") or {}
    doi = ext.get("DOI") if isinstance(ext, dict) else None
    return 1.0 if doi else 0.0


def score_paper(topic: str, paper: Dict[str, Any]) -> Tuple[float, Dict[str, float]]:
    rel = _relevance_score(topic, paper)
    rec = _recency_score(paper.get("year"))
    cit = _citation_score(paper.get("citationCount"))
    ven = _venue_score(paper.get("venue"))
    pdf = _pdf_score(paper)
    ptype = _publication_type_score(paper)
    doi = _doi_bonus(paper)

    # DOI is folded into venue_score and publication_type_score subtly (bonus).
    ven = min(1.0, ven + 0.15 * doi)
    ptype = min(1.0, ptype + 0.10 * doi)

    final = 0.35 * rel + 0.20 * rec + 0.15 * cit + 0.10 * ven + 0.10 * pdf + 0.10 * ptype
    parts = {
        "relevance_score": rel,
        "recency_score": rec,
        "citation_score": cit,
        "venue_score": ven,
        "pdf_score": pdf,
        "publication_type_score": ptype,
        "final_score": final,
    }
    return final, parts


def _dedupe(papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen_doi = set()
    seen_title = set()
    out: List[Dict[str, Any]] = []
    for p in papers:
        external = p.get("externalIds") or {}
        doi = external.get("DOI") if isinstance(external, dict) else None
        title = p.get("title") or ""
        tnorm = _normalize_title(title)
        if doi:
            key = doi.lower().strip()
            if key in seen_doi:
                continue
            seen_doi.add(key)
        else:
            if tnorm and tnorm in seen_title:
                continue
            if tnorm:
                seen_title.add(tnorm)
        out.append(p)
    return out


def rank_and_select_papers(
    topic: str,
    papers: List[Dict[str, Any]],
    *,
    top_n: int = 10,
    expanded_queries: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    combined_topic = topic
    if expanded_queries:
        combined_topic = topic + " " + " ".join(expanded_queries[:8])

    cleaned = [p for p in papers if p.get("title")]
    deduped = _dedupe(cleaned)
    scored: List[Dict[str, Any]] = []
    for p in deduped:
        final, parts = score_paper(combined_topic, p)
        p2 = dict(p)
        p2["ranking"] = parts
        scored.append(p2)
    scored.sort(key=lambda x: x.get("ranking", {}).get("final_score", 0.0), reverse=True)
    return scored[:top_n]
