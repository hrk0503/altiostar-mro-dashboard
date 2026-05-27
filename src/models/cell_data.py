"""Pydantic models for telecom cell data — typed internal schema."""

from pydantic import BaseModel, Field


class CellSite(BaseModel):
    cell_id: str
    site_id: str
    sector: int = Field(ge=1, le=3)
    latitude: float
    longitude: float
    azimuth: float = Field(ge=0, lt=360)
    band: str
    tx_power_dbm: float
    antenna_height_m: float
    mechanical_tilt: float
    electrical_tilt: float


class NeighborRelation(BaseModel):
    source_cell_id: str
    target_cell_id: str
    cio_db: float = Field(ge=-24.0, le=24.0)
    distance_m: float
    is_intra_freq: bool


class PMRecord(BaseModel):
    """Performance Management record — one per cell per ROP (15-min interval)."""
    cell_id: str
    timestamp: str
    ho_attempts: int = Field(ge=0)
    ho_successes: int = Field(ge=0)
    ho_failures: int = Field(ge=0)
    ho_ping_pongs: int = Field(ge=0)
    rsrp_mean: float
    rsrq_mean: float
    sinr_mean: float
    prb_utilization: float = Field(ge=0, le=1)
    connected_ues: int = Field(ge=0)
    throughput_dl_mbps: float = Field(ge=0)
    throughput_ul_mbps: float = Field(ge=0)


class ClusterKPISummary(BaseModel):
    cell_id: str
    ho_success_rate: float = Field(ge=0, le=1)
    ho_failure_rate: float = Field(ge=0, le=1)
    ping_pong_rate: float = Field(ge=0, le=1)
    avg_rsrp: float
    avg_sinr: float
    is_problem_cell: bool
