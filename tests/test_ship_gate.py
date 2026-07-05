from __future__ import annotations

import json

from src.pipeline.ship_gate import (
    check_gate_conditions,
    check_results_json,
    load_thresholds_from_config,
)


def test_check_gate_conditions():
    # Pass case
    passed, reasons = check_gate_conditions(ho_success_rate=99.5, pingpong_rate=1.2)
    assert passed is True
    assert len(reasons) == 0

    # Fail success rate case
    passed, reasons = check_gate_conditions(ho_success_rate=98.5, pingpong_rate=1.2)
    assert passed is False
    assert any("Handover Success Rate" in r for r in reasons)

    # Fail pingpong rate case
    passed, reasons = check_gate_conditions(ho_success_rate=99.5, pingpong_rate=6.0)
    assert passed is False
    assert any("Ping-Pong Rate" in r for r in reasons)

    # Custom thresholds pass
    passed, reasons = check_gate_conditions(
        ho_success_rate=95.0, pingpong_rate=2.0, ho_success_min=90.0, ping_pong_max=3.0
    )
    assert passed is True


def test_load_thresholds_from_config(tmp_path):
    # Test loading fractional config (0.99 and 0.05)
    config_file = tmp_path / "test_config_fractional.yaml"
    config_content = """
ship_gate:
  ho_success_rate_min: 0.99
  ping_pong_rate_max: 0.005
"""
    config_file.write_text(config_content)
    success, pingpong = load_thresholds_from_config(config_file)
    assert success == 99.0
    assert pingpong == 0.5

    # Test loading percentage config (95.0 and 2.0)
    config_file_pct = tmp_path / "test_config_percentage.yaml"
    config_content_pct = """
ship_gate:
  ho_success_rate_min: 95.0
  ping_pong_rate_max: 2.0
"""
    config_file_pct.write_text(config_content_pct)
    success, pingpong = load_thresholds_from_config(config_file_pct)
    assert success == 95.0
    assert pingpong == 2.0


def test_check_results_json_single(tmp_path):
    # Valid single run passing
    result_file = tmp_path / "experiment_pass.json"
    data = {
        "experiment": "v2_baseline",
        "evaluation": {
            "ho_success_rate": 99.5,
            "pingpong_rate": 1.2
        }
    }
    result_file.write_text(json.dumps(data))
    report = check_results_json(result_file)
    assert report["passed"] is True
    assert report["is_sweep"] is False
    assert report["ho_success_rate"] == 99.5
    assert report["pingpong_rate"] == 1.2

    # Valid single run failing
    result_file_fail = tmp_path / "experiment_fail.json"
    data_fail = {
        "experiment": "v2_baseline",
        "evaluation": {
            "ho_success_rate": 95.0,
            "pingpong_rate": 6.0
        }
    }
    result_file_fail.write_text(json.dumps(data_fail))
    report_fail = check_results_json(result_file_fail)
    assert report_fail["passed"] is False
    assert len(report_fail["reasons"]) == 2

    # Missing evaluation section
    result_file_missing = tmp_path / "experiment_missing.json"
    data_missing = {
        "experiment": "v2_baseline"
    }
    result_file_missing.write_text(json.dumps(data_missing))
    report_missing = check_results_json(result_file_missing)
    assert report_missing["passed"] is False
    assert "reasons" in report_missing


def test_check_results_json_sweep(tmp_path):
    # Valid sweep passing
    sweep_file = tmp_path / "sweep_results.json"
    data = {
        "experiments": [
            {
                "experiment": "v2_baseline",
                "evaluation": {
                    "ho_success_rate": 99.5,
                    "pingpong_rate": 1.2
                }
            },
            {
                "experiment": "v2_rush_hour",
                "evaluation": {
                    "ho_success_rate": 99.9,
                    "pingpong_rate": 0.5
                }
            }
        ]
    }
    sweep_file.write_text(json.dumps(data))
    report = check_results_json(sweep_file)
    assert report["passed"] is True
    assert report["is_sweep"] is True
    assert len(report["runs"]) == 2
    assert report["runs"][0]["passed"] is True
    assert report["runs"][1]["passed"] is True

    # Sweep failing (one run fails)
    data_fail = {
        "experiments": [
            {
                "experiment": "v2_baseline",
                "evaluation": {
                    "ho_success_rate": 99.5,
                    "pingpong_rate": 1.2
                }
            },
            {
                "experiment": "v2_rush_hour",
                "evaluation": {
                    "ho_success_rate": 95.0,
                    "pingpong_rate": 0.5
                }
            }
        ]
    }
    sweep_file.write_text(json.dumps(data_fail))
    report_fail = check_results_json(sweep_file)
    assert report_fail["passed"] is False
    assert report_fail["runs"][0]["passed"] is True
    assert report_fail["runs"][1]["passed"] is False
