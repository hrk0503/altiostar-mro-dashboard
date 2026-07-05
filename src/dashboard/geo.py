"""Sector geometry (Sprint 01, Epic 4.1).

Render 3GPP sectors as azimuth wedges instead of stacked circles per site
(Soumyadeep's objection). Pure functions, unit-tested; the dashboard maps the
output to plotly Scattermapbox fills.
"""
from __future__ import annotations

import math

# ~metres per degree latitude; longitude scaled by cos(lat).
_M_PER_DEG = 111_320.0


def sector_wedge(lat: float, lon: float, azimuth_deg: float,
                 beamwidth_deg: float = 65.0, radius_m: float = 120.0,
                 steps: int = 8) -> list[tuple[float, float]]:
    """Polygon (lat, lon) for a sector fan centred on `azimuth_deg`.

    Azimuth is clockwise from north (0=N, 90=E), the 3GPP convention.
    Returns apex → arc → back to apex (closed ring).
    """
    ring: list[tuple[float, float]] = [(lat, lon)]
    start = azimuth_deg - beamwidth_deg / 2.0
    for i in range(steps + 1):
        ang = math.radians(start + beamwidth_deg * i / steps)
        # bearing: north = +lat, east = +lon
        dlat = radius_m * math.cos(ang) / _M_PER_DEG
        dlon = radius_m * math.sin(ang) / (_M_PER_DEG * math.cos(math.radians(lat)))
        ring.append((lat + dlat, lon + dlon))
    ring.append((lat, lon))
    return ring
