"""Tests for the synthetic UE mobility generator (test-first hardening)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from scripts.generate_mobility_traces import PROFILES, generate

DATA = Path(__file__).resolve().parents[1] / "data" / "synthetic"
pytestmark = pytest.mark.skipif(
    not (DATA / "site_database.csv").exists(), reason="synthetic site data unavailable")

_COLS = {"ue_id", "user_type", "t_s", "timestamp_utc", "lat", "lon",
         "ue_height_agl_m", "env", "speed_kmh", "heading_deg", "serving_cell", "handover"}


def test_schema_includes_height_and_env(tmp_path):
    generate(DATA, tmp_path)
    df = pd.read_csv(tmp_path / "mobility_traces.csv", comment="#")
    assert _COLS.issubset(df.columns)
    assert (df["env"] == "outdoor").all()


def test_height_matches_3gpp_profiles(tmp_path):
    generate(DATA, tmp_path)
    df = pd.read_csv(tmp_path / "mobility_traces.csv", comment="#")
    # AGL heights per profile (TR 38.901): ped/car 1.5 m, train 2.0 m
    for utype, params in PROFILES.items():
        h = params[4]
        assert (df[df["user_type"] == utype]["ue_height_agl_m"] == h).all()
    assert set(df["ue_height_agl_m"].unique()) <= {1.5, 2.0}


def test_deterministic(tmp_path):
    a = generate(DATA, tmp_path / "a")
    b = generate(DATA, tmp_path / "b")
    assert a == b
    assert (tmp_path / "a" / "mobility_traces.csv").read_bytes() == \
           (tmp_path / "b" / "mobility_traces.csv").read_bytes()


def test_geometry_and_handovers(tmp_path):
    m = generate(DATA, tmp_path)
    assert m["ues"] == sum(p[3] for p in PROFILES.values())
    assert m["handovers"] > 0
    df = pd.read_csv(tmp_path / "mobility_traces.csv", comment="#")
    assert (df["lon"].between(139.0, 140.5)).all()   # Shibuya bounds
    assert (df["lat"].between(35.0, 36.5)).all()
