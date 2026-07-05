"""Tests for the LangGraph agentic MRO pipeline (src.pipeline_graph).

Wiring + per-node state transforms are verified. The heavy calls (MROEnv,
find_optimal_cios, evaluate_with_optimal_cios) are mocked with a small fixture
so the suite stays fast; the ingest/validate/ship_gate/spectrum paths run for
real against a tiny generated CSV.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.pipeline_graph import graph as graph_mod
from src.pipeline_graph import nodes
from src.pipeline_graph.graph import LANGGRAPH_AVAILABLE, build_graph, run_sequential

# ── fixtures ──────────────────────────────────────────────────────────────────

# All columns required by validator's pm_data range rules + schema_mapper's
# PMRecord signature, so the real validator/schema_mapper run end-to-end.
_PM_COLUMNS = [
    "cell_id", "timestamp_utc", "avg_rsrp_dBm", "avg_rsrq_dB", "avg_sinr_dB",
    "prb_utilization_dl_pct", "prb_utilization_ul_pct", "ho_attempts_intra",
    "ho_success_intra", "ho_failure_intra", "ho_success_rate_pct",
    "ho_failure_rate_pct",
]


def _write_pm_csv(path, *, rsrp_values):
    rows = []
    for i, rsrp in enumerate(rsrp_values):
        rows.append({
            "cell_id": f"RKSB-001-{i + 1}",
            "timestamp_utc": f"2026-04-01 00:0{i}:00",
            "avg_rsrp_dBm": rsrp,
            "avg_rsrq_dB": -13.0,
            "avg_sinr_dB": 13.0,
            "prb_utilization_dl_pct": 3.0,
            "prb_utilization_ul_pct": 8.0,
            "ho_attempts_intra": 18,
            "ho_success_intra": 18,
            "ho_failure_intra": 0,
            "ho_success_rate_pct": 100.0,
            "ho_failure_rate_pct": 0.0,
        })
    pd.DataFrame(rows, columns=_PM_COLUMNS).to_csv(path, index=False)
    return path


@pytest.fixture
def good_csv(tmp_path):
    # Named exactly so validator applies the pm range-rules.
    return _write_pm_csv(tmp_path / "pm_data_april2026.csv", rsrp_values=[-94.0, -96.0, -90.0])


@pytest.fixture
def bad_csv(tmp_path):
    # avg_rsrp_dBm=0.0 is above the -40 dBm ceiling → real range violation.
    return _write_pm_csv(tmp_path / "pm_data_april2026.csv", rsrp_values=[0.0, -96.0, -90.0])


class _FakeEnv:
    """Stand-in for MROEnv — avoids loading the 2.2M-row relation dataset."""

    n_relations = 2

    def reset(self, seed=None):
        return None, {}


_FAKE_OPT = {
    "optimal_cios": np.array([2.0, 30.0], dtype=np.float32),  # 30.0 is out of 3GPP range
    "improvements": [
        {"relation": "RKSB-001-1->RKSB-001-2", "initial_cio": 0.0, "optimal_cio": 2.0,
         "delta": 2.0, "current_success": 95.0, "optimal_success": 99.5, "improvement": 4.5},
        {"relation": "RKSB-002-1->RKSB-002-2", "initial_cio": 0.0, "optimal_cio": 30.0,
         "delta": 30.0, "current_success": 90.0, "optimal_success": 98.0, "improvement": 8.0},
    ],
}

_PASS_METRICS = {"ho_success_rate": 99.5, "pingpong_rate": 1.0, "ho_failure_rate": 0.5}
_FAIL_METRICS = {"ho_success_rate": 80.0, "pingpong_rate": 10.0, "ho_failure_rate": 20.0}


@pytest.fixture
def mock_heavy(monkeypatch):
    """Patch the heavy env + optimizer calls in the nodes module."""
    monkeypatch.setattr(nodes, "MROEnv", _FakeEnv)
    monkeypatch.setattr(nodes, "find_optimal_cios", lambda env: _FAKE_OPT)

    def _fake_eval(env, optimal, n_episodes=3, seed=42):
        return dict(_PASS_METRICS)

    monkeypatch.setattr(nodes, "evaluate_with_optimal_cios", _fake_eval)
    return monkeypatch


# ── node-level transforms ─────────────────────────────────────────────────────

def test_ingest_reads_shape_and_schema(good_csv):
    state = nodes.node_ingest({"data_path": str(good_csv)})
    assert state["n_rows"] == 3
    assert state["n_cols"] == len(_PM_COLUMNS)
    assert state["csv_name"] == "pm_data_april2026.csv"
    assert state["schema_matched_model"] == "PMRecord"


def test_ingest_missing_file():
    state = nodes.node_ingest({"data_path": "does/not/exist.csv"})
    assert state["n_rows"] == 0
    assert any("file not found" in e for e in state["errors"])


def test_validate_pass(good_csv):
    state = nodes.node_validate({"data_path": str(good_csv)})
    assert state["validation_passed"] is True
    assert state["validation_report"]["total_rows"] == 3


def test_validate_fail_on_range(bad_csv):
    state = nodes.node_validate({"data_path": str(bad_csv)})
    assert state["validation_passed"] is False
    assert state["validation_report"]["range_violations"]


def test_optimize_node_records_cios_and_spectrum(mock_heavy):
    state = nodes.node_optimize_cio({}, env=_FakeEnv())
    assert state["n_relations"] == 2
    assert state["optimal_cios"] == [2.0, 30.0]
    # 30 dB is out of the 3GPP CIO range → at least one violation flagged.
    assert state["spectrum_review"]["n_violations"] >= 1
    assert state["spectrum_review"]["n_checked"] == 2


def test_evaluate_node_sets_metrics(mock_heavy):
    state = nodes.node_evaluate({"optimal_cios": [2.0, 30.0]}, env=_FakeEnv())
    assert state["eval_metrics"]["ho_success_rate"] == 99.5


def test_ship_gate_pass():
    state = nodes.node_ship_gate({"eval_metrics": dict(_PASS_METRICS)})
    assert state["gate_passed"] is True
    assert state["gate_reasons"] == []


def test_ship_gate_fail():
    state = nodes.node_ship_gate({"eval_metrics": dict(_FAIL_METRICS)})
    assert state["gate_passed"] is False
    assert state["gate_reasons"]


def test_report_and_needs_review_terminals():
    r = nodes.node_report({"eval_metrics": dict(_PASS_METRICS), "gate_passed": True})
    assert r["status"] == "shipped"
    assert "not RL" in r["summary"]["method"]

    nr = nodes.node_needs_review({"gate_reasons": ["boom"]})
    assert nr["status"] == "needs_review"
    assert nr["summary"]["gate_reasons"] == ["boom"]


# ── routing ───────────────────────────────────────────────────────────────────

def test_route_after_validate():
    assert nodes.route_after_validate({"validation_passed": True}) == "optimize_cio"
    assert nodes.route_after_validate({"validation_passed": False}) == "stop"


def test_route_after_ship_gate():
    assert nodes.route_after_ship_gate({"gate_passed": True}) == "report"
    assert nodes.route_after_ship_gate({"gate_passed": False}) == "needs_review"


# ── end-to-end via the reference executor (wiring order) ───────────────────────

def test_sequential_happy_path_ships(good_csv, mock_heavy):
    final = run_sequential({"data_path": str(good_csv)})
    assert final["status"] == "shipped"
    assert final["summary"]["gate_passed"] is True


def test_sequential_needs_review_when_gate_fails(good_csv, mock_heavy):
    mock_heavy.setattr(
        nodes, "evaluate_with_optimal_cios",
        lambda env, optimal, n_episodes=3, seed=42: dict(_FAIL_METRICS),
    )
    final = run_sequential({"data_path": str(good_csv)})
    assert final["status"] == "needs_review"


def test_sequential_stops_on_validation_failure(bad_csv, mock_heavy):
    final = run_sequential({"data_path": str(bad_csv)})
    assert final["status"] == "validation_failed"
    assert "optimal_cios" not in final  # never reached the optimizer


# ── build_graph (real LangGraph when available) ───────────────────────────────

@pytest.mark.skipif(not LANGGRAPH_AVAILABLE, reason="langgraph not installed")
def test_build_graph_compiles_and_runs(good_csv, mock_heavy):
    app = build_graph().compile()
    final = app.invoke({"data_path": str(good_csv)})
    assert final["status"] == "shipped"


def test_build_graph_raises_clearly_without_langgraph(monkeypatch):
    if LANGGRAPH_AVAILABLE:
        pytest.skip("langgraph is installed")
    monkeypatch.setattr(graph_mod, "LANGGRAPH_AVAILABLE", False)
    with pytest.raises(RuntimeError, match="langgraph is not installed"):
        build_graph()
