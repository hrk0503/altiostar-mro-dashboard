"""Epic 4 tests — weighted KPI + sector wedges (test-first)."""
from __future__ import annotations

import math

from src.dashboard.geo import sector_wedge
from src.dashboard.kpi import attempt_weighted_hosr


# 4.2 attempt-weighted KPI
def test_weighted_differs_from_mean_when_attempts_uneven():
    rates = [50.0, 100.0]          # one bad big cell, one perfect tiny cell
    attempts = [1000.0, 1.0]
    weighted = attempt_weighted_hosr(rates, attempts)
    plain = sum(rates) / 2         # 75.0 — misleadingly high
    assert weighted < 51.0         # weighted ~50.05, reflects the big cell
    assert abs(weighted - plain) > 20


def test_weighted_equals_mean_when_attempts_equal():
    assert attempt_weighted_hosr([80.0, 90.0], [100.0, 100.0]) == 85.0


def test_weighted_zero_attempts_falls_back():
    assert attempt_weighted_hosr([80.0, 90.0], [0.0, 0.0]) == 85.0


# 4.1 sector wedges
def test_wedge_is_closed_ring_with_apex():
    w = sector_wedge(35.66, 139.69, azimuth_deg=90.0)
    assert w[0] == w[-1] == (35.66, 139.69)     # closed on the site apex
    assert len(w) >= 5                           # apex + arc


def test_wedge_points_toward_azimuth():
    # azimuth 90 (east) → arc points should be east (higher lon) of the site
    site = (35.66, 139.69)
    w = sector_wedge(*site, azimuth_deg=90.0, beamwidth_deg=60.0)
    arc = w[1:-1]
    assert all(p[1] > site[1] for p in arc)      # all east
    # azimuth 0 (north) → arc points north (higher lat)
    wn = sector_wedge(*site, azimuth_deg=0.0, beamwidth_deg=60.0)
    assert all(p[0] > site[0] for p in wn[1:-1])


def test_three_sectors_are_distinct():
    site = (35.66, 139.69)
    centroids = []
    for az in (0.0, 120.0, 240.0):
        w = sector_wedge(*site, azimuth_deg=az)
        arc = w[1:-1]
        centroids.append((sum(p[0] for p in arc) / len(arc), sum(p[1] for p in arc) / len(arc)))
    # the three sector centroids must be mutually distinct
    for i in range(3):
        for j in range(i + 1, 3):
            assert math.dist(centroids[i], centroids[j]) > 1e-4
