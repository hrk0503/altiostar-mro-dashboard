#!/usr/bin/env python3
"""Generate LTE and 5G handover CSV datasets for different geographies.

Proves the pipeline is geography-agnostic by generating realistic
synthetic data for non-Tokyo clusters:
  1. Berlin LTE  — 20 sites x 3 sectors (60 cells), Band 3/7
  2. Seoul 5G NR — 15 sites x 3 sectors (45 cells), n78/n257

Output format matches the exact schema our MROEnv expects:
  - site_database.csv
  - neighbor_relations.csv
  - pm_data_relation_level.csv
  - cluster_kpi_summary.csv
"""

import csv
import math
import random
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent / "data"


def haversine_m(lat1, lon1, lat2, lon2):
    """Distance in meters between two lat/lon points."""
    R = 6_371_000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def jitter(lat, lon, radius_km=1.5):
    dlat = random.uniform(-radius_km / 111, radius_km / 111)
    dlon = random.uniform(
        -radius_km / (111 * math.cos(math.radians(lat))),
        radius_km / (111 * math.cos(math.radians(lat))),
    )
    return round(lat + dlat, 6), round(lon + dlon, 6)


def generate_cluster(
    *,
    output_dir: Path,
    prefix: str,          # e.g. "BRLN" or "SEOL"
    city_name: str,       # e.g. "Berlin" or "Seoul"
    center_lat: float,
    center_lon: float,
    num_sites: int,
    bands: list,          # e.g. ["Band 3 (1800MHz)", "Band 7 (2600MHz)"]
    vendor: str,
    technology: str,      # "LTE" or "5G NR"
    tac_base: int,
    clutter_types: list,
    problem_fraction: float = 0.08,
    base_ho_rate: float = 20.0,
    base_fail_rate: float = 0.02,
    problem_fail_rate: float = 0.08,
    days: int = 30,
    rops_per_day: int = 96,
    seed: int = 42,
):
    """Generate all 4 CSVs for a cluster."""
    random.seed(seed)
    output_dir.mkdir(parents=True, exist_ok=True)

    sectors_per_site = 3
    num_cells = num_sites * sectors_per_site

    # ========== 1. site_database.csv ==========
    sites = []
    for i in range(num_sites):
        lat, lon = jitter(center_lat, center_lon)
        band = bands[i % len(bands)]
        for s in range(1, sectors_per_site + 1):
            cell_id = f"{prefix}-{i + 1:03d}-{s}"
            enodeb_id = f"{prefix}-{i + 1:03d}"
            sites.append({
                "cell_id": cell_id,
                "enodeb_id": enodeb_id,
                "site_name": f"{city_name}-Site-{i + 1:03d}",
                "latitude": lat,
                "longitude": lon,
                "antenna_height_m": random.randint(25, 50),
                "sector": s,
                "azimuth_deg": (s - 1) * 120 + random.randint(-5, 5),
                "electrical_tilt_deg": random.randint(2, 6),
                "mechanical_tilt_deg": random.randint(0, 3),
                "total_tilt_deg": 0,  # filled below
                "clutter_type": random.choice(clutter_types),
                "elevation_m": round(random.uniform(30, 80), 1),
                "frequency_band": band,
                "pci": (i * sectors_per_site + s) % 504,
                "tac": tac_base + i,
                "vendor": vendor,
                "technology": technology,
                "status": "Active",
            })
            sites[-1]["total_tilt_deg"] = (
                sites[-1]["electrical_tilt_deg"]
                + sites[-1]["mechanical_tilt_deg"]
            )

    site_path = output_dir / "site_database.csv"
    with open(site_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=sites[0].keys())
        w.writeheader()
        w.writerows(sites)
    print(f"  {site_path.name}: {len(sites)} cells")

    # ========== 2. neighbor_relations.csv ==========
    neighbors = []
    {c["cell_id"]: c for c in sites}

    for cell in sites:
        candidates = sorted(
            [c for c in sites if c["cell_id"] != cell["cell_id"]],
            key=lambda c: haversine_m(
                cell["latitude"], cell["longitude"],
                c["latitude"], c["longitude"],
            ),
        )
        n_nbrs = random.randint(8, min(14, len(candidates)))
        for rank, nbr in enumerate(candidates[:n_nbrs], 1):
            dist = haversine_m(
                cell["latitude"], cell["longitude"],
                nbr["latitude"], nbr["longitude"],
            )
            neighbors.append({
                "serving_cell": cell["cell_id"],
                "neighbor_cell": nbr["cell_id"],
                "neighbor_rank": rank,
                "distance_m": round(dist, 1),
                "cell_individual_offset_dB": round(random.uniform(-6, 6), 1),
                "handover_allowed": "Yes",
                "relation_type": (
                    "Intra-Frequency"
                    if cell["frequency_band"] == nbr["frequency_band"]
                    else "Inter-Frequency"
                ),
                "last_updated": "2026-06-01",
            })

    nbr_path = output_dir / "neighbor_relations.csv"
    with open(nbr_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=neighbors[0].keys())
        w.writeheader()
        w.writerows(neighbors)
    print(f"  {nbr_path.name}: {len(neighbors)} relations")

    # Build lookup: serving_cell -> list of neighbor dicts
    nbr_by_cell = defaultdict(list)
    for n in neighbors:
        nbr_by_cell[n["serving_cell"]].append(n)

    # Problem cells
    n_problem = max(1, int(num_cells * problem_fraction))
    problem_ids = set(random.sample([c["cell_id"] for c in sites], n_problem))

    # ========== 3. pm_data_relation_level.csv ==========
    pm_path = output_dir / "pm_data_relation_level.csv"
    start_date = datetime(2026, 5, 1)
    row_count = 0

    with open(pm_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "timestamp_utc", "rop_duration_min",
            "source_cell_id", "target_cell_id",
            "ho_attempts", "ho_successes", "ho_failures",
            "too_early_ho", "too_late_ho", "wrong_cell",
            "correct_cell", "ping_pong", "cio_db",
        ])

        for day in range(days):
            for rop in range(rops_per_day):
                ts = start_date + timedelta(days=day, minutes=rop * 15)
                hour = ts.hour
                # Realistic load curve: peak 8-10 AM, 12-2 PM, 5-8 PM
                load = 0.3
                if 7 <= hour <= 9:
                    load = 1.0 + 0.3 * math.sin(math.pi * (hour - 7) / 2)
                elif 11 <= hour <= 14:
                    load = 0.9
                elif 16 <= hour <= 20:
                    load = 1.2 + 0.2 * math.sin(math.pi * (hour - 16) / 4)
                elif hour >= 22 or hour <= 5:
                    load = 0.15

                ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")

                for cell in sites:
                    cid = cell["cell_id"]
                    is_problem = cid in problem_ids
                    cell_nbrs = nbr_by_cell.get(cid, [])
                    if not cell_nbrs:
                        continue

                    # Total cell-level HO attempts this ROP
                    total_att = max(
                        1,
                        int(random.gauss(base_ho_rate, base_ho_rate * 0.25) * load),
                    )

                    fail_rate = (
                        random.uniform(problem_fail_rate * 0.7, problem_fail_rate * 1.3)
                        if is_problem
                        else random.uniform(base_fail_rate * 0.5, base_fail_rate * 1.5)
                    )
                    total_fail = max(0, int(total_att * fail_rate))
                    total_succ = total_att - total_fail
                    total_pp = max(0, int(total_succ * random.uniform(0.005, 0.04 if is_problem else 0.015)))

                    # Distribute across neighbors
                    n = len(cell_nbrs)
                    weights = [random.random() ** 0.5 for _ in range(n)]
                    wsum = sum(weights) or 1

                    for j, nbr in enumerate(cell_nbrs):
                        frac = weights[j] / wsum
                        att = max(0, int(total_att * frac + random.gauss(0, 0.5)))
                        fail = min(att, max(0, int(total_fail * frac + random.gauss(0, 0.3))))
                        succ = att - fail
                        pp = min(succ, max(0, int(total_pp * frac)))

                        # Failure breakdown
                        early = max(0, int(fail * random.uniform(0.15, 0.35)))
                        late = max(0, int(fail * random.uniform(0.2, 0.45)))
                        wrong = max(0, min(fail - early - late, int(fail * random.uniform(0.1, 0.3))))

                        w.writerow([
                            ts_str, 15,
                            cid, nbr["neighbor_cell"],
                            att, succ, fail,
                            early, late, wrong,
                            succ, pp,
                            nbr["cell_individual_offset_dB"],
                        ])
                        row_count += 1

    print(f"  {pm_path.name}: {row_count:,} rows")

    # ========== 4. cluster_kpi_summary.csv ==========
    kpi_path = output_dir / "cluster_kpi_summary.csv"
    kpis = []
    for cell in sites:
        cid = cell["cell_id"]
        is_problem = cid in problem_ids
        total_att = random.randint(150_000, 300_000)
        fail_pct = round(random.uniform(4.0, 10.0) if is_problem else random.uniform(0.5, 2.5), 2)
        total_fail = int(total_att * fail_pct / 100)
        total_succ = total_att - total_fail
        pp_pct = round(random.uniform(2.0, 5.0) if is_problem else random.uniform(0.3, 1.5), 2)

        kpis.append({
            "cell_id": cid,
            "enodeb_id": cell["enodeb_id"],
            "clutter_type": cell["clutter_type"],
            "total_ho_attempts": total_att,
            "total_ho_success": total_succ,
            "total_ho_failures": total_fail,
            "ho_failure_rate_pct": fail_pct,
            "failure_too_early": int(total_fail * random.uniform(0.15, 0.35)),
            "failure_too_late": int(total_fail * random.uniform(0.25, 0.45)),
            "failure_wrong_cell": int(total_fail * random.uniform(0.1, 0.3)),
            "total_pingpong": int(total_succ * pp_pct / 100),
            "pingpong_rate_pct": pp_pct,
            "avg_rsrp_dBm": round(random.gauss(-95 if is_problem else -82, 4), 1),
            "problem_cell": "Yes" if is_problem else "No",
        })

    with open(kpi_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=kpis[0].keys())
        w.writeheader()
        w.writerows(kpis)
    print(f"  {kpi_path.name}: {len(kpis)} cells")

    print(f"  Problem cells: {sorted(problem_ids)}")
    return len(sites), len(neighbors), row_count


