#!/usr/bin/env python3
"""Generate ADDITIONAL multi-geo / multi-season LTE MRO datasets.

Matrix: 3 footprints x 4 seasons = 12 datasets (LTE).

Covers every "You bring" input on the Rakuten/Altiostar slide:
  * Site database — azimuth, tilt, height        -> site_database.csv
  * Clutter & elevation                          -> site_database.csv
  * Neighbour lists & mobility KPIs              -> neighbor_relations.csv +
                                                    pm_data_relation_level.csv +
                                                    cluster_kpi_summary.csv
  * RSRP / RSRQ / SINR samples                   -> radio_samples.csv

Each season bends the curves with research-grounded, climate- AND band-specific
RF physics so footprints react differently (see SEASONAL_RESEARCH.md):
  foliage (summer/spring, vegetated, worse at higher freq), snow/ice (continental
  & mountain winter), tropospheric ducting (coastal Band-41 TDD summer/autumn ->
  wrong-cell + ping-pong), typhoon/rain (Japan autumn), traffic seasonality
  (Tokyo summer tourism, Nagano winter ski).

Distinct learnable signatures:
  rural  -> too-LATE-dominated failures (wide cells)
  Tokyo summer/autumn -> WRONG-CELL + ping-pong (Band 41 TDD ducting, Tokyo Bay)
  Kyiv winter -> high overall failure, low RSRP (snow/cold)

All CSVs pass src/pipeline/models.py validators (Band 1/3/41 whitelist) and the
env's source_cell_id relation-mode detection. Data is synthetic.
"""

import csv
import math
import random
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent / "data" / "extra_geo"

WHITELIST_BANDS = {"Band 1 (2100MHz)", "Band 3 (1800MHz)", "Band 41 (2500MHz)"}
TDD_BAND = "Band 41 (2500MHz)"  # TDD -> tropospheric-ducting sensitive

SEASON_MONTH = {"winter": (2026, 1, 13), "spring": (2026, 4, 14),
                "summer": (2026, 7, 15), "autumn": (2026, 10, 13)}

LOCATIONS = {
    "kyiv": {
        "prefix": "KYIV", "city_name": "Kyiv", "center": (50.4501, 30.5234),
        "num_sites": 16, "tac_base": 40000, "vendor": "Ericsson",
        "bands": ["Band 1 (2100MHz)", "Band 3 (1800MHz)"],
        "clutter": ["Dense Urban", "Urban", "Suburban"], "jitter_km": 1.6,
        "base_ho_rate": 200.0, "base_fail_rate": 0.025, "problem_fail_rate": 0.09,
        "problem_fraction": 0.10, "days": 8, "late_bias": 0.0,
        "climate": "continental",
    },
    "japan_rural": {
        "prefix": "RJPN", "city_name": "Nagano-Rural", "center": (36.6510, 138.1810),
        "num_sites": 11, "tac_base": 41000, "vendor": "NEC",
        "bands": ["Band 1 (2100MHz)", "Band 3 (1800MHz)"],
        "clutter": ["Rural", "Suburban", "Open Area"], "jitter_km": 6.0,
        "base_ho_rate": 100.0, "base_fail_rate": 0.022, "problem_fail_rate": 0.085,
        "problem_fraction": 0.10, "days": 10, "late_bias": 0.20,
        "climate": "mountain",
    },
    "tokyo": {
        "prefix": "TKYO", "city_name": "Tokyo-Downtown", "center": (35.6595, 139.7005),
        "num_sites": 16, "tac_base": 42000, "vendor": "Rakuten",
        "bands": ["Band 1 (2100MHz)", "Band 41 (2500MHz)"],
        "clutter": ["Dense Urban", "High-Rise", "Urban"], "jitter_km": 1.3,
        "base_ho_rate": 350.0, "base_fail_rate": 0.03, "problem_fail_rate": 0.10,
        "problem_fraction": 0.12, "days": 7, "late_bias": 0.0,
        "climate": "coastal_subtropical",
    },
}

