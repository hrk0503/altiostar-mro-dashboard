from __future__ import annotations

import typing
from pathlib import Path
from typing import Any

import gymnasium as gym
import numpy as np
import pandas as pd
import yaml
from gymnasium import spaces

_RELATION_GROUPS_CACHE: dict[int, Any] = {}
_ALL_RELATIONS_CACHE: dict[int, Any] = {}
_DF_CACHE: dict[str, pd.DataFrame] = {}

# Default reward weights — used when no YAML config is provided
_DEFAULT_REWARD_WEIGHTS: dict[str, float] = {
    "ho_success": 1.0,
    "ho_failure": -5.0,
    "ping_pong": -2.0,
    "too_early_ho": -3.0,
    "too_late_ho": -4.0,
    "wrong_cell": -5.0,
}


def load_reward_config(config_path: str | None = None) -> dict[str, Any]:
    """Load reward configuration from YAML file.

    Returns a dict with keys: version, weights.
    Falls back to defaults if no config is provided.
    """
    if config_path is None:
        default_yaml = Path(__file__).resolve().parents[2] / "configs" / "mro_default.yaml"
        if default_yaml.exists():
            config_path = str(default_yaml)
        else:
            return {"version": "v0", "weights": dict(_DEFAULT_REWARD_WEIGHTS)}

    try:
        with open(config_path) as f:
            full_config = yaml.safe_load(f)
    except (FileNotFoundError, OSError):
        return {"version": "v0", "weights": dict(_DEFAULT_REWARD_WEIGHTS)}

    reward_section = full_config.get("reward", {})
    version = reward_section.get("version", "v0")
    weights = {
        "ho_success": reward_section.get("ho_success", 1.0),
        "ho_failure": reward_section.get("ho_failure", -5.0),
        "ping_pong": reward_section.get("ping_pong", -2.0),
        "too_early_ho": reward_section.get("too_early_ho", -3.0),
        "too_late_ho": reward_section.get("too_late_ho", -4.0),
        "wrong_cell": reward_section.get("wrong_cell", -5.0),
    }
    return {"version": version, "weights": weights}


