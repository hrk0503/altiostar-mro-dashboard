"""Tests for ScenarioLoader — validates loading, validation, and application of scenarios."""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from src.env.scenario_loader import (
    ScenarioLoader,
    ScenarioValidationError,
    load_scenario,
)

# ── Path to real scenario configs ──
SCENARIOS_DIR = Path(__file__).resolve().parents[1] / "configs" / "scenarios"


# ─────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────

@pytest.fixture
def loader() -> ScenarioLoader:
    """ScenarioLoader pointing to actual project scenarios."""
    return ScenarioLoader(SCENARIOS_DIR)


@pytest.fixture
def cell_pm_data() -> pd.DataFrame:
    """Synthetic cell-level PM data for testing scenario application."""
    rng = np.random.default_rng(42)
    n_rows = 100
    return pd.DataFrame({
        "cell_id": [f"SITE{i // 3 + 1:02d}{chr(65 + i % 3)}" for i in range(n_rows)],
        "timestamp": pd.date_range("2026-04-01", periods=n_rows, freq="h"),
        "rsrp_dbm": rng.uniform(-110, -70, n_rows),
        "sinr_db": rng.uniform(0, 25, n_rows),
        "prb_utilization_pct": rng.uniform(20, 80, n_rows),
        "connected_ues": rng.integers(10, 200, n_rows),
        "ho_attempt": rng.integers(50, 300, n_rows),
        "ho_success_intra": rng.integers(40, 280, n_rows),
        "ho_failure_intra": rng.integers(0, 20, n_rows),
        "ho_ping_pong": rng.integers(0, 10, n_rows),
    })


@pytest.fixture
def relation_pm_data() -> pd.DataFrame:
    """Synthetic relation-level PM data for testing scenario application."""
    rng = np.random.default_rng(42)
    n_rows = 200
    sources = [f"SITE{i // 3 + 1:02d}{chr(65 + i % 3)}" for i in range(15)]
    targets = [f"SITE{(i + 5) // 3 + 1:02d}{chr(65 + (i + 1) % 3)}" for i in range(15)]
    return pd.DataFrame({
        "source_cell_id": rng.choice(sources, n_rows),
        "target_cell_id": rng.choice(targets, n_rows),
        "cio_db": rng.choice([0, 2, 4, -2, -4], n_rows),
        "ho_attempts": rng.integers(10, 150, n_rows),
        "ho_successes": rng.integers(8, 140, n_rows),
        "ho_failures": rng.integers(0, 15, n_rows),
        "too_early_ho": rng.integers(0, 5, n_rows),
        "too_late_ho": rng.integers(0, 5, n_rows),
        "wrong_cell": rng.integers(0, 3, n_rows),
        "correct_cell": rng.integers(5, 100, n_rows),
        "ping_pong": rng.integers(0, 8, n_rows),
    })


# ─────────────────────────────────────────────────────────────────────
# Discovery & listing
# ─────────────────────────────────────────────────────────────────────

class TestScenarioDiscovery:
    """Tests for scenario listing and availability."""

    def test_available_includes_baseline(self, loader: ScenarioLoader) -> None:
        assert "baseline" in loader.available()

    def test_available_includes_all_three_scenarios(self, loader: ScenarioLoader) -> None:
        available = loader.available()
        assert "rush_hour" in available
        assert "rain_fade" in available
        assert "tower_failure" in available

    def test_available_returns_sorted(self, loader: ScenarioLoader) -> None:
        available = loader.available()
        assert available == sorted(available)

    def test_available_at_least_four(self, loader: ScenarioLoader) -> None:
        """Gate G3 requires >= 3 distinct scenarios + baseline."""
        assert len(loader.available()) >= 4


# ─────────────────────────────────────────────────────────────────────
# Loading & validation
# ─────────────────────────────────────────────────────────────────────

