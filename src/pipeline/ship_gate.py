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

# ── Defaults (in percentage units, e.g. 99.0 means 99%) ──────────────────────
DEFAULT_HO_SUCCESS_MIN = 99.0
DEFAULT_PING_PONG_MAX = 5.0


# ── Core gate logic ───────────────────────────────────────────────────────────

def check_gate_conditions(
    ho_success_rate: float,
    pingpong_rate: float,
    ho_success_min: float = DEFAULT_HO_SUCCESS_MIN,
    ping_pong_max: float = DEFAULT_PING_PONG_MAX,
) -> tuple[bool, list[str]]:
    """Check whether KPI values pass the ship gate.

    Both thresholds are STRICT:
      - ho_success_rate must be STRICTLY > ho_success_min
      - pingpong_rate   must be STRICTLY < ping_pong_max

    Returns
    -------
    passed  : True if all conditions met
    reasons : list of failure messages (empty when passed)
    """
    reasons: list[str] = []

    if not ho_success_rate > ho_success_min:
        reasons.append(
            f"Handover Success Rate {ho_success_rate:.4f}% "
            f"is not > {ho_success_min:.4f}% (got {ho_success_rate:.4f}%)"
        )

    if not pingpong_rate < ping_pong_max:
        reasons.append(
            f"Ping-Pong Rate {pingpong_rate:.4f}% "
            f"is not < {ping_pong_max:.4f}% (got {pingpong_rate:.4f}%)"
        )

    return len(reasons) == 0, reasons


# ── Config loader ─────────────────────────────────────────────────────────────

def load_thresholds_from_config(
    config_path: Path | str,
) -> tuple[float, float]:
    """Load HO success and ping-pong thresholds from a YAML config file.

    Expects structure:
        ship_gate:
          ho_success_rate_min: 0.99   # fraction OR percentage
          ping_pong_rate_max:  0.05

    Values <= 1.0 are treated as fractions and multiplied by 100.
    Values >  1.0 are treated as already in percentage units.

    Missing ship_gate section → defaults (99.0, 5.0).
    Missing individual key   → its default.
    """
    try:
        text = Path(config_path).read_text()
        cfg = yaml.safe_load(text) or {}
    except Exception:
        return DEFAULT_HO_SUCCESS_MIN, DEFAULT_PING_PONG_MAX

    gate = cfg.get("ship_gate", {}) or {}

    raw_ho = gate.get("ho_success_rate_min", None)
    raw_pp = gate.get("ping_pong_rate_max", None)

    def _to_pct(value: float | None, default: float) -> float:
        if value is None:
            return default
        # fraction format (<=1.0) → multiply by 100
        if value <= 1.0:
            return float(value) * 100.0
        return float(value)

    ho_success = _to_pct(raw_ho, DEFAULT_HO_SUCCESS_MIN)
    ping_pong  = _to_pct(raw_pp, DEFAULT_PING_PONG_MAX)

    return ho_success, ping_pong


# ── JSON results checker ──────────────────────────────────────────────────────

def _check_single(
    eval_block: dict[str, Any] | None,
    experiment_name: str = "",
    ho_success_min: float = DEFAULT_HO_SUCCESS_MIN,
    ping_pong_max: float = DEFAULT_PING_PONG_MAX,
) -> dict:
    """Check a single evaluation block."""
    if eval_block is None:
        return {
            "experiment": experiment_name,
            "passed": False,
            "reasons": ["No evaluation block found"],
        }

    ho  = eval_block.get("ho_success_rate",  0.0)   # missing → 0 → FAIL
    pp  = eval_block.get("pingpong_rate",  100.0)    # missing → 100 → FAIL

    passed, reasons = check_gate_conditions(ho, pp, ho_success_min, ping_pong_max)
    return {
        "experiment": experiment_name,
        "passed": passed,
        "reasons": reasons,
        "ho_success_rate": ho,
        "pingpong_rate": pp,
    }


def check_results_json(
    results_path: Path | str,
    ho_success_min: float = DEFAULT_HO_SUCCESS_MIN,
    ping_pong_max: float = DEFAULT_PING_PONG_MAX,
) -> dict:
    """Check a results JSON file against gate conditions.

    Handles:
      - Single experiment:  { "experiment": "...", "evaluation": {...} }
      - Sweep:              { "experiments": [ {...}, ... ] }
      - Missing file        → passed=False
      - Malformed JSON      → passed=False
      - Experiment with "error" key → that run fails

    Returns a report dict with at minimum { "passed": bool }.
    """
    path = Path(results_path)

    # ── file not found ────────────────────────────────────────────────────────
    if not path.exists():
        return {"passed": False, "reasons": [f"File not found: {path}"]}

    # ── parse JSON ────────────────────────────────────────────────────────────
    try:
        data = json.loads(path.read_text())
    except Exception as exc:
        return {"passed": False, "error": str(exc), "reasons": [f"JSON parse error: {exc}"]}

    if not isinstance(data, dict):
        return {"passed": False, "reasons": ["JSON root is not an object"]}

    # ── sweep format ─────────────────────────────────────────────────────────
    if "experiments" in data:
        runs = []
        for exp in data["experiments"]:
            name = exp.get("experiment", "unknown")
            if "error" in exp:
                runs.append({
                    "experiment": name,
                    "passed": False,
                    "reasons": [f"Training error: {exp['error']}"],
                })
            else:
                runs.append(_check_single(exp.get("evaluation"), name, ho_success_min, ping_pong_max))

        overall = all(r["passed"] for r in runs)
        return {"passed": overall, "runs": runs, "is_sweep": True}

    # ── single experiment format ──────────────────────────────────────────────
    if not data:
        return {"passed": False, "reasons": ["Empty JSON object"]}

    name   = data.get("experiment", "")
    report = _check_single(data.get("evaluation"), name, ho_success_min, ping_pong_max)
    report["is_sweep"] = False
    return report


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
        default=DEFAULT_HO_SUCCESS_MIN,
        help="Minimum Handover Success Rate threshold (default: 99.0%%)",
    )
    parser.add_argument(
        "--ping-pong-max",
        type=float,
        default=DEFAULT_PING_PONG_MAX,
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
            for run in report.get("runs", []):
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
                    for reason in run.get("reasons", []):
                        print(f"    - {reason}")
        else:
            exp_name = report.get("experiment", file.name)
            if report["passed"]:
                print(
                    f"[{GREEN}PASS{RESET}] {exp_name} "
                    f"(HO Success: {report.get('ho_success_rate', 0.0):.2f}%, Ping-Pong: {report.get('pingpong_rate', 100.0):.2f}%)"
                )
            else:
                all_passed = False
                print(
                    f"[{RED}FAIL{RESET}] {exp_name} "
                    f"(HO Success: {report.get('ho_success_rate', 0.0):.2f}%, Ping-Pong: {report.get('pingpong_rate', 100.0):.2f}%)"
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
