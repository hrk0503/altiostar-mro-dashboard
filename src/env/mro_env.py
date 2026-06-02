import logging
import typing
from pathlib import Path

import gymnasium as gym
import numpy as np
import pandas as pd
from gymnasium import spaces

logger = logging.getLogger(__name__)


class MROEnv(gym.Env[typing.Any, typing.Any]):
    """
    MRO (Mobility Robustness Optimization) Gymnasium Environment.
    Supports both cell-level (v0/v1) and relation-level (v2) PM optimization dynamically.
    """

    def __init__(
        self,
        pm_data_path: str | None = None,
        kpi_path: str | None = None,
        cell_id: str | None = None,
    ):
        super().__init__()

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

        self.pm_data_raw = pd.read_csv(pm_data_path)
        self.kpi_data = pd.read_csv(kpi_path)

        # Detect mode based on column schema
        if "source_cell_id" in self.pm_data_raw.columns:
            self.mode = "relation"
            self.cell_id = cell_id or "relation_level_network"
            
            # Group relations
            all_relations = list(self.pm_data_raw.groupby(["source_cell_id", "target_cell_id"]).groups.keys())
            if cell_id:
                self.relations = [(src, tgt) for (src, tgt) in all_relations if src == cell_id]
            else:
                self.relations = all_relations
            
            self.n_relations = len(self.relations)
            
            # Pre-group for fast O(1) step access
            self.relation_groups = {}
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
                self.relation_groups[(src, tgt)] = {
                    "cio_groups": cio_groups,
                    "all_cios": np.sort(np.array(list(cio_groups.keys()))),
                    "full_df": group.reset_index(drop=True),
                }

            self.n_steps = len(self.pm_data_raw) // len(all_relations) if len(all_relations) > 0 else 0
            self.current_step = 0
            self.episode_history = []

            # Observation matrix shape (n_relations, 9)
            low = np.full((self.n_relations, 9), -1000.0, dtype=np.float32)
            high = np.full((self.n_relations, 9), 100000.0, dtype=np.float32)
            self.observation_space = spaces.Box(low=low, high=high, dtype=np.float32)

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
            low = np.array([-140.0, -20.0, -10.0, 0.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float32)
            high = np.array([-40.0, 0.0, 30.0, 100.0, 100.0, 100.0, 100.0, 500.0], dtype=np.float32)
            self.observation_space = spaces.Box(low=low, high=high, dtype=np.float32)

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

    def _update_state_from_replay(self, action: typing.Any = None) -> None:
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
        self.episode_history = []

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
                self.current_state[i] = [
                    float(row["ho_attempts"]),
                    float(row["ho_successes"]),
                    float(row["ho_failures"]),
                    float(row["too_early_ho"]),
                    float(row["too_late_ho"]),
                    float(row["wrong_cell"]),
                    float(row["correct_cell"]),
                    float(row["ping_pong"]),
                    float(row["cio_db"]),
                ]
            info = {"cell_id": self.cell_id, "step": self.current_step}
            return self.current_state, info
        else:
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

            reward = float(total_successes - 10 * total_failures - 3 * total_ping_pongs)
            rate = (total_successes / total_attempts * 100.0) if total_attempts > 0 else 100.0
            
            self.episode_history.append({
                "ho_attempts_intra": total_attempts,
                "ho_success_intra": total_successes,
                "ho_pingpong_count": total_ping_pongs,
                "ho_success_rate_pct": rate,
                "ho_failure_rate_pct": (total_failures / total_attempts * 100.0) if total_attempts > 0 else 0.0,
                "ho_failure_too_early": sum(next_state[:, 3]),
                "ho_failure_too_late": sum(next_state[:, 4]),
                "ho_failure_wrong_cell": sum(next_state[:, 5]),
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
                "action": [int(x) for x in action] if hasattr(action, "__len__") else int(action),
                "action_effect": "simulated transition physics v1",
            }
            return obs, reward, terminated, truncated, info

    def render(self) -> None:
        pass