class MROEnv(gym.Env[typing.Any, typing.Any]):
    """
    MRO (Mobility Robustness Optimization) Gymnasium Environment.
    Supports both cell-level (v0/v1) and relation-level (v2) PM optimization dynamically.

    Reward variants (configurable via ``reward_version`` or ``mro_default.yaml``):
        v0 — Simple count-based: success*1 - failure*10 - pingpong*3 (original)
        v1 — Traffic-weighted: normalizes by ho_attempts so busy cells don't dominate
        v2 — Rate-based: uses percentage metrics for bounded, comparable rewards
        v3 — Multi-objective: separate weights for too_early/too_late/wrong_cell from YAML

    Scenario support (configurable via ``scenario`` parameter):
        baseline      — No modifications (default, backward compatible)
        rush_hour     — High UE density, congestion, PRB floor
        rain_fade     — Signal degradation, RSRP/SINR drops, more failures
        tower_failure — Site removed, neighbor load spike, cascade failures
    """

    def __init__(
        self,
        pm_data_path: str | pd.DataFrame | None = None,
        kpi_path: str | pd.DataFrame | None = None,
        cell_id: str | None = None,
        reward_version: str | None = None,
        reward_config_path: str | None = None,
        scenario: str | dict[str, Any] | None = None,
        scenario_seed: int | None = None,
        scenario_config: dict[str, Any] | None = None,
    ):
        super().__init__()

        # ── Reward configuration ──
        reward_cfg = load_reward_config(reward_config_path)
        self.reward_version: str = reward_version or reward_cfg["version"]
        self.reward_weights: dict[str, float] = reward_cfg["weights"]

        # ── Scenario configuration ──
        self._failed_sites_list: list[str] = []
        if scenario_config is not None:
            self._scenario_config = scenario_config
            self.scenario_name = scenario_config.get("name", "custom_scenario")
        elif isinstance(scenario, dict):
            self._scenario_config = scenario
            self.scenario_name = scenario.get("name", "custom_scenario")
        elif isinstance(scenario, str) and scenario != "baseline":
            from src.env.scenario_loader import ScenarioLoader
            loader = ScenarioLoader()
            self._scenario_config = loader.load(scenario)
            self.scenario_name = scenario
        else:
            self._scenario_config = {"name": "baseline", "description": "No modifications"}
            self.scenario_name = "baseline"

        self._scenario_seed: int | None = scenario_seed

        base_dir = Path(__file__).resolve().parents[2]
        if pm_data_path is None:
            # Default to relation-level if it exists, otherwise fallback to cell-level
            rel_path = base_dir / "data" / "synthetic" / "pm_data_relation_level.csv"
            if rel_path.exists():
                pm_data_path = str(rel_path)
            else:
                pm_data_path = str(base_dir / "data" / "synthetic" / "pm_data_april2026.csv")
        if kpi_path is None:
            kpi_path = str(base_dir / "data" / "synthetic" / "cluster_kpi_summary.csv")

        if isinstance(pm_data_path, pd.DataFrame):
            self.pm_data_raw = pm_data_path
        else:
            path_str = str(pm_data_path)
            if path_str in _DF_CACHE:
                self.pm_data_raw = _DF_CACHE[path_str]
            else:
                self.pm_data_raw = pd.read_csv(pm_data_path)
                _DF_CACHE[path_str] = self.pm_data_raw

        # Note: Scenario configurations are applied dynamically on reset() and step().

        if isinstance(kpi_path, pd.DataFrame):
            self.kpi_data = kpi_path
        else:
            path_str = str(kpi_path)
            if path_str in _DF_CACHE:
                self.kpi_data = _DF_CACHE[path_str]
            else:
                self.kpi_data = pd.read_csv(kpi_path)
                _DF_CACHE[path_str] = self.kpi_data

        # Detect mode based on column schema
        if "source_cell_id" in self.pm_data_raw.columns:
            self.mode = "relation"
            self.cell_id = cell_id or "relation_level_network"
            
            # Group relations using cache to optimize performance
            cache_key = id(self.pm_data_raw)
            if cache_key in _ALL_RELATIONS_CACHE:
                all_relations = _ALL_RELATIONS_CACHE[cache_key]
                self.relation_groups = _RELATION_GROUPS_CACHE[cache_key]
            else:
                all_relations = list(self.pm_data_raw.groupby(["source_cell_id", "target_cell_id"]).groups.keys())
                _ALL_RELATIONS_CACHE[cache_key] = all_relations
                
                # Pre-group for fast O(1) step access
                relation_groups = {}
                for (src, tgt), group in self.pm_data_raw.groupby(["source_cell_id", "target_cell_id"]):
                    cio_groups = {}
                    for cio, cio_group in group.groupby("cio_db"):
                        cio_groups[cio] = {
                            "ho_attempts": cio_group["ho_attempts"].values,
                            "ho_successes": cio_group["ho_successes"].values,
                            "ho_failures": cio_group["ho_failures"].values,
                            "too_early_ho": cio_group["too_early_ho"].values,
                            "too_late_ho": cio_group["too_late_ho"].values,
                            "wrong_cell": cio_group["wrong_cell"].values,
                            "correct_cell": cio_group["correct_cell"].values,
                            "ping_pong": cio_group["ping_pong"].values,
                        }
                    relation_groups[(src, tgt)] = {
                        "cio_groups": cio_groups,
                        "all_cios": np.sort(np.array(list(cio_groups.keys()))),
                        "full_df": group.reset_index(drop=True),
                    }
                self.relation_groups = relation_groups
                _RELATION_GROUPS_CACHE[cache_key] = relation_groups

            if cell_id:
                self.relations = [(src, tgt) for (src, tgt) in all_relations if src == cell_id]
            else:
                self.relations = all_relations
            
            self.n_relations = len(self.relations)

            self.n_steps = len(self.pm_data_raw) // len(all_relations) if len(all_relations) > 0 else 0
            self.current_step = 0
            self.episode_history: list[dict[str, Any]] = []

            # Observation matrix shape (n_relations, 9)
            low_rel = np.full((self.n_relations, 9), -1000.0, dtype=np.float32)
            high_rel = np.full((self.n_relations, 9), 100000.0, dtype=np.float32)
            self.observation_space = spaces.Box(low=low_rel, high=high_rel, dtype=np.float32)

            # Continuous CIO deltas Box shape (n_relations,)
            self.action_space = spaces.Box(
                low=-2.0, high=2.0, shape=(self.n_relations,), dtype=np.float32
            )
        else:
            self.mode = "cell"
            
            # Normalize PM data synthetic CSV schema to expected internal schema
            rename_pm_cols = {
                "timestamp": "timestamp_utc",
                "rsrp_dbm": "avg_rsrp_dBm",
                "rsrq_db": "avg_rsrq_dB",
                "sinr_db": "avg_sinr_dB",
                "ho_ping_pong": "ho_pingpong_count",
                "ho_success": "ho_success_intra",
                "ho_failure": "ho_failure_intra",
            }
            self.pm_data = self.pm_data_raw.rename(
                columns={k: v for k, v in rename_pm_cols.items() if k in self.pm_data_raw.columns}
            )

            if "timestamp_utc" in self.pm_data.columns:
                self.pm_data["timestamp_utc"] = pd.to_datetime(self.pm_data["timestamp_utc"])

            # Handle PRB utilization mapping
            if (
                "prb_utilization_dl_pct" not in self.pm_data.columns
                and "prb_utilization_pct" in self.pm_data.columns
            ):
                self.pm_data["prb_utilization_dl_pct"] = self.pm_data["prb_utilization_pct"]
                self.pm_data["prb_utilization_ul_pct"] = self.pm_data["prb_utilization_pct"]

            # Compute ho_success_rate_pct and ho_failure_rate_pct if not present
            if "ho_success_rate_pct" not in self.pm_data.columns:
                attempts = self.pm_data.get("ho_attempt", 1.0)
                attempts_safe = attempts.replace(0, 1.0)
                success = self.pm_data.get("ho_success_intra", 0.0)
                failure = self.pm_data.get("ho_failure_intra", 0.0)
                self.pm_data["ho_success_rate_pct"] = (success / attempts_safe) * 100.0
                self.pm_data["ho_failure_rate_pct"] = (failure / attempts_safe) * 100.0

            if cell_id:
                self.cell_id = cell_id
            else:
                if "problem_cell" in self.kpi_data.columns:
                    problem_cells = self.kpi_data[self.kpi_data["problem_cell"] == "Yes"]
                elif "problem_flag" in self.kpi_data.columns:
                    problem_cells = self.kpi_data[self.kpi_data["problem_flag"]]
                else:
                    problem_cells = self.kpi_data

                if len(problem_cells) > 0:
                    self.cell_id = problem_cells.iloc[0]["cell_id"]
                else:
                    self.cell_id = self.kpi_data.iloc[0]["cell_id"]

            self.cell_pm_df = (
                self.pm_data[self.pm_data["cell_id"] == self.cell_id]
                .sort_values("timestamp_utc")
                .reset_index(drop=True)
            )

            self.pm_records = self.cell_pm_df.to_dict("records")
            self.n_steps = len(self.cell_pm_df)
            self.current_step = 0

            # Observation vector shape (8,)
            low_cell = np.array([-140.0, -20.0, -10.0, 0.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float32)
            high_cell = np.array([-40.0, 0.0, 30.0, 100.0, 100.0, 100.0, 100.0, 500.0], dtype=np.float32)
            self.observation_space = spaces.Box(low=low_cell, high=high_cell, dtype=np.float32)

            # Action multidiscrete
            self.action_space = spaces.MultiDiscrete([5, 7, 5, 3])

    @property
    def cell_pm(self) -> pd.DataFrame:
        """Backwards compatibility helper for forge.py & random_policy.py metric evaluation."""
        if self.mode == "relation":
            if not self.episode_history:
                return pd.DataFrame([{
                    "ho_success_rate_pct": 100.0,
                    "ho_attempts_intra": 10.0,
                    "ho_pingpong_count": 0.0,
                }])
            return pd.DataFrame(self.episode_history)
        else:
            return self.cell_pm_df

    def _update_state_from_replay(self, action: Any = None) -> None:
        """v1 Cell-level physical simulation overlay."""
        row = self.pm_records[self.current_step]

        base_rsrp = float(row["avg_rsrp_dBm"])
        base_rsrq = float(row["avg_rsrq_dB"])
        base_sinr = float(row["avg_sinr_dB"])
        self.prb_utilization_dl_pct = float(row["prb_utilization_dl_pct"])
        self.prb_utilization_ul_pct = float(row["prb_utilization_ul_pct"])
        base_success = float(row["ho_success_rate_pct"])
        base_pingpong = float(row["ho_pingpong_count"])

        if action is not None:
            tilt_delta = float(action[0] - 2) * 1.0
            power_delta = float(action[1] - 3) * 1.0
            cio_delta = float(action[2] - 2) * 1.0

            self.avg_rsrp_dBm = float(np.clip(base_rsrp + power_delta - 1.5 * abs(tilt_delta), -140.0, -40.0))
            self.avg_sinr_dB = float(np.clip(base_sinr + 0.5 * power_delta - 2.0 * abs(tilt_delta), -10.0, 30.0))
            self.avg_rsrq_dB = float(np.clip(base_rsrq + 0.2 * power_delta - 0.5 * abs(tilt_delta), -20.0, 0.0))

            success_impact = - 5.0 * abs(cio_delta) - 3.0 * abs(tilt_delta)
            if cio_delta == 0 and tilt_delta == 0:
                success_impact = 2.0

            self.ho_success_rate_pct = float(np.clip(base_success + success_impact, 0.0, 100.0))
            self.ho_failure_rate_pct = float(100.0 - self.ho_success_rate_pct)
            self.ho_pingpong_count = float(max(0.0, base_pingpong + 3.0 * cio_delta + 1.0 * power_delta))
        else:
            self.avg_rsrp_dBm = base_rsrp
            self.avg_rsrq_dB = base_rsrq
            self.avg_sinr_dB = base_sinr
            self.ho_success_rate_pct = base_success
            self.ho_failure_rate_pct = float(row["ho_failure_rate_pct"])
            self.ho_pingpong_count = base_pingpong

        # Apply scenario modifications on the fly
        if self.scenario_name != "baseline" and self._scenario_config:
            cfg = self._scenario_config
            if self.cell_id[:-1] in self._failed_sites_list:
                self.avg_rsrp_dBm = -140.0
                self.avg_rsrq_dB = -20.0
                self.avg_sinr_dB = -10.0
                self.prb_utilization_dl_pct = 0.0
                self.prb_utilization_ul_pct = 0.0
                self.ho_success_rate_pct = 0.0
                self.ho_failure_rate_pct = 0.0
                self.ho_pingpong_count = 0.0
            else:
                self.avg_rsrp_dBm += cfg.get("rsrp_offset_db", 0.0)
                self.avg_sinr_dB += cfg.get("sinr_offset_db", 0.0)
                prb_floor = cfg.get("prb_floor", 0.0) * 100.0
                self.prb_utilization_dl_pct = max(self.prb_utilization_dl_pct, prb_floor)
                self.prb_utilization_ul_pct = max(self.prb_utilization_ul_pct, prb_floor)
                
                fail_mult = cfg.get("ho_failure_multiplier", 1.0)
                if fail_mult != 1.0:
                    self.ho_failure_rate_pct = min(100.0, self.ho_failure_rate_pct * fail_mult)
                    self.ho_success_rate_pct = 100.0 - self.ho_failure_rate_pct

    def _get_obs(self) -> np.ndarray:
        return np.array([
            self.avg_rsrp_dBm,
            self.avg_rsrq_dB,
            self.avg_sinr_dB,
            self.prb_utilization_dl_pct,
            self.prb_utilization_ul_pct,
            self.ho_success_rate_pct,
            self.ho_failure_rate_pct,
            self.ho_pingpong_count,
        ], dtype=np.float32)

    def _get_reward(self) -> float:
        row = self.pm_records[self.current_step]
        attempts = float(row.get("ho_attempts_intra", row.get("ho_attempt", 10.0)))
        safe_attempts = max(attempts, 1.0)

        ho_success_intra = int(round(attempts * (self.ho_success_rate_pct / 100.0)))
        ho_failure_intra = int(round(attempts * (self.ho_failure_rate_pct / 100.0)))

        w = self.reward_weights
        if self.reward_version == "v1":
            reward = (
                (ho_success_intra / safe_attempts) * 100.0
                + (ho_failure_intra / safe_attempts) * w["ho_failure"] * 100.0
                + (self.ho_pingpong_count / safe_attempts) * w["ping_pong"] * 100.0
            )
        elif self.reward_version == "v2":
            reward = (
                self.ho_success_rate_pct * w["ho_success"]
                + self.ho_failure_rate_pct * w["ho_failure"]
                + (self.ho_pingpong_count / safe_attempts * 100.0) * w["ping_pong"]
            )
        elif self.reward_version == "v3":
            # Cell mode doesn't have too_early/too_late/wrong_cell breakdown,
            # so we approximate: split failure evenly across modes
            failure_pct = self.ho_failure_rate_pct
            third = failure_pct / 3.0
            pingpong_pct = self.ho_pingpong_count / safe_attempts * 100.0
            reward = (
                self.ho_success_rate_pct * w["ho_success"]
                + third * w["too_early_ho"]
                + third * w["too_late_ho"]
                + third * w["wrong_cell"]
                + pingpong_pct * w["ping_pong"]
            )
        else:
            # v0 — Original
            reward = (
                ho_success_intra * w["ho_success"]
                + ho_failure_intra * w["ho_failure"]
                + self.ho_pingpong_count * w["ping_pong"]
            )

        return float(reward)

    def _apply_scenario_to_relation_state(self, state: np.ndarray, relation_idx: int) -> np.ndarray:
        if not self._scenario_config or self.scenario_name == "baseline":
            return state

        cfg = self._scenario_config
        src, tgt = self.relations[relation_idx]

        # 1. Tower failure (failed_sites)
        if "failed_sites" in cfg and cfg["failed_sites"] > 0:
            if src[:-1] in self._failed_sites_list or tgt[:-1] in self._failed_sites_list:
                state[0:8] = 0.0
                return state

        # 2. Multipliers
        ue_mult = cfg.get("ue_multiplier", 1.0)
        ho_att_mult = cfg.get("ho_attempt_multiplier", 1.0)
        state[0] = round(state[0] * ue_mult * ho_att_mult)

        ho_fail_mult = cfg.get("ho_failure_multiplier", 1.0)
        state[2] = round(state[2] * ho_fail_mult)

        # ho_attempt_spike for surviving neighbors
        spike = cfg.get("ho_attempt_spike", 1.0)
        if spike > 1.0 and len(self._failed_sites_list) > 0:
            state[0] = round(state[0] * spike)

        # neighbor_load_multiplier
        neigh_load_mult = cfg.get("neighbor_load_multiplier", 1.0)
        if neigh_load_mult != 1.0:
            state[0] = round(state[0] * neigh_load_mult)

        # Success rate/values adjustment (successes cannot exceed attempts)
        if state[0] > 0:
            if state[1] > state[0]:
                state[1] = state[0]
            if state[2] > state[0] - state[1]:
                state[2] = state[0] - state[1]
        else:
            state[1:8] = 0.0

        return state

    def _apply_scenario_to_cell_obs(self, obs: np.ndarray) -> np.ndarray:
        if not self._scenario_config or self.scenario_name == "baseline":
            return obs

        cfg = self._scenario_config

        # 1. Tower failure
        if "failed_sites" in cfg and cfg["failed_sites"] > 0:
            if self.cell_id[:-1] in self._failed_sites_list:
                return np.zeros_like(obs)

        # 2. RSRP / SINR offsets
        obs[0] += cfg.get("rsrp_offset_db", 0.0)
        obs[2] += cfg.get("sinr_offset_db", 0.0)

        # 3. PRB floor
        prb_floor_pct = cfg.get("prb_floor", 0.0) * 100.0
        obs[3] = max(obs[3], prb_floor_pct)
        obs[4] = max(obs[4], prb_floor_pct)

        # 4. HO failure multiplier
        fail_mult = cfg.get("ho_failure_multiplier", 1.0)
        if fail_mult != 1.0:
            new_fail_pct = min(100.0, obs[6] * fail_mult)
            obs[6] = new_fail_pct
            obs[5] = 100.0 - new_fail_pct

        return obs

    def reset(
        self,
        *,
        seed: int | None = None,
        options: dict[str, Any] | None = None,
    ) -> tuple[np.ndarray, dict[str, Any]]:
        super().reset(seed=seed)
        self.episode_history = []

        # Determine failed sites for this episode using the environment's seeded np_random
        cfg = self._scenario_config
        self._failed_sites_list = []
        if cfg and cfg.get("failed_sites", 0) > 0:
            if self.mode == "relation":
                sites = list({str(src)[:-1] for src, _ in self.relations})
            else:
                sites = [self.cell_id[:-1]]
            
            n_failed = cfg["failed_sites"]
            if len(sites) <= n_failed:
                n_failed = max(len(sites) - 1, 0)
            if n_failed > 0:
                self._failed_sites_list = list(self.np_random.choice(sites, size=n_failed, replace=False))

        if self.mode == "relation":
            if options and options.get("random_start"):
                self.current_step = int(self.np_random.integers(0, self.n_steps - 1))
            else:
                self.current_step = 0

            self.current_state = np.zeros((self.n_relations, 9), dtype=np.float32)
            for i, (src, tgt) in enumerate(self.relations):
                rel_df = self.relation_groups[(src, tgt)]["full_df"]
                step_idx = self.current_step % len(rel_df)
                row = rel_df.iloc[step_idx]
                state = np.array([
                    float(row["ho_attempts"]),
                    float(row["ho_successes"]),
                    float(row["ho_failures"]),
                    float(row["too_early_ho"]),
                    float(row["too_late_ho"]),
                    float(row["wrong_cell"]),
                    float(row["correct_cell"]),
                    float(row["ping_pong"]),
                    float(row["cio_db"]),
                ], dtype=np.float32)
                
                # Apply scenario modifications on the fly
                self.current_state[i] = self._apply_scenario_to_relation_state(state, i)

            info = {
                "cell_id": self.cell_id,
                "step": self.current_step,
                "scenario": self.scenario_name,
            }
            return self.current_state, info
        else:
            if options and options.get("random_start"):
                self.current_step = int(self.np_random.integers(0, self.n_steps - 1))
            else:
                self.current_step = 0

            self._update_state_from_replay(action=None)
            obs = self._get_obs()
            # Apply scenario to cell observation on the fly
            obs = self._apply_scenario_to_cell_obs(obs)
            info = {
                "cell_id": self.cell_id,
                "step": self.current_step,
                "scenario": self.scenario_name,
            }
            return obs, info

    def step(
        self, action: Any
    ) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        if self.mode == "relation":
            next_state = np.zeros((self.n_relations, 9), dtype=np.float32)
            total_successes = 0
            total_failures = 0
            total_ping_pongs = 0
            total_attempts = 0

            for i, (src, tgt) in enumerate(self.relations):
                cio_delta = float(action[i])
                current_cio = self.current_state[i][8]
                target_cio = current_cio + cio_delta

                rel_info = self.relation_groups[(src, tgt)]
                all_cios = rel_info["all_cios"]

                # Optimized binary search for closest CIO
                idx = np.searchsorted(all_cios, target_cio)
                if idx == 0:
                    closest_cio = all_cios[0]
                elif idx >= len(all_cios):
                    closest_cio = all_cios[-1]
                else:
                    val_left = all_cios[idx - 1]
                    val_right = all_cios[idx]
                    if abs(val_left - target_cio) <= abs(val_right - target_cio):
                        closest_cio = val_left
                    else:
                        closest_cio = val_right

                cio_info = rel_info["cio_groups"][closest_cio]
                n_records = len(cio_info["ho_attempts"])
                idx_sampled = self.np_random.integers(0, n_records)

                att = int(cio_info["ho_attempts"][idx_sampled])
                succ = int(cio_info["ho_successes"][idx_sampled])
                fail = int(cio_info["ho_failures"][idx_sampled])
                early = int(cio_info["too_early_ho"][idx_sampled])
                late = int(cio_info["too_late_ho"][idx_sampled])
                wrong = int(cio_info["wrong_cell"][idx_sampled])
                correct = int(cio_info["correct_cell"][idx_sampled])
                ping = int(cio_info["ping_pong"][idx_sampled])

                # Apply scenario modifications on the fly
                if self.scenario_name != "baseline" and self._scenario_config:
                    cfg = self._scenario_config
                    if src[:-1] in self._failed_sites_list or tgt[:-1] in self._failed_sites_list:
                        att = succ = fail = early = late = wrong = correct = ping = 0
                    else:
                        ue_mult = cfg.get("ue_multiplier", 1.0)
                        ho_att_mult = cfg.get("ho_attempt_multiplier", 1.0)
                        att = round(att * ue_mult * ho_att_mult)
                        
                        ho_fail_mult = cfg.get("ho_failure_multiplier", 1.0)
                        fail = round(fail * ho_fail_mult)
                        
                        spike = cfg.get("ho_attempt_spike", 1.0)
                        if spike > 1.0 and len(self._failed_sites_list) > 0:
                            att = round(att * spike)
                            
                        neigh_load_mult = cfg.get("neighbor_load_multiplier", 1.0)
                        if neigh_load_mult != 1.0:
                            att = round(att * neigh_load_mult)

                        # Adjust succ and fail to not exceed att
                        if att > 0:
                            if succ > att:
                                succ = att
                            if fail > att - succ:
                                fail = att - succ
                        else:
                            succ = fail = early = late = wrong = correct = ping = 0

                next_state[i] = [
                    float(att),
                    float(succ),
                    float(fail),
                    float(early),
                    float(late),
                    float(wrong),
                    float(correct),
                    float(ping),
                    float(closest_cio),
                ]

                total_successes += succ
                total_failures += fail
                total_ping_pongs += ping
                total_attempts += att

            # ── Aggregate failure-mode totals ──
            total_too_early = int(np.sum(next_state[:, 3]))
            total_too_late = int(np.sum(next_state[:, 4]))
            total_wrong_cell = int(np.sum(next_state[:, 5]))

            if total_attempts == 0:
                success_rate = 100.0
                failure_rate = 0.0
                pingpong_rate = 0.0
                too_early_rate = 0.0
                too_late_rate = 0.0
                wrong_cell_rate = 0.0
            else:
                success_rate = total_successes / total_attempts * 100.0
                failure_rate = total_failures / total_attempts * 100.0
                pingpong_rate = total_ping_pongs / total_attempts * 100.0
                too_early_rate = total_too_early / total_attempts * 100.0
                too_late_rate = total_too_late / total_attempts * 100.0
                wrong_cell_rate = total_wrong_cell / total_attempts * 100.0

            # ── Reward variants ──
            w = self.reward_weights
            if self.reward_version == "v1":
                # Traffic-weighted: aggregate counts ÷ aggregate attempts.
                # High-traffic relations contribute more to the reward.
                reward = float(
                    success_rate * w["ho_success"]
                    + failure_rate * w["ho_failure"]
                    + pingpong_rate * w["ping_pong"]
                )
            elif self.reward_version == "v2":
                # Rate-based: simple average of per-relation rates.
                # Every relation counts equally regardless of traffic volume.
                per_att = np.maximum(next_state[:, 0], 1.0)
                avg_success = float(np.mean(next_state[:, 1] / per_att)) * 100.0
                avg_failure = float(np.mean(next_state[:, 2] / per_att)) * 100.0
                avg_pingpong = float(np.mean(next_state[:, 7] / per_att)) * 100.0
                reward = float(
                    avg_success * w["ho_success"]
                    + avg_failure * w["ho_failure"]
                    + avg_pingpong * w["ping_pong"]
                )
            elif self.reward_version == "v3":
                # Multi-objective: separate failure-mode weights from YAML
                reward = float(
                    success_rate * w["ho_success"]
                    + too_early_rate * w["too_early_ho"]
                    + too_late_rate * w["too_late_ho"]
                    + wrong_cell_rate * w["wrong_cell"]
                    + pingpong_rate * w["ping_pong"]
                )
            else:
                # v0 — Original count-based (backward compatible)
                reward = float(
                    total_successes * w["ho_success"]
                    + total_failures * w["ho_failure"]
                    + total_ping_pongs * w["ping_pong"]
                )

            # Apply boundary penalties for HOSR < 95% and Ping-Pong > 5%
            if success_rate < 95.0:
                reward -= 100.0 * (95.0 - success_rate)
            if pingpong_rate > 5.0:
                reward -= 50.0 * (pingpong_rate - 5.0)

            self.episode_history.append({
                "ho_attempts_intra": total_attempts,
                "ho_success_intra": total_successes,
                "ho_failure_intra": total_failures,
                "ho_pingpong_count": total_ping_pongs,
                "ho_success_rate_pct": success_rate,
                "ho_failure_rate_pct": failure_rate,
                "ho_failure_too_early": total_too_early,
                "ho_failure_too_late": total_too_late,
                "ho_failure_wrong_cell": total_wrong_cell,
                "too_early_rate_pct": too_early_rate,
                "too_late_rate_pct": too_late_rate,
                "wrong_cell_rate_pct": wrong_cell_rate,
                "pingpong_rate_pct": pingpong_rate,
                "reward_version": self.reward_version,
                "scenario": self.scenario_name,
                "reward": reward,
                "avg_rsrp_dBm": -90.0,
                "avg_rsrq_dB": -12.0,
                "avg_sinr_dB": 15.0,
            })

            self.current_state = next_state
            self.current_step += 1
            terminated = self.current_step >= self.n_steps
            truncated = False

            info = {
                "cell_id": self.cell_id,
                "step": self.current_step,
                "scenario": self.scenario_name,
                "total_attempts": total_attempts,
                "total_successes": total_successes,
                "total_failures": total_failures,
            }

            obs_to_return = next_state if not terminated else np.zeros((self.n_relations, 9), dtype=np.float32)
            return obs_to_return, reward, terminated, truncated, info
        else:
            reward = self._get_reward()
            self.current_step += 1
            terminated = self.current_step >= self.n_steps
            truncated = False

            if not terminated:
                self._update_state_from_replay(action)
                obs = self._get_obs()
            else:
                obs = np.zeros(8, dtype=np.float32)

            info = {
                "cell_id": self.cell_id,
                "step": self.current_step,
                "scenario": self.scenario_name,
                "action": [int(x) for x in action] if hasattr(action, "__len__") else int(action),
                "action_effect": "simulated transition physics v1",
            }
            return obs, reward, terminated, truncated, info

    def render(self) -> None:
        pass
