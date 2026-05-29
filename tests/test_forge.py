"""Tests for Forge Agent — PPO Training and MLflow logging."""

from pathlib import Path

import pytest

from src.agents.forge import ForgeAgent
from src.env.mro_env import MROEnv


class TestForgeAgent:
    def setup_method(self):
        self.agent = ForgeAgent()
        self.config_path = Path("configs/mro_default.yaml")

    def test_build_env(self):
        env = self.agent.build_env(self.config_path)
        assert isinstance(env, MROEnv)
        assert env.observation_space.shape == (8,)
        assert env.action_space.nvec.tolist() == [5, 7, 5, 3]

    def test_train_and_evaluate(self):
        env = self.agent.build_env(self.config_path)
        # Use a very small timestep count for unit testing speed
        result = self.agent.train(env, total_timesteps=100)

        assert result.episodes == 5
        assert isinstance(result.mean_reward, float)
        assert 0.0 <= result.ho_success_rate <= 100.0
        assert 0.0 <= result.ping_pong_rate <= 1.0
        assert Path(result.checkpoint_path).exists()
        assert len(result.mlflow_run_id) > 0

        # Verify evaluation executes successfully
        eval_metrics = self.agent.evaluate(Path(result.checkpoint_path), env, n_episodes=2)
        assert "mean_reward" in eval_metrics
        assert "ho_success_rate" in eval_metrics
        assert "ping_pong_rate" in eval_metrics
        assert isinstance(eval_metrics["mean_reward"], float)
