"""ship_gate.py — Phase 3 Ship Gate logic.

Checks whether experiment results meet Gate G4 KPI thresholds:
  - HO Success Rate  > 99%  (strictly greater)
  - Ping-Pong Rate   < 5%   (strictly less)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

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
    config_path: Path,
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

def _check_single(eval_block: dict[str, Any] | None, experiment_name: str = "") -> dict:
    """Check a single evaluation block."""
    if eval_block is None:
        return {
            "experiment": experiment_name,
            "passed": False,
            "reasons": ["No evaluation block found"],
        }

    ho  = eval_block.get("ho_success_rate",  0.0)   # missing → 0 → FAIL
    pp  = eval_block.get("pingpong_rate",  100.0)    # missing → 100 → FAIL

    passed, reasons = check_gate_conditions(ho, pp)
    return {
        "experiment": experiment_name,
        "passed": passed,
        "reasons": reasons,
        "ho_success_rate": ho,
        "pingpong_rate": pp,
    }


def check_results_json(results_path: Path) -> dict:
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
                runs.append(_check_single(exp.get("evaluation"), name))

        overall = all(r["passed"] for r in runs)
        return {"passed": overall, "runs": runs}

    # ── single experiment format ──────────────────────────────────────────────
    if not data:
        return {"passed": False, "reasons": ["Empty JSON object"]}

    name   = data.get("experiment", "")
    report = _check_single(data.get("evaluation"), name)
    return report