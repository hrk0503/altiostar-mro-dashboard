"""Schema Mapper — auto-detects CSV column types and maps to internal schema.

Core Phase 0 deliverable. Must handle unknown CSV formats from any operator.
"""

from pathlib import Path

import pandas as pd

from src.models.cell_data import CellSite, NeighborRelation, PMRecord


def infer_csv_schema(csv_path: Path) -> dict[str, str]:
    """Read CSV header + sample rows, infer column types."""
    df = pd.read_csv(csv_path, nrows=100)
    return {col: str(dtype) for col, dtype in df.dtypes.items()}


def load_site_database(csv_path: Path) -> list[CellSite]:
    """Load and validate site database CSV into typed models."""
    df = pd.read_csv(csv_path)
    return [CellSite(**row) for row in df.to_dict(orient="records")]


def load_neighbor_relations(csv_path: Path) -> list[NeighborRelation]:
    """Load and validate neighbor relations CSV."""
    df = pd.read_csv(csv_path)
    return [NeighborRelation(**row) for row in df.to_dict(orient="records")]


def load_pm_data(csv_path: Path) -> list[PMRecord]:
    """Load and validate PM data CSV."""
    df = pd.read_csv(csv_path)
    return [PMRecord(**row) for row in df.to_dict(orient="records")]
