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

    Without an API key the public endpoint allows roughly 1 req/s with a hard burst
    cap, so we default to 5 s between queries and respect Retry-After on 429.
    """
    # Use a conservative gap when running without an API key to avoid 429s
    effective_interval = min_interval_s if api_key else max(min_interval_s, 5.0)
    limiter = RateLimiter(min_interval_s=effective_interval)
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
            # If still 429 after retries, respect Retry-After and skip this query
            if resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After")
                sleep_s = float(retry_after) if retry_after and str(retry_after).isdigit() else 15.0
                log.warning(
                    "Semantic Scholar 429 on query '%s'; sleeping %.0fs before next query", q, sleep_s
                )
                time.sleep(sleep_s)
                results.append({
                    "paperId": None, "title": None, "abstract": None,
                    "error": "rate_limited_429", "query_used": q,
                })
                continue
            resp.raise_for_status()
            payload = resp.json()
            for p in payload.get("data", []) or []:
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
        title_key = _normalize_title(p.get("title") or "")
        if title_key in seen_title:
            continue

        ext = p.get("externalIds") or {}
        doi = ext.get("DOI") if isinstance(ext, dict) else None
        if doi:
            doi_key = doi.lower().strip()
            if doi_key in seen_doi:
                continue
            seen_doi.add(doi_key)

        seen_title.add(title_key)
        out.append(p)
    return out


def _get_with_retry(
    session: requests.Session,
    url: str,
    *,
    headers: Dict[str, str],
    params: Dict[str, str],
    timeout_s: int,
    max_retries: int = 2,
) -> requests.Response:
    """HTTP GET with exponential backoff. Returns the final response even on 429
    so the caller can inspect the status code and Retry-After header."""
    backoff = 2.0
    last_exc: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        try:
            resp = session.get(url, headers=headers, params=params, timeout=timeout_s)
            # Only retry on transient server errors, not 429 (handled by caller)
            if resp.status_code in {500, 502, 503, 504} and attempt < max_retries:
                time.sleep(min(12.0, backoff ** (attempt + 1)))
                continue
            return resp
        except Exception as e:
            last_exc = e
            if attempt >= max_retries:
                break
            time.sleep(min(12.0, backoff ** (attempt + 1)))
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
