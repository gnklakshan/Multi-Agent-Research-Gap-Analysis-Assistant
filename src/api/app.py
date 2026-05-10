from __future__ import annotations

import threading
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from ..main import run as run_pipeline
from ..config import OUTPUT_DIR


app = FastAPI(title="Citation-Grounded Research Gap Analysis Assistant")

RUNS: Dict[str, Dict[str, Any]] = {}


class RunRequest(BaseModel):
    topic: str = Field(min_length=3)
    max_papers: int = Field(default=10, ge=1, le=50)


@app.post("/research/run")
def start_run(req: RunRequest) -> Dict[str, Any]:
    run_id = str(uuid.uuid4())
    RUNS[run_id] = {"status": "running", "topic": req.topic, "max_papers": req.max_papers, "final_report": None, "error": None}

    def _worker():
        try:
            report_path = run_pipeline(req.topic, max_papers=req.max_papers, output_dir=OUTPUT_DIR)
            RUNS[run_id]["status"] = "completed"
            RUNS[run_id]["final_report"] = report_path
        except Exception as e:
            RUNS[run_id]["status"] = "failed"
            RUNS[run_id]["error"] = f"{type(e).__name__}: {e}"

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    return {"run_id": run_id}


@app.get("/research/{run_id}/status")
def get_status(run_id: str) -> Dict[str, Any]:
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail="run_id not found")
    return RUNS[run_id]


@app.get("/research/{run_id}/outputs")
def get_outputs(run_id: str) -> Dict[str, Any]:
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail="run_id not found")
    report = RUNS[run_id].get("final_report")
    if not report:
        return {"available": False, "reason": "run not completed"}
    p = Path(report)
    if not p.exists():
        return {"available": False, "reason": "report path missing on disk"}
    return {"available": True, "final_report": p.read_text(encoding="utf-8")}
