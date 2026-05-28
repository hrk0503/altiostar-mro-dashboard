"""Load CSVs into typed Pydantic models with chunked reading.

Also exports validated data to Parquet via pyarrow for
downstream consumption (e.g. Gymnasium RL environment).
"""
from __future__ import annotations

from pathlib import Path
from typing import TypeVar

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import BaseModel

from src.pipeline.models import (
    ClusterKPISummary,
    NeighborRelation,
    PMRecord,
    SiteRecord,
)

T = TypeVar("T", bound=BaseModel)
DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "synthetic"
PROCESSED_DIR = DATA_DIR / "processed"


def _load_csv(path: Path, model: type[T], *, chunk_size: int | None = None) -> list[T]:
    """Load a CSV into a list of Pydantic models."""
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
    """Load pm_data as DataFrame — preferred for performance.

    Use this instead of load_pm_data() for large datasets;
    avoids creating 216K Pydantic instances.
    """
    p = path or DATA_DIR / "pm_data_april2026.csv"
    if not p.exists():
        raise FileNotFoundError(f"CSV not found: {p}")
    return pd.read_csv(p, parse_dates=["timestamp_utc"])


# ── Parquet export ──────────────────────────────────────

def _csv_to_parquet(
    csv_name: str,
    data_dir: Path | None = None,
    out_dir: Path | None = None,
) -> Path:
    """Read a CSV, validate with pandas, export as Parquet.

    Returns the path to the written .parquet file.
    """
    src = (data_dir or DATA_DIR) / csv_name
    if not src.exists():
        raise FileNotFoundError(f"CSV not found: {src}")

    dest_dir = out_dir or PROCESSED_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)

    parquet_name = csv_name.replace(".csv", ".parquet")
    dest = dest_dir / parquet_name

    df = pd.read_csv(src)
    if "timestamp_utc" in df.columns:
        df["timestamp_utc"] = pd.to_datetime(
            df["timestamp_utc"]
        )

    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(table, dest, compression="snappy")
    return dest


def export_sites_parquet(
    data_dir: Path | None = None,
    out_dir: Path | None = None,
) -> Path:
    """Export site_database.csv → .parquet."""
    return _csv_to_parquet(
        "site_database.csv", data_dir, out_dir,
    )


def export_neighbors_parquet(
    data_dir: Path | None = None,
    out_dir: Path | None = None,
) -> Path:
    """Export neighbor_relations.csv → .parquet."""
    return _csv_to_parquet(
        "neighbor_relations.csv", data_dir, out_dir,
    )


def export_pm_data_parquet(
    data_dir: Path | None = None,
    out_dir: Path | None = None,
) -> Path:
    """Export pm_data_april2026.csv → .parquet."""
    return _csv_to_parquet(
        "pm_data_april2026.csv", data_dir, out_dir,
    )


def export_cluster_kpi_parquet(
    data_dir: Path | None = None,
    out_dir: Path | None = None,
) -> Path:
    """Export cluster_kpi_summary.csv → .parquet."""
    return _csv_to_parquet(
        "cluster_kpi_summary.csv", data_dir, out_dir,
    )


def export_all_parquet(
    data_dir: Path | None = None,
    out_dir: Path | None = None,
) -> dict[str, Path]:
    """Export all 4 CSVs to Parquet. Returns {name: path}."""
    exporters = {
        "site_database": export_sites_parquet,
        "neighbor_relations": export_neighbors_parquet,
        "pm_data": export_pm_data_parquet,
        "cluster_kpi": export_cluster_kpi_parquet,
    }
    results: dict[str, Path] = {}
    for name, fn in exporters.items():
        results[name] = fn(data_dir, out_dir)
    return results
