from __future__ import annotations

from typing import Any, Dict, Optional

import requests


def fetch_unpaywall_pdf_url(doi: str, *, email: str, timeout_s: int = 20) -> Optional[Dict[str, Any]]:
    """
    Returns a small dict with best OA PDF info when available, else None.
    """
    doi = doi.strip()
    if not doi:
        return None
    url = f"https://api.unpaywall.org/v2/{doi}"
    resp = requests.get(url, params={"email": email}, timeout=timeout_s, headers={"Accept": "application/json"})
    resp.raise_for_status()
    payload = resp.json()

    best = payload.get("best_oa_location")
    if not isinstance(best, dict):
        return None
    pdf_url = best.get("url_for_pdf")
    if not pdf_url:
        return None

    return {
        "unpaywall_pdf_url": pdf_url,
        "unpaywall_version": best.get("version"),
        "unpaywall_host_type": best.get("host_type"),
        "unpaywall_landing_url": best.get("url"),
    }

