"""Mobility traces + sites -> CZML time-dynamic document for CesiumJS.

The CZML clock drives play / pause / rewind / fast-forward natively in Cesium
(viewer.clock.multiplier + shouldAnimate) — no custom timeline engine.

Packets:
  document        — clock spanning the trace window (Blaretech demo gap #1)
  site/<cell_id>  — one point+label per site (deduped by site position)
  UE-<id>         — time-tagged positions (interpolated), path trail, type color
  ho/<n>          — handover marker visible only at its instant (availability)
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

_TYPE_COLOR = {  # rgba — matches the dashboard legend hues
    "pedestrian": [34, 193, 214, 255],
    "car":        [255, 176, 32, 255],
    "train":      [199, 125, 255, 255],
}
_DEFAULT_COLOR = [160, 180, 210, 255]
_HO_COLOR = [255, 221, 87, 255]
_ISO = "%Y-%m-%dT%H:%M:%SZ"


def _iso(ts: str) -> str:
    return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S").replace(
        tzinfo=timezone.utc).strftime(_ISO)


def build_czml(traces_csv: Path, sites_csv: Path,
               ue_height_m: float = 1.5) -> list[dict]:
    df = pd.read_csv(traces_csv, comment="#")
    sites = pd.read_csv(sites_csv)

    t_min = df["timestamp_utc"].min()
    t_max = df["timestamp_utc"].max()
    start, end = _iso(t_min), _iso(t_max)
    interval = f"{start}/{end}"

    doc: list[dict] = [{
        "id": "document",
        "name": "WINNIIO Reality Canvas — SYNTHETIC mobility",
        "version": "1.0",
        "clock": {
            "interval": interval,
            "currentTime": start,
            "multiplier": 8,           # default playback speed
            "range": "LOOP_STOP",
            "step": "SYSTEM_CLOCK_MULTIPLIER",
        },
    }]

    # ── sites (dedupe by site_name; one mast marker per site) ──
    seen = set()
    for _, r in sites.iterrows():
        key = r.get("site_name", r["cell_id"])
        if key in seen:
            continue
        seen.add(key)
        doc.append({
            "id": f"site/{key}",
            "name": str(key),
            "position": {"cartographicDegrees":
                         [float(r["longitude"]), float(r["latitude"]), 0.0]},
            "point": {"pixelSize": 8, "color": {"rgba": [255, 93, 108, 255]},
                      "outlineColor": {"rgba": [10, 14, 28, 255]}, "outlineWidth": 1},
            "label": {"text": str(key), "font": "11px sans-serif", "showBackground": True,
                      "pixelOffset": {"cartesian2": [0, -18]},
                      "fillColor": {"rgba": [233, 238, 247, 255]},
                      "backgroundColor": {"rgba": [10, 14, 28, 190]}},
        })

    # ── UEs: time-dynamic positions + path trail ──
    ho_idx = 0
    for ue_id, g in df.groupby("ue_id", sort=False):
        g = g.sort_values("t_s")
        utype = str(g["user_type"].iloc[0])
        color = _TYPE_COLOR.get(utype, _DEFAULT_COLOR)
        epoch = _iso(g["timestamp_utc"].iloc[0])
        h = float(g["ue_height_agl_m"].iloc[0]) if "ue_height_agl_m" in g else ue_height_m
        coords: list[float] = []
        for _, r in g.iterrows():
            coords.extend([float(r["t_s"]), float(r["lon"]), float(r["lat"]), h])
        doc.append({
            "id": str(ue_id),
            "name": f"{ue_id} ({utype})",
            "availability": interval,
            "position": {"epoch": epoch, "cartographicDegrees": coords,
                         "interpolationAlgorithm": "LAGRANGE",
                         "interpolationDegree": 1},
            "point": {"pixelSize": 6, "color": {"rgba": color},
                      "outlineColor": {"rgba": [10, 14, 28, 255]}, "outlineWidth": 1},
            "path": {"leadTime": 0, "trailTime": 45, "width": 2,
                     "material": {"solidColor": {"color": {"rgba":
                         [color[0], color[1], color[2], 140]}}}},
            "properties": {"user_type": utype},
        })

        # ── handover markers: visible only at their instant ──
        for _, r in g[g["handover"] == 1].iterrows():
            t = datetime.strptime(str(r["timestamp_utc"]), "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=timezone.utc)
            avail = (f"{t.strftime(_ISO)}/"
                     f"{(t + timedelta(seconds=8)).strftime(_ISO)}")
            doc.append({
                "id": f"ho/{ho_idx}",
                "name": f"HO {ue_id} -> {r['serving_cell']}",
                "availability": avail,
                "position": {"cartographicDegrees":
                             [float(r["lon"]), float(r["lat"]), h + 2.0]},
                "point": {"pixelSize": 10, "color": {"rgba": _HO_COLOR},
                          "outlineColor": {"rgba": [10, 14, 28, 255]},
                          "outlineWidth": 2},
                "properties": {"ue_id": str(ue_id),
                               "serving_cell": str(r["serving_cell"])},
            })
            ho_idx += 1

    return doc
