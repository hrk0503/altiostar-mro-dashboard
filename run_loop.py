#!/usr/bin/env python3
"""One-command MRO loop demo (SYNTHETIC, end-to-end, reproducible).

    python run_loop.py [--data-dir data/synthetic] [--out-dir results/loop]

Runs: export counterfactual request -> synthetic RF return (Blaretech stand-in)
-> ingest -> optimize -> before/after result. Prints a deterministic run hash so
anyone can verify the numbers reproduce (see VERIFY.md). No real data, no
fabricated real-world claims — the whole loop is watermarked SYNTHETIC.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.integration.blaretech_export import build_export
from src.integration.counterfactual_loop import (
    current_from_request,
    ingest_counterfactuals,
    optimize,
)
from src.integration.synthetic_rf_return import generate
from src.repro import file_hash, synthetic_badge


def run_loop(data_dir: Path, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    # 1. WINNIIO exports the counterfactual request
    build_export(data_dir, out_dir)
    request = out_dir / "01_counterfactual_request.csv"
    # 2. RF layer (synthetic stand-in) returns simulated outcomes
    ret = out_dir / "rf_return_SYNTHETIC.csv"
    generate(request, ret)
    # 3. WINNIIO re-ingests and optimizes over the counterfactual space
    space = ingest_counterfactuals(ret)
    result = optimize(space, current=current_from_request(request))
    result_path = out_dir / "loop_before_after.csv"
    result.to_csv(result_path, index=False)
    summary = {
        "watermark": synthetic_badge("text"),
        "relations": int(len(result)),
        "mean_before_%": round(float(result["before_success_%"].mean()), 4),
        "mean_after_%": round(float(result["after_success_%"].mean()), 4),
        "mean_improvement_pp": round(float(result["improvement_pp"].mean()), 4),
        "result_file": str(result_path),
    }
    (out_dir / "loop_summary.json").write_text(json.dumps(summary, indent=2))
    summary["run_hash"] = file_hash(result_path)
    return summary


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data/synthetic")
    ap.add_argument("--out-dir", default="results/loop")
    args = ap.parse_args()
    s = run_loop(Path(args.data_dir), Path(args.out_dir))
    print(json.dumps(s, indent=2))
    print("\n" + synthetic_badge("text"))


if __name__ == "__main__":
    main()
