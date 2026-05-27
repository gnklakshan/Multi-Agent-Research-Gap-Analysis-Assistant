from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

import pandas as pd

from ..schemas.paper_summary import PaperSummary


def build_comparison_table(summaries: List[PaperSummary]) -> Tuple[str, List[Dict[str, Any]]]:
    rows: List[Dict[str, Any]] = []
    for s in summaries:
        rows.append(
            {
                "Paper": s.title,
                "Year": s.year or "n/a",
                "Method": s.proposed_method,
                "Input Type": s.input_type,
                "Dataset": ", ".join(s.datasets) if s.datasets else "not reported",
                "Metrics / Results": "; ".join(s.main_results) if s.main_results else "not reported",
                "Privacy Handling": "; ".join(s.privacy_notes) if s.privacy_notes else "not reported",
                "Edge Deployment": "; ".join(s.deployment_notes) if s.deployment_notes else "not reported",
                "Main Limitation": (s.author_limitations[0] if s.author_limitations else (s.inferred_limitations[0] if s.inferred_limitations else "not reported")),
                "Version Type": s.selected_version or "unknown",
            }
        )
    df = pd.DataFrame(rows)
    try:
        md = df.to_markdown(index=False)
    except ImportError:
        # Fallback when optional pandas markdown dependency is unavailable.
        md = df.to_string(index=False)
    return md, rows
