"""Tests for schema mapper — type inference and column mapping."""
from __future__ import annotations
import pytest
from hypothesis import given
from hypothesis import strategies as st
import pandas as pd
from src.pipeline.loader import DATA_DIR
from src.pipeline.schema_mapper import infer_column_types, map_to_schema, run_schema_mapper


class TestInferColumnTypes:
    def test_returns_dict(self):
        df = pd.DataFrame({"cell_id": ["CELL_000_0"], "band": [1], "latitude": [35.6]})
        result = infer_column_types(df)
        assert isinstance(result, dict)

    def test_int_column(self):
        df = pd.DataFrame({"band": [1, 3, 41]})
        result = infer_column_types(df)
        assert result["band"] == "int"

    def test_float_column(self):
        df = pd.DataFrame({"latitude": [35.6, 35.7]})
        result = infer_column_types(df)
        assert result["latitude"] == "float"

    def test_str_column(self):
        df = pd.DataFrame({"cell_id": ["CELL_000_0", "CELL_001_0"]})
        result = infer_column_types(df)
        assert result["cell_id"] == "str"

    def test_bool_column(self):
        df = pd.DataFrame({"problem_flag": [True, False]})
        result = infer_column_types(df)
        assert result["problem_flag"] == "bool"

    def test_all_site_columns(self):
        df = pd.DataFrame({
            "cell_id": ["CELL_000_0"],
            "site_id": ["SITE_000"],
            "band": [1],
            "latitude": [35.6],
            "longitude": [139.7],
            "antenna_height_m": [30.0],
            "mechanical_tilt": [4.0],
            "tx_power_dbm": [43.0],
        })
        result = infer_column_types(df)
        assert result["band"] == "int"
        assert result["latitude"] == "float"
        assert result["cell_id"] == "str"


class TestMapToSchema:
    def test_all_fields_present(self):
        inferred = {"cell_id": "str", "band": "int", "latitude": "float"}
        schema = {"cell_id": "str", "band": "int", "latitude": "float"}
        result = map_to_schema(inferred, schema)
        assert "MISSING" not in result.values()

    def test_missing_field_flagged(self):
        inferred = {"cell_id": "str", "band": "int"}
        schema = {"cell_id": "str", "band": "int", "latitude": "float"}
        result = map_to_schema(inferred, schema)
        assert result["latitude"] == "MISSING"

    def test_returns_all_schema_keys(self):
        inferred = {"cell_id": "str", "band": "int"}
        schema = {"cell_id": "str", "band": "int", "latitude": "float"}
        result = map_to_schema(inferred, schema)
        assert set(result.keys()) == set(schema.keys())

    def test_extra_csv_columns_ignored(self):
        inferred = {"cell_id": "str", "band": "int", "extra_col": "str"}
        schema = {"cell_id": "str", "band": "int"}
        result = map_to_schema(inferred, schema)
        assert "extra_col" not in result

pytestmark = pytest.mark.skipif(
    not (DATA_DIR / "site_database.csv").exists(),
    reason="Real CSVs not available in CI"
)

class TestRunSchemaMapper:
    def test_runs_on_site_csv(self, data_dir):
        schema = {
            "cell_id": "str", "enodeb_id": "str", "frequency_band": "int",
            "latitude": "float", "longitude": "float"
        }
        result = run_schema_mapper(str(data_dir / "site_database.csv"), schema)
        assert "MISSING" not in result.values()

    def test_runs_on_neighbor_csv(self, data_dir):
        schema = {
            "serving_cell": "str", "neighbor_cell": "str",
            "cell_individual_offset_dB": "float", "distance_m": "float"
        }
        result = run_schema_mapper(str(data_dir / "neighbor_relations.csv"), schema)
        assert "MISSING" not in result.values()

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            run_schema_mapper(tmp_path / "nonexistent.csv", {"cell_id": "str"})

class TestSchemaMapperHypothesis:

    @given(st.dictionaries(
        keys=st.text(min_size=1, max_size=20),
        values=st.one_of(
            st.integers(),
            st.floats(allow_nan=False, allow_infinity=False),
            st.text(min_size=0, max_size=50),
            st.booleans()
        ),
        min_size=1,
        max_size=10
    ))
    def test_infer_always_returns_dict(self, data):
        df = pd.DataFrame([data])
        result = infer_column_types(df)
        assert isinstance(result, dict)

    @given(st.dictionaries(
        keys=st.text(min_size=1, max_size=20),
        values=st.one_of(
            st.integers(),
            st.floats(allow_nan=False, allow_infinity=False),
            st.text(min_size=0, max_size=50),
            st.booleans()
        ),
        min_size=1,
        max_size=10
    ))
    def test_infer_never_returns_unknown_type(self, data):
        df = pd.DataFrame([data])
        result = infer_column_types(df)
        valid_types = {"int", "float", "str", "bool"}
        for col, dtype in result.items():
            assert dtype in valid_types, f"Unknown type {dtype} for column {col}"

    @given(
        st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.just("str"),
            min_size=1,
            max_size=10
        )
    )
    def test_map_always_returns_all_schema_keys(self, schema):
        inferred = {k: "str" for k in schema.keys()}
        result = map_to_schema(inferred, schema)
        assert set(result.keys()) == set(schema.keys())

    @given(
        st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.just("str"),
            min_size=1,
            max_size=5
        )
    )
    def test_missing_columns_always_flagged(self, schema):
        result = map_to_schema({}, schema)
        for v in result.values():
            assert v == "MISSING"

