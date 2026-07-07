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

# user_type -> (speed km/h mean, speed jitter, path straightness 0..1, count,
#               ue_height_agl_m). Heights per 3GPP TR 38.901 outdoor UT = 1.5 m
# (train occupant slightly higher). AGL, not absolute — add the DEM surface.
PROFILES = {
    "pedestrian": (4.5, 1.0, 0.35, 10, 1.5),
    "car":        (38.0, 10.0, 0.85, 8, 1.5),
    "train":      (75.0, 8.0, 0.98, 3, 2.0),
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


def _nearest_np(lat: float, lon: float, clat, clon, cids) -> str:
    """Fast numpy nearest-cell for the hot loop (avoids pandas per-call overhead)."""
    i = int(((clat - lat) ** 2 + (clon - lon) ** 2).argmin())
    return cids[i]


def _scaled_profiles(n_ues: int | None):
    """Scale the ped/car/train counts to a target total UE count, keeping the mix."""
    if not n_ues:
        return {k: v for k, v in PROFILES.items()}
    base = {k: v[3] for k, v in PROFILES.items()}
    tot = sum(base.values())
    out, assigned = {}, 0
    keys = list(PROFILES)
    for i, k in enumerate(keys):
        cnt = round(n_ues * base[k] / tot) if i < len(keys) - 1 else n_ues - assigned
        assigned += cnt
        p = list(PROFILES[k])
        p[3] = max(1, cnt)
        out[k] = tuple(p)
    return out


def generate(data_dir: Path, out_dir: Path, n_ues: int | None = None,
             duration_s: int = DURATION_S, sample_s: int = SAMPLE_S,
             seed: int = 42) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    profiles = _scaled_profiles(n_ues)
    sites = _sites(data_dir)
    cells = pd.read_csv(data_dir / "site_database.csv")[["cell_id", "latitude", "longitude"]]
    _clat = cells["latitude"].to_numpy()
    _clon = cells["longitude"].to_numpy()
    _cids = cells["cell_id"].to_numpy()
    lat0, lat1 = sites["latitude"].min(), sites["latitude"].max()
    lon0, lon1 = sites["longitude"].min(), sites["longitude"].max()

    rows, features = [], []
    uid = 0
    for utype, (spd_mean, spd_jit, straight, n, height_agl) in profiles.items():
        for _ in range(n):
            uid += 1
            ue = f"UE-{utype[:3].upper()}-{uid:04d}"
            # start at a random edge point, head across the cluster
            lat = float(rng.uniform(lat0, lat1))
            lon = float(rng.uniform(lon0, lon1))
            heading = float(rng.uniform(0, 360))
            prev_cell = _nearest_np(lat, lon, _clat, _clon, _cids)
            t0 = START + timedelta(seconds=int(rng.integers(0, 3600)))
            path = []
            for t in range(0, duration_s, sample_s):
                spd = max(0.3, float(rng.normal(spd_mean, spd_jit)))          # km/h
                # turn: pedestrians wander, trains go straight
                heading += float(rng.normal(0, (1 - straight) * 25))
                step_m = spd * 1000 / 3600 * sample_s
                rad = math.radians(heading)
                lat += step_m * math.cos(rad) / _M_PER_DEG
                lon += step_m * math.sin(rad) / (_M_PER_DEG * math.cos(math.radians(lat)))
                lat = min(max(lat, lat0 - 0.01), lat1 + 0.01)
                lon = min(max(lon, lon0 - 0.01), lon1 + 0.01)
                cell = _nearest_np(lat, lon, _clat, _clon, _cids)
                ho = int(cell != prev_cell)
                ts = t0 + timedelta(seconds=t)
                rows.append({
                    "ue_id": ue, "user_type": utype, "t_s": t,
                    "timestamp_utc": ts.strftime("%Y-%m-%d %H:%M:%S"),
                    "lat": round(lat, 6), "lon": round(lon, 6),
                    "ue_height_agl_m": height_agl,   # AGL, add DEM for absolute
                    "env": "outdoor",                # all outdoor; no O2I modelled
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
        "sample_hz": round(1.0 / sample_s, 3), "duration_s": duration_s,
        "handovers": int(df["handover"].sum()),
        "crs": "WGS84 (EPSG:4326); ue_height_agl_m is Above-Ground-Level, add your DEM",
        "matches": "same Shibuya site geometry as the counterfactual package",
        "caveats": [
            "height is AGL (1.5 m ped/car, 2.0 m train per 3GPP TR 38.901), not absolute",
            "all UEs outdoor — no outdoor-to-indoor (O2I) penetration modelled",
            "paths are free-space random walks, NOT map-matched to roads/rails",
            "1 Hz sampling is coarse for fast UEs (train ~21 m/sample) — tune if needed",
        ],
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data/synthetic")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--n-ues", type=int, default=None, help="total UE count (mix kept); default 21")
    ap.add_argument("--duration-s", type=int, default=DURATION_S)
    ap.add_argument("--sample-hz", type=float, default=1.0, help="samples/sec (e.g. 2 for fast UEs)")
    ap.add_argument("--seed", type=int, default=42, help="RNG seed — new seed = new UE placements")
    args = ap.parse_args()
    sample_s = max(1, round(1.0 / args.sample_hz))
    print(json.dumps(generate(Path(args.data_dir), Path(args.out_dir),
                              n_ues=args.n_ues, duration_s=args.duration_s,
                              sample_s=sample_s, seed=args.seed), indent=2))


if __name__ == "__main__":
    main()
