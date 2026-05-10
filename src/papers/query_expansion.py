from __future__ import annotations

import re
from typing import List


def _keywords(topic: str) -> List[str]:
    tokens = re.findall(r"[a-zA-Z0-9]+", topic.lower())
    stop = {
        "for",
        "and",
        "or",
        "the",
        "a",
        "an",
        "to",
        "of",
        "in",
        "on",
        "with",
        "using",
        "via",
        "based",
    }
    return [t for t in tokens if t not in stop and len(t) > 2]


def expand_queries(topic: str, *, max_queries: int = 8) -> List[str]:
    """
    Topic-agnostic deterministic query expansion.

    Goals:
    - Keep the original topic
    - Generate a small set of diverse, search-friendly variants
    - Avoid hardcoding to a single domain (e.g., fall detection)
    """
    cleaned_topic = " ".join((topic or "").split()).strip()
    kws = _keywords(cleaned_topic)
    base = " ".join(kws[:12]) if kws else cleaned_topic

    queries: List[str] = []
    if cleaned_topic:
        queries.append(cleaned_topic)

    # Generic research-intent variants
    if base:
        queries.extend(
            [
                f"{base} recent papers",
                f"{base} survey review",
                f"{base} benchmark dataset",
                f"{base} evaluation metrics",
                f"{base} limitations",
                f"{base} state of the art",
                f"{base} method approach",
            ]
        )

    # Light expansions based on detected cues (still generic)
    t = cleaned_topic.lower()
    if any(x in t for x in ["privacy", "private", "anonym", "federated", "encrypted"]):
        queries.append(f"{base} privacy-preserving")
    if any(x in t for x in ["edge", "on-device", "mobile", "embedded", "iot", "real-time", "realtime"]):
        queries.append(f"{base} edge deployment latency")
    if any(x in t for x in ["vision", "image", "video", "camera", "cv"]):
        queries.append(f"{base} computer vision")
    if any(x in t for x in ["nlp", "language", "text", "llm", "transformer"]):
        queries.append(f"{base} natural language processing")

    # De-dup while preserving order
    seen = set()
    out: List[str] = []
    for q in queries:
        qn = " ".join(q.split())
        if not qn:
            continue
        key = qn.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(qn)
        if len(out) >= max_queries:
            break
    return out
