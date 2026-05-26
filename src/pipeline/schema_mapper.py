"""Schema mapper: infer CSV column types and auto-map to known Pydantic schemas."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Type

import pandas as pd
from pydantic import BaseModel

from src.pipeline.models import (
    SiteRecord,
    NeighborRelation,
    PMRecord,
    ClusterKPISummary,
)


class InferredType(str, Enum):
    INTEGER = "integer"
    FLOAT = "float"
    STRING = "string"
    BOOLEAN = "boolean"
    DATETIME = "datetime"


@dataclass
class ColumnProfile:
    name: str
    inferred_type: InferredType
    null_pct: float
    unique_count: int
    sample_values: list


@dataclass
class SchemaInferenceResult:
    columns: list[ColumnProfile]
    row_count: int
    matched_model: str | None = None
    field_mapping: dict[str, str] | None = None
    unmapped_csv_cols: list[str] | None = None
    unmapped_model_fields: list[str] | None = None


KNOWN_SCHEMAS: dict[str, Type[BaseModel]] = {
    "SiteRecord": SiteRecord,
    "NeighborRelation": NeighborRelation,
    "PMRecord": PMRecord,
    "ClusterKPISummary": ClusterKPISummary,
}

# Signature columns that identify each schema
_SIGNATURES: dict[str, set[str]] = {
    "SiteRecord": {"cell_id", "site_id", "sector", "azimuth", "tx_power_dbm"},
    "NeighborRelation": {"source_cell", "target_cell", "cio_db"},
    "PMRecord": {"cell_id", "timestamp", "ho_attempt", "ho_success", "rsrp_dbm"},
    "ClusterKPISummary": {"cell_id", "monthly_ho_success_rate", "problem_flag"},
}


def infer_column_type(series: pd.Series) -> InferredType:
    """Infer the semantic type of a pandas Series."""
    if series.dtype == bool or set(series.dropna().unique()) <= {True, False, 0, 1, "True", "False", "true", "false"}:
        if series.dtype == bool:
            return InferredType.BOOLEAN

    if pd.api.types.is_integer_dtype(series):
        return InferredType.INTEGER

    if pd.api.types.is_float_dtype(series):
        return InferredType.FLOAT

    str_series = series.dropna().astype(str)
    if len(str_series) > 0:
        try:
            pd.to_datetime(str_series.head(20))
            return InferredType.DATETIME
        except (ValueError, TypeError):
            pass

        try:
            pd.to_numeric(str_series)
            if str_series.str.contains(r"\.").any():
                return InferredType.FLOAT
            return InferredType.INTEGER
        except (ValueError, TypeError):
            pass

    return InferredType.STRING


def infer_schema(path: Path, *, sample_rows: int = 1000) -> SchemaInferenceResult:
    """Infer column types from a CSV and attempt to match to a known Pydantic model."""
    df = pd.read_csv(path, nrows=sample_rows)
    total_rows = sum(1 for _ in open(path)) - 1  # exclude header

    columns = []
    for col in df.columns:
        profile = ColumnProfile(
            name=col,
            inferred_type=infer_column_type(df[col]),
            null_pct=round(float(df[col].isnull().mean()) * 100, 2),
            unique_count=int(df[col].nunique()),
            sample_values=df[col].dropna().head(3).tolist(),
        )
        columns.append(profile)

    result = SchemaInferenceResult(columns=columns, row_count=total_rows)

    csv_cols = {c.lower().replace(" ", "_") for c in df.columns}
    best_match = None
    best_score = 0

    for model_name, signature in _SIGNATURES.items():
        overlap = len(signature & csv_cols)
        score = overlap / len(signature)
        if score > best_score:
            best_score = score
            best_match = model_name

    if best_match and best_score >= 0.6:
        result.matched_model = best_match
        model_cls = KNOWN_SCHEMAS[best_match]
        model_fields = set(model_cls.model_fields.keys())

        mapping = {}
        for csv_col in df.columns:
            normalized = csv_col.lower().replace(" ", "_")
            if normalized in model_fields:
                mapping[csv_col] = normalized

        result.field_mapping = mapping
        result.unmapped_csv_cols = [c for c in df.columns if c not in mapping]
        result.unmapped_model_fields = [f for f in model_fields if f not in mapping.values()]

    return result


def auto_map_and_load(path: Path) -> tuple[str, list[BaseModel]]:
    """Infer schema, map columns, and load data into the matched Pydantic model."""
    inference = infer_schema(path)

    if not inference.matched_model:
        raise ValueError(
            f"Could not match {path.name} to any known schema. "
            f"Columns: {[c.name for c in inference.columns]}"
        )

    model_cls = KNOWN_SCHEMAS[inference.matched_model]
    df = pd.read_csv(path)

    if inference.field_mapping:
        rename_map = {k: v for k, v in inference.field_mapping.items() if k != v}
        if rename_map:
            df = df.rename(columns=rename_map)

    records = [model_cls.model_validate(row) for row in df.to_dict(orient="records")]
    return inference.matched_model, records
