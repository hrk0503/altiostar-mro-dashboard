"""Typed Pydantic models for all 4 Altiostar MRO synthetic CSVs."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, ValidationInfo, field_validator


class SiteRecord(BaseModel):
    """Single cell/sector from site_database.csv (75 rows: 25 sites x 3 sectors)."""
    cell_id: str
    site_id: str
    sector: int = Field(ge=0, le=2)
    band: int
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    azimuth: int = Field(ge=-10, le=370)
    mechanical_tilt: float = Field(ge=0, le=15)
    electrical_tilt: float = Field(ge=0, le=15)
    tx_power_dbm: float = Field(ge=20, le=60)
    antenna_height_m: float = Field(ge=5, le=100)
    frequency_mhz: int = Field(gt=0)

    @field_validator("band")
    @classmethod
    def validate_band(cls, v: int) -> int:
        if v not in (1, 3, 41):
            raise ValueError(f"Invalid band {v}, expected 1, 3, or 41")
        return v


class NeighborRelation(BaseModel):
    """Single neighbor pair from neighbor_relations.csv."""
    source_cell: str
    target_cell: str
    cio_db: float = Field(ge=-15, le=15)
    distance_km: float = Field(ge=0)
    handover_count_monthly: int = Field(ge=0)
    handover_success_rate: float = Field(ge=0, le=1)
    ping_pong_rate: float = Field(ge=0, le=1)

    @field_validator("target_cell")
    @classmethod
    def source_and_target_differ(cls, v: str, info: ValidationInfo) -> str:
        if info.data.get("source_cell") == v:
            raise ValueError("source_cell and target_cell must differ")
        return v


class PMRecord(BaseModel):
    """Single 15-min ROP from pm_data_april2026.csv (216K rows)."""
    cell_id: str
    timestamp: datetime
    rsrp_dbm: float = Field(ge=-140, le=-40)
    rsrq_db: float = Field(ge=-30, le=0)
    sinr_db: float = Field(ge=-10, le=40)
    prb_utilization_pct: float = Field(ge=0, le=100)
    active_ue_count: int = Field(ge=0)
    rrc_connected_ue: int = Field(ge=0)
    ho_attempt: int = Field(ge=0)
    ho_success: int = Field(ge=0)
    ho_failure: int = Field(ge=0)
    ho_ping_pong: int = Field(ge=0)
    late_ho: int = Field(ge=0)
    early_ho: int = Field(ge=0)
    wrong_cell_ho: int = Field(ge=0)
    dl_throughput_mbps: float = Field(ge=0)
    ul_throughput_mbps: float = Field(ge=0)
    cqi_avg: float = Field(ge=1, le=15)
    rlf_count: int = Field(ge=0)
    call_drop_rate_pct: float = Field(ge=0, le=100)

    @field_validator("ho_success")
    @classmethod
    def success_le_attempts(cls, v: int, info: ValidationInfo) -> int:
        attempts = info.data.get("ho_attempt")
        if attempts is not None and v > attempts:
            raise ValueError(f"ho_success ({v}) > ho_attempt ({attempts})")
        return v


class ClusterKPISummary(BaseModel):
    """Monthly aggregate per cell from cluster_kpi_summary.csv (75 rows)."""
    cell_id: str
    site_id: str
    band: int
    monthly_ho_attempts: int = Field(ge=0)
    monthly_ho_success_rate: float = Field(ge=0, le=1)
    monthly_ho_failure_rate: float = Field(ge=0, le=1)
    monthly_ping_pong_rate: float = Field(ge=0, le=1)
    avg_rsrp_dbm: float
    avg_sinr_db: float
    avg_prb_utilization_pct: float = Field(ge=0, le=100)
    avg_dl_throughput_mbps: float = Field(ge=0)
    total_rlf_count: int = Field(ge=0)
    problem_flag: bool

    @field_validator("monthly_ho_failure_rate")
    @classmethod
    def failure_rate_consistent(cls, v: float, info: ValidationInfo) -> float:
        success = info.data.get("monthly_ho_success_rate")
        if success is not None and abs(v - (1 - success)) > 0.01:
            raise ValueError(
                f"failure_rate ({v}) inconsistent with success_rate ({success})"
            )
        return v
