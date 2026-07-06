#!/usr/bin/env python3
"""Synthetic UE mobility traces — the piece Blaretech (Grzegorz) said was missing.

SYNTHETIC / illustrative. Deterministic (seed=42). Built over the SAME Shibuya
site geometry as the counterfactual package already sent, so the traces move
through the same cells and induce handovers on the same source->target relations.

Grzegorz's three gaps, answered:
  - movement PATHS  -> per-UE lat/lon polyline over time
  - TIMING          -> per-second samples with timestamps
  - user TYPE       -> pedestrian / car / train, each with realistic speed

NOT real UE data. Real movement/timing/type comes from the operator's MDT / PCAP
traces under NDA; this lets the RF sim be developed and tested now.

Outputs (into --out-dir):
  mobility_traces.csv   ue_id,user_type,t_s,timestamp_utc,lat,lon,speed_kmh,heading_deg,serving_cell,handover
  mobility_paths.geojson  one LineString per UE (for the map / RF world)
  README.md
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

# user_type -> (speed km/h mean, speed jitter, path straightness 0..1, count)
PROFILES = {
    "pedestrian": (4.5, 1.0, 0.35, 10),
    "car":        (38.0, 10.0, 0.85, 8),
    "train":      (75.0, 8.0, 0.98, 3),
}
_M_PER_DEG = 111_320.0
SAMPLE_S = 1          # 1 Hz
DURATION_S = 240      # 4 min per UE
START = datetime(2026, 4, 1, 8, 0, 0, tzinfo=timezone.utc)


def _sites(data_dir: Path) -> pd.DataFrame:
    df = pd.read_csv(data_dir / "site_database.csv")
    return df.drop_duplicates("site_name")[["site_name", "latitude", "longitude"]].reset_index(drop=True)


def _nearest_cell(lat: float, lon: float, cells: pd.DataFrame) -> str:
    d = (cells["latitude"] - lat) ** 2 + (cells["longitude"] - lon) ** 2
    return str(cells.loc[d.idxmin(), "cell_id"])


def generate(data_dir: Path, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(42)
    sites = _sites(data_dir)
    cells = pd.read_csv(data_dir / "site_database.csv")[["cell_id", "latitude", "longitude"]]
    lat0, lat1 = sites["latitude"].min(), sites["latitude"].max()
    lon0, lon1 = sites["longitude"].min(), sites["longitude"].max()

    rows, features = [], []
    uid = 0
    for utype, (spd_mean, spd_jit, straight, n) in PROFILES.items():
        for _ in range(n):
            uid += 1
            ue = f"UE-{utype[:3].upper()}-{uid:03d}"
            # start at a random edge point, head across the cluster
            lat = float(rng.uniform(lat0, lat1))
            lon = float(rng.uniform(lon0, lon1))
            heading = float(rng.uniform(0, 360))
            prev_cell = _nearest_cell(lat, lon, cells)
            t0 = START + timedelta(seconds=int(rng.integers(0, 3600)))
            path = []
            for t in range(0, DURATION_S, SAMPLE_S):
                spd = max(0.3, float(rng.normal(spd_mean, spd_jit)))          # km/h
                # turn: pedestrians wander, trains go straight
                heading += float(rng.normal(0, (1 - straight) * 25))
                step_m = spd * 1000 / 3600 * SAMPLE_S
                rad = math.radians(heading)
                lat += step_m * math.cos(rad) / _M_PER_DEG
                lon += step_m * math.sin(rad) / (_M_PER_DEG * math.cos(math.radians(lat)))
                lat = min(max(lat, lat0 - 0.01), lat1 + 0.01)
                lon = min(max(lon, lon0 - 0.01), lon1 + 0.01)
                cell = _nearest_cell(lat, lon, cells)
                ho = int(cell != prev_cell)
                ts = t0 + timedelta(seconds=t)
                rows.append({
                    "ue_id": ue, "user_type": utype, "t_s": t,
                    "timestamp_utc": ts.strftime("%Y-%m-%d %H:%M:%S"),
                    "lat": round(lat, 6), "lon": round(lon, 6),
                    "speed_kmh": round(spd, 1), "heading_deg": round(heading % 360, 1),
                    "serving_cell": cell, "handover": ho,
                })
                path.append([round(lon, 6), round(lat, 6)])
                prev_cell = cell
            features.append({
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": path},
                "properties": {"ue_id": ue, "user_type": utype},
            })

    df = pd.DataFrame(rows)
    header = "# SYNTHETIC — illustrative UE mobility (paths/timing/type); NOT real MDT/PCAP\n"
    with open(out_dir / "mobility_traces.csv", "w", encoding="utf-8", newline="") as fh:
        fh.write(header)
        df.to_csv(fh, index=False)
    (out_dir / "mobility_paths.geojson").write_text(json.dumps(
        {"type": "FeatureCollection", "features": features}, indent=1))

    manifest = {
        "package": "WINNIIO synthetic UE mobility (Blaretech RF-sim input)",
        "watermark": "SYNTHETIC — not real UE data; movement/timing/type illustrative",
        "ues": int(df["ue_id"].nunique()),
        "by_type": df.groupby("user_type")["ue_id"].nunique().to_dict(),
        "rows": int(len(df)),
        "sample_hz": 1, "duration_s": DURATION_S,
        "handovers": int(df["handover"].sum()),
        "matches": "same Shibuya site geometry as the counterfactual package",
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data/synthetic")
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    print(json.dumps(generate(Path(args.data_dir), Path(args.out_dir)), indent=2))


if __name__ == "__main__":
    main()
