"""POST /api/v1/simulate + GET /api/v1/jobs/{id} -- counterfactual CIO loop.

Runs the full WINNIIO<->RF loop synchronously, in-process, for providers that
support it (today: "synthetic" only). "blaretech" is an honest 501 -- see
backend/app/rf/blaretech.py for the documented file-handoff contract that
still needs to be built.
"""
from __future__ import annotations

import json
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.app.main import require_token
from backend.app.paths import DATA_DIR, RESULTS_DIR
from backend.app.rf.blaretech import BlaretechRFProvider
from backend.app.rf.provider import RFProvider
from backend.app.rf.synthetic import SyntheticRFProvider
from src.integration.blaretech_export import build_export
from src.integration.counterfactual_loop import (
    current_from_request,
    ingest_counterfactuals,
    optimize,
)

router = APIRouter(prefix="/api/v1", tags=["simulate"])

NOT_A_PERFORMANCE_CLAIM = "NOT_A_PERFORMANCE_CLAIM — synthetic counterfactuals"

_PROVIDERS: dict[str, RFProvider] = {
    "synthetic": SyntheticRFProvider(),
    "blaretech": BlaretechRFProvider(),
}


class SimulateRequest(BaseModel):
    rf_provider: str = "synthetic"


@router.post("/simulate")
async def simulate(
    request: SimulateRequest,
    _: None = Depends(require_token),
) -> dict:
    provider = _PROVIDERS.get(request.rf_provider)
    if provider is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            f"unknown rf_provider '{request.rf_provider}'")

    if request.rf_provider == "blaretech":
        try:
            with tempfile.TemporaryDirectory() as tmp:
                provider.simulate(Path(tmp))
        except NotImplementedError as exc:
            raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, str(exc)) from exc

    job_id = str(uuid.uuid4())
    with tempfile.TemporaryDirectory() as tmp:
        req_dir = Path(tmp)
        build_export(DATA_DIR, req_dir)
        return_csv = provider.simulate(req_dir)

        space = ingest_counterfactuals(return_csv)
        current = current_from_request(req_dir / "01_counterfactual_request.csv")
        df = optimize(space, current)

    results_csv = RESULTS_DIR / f"{job_id}.csv"
    df.to_csv(results_csv, index=False)

    summary = {
        "relations": int(len(df)),
        "avg_before": round(float(df["before_success_%"].mean()), 2) if len(df) else None,
        "avg_after": round(float(df["after_success_%"].mean()), 2) if len(df) else None,
        "banner": NOT_A_PERFORMANCE_CLAIM,
    }
    manifest = {"job_id": job_id, "status": "done", "rf_provider": request.rf_provider,
               "summary": summary, "results_csv": str(results_csv)}
    (RESULTS_DIR / f"{job_id}.json").write_text(json.dumps(manifest, indent=2))

    return {"job_id": job_id, "status": "done", "summary": summary}


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, _: None = Depends(require_token)) -> dict:
    manifest_path = RESULTS_DIR / f"{job_id}.json"
    if not manifest_path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"job '{job_id}' not found")
    return json.loads(manifest_path.read_text())
