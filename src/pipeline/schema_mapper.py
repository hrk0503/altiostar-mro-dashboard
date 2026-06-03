from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.pipeline.models import (
    ClusterKPISummary,
    NeighborRelation,
    PMRecord,
    RelationPMRecord,
    SiteRecord,
)


def infer_column_types(df: pd.DataFrame) -> dict[str, str]:
    # Note: nullable int columns are upcast to float64 by pandas.
    # This means int columns with NaN values will be inferred as "float".
    """
    Auto-infer column types from a CSV dataframe.
    Returns a dict of column_name -> inferred_type
    """
    type_map = {}
    for col in df.columns:
        dtype = df[col].dtype
        if dtype == "int64":
            type_map[col] = "int"
        elif dtype == "float64":
            type_map[col] = "float"
        elif dtype == "bool":
            type_map[col] = "bool"
        else:
            type_map[col] = "str"
    return type_map


def map_to_schema(inferred: dict[str, str], schema_fields: dict[str, str]) -> dict[str, str]:
    matched = {}
    for field, expected_type in schema_fields.items():
        if field not in inferred:
            matched[field] = "MISSING"
        elif inferred[field] != expected_type:
            got = inferred[field]
            matched[field] = f"TYPE_MISMATCH (expected {expected_type}, got {got})"
        else:
            matched[field] = inferred[field]
    return matched


def run_schema_mapper(csv_path: Path, schema_fields: dict[str, str]) -> dict[str, str]:
    df = pd.read_csv(csv_path)
    inferred = infer_column_types(df)
    mapped = map_to_schema(inferred, schema_fields)
    return mapped



_SIGNATURES: dict[str, set[str]] = {
    "SiteRecord": {"cell_id", "enodeb_id", "sector", "azimuth_deg", "antenna_height_m"},
    "NeighborRelation": {"serving_cell", "neighbor_cell", "cell_individual_offset_dB"},
    "PMRecord": {"cell_id", "timestamp_utc", "ho_attempts_intra", "ho_success_intra", "avg_rsrp_dBm"},
    "RelationPMRecord": {"source_cell_id", "target_cell_id", "too_early_ho", "wrong_cell", "cio_db"},
    "ClusterKPISummary": {"cell_id", "ho_failure_rate_pct", "problem_cell", "total_ho_attempts"},
}

KNOWN_SCHEMAS = {
    "SiteRecord": SiteRecord,
    "NeighborRelation": NeighborRelation,
    "PMRecord": PMRecord,
    "RelationPMRecord": RelationPMRecord,
    "ClusterKPISummary": ClusterKPISummary,
}

@dataclass
class SchemaMatch:
    matched_model: str | None
    model_class: type | None

def infer_schema(csv_path: Path) -> SchemaMatch:
    df = pd.read_csv(csv_path, nrows=1)
    cols = set(df.columns)
    for model_name, signature in _SIGNATURES.items():
        if signature.issubset(cols):
            return SchemaMatch(matched_model=model_name, model_class=KNOWN_SCHEMAS[model_name])
    return SchemaMatch(matched_model=None, model_class=None)
