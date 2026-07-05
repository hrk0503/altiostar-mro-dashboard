"""Epic 1 tests — synthetic return + ingest + optimize (test-first)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.integration.blaretech_export import build_export
from src.integration.counterfactual_loop import (
    current_from_request,
    ingest_counterfactuals,
    optimize,
)
from src.integration.synthetic_rf_return import RETURN_COLS, generate, simulate_return

DATA = Path(__file__).resolve().parents[1] / "data" / "synthetic"
pytestmark = pytest.mark.skipif(
    not (DATA / "pm_data_relation_level.csv").exists(),
    reason="synthetic data not available",
)


def _request(tmp_path):
    build_export(DATA, tmp_path)
    return tmp_path / "01_counterfactual_request.csv"


# 1.1 synthetic return
def test_return_has_schema_and_rowcount(tmp_path):
    req = _request(tmp_path)
    n_rel = pd.read_csv(req)[["source_cell_id", "target_cell_id"]].drop_duplicates().shape[0]
    n_cio = pd.read_csv(req)["candidate_cio_db"].nunique()
    out = simulate_return(pd.read_csv(req))
    assert list(out.columns) == RETURN_COLS
    assert len(out) == n_rel * n_cio
    # success = attempts - failures for every row
    assert (out["sim_ho_successes"] + out["sim_ho_failures"] == out["sim_ho_attempts"]).all()


def test_return_is_deterministic(tmp_path):
    req = _request(tmp_path)
    a = generate(req, tmp_path / "r1.csv")
    b = generate(req, tmp_path / "r2.csv")
    assert a.equals(b)
    assert (tmp_path / "r1.csv").read_bytes() == (tmp_path / "r2.csv").read_bytes()


def test_return_file_has_synthetic_banner(tmp_path):
    req = _request(tmp_path)
    generate(req, tmp_path / "r.csv")
    assert (tmp_path / "r.csv").read_text(encoding="utf-8").splitlines()[0].startswith("# SYNTHETIC")


# 1.2 ingest
def test_ingest_builds_multi_cio_space(tmp_path):
    req = _request(tmp_path)
    generate(req, tmp_path / "r.csv")
    space = ingest_counterfactuals(tmp_path / "r.csv")
    assert len(space) > 0
    any_rel = next(iter(space.values()))
    assert len(any_rel) >= 2  # more than one CIO to search over


# 1.3 optimize
def test_optimize_picks_argmax_success():
    space = {("A-1", "A-2"): {-2.0: 80.0, 0.0: 99.0, 2.0: 85.0}}
    df = optimize(space, current={("A-1", "A-2"): (-2.0, 80.0)})
    row = df.iloc[0]
    assert row["optimal_cio_db"] == 0.0
    assert row["after_success_%"] == 99.0
    assert row["improvement_pp"] == 19.0


def test_optimize_end_to_end_improves_or_holds(tmp_path):
    req = _request(tmp_path)
    generate(req, tmp_path / "r.csv")
    space = ingest_counterfactuals(tmp_path / "r.csv")
    cur = current_from_request(req)
    df = optimize(space, current=cur)
    # metamorphic: the chosen CIO's success is never worse than any other option
    for (src, tgt), opts in space.items():
        chosen = df[(df.source_cell == src) & (df.target_cell == tgt)]["after_success_%"].iloc[0]
        assert chosen >= max(opts.values()) - 0.011  # rounding tolerance
