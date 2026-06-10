#!/usr/bin/env python3
"""AltioStar MRO Ship Gate Validator.

Verifies if RL experiment results satisfy target gate conditions:
- Handover Success Rate > 99%
- Ping-Pong Rate < 5%
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

# ANSI Color formatting support
try:
    import colorama
    colorama.init()
    GREEN = "\033[92m"
    RED = "\033[91m"
    RESET = "\033[0m"
    BOLD = "\033[1m"
except ImportError:
    GREEN = ""
    RED = ""
    RESET = ""
    BOLD = ""


def check_gate_conditions(
    ho_success_rate: float,
    pingpong_rate: float,
    ho_success_min: float = 99.0,
    ping_pong_max: float = 5.0,
) -> tuple[bool, list[str]]:
    """Check if metrics satisfy the gate conditions.

    Returns
    -------
    tuple[bool, list[str]]
        - passed: True if all conditions are satisfied, else False.
        - reasons: List of failure descriptions if any.
    """
    reasons = []
    # ho_success_rate must be > ho_success_min (specifically > 99%)
    if ho_success_rate <= ho_success_min:
        reasons.append(
            f"Handover Success Rate {ho_success_rate:.4f}% is not strictly greater than "
            f"required minimum {ho_success_min}%"
        )

    # pingpong_rate must be < ping_pong_max (specifically < 5%)
    if pingpong_rate >= ping_pong_max:
        reasons.append(
            f"Ping-Pong Rate {pingpong_rate:.4f}% is not strictly less than "
            f"required maximum {ping_pong_max}%"
        )

    return len(reasons) == 0, reasons


def load_thresholds_from_config(config_path: Path | str) -> tuple[float, float]:
    """Load ho_success_min and ping_pong_max from a YAML configuration file.

    If the thresholds are defined as fractions (e.g. 0.99 or 0.05), they are
    converted to percentages (e.g. 99.0% and 5.0%).
    """
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    gate_config = config.get("ship_gate", {})
    success_val = gate_config.get("ho_success_rate_min", 0.99)
    pingpong_val = gate_config.get("ping_pong_rate_max", 0.05)

    # Convert from fraction (<= 1.0) to percentage (<= 100.0)
    success_min = success_val * 100.0 if success_val <= 1.0 else success_val
    ping_pong_max = pingpong_val * 100.0 if pingpong_val <= 1.0 else pingpong_val

    return success_min, ping_pong_max


def check_results_json(
    json_path: Path | str,
    ho_success_min: float = 99.0,
    ping_pong_max: float = 5.0,
) -> dict[str, Any]:
    """Check if the evaluation metrics in a results JSON meet the gate conditions."""
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
    except Exception as e:
        return {
            "passed": False,
            "error": f"Failed to read/parse JSON file: {e}",
            "ho_success_rate": 0.0,
            "pingpong_rate": 100.0,
            "reasons": [f"File read error: {e}"],
        }

    # Handle compiled sweep (e.g. sweep_results.json)
    if isinstance(data, dict) and "experiments" in data:
        experiments = data["experiments"]
        all_passed = True
        runs_report = []
        for item in experiments:
            if "error" in item:
                all_passed = False
                runs_report.append({
                    "experiment": item.get("experiment", "unknown"),
                    "passed": False,
                    "reasons": [f"Experiment failed with error: {item['error']}"],
                    "ho_success_rate": 0.0,
                    "pingpong_rate": 100.0,
                })
                continue

            run_eval = item.get("evaluation", {})
            success = run_eval.get("ho_success_rate", 0.0)
            ping_pong = run_eval.get("pingpong_rate", 100.0)
            passed, reasons = check_gate_conditions(
                success, ping_pong, ho_success_min, ping_pong_max
            )
            if not passed:
                all_passed = False
            runs_report.append({
                "experiment": item.get("experiment", "unknown"),
                "passed": passed,
                "reasons": reasons,
                "ho_success_rate": success,
                "pingpong_rate": ping_pong,
            })
        return {
            "passed": all_passed,
            "is_sweep": True,
            "runs": runs_report,
            "ho_success_min": ho_success_min,
            "ping_pong_max": ping_pong_max,
        }

    # Handle single experiment result JSON
    eval_section = data.get("evaluation")
    if not eval_section:
        return {
            "passed": False,
            "error": "Missing 'evaluation' section in JSON",
            "ho_success_rate": 0.0,
            "pingpong_rate": 100.0,
            "reasons": ["Missing evaluation metrics section"],
        }

    success = eval_section.get("ho_success_rate", 0.0)
    ping_pong = eval_section.get("pingpong_rate", 100.0)
    passed, reasons = check_gate_conditions(
        success, ping_pong, ho_success_min, ping_pong_max
    )

    return {
        "passed": passed,
        "is_sweep": False,
        "experiment": data.get("experiment", "unknown"),
        "ho_success_rate": success,
        "pingpong_rate": ping_pong,
        "ho_success_min": ho_success_min,
        "ping_pong_max": ping_pong_max,
        "reasons": reasons,
    }


def main() -> None:
    """Main CLI entrypoint for verifying results against MRO ship gates."""
    parser = argparse.ArgumentParser(description="Verify RL experiment results against MRO ship gates.")
    parser.add_argument(
        "--results",
        type=str,
        help="Path to a single results JSON file (e.g. results/experiment_v2_baseline.json)",
    )
    parser.add_argument(
        "--results-dir",
        type=str,
        help="Path to a directory containing experiment JSON files to validate",
    )
    parser.add_argument(
        "--ho-success-min",
        type=float,
        default=99.0,
        help="Minimum Handover Success Rate threshold (default: 99.0%%)",
    )
    parser.add_argument(
        "--ping-pong-max",
        type=float,
        default=5.0,
        help="Maximum Ping-Pong Rate threshold (default: 5.0%%)",
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to default YAML config file (e.g. configs/mro_default.yaml) to load thresholds",
    )

    args = parser.parse_args()

    ho_success_min = args.ho_success_min
    ping_pong_max = args.ping_pong_max

    if args.config:
        try:
            ho_success_min, ping_pong_max = load_thresholds_from_config(args.config)
            print(f"Loaded thresholds from config {args.config}:")
            print(f"  - HO Success Rate > {ho_success_min}%")
            print(f"  - Ping-Pong Rate < {ping_pong_max}%")
        except Exception as e:
            print(f"{RED}Error loading config thresholds: {e}{RESET}", file=sys.stderr)
            sys.exit(1)

    if not args.results and not args.results_dir:
        print(
            f"{RED}Error: You must specify either --results or --results-dir.{RESET}",
            file=sys.stderr,
        )
        parser.print_help()
        sys.exit(1)

    all_passed = True
    files_to_check = []

    if args.results:
        files_to_check.append(Path(args.results))

    if args.results_dir:
        dir_path = Path(args.results_dir)
        if not dir_path.is_dir():
            print(f"{RED}Error: {args.results_dir} is not a valid directory.{RESET}", file=sys.stderr)
            sys.exit(1)
        # Scan for all individual experiment files, skip consolidated sweep results
        for file in dir_path.glob("experiment_*.json"):
            files_to_check.append(file)

    if not files_to_check:
        print(f"{RED}No files found matching criteria.{RESET}")
        sys.exit(1)

    print(f"\nVerifying {len(files_to_check)} results files against gate conditions...")
    print(f"Gate criteria: Handover Success > {ho_success_min}%, Ping-Pong < {ping_pong_max}%\n")

    for file in sorted(files_to_check):
        report = check_results_json(file, ho_success_min, ping_pong_max)
        if report.get("is_sweep"):
            print(f"{BOLD}Sweep File: {file.name}{RESET}")
            for run in report["runs"]:
                exp_name = run["experiment"]
                if run["passed"]:
                    print(
                        f"  [{GREEN}PASS{RESET}] {exp_name} "
                        f"(HO Success: {run['ho_success_rate']:.2f}%, Ping-Pong: {run['pingpong_rate']:.2f}%)"
                    )
                else:
                    all_passed = False
                    print(
                        f"  [{RED}FAIL{RESET}] {exp_name} "
                        f"(HO Success: {run['ho_success_rate']:.2f}%, Ping-Pong: {run['pingpong_rate']:.2f}%)"
                    )
                    for reason in run["reasons"]:
                        print(f"    - {reason}")
        else:
            exp_name = report.get("experiment", file.name)
            if report["passed"]:
                print(
                    f"[{GREEN}PASS{RESET}] {exp_name} "
                    f"(HO Success: {report['ho_success_rate']:.2f}%, Ping-Pong: {report['pingpong_rate']:.2f}%)"
                )
            else:
                all_passed = False
                print(
                    f"[{RED}FAIL{RESET}] {exp_name} "
                    f"(HO Success: {report['ho_success_rate']:.2f}%, Ping-Pong: {report['pingpong_rate']:.2f}%)"
                )
                for reason in report.get("reasons", []):
                    print(f"  - {reason}")

    print("\n" + "=" * 60)
    if all_passed:
        print(f"{BOLD}{GREEN}ALL CHECKED RUNS PASSED THE SHIP GATE CRITERIA!{RESET}")
        sys.exit(0)
    else:
        print(f"{BOLD}{RED}SOME CHECKED RUNS FAILED THE SHIP GATE CRITERIA.{RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