PROFILES = {
    "continental": {
        "winter": {"load": 0.95, "fail": 1.60, "rsrp": -5.0, "pp": 1.20, "wrong": 0.00},
        "spring": {"load": 1.00, "fail": 1.05, "rsrp": -1.0, "pp": 1.00, "wrong": 0.00},
        "summer": {"load": 1.10, "fail": 1.20, "rsrp": -3.0, "pp": 1.05, "wrong": 0.03},
        "autumn": {"load": 1.00, "fail": 1.15, "rsrp": -2.0, "pp": 1.05, "wrong": 0.02},
    },
    "mountain": {
        "winter": {"load": 1.25, "fail": 1.70, "rsrp": -5.0, "pp": 1.20, "wrong": 0.00},
        "spring": {"load": 0.95, "fail": 1.10, "rsrp": -2.0, "pp": 1.00, "wrong": 0.00},
        "summer": {"load": 1.00, "fail": 1.35, "rsrp": -5.0, "pp": 1.05, "wrong": 0.02},
        "autumn": {"load": 1.00, "fail": 1.45, "rsrp": -3.0, "pp": 1.15, "wrong": 0.03},
    },
    "coastal_subtropical": {
        "winter": {"load": 1.05, "fail": 1.05, "rsrp": -1.0, "pp": 1.00, "wrong": 0.00},
        "spring": {"load": 1.15, "fail": 1.10, "rsrp": -1.0, "pp": 1.15, "wrong": 0.05},
        "summer": {"load": 1.40, "fail": 1.30, "rsrp": -2.0, "pp": 1.50, "wrong": 0.20},
        "autumn": {"load": 1.10, "fail": 1.25, "rsrp": -2.0, "pp": 1.35, "wrong": 0.15},
    },
}


def sround(x):
    """Unbiased stochastic rounding — preserves expected value for small counts."""
    if x <= 0:
        return 0
    f = math.floor(x)
    return int(f + (1 if random.random() < (x - f) else 0))


def haversine_m(lat1, lon1, lat2, lon2):
    R = 6_371_000
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def jitter(lat, lon, radius_km):
    dlat = random.uniform(-radius_km / 111, radius_km / 111)
    dlon = random.uniform(-radius_km / (111 * math.cos(math.radians(lat))),
                          radius_km / (111 * math.cos(math.radians(lat))))
    return round(lat + dlat, 6), round(lon + dlon, 6)


def split_failures(fail, late_bias, wrong_bias):
    """Distribute failures into (too_early, too_late, wrong_cell) with biases,
    using unbiased stochastic rounding so ratios hold at any volume."""
    if fail <= 0:
        return 0, 0, 0
    late_share = min(0.75, 0.30 + late_bias)
    wrong_share = min(0.75, 0.20 + wrong_bias)
    early_share = max(0.05, 1.0 - late_share - wrong_share)
    early = min(fail, sround(fail * early_share))
    late = min(fail - early, sround(fail * late_share))
    wrong = max(0, fail - early - late)
    return early, late, wrong


def load_curve(hour):
    if 7 <= hour <= 9:
        return 1.0 + 0.3 * math.sin(math.pi * (hour - 7) / 2)
    if 11 <= hour <= 14:
        return 0.9
    if 16 <= hour <= 20:
        return 1.2 + 0.2 * math.sin(math.pi * (hour - 16) / 4)
    if hour >= 22 or hour <= 5:
        return 0.15
    return 0.3


