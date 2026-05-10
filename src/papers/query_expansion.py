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
    Deterministic query expansion:
    - Keeps original topic
    - Adds domain synonyms and common sub-phrases
    """
    kws = _keywords(topic)
    base = " ".join(kws[:10]) if kws else topic

    privacy_terms = [
        "privacy-preserving",
        "privacy",
        "anonymized",
        "de-identification",
        "on-device",
        "federated",
    ]
    vision_terms = [
        "computer vision",
        "vision-based",
        "pose estimation",
        "skeleton-based",
        "keypoint-based",
        "optical flow",
        "RGB-D",
        "depth camera",
    ]
    eval_terms = ["edge AI", "real-time", "lightweight", "latency", "resource-constrained", "mobile inference"]

    queries: List[str] = []
    queries.append(topic.strip())

    # Common expansions for assistive-care fall detection topics
    queries.append(f"{base} privacy-preserving fall detection computer vision")
    queries.append(f"{base} skeleton-based fall detection elderly care")
    queries.append(f"{base} pose estimation fall detection elderly")
    queries.append(f"{base} optical flow fall detection")
    queries.append(f"{base} lightweight fall detection edge AI")
    queries.append(f"{base} RGB-D fall detection deep learning")
    queries.append(f"{base} vision-based fall detection privacy")
    queries.append(f"{base} human activity recognition fall detection elderly")

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
