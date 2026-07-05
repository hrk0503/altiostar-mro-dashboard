"""Tests for the WINNIIO→Blaretech counterfactual export."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.integration.blaretech_export import DEFAULT_CIO_CANDIDATES, build_export

DATA = Path(__file__).resolve().parents[1] / "data" / "synthetic"

pytestmark = pytest.mark.skipif(
    not (DATA / "pm_data_relation_level.csv").exists(),
    reason="synthetic relation PM not available",
)


def test_export_shape_and_files(tmp_path):
    m = build_export(DATA, tmp_path)
    # all expected files exist
    for f in ["01_counterfactual_request.csv", "02_sites.geojson",
              "03_relations.geojson", "RETURN_SCHEMA.csv", "manifest.json"]:
        assert (tmp_path / f).exists(), f

    req = pd.read_csv(tmp_path / "01_counterfactual_request.csv")
    # one row per (relation × candidate CIO)
    assert len(req) == m["n_relations"] * len(DEFAULT_CIO_CANDIDATES)
    assert set(req["candidate_cio_db"].unique()) == set(DEFAULT_CIO_CANDIDATES)
    # geometry present, no fabricated candidate outcomes
    for col in ["src_latitude", "src_longitude", "src_azimuth_deg", "current_success_pct"]:
        assert col in req.columns
    assert "sim_ho_successes" not in req.columns  # outcomes are Blaretech's job


def test_return_schema_is_headers_only(tmp_path):
    build_export(DATA, tmp_path)
    ret = pd.read_csv(tmp_path / "RETURN_SCHEMA.csv")
    assert len(ret) == 0
    for c in ["candidate_cio_db", "sim_ho_attempts", "sim_ho_successes", "sim_ping_pong"]:
        assert c in ret.columns


def test_geojson_valid_wgs84(tmp_path):
    build_export(DATA, tmp_path)
    sites = json.loads((tmp_path / "02_sites.geojson").read_text())
    assert sites["type"] == "FeatureCollection"
    lon, lat = sites["features"][0]["geometry"]["coordinates"]
    assert 139.0 < lon < 140.5 and 35.0 < lat < 36.5  # Shibuya bounds
