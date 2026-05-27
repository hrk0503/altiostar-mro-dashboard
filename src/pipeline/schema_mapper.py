from __future__ import annotations
from pathlib import Path
import pandas as pd

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

