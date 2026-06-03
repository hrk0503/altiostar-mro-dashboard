"""Pipeline Agent — Data Engineer.

Auto-detects CSV schema, maps to internal format, normalizes to Parquet.
Outputs: normalized Parquet, data quality report, schema mapping.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd
from pydantic import BaseModel


class SchemaMapping(BaseModel):
    source_column: str
    target_field: str
    dtype: str
    transform: Optional[str] = None


class DataQualityReport(BaseModel):
    total_rows: int
    valid_rows: int
    null_counts: dict[str, int]
    type_mismatches: list[str]
    warnings: list[str]


class PipelineAgent:
    """Ingests operator CSV data, auto-maps schema, validates, normalizes."""

    def infer_schema(self, csv_path: Path) -> list[SchemaMapping]:
        """Auto-detect CSV column types and map to internal schema."""
        raise NotImplementedError

    def validate(self, df: pd.DataFrame) -> DataQualityReport:
        """Run data quality checks on ingested data."""
        raise NotImplementedError

    def normalize(self, csv_path: Path, output_path: Path) -> Path:
        """Full pipeline: infer → validate → normalize → write Parquet."""
        raise NotImplementedError
