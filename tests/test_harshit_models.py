"""Tests for Pydantic models — field validation, edge cases, rejection of bad data."""
import pytest
from pydantic import ValidationError

from src.pipeline.models import ClusterKPISummary, NeighborRelation, PMRecord, SiteRecord


class TestSiteRecord:
    def test_valid_record(self, sample_site):
        assert sample_site.cell_id == "CELL_000_0"
        assert sample_site.band == 1

    def test_invalid_band_rejected(self, sample_site):
        data = sample_site.model_dump()
        data["band"] = 99
        with pytest.raises(ValidationError, match="Invalid band"):
            SiteRecord.model_validate(data)

    def test_sector_out_of_range(self, sample_site):
        data = sample_site.model_dump()
        data["sector"] = 5
        with pytest.raises(ValidationError):
            SiteRecord.model_validate(data)

    def test_latitude_out_of_range(self, sample_site):
        data = sample_site.model_dump()
        data["latitude"] = 100.0
        with pytest.raises(ValidationError):
            SiteRecord.model_validate(data)

    def test_negative_power_rejected(self, sample_site):
        data = sample_site.model_dump()
        data["tx_power_dbm"] = -5.0
        with pytest.raises(ValidationError):
            SiteRecord.model_validate(data)


class TestNeighborRelation:
    def test_valid_record(self, sample_neighbor):
        assert sample_neighbor.source_cell == "CELL_000_0"
        assert sample_neighbor.distance_km == 0.5

    def test_same_source_target_rejected(self):
        with pytest.raises(ValidationError, match="must differ"):
            NeighborRelation(
                source_cell="CELL_000_0",
                target_cell="CELL_000_0",
                cio_db=0.0,
                distance_km=0.0,
                handover_count_monthly=0,
                handover_success_rate=0.95,
                ping_pong_rate=0.01,
            )

    def test_success_rate_above_one_rejected(self, sample_neighbor):
        data = sample_neighbor.model_dump()
        data["handover_success_rate"] = 1.5
        with pytest.raises(ValidationError):
            NeighborRelation.model_validate(data)

    def test_negative_distance_rejected(self, sample_neighbor):
        data = sample_neighbor.model_dump()
        data["distance_km"] = -1.0
        with pytest.raises(ValidationError):
            NeighborRelation.model_validate(data)


class TestPMRecord:
    def test_valid_record(self, sample_pm_record):
        assert sample_pm_record.ho_attempt == 20
        assert sample_pm_record.ho_success == 19

    def test_success_exceeds_attempts_rejected(self, sample_pm_record):
        data = sample_pm_record.model_dump()
        data["ho_success"] = 25
        data["ho_attempt"] = 20
        with pytest.raises(ValidationError, match="ho_success.*ho_attempt"):
            PMRecord.model_validate(data)

    def test_rsrp_too_high_rejected(self, sample_pm_record):
        data = sample_pm_record.model_dump()
        data["rsrp_dbm"] = 0.0
        with pytest.raises(ValidationError):
            PMRecord.model_validate(data)

    def test_prb_above_100_rejected(self, sample_pm_record):
        data = sample_pm_record.model_dump()
        data["prb_utilization_pct"] = 150.0
        with pytest.raises(ValidationError):
            PMRecord.model_validate(data)

    def test_timestamp_parsed(self, sample_pm_record):
        assert sample_pm_record.timestamp.year == 2026
        assert sample_pm_record.timestamp.month == 4


class TestClusterKPISummary:
    def test_valid_record(self, sample_cluster_kpi):
        assert sample_cluster_kpi.problem_flag is False
        assert sample_cluster_kpi.monthly_ho_success_rate == 0.97

    def test_inconsistent_rates_rejected(self, sample_cluster_kpi):
        data = sample_cluster_kpi.model_dump()
        data["monthly_ho_success_rate"] = 0.95
        data["monthly_ho_failure_rate"] = 0.20
        with pytest.raises(ValidationError, match="inconsistent"):
            ClusterKPISummary.model_validate(data)

    def test_negative_rlf_rejected(self, sample_cluster_kpi):
        data = sample_cluster_kpi.model_dump()
        data["total_rlf_count"] = -5
        with pytest.raises(ValidationError):
            ClusterKPISummary.model_validate(data)
