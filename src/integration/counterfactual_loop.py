"""Counterfactual ingest + optimize — the WINNIIO half of the loop.

Given a filled RETURN_SCHEMA (real Blaretech, or the synthetic stand-in),
build the per-relation CIO search space and pick the best CIO per relation.
This is where the optimizer finally has something to search over.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def _read_return(return_csv: Path) -> pd.DataFrame:
    # tolerate the leading "# SYNTHETIC" comment line
    return pd.read_csv(return_csv, comment="#")


def ingest_counterfactuals(return_csv: Path) -> dict:
    """{(source, target): {cio: success_pct}} from the returned counterfactuals."""
    df = _read_return(return_csv)
    df["success_pct"] = df["sim_ho_successes"] / df["sim_ho_attempts"].clip(lower=1) * 100.0
    space: dict = {}
    for (src, tgt), grp in df.groupby(["source_cell_id", "target_cell_id"], sort=True):
        space[(src, tgt)] = dict(zip(grp["candidate_cio_db"], grp["success_pct"].round(4)))
    return space


def optimize(space: dict, current: dict | None = None) -> pd.DataFrame:
    """Pick the argmax-success CIO per relation. `current` = {(s,t): (cio, success)}.

    Returns a before/after table with provenance.
    """
    rows = []
    for (src, tgt), options in space.items():
        best_cio = max(options, key=options.get)
        after = options[best_cio]
        if current and (src, tgt) in current:
            cur_cio, before = current[(src, tgt)]
        else:
            cur_cio, before = None, min(options.values())
        rows.append({
            "source_cell": src, "target_cell": tgt,
            "current_cio_db": cur_cio, "before_success_%": round(before, 2),
            "optimal_cio_db": best_cio, "after_success_%": round(after, 2),
            "improvement_pp": round(after - before, 2),
            "source": "counterfactual_sim",
        })
    df = pd.DataFrame(rows).sort_values(["source_cell", "target_cell"]).reset_index(drop=True)
    return df


def current_from_request(request_csv: Path) -> dict:
    """{(s,t): (current_cio, current_success)} from the original request."""
    req = pd.read_csv(request_csv).drop_duplicates(["source_cell_id", "target_cell_id"])
    return {
        (r.source_cell_id, r.target_cell_id): (float(r.current_cio_db), float(r.current_success_pct))
        for r in req.itertuples()
    }
