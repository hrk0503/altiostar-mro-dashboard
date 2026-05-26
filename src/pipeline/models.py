from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class SiteRecord(BaseModel):
    """Single cell/sector from site_database.csv"""
    cell_id: str
    enodeb_id: str
    site_name: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    antenna_height_m: float = Field(ge=5, le=100)
    sector: int = Field(ge=0, le=2)
    azimuth_deg: int = Field(ge=-10, le=370)
    electrical_tilt_deg: float = Field(ge=0, le=15)
    mechanical_tilt_deg: float = Field(ge=0, le=15)
    total_tilt_deg: float = Field(ge=0, le=30)
    clutter_type: str
    elevation_m: float
    frequency_band: int
    pci: int = Field(ge=0)
    tac: int = Field(ge=0)
    vendor: str
    technology: str
    status: str

    @field_validator("frequency_band")
    @classmethod
    def validate_band(cls, v: int) -> int:
        if v not in (1, 3, 41):
            raise ValueError(f"Invalid band {v}, expected 1, 3, or 41")
        return v


class NeighborRelation(BaseModel):
    """Single neighbor pair from neighbor_relations.csv"""
    serving_cell: str
    neighbor_cell: str
    neighbor_rank: int = Field(ge=0)
    distance_m: float = Field(ge=0)
    cell_individual_offset_dB: float = Field(ge=-15, le=15)
    handover_allowed: bool
    relation_type: str
    last_updated: str

    @field_validator("neighbor_cell")
    @classmethod
    def source_and_target_differ(cls, v: str, info) -> str:
        if info.data.get("serving_cell") == v:
            raise ValueError("serving_cell and neighbor_cell must differ")
        return v


class PMRecord(BaseModel):
    """Single 15-min ROP from pm_data_april2026.csv (216K rows)"""
    timestamp_utc: datetime
    rop_duration_min: int = Field(ge=0)
    cell_id: str
    enodeb_id: str
    ho_attempts_intra: int = Field(ge=0)
    ho_success_intra: int = Field(ge=0)
    ho_failure_intra: int = Field(ge=0)
    ho_failure_too_early: int = Field(ge=0)
    ho_failure_too_late: int = Field(ge=0)
    ho_failure_wrong_cell: int = Field(ge=0)
    ho_pingpong_count: int = Field(ge=0)
    ho_success_rate_pct: float = Field(ge=0, le=100)
    ho_failure_rate_pct: float = Field(ge=0, le=100)
    avg_rsrp_dBm: float = Field(ge=-140, le=-40)
    avg_rsrq_dB: float = Field(ge=-30, le=0)
    avg_sinr_dB: float = Field(ge=-10, le=40)
    rrc_conn_attempts: int = Field(ge=0)
    rrc_conn_success: int = Field(ge=0)
    prb_utilization_dl_pct: float = Field(ge=0, le=100)
    prb_utilization_ul_pct: float = Field(ge=0, le=100)
    active_ue_avg: float = Field(ge=0)
    max_ue_connected: int = Field(ge=0)

    @field_validator("ho_success_intra")
    @classmethod
    def success_le_attempts(cls, v: int, info) -> int:
        attempts = info.data.get("ho_attempts_intra")
        if attempts is not None and v > attempts:
            raise ValueError(f"ho_success_intra ({v}) > ho_attempts_intra ({attempts})")
        return v


class ClusterKPISummary(BaseModel):
    """Monthly aggregate per cell from cluster_kpi_summary.csv (75 rows)"""
    cell_id: str
    enodeb_id: str
    clutter_type: str
    total_ho_attempts: int = Field(ge=0)
    total_ho_success: int = Field(ge=0)
    total_ho_failures: int = Field(ge=0)
    ho_failure_rate_pct: float = Field(ge=0, le=100)
    failure_too_early: int = Field(ge=0)
    failure_too_late: int = Field(ge=0)
    failure_wrong_cell: int = Field(ge=0)
    total_pingpong: int = Field(ge=0)
    pingpong_rate_pct: float = Field(ge=0, le=100)
    avg_rsrp_dBm: float
    problem_cell: bool