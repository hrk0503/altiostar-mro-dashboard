import logging
import typing

import gymnasium as gym
import numpy as np
import pandas as pd
from gymnasium import spaces

logger = logging.getLogger(__name__)


class MROEnv(gym.Env[typing.Any, typing.Any]):
    """
    MRO (Mobility Robustness Optimization) Gymnasium Environment.

    Observation space: RSRP, RSRQ, SINR, PRB utilization, HO success rate,
                       HO failure rate, ping-pong count (per cell, per step)
    Action space: tilt delta, power delta, CIO delta, neighbor list toggle
    Reward: +1 HO success, -5 HO failure, -2 ping-pong

    Memory Footprint Note:
    This environment currently loads the entire PM DataFrame into memory (via pd.read_csv)
    and filters it. For 216K rows, this footprint is negligible (~15-20MB). However, when
    scaling to millions of cells or longer time horizons, consider using chunked loading,
    database queries, or memory-mapped formats (e.g. Parquet) to avoid high memory overhead.
    """

    def __init__(self, pm_data_path: str, kpi_path: str, cell_id: str | None = None):
        super().__init__()

        self.pm_data = pd.read_csv(pm_data_path)
        self.kpi_data = pd.read_csv(kpi_path)

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
        self.pm_data = self.pm_data.rename(
            columns={k: v for k, v in rename_pm_cols.items() if k in self.pm_data.columns}
        )

        if "timestamp_utc" in self.pm_data.columns:
            self.pm_data["timestamp_utc"] = pd.to_datetime(self.pm_data["timestamp_utc"])

        # Handle PRB utilization mapping
        if "prb_utilization_dl_pct" not in self.pm_data.columns and "prb_utilization_pct" in self.pm_data.columns:
            self.pm_data["prb_utilization_dl_pct"] = self.pm_data["prb_utilization_pct"]
            self.pm_data["prb_utilization_ul_pct"] = self.pm_data["prb_utilization_pct"]

        # Compute ho_success_rate_pct and ho_failure_rate_pct if not present
        if "ho_success_rate_pct" not in self.pm_data.columns:
            attempts = self.pm_data.get("ho_attempt", 1.0)
            # Avoid division by zero
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
                problem_cells = self.kpi_data[self.kpi_data["problem_flag"] == True]
            else:
                problem_cells = self.kpi_data

            if len(problem_cells) > 0:
                self.cell_id = problem_cells.iloc[0]["cell_id"]
            else:
                self.cell_id = self.kpi_data.iloc[0]["cell_id"]

        self.cell_pm = (
            self.pm_data[self.pm_data["cell_id"] == self.cell_id]
            .sort_values("timestamp_utc")
            .reset_index(drop=True)
        )

        self.n_steps = len(self.cell_pm)
        self.current_step = 0

        # --- Observation Space ---
        # [rsrp, rsrq, sinr, prb_dl, prb_ul, ho_success_rate, ho_failure_rate, pingpong]
        low = np.array([-140.0, -20.0, -10.0, 0.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float32)
        high = np.array([-40.0, 0.0, 30.0, 100.0, 100.0, 100.0, 100.0, 500.0], dtype=np.float32)
        self.observation_space = spaces.Box(low=low, high=high, dtype=np.float32)

        # --- Action Space ---
        # [tilt_delta, power_delta, cio_delta, neighbor_toggle]
        self.action_space = spaces.MultiDiscrete([5, 7, 5, 3])

    def _get_obs(self) -> np.ndarray:
        row = self.cell_pm.iloc[self.current_step]
        return np.array([
            row["avg_rsrp_dBm"],
            row["avg_rsrq_dB"],
            row["avg_sinr_dB"],
            row["prb_utilization_dl_pct"],
            row["prb_utilization_ul_pct"],
            row["ho_success_rate_pct"],
            row["ho_failure_rate_pct"],
            row["ho_pingpong_count"],
        ], dtype=np.float32)

    def _get_reward(self) -> float:
        # TODO Phase 1: Reward normalization or scaling. Currently reward depends on raw counts,
        # which varies by traffic volume. Consider normalizing by ho_attempts_intra or
        # using rates, e.g.:
        # reward = row["ho_success_rate_pct"] * 0.01 - row["ho_failure_rate_pct"] * 0.05 - ...
        row = self.cell_pm.iloc[self.current_step]
        reward = 0.0
        reward += row["ho_success_intra"] * 1.0
        reward += row["ho_failure_intra"] * -5.0
        reward += row["ho_pingpong_count"] * -2.0
        return float(reward)

    def reset(
        self,
        *,
        seed: int | None = None,
        options: dict[str, typing.Any] | None = None,
    ) -> tuple[np.ndarray, dict[str, typing.Any]]:
        super().reset(seed=seed)
        if options and options.get("random_start"):
            self.current_step = int(self.np_random.integers(0, self.n_steps - 1))
        else:
            self.current_step = 0
        obs = self._get_obs()
        info = {"cell_id": self.cell_id, "step": self.current_step}
        return obs, info

    def step(
        self, action: typing.Any
    ) -> tuple[np.ndarray, float, bool, bool, dict[str, typing.Any]]:
        """
        v0: Historical replay mode — actions are recorded but do not
        affect state transitions. Environment replays real PM data row
        by row. Action effect will be modelled in v1.
        """
        # TODO v1: Implement a simulation model where actions (tilt/power/CIO deltas,
        # neighbor toggle) affect the KPIs (RSRP, RSRQ, SINR, handover success/failure,
        # ping-pong).
        logger.warning(
            "v0: historical replay only — actions are recorded but do not affect state transitions"
        )
        reward = self._get_reward()
        self.current_step += 1
        terminated = self.current_step >= self.n_steps
        truncated = False

        obs = np.zeros(8, dtype=np.float32) if terminated else self._get_obs()

        info = {
            "cell_id": self.cell_id,
            "step": self.current_step,
            "action": action,
            "action_effect": "none (replay mode)",
        }

        return obs, reward, terminated, truncated, info

    def render(self) -> None:
        pass
