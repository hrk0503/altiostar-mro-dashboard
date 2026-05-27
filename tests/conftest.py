"""Shared pytest fixtures for Altiostar MRO pipeline tests."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.pipeline.loader import DATA_DIR
from src.pipeline.models import ClusterKPISummary, NeighborRelation, PMRecord, SiteRecord


@pytest.fixture
def data_dir() -> Path:
    return DATA_DIR


@pytest.fixture
def sample_site() -> SiteRecord:
    return SiteRecord(
        cell_id="CELL_000_0",
        site_id="SITE_000",
        sector=0,
        band=1,
        latitude=35.6580,
        longitude=139.7016,
        azimuth=0,
        mechanical_tilt=4.0,
        electrical_tilt=2.0,
        tx_power_dbm=43.0,
        antenna_height_m=30.0,
        frequency_mhz=2100,
    )


@pytest.fixture
def sample_neighbor() -> NeighborRelation:
    return NeighborRelation(
        source_cell="CELL_000_0",
        target_cell="CELL_001_0",
        cio_db=2.0,
        distance_km=0.5,
        handover_count_monthly=1500,
        handover_success_rate=0.96,
        ping_pong_rate=0.02,
    )


@pytest.fixture
def sample_pm_record() -> PMRecord:
    return PMRecord(
        cell_id="CELL_000_0",
        timestamp="2026-04-01T00:00:00",
        rsrp_dbm=-85.0,
        rsrq_db=-10.0,
        sinr_db=12.0,
        prb_utilization_pct=45.0,
        active_ue_count=30,
        rrc_connected_ue=50,
        ho_attempt=20,
        ho_success=19,
        ho_failure=1,
        ho_ping_pong=0,
        late_ho=0,
        early_ho=0,
        wrong_cell_ho=0,
        dl_throughput_mbps=80.0,
        ul_throughput_mbps=20.0,
        cqi_avg=10.0,
        rlf_count=2,
        call_drop_rate_pct=0.5,
    )


@pytest.fixture
def sample_cluster_kpi() -> ClusterKPISummary:
    return ClusterKPISummary(
        cell_id="CELL_000_0",
        site_id="SITE_000",
        band=1,
        monthly_ho_attempts=60000,
        monthly_ho_success_rate=0.97,
        monthly_ho_failure_rate=0.03,
        monthly_ping_pong_rate=0.01,
        avg_rsrp_dbm=-85.0,
        avg_sinr_db=12.0,
        avg_prb_utilization_pct=40.0,
        avg_dl_throughput_mbps=80.0,
        total_rlf_count=30,
        problem_flag=False,
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
