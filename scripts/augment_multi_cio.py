#!/usr/bin/env python3
"""Augment relation-level PM data with multiple CIO values per relation.

Problem: The original generator assigns ONE CIO value per relation across
all 2880 ROPs. This makes RL fundamentally broken — the agent's CIO delta
actions always map back to the same single CIO, so actions have zero effect.

Fix: For each relation, add data at multiple CIO values with realistically
modulated HO outcomes. An "optimal" CIO is randomly assigned per relation
(offset from current CIO). At optimal CIO → lowest failures. Away from
optimal → higher failures, ping-pong, etc.

This creates a meaningful optimization landscape where the RL agent can
learn to adjust CIO values toward each relation's optimum.

Usage:
    python scripts/augment_multi_cio.py

Reads:  data/synthetic/pm_data_relation_level.csv (single-CIO)
Writes: data/synthetic/pm_data_relation_level.csv (multi-CIO, overwrites)
Backup: data/synthetic/pm_data_relation_level_single_cio.csv
"""
from __future__ import annotations

import csv
import shutil
from collections import defaultdict
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "synthetic"
INPUT = DATA_DIR / "pm_data_relation_level.csv"
BACKUP = DATA_DIR / "pm_data_relation_level_single_cio.csv"
OUTPUT = DATA_DIR / "pm_data_relation_level.csv"

# Reproducible
RNG = np.random.default_rng(42)

# CIO values to generate (dB). Covers the 3GPP range we use.
ALT_CIO_VALUES = [-6, -4, -2, -1, 0, 1, 2, 4, 6]

# How many rows to generate per alternative CIO value per relation
SAMPLES_PER_ALT_CIO = 100

# Optimal CIO offset range (from current CIO)
# Each relation gets a random optimal offset in this range
OPTIMAL_OFFSETS = [-2, -1, 1, 2]


def compute_failure_scale(cio: int, optimal_cio: float) -> float:
    """Compute failure scaling factor based on CIO deviation from optimal.

    At optimal CIO: failures are reduced to 0% (perfect).
    At current CIO: failures stay roughly the same (scale ~1.0).
    Far from optimal: failures increase significantly.

    Returns a multiplier for failure-related counters.
    """
    dev = abs(cio - optimal_cio)
    if dev < 0.5:
        return 0.0   # optimal → 100% failure reduction
    elif dev < 1.5:
        return 0.35   # close to optimal → 65% reduction
    elif dev < 2.5:
        return 0.7    # moderate → 30% reduction
    elif dev < 3.5:
        return 1.2    # slightly worse than baseline
    elif dev < 4.5:
        return 1.8    # worse
    elif dev < 5.5:
        return 2.5    # much worse
    else:
        return 3.5    # terrible


def modulate_row(
    base_row: dict,
    cio: int,
    optimal_cio: float,
) -> dict:
    """Create a modulated copy of a PM data row at a different CIO value.

    Adjusts HO failure counters based on deviation from optimal CIO.
    Keeps total attempts constant. Redistributes successes/failures.
    """
    row = dict(base_row)
    row["cio_db"] = str(cio)

    att = int(row["ho_attempts"])
    if att == 0:
        return row

    fail_scale = compute_failure_scale(cio, optimal_cio)

    # Scale failure-related counters
    orig_fail = int(row["ho_failures"])
    orig_early = int(row["too_early_ho"])
    orig_late = int(row["too_late_ho"])
    orig_wrong = int(row["wrong_cell"])
    orig_ping = int(row["ping_pong"])
    orig_succ = int(row["ho_successes"])

    # If original failures are 0, create some based on attempts
    base_fail_rate = orig_fail / att if att > 0 else 0.05
    if base_fail_rate < 0.005:
        base_fail_rate = 0.005  # minimum base rate for modulation

    # New failure count
    new_fail_rate = min(base_fail_rate * fail_scale, 0.95)
    new_fail = max(0, min(round(att * new_fail_rate), att - 1))

    # Redistribute failure types proportionally
    if new_fail > 0:
        total_orig_types = max(orig_early + orig_late + orig_wrong, 1)
        # If no original failure type breakdown, create realistic split
        if total_orig_types <= 1:
            # Typical split: 40% too_early, 30% too_late, 30% wrong_cell
            new_early = round(new_fail * 0.4)
            new_late = round(new_fail * 0.3)
            new_wrong = new_fail - new_early - new_late
        else:
            new_early = min(round(orig_early / total_orig_types * new_fail), new_fail)
            new_late = min(round(orig_late / total_orig_types * new_fail), new_fail - new_early)
            new_wrong = max(0, new_fail - new_early - new_late)

        # CIO direction affects failure types
        cio_diff = cio - optimal_cio
        if cio_diff > 0:
            # CIO too high → handover too easy → more too_early + ping_pong
            bonus = round(abs(cio_diff) * 0.5)
            new_early = min(new_early + bonus, new_fail)
        elif cio_diff < 0:
            # CIO too low → handover too hard → more too_late
            bonus = round(abs(cio_diff) * 0.5)
            new_late = min(new_late + bonus, new_fail)
    else:
        new_early = 0
        new_late = 0
        new_wrong = 0

    # Success = attempts - failures
    new_succ = max(0, att - new_fail)
    new_correct = new_succ

    # Ping-pong scales similarly but with a floor
    new_ping = max(0, min(round(max(orig_ping, 1) * fail_scale * 0.8), new_succ))

    # Add noise (±1) for realism only if attempts are large enough and not at optimal
    if att > 20 and fail_scale > 0.0:
        noise = int(RNG.integers(-1, 2))
        new_succ = max(0, min(new_succ + noise, att))
    new_fail = att - new_succ

    row["ho_successes"] = str(new_succ)
    row["ho_failures"] = str(new_fail)
    row["too_early_ho"] = str(min(new_early, new_fail))
    row["too_late_ho"] = str(min(new_late, new_fail))
    row["wrong_cell"] = str(min(new_wrong, new_fail))
    row["correct_cell"] = str(new_correct)
    row["ping_pong"] = str(min(new_ping, new_succ))

    return row


