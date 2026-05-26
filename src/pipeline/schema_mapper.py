import pandas as pd
from typing import Dict

def infer_column_types(df: pd.DataFrame) -> Dict[str, str]:
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


def map_to_schema(inferred: Dict[str, str], schema_fields: Dict[str, str]) -> Dict[str, str]:
    """
    Maps inferred CSV columns to internal schema fields.
    Returns matched fields only.
    """
    matched = {}
    for field, expected_type in schema_fields.items():
        if field in inferred:
            matched[field] = inferred[field]
        else:
            matched[field] = "MISSING"
    return matched


def run_schema_mapper(csv_path: str, schema_fields: Dict[str, str]) -> Dict[str, str]:
    """
    Full pipeline: load CSV -> infer types -> map to schema.
    """
    df = pd.read_csv(csv_path)
    inferred = infer_column_types(df)
    mapped = map_to_schema(inferred, schema_fields)
    return mapped
