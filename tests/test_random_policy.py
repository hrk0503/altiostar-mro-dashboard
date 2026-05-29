"""Tests for random policy benchmark — episode runner, aggregation, I/O."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from src.benchmark.random_policy import (
    BenchmarkResult,
    EpisodeResult,
    _get_problem_cell_ids,
    _safe_rate,
    load_results,
    print_summary,
    run_benchmark,
    run_episode,
    save_results,
)
from src.pipeline.loader import DATA_DIR

# Skip entire module when synthetic CSVs are absent (CI)
pytestmark = pytest.mark.skipif(
    not (DATA_DIR / "pm_data_april2026.csv").exists(),
    reason="Synthetic CSVs not available in CI",
)

PM_PATH = str(DATA_DIR / "pm_data_april2026.csv")
KPI_PATH = str(DATA_DIR / "cluster_kpi_summary.csv")

# Known cells from synthetic data
NORMAL_CELL = "RKSB-001-1"
PROBLEM_CELL = "RKSB-001-3"


# ── Helper function tests ────────────────────────────────────


class TestSafeRate:
    def test_normal_rate(self) -> None:
        assert _safe_rate(95, 100) == pytest.approx(95.0)

    def test_zero_denominator(self) -> None:
        assert _safe_rate(10, 0) == 0.0

    def test_negative_denominator(self) -> None:
        assert _safe_rate(10, -1) == 0.0

    def test_full_success(self) -> None:
        assert _safe_rate(200, 200) == pytest.approx(100.0)

    def test_zero_numerator(self) -> None:
        assert _safe_rate(0, 100) == pytest.approx(0.0)


class TestGetProblemCellIds:
    def test_returns_frozenset(self) -> None:
        result = _get_problem_cell_ids(KPI_PATH)
        assert isinstance(result, frozenset)

    def test_known_problem_cells(self) -> None:
        result = _get_problem_cell_ids(KPI_PATH)
        assert PROBLEM_CELL in result
        assert NORMAL_CELL not in result

    def test_count_matches_data(self) -> None:
        result = _get_problem_cell_ids(KPI_PATH)
        # Synthetic data has 6 problem cells
        assert len(result) == 6


# ── Episode tests ────────────────────────────────────────────


class TestRunEpisode:
    def test_returns_episode_result(self) -> None:
        ep = run_episode(PM_PATH, KPI_PATH, NORMAL_CELL, seed=42)
        assert isinstance(ep, EpisodeResult)

    def test_cell_id_matches(self) -> None:
        ep = run_episode(PM_PATH, KPI_PATH, NORMAL_CELL, seed=42)
        assert ep.cell_id == NORMAL_CELL

    def test_steps_positive(self) -> None:
        ep = run_episode(PM_PATH, KPI_PATH, NORMAL_CELL, seed=42)
        assert ep.n_steps > 0

    def test_steps_equals_2880(self) -> None:
        """Each cell has 2880 time steps (30 days * 96 ROPs/day)."""
        ep = run_episode(PM_PATH, KPI_PATH, NORMAL_CELL, seed=42)
        assert ep.n_steps == 2880

    def test_ho_success_rate_in_range(self) -> None:
        ep = run_episode(PM_PATH, KPI_PATH, NORMAL_CELL, seed=42)
        assert 0 <= ep.ho_success_rate_pct <= 100

    def test_ho_failure_rate_in_range(self) -> None:
        ep = run_episode(PM_PATH, KPI_PATH, NORMAL_CELL, seed=42)
        assert 0 <= ep.ho_failure_rate_pct <= 100

    def test_pingpong_rate_in_range(self) -> None:
        ep = run_episode(PM_PATH, KPI_PATH, NORMAL_CELL, seed=42)
        assert 0 <= ep.pingpong_rate_pct <= 100

    def test_rates_sum_under_200(self) -> None:
        """Success + failure rates together should not exceed 200%."""
        ep = run_episode(PM_PATH, KPI_PATH, NORMAL_CELL, seed=42)
        assert ep.ho_success_rate_pct + ep.ho_failure_rate_pct <= 200.01

    def test_ho_counts_consistent(self) -> None:
        """success + failure should equal attempts (synthetic data is clean)."""
        ep = run_episode(PM_PATH, KPI_PATH, NORMAL_CELL, seed=42)
        assert ep.total_ho_success + ep.total_ho_failure == ep.total_ho_attempts

    def test_failure_breakdown_sums_to_total(self) -> None:
        ep = run_episode(PM_PATH, KPI_PATH, NORMAL_CELL, seed=42)
        breakdown = ep.failure_too_early + ep.failure_too_late + ep.failure_wrong_cell
        assert breakdown == ep.total_ho_failure

    def test_rsrp_in_valid_range(self) -> None:
        ep = run_episode(PM_PATH, KPI_PATH, NORMAL_CELL, seed=42)
        assert -140 <= ep.mean_rsrp_dBm <= -40

    def test_rsrq_in_valid_range(self) -> None:
        ep = run_episode(PM_PATH, KPI_PATH, NORMAL_CELL, seed=42)
        assert -30 <= ep.mean_rsrq_dB <= 0

    def test_sinr_in_valid_range(self) -> None:
        ep = run_episode(PM_PATH, KPI_PATH, NORMAL_CELL, seed=42)
        assert -10 <= ep.mean_sinr_dB <= 40

    def test_problem_cell_flagged(self) -> None:
        ep = run_episode(PM_PATH, KPI_PATH, PROBLEM_CELL, seed=42)
        assert ep.is_problem_cell is True

    def test_normal_cell_not_flagged(self) -> None:
        ep = run_episode(PM_PATH, KPI_PATH, NORMAL_CELL, seed=42)
        assert ep.is_problem_cell is False

    def test_reproducible_same_seed(self) -> None:
        ep1 = run_episode(PM_PATH, KPI_PATH, NORMAL_CELL, seed=42)
        ep2 = run_episode(PM_PATH, KPI_PATH, NORMAL_CELL, seed=42)
        assert ep1.total_reward == ep2.total_reward
        assert ep1.ho_success_rate_pct == ep2.ho_success_rate_pct
        assert ep1.n_steps == ep2.n_steps

    def test_problem_cell_worse_than_normal(self) -> None:
        """Problem cells should have lower HO success than normal cells."""
        prob = run_episode(PM_PATH, KPI_PATH, PROBLEM_CELL, seed=42)
        norm = run_episode(PM_PATH, KPI_PATH, NORMAL_CELL, seed=42)
        assert prob.ho_success_rate_pct < norm.ho_success_rate_pct

    def test_reward_sign_matches_kpis(self) -> None:
        """Mean reward should be positive (successes outweigh failures)."""
        ep = run_episode(PM_PATH, KPI_PATH, NORMAL_CELL, seed=42)
        assert ep.mean_reward_per_step > 0

    def test_invalid_cell_raises(self) -> None:
        with pytest.raises(ValueError, match="0 PM rows"):
            run_episode(PM_PATH, KPI_PATH, "NONEXISTENT-CELL-999", seed=42)

    def test_accepts_precomputed_problem_ids(self) -> None:
        """Passing problem_cell_ids avoids redundant CSV read."""
        ids = frozenset({PROBLEM_CELL})
        ep = run_episode(
            PM_PATH,
            KPI_PATH,
            PROBLEM_CELL,
            seed=42,
            problem_cell_ids=ids,
        )
        assert ep.is_problem_cell is True


# ── Benchmark tests ──────────────────────────────────────────


class TestRunBenchmark:
    def test_returns_benchmark_result(self) -> None:
        result = run_benchmark(cell_ids=[NORMAL_CELL], seed=42)
        assert isinstance(result, BenchmarkResult)

    def test_cell_count(self) -> None:
        cells = [NORMAL_CELL, "RKSB-001-2", PROBLEM_CELL]
        result = run_benchmark(cell_ids=cells, seed=42)
        assert result.n_cells == 3

    def test_problem_normal_split(self) -> None:
        cells = [NORMAL_CELL, "RKSB-001-2", PROBLEM_CELL]
        result = run_benchmark(cell_ids=cells, seed=42)
        assert result.n_problem_cells == 1
        assert result.n_normal_cells == 2

    def test_cluster_rates_valid_range(self) -> None:
        result = run_benchmark(cell_ids=[NORMAL_CELL, PROBLEM_CELL], seed=42)
        assert 0 <= result.cluster_ho_success_rate_pct <= 100
        assert 0 <= result.cluster_ho_failure_rate_pct <= 100
        assert 0 <= result.cluster_pingpong_rate_pct <= 100

    def test_percentiles_ordered(self) -> None:
        cells = [NORMAL_CELL, "RKSB-001-2", PROBLEM_CELL]
        result = run_benchmark(cell_ids=cells, seed=42)
        assert result.ho_success_rate_min <= result.ho_success_rate_p25
        assert result.ho_success_rate_p25 <= result.ho_success_rate_p50
        assert result.ho_success_rate_p50 <= result.ho_success_rate_p75
        assert result.ho_success_rate_p75 <= result.ho_success_rate_max

    def test_mean_between_min_and_max(self) -> None:
        cells = [NORMAL_CELL, "RKSB-001-2", PROBLEM_CELL]
        result = run_benchmark(cell_ids=cells, seed=42)
        assert result.ho_success_rate_min <= result.ho_success_rate_mean
        assert result.ho_success_rate_mean <= result.ho_success_rate_max

    def test_episodes_list_populated(self) -> None:
        cells = [NORMAL_CELL, PROBLEM_CELL]
        result = run_benchmark(cell_ids=cells, seed=42)
        assert len(result.episodes) == 2
        assert all(isinstance(e, EpisodeResult) for e in result.episodes)

    def test_seed_preserved(self) -> None:
        result = run_benchmark(cell_ids=[NORMAL_CELL], seed=123)
        assert result.seed == 123

    def test_problem_cells_worse_than_normal(self) -> None:
        cells = [NORMAL_CELL, "RKSB-001-2", PROBLEM_CELL]
        result = run_benchmark(cell_ids=cells, seed=42)
        assert result.problem_cells_ho_success_rate_pct < result.normal_cells_ho_success_rate_pct


# ── I/O tests ────────────────────────────────────────────────


class TestSaveLoad:
    def test_save_creates_file(self, tmp_path: Path) -> None:
        result = run_benchmark(cell_ids=[NORMAL_CELL], seed=42)
        out = save_results(result, tmp_path / "test.json")
        assert out.exists()

    def test_save_creates_parent_dirs(self, tmp_path: Path) -> None:
        result = run_benchmark(cell_ids=[NORMAL_CELL], seed=42)
        out = save_results(result, tmp_path / "sub" / "dir" / "test.json")
        assert out.exists()

    def test_json_parseable(self, tmp_path: Path) -> None:
        result = run_benchmark(cell_ids=[NORMAL_CELL], seed=42)
        out = save_results(result, tmp_path / "test.json")
        data = json.loads(out.read_text())
        assert data["n_cells"] == 1
        assert len(data["episodes"]) == 1

    def test_json_preserves_kpis(self, tmp_path: Path) -> None:
        result = run_benchmark(cell_ids=[NORMAL_CELL], seed=42)
        out = save_results(result, tmp_path / "test.json")
        data = json.loads(out.read_text())
        ep = data["episodes"][0]
        assert ep["cell_id"] == NORMAL_CELL
        assert 0 <= ep["ho_success_rate_pct"] <= 100

    def test_load_returns_dict(self, tmp_path: Path) -> None:
        result = run_benchmark(cell_ids=[NORMAL_CELL], seed=42)
        out = save_results(result, tmp_path / "test.json")
        loaded = load_results(out)
        assert isinstance(loaded, dict)
        assert loaded["seed"] == 42


# ── Print summary test ───────────────────────────────────────


class TestPrintSummary:
    def test_does_not_raise(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = run_benchmark(cell_ids=[NORMAL_CELL, PROBLEM_CELL], seed=42)
        print_summary(result)
        captured = capsys.readouterr()
        assert "RANDOM POLICY BENCHMARK" in captured.out
        assert "HO Success Rate" in captured.out

    def test_shows_problem_flag(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = run_benchmark(cell_ids=[PROBLEM_CELL], seed=42)
        print_summary(result)
        captured = capsys.readouterr()
        assert "PROBLEM" in captured.out


# ── Property-based tests ─────────────────────────────────────


class TestProperties:
    """Invariants that must hold for ANY cell in the synthetic data."""

    @pytest.fixture(params=["RKSB-001-1", "RKSB-001-3", "RKSB-005-2"])
    def episode(self, request: pytest.FixtureRequest) -> EpisodeResult:
        return run_episode(PM_PATH, KPI_PATH, request.param, seed=42)

    def test_success_plus_failure_equals_attempts(self, episode: EpisodeResult) -> None:
        assert episode.total_ho_success + episode.total_ho_failure == episode.total_ho_attempts

    def test_failure_breakdown_equals_total_failure(self, episode: EpisodeResult) -> None:
        breakdown = (
            episode.failure_too_early + episode.failure_too_late + episode.failure_wrong_cell
        )
        assert breakdown == episode.total_ho_failure

    def test_rates_are_percentages(self, episode: EpisodeResult) -> None:
        assert 0 <= episode.ho_success_rate_pct <= 100
        assert 0 <= episode.ho_failure_rate_pct <= 100
        assert 0 <= episode.pingpong_rate_pct <= 100

    def test_success_rate_plus_failure_rate_approximately_100(
        self,
        episode: EpisodeResult,
    ) -> None:
        """Success rate + failure rate should be ~100% (they partition attempts)."""
        total = episode.ho_success_rate_pct + episode.ho_failure_rate_pct
        assert total == pytest.approx(100.0, abs=0.01)

    def test_reward_is_finite(self, episode: EpisodeResult) -> None:
        assert np.isfinite(episode.total_reward)
        assert np.isfinite(episode.mean_reward_per_step)

    def test_signal_quality_finite(self, episode: EpisodeResult) -> None:
        assert np.isfinite(episode.mean_rsrp_dBm)
        assert np.isfinite(episode.mean_rsrq_dB)
        assert np.isfinite(episode.mean_sinr_dB)
