"""Tests for Parquet export functionality."""
import pyarrow.parquet as pq
import pytest

from src.pipeline.loader import (
    export_all_parquet,
    export_cluster_kpi_parquet,
    export_neighbors_parquet,
    export_pm_data_parquet,
    export_sites_parquet,
)


@pytest.fixture
def out_dir(tmp_path):
    """Temporary output directory for parquet files."""
    return tmp_path / "processed"


class TestSitesParquet:
    def test_creates_file(self, data_dir, out_dir):
        path = export_sites_parquet(data_dir, out_dir)
        assert path.exists()
        assert path.suffix == ".parquet"

    def test_row_count(self, data_dir, out_dir):
        path = export_sites_parquet(data_dir, out_dir)
        table = pq.read_table(path)
        assert len(table) == 75

    def test_has_key_columns(self, data_dir, out_dir):
        path = export_sites_parquet(data_dir, out_dir)
        table = pq.read_table(path)
        cols = table.column_names
        assert "cell_id" in cols
        assert "latitude" in cols
        assert "frequency_band" in cols


class TestNeighborsParquet:
    def test_creates_file(self, data_dir, out_dir):
        path = export_neighbors_parquet(data_dir, out_dir)
        assert path.exists()

    def test_row_count(self, data_dir, out_dir):
        path = export_neighbors_parquet(data_dir, out_dir)
        table = pq.read_table(path)
        assert len(table) == 763


class TestPMDataParquet:
    def test_creates_file(self, data_dir, out_dir):
        path = export_pm_data_parquet(data_dir, out_dir)
        assert path.exists()

    def test_row_count(self, data_dir, out_dir):
        path = export_pm_data_parquet(data_dir, out_dir)
        table = pq.read_table(path)
        assert len(table) == 216000

    def test_timestamp_preserved(self, data_dir, out_dir):
        path = export_pm_data_parquet(data_dir, out_dir)
        table = pq.read_table(path)
        assert "timestamp_utc" in table.column_names


class TestClusterKPIParquet:
    def test_creates_file(self, data_dir, out_dir):
        path = export_cluster_kpi_parquet(data_dir, out_dir)
        assert path.exists()

    def test_row_count(self, data_dir, out_dir):
        path = export_cluster_kpi_parquet(data_dir, out_dir)
        table = pq.read_table(path)
        assert len(table) == 75


class TestExportAll:
    def test_exports_five_files(self, data_dir, out_dir):
        results = export_all_parquet(data_dir, out_dir)
        assert len(results) == 5
        for name, path in results.items():
            assert path.exists(), f"{name} not created"

    def test_missing_csv_raises(self, tmp_path, out_dir):
        with pytest.raises(FileNotFoundError):
            export_sites_parquet(tmp_path, out_dir)