class TestScenarioLoading:
    """Tests for loading individual scenarios."""

    def test_load_baseline(self, loader: ScenarioLoader) -> None:
        config = loader.load("baseline")
        assert config["name"] == "baseline"

    def test_load_rush_hour(self, loader: ScenarioLoader) -> None:
        config = loader.load("rush_hour")
        assert config["name"] == "rush_hour"
        assert config["ue_multiplier"] == 3.0
        assert config["prb_floor"] == 0.7
        assert config["ho_attempt_multiplier"] == 2.0

    def test_load_rain_fade(self, loader: ScenarioLoader) -> None:
        config = loader.load("rain_fade")
        assert config["name"] == "rain_fade"
        assert config["rsrp_offset_db"] == -5.0
        assert config["sinr_offset_db"] == -3.0
        assert config["ho_failure_multiplier"] == 1.5

    def test_load_tower_failure(self, loader: ScenarioLoader) -> None:
        config = loader.load("tower_failure")
        assert config["name"] == "tower_failure"
        assert config["failed_sites"] == 1
        assert config["neighbor_load_multiplier"] == 2.5
        assert config["ho_attempt_spike"] == 5.0

    def test_load_nonexistent_raises(self, loader: ScenarioLoader) -> None:
        with pytest.raises(FileNotFoundError, match="not found"):
            loader.load("nonexistent_scenario")

    def test_load_caching(self, loader: ScenarioLoader) -> None:
        """Loading the same scenario twice returns equal but independent dicts."""
        c1 = loader.load("rush_hour")
        c2 = loader.load("rush_hour")
        assert c1 == c2
        c1["ue_multiplier"] = 999  # mutation shouldn't affect cache
        c3 = loader.load("rush_hour")
        assert c3["ue_multiplier"] == 3.0

    def test_load_all(self, loader: ScenarioLoader) -> None:
        all_configs = loader.load_all()
        assert "baseline" in all_configs
        assert "rush_hour" in all_configs
        assert len(all_configs) >= 4


