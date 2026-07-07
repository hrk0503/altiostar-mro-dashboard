"""Shared filesystem locations for the backend app.

NOTE (honest, P3): single-tenant filesystem layout. No tenant_id partitioning
yet -- every uploaded dataset and job result lives in one flat namespace keyed
by uuid. Multi-tenant isolation (per-tenant dirs/DB rows + auth scoping) is a
Phase 3 item, not implemented here.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data" / "synthetic"

CACHE_DIR = REPO_ROOT / "data" / "cache" / "czml"
UPLOADS_DIR = REPO_ROOT / "data" / "uploads"
RESULTS_DIR = REPO_ROOT / "data" / "results"

for _d in (CACHE_DIR, UPLOADS_DIR, RESULTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

TENANCY_NOTE = "single (P3)"
