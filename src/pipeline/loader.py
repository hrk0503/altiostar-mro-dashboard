"""Load CSV files into typed Pydantic models with performance handling for large files."""
from __future__ import annotations

from pathlib import Path
from typing import TypeVar, Type

import pandas as pd
from pydantic import BaseModel

from src.pipeline.models import (
    SiteRecord,
    NeighborRelation,
    PMRecord,
    ClusterKPISummary,
)

T = TypeVar("T", bound=BaseModel)
DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def _load_csv(path: Path, model: Type[T], *, chunk_size: int | None = None) -> list[T]:
    """Load a CSV into a list of Pydantic models. Uses chunked reading for large files."""
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")

    if chunk_size:
        records: list[T] = []
        for chunk in pd.read_csv(path, chunksize=chunk_size):
            for row in chunk.to_dict(orient="records"):
                records.append(model.model_validate(row))
        return records

    df = pd.read_csv(path)
    return [model.model_validate(row) for row in df.to_dict(orient="records")]


def load_sites(path: Path | None = None) -> list[SiteRecord]:
    """Load site_database.csv → list[SiteRecord] (75 rows)."""
    return _load_csv(path or DATA_DIR / "site_database.csv", SiteRecord)


def load_neighbors(path: Path | None = None) -> list[NeighborRelation]:
    """Load neighbor_relations.csv → list[NeighborRelation] (~763 rows)."""
    return _load_csv(path or DATA_DIR / "neighbor_relations.csv", NeighborRelation)


def load_pm_data(
    path: Path | None = None, *, chunk_size: int = 10_000
) -> list[PMRecord]:
    """Load pm_data_april2026.csv → list[PMRecord] (216K rows, chunked)."""
    return _load_csv(
        path or DATA_DIR / "pm_data_april2026.csv", PMRecord, chunk_size=chunk_size
    )


def load_cluster_kpi(path: Path | None = None) -> list[ClusterKPISummary]:
    """Load cluster_kpi_summary.csv → list[ClusterKPISummary] (75 rows)."""
    return _load_csv(path or DATA_DIR / "cluster_kpi_summary.csv", ClusterKPISummary)


def load_pm_data_df(path: Path | None = None) -> pd.DataFrame:
    """Load pm_data as a DataFrame for performance-sensitive operations."""
    p = path or DATA_DIR / "pm_data_april2026.csv"
    if not p.exists():
        raise FileNotFoundError(f"CSV not found: {p}")
    return pd.read_csv(p, parse_dates=["timestamp_utc"])
