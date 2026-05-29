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
        if (
            "prb_utilization_dl_pct" not in self.pm_data.columns
            and "prb_utilization_pct" in self.pm_data.columns
        ):
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
                problem_cells = self.kpi_data[self.kpi_data["problem_flag"]]
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

    def _update_state_from_replay(self, action: typing.Any = None) -> None:
        row = self.cell_pm.iloc[self.current_step]

        base_rsrp = float(row["avg_rsrp_dBm"])
        base_rsrq = float(row["avg_rsrq_dB"])
        base_sinr = float(row["avg_sinr_dB"])
        self.prb_utilization_dl_pct = float(row["prb_utilization_dl_pct"])
        self.prb_utilization_ul_pct = float(row["prb_utilization_ul_pct"])
        base_success = float(row["ho_success_rate_pct"])
        base_pingpong = float(row["ho_pingpong_count"])

        if action is not None:
            # action shape is MultiDiscrete([5, 7, 5, 3])
            tilt_delta = float(action[0] - 2) * 1.0
            power_delta = float(action[1] - 3) * 1.0
            cio_delta = float(action[2] - 2) * 1.0

            # Signal quality physics: Power delta boosts signals, tilt misalignment harms them
            self.avg_rsrp_dBm = float(np.clip(base_rsrp + power_delta - 1.5 * abs(tilt_delta), -140.0, -40.0))
            self.avg_sinr_dB = float(np.clip(base_sinr + 0.5 * power_delta - 2.0 * abs(tilt_delta), -10.0, 30.0))
            self.avg_rsrq_dB = float(np.clip(base_rsrq + 0.2 * power_delta - 0.5 * abs(tilt_delta), -20.0, 0.0))

            # Handover physics: Deviating from 0-CIO and 0-tilt harms handover success
            success_impact = - 5.0 * abs(cio_delta) - 3.0 * abs(tilt_delta)
            if cio_delta == 0 and tilt_delta == 0:
                success_impact = 2.0  # boost if optimal

            self.ho_success_rate_pct = float(np.clip(base_success + success_impact, 0.0, 100.0))
            self.ho_failure_rate_pct = float(100.0 - self.ho_success_rate_pct)

            # Ping-pong physics: excess power & high positive CIO trigger ping-pongs
            self.ho_pingpong_count = float(max(0.0, base_pingpong + 3.0 * cio_delta + 1.0 * power_delta))
        else:
            self.avg_rsrp_dBm = base_rsrp
            self.avg_rsrq_dB = base_rsrq
            self.avg_sinr_dB = base_sinr
            self.ho_success_rate_pct = base_success
            self.ho_failure_rate_pct = float(row["ho_failure_rate_pct"])
            self.ho_pingpong_count = base_pingpong

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
        # v1: calculate reward based on simulated success, failure, and ping-pongs
        row = self.cell_pm.iloc[self.current_step]
        attempts = float(row.get("ho_attempts_intra", 10.0))

        ho_success_intra = int(round(attempts * (self.ho_success_rate_pct / 100.0)))
        ho_failure_intra = int(round(attempts * (self.ho_failure_rate_pct / 100.0)))

        reward = 0.0
        reward += ho_success_intra * 1.0
        reward += ho_failure_intra * -5.0
        reward += self.ho_pingpong_count * -2.0
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

        self._update_state_from_replay(action=None)
        obs = self._get_obs()
        info = {"cell_id": self.cell_id, "step": self.current_step}
        return obs, info

    def step(
        self, action: typing.Any
    ) -> tuple[np.ndarray, float, bool, bool, dict[str, typing.Any]]:
        # Compute reward of previous step before we increment the time-series row
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
            "action": [int(x) for x in action] if hasattr(action, "__len__") else int(action),
            "action_effect": "simulated transition physics v1",
        }

        return obs, reward, terminated, truncated, info

    def render(self) -> None:
        pass

