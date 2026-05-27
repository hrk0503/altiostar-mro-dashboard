"""Shared pytest fixtures for Altiostar MRO pipeline tests."""
from __future__ import annotations

from pathlib import Path

import pytest
import pandas as pd

from src.pipeline.models import (
    SiteRecord,
    NeighborRelation,
    PMRecord,
    ClusterKPISummary,
)
from src.pipeline.loader import DATA_DIR


@pytest.fixture
def data_dir() -> Path:
    return DATA_DIR


@pytest.fixture
def sample_site() -> SiteRecord:
    return SiteRecord(
        cell_id="RKSB-001-1",
        enodeb_id="RKSB-001",
        site_name="Shibuya-Site-001",
        latitude=35.662183,
        longitude=139.68735,
        antenna_height_m=45,
        sector=1,
        azimuth_deg=357,
        electrical_tilt_deg=4,
        mechanical_tilt_deg=0,
        total_tilt_deg=4,
        clutter_type="Dense Urban",
        elevation_m=60.6,
        frequency_band="Band 41 (2500MHz)",
        pci=4,
        tac=12001,
        vendor="Altiostar",
        technology="LTE",
        status="Active",
    )


@pytest.fixture
def sample_neighbor() -> NeighborRelation:
    return NeighborRelation(
        serving_cell="RKSB-001-1",
        neighbor_cell="RKSB-001-2",
        neighbor_rank=1,
        distance_m=0.0,
        cell_individual_offset_dB=0,
        handover_allowed="Yes",
        relation_type="Inter-Frequency",
        last_updated="2026-04-01",
    )


@pytest.fixture
def sample_pm_record() -> PMRecord:
    return PMRecord(
        timestamp_utc="2026-04-01 00:00:00",
        rop_duration_min=15,
        cell_id="RKSB-001-1",
        enodeb_id="RKSB-001",
        ho_attempts_intra=18,
        ho_success_intra=18,
        ho_failure_intra=0,
        ho_failure_too_early=0,
        ho_failure_too_late=0,
        ho_failure_wrong_cell=0,
        ho_pingpong_count=0,
        ho_success_rate_pct=100.0,
        ho_failure_rate_pct=0.0,
        avg_rsrp_dBm=-94.2,
        avg_rsrq_dB=-13.8,
        avg_sinr_dB=13.4,
        rrc_conn_attempts=79,
        rrc_conn_success=77,
        prb_utilization_dl_pct=3.8,
        prb_utilization_ul_pct=8.2,
        active_ue_avg=3,
        max_ue_connected=10,
    )


@pytest.fixture
def sample_cluster_kpi() -> ClusterKPISummary:
    return ClusterKPISummary(
        cell_id="RKSB-001-1",
        enodeb_id="RKSB-001",
        clutter_type="Dense Urban",
        total_ho_attempts=202227,
        total_ho_success=198073,
        total_ho_failures=4154,
        ho_failure_rate_pct=2.05,
        failure_too_early=447,
        failure_too_late=718,
        failure_wrong_cell=2989,
        total_pingpong=2200,
        pingpong_rate_pct=1.11,
        avg_rsrp_dBm=-85.0,
        problem_cell="No",
    )


@pytest.fixture
def sites_df(data_dir: Path) -> pd.DataFrame:
    return pd.read_csv(data_dir / "site_database.csv")


@pytest.fixture
def neighbors_df(data_dir: Path) -> pd.DataFrame:
    return pd.read_csv(data_dir / "neighbor_relations.csv")


@pytest.fixture
def pm_data_df(data_dir: Path) -> pd.DataFrame:
    return pd.read_csv(data_dir / "pm_data_april2026.csv", nrows=1000)


@pytest.fixture
def cluster_kpi_df(data_dir: Path) -> pd.DataFrame:
    return pd.read_csv(data_dir / "cluster_kpi_summary.csv")