# ============================================================
# Generate both clusters
# ============================================================
if __name__ == "__main__":
    print("\n=== Berlin LTE Cluster ===")
    generate_cluster(
        output_dir=BASE_DIR / "berlin_lte",
        prefix="BRLN",
        city_name="Berlin",
        center_lat=52.5200,
        center_lon=13.4050,
        num_sites=20,
        bands=["Band 3 (1800MHz)", "Band 7 (2600MHz)"],
        vendor="Nokia",
        technology="LTE",
        tac_base=20001,
        clutter_types=["Dense Urban", "Urban", "Suburban"],
        problem_fraction=0.08,
        base_ho_rate=18.0,
        base_fail_rate=0.025,
        problem_fail_rate=0.09,
        days=30,
        seed=100,
    )

    print("\n=== Seoul 5G NR Cluster ===")
    generate_cluster(
        output_dir=BASE_DIR / "seoul_5g",
        prefix="SEOL",
        city_name="Seoul",
        center_lat=37.5665,
        center_lon=126.9780,
        num_sites=15,
        bands=["n78 (3500MHz)", "n257 (28GHz)"],
        vendor="Samsung",
        technology="5G NR",
        tac_base=30001,
        clutter_types=["Dense Urban", "Urban", "High-Rise"],
        problem_fraction=0.10,
        base_ho_rate=25.0,    # 5G has more frequent HOs
        base_fail_rate=0.03,  # slightly higher fail rate
        problem_fail_rate=0.10,
        days=30,
        seed=200,
    )

    print("\nDone! Both datasets generated.")
