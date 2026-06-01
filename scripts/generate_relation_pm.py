"""Generate relation-level PM data CSV from existing cell-level data + neighbor relations.

SD confirmed (May 27): PM counters are at RELATION level — serving_cell → neighbor_cell
per 15-min ROP. This script distributes cell-level HO counts across neighbor relations
to produce the granularity that matches real Altiostar .per → CSV exports.

Output: data/synthetic/pm_data_relation_level.csv
Keeps: data/synthetic/pm_data_april2026.csv (cell-level, unchanged)
"""
import csv
import random
from collections import defaultdict
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "synthetic"
CELL_PM = DATA_DIR / "pm_data_april2026.csv"
NEIGHBORS = DATA_DIR / "neighbor_relations.csv"
OUTPUT = DATA_DIR / "pm_data_relation_level.csv"

random.seed(42)


def load_neighbors() -> dict[str, list[dict]]:
    """Load neighbor relations grouped by serving cell."""
    by_cell: dict[str, list[dict]] = defaultdict(list)
    with open(NEIGHBORS) as f:
        reader = csv.DictReader(f)
        for row in reader:
            by_cell[row["serving_cell"]].append(row)
    return dict(by_cell)


def distribute_count(total: int, n_buckets: int) -> list[int]:
    """Distribute an integer total across n buckets with realistic skew."""
    if n_buckets == 0 or total == 0:
        return [0] * max(n_buckets, 1)
    weights = [random.random() ** 0.5 for _ in range(n_buckets)]
    wsum = sum(weights)
    raw = [total * w / wsum for w in weights]
    result = [int(r) for r in raw]
    remainder = total - sum(result)
    for i in range(abs(remainder)):
        idx = i % n_buckets
        result[idx] += 1 if remainder > 0 else -1
    return [max(0, r) for r in result]


def main() -> None:
    neighbors = load_neighbors()
    rows_written = 0

    with open(CELL_PM) as fin, open(OUTPUT, "w", newline="") as fout:
        reader = csv.DictReader(fin)
        writer = csv.writer(fout)
        writer.writerow([
            "timestamp_utc", "rop_duration_min",
            "source_cell_id", "target_cell_id",
            "ho_attempts", "ho_successes", "ho_failures",
            "too_early_ho", "too_late_ho", "wrong_cell",
            "correct_cell", "ping_pong",
            "cio_db",
        ])

        for row in reader:
            cell_id = row["cell_id"]
            ts = row["timestamp_utc"]
            rop = row["rop_duration_min"]

            nbrs = neighbors.get(cell_id, [])
            n = len(nbrs)
            if n == 0:
                continue

            attempts = int(row["ho_attempts_intra"])
            successes = int(row["ho_success_intra"])
            failures = int(row["ho_failure_intra"])
            too_early = int(row["ho_failure_too_early"])
            too_late = int(row["ho_failure_too_late"])
            wrong = int(row["ho_failure_wrong_cell"])
            pings = int(row["ho_pingpong_count"])

            d_attempts = distribute_count(attempts, n)
            d_successes = distribute_count(successes, n)
            d_failures = distribute_count(failures, n)
            d_early = distribute_count(too_early, n)
            d_late = distribute_count(too_late, n)
            d_wrong = distribute_count(wrong, n)
            d_pings = distribute_count(pings, n)

            for i, nbr in enumerate(nbrs):
                a = d_attempts[i]
                s = min(d_successes[i], a)
                f = min(d_failures[i], a - s)
                correct = s

                writer.writerow([
                    ts, rop,
                    cell_id, nbr["neighbor_cell"],
                    a, s, f,
                    min(d_early[i], f), min(d_late[i], f), min(d_wrong[i], f),
                    correct, min(d_pings[i], s),
                    nbr["cell_individual_offset_dB"],
                ])
                rows_written += 1

    print(f"Generated {rows_written:,} relation-level rows -> {OUTPUT}")
    print(f"Relations: {sum(len(v) for v in neighbors.values())} | ROPs per cell: {rows_written // max(sum(len(v) for v in neighbors.values()), 1)}")


if __name__ == "__main__":
    main()
