"""Tests for the schema mapper — type inference and auto-mapping to Pydantic models."""
import csv
import tempfile
from pathlib import Path

import pytest

from src.pipeline.schema_mapper import infer_schema, auto_map_and_load, InferredType


class TestTypeInference:
    def test_infer_site_database(self, data_dir):
        result = infer_schema(data_dir / "site_database.csv")
        assert result.row_count == 75
        assert result.matched_model == "SiteRecord"
        col_names = [c.name for c in result.columns]
        assert "cell_id" in col_names
        assert "latitude" in col_names

    def test_infer_neighbor_relations(self, data_dir):
        result = infer_schema(data_dir / "neighbor_relations.csv")
        assert result.matched_model == "NeighborRelation"

    def test_infer_pm_data(self, data_dir):
        result = infer_schema(data_dir / "pm_data_april2026.csv")
        assert result.matched_model == "PMRecord"
        assert result.row_count == 216000

    def test_infer_cluster_kpi(self, data_dir):
        result = infer_schema(data_dir / "cluster_kpi_summary.csv")
        assert result.matched_model == "ClusterKPISummary"

    def test_column_types_detected(self, data_dir):
        result = infer_schema(data_dir / "site_database.csv")
        type_map = {c.name: c.inferred_type for c in result.columns}
        assert type_map["cell_id"] == InferredType.STRING
        assert type_map["sector"] == InferredType.INTEGER
        assert type_map["latitude"] == InferredType.FLOAT


class TestAutoMapAndLoad:
    def test_load_site_database(self, data_dir):
        model_name, records = auto_map_and_load(data_dir / "site_database.csv")
        assert model_name == "SiteRecord"
        assert len(records) == 75

    def test_load_neighbor_relations(self, data_dir):
        model_name, records = auto_map_and_load(data_dir / "neighbor_relations.csv")
        assert model_name == "NeighborRelation"
        assert len(records) > 700

    def test_load_cluster_kpi(self, data_dir):
        model_name, records = auto_map_and_load(data_dir / "cluster_kpi_summary.csv")
        assert model_name == "ClusterKPISummary"
        assert len(records) == 75

    def test_unknown_csv_raises(self, tmp_path):
        csv_path = tmp_path / "random.csv"
        with open(csv_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["foo", "bar", "baz"])
            w.writerow([1, 2, 3])
        with pytest.raises(ValueError, match="Could not match"):
            auto_map_and_load(csv_path)