def main() -> None:
    if not INPUT.exists():
        print(f"ERROR: {INPUT} not found")
        return

    # Backup original
    print(f"Backing up original to {BACKUP.name} ...")
    shutil.copy2(INPUT, BACKUP)

    # Read all data, grouped by relation
    print("Reading existing PM data ...")
    relations: dict[tuple[str, str], list[dict]] = defaultdict(list)
    fieldnames: list[str] = []

    with open(INPUT) as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)  # type: ignore[arg-type]
        for row in reader:
            key = (row["source_cell_id"], row["target_cell_id"])
            relations[key].append(row)

    n_relations = len(relations)
    original_rows = sum(len(rows) for rows in relations.values())
    print(f"  {n_relations} relations, {original_rows:,} rows")

    # Assign optimal CIO per relation (snapped to ALT_CIO_VALUES to ensure we can hit it)
    print("Assigning optimal CIO per relation ...")
    optimal_cios: dict[tuple[str, str], float] = {}
    for key, rows in relations.items():
        current_cio = int(rows[0]["cio_db"])
        offset = int(RNG.choice(OPTIMAL_OFFSETS))
        target_optimal = np.clip(current_cio + offset, -6, 6)
        optimal = ALT_CIO_VALUES[np.argmin(np.abs(np.array(ALT_CIO_VALUES) - target_optimal))]
        if optimal == current_cio:
            idx = ALT_CIO_VALUES.index(optimal)
            if idx + 1 < len(ALT_CIO_VALUES):
                optimal = ALT_CIO_VALUES[idx + 1]
            else:
                optimal = ALT_CIO_VALUES[idx - 1]
        optimal_cios[key] = float(optimal)

    # Generate augmented data
    print("Generating multi-CIO augmented data ...")
    augmented_rows = 0
    all_output_rows: list[dict] = []

    for key, rows in relations.items():
        current_cio = int(rows[0]["cio_db"])
        optimal = optimal_cios[key]

        # Keep ALL original rows unchanged
        all_output_rows.extend(rows)

        # Generate alternative CIO variants
        for alt_cio in ALT_CIO_VALUES:
            if alt_cio == current_cio:
                continue  # skip — already have original data at this CIO

            # Sample base rows to modulate
            n_samples = min(SAMPLES_PER_ALT_CIO, len(rows))
            sample_indices = RNG.choice(len(rows), size=n_samples, replace=False)

            for idx in sample_indices:
                mod_row = modulate_row(rows[idx], alt_cio, optimal)
                all_output_rows.append(mod_row)
                augmented_rows += 1

    total_rows = len(all_output_rows)
    print(f"  Original: {original_rows:,} | Augmented: {augmented_rows:,} | Total: {total_rows:,}")

    # Write output
    print(f"Writing augmented data to {OUTPUT.name} ...")
    with open(OUTPUT, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_output_rows)

    print(f"Done! File size: {OUTPUT.stat().st_size / 1e6:.1f} MB")

    # Print summary
    print()
    print("Sample relation CIO distribution:")
    for i, (key, rows) in enumerate(relations.items()):
        if i >= 3:
            break
        current_cio = int(rows[0]["cio_db"])
        optimal = optimal_cios[key]
        cios_in_output = {current_cio: len(rows)}
        for alt_cio in ALT_CIO_VALUES:
            if alt_cio != current_cio:
                cios_in_output[alt_cio] = min(SAMPLES_PER_ALT_CIO, len(rows))
        print(f"  {key[0]} -> {key[1]}:")
        print(f"    Current CIO: {current_cio}, Optimal CIO: {optimal}")
        print(f"    CIO values: {sorted(cios_in_output.keys())}")
        print(f"    Rows per CIO: {dict(sorted(cios_in_output.items()))}")


if __name__ == "__main__":
    main()
