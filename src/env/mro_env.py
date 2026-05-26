import gymnasium as gym
import numpy as np
import pandas as pd
from gymnasium import spaces

class MROEnv(gym.Env):
    """
    MRO (Mobility Robustness Optimization) Gymnasium Environment.
    
    Observation space: RSRP, RSRQ, SINR, PRB utilization, HO success rate,
                       HO failure rate, ping-pong count (per cell, per step)
    Action space: tilt delta, power delta, CIO delta, neighbor list toggle
    Reward: +1 HO success, -5 HO failure, -2 ping-pong
    """

    metadata = {"render_modes": []}

    def __init__(self, pm_data_path: str, kpi_path: str, cell_id: str = None):
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
        row = self.cell_pm.iloc[self.current_step]
        reward = 0.0
        reward += row["ho_success_intra"] * 1.0
        reward += row["ho_failure_intra"] * -5.0
        reward += row["ho_pingpong_count"] * -2.0
        return reward

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.current_step = 0
        obs = self._get_obs()
        info = {"cell_id": self.cell_id, "step": self.current_step}
        return obs, info

    def step(self, action):
        reward = self._get_reward()
        self.current_step += 1
        terminated = self.current_step >= self.n_steps
        truncated = False

        if terminated:
            obs = np.zeros(8, dtype=np.float32)
        else:
            obs = self._get_obs()

        info = {
            "cell_id": self.cell_id,
            "step": self.current_step,
            "action": action,
        }

        return obs, reward, terminated, truncated, info

    def render(self):
        pass