def generate(location_key, season, seed):
    cfg = LOCATIONS[location_key]
    prof = PROFILES[cfg["climate"]][season]
    for b in cfg["bands"]:
        if b not in WHITELIST_BANDS:
            raise ValueError(f"Band {b!r} not whitelisted")
    random.seed(seed)

    center_lat, center_lon = cfg["center"]
    start_date = datetime(*SEASON_MONTH[season])
    out = BASE_DIR / f"{location_key}_{season}"
    out.mkdir(parents=True, exist_ok=True)
    sectors = 3
    num_cells = cfg["num_sites"] * sectors
    last_updated = start_date.strftime("%Y-%m-%d")

    # 1. site_database.csv
    sites = []
    for i in range(cfg["num_sites"]):
        lat, lon = jitter(center_lat, center_lon, cfg["jitter_km"])
        band = cfg["bands"][i % len(cfg["bands"])]
        for s in range(1, sectors + 1):
            elec, mech = random.randint(2, 6), random.randint(0, 3)
            sites.append({
                "cell_id": f"{cfg['prefix']}-{i + 1:03d}-{s}",
                "enodeb_id": f"{cfg['prefix']}-{i + 1:03d}",
                "site_name": f"{cfg['city_name']}-Site-{i + 1:03d}",
                "latitude": lat, "longitude": lon,
                "antenna_height_m": random.randint(25, 50), "sector": s,
                "azimuth_deg": (s - 1) * 120 + random.randint(-5, 5),
                "electrical_tilt_deg": elec, "mechanical_tilt_deg": mech,
                "total_tilt_deg": elec + mech,
                "clutter_type": random.choice(cfg["clutter"]),
                "elevation_m": round(random.uniform(30, 80), 1),
                "frequency_band": band, "pci": (i * sectors + s) % 504,
                "tac": cfg["tac_base"] + i, "vendor": cfg["vendor"],
                "technology": "LTE", "status": "Active",
            })
    with open(out / "site_database.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=sites[0].keys())
        w.writeheader()
        w.writerows(sites)
    band_of = {c["cell_id"]: c["frequency_band"] for c in sites}

    # 2. neighbor_relations.csv
    neighbors = []
    for cell in sites:
        cands = sorted([c for c in sites if c["cell_id"] != cell["cell_id"]],
                       key=lambda c: haversine_m(cell["latitude"], cell["longitude"],
                                                 c["latitude"], c["longitude"]))
        n_nbrs = random.randint(8, min(14, len(cands)))
        for rank, nbr in enumerate(cands[:n_nbrs], 1):
            dist = haversine_m(cell["latitude"], cell["longitude"],
                               nbr["latitude"], nbr["longitude"])
            neighbors.append({
                "serving_cell": cell["cell_id"], "neighbor_cell": nbr["cell_id"],
                "neighbor_rank": rank, "distance_m": round(dist, 1),
                "cell_individual_offset_dB": round(random.uniform(-6, 6), 1),
                "handover_allowed": "Yes",
                "relation_type": ("Intra-Frequency"
                                  if cell["frequency_band"] == nbr["frequency_band"]
                                  else "Inter-Frequency"),
                "last_updated": last_updated,
            })
    with open(out / "neighbor_relations.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=neighbors[0].keys())
        w.writeheader()
        w.writerows(neighbors)

    nbr_by_cell = defaultdict(list)
    for n in neighbors:
        nbr_by_cell[n["serving_cell"]].append(n)
    n_problem = max(1, int(num_cells * cfg["problem_fraction"]))
    problem_ids = set(random.sample([c["cell_id"] for c in sites], n_problem))

    # 3. pm_data_relation_level.csv  (mobility KPIs, relation level — env-preferred)
    rows = 0
    with open(out / "pm_data_relation_level.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp_utc", "rop_duration_min", "source_cell_id",
                    "target_cell_id", "ho_attempts", "ho_successes", "ho_failures",
                    "too_early_ho", "too_late_ho", "wrong_cell", "correct_cell",
                    "ping_pong", "cio_db"])
        for day in range(cfg["days"]):
            for rop in range(96):
                ts = start_date + timedelta(days=day, minutes=rop * 15)
                load = load_curve(ts.hour) * prof["load"]
                ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
                for cell in sites:
                    cid = cell["cell_id"]
                    is_problem = cid in problem_ids
                    cnbrs = nbr_by_cell.get(cid, [])
                    if not cnbrs:
                        continue
                    total_att = max(1, int(random.gauss(cfg["base_ho_rate"],
                                                        cfg["base_ho_rate"] * 0.25) * load))
                    base = (random.uniform(cfg["problem_fail_rate"] * 0.7, cfg["problem_fail_rate"] * 1.3)
                            if is_problem else
                            random.uniform(cfg["base_fail_rate"] * 0.5, cfg["base_fail_rate"] * 1.5))
                    fail_rate = min(0.6, base * prof["fail"])
                    total_fail = min(total_att, max(0, int(total_att * fail_rate)))
                    total_succ = total_att - total_fail
                    pp_base = 0.04 if is_problem else 0.015
                    total_pp = min(total_succ, max(0, int(
                        total_succ * random.uniform(0.005, pp_base) * prof["pp"])))
                    c_early, c_late, c_wrong = split_failures(
                        total_fail, cfg["late_bias"], prof["wrong"])

                    weights = [random.random() ** 0.5 for _ in cnbrs]
                    wsum = sum(weights) or 1
                    for j, nbr in enumerate(cnbrs):
                        frac = weights[j] / wsum
                        early = sround(c_early * frac)
                        late = sround(c_late * frac)
                        wrong = sround(c_wrong * frac)
                        fail = early + late + wrong
                        att = max(fail, sround(total_att * frac))
                        succ = att - fail
                        pp = min(succ, sround(total_pp * frac))
                        w.writerow([ts_str, 15, cid, nbr["neighbor_cell"], att, succ,
                                    fail, early, late, wrong, succ, pp,
                                    nbr["cell_individual_offset_dB"]])
                        rows += 1

    # 4. cluster_kpi_summary.csv
    kpis = []
    for cell in sites:
        cid = cell["cell_id"]
        is_problem = cid in problem_ids
        total_att = random.randint(150_000, 300_000)
        raw = random.uniform(4.0, 10.0) if is_problem else random.uniform(0.5, 2.5)
        fail_pct = round(min(60.0, raw * prof["fail"]), 2)
        total_fail = int(total_att * fail_pct / 100)
        total_succ = total_att - total_fail
        pp_pct = round(min(20.0, (random.uniform(2.0, 5.0) if is_problem
                                  else random.uniform(0.3, 1.5)) * prof["pp"]), 2)
        early, late, wrong = split_failures(total_fail, cfg["late_bias"], prof["wrong"])
        kpis.append({
            "cell_id": cid, "enodeb_id": cell["enodeb_id"],
            "clutter_type": cell["clutter_type"], "total_ho_attempts": total_att,
            "total_ho_success": total_succ, "total_ho_failures": total_fail,
            "ho_failure_rate_pct": fail_pct, "failure_too_early": early,
            "failure_too_late": late, "failure_wrong_cell": wrong,
            "total_pingpong": int(total_succ * pp_pct / 100), "pingpong_rate_pct": pp_pct,
            "avg_rsrp_dBm": round(random.gauss(-95 if is_problem else -82, 4) + prof["rsrp"], 1),
            "problem_cell": "Yes" if is_problem else "No",
        })
    with open(out / "cluster_kpi_summary.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=kpis[0].keys())
        w.writeheader()
        w.writerows(kpis)

    # 5. radio_samples.csv  (RSRP / RSRQ / SINR samples — hourly, cell level)
    #    Interference (ducting on Band 41 TDD + ping-pong) degrades SINR;
    #    congestion degrades RSRQ. Matches PMRecord radio fields / valid ranges.
    sinr_intf = -((prof["pp"] - 1.0) * 6.0 + prof["wrong"] * 12.0)
    rs_rows = 0
    with open(out / "radio_samples.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp_utc", "cell_id", "enodeb_id", "frequency_band",
                    "avg_rsrp_dBm", "avg_rsrq_dB", "avg_sinr_dB",
                    "prb_utilization_dl_pct", "prb_utilization_ul_pct", "active_ue_avg"])
        for day in range(cfg["days"]):
            for hour in range(24):
                ts = start_date + timedelta(days=day, hours=hour)
                load = load_curve(hour) * prof["load"]
                ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
                for cell in sites:
                    cid = cell["cell_id"]
                    is_problem = cid in problem_ids
                    # Band 41 (TDD) extra interference hit during ducting seasons.
                    tdd_hit = (3.0 if band_of[cid] == TDD_BAND
                               and season in ("summer", "autumn") else 0.0)
                    rsrp = random.gauss(-95 if is_problem else -82, 4) + prof["rsrp"]
                    rsrp = round(min(-40.0, max(-140.0, rsrp)), 1)
                    sinr = random.gauss(14 - (8 if is_problem else 0), 5) + sinr_intf - tdd_hit
                    sinr = round(min(40.0, max(-10.0, sinr)), 1)
                    rsrq = random.gauss(-9 if not is_problem else -13, 2) - (load - 0.5) * 3.0
                    rsrq = round(min(0.0, max(-30.0, rsrq)), 1)
                    prb_dl = round(min(100.0, max(0.0, random.gauss(55 * load, 12))), 1)
                    prb_ul = round(min(100.0, max(0.0, random.gauss(32 * load, 9))), 1)
                    ue = round(max(0.0, random.gauss(90 * load, 22)), 1)
                    w.writerow([ts_str, cid, cell["enodeb_id"], cell["frequency_band"],
                                rsrp, rsrq, sinr, prb_dl, prb_ul, ue])
                    rs_rows += 1

    print(f"  {location_key:11s} {season:6s}: {len(sites):3d} cells {len(neighbors):4d} rel  "
          f"{rows:>8,} PM  {rs_rows:>6,} radio  {n_problem} problem  -> {out.name}/")
    return rows


if __name__ == "__main__":
    seasons = ["winter", "spring", "summer", "autumn"]
    seed, grand = 300, 0
    for loc in LOCATIONS:
        print(f"\n=== {loc} (all seasons, LTE) ===")
        for season in seasons:
            grand += generate(loc, season, seed)
            seed += 1
    n = len(LOCATIONS) * len(seasons)
    print(f"\nDone! {n} LTE datasets ({len(LOCATIONS)} footprints x {len(seasons)} seasons), "
          f"{grand:,} PM rows under data/extra_geo/")
