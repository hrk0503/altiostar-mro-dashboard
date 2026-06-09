"""Edge case tests for ship_gate.py — QA by Harshit (Phase 3 Day 2).

Focus: boundary conditions at exactly 99% HO success and 5% ping-pong,
float precision, extreme values, malformed inputs, config edge cases.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.pipeline.ship_gate import (
    check_gate_conditions,
    check_results_json,
    load_thresholds_from_config,
)


# ─────────────────────────────────────────────────────────
# 1. BOUNDARY: HO_success exactly 99%
# ─────────────────────────────────────────────────────────

class TestHOSuccessBoundary:
    """Gate requires STRICTLY > 99%. Exactly 99% must FAIL."""

    def test_exactly_99_percent_fails(self):
        """Exactly 99.0% should FAIL — not strictly greater than 99%."""
        passed, reasons = check_gate_conditions(
            ho_success_rate=99.0, pingpong_rate=1.0
        )
        assert passed is False
        assert any("99.0000%" in r for r in reasons)

    def test_just_above_99_passes(self):
        """99.0001% should PASS — strictly greater than 99%."""
        passed, reasons = check_gate_conditions(
            ho_success_rate=99.0001, pingpong_rate=1.0
        )
        assert passed is True
        assert len(reasons) == 0

    def test_just_below_99_fails(self):
        """98.9999% should FAIL."""
        passed, reasons = check_gate_conditions(
            ho_success_rate=98.9999, pingpong_rate=1.0
        )
        assert passed is False

    def test_99_point_5_passes(self):
        """99.5% should PASS."""
        passed, reasons = check_gate_conditions(
            ho_success_rate=99.5, pingpong_rate=1.0
        )
        assert passed is True

    def test_100_percent_passes(self):
        """100% (perfect) should PASS."""
        passed, reasons = check_gate_conditions(
            ho_success_rate=100.0, pingpong_rate=0.0
        )
        assert passed is True

    def test_0_percent_fails(self):
        """0% (worst case) should FAIL."""
        passed, reasons = check_gate_conditions(
            ho_success_rate=0.0, pingpong_rate=1.0
        )
        assert passed is False


# ─────────────────────────────────────────────────────────
# 2. BOUNDARY: Ping-pong exactly 5%
# ─────────────────────────────────────────────────────────

class TestPingPongBoundary:
    """Gate requires STRICTLY < 5%. Exactly 5% must FAIL."""

    def test_exactly_5_percent_fails(self):
        """Exactly 5.0% should FAIL — not strictly less than 5%."""
        passed, reasons = check_gate_conditions(
            ho_success_rate=99.5, pingpong_rate=5.0
        )
        assert passed is False
        assert any("5.0000%" in r for r in reasons)

    def test_just_below_5_passes(self):
        """4.9999% should PASS."""
        passed, reasons = check_gate_conditions(
            ho_success_rate=99.5, pingpong_rate=4.9999
        )
        assert passed is True

    def test_just_above_5_fails(self):
        """5.0001% should FAIL."""
        passed, reasons = check_gate_conditions(
            ho_success_rate=99.5, pingpong_rate=5.0001
        )
        assert passed is False

    def test_0_percent_passes(self):
        """0% ping-pong should PASS."""
        passed, reasons = check_gate_conditions(
            ho_success_rate=99.5, pingpong_rate=0.0
        )
        assert passed is True

    def test_100_percent_fails(self):
        """100% ping-pong should FAIL."""
        passed, reasons = check_gate_conditions(
            ho_success_rate=99.5, pingpong_rate=100.0
        )
        assert passed is False


# ─────────────────────────────────────────────────────────
# 3. BOTH BOUNDARIES SIMULTANEOUSLY
# ─────────────────────────────────────────────────────────

class TestBothBoundaries:
    """Test when both metrics are at boundary."""

    def test_both_at_boundary_fails(self):
        """99.0% success + 5.0% ping-pong — both fail simultaneously."""
        passed, reasons = check_gate_conditions(
            ho_success_rate=99.0, pingpong_rate=5.0
        )
        assert passed is False
        assert len(reasons) == 2  # both conditions fail

    def test_success_boundary_pingpong_ok(self):
        """99.0% success + 1.0% ping-pong — only success fails."""
        passed, reasons = check_gate_conditions(
            ho_success_rate=99.0, pingpong_rate=1.0
        )
        assert passed is False
        assert len(reasons) == 1
        assert "Handover Success Rate" in reasons[0]

    def test_success_ok_pingpong_boundary(self):
        """99.5% success + 5.0% ping-pong — only ping-pong fails."""
        passed, reasons = check_gate_conditions(
            ho_success_rate=99.5, pingpong_rate=5.0
        )
        assert passed is False
        assert len(reasons) == 1
        assert "Ping-Pong Rate" in reasons[0]

    def test_both_just_pass(self):
        """99.001% success + 4.999% ping-pong — both just pass."""
        passed, reasons = check_gate_conditions(
            ho_success_rate=99.001, pingpong_rate=4.999
        )
        assert passed is True
        assert len(reasons) == 0


# ─────────────────────────────────────────────────────────
# 4. FLOAT PRECISION
# ─────────────────────────────────────────────────────────

class TestFloatPrecision:
    """Test floating point edge cases."""

    def test_very_small_above_99(self):
        """99 + 1e-10 should PASS."""
        passed, _ = check_gate_conditions(
            ho_success_rate=99.0 + 1e-10, pingpong_rate=1.0
        )
        assert passed is True

    def test_very_small_below_5(self):
        """5 - 1e-10 should PASS."""
        passed, _ = check_gate_conditions(
            ho_success_rate=99.5, pingpong_rate=5.0 - 1e-10
        )
        assert passed is True

    def test_negative_values(self):
        """Negative HO success should FAIL, negative ping-pong should PASS."""
        passed, reasons = check_gate_conditions(
            ho_success_rate=-1.0, pingpong_rate=-1.0
        )
        assert passed is False  # HO success fails
        # ping-pong passes since -1 < 5

    def test_large_values(self):
        """Values above 100% — unusual but should handle gracefully."""
        passed, _ = check_gate_conditions(
            ho_success_rate=150.0, pingpong_rate=1.0
        )
        assert passed is True  # 150 > 99


# ─────────────────────────────────────────────────────────
# 5. CUSTOM THRESHOLDS
# ─────────────────────────────────────────────────────────

class TestCustomThresholds:
    """Test with non-default thresholds."""

    def test_lower_threshold(self):
        """90% threshold — 95% success should PASS."""
        passed, _ = check_gate_conditions(
            ho_success_rate=95.0, pingpong_rate=2.0,
            ho_success_min=90.0, ping_pong_max=3.0
        )
        assert passed is True

    def test_higher_threshold(self):
        """99.9% threshold — 99.5% success should FAIL."""
        passed, _ = check_gate_conditions(
            ho_success_rate=99.5, pingpong_rate=1.0,
            ho_success_min=99.9, ping_pong_max=5.0
        )
        assert passed is False

    def test_zero_thresholds(self):
        """0% thresholds — any positive should pass success, any positive should fail ping-pong."""
        passed, reasons = check_gate_conditions(
            ho_success_rate=0.001, pingpong_rate=0.001,
            ho_success_min=0.0, ping_pong_max=0.0
        )
        assert passed is False  # ping-pong 0.001 >= 0.0


# ─────────────────────────────────────────────────────────
# 6. CONFIG LOADING EDGE CASES
# ─────────────────────────────────────────────────────────

class TestConfigEdgeCases:
    """Test config loading edge cases."""

    def test_config_with_exactly_1_point_0(self, tmp_path):
        """Config value 1.0 — should convert to 100.0%."""
        config = tmp_path / "config.yaml"
        config.write_text(
            "ship_gate:\n  ho_success_rate_min: 1.0\n  ping_pong_rate_max: 0.01\n"
        )
        success, pingpong = load_thresholds_from_config(config)
        assert success == 100.0
        assert pingpong == 1.0

    def test_config_missing_ship_gate_section(self, tmp_path):
        """Config with no ship_gate section — should use defaults."""
        config = tmp_path / "config.yaml"
        config.write_text("reward:\n  version: v2\n")
        success, pingpong = load_thresholds_from_config(config)
        assert success == 99.0  # 0.99 * 100
        assert pingpong == 5.0  # 0.05 * 100

    def test_config_partial_thresholds(self, tmp_path):
        """Config with only one threshold — other should use default."""
        config = tmp_path / "config.yaml"
        config.write_text(
            "ship_gate:\n  ho_success_rate_min: 0.95\n"
        )
        success, pingpong = load_thresholds_from_config(config)
        assert success == 95.0
        assert pingpong == 5.0  # default 0.05 * 100

    def test_config_percentage_format(self, tmp_path):
        """Config with percentage values (>1.0) — should NOT multiply by 100."""
        config = tmp_path / "config.yaml"
        config.write_text(
            "ship_gate:\n  ho_success_rate_min: 99.5\n  ping_pong_rate_max: 3.0\n"
        )
        success, pingpong = load_thresholds_from_config(config)
        assert success == 99.5
        assert pingpong == 3.0


# ─────────────────────────────────────────────────────────
# 7. JSON EDGE CASES
# ─────────────────────────────────────────────────────────

class TestJsonEdgeCases:
    """Test results JSON handling edge cases."""

    def test_exactly_99_in_json_fails(self, tmp_path):
        """THE key test: JSON with exactly 99.0% HO success should FAIL gate."""
        result_file = tmp_path / "experiment_edge.json"
        data = {
            "experiment": "v2_baseline",
            "evaluation": {
                "ho_success_rate": 99.0,
                "pingpong_rate": 1.0
            }
        }
        result_file.write_text(json.dumps(data))
        report = check_results_json(result_file)
        assert report["passed"] is False

    def test_nonexistent_file(self, tmp_path):
        """Non-existent file should return error, not crash."""
        report = check_results_json(tmp_path / "nonexistent.json")
        assert report["passed"] is False
        assert "error" in report or len(report.get("reasons", [])) > 0

    def test_invalid_json(self, tmp_path):
        """Malformed JSON should return error, not crash."""
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("{invalid json content")
        report = check_results_json(bad_file)
        assert report["passed"] is False

    def test_empty_json(self, tmp_path):
        """Empty JSON object should FAIL gracefully."""
        empty_file = tmp_path / "empty.json"
        empty_file.write_text("{}")
        report = check_results_json(empty_file)
        assert report["passed"] is False

    def test_sweep_with_error_experiment(self, tmp_path):
        """Sweep containing an errored experiment should FAIL overall."""
        sweep_file = tmp_path / "sweep.json"
        data = {
            "experiments": [
                {
                    "experiment": "v2_baseline",
                    "evaluation": {"ho_success_rate": 99.5, "pingpong_rate": 1.0}
                },
                {
                    "experiment": "v2_rush_hour",
                    "error": "Training diverged"
                }
            ]
        }
        sweep_file.write_text(json.dumps(data))
        report = check_results_json(sweep_file)
        assert report["passed"] is False
        assert report["runs"][0]["passed"] is True
        assert report["runs"][1]["passed"] is False

    def test_sweep_all_pass(self, tmp_path):
        """Sweep where all experiments pass."""
        sweep_file = tmp_path / "sweep.json"
        data = {
            "experiments": [
                {"experiment": "v2_baseline", "evaluation": {"ho_success_rate": 99.5, "pingpong_rate": 1.0}},
                {"experiment": "v2_rush", "evaluation": {"ho_success_rate": 99.9, "pingpong_rate": 0.5}},
            ]
        }
        sweep_file.write_text(json.dumps(data))
        report = check_results_json(sweep_file)
        assert report["passed"] is True

    def test_missing_pingpong_defaults_to_100(self, tmp_path):
        """Missing pingpong_rate in eval should default to 100 and FAIL."""
        result_file = tmp_path / "experiment_no_pp.json"
        data = {
            "experiment": "v2_baseline",
            "evaluation": {"ho_success_rate": 99.5}
        }
        result_file.write_text(json.dumps(data))
        report = check_results_json(result_file)
        assert report["passed"] is False  # pingpong defaults to 100

    def test_missing_ho_success_defaults_to_0(self, tmp_path):
        """Missing ho_success_rate in eval should default to 0 and FAIL."""
        result_file = tmp_path / "experiment_no_ho.json"
        data = {
            "experiment": "v2_baseline",
            "evaluation": {"pingpong_rate": 1.0}
        }
        result_file.write_text(json.dumps(data))
        report = check_results_json(result_file)
        assert report["passed"] is False  # ho_success defaults to 0
