"""Forge Agent — ML Engineer.

Builds Gymnasium environment from YAML config, runs PPO training.
Outputs: Gymnasium env, training scripts, model checkpoints.
"""

from pathlib import Path

from pydantic import BaseModel


class TrainingResult(BaseModel):
    episodes: int
    mean_reward: float
    ho_success_rate: float
    ping_pong_rate: float
    checkpoint_path: str
    mlflow_run_id: str


class ForgeAgent:
    """Creates RL environment from config and trains PPO agent."""

    def build_env(self, config_path: Path) -> object:
        """Build Gymnasium environment from YAML config."""
        raise NotImplementedError

    def train(self, env: object, total_timesteps: int = 100_000) -> TrainingResult:
        """Train PPO agent with MLflow tracking."""
        raise NotImplementedError

    def evaluate(self, model_path: Path, env: object, n_episodes: int = 100) -> dict:
        """Evaluate trained model and return KPI metrics."""
        raise NotImplementedError
