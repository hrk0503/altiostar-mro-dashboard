"""Data quality tests -- validate the official CSVs."""
import pandas as pd

from src.pipeline.validator import validate_csv, validate_all


class TestSiteDatabaseQuality:
    def test_no_nulls(self, data_dir):
        result = validate_csv(
            "site_database.csv",
            data_dir / "site_database.csv",
        )
        assert result.null_counts == {}, (
            f"Unexpected nulls: {result.null_counts}"
        )

    def test_75_rows(self, sites_df):
        assert len(sites_df) == 75, (
            f"Expected 75 rows, got {len(sites_df)}"
        )

    def test_25_unique_sites(self, sites_df):
        assert sites_df["enodeb_id"].nunique() == 25

    def test_3_sectors_per_site(self, sites_df):
        for site, group in sites_df.groupby("enodeb_id"):
            assert len(group) == 3, (
                f"{site} has {len(group)} sectors, expected 3"
            )

    def test_valid_bands(self, sites_df):
        valid = {
            "Band 1 (2100MHz)",
            "Band 3 (1800MHz)",
            "Band 41 (2500MHz)",
        }
        assert set(sites_df["frequency_band"].unique()) <= valid

    def test_coordinates_in_tokyo(self, sites_df):
        assert sites_df["latitude"].between(35.5, 35.8).all()
        assert sites_df["longitude"].between(139.5, 139.9).all()


class TestNeighborRelationsQuality:
    def test_no_nulls(self, data_dir):
        result = validate_csv(
            "neighbor_relations.csv",
            data_dir / "neighbor_relations.csv",
        )
        assert result.null_counts == {}

    def test_no_self_neighbors(self, neighbors_df):
        self_refs = neighbors_df[
            neighbors_df["serving_cell"]
            == neighbors_df["neighbor_cell"]
        ]
        assert len(self_refs) == 0, (
            f"Found {len(self_refs)} self-referencing entries"
        )

    def test_reasonable_distances(self, neighbors_df):
        assert (neighbors_df["distance_m"] >= 0).all()

    def test_cio_in_range(self, neighbors_df):
        cio = neighbors_df["cell_individual_offset_dB"]
        assert (cio.between(-15, 15)).all()

    def test_each_cell_has_neighbors(self, neighbors_df, sites_df):
        cells_with = set(neighbors_df["serving_cell"].unique())
        all_cells = set(sites_df["cell_id"].unique())
        missing = all_cells - cells_with
        assert len(missing) == 0, (
            f"Cells without neighbors: {missing}"
        )


class TestPMDataQuality:
    def test_no_nulls_in_sample(self, data_dir):
        result = validate_csv(
            "pm_data_april2026.csv",
            data_dir / "pm_data_april2026.csv",
        )
        assert result.null_counts == {}

    def test_216k_rows(self, data_dir):
        df = pd.read_csv(
            data_dir / "pm_data_april2026.csv",
        )
        assert len(df) == 216000, (
            f"Expected 216000 rows, got {len(df)}"
        )

    def test_ho_success_le_attempts(self, pm_data_df):
        violations = pm_data_df[
            pm_data_df["ho_success_intra"]
            > pm_data_df["ho_attempts_intra"]
        ]
        assert len(violations) == 0, (
            f"{len(violations)} rows where ho_success > attempts"
        )

    def test_kpi_ranges(self, pm_data_df):
        prb = pm_data_df["prb_utilization_dl_pct"]
        assert (prb.between(0, 100)).all()
        rsrp = pm_data_df["avg_rsrp_dBm"]
        assert (rsrp.between(-140, -40)).all()

    def test_75_unique_cells(self, data_dir):
        df = pd.read_csv(
            data_dir / "pm_data_april2026.csv",
            usecols=["cell_id"],
        )
        assert df["cell_id"].nunique() == 75

    def test_rates_sum_to_100(self, pm_data_df):
        total = (
            pm_data_df["ho_success_rate_pct"]
            + pm_data_df["ho_failure_rate_pct"]
        )
        assert ((total - 100.0).abs() < 1.0).all(), (
            "success_rate + failure_rate should ~ 100%"
        )


class TestClusterKPIQuality:
    def test_no_nulls(self, data_dir):
        result = validate_csv(
            "cluster_kpi_summary.csv",
            data_dir / "cluster_kpi_summary.csv",
        )
        assert result.null_counts == {}

    def test_75_rows(self, cluster_kpi_df):
        assert len(cluster_kpi_df) == 75

    def test_has_problem_cells(self, cluster_kpi_df):
        problem_count = (
            cluster_kpi_df["problem_cell"] == "Yes"
        ).sum()
        assert problem_count > 0, (
            "Expected at least one problem cell"
        )

    def test_failure_rate_matches_counts(self, cluster_kpi_df):
        computed = (
            cluster_kpi_df["total_ho_failures"]
            / cluster_kpi_df["total_ho_attempts"]
            * 100
        )
        diff = (
            cluster_kpi_df["ho_failure_rate_pct"] - computed
        ).abs()
        assert (diff < 0.1).all(), (
            "ho_failure_rate_pct should match failures/attempts"
        )

    def test_problem_cells_have_high_failure(self, cluster_kpi_df):
        problems = cluster_kpi_df[
            cluster_kpi_df["problem_cell"] == "Yes"
        ]
        assert (problems["ho_failure_rate_pct"] > 4.0).all(), (
            "Problem cells should have >4% HO failure rate"
        )


class TestFullValidation:
    def test_all_csvs_pass(self, data_dir):
        results = validate_all(data_dir)
        for name, result in results.items():
            assert result.passed, (
                f"{name} failed: {result.range_violations}"
            )
