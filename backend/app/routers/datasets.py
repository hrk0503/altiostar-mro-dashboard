"""POST /api/v1/datasets -- CSV upload + fuzzy schema inference.

Single-tenant (see backend/app/paths.py TENANCY_NOTE): no tenant_id scoping
yet, every dataset lives in one flat data/uploads/ namespace keyed by uuid.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from backend.app.main import require_token
from backend.app.paths import TENANCY_NOTE, UPLOADS_DIR
from src.pipeline.schema_mapper import infer_schema_flex

router = APIRouter(prefix="/api/v1", tags=["datasets"])

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50MB
MAX_ROWS = 1_000_000
ALLOWED_EXTENSIONS = {".csv"}
ALLOWED_CONTENT_TYPES = {"text/csv", "application/vnd.ms-excel", "application/csv",
                          "text/plain", "application/octet-stream"}


@router.post("/datasets", status_code=status.HTTP_200_OK)
async def upload_dataset(
    file: UploadFile,
    _: None = Depends(require_token),
) -> dict:
    filename = file.filename or ""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            f"only {sorted(ALLOWED_EXTENSIONS)} files are accepted")
    if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            f"unsupported content-type '{file.content_type}'")

    # stream + size-cap read (never trust Content-Length alone)
    chunks: list[bytes] = []
    total = 0
    chunk_size = 1024 * 1024
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_UPLOAD_BYTES:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                                f"upload exceeds {MAX_UPLOAD_BYTES} byte cap")
        chunks.append(chunk)
    raw = b"".join(chunks)

    dataset_id = str(uuid.uuid4())
    dest = UPLOADS_DIR / f"{dataset_id}.csv"
    dest.write_bytes(raw)

    try:
        df = pd.read_csv(dest)
    except Exception as exc:
        dest.unlink(missing_ok=True)
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            f"file is not a parseable CSV: {exc}") from exc

    if len(df) > MAX_ROWS:
        dest.unlink(missing_ok=True)
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            f"row count {len(df)} exceeds cap {MAX_ROWS}")

    match, mapping = infer_schema_flex(dest)

    manifest = {
        "dataset_id": dataset_id,
        "original_name": filename,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "row_count": int(len(df)),
        "matched_model": match.matched_model,
        "tenancy": TENANCY_NOTE,
    }
    (UPLOADS_DIR / f"{dataset_id}.manifest.json").write_text(json.dumps(manifest, indent=2))

    result = {
        "dataset_id": dataset_id,
        "matched_model": match.matched_model,
        "rename_map": mapping.rename,
        "unmapped": mapping.unmapped,
        "fuzzy": mapping.fuzzy,
        "row_count": int(len(df)),
        "tenancy": TENANCY_NOTE,
    }

    if match.matched_model is None:
        dest.unlink(missing_ok=True)
        (UPLOADS_DIR / f"{dataset_id}.manifest.json").unlink(missing_ok=True)
        result["hint"] = (
            "no known schema (SiteRecord/NeighborRelation/PMRecord/"
            "RelationPMRecord/ClusterKPISummary) matched these columns even "
            "after alias/fuzzy mapping; rename the unmapped columns above "
            "or provide a mapping."
        )
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, result)

    return result
