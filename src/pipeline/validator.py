"""Data quality validation for Altiostar MRO CSVs."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from src.pipeline.loader import DATA_DIR


@dataclass
class ValidationResult:
    csv_name: str
    total_rows: int
    null_counts: dict[str, int] = field(default_factory=dict)
    range_violations: list[str] = field(default_factory=list)
    type_mismatches: list[str] = field(default_factory=list)
    duplicate_rows: int = 0
    passed: bool = True

    def add_issue(self, issue: str) -> None:
        self.range_violations.append(issue)
        self.passed = False


RANGE_RULES: dict[str, dict[str, tuple[float | None, float | None]]] = {
    "site_database.csv": {
        "sector": (0, 2),
        "latitude": (34, 37),
        "longitude": (138, 141),
        "mechanical_tilt": (0, 15),
        "electrical_tilt": (0, 15),
        "tx_power_dbm": (20, 60),
        "antenna_height_m": (5, 100),
    },
    "neighbor_relations.csv": {
        "cio_db": (-15, 15),
        "distance_km": (0, 50),
        "handover_success_rate": (0, 1),
        "ping_pong_rate": (0, 1),
    },
    "pm_data_april2026.csv": {
        "rsrp_dbm": (-140, -40),
        "rsrq_db": (-30, 0),
        "sinr_db": (-10, 40),
        "prb_utilization_pct": (0, 100),
        "ho_attempt": (0, None),
        "ho_success": (0, None),
        "ho_failure": (0, None),
        "call_drop_rate_pct": (0, 100),
    },
    "cluster_kpi_summary.csv": {
        "monthly_ho_success_rate": (0, 1),
        "monthly_ho_failure_rate": (0, 1),
        "monthly_ping_pong_rate": (0, 1),
        "avg_prb_utilization_pct": (0, 100),
    },
}


def validate_csv(csv_name: str, path: Path | None = None) -> ValidationResult:
    """Run null checks, range checks, type mismatch detection, and duplicate detection."""
    p = path or DATA_DIR / csv_name
    df = pd.read_csv(p)
    result = ValidationResult(csv_name=csv_name, total_rows=len(df))

    # Null checks
    for col in df.columns:
        null_count = int(df[col].isnull().sum())
        if null_count > 0:
            result.null_counts[col] = null_count
            result.passed = False

    # Duplicate rows
    result.duplicate_rows = int(df.duplicated().sum())
    if result.duplicate_rows > 0:
        result.add_issue(f"{result.duplicate_rows} duplicate rows found")

    # Range checks
    rules = RANGE_RULES.get(csv_name, {})
    for col, (lo, hi) in rules.items():
        if col not in df.columns:
            result.add_issue(f"Missing expected column: {col}")
            continue
        series = pd.to_numeric(df[col], errors="coerce")
        if lo is not None:
            violations = int((series < lo).sum())
            if violations > 0:
                result.add_issue(f"{col}: {violations} values below minimum {lo}")
        if hi is not None:
            violations = int((series > hi).sum())
            if violations > 0:
                result.add_issue(f"{col}: {violations} values above maximum {hi}")

    # Type mismatches: check numeric columns are actually numeric
    for col in rules:
        if col in df.columns:
            coerced = pd.to_numeric(df[col], errors="coerce")
            mismatches = int(coerced.isnull().sum() - df[col].isnull().sum())
            if mismatches > 0:
                result.type_mismatches.append(f"{col}: {mismatches} non-numeric values")
                result.passed = False

    return result


def validate_all(data_dir: Path | None = None) -> dict[str, ValidationResult]:
    """Validate all 4 CSVs and return results."""
    csvs = [
        "site_database.csv",
        "neighbor_relations.csv",
        "pm_data_april2026.csv",
        "cluster_kpi_summary.csv",
    ]
    results = {}
    for csv_name in csvs:
        csv_path = (data_dir or DATA_DIR) / csv_name if data_dir else None
        results[csv_name] = validate_csv(csv_name, csv_path)
    return results


def print_validation_report(results: dict[str, ValidationResult]) -> None:
    """Print a human-readable validation report."""
    for name, r in results.items():
        status = "PASS" if r.passed else "FAIL"
        print(f"\n[{status}] {name} ({r.total_rows} rows)")
        if r.null_counts:
            print(f"  Nulls: {r.null_counts}")
        if r.range_violations:
            for v in r.range_violations:
                print(f"  Range: {v}")
        if r.type_mismatches:
            for t in r.type_mismatches:
                print(f"  Type: {t}")
        if r.duplicate_rows:
            print(f"  Duplicates: {r.duplicate_rows}")
