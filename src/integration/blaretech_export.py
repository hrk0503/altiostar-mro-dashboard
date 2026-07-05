"""WINNIIO → Blaretech export: the counterfactual CIO request.

THE PROBLEM THIS SOLVES (see docs/COUNTERFACTUAL.md for the ELI10 version)
-------------------------------------------------------------------------
Operator PM data records each relation at ONE CIO value — the one it was
actually running. To recommend a *better* CIO, the optimizer needs to know
what handovers *would* do at other CIO values. Raw PM data cannot answer
that (it never ran those settings). So the intelligence layer STOPS here and
hands off to the RF/reality layer (Blaretech / Sionna), which can simulate
the counterfactual outcomes. Their result comes back and the optimizer
resumes with a real search space.

    WINNIIO (this module)                 BLARETECH / RF layer
    ─────────────────────                 ────────────────────
    ingest operator PM                    receive request package
    find failing relations                for each (relation, candidate CIO):
    attach geometry                         run RF/propagation/mobility sim
    list candidate CIOs        ──────►      predict HO attempts/success/fail
    EXPORT request package                return counterfactual PM
                               ◄──────    (RETURN_SCHEMA)
    re-ingest → optimize → recommend

This module produces the request package. The return package (same relations,
one row per candidate CIO, with simulated counters) is re-ingested by the
optimizer to run a genuine search.

Everything here is computed from real input data — no fabricated metrics.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

# The CIO values the optimizer wants evaluated per relation (dB).
# This is the search grid; Blaretech simulates handover outcomes at each.
DEFAULT_CIO_CANDIDATES = [-6, -4, -2, -1, 0, 1, 2, 4, 6]


def _relation_success(pm: pd.DataFrame) -> pd.DataFrame:
    """Attempt-weighted current HO success % per source→target relation."""
    g = pm.groupby(["source_cell_id", "target_cell_id"], as_index=False).agg(
        ho_attempts=("ho_attempts", "sum"),
        ho_successes=("ho_successes", "sum"),
        ho_failures=("ho_failures", "sum"),
        ping_pong=("ping_pong", "sum"),
        cio_db=("cio_db", "last"),
    )
    g["current_success_pct"] = (g["ho_successes"] / g["ho_attempts"].clip(lower=1) * 100).round(2)
    return g


def build_export(
    data_dir: Path,
    out_dir: Path,
    cio_candidates: list[int] | None = None,
    failure_threshold_pct: float = 99.0,
) -> dict:
    """Build the Blaretech counterfactual request package.

    Parameters
    ----------
    data_dir : dir with site_database.csv, neighbor_relations.csv,
               pm_data_relation_level.csv
    out_dir  : where to write the package
    cio_candidates : CIO values (dB) to request simulation for
    failure_threshold_pct : relations below this current success % are
               flagged 'priority' (the ones worth optimizing)

    Returns a manifest dict (also written as manifest.json).
    """
    cio_candidates = cio_candidates or DEFAULT_CIO_CANDIDATES
    out_dir.mkdir(parents=True, exist_ok=True)

    sites = pd.read_csv(data_dir / "site_database.csv")
    rels = pd.read_csv(data_dir / "neighbor_relations.csv")
    pm = pd.read_csv(data_dir / "pm_data_relation_level.csv")

    rel_success = _relation_success(pm)

    site_geo = sites[["cell_id", "latitude", "longitude", "azimuth_deg",
                      "antenna_height_m", "total_tilt_deg", "frequency_band",
                      "clutter_type"]].copy()

    # Join relations to source + target geometry and current success.
    df = rels.rename(columns={"serving_cell": "source_cell_id",
                              "neighbor_cell": "target_cell_id"}).merge(
        site_geo.add_prefix("src_").rename(columns={"src_cell_id": "source_cell_id"}),
        on="source_cell_id", how="left").merge(
        site_geo.add_prefix("tgt_").rename(columns={"tgt_cell_id": "target_cell_id"}),
        on="target_cell_id", how="left").merge(
        rel_success[["source_cell_id", "target_cell_id", "current_success_pct",
                     "ho_attempts"]],
        on=["source_cell_id", "target_cell_id"], how="left")

    df["current_cio_db"] = df["cell_individual_offset_dB"]
    df["priority"] = df["current_success_pct"] < failure_threshold_pct

    # ── 01: counterfactual request — one row per (relation × candidate CIO) ──
    keep = ["source_cell_id", "target_cell_id", "current_cio_db",
            "current_success_pct", "ho_attempts", "distance_m",
            "src_latitude", "src_longitude", "src_azimuth_deg",
            "src_antenna_height_m", "src_total_tilt_deg", "src_frequency_band",
            "src_clutter_type", "tgt_latitude", "tgt_longitude",
            "tgt_azimuth_deg", "priority"]
    base = df[keep].copy()
    req = base.loc[base.index.repeat(len(cio_candidates))].copy()
    req["candidate_cio_db"] = cio_candidates * len(base)
    req = req.sort_values(["priority", "source_cell_id", "target_cell_id",
                           "candidate_cio_db"], ascending=[False, True, True, True])
    req_path = out_dir / "01_counterfactual_request.csv"
    req.to_csv(req_path, index=False)

    # ── 02: georeferenced sites (points, WGS84) for RF ingestion ──
    site_features = [{
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [float(r.longitude), float(r.latitude)]},
        "properties": {"cell_id": r.cell_id, "azimuth_deg": float(r.azimuth_deg),
                       "height_m": float(r.antenna_height_m),
                       "tilt_deg": float(r.total_tilt_deg),
                       "band": r.frequency_band, "clutter": r.clutter_type},
    } for r in sites.itertuples()]
    (out_dir / "02_sites.geojson").write_text(json.dumps(
        {"type": "FeatureCollection", "features": site_features}, indent=1))

    # ── 03: georeferenced relation lines (source→target), priority flagged ──
    rel_features = []
    for r in df.itertuples():
        if pd.isna(r.src_latitude) or pd.isna(r.tgt_latitude):
            continue
        rel_features.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": [
                [float(r.src_longitude), float(r.src_latitude)],
                [float(r.tgt_longitude), float(r.tgt_latitude)]]},
            "properties": {"source": r.source_cell_id, "target": r.target_cell_id,
                           "current_cio_db": float(r.current_cio_db),
                           "current_success_pct": (None if pd.isna(r.current_success_pct)
                                                   else float(r.current_success_pct)),
                           "priority": bool(r.priority)},
        })
    (out_dir / "03_relations.geojson").write_text(json.dumps(
        {"type": "FeatureCollection", "features": rel_features}, indent=1))

    # ── RETURN schema template — the columns Blaretech fills and sends back ──
    ret_cols = ["source_cell_id", "target_cell_id", "candidate_cio_db",
                "sim_ho_attempts", "sim_ho_successes", "sim_ho_failures",
                "sim_too_early", "sim_too_late", "sim_wrong_cell", "sim_ping_pong"]
    pd.DataFrame(columns=ret_cols).to_csv(out_dir / "RETURN_SCHEMA.csv", index=False)

    manifest = {
        "package": "WINNIIO → Blaretech counterfactual CIO request",
        "generated_from": str(data_dir),
        "n_sites": int(len(sites)),
        "n_relations": int(len(base)),
        "n_priority_relations": int(base["priority"].sum()),
        "cio_candidates_db": cio_candidates,
        "rows_to_simulate": int(len(req)),
        "files": {
            "01_counterfactual_request.csv": "(relation × candidate CIO) to simulate",
            "02_sites.geojson": "georeferenced sites (points) for RF ingestion",
            "03_relations.geojson": "georeferenced relation lines, priority flagged",
            "RETURN_SCHEMA.csv": "columns Blaretech returns → WINNIIO re-ingests",
        },
        "note": "All current metrics computed from real input PM data. "
                "Candidate-CIO outcomes are UNKNOWN by design — that is what "
                "the RF layer simulates.",
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def main() -> None:
    ap = argparse.ArgumentParser(description="Export WINNIIO→Blaretech counterfactual request")
    ap.add_argument("--data-dir", default="data/synthetic")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--threshold", type=float, default=99.0)
    args = ap.parse_args()
    m = build_export(Path(args.data_dir), Path(args.out_dir), failure_threshold_pct=args.threshold)
    print(json.dumps(m, indent=2))


if __name__ == "__main__":
    main()
