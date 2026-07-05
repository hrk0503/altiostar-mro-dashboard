"""Synthetic RF return generator — a deterministic stand-in for Blaretech.

SYNTHETIC. This fabricates NOTHING about the real world; it produces an
*illustrative* counterfactual dataset so the full WINNIIO loop can be demoed
end-to-end before the real RF layer / operator data exist. Every value is a
deterministic function of the request (seed-free, so byte-reproducible).

Contract: consumes 01_counterfactual_request.csv (relation x candidate CIO)
and emits the RETURN_SCHEMA columns Blaretech would fill:
  sim_ho_attempts, sim_ho_successes, sim_ho_failures,
  sim_too_early, sim_too_late, sim_wrong_cell, sim_ping_pong
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

RETURN_COLS = [
    "source_cell_id", "target_cell_id", "candidate_cio_db",
    "sim_ho_attempts", "sim_ho_successes", "sim_ho_failures",
    "sim_too_early", "sim_too_late", "sim_wrong_cell", "sim_ping_pong",
]


def _relation_optimal_cio(source: str, target: str, candidates: list[float]) -> float:
    """Deterministic pseudo-optimal CIO for a relation (stable across runs)."""
    key = f"{source}->{target}".encode()
    idx = int(hashlib.sha256(key).hexdigest(), 16) % len(candidates)
    return float(sorted(candidates)[idx])


def _success_at(cio: float, optimal: float) -> float:
    """Illustrative, ASYMMETRIC success curve (DD hardening).

    Real HOSR-vs-CIO is not a symmetric V: too-high CIO (past optimal) triggers
    early handovers + ping-pong (gentler slope); too-low CIO triggers late
    handovers + RLF (steeper slope). We reflect that with direction-dependent
    quadratic slopes, and cap the peak at 99.0% with a residual-failure floor
    (real networks never hit 100%). Still SYNTHETIC — shape is plausible, not
    calibrated to any real cluster.
    """
    dev = cio - optimal
    if dev >= 0:      # above optimal: early-HO / ping-pong side (gentler)
        penalty = 1.6 * dev * dev + 1.0 * dev
    else:             # below optimal: late-HO / RLF side (steeper)
        penalty = 2.6 * dev * dev + 1.4 * abs(dev)
    return max(72.0, 99.0 - penalty)


def simulate_return(request: pd.DataFrame) -> pd.DataFrame:
    """Produce the filled RETURN_SCHEMA rows from a counterfactual request."""
    candidates = sorted(request["candidate_cio_db"].unique().tolist())
    rows = []
    for (src, tgt), grp in request.groupby(["source_cell_id", "target_cell_id"], sort=True):
        opt = _relation_optimal_cio(src, tgt, candidates)
        # Base attempts from the request (stable); split evenly across candidates.
        base_att = int(max(20, float(grp["ho_attempts"].iloc[0]) / max(1, len(candidates))))
        for cio in candidates:
            succ_pct = _success_at(cio, opt)
            att = base_att
            succ = int(round(att * succ_pct / 100.0))
            fail = att - succ
            # Deterministic failure split (weights sum to 1).
            too_early = int(round(fail * 0.30))
            too_late = int(round(fail * 0.35))
            wrong = fail - too_early - too_late
            ping = int(round(att * 0.01))
            rows.append({
                "source_cell_id": src, "target_cell_id": tgt,
                "candidate_cio_db": cio,
                "sim_ho_attempts": att, "sim_ho_successes": succ,
                "sim_ho_failures": fail, "sim_too_early": too_early,
                "sim_too_late": too_late, "sim_wrong_cell": max(0, wrong),
                "sim_ping_pong": ping,
            })
    out = pd.DataFrame(rows, columns=RETURN_COLS)
    return out.sort_values(["source_cell_id", "target_cell_id", "candidate_cio_db"]).reset_index(drop=True)


def generate(request_csv: Path, out_csv: Path) -> pd.DataFrame:
    req = pd.read_csv(request_csv)
    out = simulate_return(req)
    header = "# SYNTHETIC — illustrative counterfactuals (stand-in for Blaretech RF sim)\n"
    with open(out_csv, "w", encoding="utf-8", newline="") as fh:
        fh.write(header)
        out.to_csv(fh, index=False)
    return out
