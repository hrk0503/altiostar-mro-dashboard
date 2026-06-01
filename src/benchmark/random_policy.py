"""Random policy benchmark for the MRO Gymnasium environment.

Establishes baseline KPIs by running the MROEnv with a random policy
(uniform-random actions at every step).  The v0 env replays historical
PM data -- actions are recorded but do NOT affect state transitions.
This captures the current network performance as the **before** in
before/after comparisons with trained RL agents.

Usage
-----
    from src.benchmark.random_policy import run_benchmark, print_summary
    result = run_benchmark()                    # all 75 cells
    print_summary(result)
    save_results(result, "results/random_baseline.json")

Or from the command line::

    python -m src.benchmark.random_policy
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from src.env.mro_env import MROEnv

logger = logging.getLogger(__name__)

# ── Default paths (mirrors src.pipeline.loader) ──────────────
DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "synthetic"
PM_DATA_PATH = DATA_DIR / "pm_data_april2026.csv"
KPI_PATH = DATA_DIR / "cluster_kpi_summary.csv"


# ── Result dataclasses ───────────────────────────────────────


@dataclass
class EpisodeResult:
    """KPI results from a single episode (one cell's full rollout)."""

    cell_id: str
    n_steps: int
    total_reward: float
    mean_reward_per_step: float

    # Handover KPIs — absolute counts over the episode
    total_ho_attempts: int
    total_ho_success: int
    total_ho_failure: int
    total_pingpong: int

    # Handover KPIs — rates (%)
    ho_success_rate_pct: float
    ho_failure_rate_pct: float
    pingpong_rate_pct: float

    # Failure breakdown (sub-categories of total_ho_failure)
    failure_too_early: int
    failure_too_late: int
    failure_wrong_cell: int

    # Signal quality — episode averages
    mean_rsrp_dBm: float
    mean_rsrq_dB: float
    mean_sinr_dB: float

    # Cell metadata
    is_problem_cell: bool


@dataclass
class BenchmarkResult:
    """Aggregated random-policy benchmark across all cells."""

    seed: int
    n_cells: int
    n_problem_cells: int
    n_normal_cells: int

    # Cluster-level KPIs (weighted by HO attempts)
    cluster_ho_success_rate_pct: float
    cluster_ho_failure_rate_pct: float
    cluster_pingpong_rate_pct: float
    cluster_mean_reward_per_step: float

    # Problem vs normal cell comparison
    problem_cells_ho_success_rate_pct: float
    normal_cells_ho_success_rate_pct: float

    # Distribution of per-cell HO success rates
    ho_success_rate_mean: float
    ho_success_rate_std: float
    ho_success_rate_min: float
    ho_success_rate_max: float
    ho_success_rate_p25: float
    ho_success_rate_p50: float
    ho_success_rate_p75: float

    # Per-cell episode results
    episodes: list[EpisodeResult] = field(default_factory=list)


# ── Helpers ──────────────────────────────────────────────────


def _get_problem_cell_ids(kpi_path: str | Path) -> frozenset[str]:
    """Read KPI summary and return the set of problem cell IDs."""
    kpi_df = pd.read_csv(kpi_path)
    col = "problem_cell" if "problem_cell" in kpi_df.columns else "problem_flag"
    mask = kpi_df[col].isin(["Yes", True, "true", "TRUE"])
    return frozenset(kpi_df.loc[mask, "cell_id"])


def _safe_rate(numerator: int, denominator: int) -> float:
    """Compute percentage rate, returning 0.0 when denominator is zero."""
    if denominator <= 0:
        return 0.0
    return numerator / denominator * 100.0


# ── Core functions ───────────────────────────────────────────


def run_episode(
    pm_data_path: str | Path,
    kpi_path: str | Path,
    cell_id: str,
    *,
    seed: int = 42,
    problem_cell_ids: frozenset[str] | None = None,
) -> EpisodeResult:
    """Run one full episode for a specific cell with random actions.

    Parameters
    ----------
    pm_data_path : path to pm_data CSV
    kpi_path : path to cluster_kpi_summary CSV
    cell_id : target cell identifier (e.g. ``"RKSB-001-1"``)
    seed : random seed for action sampling reproducibility
    problem_cell_ids : pre-computed set of problem cell IDs.
        When *None*, reads ``kpi_path`` to determine problem cells.

    Returns
    -------
    EpisodeResult
        Per-cell KPIs extracted from the episode rollout.

    Raises
    ------
    ValueError
        If ``cell_id`` has no rows in the PM data.
    """
    # Suppress the env's per-step replay-mode warning
    env_logger = logging.getLogger("src.env.mro_env")
    prev_level = env_logger.level
    env_logger.setLevel(logging.ERROR)

    try:
        env = MROEnv(
            pm_data_path=str(pm_data_path),
            kpi_path=str(kpi_path),
            cell_id=cell_id,
        )

        if env.n_steps == 0:
            msg = f"Cell '{cell_id}' has 0 PM rows — cannot run episode"
            raise ValueError(msg)

        obs, _info = env.reset(seed=seed)
        env.action_space.seed(seed)

        step_rewards: list[float] = []
        terminated = False

        while not terminated:
            action = env.action_space.sample()
            obs, reward, terminated, _truncated, _info = env.step(action)
            step_rewards.append(reward)
    finally:
        env_logger.setLevel(prev_level)

    # ── Extract KPIs from the cell's PM data ──
    cell_pm: pd.DataFrame = env.cell_pm

    total_attempts = int(cell_pm["ho_attempts_intra"].sum())
    total_success = int(cell_pm["ho_success_intra"].sum())
    total_failure = int(cell_pm["ho_failure_intra"].sum())
    total_pingpong = int(cell_pm["ho_pingpong_count"].sum())

    failure_early = int(cell_pm["ho_failure_too_early"].sum())
    failure_late = int(cell_pm["ho_failure_too_late"].sum())
    failure_wrong = int(cell_pm["ho_failure_wrong_cell"].sum())

    # ── Determine problem-cell flag ──
    if problem_cell_ids is None:
        problem_cell_ids = _get_problem_cell_ids(kpi_path)
    is_problem = cell_id in problem_cell_ids

    total_reward = sum(step_rewards)
    n_steps = len(step_rewards)

    return EpisodeResult(
        cell_id=cell_id,
        n_steps=n_steps,
        total_reward=round(total_reward, 4),
        mean_reward_per_step=round(total_reward / n_steps, 4) if n_steps > 0 else 0.0,
        total_ho_attempts=total_attempts,
        total_ho_success=total_success,
        total_ho_failure=total_failure,
        total_pingpong=total_pingpong,
        ho_success_rate_pct=round(_safe_rate(total_success, total_attempts), 4),
        ho_failure_rate_pct=round(_safe_rate(total_failure, total_attempts), 4),
        pingpong_rate_pct=round(_safe_rate(total_pingpong, total_attempts), 4),
        failure_too_early=failure_early,
        failure_too_late=failure_late,
        failure_wrong_cell=failure_wrong,
        mean_rsrp_dBm=round(float(cell_pm["avg_rsrp_dBm"].mean()), 2),
        mean_rsrq_dB=round(float(cell_pm["avg_rsrq_dB"].mean()), 2),
        mean_sinr_dB=round(float(cell_pm["avg_sinr_dB"].mean()), 2),
        is_problem_cell=is_problem,
    )


def run_benchmark(
    pm_data_path: str | Path | None = None,
    kpi_path: str | Path | None = None,
    cell_ids: list[str] | None = None,
    *,
    seed: int = 42,
) -> BenchmarkResult:
    """Run random-policy benchmark across multiple cells.

    Parameters
    ----------
    pm_data_path : path to PM data CSV (default: synthetic data)
    kpi_path : path to cluster KPI summary CSV (default: synthetic data)
    cell_ids : specific cells to benchmark (default: all 75 cells)
    seed : base seed; each cell gets ``seed + cell_index``

    Returns
    -------
    BenchmarkResult
        Cluster-level aggregates, per-cell episodes, distribution stats.
    """
    pm_path = str(pm_data_path or PM_DATA_PATH)
    kpi_p = str(kpi_path or KPI_PATH)

    # Read KPI summary once for cell list + problem flags
    kpi_df = pd.read_csv(kpi_p)
    if cell_ids is None:
        cell_ids = list(kpi_df["cell_id"])

    problem_ids = _get_problem_cell_ids(kpi_p)

    logger.info("Starting random-policy benchmark: %d cells, seed=%d", len(cell_ids), seed)

    episodes: list[EpisodeResult] = []
    for i, cid in enumerate(cell_ids):
        logger.info("  [%d/%d] %s", i + 1, len(cell_ids), cid)
        ep = run_episode(
            pm_path,
            kpi_p,
            cid,
            seed=seed + i,
            problem_cell_ids=problem_ids,
        )
        episodes.append(ep)

    # ── Cluster-level aggregation (weighted by HO attempts) ──
    total_attempts = sum(e.total_ho_attempts for e in episodes)
    total_success = sum(e.total_ho_success for e in episodes)
    total_failure = sum(e.total_ho_failure for e in episodes)
    total_pp = sum(e.total_pingpong for e in episodes)

    cluster_success = _safe_rate(total_success, total_attempts)
    cluster_failure = _safe_rate(total_failure, total_attempts)
    cluster_pp = _safe_rate(total_pp, total_attempts)

    # ── Problem vs normal cells ──
    prob_eps = [e for e in episodes if e.is_problem_cell]
    norm_eps = [e for e in episodes if not e.is_problem_cell]

    prob_att = sum(e.total_ho_attempts for e in prob_eps)
    prob_suc = sum(e.total_ho_success for e in prob_eps)
    norm_att = sum(e.total_ho_attempts for e in norm_eps)
    norm_suc = sum(e.total_ho_success for e in norm_eps)

    # ── Distribution of per-cell success rates ──
    rates = np.array([e.ho_success_rate_pct for e in episodes])

    return BenchmarkResult(
        seed=seed,
        n_cells=len(episodes),
        n_problem_cells=len(prob_eps),
        n_normal_cells=len(norm_eps),
        cluster_ho_success_rate_pct=round(cluster_success, 4),
        cluster_ho_failure_rate_pct=round(cluster_failure, 4),
        cluster_pingpong_rate_pct=round(cluster_pp, 4),
        cluster_mean_reward_per_step=round(
            float(np.mean([e.mean_reward_per_step for e in episodes])),
            4,
        ),
        problem_cells_ho_success_rate_pct=round(_safe_rate(prob_suc, prob_att), 4),
        normal_cells_ho_success_rate_pct=round(_safe_rate(norm_suc, norm_att), 4),
        ho_success_rate_mean=round(float(np.mean(rates)), 4),
        ho_success_rate_std=round(float(np.std(rates)), 4),
        ho_success_rate_min=round(float(np.min(rates)), 4),
        ho_success_rate_max=round(float(np.max(rates)), 4),
        ho_success_rate_p25=round(float(np.percentile(rates, 25)), 4),
        ho_success_rate_p50=round(float(np.percentile(rates, 50)), 4),
        ho_success_rate_p75=round(float(np.percentile(rates, 75)), 4),
        episodes=episodes,
    )


# ── I/O ──────────────────────────────────────────────────────


def save_results(result: BenchmarkResult, output_path: str | Path) -> Path:
    """Serialize benchmark results to JSON for later comparison.

    Returns
    -------
    Path to the written JSON file.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = asdict(result)
    path.write_text(json.dumps(data, indent=2, default=str))
    logger.info("Saved benchmark results -> %s", path)
    return path


def load_results(path: str | Path) -> dict[str, object]:
    """Load previously saved benchmark results from JSON."""
    return json.loads(Path(path).read_text())  # type: ignore[no-any-return]


# ── Console output ───────────────────────────────────────────


def print_summary(result: BenchmarkResult) -> None:
    """Print a human-readable benchmark summary to stdout."""
    sep = "=" * 64
    print(f"\n{sep}")
    print("  RANDOM POLICY BENCHMARK  --  BASELINE RESULTS")
    print(sep)
    print(
        f"  Cells: {result.n_cells}"
        f" ({result.n_problem_cells} problem, {result.n_normal_cells} normal)"
    )
    print(f"  Seed:  {result.seed}")
    print()
    print("  -- Cluster-Level KPIs (weighted by HO attempts) --")
    print(f"  HO Success Rate:  {result.cluster_ho_success_rate_pct:.2f}%")
    print(f"  HO Failure Rate:  {result.cluster_ho_failure_rate_pct:.2f}%")
    print(f"  Ping-Pong Rate:   {result.cluster_pingpong_rate_pct:.2f}%")
    print(f"  Mean Reward/Step: {result.cluster_mean_reward_per_step:.2f}")
    print()
    print("  -- Problem vs Normal Cells --")
    print(f"  Problem Cells HO Success: {result.problem_cells_ho_success_rate_pct:.2f}%")
    print(f"  Normal  Cells HO Success: {result.normal_cells_ho_success_rate_pct:.2f}%")
    print()
    print("  -- Per-Cell HO Success Rate Distribution --")
    print(f"  Mean: {result.ho_success_rate_mean:.2f}%  (std: {result.ho_success_rate_std:.2f})")
    print(f"  Min:  {result.ho_success_rate_min:.2f}%")
    print(f"  P25:  {result.ho_success_rate_p25:.2f}%")
    print(f"  P50:  {result.ho_success_rate_p50:.2f}%")
    print(f"  P75:  {result.ho_success_rate_p75:.2f}%")
    print(f"  Max:  {result.ho_success_rate_max:.2f}%")
    print()

    # Top-5 worst and best cells
    sorted_eps = sorted(result.episodes, key=lambda e: e.ho_success_rate_pct)

    print("  -- Top 5 Worst Cells --")
    for ep in sorted_eps[:5]:
        flag = " [PROBLEM]" if ep.is_problem_cell else ""
        print(
            f"  {ep.cell_id}: {ep.ho_success_rate_pct:.2f}% success,"
            f" {ep.pingpong_rate_pct:.2f}% ping-pong{flag}"
        )

    print()
    print("  -- Top 5 Best Cells --")
    for ep in sorted_eps[-5:]:
        print(f"  {ep.cell_id}: {ep.ho_success_rate_pct:.2f}% success")

    print(sep)


# ── CLI entry point ──────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    benchmark = run_benchmark()
    print_summary(benchmark)
    out = save_results(benchmark, "results/random_baseline.json")
    print(f"\nResults saved to {out}")
