"""AltioStar MRO API Gateway — backend scaffold.

SECURITY / HONESTY NOTES (see docs/METHODOLOGY.md, docs/COUNTERFACTUAL.md):
- Endpoints not yet wired to a real model return HTTP 501 (Not Implemented).
  They MUST NOT fabricate KPIs (no hardcoded 99.99).
- Every non-public route requires a bearer token (WINNIIO_API_TOKEN); the API
  fails closed if the token is unset.
- CORS is an explicit allowlist (WINNIIO_ALLOWED_ORIGINS), never "*".
This is a minimal scaffold gate; production needs a real IdP/JWT + rate limiting.
"""
from __future__ import annotations

import os

from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="AltioStar MRO API Gateway",
    description="Backend for MRO CIO-optimization inference and pipeline orchestration.",
    version="0.1.0",
)

_ALLOWED_ORIGINS = [
    o.strip() for o in os.environ.get(
        "WINNIIO_ALLOWED_ORIGINS", "http://localhost:8501",
    ).split(",") if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,     # explicit allowlist, never "*"
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


def require_token(authorization: str = Header(default="")) -> None:
    """Minimal bearer-token gate. Fails closed if WINNIIO_API_TOKEN is unset."""
    expected = os.environ.get("WINNIIO_API_TOKEN")
    if not expected:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            "API auth not configured (WINNIIO_API_TOKEN unset)")
    if authorization.removeprefix("Bearer ").strip() != expected:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or missing token")


class InferRequest(BaseModel):
    cell_id: str
    scenario: str = "baseline"


@app.get("/")
def read_root() -> dict:
    return {"status": "healthy", "service": "altiostar-mro-backend", "version": app.version}


@app.post("/api/v1/infer")
async def infer(request: InferRequest, _: None = Depends(require_token)) -> dict:
    """Run CIO-optimization inference. NOT YET WIRED — returns 501, never a fake KPI."""
    raise HTTPException(
        status.HTTP_501_NOT_IMPLEMENTED,
        "inference not implemented: model wiring pending real-data validation",
    )


@app.post("/api/v1/retrain")
async def retrain(scenario: str, _: None = Depends(require_token)) -> dict:
    """Trigger a retraining run. NOT YET IMPLEMENTED (501, no fake job id)."""
    raise HTTPException(
        status.HTTP_501_NOT_IMPLEMENTED,
        "retrain not implemented: training orchestration pending",
    )


@app.websocket("/api/v1/ws/noc-copilot")
async def websocket_noc_copilot(websocket: WebSocket) -> None:
    """NOC copilot socket — honest stub, token-gated."""
    expected = os.environ.get("WINNIIO_API_TOKEN")
    if not expected or websocket.query_params.get("token") != expected:
        await websocket.close(code=1008)  # policy violation
        return
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({
                "status": "not_implemented",
                "echo": data,
                "note": "NOC copilot is a scaffold; no model is wired yet.",
            })
    except Exception:
        await websocket.close()
