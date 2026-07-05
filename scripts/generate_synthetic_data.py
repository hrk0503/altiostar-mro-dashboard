"""
Generate 4 synthetic CSVs for Altiostar MRO pipeline.
Based on specs: 25 sites x 3 sectors (75 cells), Shibuya area, Band 1/3/41.
"""
import csv
import math
import random
from datetime import datetime, timedelta

random.seed(42)

# --- Constants ---
BANDS = [1, 3, 41]
SHIBUYA_CENTER = (35.6580, 139.7016)
NUM_SITES = 25
SECTORS_PER_SITE = 3
NUM_CELLS = NUM_SITES * SECTORS_PER_SITE  # 75

def jitter(lat, lon, radius_km=2.0):
    dlat = random.uniform(-radius_km / 111, radius_km / 111)
    dlon = random.uniform(-radius_km / (111 * math.cos(math.radians(lat))),
                           radius_km / (111 * math.cos(math.radians(lat))))
    return round(lat + dlat, 6), round(lon + dlon, 6)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))

# ========== 1. site_database.csv ==========
sites = []
for i in range(NUM_SITES):
    lat, lon = jitter(*SHIBUYA_CENTER)
    band = BANDS[i % 3]
    for s in range(SECTORS_PER_SITE):
        cell_id = f"CELL_{i:03d}_{s}"
        sites.append({
            "cell_id": cell_id,
            "site_id": f"SITE_{i:03d}",
            "sector": s,
            "band": band,
            "latitude": lat,
            "longitude": lon,
            "azimuth": s * 120 + random.randint(-5, 5),
            "mechanical_tilt": round(random.uniform(2.0, 8.0), 1),
            "electrical_tilt": round(random.uniform(0.0, 6.0), 1),
            "tx_power_dbm": round(random.uniform(40.0, 46.0), 1),
            "antenna_height_m": round(random.uniform(20.0, 45.0), 1),
            "frequency_mhz": {1: 2100, 3: 1800, 41: 2500}[band],
        })

