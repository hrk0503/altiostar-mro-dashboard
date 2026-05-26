from pydantic import BaseModel, Field
from typing import Optional

class SiteRecord(BaseModel):
    site_id: str
    sector_id: str
    band: int
    latitude: float
    longitude: float
    antenna_height: float
    tilt: float
    power_dbm: float

class NeighborRelation(BaseModel):
    source_cell: str
    target_cell: str
    cio: float
    distance_m: float

class PMRecord(BaseModel):
    cell_id: str
    timestamp: str
    rsrp: float
    rsrq: float
    sinr: float
    prb_util: float
    ho_success: int
    ho_failure: int
    ping_pong: int

class ClusterKPISummary(BaseModel):
    cell_id: str
    ho_failure_rate: float
    ping_pong_rate: float
    avg_rsrp: float
    avg_sinr: float
    problem_cell: bool