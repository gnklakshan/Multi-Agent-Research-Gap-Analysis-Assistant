from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import requests

from .query_expansion import expand_queries
from ..utils.logging import get_logger


SEMANTIC_SCHOLAR_SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"


REQUIRED_FIELDS = [
    "paperId",
    "title",
    "authors",
    "year",
    "abstract",
    "venue",
    "publicationTypes",
    "citationCount",
    "externalIds",
    "url",
    "openAccessPdf",
    "publicationDate",
    "fieldsOfStudy",
]

log = get_logger(__name__)


@dataclass
class RateLimiter:
    min_interval_s: float = 1.0
    last_ts: float = 0.0

    def wait(self) -> None:
        now = time.time()
        sleep_s = self.min_interval_s - (now - self.last_ts)
        if sleep_s > 0:
            time.sleep(sleep_s)
        self.last_ts = time.time()


def _headers(api_key: Optional[str]) -> Dict[str, str]:
    h = {"Accept": "application/json"}
    if api_key:
        h["x-api-key"] = api_key
    return h


def search_papers(
    queries: List[str],
    *,
    api_key: Optional[str] = None,
    limit_per_query: int = 20,
    timeout_s: int = 20,
    min_interval_s: float = 1.0,
) -> List[Dict[str, Any]]:
    """
    Searches Semantic Scholar Graph API for each query and returns a flat list of paper metadata dicts.
    Continues on errors and returns whatever it can retrieve.
    """
    limiter = RateLimiter(min_interval_s=min_interval_s)
    fields = ",".join(REQUIRED_FIELDS)
    results: List[Dict[str, Any]] = []
    session = requests.Session()

    for q in queries:
        limiter.wait()
        params = {"query": q, "limit": str(limit_per_query), "fields": fields}
        try:
            resp = _get_with_retry(
                session,
                SEMANTIC_SCHOLAR_SEARCH_URL,
                headers=_headers(api_key),
                params=params,
                timeout_s=timeout_s,
            )
            resp.raise_for_status()
            payload = resp.json()
            for p in payload.get("data", []) or []:
                # Normalize a few fields defensively
                p["query_used"] = q
                results.append(p)
        except Exception as e:
            log.warning("Semantic Scholar query failed: %s (%s)", q, e)
            results.append(
                {
                    "paperId": None,
                    "title": None,
                    "abstract": None,
                    "error": f"search_failed: {type(e).__name__}: {e}",
                    "query_used": q,
                }
            )

    return results


def _normalize_title(title: str) -> str:
    t = (title or "").lower().strip()
    t = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in t)
    return " ".join(t.split())


def dedupe_papers(papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen_doi = set()
    seen_title = set()
    out: List[Dict[str, Any]] = []
    for p in papers:
        if not p.get("title"):
            continue
        ext = p.get("externalIds") or {}
        doi = ext.get("DOI") if isinstance(ext, dict) else None
        if doi:
            key = doi.lower().strip()
            if key in seen_doi:
                continue
            seen_doi.add(key)
        else:
            key = _normalize_title(p.get("title") or "")
            if key in seen_title:
                continue
            seen_title.add(key)
        out.append(p)
    return out


def _get_with_retry(
    session: requests.Session,
    url: str,
    *,
    headers: Dict[str, str],
    params: Dict[str, str],
    timeout_s: int,
    max_retries: int = 3,
) -> requests.Response:
    backoff = 1.5
    last_exc: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        try:
            resp = session.get(url, headers=headers, params=params, timeout=timeout_s)
            if resp.status_code in {429, 500, 502, 503, 504} and attempt < max_retries:
                retry_after = resp.headers.get("Retry-After")
                sleep_s = float(retry_after) if retry_after and retry_after.isdigit() else (backoff**attempt)
                time.sleep(min(10.0, sleep_s))
                continue
            return resp
        except Exception as e:
            last_exc = e
            if attempt >= max_retries:
                break
            time.sleep(min(10.0, backoff**attempt))
    raise RuntimeError(f"request_failed after retries: {last_exc}")


def search_papers_for_topic(
    topic: str,
    *,
    api_key: Optional[str] = None,
    limit_per_query: int = 20,
    timeout_s: int = 20,
    min_interval_s: float = 1.0,
) -> List[Dict[str, Any]]:
    """
    Convenience wrapper: expands a topic into queries and searches Semantic Scholar.
    """
    queries = expand_queries(topic)
    return search_papers(
        queries,
        api_key=api_key,
        limit_per_query=limit_per_query,
        timeout_s=timeout_s,
        min_interval_s=min_interval_s,
    )
