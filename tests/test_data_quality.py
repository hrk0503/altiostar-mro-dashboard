"""Data quality tests — validate the actual synthetic CSVs pass all quality checks."""
import pandas as pd

from src.pipeline.validator import validate_all, validate_csv


class TestSiteDatabaseQuality:
    def test_no_nulls(self, data_dir):
        result = validate_csv("site_database.csv", data_dir / "site_database.csv")
        assert result.null_counts == {}, f"Unexpected nulls: {result.null_counts}"

    def test_75_rows(self, sites_df):
        assert len(sites_df) == 75, f"Expected 75 rows, got {len(sites_df)}"

    def test_25_unique_sites(self, sites_df):
        assert sites_df["site_id"].nunique() == 25

    def test_3_sectors_per_site(self, sites_df):
        for site, group in sites_df.groupby("site_id"):
            assert len(group) == 3, f"{site} has {len(group)} sectors, expected 3"

    def test_valid_bands(self, sites_df):
        assert set(sites_df["band"].unique()) <= {1, 3, 41}

    def test_coordinates_in_tokyo(self, sites_df):
        assert sites_df["latitude"].between(35.5, 35.8).all()
        assert sites_df["longitude"].between(139.5, 139.9).all()


class TestNeighborRelationsQuality:
    def test_no_nulls(self, data_dir):
        result = validate_csv("neighbor_relations.csv", data_dir / "neighbor_relations.csv")
        assert result.null_counts == {}

    def test_no_self_neighbors(self, neighbors_df):
        self_refs = neighbors_df[neighbors_df["source_cell"] == neighbors_df["target_cell"]]
        assert len(self_refs) == 0, f"Found {len(self_refs)} self-referencing neighbor entries"

    def test_reasonable_distances(self, neighbors_df):
        assert (neighbors_df["distance_km"] >= 0).all()
        assert (neighbors_df["distance_km"] < 50).all()

    def test_cio_in_range(self, neighbors_df):
        assert (neighbors_df["cio_db"].between(-15, 15)).all()

    def test_each_cell_has_neighbors(self, neighbors_df, sites_df):
        cells_with_neighbors = set(neighbors_df["source_cell"].unique())
        all_cells = set(sites_df["cell_id"].unique())
        missing = all_cells - cells_with_neighbors
        assert len(missing) == 0, f"Cells without neighbors: {missing}"


class TestPMDataQuality:
    def test_no_nulls_in_sample(self, data_dir):
        result = validate_csv("pm_data_april2026.csv", data_dir / "pm_data_april2026.csv")
        assert result.null_counts == {}

    def test_216k_rows(self, data_dir):
        df = pd.read_csv(data_dir / "pm_data_april2026.csv")
        assert len(df) == 216000, f"Expected 216000 rows, got {len(df)}"

    def test_ho_success_le_attempts(self, pm_data_df):
        violations = pm_data_df[pm_data_df["ho_success"] > pm_data_df["ho_attempt"]]
        assert len(violations) == 0, f"{len(violations)} rows where ho_success > ho_attempt"

    def test_kpi_ranges(self, pm_data_df):
        assert (pm_data_df["prb_utilization_pct"].between(0, 100)).all()
        assert (pm_data_df["rsrp_dbm"].between(-140, -40)).all()

    def test_75_unique_cells(self, data_dir):
        df = pd.read_csv(data_dir / "pm_data_april2026.csv", usecols=["cell_id"])
        assert df["cell_id"].nunique() == 75


class TestClusterKPIQuality:
    def test_no_nulls(self, data_dir):
        result = validate_csv("cluster_kpi_summary.csv", data_dir / "cluster_kpi_summary.csv")
        assert result.null_counts == {}

    def test_75_rows(self, cluster_kpi_df):
        assert len(cluster_kpi_df) == 75

    def test_has_problem_cells(self, cluster_kpi_df):
        problem_count = cluster_kpi_df["problem_flag"].sum()
        assert problem_count == 6, f"Expected 6 problem cells, got {problem_count}"

    def test_rates_sum_to_one(self, cluster_kpi_df):
        total = cluster_kpi_df["monthly_ho_success_rate"] + cluster_kpi_df["monthly_ho_failure_rate"]
        assert ((total - 1.0).abs() < 0.01).all(), "success_rate + failure_rate should ≈ 1.0"

    def test_problem_cells_have_high_failure(self, cluster_kpi_df):
        problems = cluster_kpi_df[cluster_kpi_df["problem_flag"]]
        assert (problems["monthly_ho_failure_rate"] > 0.04).all(), \
            "Problem cells should have >4% HO failure rate"


class TestFullValidation:
    def test_all_csvs_pass(self, data_dir):
        results = validate_all(data_dir)
        for name, result in results.items():
            assert result.passed, f"{name} failed validation: {result.range_violations}"
