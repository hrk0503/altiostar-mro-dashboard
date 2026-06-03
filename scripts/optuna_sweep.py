"""Optuna hyperparameter sweep script for the MRO Gymnasium environment.
Tracks trials live in MLflow.
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
import optuna
import mlflow
from stable_baselines3 import PPO

from src.env.mro_env import MROEnv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run_sweep(timesteps: int, n_trials: int, mode: str, seed: int, device: str) -> None:
    base_dir = Path(__file__).resolve().parents[1]
    
    # Select default files based on mode
    if mode == "relation":
        pm_data_path = base_dir / "data" / "synthetic" / "pm_data_relation_level.csv"
    else:
        pm_data_path = base_dir / "data" / "synthetic" / "pm_data_april2026.csv"
        
    kpi_path = base_dir / "data" / "synthetic" / "cluster_kpi_summary.csv"

    logger.info("Pre-loading dataframes for environment cache...")
    pm_df = pd.read_csv(pm_data_path)
    kpi_df = pd.read_csv(kpi_path)

    # Build the optimization env
    logger.info("Building env in %s mode...", mode)
    env = MROEnv(pm_data_path=pm_df, kpi_path=kpi_df)

    # Setup MLflow tracking and experiment
    mlflow.set_tracking_uri("sqlite:///mlflow.db")
    mlflow.set_experiment("MRO_Optuna_Sweep")

    def objective(trial: optuna.Trial) -> float:
        # Suggest parameters
        learning_rate = trial.suggest_float("learning_rate", 1e-5, 1e-2, log=True)
        n_steps = trial.suggest_categorical("n_steps", [512, 1024, 2048])
        
        # Ensure batch_size is <= n_steps and divides n_steps
        possible_batch_sizes = [b for b in [16, 32, 64, 128, 256] if b <= n_steps and n_steps % b == 0]
        batch_size = trial.suggest_categorical("batch_size", possible_batch_sizes)
        gamma = trial.suggest_float("gamma", 0.9, 0.999)

        logger.info(
            "Trial %d: LR=%.6f, n_steps=%d, batch_size=%d, gamma=%.4f",
            trial.number, learning_rate, n_steps, batch_size, gamma
        )

        # Log trial to MLflow under active study run
        with mlflow.start_run(run_name=f"trial_{trial.number}", nested=True) as run:
            mlflow.log_params({
                "learning_rate": learning_rate,
                "n_steps": n_steps,
                "batch_size": batch_size,
                "gamma": gamma,
                "trial_number": trial.number,
                "mode": mode,
            })

            # Create PPO agent
            model = PPO(
                "MlpPolicy",
                env,
                learning_rate=learning_rate,
                n_steps=n_steps,
                batch_size=batch_size,
                gamma=gamma,
                verbose=0,
                seed=seed,
                device=device,
            )

            # Train PPO agent
            model.learn(total_timesteps=timesteps)

            # Evaluate performance over 3 episodes
            eval_rewards = []
            for ep in range(3):
                obs, info = env.reset(seed=seed + 200 + ep)
                done = False
                ep_reward = 0.0
                while not done:
                    action, _ = model.predict(obs, deterministic=True)
                    obs, reward, terminated, truncated, info = env.step(action)
                    ep_reward += reward
                    done = terminated or truncated
                eval_rewards.append(ep_reward)

            mean_reward = float(np.mean(eval_rewards))
            mlflow.log_metric("mean_reward", mean_reward)
            
            # Extract success/ping-pong metrics
            success_rate = float(env.cell_pm["ho_success_rate_pct"].mean())
            mlflow.log_metric("ho_success_rate", success_rate)
            
            logger.info("Trial %d finished with mean_reward: %.2f", trial.number, mean_reward)
            return mean_reward

    # Start study run in MLflow to group trials
    with mlflow.start_run(run_name=f"study_sweep_{mode}") as study_run:
        study = optuna.create_study(direction="maximize")
        study.optimize(objective, n_trials=n_trials)

        logger.info("Optuna study completed!")
        logger.info("Best trial: Trial %d", study.best_trial.number)
        logger.info("Best Value: %.2f", study.best_value)
        logger.info("Best Params: %s", study.best_params)

        # Log best results to study run
        mlflow.log_params(study.best_params)
        mlflow.log_metric("best_mean_reward", study.best_value)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Optuna hyperparameter sweep.")
    parser.add_argument("--timesteps", type=int, default=3000, help="Timesteps per trial.")
    parser.add_argument("--trials", type=int, default=5, help="Number of trials.")
    parser.add_argument("--mode", default="relation", choices=["cell", "relation"], help="Environment mode.")
    parser.add_argument("--seed", type=int, default=42, help="Seed.")
    parser.add_argument("--device", default="cpu", help="PyTorch device.")
    args = parser.parse_args()

    run_sweep(args.timesteps, args.trials, args.mode, args.seed, args.device)
