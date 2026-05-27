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

        self.pm_data = pd.read_csv(pm_data_path, parse_dates=["timestamp_utc"])
        self.kpi_data = pd.read_csv(kpi_path)

        if cell_id:
            self.cell_id = cell_id
        else:
            problem_cells = self.kpi_data[self.kpi_data["problem_cell"] == "Yes"]
            self.cell_id = problem_cells.iloc[0]["cell_id"]

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
