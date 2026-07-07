"""GET /api/v1/czml -- synthetic mobility -> CZML, disk-cached by params."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from backend.app.main import require_token
from backend.app.paths import CACHE_DIR, DATA_DIR
from scripts.generate_mobility_traces import generate
from src.exporters.czml import build_czml

router = APIRouter(prefix="/api/v1", tags=["czml"])

MAX_N_UES = 500
MAX_SEED = 1_000_000
MAX_DURATION_S = 600


def _cache_path(n_ues: int, seed: int, duration_s: int) -> Path:
    return CACHE_DIR / f"czml_{n_ues}_{seed}_{duration_s}.json"


@router.get("/czml")
async def get_czml(
    response: Response,
    n_ues: int = Query(default=21, ge=1),
    seed: int = Query(default=42, ge=0),
    duration_s: int = Query(default=240, ge=1),
    _: None = Depends(require_token),
) -> list[dict]:
    if n_ues > MAX_N_UES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            f"n_ues must be <= {MAX_N_UES}")
    if seed > MAX_SEED:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            f"seed must be <= {MAX_SEED}")
    if duration_s > MAX_DURATION_S:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            f"duration_s must be <= {MAX_DURATION_S}")

    cache_file = _cache_path(n_ues, seed, duration_s)
    if cache_file.exists():
        response.headers["X-Cache"] = "HIT"
        return json.loads(cache_file.read_text())

    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp)
        generate(DATA_DIR, out_dir, n_ues=n_ues, duration_s=duration_s, seed=seed)
        doc = build_czml(out_dir / "mobility_traces.csv", DATA_DIR / "site_database.csv")

    cache_file.write_text(json.dumps(doc))
    response.headers["X-Cache"] = "MISS"
    return doc
