#!/usr/bin/env python3
"""Generate ADDITIONAL multi-geo / multi-SEASON MRO datasets (4 sites x 4 seasons = 16).

Extends generate_multi_geo_data.py with calendar anchoring (``start_date``) and a
research-grounded, *climate- and band-specific* seasonal modifier per location.

Why seasons vary the data (sources in the accompanying SEASONAL_RESEARCH.md):
  * Foliage: deciduous canopy in leaf adds ~3-10 dB path loss at ~2 GHz vs bare
    winter, worse when wet, and worse at Band 41 (2.5 GHz) than Band 1/3
    (ITU-R P.833; MP Antenna; RF Essentials). -> summer/spring hurt vegetated
    (rural Japan, parks): lower RSRP, more failures.
  * Snow / ice accretion + cold: antenna icing and detuning in continental and
    mountain winters (Kyiv, Nagano ski country) -> RSRP down, failures up.
    Tokyo winter is mild/dry -> minimal.
  * Tropospheric ducting: temperature-inversion co-channel interference,
    "predominately co-channel TDD", peaking summer/autumn over coastal water
    (Wikipedia tropospheric propagation; US11018784B2). Band 41 is TDD and
    Tokyo is coastal (Tokyo Bay) -> downtown summer/autumn sees more WRONG-CELL
    handovers and ping-pong. Inland Kyiv/Nagano largely spared.
  * Typhoon / rain (Japan autumn): wind-driven foliage fades (up to ~22 dB) and
    Band 41 rain fade -> elevated, variable failures.
  * Traffic seasonality: Tokyo summer tourism + rainy season; Nagano winter ski
    crowds; Kyiv mild summer.

Distinct learnable signatures the RL agent should pick up:
  rural  -> too-LATE-dominated failures (wide cells, UE travels far)
  Tokyo summer/autumn -> WRONG-CELL + ping-pong dominated (Band 41 TDD ducting)
  Kyiv winter -> high overall failure, low RSRP (snow/cold)

Output per dataset (schema = src/pipeline/models.py, format the env prefers):
  data/extra_geo/<location>_<season>/{site_database,neighbor_relations,
  pm_data_relation_level,cluster_kpi_summary}.csv

Bands restricted to SiteRecord.validate_band whitelist so data passes the
strict pipeline validator.
"""

import csv
import math
import random
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent / "data" / "extra_geo"

WHITELIST_BANDS = {"Band 1 (2100MHz)", "Band 3 (1800MHz)", "Band 41 (2500MHz)"}

# Season anchor month (year fixed for reproducibility).
SEASON_MONTH = {"winter": (2026, 1, 13), "spring": (2026, 4, 14),
                "summer": (2026, 7, 15), "autumn": (2026, 10, 13)}

# ── Per-location base config ──────────────────────────────────────
# has_tdd flips on Band-41 ducting sensitivity. veg = vegetation density
# (foliage seasonal swing). climate drives which seasonal profile applies.
LOCATIONS = {
    "kyiv": {
        "prefix": "KYIV", "city_name": "Kyiv",
        "center": (50.4501, 30.5234), "num_sites": 16, "tac_base": 40000,
        "bands": ["Band 1 (2100MHz)", "Band 3 (1800MHz)"], "vendor": "Ericsson",
        "clutter": ["Dense Urban", "Urban", "Suburban"],
        "jitter_km": 1.6, "base_ho_rate": 200.0, "base_fail_rate": 0.025,
        "problem_fail_rate": 0.09, "problem_fraction": 0.10, "days": 8,
        "late_bias": 0.0, "climate": "continental",
    },
    "japan_rural": {
        "prefix": "RJPN", "city_name": "Nagano-Rural",
        "center": (36.6510, 138.1810), "num_sites": 11, "tac_base": 41000,
        "bands": ["Band 1 (2100MHz)", "Band 3 (1800MHz)"], "vendor": "NEC",
        "clutter": ["Rural", "Suburban", "Open Area"],
        "jitter_km": 6.0, "base_ho_rate": 100.0, "base_fail_rate": 0.022,
        "problem_fail_rate": 0.085, "problem_fraction": 0.10, "days": 10,
        "late_bias": 0.20, "climate": "mountain",
    },
    "tokyo": {
        "prefix": "TKYO", "city_name": "Tokyo-Downtown",
        "center": (35.6595, 139.7005), "num_sites": 16, "tac_base": 42000,
        "bands": ["Band 1 (2100MHz)", "Band 41 (2500MHz)"], "vendor": "Rakuten",
        "clutter": ["Dense Urban", "High-Rise", "Urban"],
        "jitter_km": 1.3, "base_ho_rate": 350.0, "base_fail_rate": 0.03,
        "problem_fail_rate": 0.10, "problem_fraction": 0.12, "days": 7,
        "late_bias": 0.0, "climate": "coastal_subtropical",
    },
}

