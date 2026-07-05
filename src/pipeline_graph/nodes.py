"""Pipeline nodes — thin, honest wrappers around the existing MRO functions.

Each node is a pure ``MROState -> MROState`` function. It calls the REAL
implementation that already lives in this repo (loader / validator /
schema_mapper / optimize_cio / MROEnv / ship_gate) and copies the result into
the typed state. No node trains anything, and no node re-implements logic that
exists elsewhere — read each docstring for exactly what it does.

Honesty note for the optimize node specifically: it performs *data-driven CIO
optimization (not RL)*. It calls ``scripts.optimize_cio.find_optimal_cios``,
which is an exhaustive per-relation search over the PM data. No policy network
is trained; ``model.learn()`` is never called. See ``docs/METHODOLOGY.md`` on
the ``chore/reset-and-onboarding`` branch for the full description.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from src.agents.spectrum import validate_cio_change
from src.env.mro_env import MROEnv
from src.pipeline import validator
from src.pipeline.loader import DATA_DIR
from src.pipeline.schema_mapper import infer_schema
from src.pipeline.ship_gate import check_gate_conditions
from src.pipeline_graph.state import MROState

# ``scripts`` is a top-level namespace package (no src-layout guarantee), so make
# sure the project root is importable before importing from it. This mirrors the
# path handling in scripts/optimize_cio.py itself.
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.optimize_cio import evaluate_with_optimal_cios, find_optimal_cios  # noqa: E402

# Default synthetic input: the Shibuya/Tokyo cell-level PM export. This CSV has
# validator range-rules defined and schema_mapper recognises it as a PMRecord.
DEFAULT_CSV = DATA_DIR / "pm_data_april2026.csv"


def _append_error(state: MROState, message: str) -> None:
    errors = list(state.get("errors", []))
    errors.append(message)
    state["errors"] = errors


# ── ingest ────────────────────────────────────────────────────────────────────

def node_ingest(state: MROState) -> MROState:
    """Ingest node: read the CSV shape and detect its schema.

    Thin wrapper. Resolves ``data_path`` (default: the synthetic Shibuya PM
    CSV), reads it with pandas to record row/column counts, and calls
    ``schema_mapper.infer_schema`` to identify which known model it matches.
    Performs NO transformation and NO cleaning.
    """
    path = Path(state.get("data_path") or DEFAULT_CSV)
    state["data_path"] = str(path)
    state["csv_name"] = path.name

    if not path.exists():
        _append_error(state, f"ingest: file not found: {path}")
        state["n_rows"] = 0
        state["n_cols"] = 0
        state["schema_matched_model"] = None
        return state

    df = pd.read_csv(path)
    state["n_rows"] = int(len(df))
    state["n_cols"] = int(df.shape[1])
    match = infer_schema(path)
    state["schema_matched_model"] = match.matched_model
    return state


# ── validate ──────────────────────────────────────────────────────────────────

def node_validate(state: MROState) -> MROState:
    """Validate node: run data-quality checks via ``validator.validate_csv``.

    Thin wrapper around the existing validator (null / range / type / duplicate
    checks). Range rules only exist for the four canonical CSVs; for other files
    the null/duplicate checks still apply. Writes ``validation_passed`` and a
    compact ``validation_report`` into the state.
    """
    path = Path(state["data_path"])
    if not path.exists():
        state["validation_passed"] = False
        state["validation_report"] = {"error": f"file not found: {path}"}
        _append_error(state, "validate: input file missing")
        return state

    result = validator.validate_csv(path.name, path)
    state["validation_passed"] = bool(result.passed)
    state["validation_report"] = {
        "csv_name": result.csv_name,
        "total_rows": result.total_rows,
        "null_counts": result.null_counts,
        "range_violations": result.range_violations,
        "type_mismatches": result.type_mismatches,
        "duplicate_rows": result.duplicate_rows,
    }
    if not result.passed:
        _append_error(
            state,
            f"validate: {result.csv_name} failed data-quality checks",
        )
    return state


# ── optimize_cio ────────────────────────────────────────────────────────────

def node_optimize_cio(state: MROState, *, env: MROEnv | None = None, seed: int = 42) -> MROState:
    """Optimize node: DATA-DRIVEN CIO OPTIMIZATION (NOT RL).

    Builds an ``MROEnv`` (relation-level PM data) and calls
    ``scripts.optimize_cio.find_optimal_cios`` — an exhaustive per-relation
    search that picks, for each source→target relation, the CIO value that
    maximises handover success in the PM data. This is a search, not learning:
    no gradients, no episodes of training, no ``model.learn()``.

    Each recommended CIO is then passed through the 3GPP rules engine
    (``spectrum.validate_cio_change``) so out-of-spec or aggressive changes are
    surfaced before anything ships.
    """
    if env is None:
        env = MROEnv()
        env.reset(seed=seed)

    result = find_optimal_cios(env)
    optimal = result["optimal_cios"]
    improvements = result["improvements"]

    state["n_relations"] = int(env.n_relations)
    state["optimal_cios"] = [float(x) for x in optimal]
    state["improvements"] = improvements

    # 3GPP sign-off pass over every recommended change (A2 ↔ A3 bridge).
    violations: list[str] = []
    warnings: list[str] = []
    for imp in improvements:
        src, tgt = imp["relation"].split("->", 1)
        verdict = validate_cio_change(
            src, tgt, imp["initial_cio"], imp["optimal_cio"]
        )
        violations.extend(f"{imp['relation']}: {v}" for v in verdict.violations)
        warnings.extend(f"{imp['relation']}: {w}" for w in verdict.warnings)
    state["spectrum_review"] = {
        "n_checked": len(improvements),
        "n_violations": len(violations),
        "n_warnings": len(warnings),
        "violations": violations[:50],
        "warnings": warnings[:50],
    }
    return state


# ── evaluate ──────────────────────────────────────────────────────────────────

def node_evaluate(
    state: MROState,
    *,
    env: MROEnv | None = None,
    n_episodes: int = 3,
    seed: int = 42,
) -> MROState:
    """Evaluate node: deterministic roll-out of the target-CIO policy.

    Calls ``scripts.optimize_cio.evaluate_with_optimal_cios``, which steps the
    ``MROEnv`` for ``n_episodes`` using a fixed policy that drives each relation
    toward its recommended CIO, and records HOSR / ping-pong / failure rates.
    This is a deterministic evaluation of a *rule*, not a rollout of a learned
    RL policy.
    """
    import numpy as np

    if env is None:
        env = MROEnv()
        env.reset(seed=seed)

    optimal = np.array(state.get("optimal_cios", []), dtype=np.float32)
    metrics = evaluate_with_optimal_cios(env, optimal, n_episodes=n_episodes, seed=seed)
    state["eval_metrics"] = metrics
    return state


# ── ship_gate ─────────────────────────────────────────────────────────────────

def node_ship_gate(state: MROState) -> MROState:
    """Ship-gate node: thin wrapper around ``ship_gate.check_gate_conditions``.

    Reads HOSR and ping-pong from ``eval_metrics`` and applies the strict gate
    (HOSR > 99%, ping-pong < 5%). Writes ``gate_passed`` and ``gate_reasons``.
    """
    metrics = state.get("eval_metrics", {})
    ho = float(metrics.get("ho_success_rate", 0.0))
    pp = float(metrics.get("pingpong_rate", 100.0))
    passed, reasons = check_gate_conditions(ho, pp)
    state["gate_passed"] = passed
    state["gate_reasons"] = reasons
    return state


# ── terminal nodes ────────────────────────────────────────────────────────────

def node_report(state: MROState) -> MROState:
    """Report node (terminal): assemble a success summary. No side effects."""
    metrics = state.get("eval_metrics", {})
    state["status"] = "shipped"
    state["summary"] = {
        "status": "shipped",
        "csv_name": state.get("csv_name"),
        "n_relations": state.get("n_relations"),
        "ho_success_rate": metrics.get("ho_success_rate"),
        "pingpong_rate": metrics.get("pingpong_rate"),
        "gate_passed": state.get("gate_passed"),
        "spectrum_review": state.get("spectrum_review"),
        "method": "data-driven CIO optimization (exhaustive per-relation search, not RL)",
    }
    return state


def node_needs_review(state: MROState) -> MROState:
    """Needs-review node (terminal): gate failed → surface reasons for a human.

    Reached when the ship gate does not pass. Bundles the gate reasons and any
    3GPP spectrum warnings so a RAN engineer can review before any deployment.
    """
    state["status"] = "needs_review"
    state["summary"] = {
        "status": "needs_review",
        "csv_name": state.get("csv_name"),
        "gate_reasons": state.get("gate_reasons", []),
        "spectrum_review": state.get("spectrum_review"),
        "note": "Ship gate failed; human RAN-expert review required before deploy.",
    }
    return state


# ── routing (pure conditional-edge functions) ─────────────────────────────────

def route_after_validate(state: MROState) -> str:
    """Conditional edge after validate: 'optimize_cio' if passed, else 'stop'."""
    return "optimize_cio" if state.get("validation_passed") else "stop"


def route_after_ship_gate(state: MROState) -> str:
    """Conditional edge after ship_gate: 'report' if passed, else 'needs_review'."""
    return "report" if state.get("gate_passed") else "needs_review"
