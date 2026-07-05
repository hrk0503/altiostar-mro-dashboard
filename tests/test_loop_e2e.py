"""E2E-1: the whole loop runs and is byte-reproducible (Vitalik gate)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from run_loop import run_loop

DATA = Path(__file__).resolve().parents[1] / "data" / "synthetic"
pytestmark = pytest.mark.skipif(
    not (DATA / "pm_data_relation_level.csv").exists(),
    reason="synthetic data not available",
)


def test_loop_runs_end_to_end(tmp_path):
    s = run_loop(DATA, tmp_path / "run1")
    assert s["relations"] > 0
    assert Path(s["result_file"]).exists()
    df = pd.read_csv(s["result_file"])
    for col in ["source_cell", "target_cell", "before_success_%", "after_success_%", "improvement_pp"]:
        assert col in df.columns
    # provenance is explicit (grounded, not fabricated real-world)
    assert (df["source"] == "counterfactual_sim").all()


def test_loop_is_deterministic(tmp_path):
    a = run_loop(DATA, tmp_path / "a")
    b = run_loop(DATA, tmp_path / "b")
    assert a["run_hash"] == b["run_hash"]  # same inputs -> identical result


def test_loop_improves_on_average(tmp_path):
    # On synthetic data the optimizer must beat the current config (the whole point).
    s = run_loop(DATA, tmp_path / "r")
    assert s["mean_after_%"] > s["mean_before_%"]
