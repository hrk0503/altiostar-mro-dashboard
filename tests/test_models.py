"""Tests for Pydantic models -- field validation, edge cases, rejection of bad data."""
import pytest
from pydantic import ValidationError

from src.pipeline.models import (
    SiteRecord,
    NeighborRelation,
    PMRecord,
    ClusterKPISummary,
)


class TestSiteRecord:
    def test_valid_record(self, sample_site):
        assert sample_site.cell_id == "RKSB-001-1"
        assert sample_site.frequency_band == "Band 41 (2500MHz)"

    def test_invalid_band_rejected(self, sample_site):
        data = sample_site.model_dump()
        data["frequency_band"] = "Band 99 (9999MHz)"
        with pytest.raises(ValidationError, match="Invalid frequency_band"):
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

    def test_pci_out_of_range(self, sample_site):
        data = sample_site.model_dump()
        data["pci"] = -1
        with pytest.raises(ValidationError):
            SiteRecord.model_validate(data)


class TestNeighborRelation:
    def test_valid_record(self, sample_neighbor):
        assert sample_neighbor.serving_cell == "RKSB-001-1"
        assert sample_neighbor.distance_m == 0.0

    def test_same_serving_neighbor_rejected(self):
        with pytest.raises(ValidationError, match="must differ"):
            NeighborRelation(
                serving_cell="RKSB-001-1",
                neighbor_cell="RKSB-001-1",
                neighbor_rank=1,
                distance_m=0.0,
                cell_individual_offset_dB=0,
                handover_allowed="Yes",
                relation_type="Intra-Frequency",
                last_updated="2026-04-01",
            )

    def test_cio_out_of_range(self, sample_neighbor):
        data = sample_neighbor.model_dump()
        data["cell_individual_offset_dB"] = 20
        with pytest.raises(ValidationError):
            NeighborRelation.model_validate(data)

    def test_negative_distance_rejected(self, sample_neighbor):
        data = sample_neighbor.model_dump()
        data["distance_m"] = -1.0
        with pytest.raises(ValidationError):
            NeighborRelation.model_validate(data)


class TestPMRecord:
    def test_valid_record(self, sample_pm_record):
        assert sample_pm_record.ho_attempts_intra == 18
        assert sample_pm_record.ho_success_intra == 18

    def test_success_exceeds_attempts_rejected(self, sample_pm_record):
        data = sample_pm_record.model_dump()
        data["ho_success_intra"] = 25
        data["ho_attempts_intra"] = 20
        with pytest.raises(
            ValidationError,
            match="ho_success_intra.*ho_attempts_intra",
        ):
            PMRecord.model_validate(data)

    def test_rsrp_too_high_rejected(self, sample_pm_record):
        data = sample_pm_record.model_dump()
        data["avg_rsrp_dBm"] = 0.0
        with pytest.raises(ValidationError):
            PMRecord.model_validate(data)

    def test_prb_above_100_rejected(self, sample_pm_record):
        data = sample_pm_record.model_dump()
        data["prb_utilization_dl_pct"] = 150.0
        with pytest.raises(ValidationError):
            PMRecord.model_validate(data)

    def test_negative_ho_attempts_rejected(self, sample_pm_record):
        data = sample_pm_record.model_dump()
        data["ho_attempts_intra"] = -1
        with pytest.raises(ValidationError):
            PMRecord.model_validate(data)


class TestClusterKPISummary:
    def test_valid_record(self, sample_cluster_kpi):
        assert sample_cluster_kpi.problem_cell is False
        assert sample_cluster_kpi.ho_failure_rate_pct == 2.05

    def test_negative_attempts_rejected(self, sample_cluster_kpi):
        data = sample_cluster_kpi.model_dump()
        data["total_ho_attempts"] = -5
        with pytest.raises(ValidationError):
            ClusterKPISummary.model_validate(data)

    def test_failure_rate_above_100_rejected(self, sample_cluster_kpi):
        data = sample_cluster_kpi.model_dump()
        data["ho_failure_rate_pct"] = 150.0
        with pytest.raises(ValidationError):
            ClusterKPISummary.model_validate(data)
