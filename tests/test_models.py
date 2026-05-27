"""Tests for Pydantic data models — validates schema constraints."""

import pytest
from pydantic import ValidationError

from src.models.cell_data import (
    CellSite,
    ClusterKPISummary,
    NeighborRelation,
    PMRecord,
    RelationPMRecord,
)


class TestCellSite:
    def test_valid_cell(self):
        cell = CellSite(
            cell_id="CELL_001_1",
            site_id="SITE_001",
            sector=1,
            latitude=35.6762,
            longitude=139.6503,
            azimuth=0.0,
            band="n77",
            tx_power_dbm=43.0,
            antenna_height_m=30.0,
            mechanical_tilt=2.0,
            electrical_tilt=4.0,
        )
        assert cell.cell_id == "CELL_001_1"

    def test_invalid_sector(self):
        with pytest.raises(ValidationError):
            CellSite(
                cell_id="X", site_id="X", sector=4,
                latitude=0, longitude=0, azimuth=0, band="n77",
                tx_power_dbm=0, antenna_height_m=0,
                mechanical_tilt=0, electrical_tilt=0,
            )


class TestNeighborRelation:
    def test_valid_relation(self):
        nr = NeighborRelation(
            source_cell_id="A", target_cell_id="B",
            cio_db=3.0, distance_m=500.0, is_intra_freq=True,
        )
        assert nr.cio_db == 3.0

    def test_cio_out_of_range(self):
        with pytest.raises(ValidationError):
            NeighborRelation(
                source_cell_id="A", target_cell_id="B",
                cio_db=25.0, distance_m=500.0, is_intra_freq=True,
            )


class TestPMRecord:
    def test_valid_record(self):
        pm = PMRecord(
            cell_id="CELL_001_1", timestamp="2026-04-01T00:00:00",
            ho_attempts=100, ho_successes=95, ho_failures=3, ho_ping_pongs=2,
            rsrp_mean=-85.0, rsrq_mean=-10.0, sinr_mean=15.0,
            prb_utilization=0.65, connected_ues=42,
            throughput_dl_mbps=150.0, throughput_ul_mbps=30.0,
        )
        assert pm.ho_attempts == 100

    def test_negative_ho_attempts(self):
        with pytest.raises(ValidationError):
            PMRecord(
                cell_id="X", timestamp="X",
                ho_attempts=-1, ho_successes=0, ho_failures=0, ho_ping_pongs=0,
                rsrp_mean=0, rsrq_mean=0, sinr_mean=0,
                prb_utilization=0, connected_ues=0,
                throughput_dl_mbps=0, throughput_ul_mbps=0,
            )


class TestRelationPMRecord:
    def test_valid_relation_record(self):
        rec = RelationPMRecord(
            source_cell_id="CELL_001_1", target_cell_id="CELL_002_3",
            timestamp="2026-04-01T00:00:00",
            ho_attempts=50, ho_successes=48, ho_failures=1,
            too_early_ho=0, too_late_ho=1, wrong_cell=0,
            correct_cell=48, ping_pong=1,
        )
        assert rec.ho_attempts == 50

    def test_negative_counter_rejected(self):
        with pytest.raises(ValidationError):
            RelationPMRecord(
                source_cell_id="A", target_cell_id="B",
                timestamp="X",
                ho_attempts=-1, ho_successes=0, ho_failures=0,
                too_early_ho=0, too_late_ho=0, wrong_cell=0,
                correct_cell=0, ping_pong=0,
            )


class TestClusterKPISummary:
    def test_problem_cell(self):
        kpi = ClusterKPISummary(
            cell_id="CELL_005_2",
            ho_success_rate=0.92, ho_failure_rate=0.06, ping_pong_rate=0.02,
            avg_rsrp=-95.0, avg_sinr=8.0, is_problem_cell=True,
        )
        assert kpi.is_problem_cell is True