# ── Per-climate, per-season modifier profiles ─────────────────────
# load_mult, fail_mult, rsrp_offset(dB), pp_mult(ping-pong), wrong_bias(extra
# wrong-cell share from ducting interference).
PROFILES = {
    "continental": {  # Kyiv: harsh snowy winter, deciduous foliage, mild summer
        "winter": {"load": 0.95, "fail": 1.60, "rsrp": -5.0, "pp": 1.20, "wrong": 0.00},
        "spring": {"load": 1.00, "fail": 1.05, "rsrp": -1.0, "pp": 1.00, "wrong": 0.00},
        "summer": {"load": 1.10, "fail": 1.20, "rsrp": -3.0, "pp": 1.05, "wrong": 0.03},
        "autumn": {"load": 1.00, "fail": 1.15, "rsrp": -2.0, "pp": 1.05, "wrong": 0.02},
    },
    "mountain": {  # Nagano: heavy snow + ski crowds winter, dense forest summer, typhoon autumn
        "winter": {"load": 1.25, "fail": 1.70, "rsrp": -5.0, "pp": 1.20, "wrong": 0.00},
        "spring": {"load": 0.95, "fail": 1.10, "rsrp": -2.0, "pp": 1.00, "wrong": 0.00},
        "summer": {"load": 1.00, "fail": 1.35, "rsrp": -5.0, "pp": 1.05, "wrong": 0.02},
        "autumn": {"load": 1.00, "fail": 1.45, "rsrp": -3.0, "pp": 1.15, "wrong": 0.03},
    },
    "coastal_subtropical": {  # Tokyo: mild winter, rainy/typhoon + Band41 TDD ducting summer/autumn
        "winter": {"load": 1.05, "fail": 1.05, "rsrp": -1.0, "pp": 1.00, "wrong": 0.00},
        "spring": {"load": 1.15, "fail": 1.10, "rsrp": -1.0, "pp": 1.15, "wrong": 0.05},
        "summer": {"load": 1.40, "fail": 1.30, "rsrp": -2.0, "pp": 1.50, "wrong": 0.20},
        "autumn": {"load": 1.10, "fail": 1.25, "rsrp": -2.0, "pp": 1.35, "wrong": 0.15},
    },
}


def haversine_m(lat1, lon1, lat2, lon2):
    R = 6_371_000
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def sround(x):
    """Stochastic rounding — preserves expected value for small counts so a
    fractional failure (e.g. 0.4) doesn't always floor to 0."""
    if x <= 0:
        return 0
    f = math.floor(x)
    return int(f + (1 if random.random() < (x - f) else 0))


def jitter(lat, lon, radius_km):
    dlat = random.uniform(-radius_km / 111, radius_km / 111)
    dlon = random.uniform(-radius_km / (111 * math.cos(math.radians(lat))),
                          radius_km / (111 * math.cos(math.radians(lat))))
    return round(lat + dlat, 6), round(lon + dlon, 6)


def split_failures(fail, late_bias, wrong_bias):
    """Distribute a failure count into (too_early, too_late, wrong_cell) using
    location/season biases, then clamp so the parts never exceed `fail`."""
    if fail <= 0:
        return 0, 0, 0
    late_share = min(0.75, 0.30 + late_bias)
    wrong_share = min(0.75, 0.20 + wrong_bias)
    early_share = max(0.05, 1.0 - late_share - wrong_share)
    # Stochastic (unbiased) rounding so the residual `wrong` bucket doesn't
    # silently absorb every flooring loss -> ratios hold at any failure volume.
    early = min(fail, sround(fail * early_share))
    late = min(fail - early, sround(fail * late_share))
    wrong = max(0, fail - early - late)
    return early, late, wrong


def generate(location_key: str, season: str, seed: int):
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

    # 3. pm_data_relation_level.csv
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
                hr = ts.hour
                load = 0.3
                if 7 <= hr <= 9:
                    load = 1.0 + 0.3 * math.sin(math.pi * (hr - 7) / 2)
                elif 11 <= hr <= 14:
                    load = 0.9
                elif 16 <= hr <= 20:
                    load = 1.2 + 0.2 * math.sin(math.pi * (hr - 16) / 4)
                elif hr >= 22 or hr <= 5:
                    load = 0.15
                load *= prof["load"]
                ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
                for cell in sites:
                    cid = cell["cell_id"]
                    is_problem = cid in problem_ids
                    cnbrs = nbr_by_cell.get(cid, [])
                    if not cnbrs:
                        continue
                    # Cell-level totals (large counts -> structure survives).
                    total_att = max(1, int(random.gauss(cfg["base_ho_rate"],
                                                        cfg["base_ho_rate"] * 0.25) * load))
                    base = (random.uniform(cfg["problem_fail_rate"] * 0.7, cfg["problem_fail_rate"] * 1.3)
                            if is_problem else
                            random.uniform(cfg["base_fail_rate"] * 0.5, cfg["base_fail_rate"] * 1.5))
                    fail_rate = min(0.6, base * prof["fail"])
                    total_fail = min(total_att, max(0, int(total_att * fail_rate)))
                    total_succ = total_att - total_fail
                    pp_base = 0.04 if is_problem else 0.015
                    total_pp = min(total_succ, max(0, int(total_succ
                                   * random.uniform(0.005, pp_base) * prof["pp"])))
                    # Split failures ONCE at cell level where counts are meaningful,
                    # then hand each category down to relations.
                    c_early, c_late, c_wrong = split_failures(
                        total_fail, cfg["late_bias"], prof["wrong"])

                    n = len(cnbrs)
                    weights = [random.random() ** 0.5 for _ in range(n)]
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

    print(f"  {location_key:12s} {season:6s}: {len(sites):3d} cells  "
          f"{len(neighbors):4d} rel  {rows:>8,} PM rows  "
          f"{n_problem} problem  -> {out.name}/")
    return rows


if __name__ == "__main__":
    seasons = ["winter", "spring", "summer", "autumn"]
    seed = 300
    grand = 0
    for loc in LOCATIONS:
        print(f"\n=== {loc} (all seasons) ===")
        for season in seasons:
            grand += generate(loc, season, seed)
            seed += 1
    n = len(LOCATIONS) * len(seasons)
    print(f"\nDone! {n} datasets ({len(LOCATIONS)} locations x {len(seasons)} seasons), "
          f"{grand:,} total PM rows under data/extra_geo/")
