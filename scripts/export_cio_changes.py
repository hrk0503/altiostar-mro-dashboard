#!/usr/bin/env python3
"""Export per-relation CIO optimization changes for all geographies.

Generates CSV files showing before/after CIO values, success rate
improvements, and failure breakdowns for every cell relation.
Used by the dashboard's "Export CIO Changes" button.

Usage:
    python scripts/export_cio_changes.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.optimize_cio import find_optimal_cios
from src.env.mro_env import MROEnv


def export_single_geo(geo_dir: Path, out_dir: Path) -> dict:
    """Export CIO changes for a single geography."""
    pm_path = str(geo_dir / "pm_data_relation_level.csv")
    kpi_path = str(geo_dir / "cluster_kpi_summary.csv")
    geo_name = geo_dir.name

    env = MROEnv(
        pm_data_path=pm_path,
        kpi_path=kpi_path,
        reward_version="v2",
        scenario="baseline",
        scenario_seed=42,
    )
    env.reset(seed=42)

    result = find_optimal_cios(env)
    improvements = result["improvements"]

    rows = []
    for imp in improvements:
        src, tgt = imp["relation"].split("->")
        init_cio = round(imp["initial_cio"], 1)
        opt_cio = round(imp["optimal_cio"], 1)
        delta = round(opt_cio - init_cio, 1)
        rows.append({
            "source_cell": src,
            "target_cell": tgt,
            "initial_cio_dB": init_cio,
            "optimized_cio_dB": opt_cio,
            "cio_delta_dB": delta,
            "before_success_%": imp["current_success"],
            "after_success_%": imp["optimal_success"],
            "improvement_%": imp["improvement"],
            "action": "increased" if delta > 0.1 else ("decreased" if delta < -0.1 else "unchanged"),
        })

    df = pd.DataFrame(rows)
    df = df.sort_values("improvement_%", ascending=False)

    csv_path = out_dir / f"{geo_name}_cio_changes.csv"
    df.to_csv(csv_path, index=False)

    env.close()

    changed = len([r for r in rows if abs(r["cio_delta_dB"]) > 0.1])
    mean_imp = float(np.mean([r["improvement_%"] for r in rows]))

    return {
        "geography": geo_name,
        "total_relations": len(rows),
        "relations_changed": changed,
        "mean_improvement": round(mean_imp, 2),
        "csv_path": str(csv_path),
    }


def main():
    out_dir = ROOT / "results" / "cio_exports"
    out_dir.mkdir(exist_ok=True)

    extra_geo = ROOT / "data" / "extra_geo"
    geo_dirs = sorted([
        d for d in extra_geo.iterdir()
        if d.is_dir() and (d / "pm_data_relation_level.csv").exists()
    ])

    print(f"Exporting CIO changes for {len(geo_dirs)} geographies...")

    summary = []
    for i, geo_dir in enumerate(geo_dirs, 1):
        print(f"  [{i}/{len(geo_dirs)}] {geo_dir.name} ...", end=" ", flush=True)
        try:
            info = export_single_geo(geo_dir, out_dir)
            print(f"✓ {info['relations_changed']}/{info['total_relations']} changed, +{info['mean_improvement']:.1f}%")
            summary.append(info)
        except Exception as e:
            print(f"✗ {e}")

    # Also export Shibuya (synthetic)
    shibuya_pm = ROOT / "data" / "synthetic" / "pm_data_relation_level.csv"
    shibuya_kpi = ROOT / "data" / "synthetic" / "cluster_kpi_summary.csv"
    if shibuya_pm.exists():
        print("  [+1] shibuya ...", end=" ", flush=True)
        try:
            env = MROEnv(
                pm_data_path=str(shibuya_pm),
                kpi_path=str(shibuya_kpi) if shibuya_kpi.exists() else None,
                reward_version="v2",
                scenario="baseline",
                scenario_seed=42,
            )
            env.reset(seed=42)
            result = find_optimal_cios(env)
            rows = []
            for imp in result["improvements"]:
                src, tgt = imp["relation"].split("->")
                init_cio = round(imp["initial_cio"], 1)
                opt_cio = round(imp["optimal_cio"], 1)
                delta = round(opt_cio - init_cio, 1)
                rows.append({
                    "source_cell": src,
                    "target_cell": tgt,
                    "initial_cio_dB": init_cio,
                    "optimized_cio_dB": opt_cio,
                    "cio_delta_dB": delta,
                    "before_success_%": imp["current_success"],
                    "after_success_%": imp["optimal_success"],
                    "improvement_%": imp["improvement"],
                    "action": "increased" if delta > 0.1 else ("decreased" if delta < -0.1 else "unchanged"),
                })
            df = pd.DataFrame(rows).sort_values("improvement_%", ascending=False)
            df.to_csv(out_dir / "shibuya_cio_changes.csv", index=False)
            env.close()
            changed = len([r for r in rows if abs(r["cio_delta_dB"]) > 0.1])
            print(f"✓ {changed}/{len(rows)} changed")
        except Exception as e:
            print(f"✗ {e}")

    # Save summary
    (out_dir / "export_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\nDone — CSVs in {out_dir}/")


if __name__ == "__main__":
    main()