class TestScenarioValidation:
    """Tests for scenario config validation."""

    def test_invalid_yaml_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_file = Path(tmpdir) / "bad.yaml"
            bad_file.write_text("scenario:\n  ue_multiplier: [invalid")
            loader = ScenarioLoader(tmpdir)
            with pytest.raises(ScenarioValidationError, match="Invalid YAML"):
                loader.load("bad")

    def test_out_of_range_multiplier_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_file = Path(tmpdir) / "extreme.yaml"
            bad_file.write_text(yaml.dump({
                "scenario": {"name": "extreme", "ue_multiplier": 100.0}
            }))
            loader = ScenarioLoader(tmpdir)
            with pytest.raises(ScenarioValidationError, match="out of range"):
                loader.load("extreme")

    def test_negative_multiplier_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_file = Path(tmpdir) / "negative.yaml"
            bad_file.write_text(yaml.dump({
                "scenario": {"name": "negative", "ue_multiplier": -1.0}
            }))
            loader = ScenarioLoader(tmpdir)
            with pytest.raises(ScenarioValidationError, match="out of range"):
                loader.load("negative")

    def test_empty_file_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_file = Path(tmpdir) / "empty.yaml"
            empty_file.write_text("")
            loader = ScenarioLoader(tmpdir)
            with pytest.raises(ScenarioValidationError, match="empty"):
                loader.load("empty")

    def test_valid_custom_scenario(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            custom = Path(tmpdir) / "custom.yaml"
            custom.write_text(yaml.dump({
                "scenario": {
                    "name": "custom",
                    "description": "Custom test",
                    "ue_multiplier": 2.0,
                    "rsrp_offset_db": -3.0,
                }
            }))
            loader = ScenarioLoader(tmpdir)
            config = loader.load("custom")
            assert config["ue_multiplier"] == 2.0
            assert config["rsrp_offset_db"] == -3.0


# ─────────────────────────────────────────────────────────────────────
# Application to PM data
# ─────────────────────────────────────────────────────────────────────

class TestScenarioApplication:
    """Tests for applying scenarios to PM data."""

    def test_baseline_returns_copy(
        self, loader: ScenarioLoader, cell_pm_data: pd.DataFrame
    ) -> None:
        result = loader.apply(cell_pm_data, "baseline")
        pd.testing.assert_frame_equal(result, cell_pm_data)
        # Must be a copy, not the same object
        assert result is not cell_pm_data

    def test_rush_hour_multiplies_ue(
        self, loader: ScenarioLoader, cell_pm_data: pd.DataFrame
    ) -> None:
        original_ues = cell_pm_data["connected_ues"].sum()
        result = loader.apply(cell_pm_data, "rush_hour", mode="cell")
        # UE count should be ~3x
        assert result["connected_ues"].sum() > original_ues * 2.5

    def test_rush_hour_multiplies_ho_attempts(
        self, loader: ScenarioLoader, cell_pm_data: pd.DataFrame
    ) -> None:
        original = cell_pm_data["ho_attempt"].sum()
        result = loader.apply(cell_pm_data, "rush_hour", mode="cell")
        # HO attempts should be ~2x
        assert result["ho_attempt"].sum() > original * 1.8

    def test_rush_hour_prb_floor(
        self, loader: ScenarioLoader, cell_pm_data: pd.DataFrame
    ) -> None:
        result = loader.apply(cell_pm_data, "rush_hour", mode="cell")
        assert result["prb_utilization_pct"].min() >= 70.0

    def test_rain_fade_lowers_rsrp(
        self, loader: ScenarioLoader, cell_pm_data: pd.DataFrame
    ) -> None:
        original_mean = cell_pm_data["rsrp_dbm"].mean()
        result = loader.apply(cell_pm_data, "rain_fade", mode="cell")
        # RSRP should be ~5 dB lower
        assert result["rsrp_dbm"].mean() < original_mean - 4.0

    def test_rain_fade_lowers_sinr(
        self, loader: ScenarioLoader, cell_pm_data: pd.DataFrame
    ) -> None:
        original_mean = cell_pm_data["sinr_db"].mean()
        result = loader.apply(cell_pm_data, "rain_fade", mode="cell")
        assert result["sinr_db"].mean() < original_mean - 2.0

    def test_rain_fade_increases_failures(
        self, loader: ScenarioLoader, cell_pm_data: pd.DataFrame
    ) -> None:
        original = cell_pm_data["ho_failure_intra"].sum()
        result = loader.apply(cell_pm_data, "rain_fade", mode="cell")
        assert result["ho_failure_intra"].sum() > original * 1.3

    def test_tower_failure_removes_cells(
        self, loader: ScenarioLoader, cell_pm_data: pd.DataFrame
    ) -> None:
        result = loader.apply(
            cell_pm_data, "tower_failure", mode="cell",
            rng=np.random.default_rng(42),
        )
        # Some cells should have zeroed-out metrics
        zero_mask = result.select_dtypes(include=[np.number]).sum(axis=1) == 0
        assert zero_mask.any(), "Tower failure should zero out some cells"

    def test_tower_failure_relation_mode(
        self, loader: ScenarioLoader, relation_pm_data: pd.DataFrame
    ) -> None:
        original_rows = len(relation_pm_data)
        result = loader.apply(
            relation_pm_data, "tower_failure", mode="relation",
            rng=np.random.default_rng(42),
        )
        # Should have fewer rows (failed site's relations removed)
        assert len(result) < original_rows

    def test_auto_mode_detection_cell(
        self, loader: ScenarioLoader, cell_pm_data: pd.DataFrame
    ) -> None:
        """Auto mode should detect cell-level data (no source_cell_id column)."""
        result = loader.apply(cell_pm_data, "rush_hour")  # mode="auto"
        assert result["connected_ues"].sum() > cell_pm_data["connected_ues"].sum()

    def test_auto_mode_detection_relation(
        self, loader: ScenarioLoader, relation_pm_data: pd.DataFrame
    ) -> None:
        """Auto mode should detect relation-level data (has source_cell_id)."""
        result = loader.apply(relation_pm_data, "rain_fade")
        # Should run without error — auto-detected relation mode
        assert len(result) > 0

    def test_original_data_unchanged(
        self, loader: ScenarioLoader, cell_pm_data: pd.DataFrame
    ) -> None:
        """Applying a scenario should not mutate the original DataFrame."""
        original_copy = cell_pm_data.copy()
        loader.apply(cell_pm_data, "rush_hour", mode="cell")
        pd.testing.assert_frame_equal(cell_pm_data, original_copy)


# ─────────────────────────────────────────────────────────────────────
# Describe
# ─────────────────────────────────────────────────────────────────────

class TestScenarioDescribe:
    """Tests for human-readable scenario descriptions."""

    def test_describe_rush_hour(self, loader: ScenarioLoader) -> None:
        desc = loader.describe("rush_hour")
        assert "rush_hour" in desc
        assert "3.0x" in desc or "3.0" in desc
        assert "Modifiers:" in desc

    def test_describe_baseline(self, loader: ScenarioLoader) -> None:
        desc = loader.describe("baseline")
        assert "baseline" in desc.lower()

    def test_describe_all_scenarios(self, loader: ScenarioLoader) -> None:
        for name in loader.available():
            desc = loader.describe(name)
            assert isinstance(desc, str)
            assert len(desc) > 0


# ─────────────────────────────────────────────────────────────────────
# Convenience function
# ─────────────────────────────────────────────────────────────────────

class TestConvenienceFunction:
    """Tests for the module-level load_scenario() function."""

    def test_load_scenario_function(self) -> None:
        config = load_scenario("rush_hour", SCENARIOS_DIR)
        assert config["name"] == "rush_hour"
        assert config["ue_multiplier"] == 3.0

    def test_load_scenario_baseline(self) -> None:
        config = load_scenario("baseline", SCENARIOS_DIR)
        assert config["name"] == "baseline"


# ─────────────────────────────────────────────────────────────────────
# Distinctness — all scenarios produce different effects
# ─────────────────────────────────────────────────────────────────────

class TestScenarioDistinctness:
    """Verify each scenario produces meaningfully different data."""

    def test_all_scenarios_produce_different_results(
        self, loader: ScenarioLoader, cell_pm_data: pd.DataFrame
    ) -> None:
        rng = np.random.default_rng(42)
        results = {}
        for name in ["baseline", "rush_hour", "rain_fade"]:
            modified = loader.apply(cell_pm_data, name, mode="cell", rng=rng)
            # Use a composite fingerprint: attempts + failures + RSRP
            fingerprint = (
                modified["ho_attempt"].sum(),
                modified["ho_failure_intra"].sum(),
                round(modified["rsrp_dbm"].mean(), 1),
            )
            results[name] = fingerprint

        # Each scenario should produce a different fingerprint
        values = list(results.values())
        assert len(set(values)) == len(values), (
            f"Scenarios produced identical fingerprints: {results}"
        )

    def test_rush_hour_vs_rain_fade_different_impact(
        self, loader: ScenarioLoader, cell_pm_data: pd.DataFrame
    ) -> None:
        rush = loader.apply(cell_pm_data, "rush_hour", mode="cell")
        rain = loader.apply(cell_pm_data, "rain_fade", mode="cell")

        # Rush hour: high UE/attempts. Rain fade: low RSRP/SINR.
        assert rush["connected_ues"].sum() > rain["connected_ues"].sum()
        assert rain["rsrp_dbm"].mean() < rush["rsrp_dbm"].mean()


# ─────────────────────────────────────────────────────────────────────
# MROEnv integration — scenario wired into environment
# ─────────────────────────────────────────────────────────────────────

class TestMROEnvScenarioIntegration:
    """Tests for scenario parameter wired into MROEnv."""

    def test_baseline_default(self) -> None:
        """MROEnv defaults to baseline scenario."""
        from src.env.mro_env import MROEnv
        env = MROEnv()
        assert env.scenario_name == "baseline"

    def test_scenario_stored(self) -> None:
        """MROEnv stores the scenario name."""
        from src.env.mro_env import MROEnv
        env = MROEnv(scenario="rush_hour")
        assert env.scenario_name == "rush_hour"

    def test_scenario_in_reset_info(self) -> None:
        """reset() info dict contains the scenario name."""
        from src.env.mro_env import MROEnv
        env = MROEnv(scenario="rain_fade", scenario_seed=42)
        obs, info = env.reset()
        assert info["scenario"] == "rain_fade"

    def test_scenario_in_step_info(self) -> None:
        """step() info dict contains the scenario name."""
        from src.env.mro_env import MROEnv
        env = MROEnv(scenario="rush_hour", scenario_seed=42)
        obs, info = env.reset()
        action = env.action_space.sample()
        obs, reward, done, trunc, info = env.step(action)
        assert info["scenario"] == "rush_hour"

    def test_scenario_in_episode_history(self) -> None:
        """Episode history tracks which scenario was used."""
        from src.env.mro_env import MROEnv
        env = MROEnv(scenario="rush_hour", scenario_seed=42)
        obs, _ = env.reset()
        action = env.action_space.sample()
        env.step(action)
        assert len(env.episode_history) > 0
        assert env.episode_history[0]["scenario"] == "rush_hour"

    def test_baseline_episode_runs(self) -> None:
        """Baseline scenario runs a full episode without errors."""
        from src.env.mro_env import MROEnv
        env = MROEnv(scenario="baseline")
        obs, info = env.reset()
        done = False
        steps = 0
        while not done and steps < 5:
            action = env.action_space.sample()
            obs, reward, done, trunc, info = env.step(action)
            steps += 1
        assert steps > 0

    def test_rush_hour_episode_runs(self) -> None:
        """Rush hour scenario runs without errors."""
        from src.env.mro_env import MROEnv
        env = MROEnv(scenario="rush_hour", scenario_seed=42)
        obs, info = env.reset()
        action = env.action_space.sample()
        obs, reward, done, trunc, info = env.step(action)
        assert np.isfinite(reward)

    def test_rain_fade_episode_runs(self) -> None:
        """Rain fade scenario runs without errors."""
        from src.env.mro_env import MROEnv
        env = MROEnv(scenario="rain_fade", scenario_seed=42)
        obs, info = env.reset()
        action = env.action_space.sample()
        obs, reward, done, trunc, info = env.step(action)
        assert np.isfinite(reward)

    def test_tower_failure_episode_runs(self) -> None:
        """Tower failure scenario runs without errors."""
        from src.env.mro_env import MROEnv
        env = MROEnv(scenario="tower_failure", scenario_seed=42)
        obs, info = env.reset()
        action = env.action_space.sample()
        obs, reward, done, trunc, info = env.step(action)
        assert np.isfinite(reward)

    def test_scenario_with_reward_variant(self) -> None:
        """Scenario + reward variant combination works."""
        from src.env.mro_env import MROEnv
        env = MROEnv(
            reward_version="v3",
            scenario="rush_hour",
            scenario_seed=42,
        )
        obs, _ = env.reset()
        action = env.action_space.sample()
        obs, reward, done, trunc, info = env.step(action)
        assert np.isfinite(reward)
        assert info["scenario"] == "rush_hour"
        assert env.reward_version == "v3"

    def test_different_scenarios_produce_different_rewards(self) -> None:
        """Different scenarios should produce different reward distributions."""
        from src.env.mro_env import MROEnv
        rewards = {}
        for scenario in ["baseline", "rush_hour", "rain_fade"]:
            env = MROEnv(
                reward_version="v1",
                scenario=scenario,
                scenario_seed=42,
            )
            obs, _ = env.reset(seed=42)
            action = env.action_space.sample()
            _, reward, _, _, _ = env.step(action)
            rewards[scenario] = reward

        # At least 2 of 3 scenarios should produce different rewards
        unique_rewards = len(set(round(r, 2) for r in rewards.values()))
        assert unique_rewards >= 2, (
            f"Scenarios produced too-similar rewards: {rewards}"
        )

    def test_invalid_scenario_raises(self) -> None:
        """Invalid scenario name raises FileNotFoundError."""
        from src.env.mro_env import MROEnv
        with pytest.raises(FileNotFoundError):
            MROEnv(scenario="nonexistent_scenario")

    def test_scenario_config_stored(self) -> None:
        """Scenario config dict is accessible on the env."""
        from src.env.mro_env import MROEnv
        env = MROEnv(scenario="rush_hour", scenario_seed=42)
        assert env._scenario_config["name"] == "rush_hour"
        assert env._scenario_config["ue_multiplier"] == 3.0
