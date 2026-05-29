from __future__ import annotations

import pandas as pd


def ho_success_rate(df: pd.DataFrame) -> pd.Series:
    """
    HO Success % per cell = (ho_success_intra / ho_attempts_intra) * 100
    Returns 0.0 for cells with zero attempts (avoids division by zero).
    Aggregates across all ROPs for each cell_id.
    """
    grouped = df.groupby("cell_id")[["ho_success_intra", "ho_attempts_intra"]].sum()
    rate = grouped["ho_success_intra"] / grouped["ho_attempts_intra"].replace(0, float("nan")) * 100
    return rate.fillna(0.0).rename("ho_success_rate_pct")


def pingpong_rate(df: pd.DataFrame) -> pd.Series:
    """
    Ping-pong % per cell = (ho_pingpong_count / ho_success_intra) * 100
    Returns 0.0 for cells with zero successful HOs.
    Aggregates across all ROPs for each cell_id.
    """
    grouped = df.groupby("cell_id")[["ho_pingpong_count", "ho_success_intra"]].sum()
    rate = grouped["ho_pingpong_count"] / grouped["ho_success_intra"].replace(0, float("nan")) * 100
    return rate.fillna(0.0).rename("pingpong_rate_pct")


def failure_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """
    Failure breakdown % per cell across 3 failure modes:
      - too_early_pct  = ho_failure_too_early  / ho_failure_intra * 100
      - too_late_pct   = ho_failure_too_late   / ho_failure_intra * 100
      - wrong_cell_pct = ho_failure_wrong_cell / ho_failure_intra * 100
    Returns 0.0 for cells with zero total failures.
    Aggregates across all ROPs for each cell_id.
    """
    cols = [
        "ho_failure_intra",
        "ho_failure_too_early",
        "ho_failure_too_late",
        "ho_failure_wrong_cell",
    ]
    grouped = df.groupby("cell_id")[cols].sum()
    total = grouped["ho_failure_intra"].replace(0, float("nan"))

    breakdown = pd.DataFrame(index=grouped.index)
    breakdown["too_early_pct"]  = (grouped["ho_failure_too_early"]  / total * 100).fillna(0.0)
    breakdown["too_late_pct"]   = (grouped["ho_failure_too_late"]   / total * 100).fillna(0.0)
    breakdown["wrong_cell_pct"] = (grouped["ho_failure_wrong_cell"] / total * 100).fillna(0.0)
    return breakdown


def extract_all_kpis(df: pd.DataFrame) -> pd.DataFrame:
    """
    Combines all 3 KPI extractions into a single DataFrame indexed by cell_id.
    This is what the Streamlit dashboard and baseline comparison will consume.
    """
    success = ho_success_rate(df)
    pingpong = pingpong_rate(df)
    breakdown = failure_breakdown(df)
    return pd.concat([success, pingpong, breakdown], axis=1)