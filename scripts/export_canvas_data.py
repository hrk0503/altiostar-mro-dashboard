"""Export sites.json, relations.json and scene-<n>.czml for the Reality Canvas
frontend (frontend/public/data/). SYNTHETIC data only — labeled as such.

Usage:
    python scripts/export_canvas_data.py

Reads:
    data/synthetic/site_database.csv
    data/synthetic/neighbor_relations.csv
    data/synthetic/pm_data_relation_level.csv
    <mobility-dir>/mobility_traces.csv  (one per scene, generated separately
        via scripts/generate_mobility_traces.py --out-dir <dir> --n-ues N --seed S)

Writes into frontend/public/data/:
    sites.json
    relations.json
    scene-21-42.czml
    scene-100-42.czml
    scene-100-99.czml
    scene-500-42.czml
    scenes.json   (manifest the frontend reads to populate the UE-count slider)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from exporters.czml import build_czml  # noqa: E402

SYNTH = ROOT / "data" / "synthetic"
OUT_DIR = ROOT / "reality-canvas" / "public" / "data"

# (n_ues, seed, mobility-trace directory)
SCENES = [
    (21, 42, ROOT / ".canvas_mobility" / "mob21_42"),
    (100, 42, ROOT / ".canvas_mobility" / "mob100_42"),
    (100, 99, ROOT / ".canvas_mobility" / "mob100_99"),
    (500, 42, ROOT / ".canvas_mobility" / "mob500_42"),
]


def export_sites(sites_csv: Path) -> list[dict]:
    df = pd.read_csv(sites_csv)
    records = []
    for _, r in df.iterrows():
        records.append({
            "cellId": str(r["cell_id"]),
            "siteName": str(r["site_name"]),
            "latitude": float(r["latitude"]),
            "longitude": float(r["longitude"]),
            "antennaHeightM": float(r["antenna_height_m"]),
            "azimuthDeg": float(r["azimuth_deg"]),
            "beamwidthDeg": 65.0,  # SYNTHETIC default (site DB has no beamwidth col)
            "frequencyBand": str(r["frequency_band"]),
            "technology": str(r["technology"]),
            "status": str(r["status"]),
        })
    return records


def export_relations(neighbor_csv: Path, pm_csv: Path, sites_csv: Path) -> list[dict]:
    neighbors = pd.read_csv(neighbor_csv)
    pm = pd.read_csv(pm_csv)
    sites = pd.read_csv(sites_csv).set_index("cell_id")

    agg = pm.groupby(["source_cell_id", "target_cell_id"], as_index=False).agg(
        ho_attempts=("ho_attempts", "sum"),
        ho_successes=("ho_successes", "sum"),
    )
    agg["success_rate"] = (agg["ho_successes"] / agg["ho_attempts"].replace(0, pd.NA)).fillna(0.0)
    agg_idx = agg.set_index(["source_cell_id", "target_cell_id"])

    out = []
    for _, r in neighbors.iterrows():
        s, n = str(r["serving_cell"]), str(r["neighbor_cell"])
        if s not in sites.index or n not in sites.index:
            continue
        rate = 0.0
        if (s, n) in agg_idx.index:
            rate = float(agg_idx.loc[(s, n), "success_rate"])
        out.append({
            "servingCell": s,
            "neighborCell": n,
            "servingLat": float(sites.loc[s, "latitude"]),
            "servingLon": float(sites.loc[s, "longitude"]),
            "neighborLat": float(sites.loc[n, "latitude"]),
            "neighborLon": float(sites.loc[n, "longitude"]),
            "relationType": str(r["relation_type"]),
            "successRate": round(rate, 4),
        })
    return out


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    sites_csv = SYNTH / "site_database.csv"
    neighbor_csv = SYNTH / "neighbor_relations.csv"
    pm_csv = SYNTH / "pm_data_relation_level.csv"

    sites = export_sites(sites_csv)
    (OUT_DIR / "sites.json").write_text(json.dumps(sites, indent=2), encoding="utf-8")

    relations = export_relations(neighbor_csv, pm_csv, sites_csv)
    (OUT_DIR / "relations.json").write_text(json.dumps(relations, indent=2), encoding="utf-8")

    manifest = []
    for n_ues, seed, mob_dir in SCENES:
        traces_csv = mob_dir / "mobility_traces.csv"
        if not traces_csv.exists():
            print(f"SKIP scene n={n_ues} seed={seed}: {traces_csv} not found "
                  f"(run generate_mobility_traces.py first)")
            continue
        czml = build_czml(traces_csv, sites_csv)
        fname = f"scene-{n_ues}-{seed}.czml"
        (OUT_DIR / fname).write_text(json.dumps(czml), encoding="utf-8")
        manifest.append({"nUes": n_ues, "seed": seed, "file": fname})
        print(f"wrote {fname} ({len(czml)} packets)")

    (OUT_DIR / "scenes.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"wrote sites.json ({len(sites)} cells), relations.json ({len(relations)} relations), "
          f"scenes.json ({len(manifest)} scenes)")


if __name__ == "__main__":
    main()