with open("data/synthetic/site_database.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=sites[0].keys())
    w.writeheader()
    w.writerows(sites)
print(f"site_database.csv: {len(sites)} rows")

# ========== 2. neighbor_relations.csv ==========
neighbors = []
for cell in sites:
    n_neighbors = random.randint(8, 12)
    candidates = [c for c in sites if c["cell_id"] != cell["cell_id"]]
    candidates.sort(key=lambda c: haversine(cell["latitude"], cell["longitude"],
                                             c["latitude"], c["longitude"]))
    for nb in candidates[:n_neighbors]:
        dist = haversine(cell["latitude"], cell["longitude"],
                         nb["latitude"], nb["longitude"])
        neighbors.append({
            "source_cell": cell["cell_id"],
            "target_cell": nb["cell_id"],
            "cio_db": round(random.uniform(-6.0, 6.0), 1),
            "distance_km": round(dist, 3),
            "handover_count_monthly": random.randint(50, 5000),
            "handover_success_rate": round(random.uniform(0.88, 0.99), 4),
            "ping_pong_rate": round(random.uniform(0.01, 0.08), 4),
        })

with open("data/synthetic/neighbor_relations.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=neighbors[0].keys())
    w.writeheader()
    w.writerows(neighbors)
print(f"neighbor_relations.csv: {len(neighbors)} rows")

# ========== 3. pm_data_april2026.csv ==========
# 75 cells x 30 days x 96 ROPs (15-min intervals) = 216,000 rows
start_date = datetime(2026, 4, 1)
pm_rows = []
problem_cells = random.sample([c["cell_id"] for c in sites], 6)

with open("data/synthetic/pm_data_april2026.csv", "w", newline="") as f:
    fields = ["cell_id", "timestamp", "rsrp_dbm", "rsrq_db", "sinr_db",
              "prb_utilization_pct", "active_ue_count", "rrc_connected_ue",
              "ho_attempt", "ho_success", "ho_failure", "ho_ping_pong",
              "late_ho", "early_ho", "wrong_cell_ho",
              "dl_throughput_mbps", "ul_throughput_mbps",
              "cqi_avg", "rlf_count", "call_drop_rate_pct"]
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    count = 0
    for cell in sites:
        is_problem = cell["cell_id"] in problem_cells
        for day in range(30):
            for rop in range(96):
                ts = start_date + timedelta(days=day, minutes=rop * 15)
                hour = ts.hour
                load_factor = 1.0 + 0.5 * math.sin(math.pi * (hour - 6) / 12) if 6 <= hour <= 22 else 0.5

                ho_attempt = int(random.gauss(20, 5) * load_factor)
                ho_attempt = max(1, ho_attempt)
                if is_problem:
                    ho_fail = max(0, int(ho_attempt * random.uniform(0.04, 0.12)))
                    ho_pp = max(0, int(ho_attempt * random.uniform(0.03, 0.08)))
                else:
                    ho_fail = max(0, int(ho_attempt * random.uniform(0.005, 0.025)))
                    ho_pp = max(0, int(ho_attempt * random.uniform(0.005, 0.02)))
                ho_success = ho_attempt - ho_fail

                row = {
                    "cell_id": cell["cell_id"],
                    "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%S"),
                    "rsrp_dbm": round(max(-140, min(-40, random.gauss(-85 if not is_problem else -95, 8))), 1),
                    "rsrq_db": round(max(-30, min(0, random.gauss(-10 if not is_problem else -14, 3))), 1),
                    "sinr_db": round(max(-10, min(40, random.gauss(12 if not is_problem else 5, 4))), 1),
                    "prb_utilization_pct": round(min(100, max(0, random.gauss(45, 20) * load_factor)), 1),
                    "active_ue_count": max(0, int(random.gauss(30, 10) * load_factor)),
                    "rrc_connected_ue": max(0, int(random.gauss(50, 15) * load_factor)),
                    "ho_attempt": ho_attempt,
                    "ho_success": ho_success,
                    "ho_failure": ho_fail,
                    "ho_ping_pong": ho_pp,
                    "late_ho": max(0, int(ho_fail * random.uniform(0.2, 0.5))),
                    "early_ho": max(0, int(ho_fail * random.uniform(0.1, 0.3))),
                    "wrong_cell_ho": max(0, int(ho_fail * random.uniform(0.05, 0.2))),
                    "dl_throughput_mbps": round(max(0, random.gauss(80 if not is_problem else 40, 20)), 1),
                    "ul_throughput_mbps": round(max(0, random.gauss(20 if not is_problem else 10, 5)), 1),
                    "cqi_avg": round(min(15, max(1, random.gauss(10 if not is_problem else 6, 2))), 1),
                    "rlf_count": max(0, int(random.gauss(2 if not is_problem else 8, 3))),
                    "call_drop_rate_pct": round(max(0, random.gauss(0.5 if not is_problem else 2.5, 0.8)), 2),
                }
                w.writerow(row)
                count += 1

print(f"pm_data_april2026.csv: {count} rows")

# ========== 4. cluster_kpi_summary.csv ==========
summaries = []
for cell in sites:
    is_problem = cell["cell_id"] in problem_cells
    ho_success_rate = round(random.uniform(0.88, 0.94) if is_problem else random.uniform(0.96, 0.995), 4)
    summaries.append({
        "cell_id": cell["cell_id"],
        "site_id": cell["site_id"],
        "band": cell["band"],
        "monthly_ho_attempts": random.randint(40000, 80000),
        "monthly_ho_success_rate": ho_success_rate,
        "monthly_ho_failure_rate": round(1 - ho_success_rate, 4),
        "monthly_ping_pong_rate": round(random.uniform(0.03, 0.07) if is_problem else random.uniform(0.005, 0.02), 4),
        "avg_rsrp_dbm": round(random.gauss(-95 if is_problem else -85, 3), 1),
        "avg_sinr_db": round(random.gauss(5 if is_problem else 12, 2), 1),
        "avg_prb_utilization_pct": round(random.uniform(60, 85) if is_problem else random.uniform(25, 55), 1),
        "avg_dl_throughput_mbps": round(random.gauss(40 if is_problem else 80, 10), 1),
        "total_rlf_count": random.randint(150, 400) if is_problem else random.randint(10, 60),
        "problem_flag": is_problem,
    })

with open("data/synthetic/cluster_kpi_summary.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=summaries[0].keys())
    w.writeheader()
    w.writerows(summaries)
print(f"cluster_kpi_summary.csv: {len(summaries)} rows")

print(f"\nProblem cells: {problem_cells}")
print("All 4 CSVs generated successfully!")
