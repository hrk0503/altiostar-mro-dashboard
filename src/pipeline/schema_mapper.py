from __future__ import annotations

import difflib
from dataclasses import dataclass, field
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


# ── Drop-in mapping (Sprint 01, Epic 2) — synonym/alias + fuzzy match ─────────
# Canonical column -> accepted aliases. Lets an operator's renamed CSV map to our
# schema WITHOUT code changes (Soumyadeep Q9). Never silently drops: unmapped
# columns are reported so a human can map them.
_CANON_ALIASES: dict[str, set[str]] = {
    "source_cell_id": {"source_cell_id", "src_cell", "src_cell_id", "source_cell", "src", "serving_cell"},
    "target_cell_id": {"target_cell_id", "tgt_cell", "tgt_cell_id", "target_cell", "tgt", "neighbor_cell"},
    "cio_db": {"cio_db", "cio", "cell_individual_offset_db", "individual_offset", "qoffset"},
    "ho_attempts": {"ho_attempts", "handover_attempts", "attempts", "ho_att"},
    "ho_successes": {"ho_successes", "ho_success", "handover_success", "successes", "ho_succ"},
    "ho_failures": {"ho_failures", "ho_fail", "failures", "ho_failure"},
    "too_early_ho": {"too_early_ho", "too_early", "early_ho", "tooearly"},
    "too_late_ho": {"too_late_ho", "too_late", "late_ho", "toolate"},
    "wrong_cell": {"wrong_cell", "wrong_target", "wrongcell"},
    "correct_cell": {"correct_cell", "correct_target"},
    "ping_pong": {"ping_pong", "pingpong", "pp"},
    "cell_id": {"cell_id", "cellid", "cell"},
    "timestamp_utc": {"timestamp_utc", "timestamp", "time_utc", "rop_time"},
    "avg_rsrp_dBm": {"avg_rsrp_dbm", "rsrp", "avg_rsrp"},
    "azimuth_deg": {"azimuth_deg", "azimuth", "az"},
}


def _norm(name: str) -> str:
    return name.strip().lower().replace(" ", "_").replace("-", "_")


_REVERSE = {_norm(a): canon for canon, al in _CANON_ALIASES.items() for a in al | {canon}}
_ALL_ALIASES = list(_REVERSE.keys())


@dataclass
class ColumnMapping:
    rename: dict[str, str] = field(default_factory=dict)   # original -> canonical
    unmapped: list[str] = field(default_factory=list)      # need human mapping
    fuzzy: dict[str, str] = field(default_factory=dict)    # original -> canonical (low confidence)


def map_columns(columns: list[str], fuzzy_cutoff: float = 0.86) -> ColumnMapping:
    """Map incoming column names to canonical names via alias then fuzzy match."""
    m = ColumnMapping()
    for col in columns:
        key = _norm(col)
        if key in _REVERSE:
            canon = _REVERSE[key]
            if _norm(canon) != key or col != canon:
                m.rename[col] = canon
            continue
        near = difflib.get_close_matches(key, _ALL_ALIASES, n=1, cutoff=fuzzy_cutoff)
        if near:
            canon = _REVERSE[near[0]]
            m.rename[col] = canon
            m.fuzzy[col] = canon
        else:
            m.unmapped.append(col)
    return m


def infer_schema_flex(csv_path: Path) -> tuple[SchemaMatch, ColumnMapping]:
    """Alias-aware schema inference. Returns (match, mapping). Apply mapping.rename
    to the dataframe before validation; surface mapping.unmapped to the user."""
    df = pd.read_csv(csv_path, nrows=1)
    mapping = map_columns(list(df.columns))
    canon_cols = {mapping.rename.get(c, c) for c in df.columns}
    for model_name, signature in _SIGNATURES.items():
        if signature.issubset(canon_cols):
            return SchemaMatch(model_name, KNOWN_SCHEMAS[model_name]), mapping
    return SchemaMatch(None, None), mapping
