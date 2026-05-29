"""Forge Agent — ML Engineer.

Builds Gymnasium environment from YAML config, runs PPO training.
Outputs: Gymnasium env, training scripts, model checkpoints.
"""

import os
from pathlib import Path
from typing import Any

import yaml
import mlflow
import numpy as np
from pydantic import BaseModel
from stable_baselines3 import PPO

from src.env.mro_env import MROEnv


class TrainingResult(BaseModel):
    episodes: int
    mean_reward: float
    ho_success_rate: float
    ping_pong_rate: float
    checkpoint_path: str
    mlflow_run_id: str


class ForgeAgent:
    """Creates RL environment from config and trains PPO agent."""

    def build_env(self, config_path: Path) -> MROEnv:
        """Build Gymnasium environment from YAML config."""
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        data_config = config.get("data", {})
        pm_path = data_config.get("pm_data", "data/synthetic/pm_data_april2026.csv")
        kpi_path = data_config.get("cluster_summary", "data/synthetic/cluster_kpi_summary.csv")

        # Resolve paths relative to workspace if necessary
        return MROEnv(pm_data_path=str(pm_path), kpi_path=str(kpi_path))

    def train(self, env: MROEnv, total_timesteps: int = 100_000) -> TrainingResult:
        """Train PPO agent with MLflow tracking."""
        mlflow.set_experiment("MRO_Training")

        checkpoint_dir = Path("checkpoints")
        checkpoint_dir.mkdir(exist_ok=True)
        checkpoint_path = checkpoint_dir / f"ppo_mro_{total_timesteps}.zip"

        with mlflow.start_run() as run:
            # 1. Log PPO hyperparameters and configuration
            mlflow.log_param("algorithm", "PPO")
            mlflow.log_param("total_timesteps", total_timesteps)
            mlflow.log_param("policy_type", "MlpPolicy")
            mlflow.log_param("cell_id", env.cell_id)

            # 2. Initialize Stable Baselines3 PPO
            model = PPO(
                "MlpPolicy",
                env,
                verbose=0,
                seed=42,
            )

            # 3. Train the model
            model.learn(total_timesteps=total_timesteps)

            # 4. Save model checkpoint
            model.save(str(checkpoint_path))
            mlflow.log_artifact(str(checkpoint_path))

            # 5. Evaluate the trained model
            eval_metrics = self.evaluate(checkpoint_path, env, n_episodes=5)

            # 6. Log evaluation metrics
            mlflow.log_metric("mean_reward", eval_metrics["mean_reward"])
            mlflow.log_metric("ho_success_rate", eval_metrics["ho_success_rate"])
            mlflow.log_metric("ping_pong_rate", eval_metrics["ping_pong_rate"])

            return TrainingResult(
                episodes=5,
                mean_reward=eval_metrics["mean_reward"],
                ho_success_rate=eval_metrics["ho_success_rate"],
                ping_pong_rate=eval_metrics["ping_pong_rate"],
                checkpoint_path=str(checkpoint_path),
                mlflow_run_id=run.info.run_id,
            )

    def evaluate(self, model_path: Path, env: MROEnv, n_episodes: int = 100) -> dict[str, Any]:
        """Evaluate trained model and return KPI metrics."""
        if not model_path.exists():
            raise FileNotFoundError(f"Model checkpoint not found: {model_path}")

        model = PPO.load(str(model_path))

        total_rewards = []
        success_rates = []
        ping_pong_rates = []

        for _ in range(n_episodes):
            obs, info = env.reset()
            done = False
            episode_reward = 0.0

            while not done:
                action, _states = model.predict(obs, deterministic=True)
                obs, reward, terminated, truncated, info = env.step(action)
                episode_reward += reward
                done = terminated or truncated

            total_rewards.append(episode_reward)

            # Extract metrics from MROEnv cell telemetry
            success_rate = float(env.cell_pm["ho_success_rate_pct"].mean())
            
            attempts = env.cell_pm["ho_attempts_intra"].sum()
            pings = env.cell_pm["ho_pingpong_count"].sum()
            ping_pong_rate = float((pings / attempts) if attempts > 0 else 0.0)


            success_rates.append(success_rate)
            ping_pong_rates.append(ping_pong_rate)

        return {
            "mean_reward": float(np.mean(total_rewards)),
            "ho_success_rate": float(np.mean(success_rates)),
            "ping_pong_rate": float(np.mean(ping_pong_rates)),
        }
