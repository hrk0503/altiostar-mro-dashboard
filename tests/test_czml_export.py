"""P0 tests (red first): mobility traces -> CZML time-dynamic document."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.generate_mobility_traces import generate
from src.exporters.czml import build_czml

DATA = Path(__file__).resolve().parents[1] / "data" / "synthetic"
pytestmark = pytest.mark.skipif(
    not (DATA / "site_database.csv").exists(), reason="synthetic site data unavailable")


@pytest.fixture(scope="module")
def traces_dir(tmp_path_factory):
    out = tmp_path_factory.mktemp("mob")
    generate(DATA, out)
    return out


def test_czml_is_valid_document(traces_dir, tmp_path):
    doc = build_czml(traces_dir / "mobility_traces.csv", DATA / "site_database.csv")
    assert doc[0]["id"] == "document"
    assert "clock" in doc[0]                     # play/rewind/FF driven by this
    json.dumps(doc)                              # serializable


def test_one_packet_per_ue_plus_sites_and_hos(traces_dir):
    doc = build_czml(traces_dir / "mobility_traces.csv", DATA / "site_database.csv")
    ues = [p for p in doc if str(p.get("id", "")).startswith("UE-")]
    sites = [p for p in doc if str(p.get("id", "")).startswith("site/")]
    hos = [p for p in doc if str(p.get("id", "")).startswith("ho/")]
    assert len(ues) == 21
    assert len(sites) > 0
    assert len(hos) > 0
    # every UE packet is time-dynamic with a path trail
    for p in ues:
        assert "cartographicDegrees" in p["position"]
        assert p["position"]["epoch"]
        assert "path" in p


def test_ho_markers_match_handover_count(traces_dir):
    import pandas as pd
    df = pd.read_csv(traces_dir / "mobility_traces.csv", comment="#")
    doc = build_czml(traces_dir / "mobility_traces.csv", DATA / "site_database.csv")
    hos = [p for p in doc if str(p.get("id", "")).startswith("ho/")]
    assert len(hos) == int(df["handover"].sum())
    # HO markers only exist at their instant (availability interval)
    assert all("availability" in p for p in hos)


def test_seed_changes_paths(tmp_path):
    a = generate(DATA, tmp_path / "a", seed=1)
    b = generate(DATA, tmp_path / "b", seed=2)
    assert a != b  # different seeds -> different traces/manifest
    ta = (tmp_path / "a" / "mobility_traces.csv").read_bytes()
    tb = (tmp_path / "b" / "mobility_traces.csv").read_bytes()
    assert ta != tb


def test_same_seed_is_deterministic(tmp_path):
    a = generate(DATA, tmp_path / "a", seed=7)
    b = generate(DATA, tmp_path / "b", seed=7)
    assert a == b
