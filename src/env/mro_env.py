"""MRO Gymnasium Environment — the 'digital twin'.

YAML-configurable RL environment for Mobility Robustness Optimization.
Same engine, different use case = different YAML config.

Observation: RSRP, RSRQ, SINR, PRB utilization, HO stats per cell
Action: tilt delta, power delta, CIO adjustment, neighbor list changes
Reward: configurable (v0: +1 success, -5 failure, -2 ping-pong)
"""

from pathlib import Path
from typing import Any

import gymnasium as gym
import numpy as np
import yaml


class MROEnv(gym.Env):
    """Gymnasium environment for MRO training."""

    metadata = {"render_modes": ["human"]}

    def __init__(self, config_path: Path | None = None, **kwargs: Any) -> None:
        super().__init__()
        self.config = self._load_config(config_path) if config_path else self._default_config()

        n_cells = self.config["n_cells"]
        n_obs_features = self.config.get("n_obs_features", 10)
        n_actions = self.config.get("n_actions", 4)

        self.observation_space = gym.spaces.Box(
            low=-np.inf, high=np.inf, shape=(n_cells, n_obs_features), dtype=np.float32
        )
        self.action_space = gym.spaces.Box(
            low=-1.0, high=1.0, shape=(n_cells, n_actions), dtype=np.float32
        )

    def _load_config(self, path: Path) -> dict:
        with open(path) as f:
            return yaml.safe_load(f)

    def _default_config(self) -> dict:
        return {"n_cells": 75, "n_obs_features": 10, "n_actions": 4, "reward_version": "v0"}

    def reset(self, *, seed: int | None = None, options: dict | None = None) -> tuple:
        super().reset(seed=seed)
        obs = self.observation_space.sample()
        return obs, {}

    def step(self, action: np.ndarray) -> tuple:
        obs = self.observation_space.sample()
        reward = 0.0  # TODO: implement reward function
        terminated = False
        truncated = False
        info: dict[str, Any] = {}
        return obs, reward, terminated, truncated, info
