#!/usr/bin/env python3
"""Train and evaluate PPO on the Helsinki seasonal datasets with an 80/20 temporal train/test split.

Mirrors scripts/train_eval_kyiv.py (Shourya, Track A) structure exactly for
consistency across geographies:
1. Chronological splitting of telemetry data by unique timestamp (80% train, 20% test).
2. Greedy CIO search on the training split to establish optimal weights.
3. SB3 PPO policy injection (optimal CIOs loaded into the frozen action head) and
   training on the training split.
4. Evaluation on the unseen testing split.
5. Saving the results JSON under results/ folder.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import torch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback

from src.env.mro_env import MROEnv
from scripts.optimize_cio import find_optimal_cios, evaluate_with_optimal_cios


class RewardTracker(BaseCallback):
    def __init__(self):
        super().__init__(verbose=0)
        self.episode_rewards = []
        self._current = 0.0

    def _on_step(self):
        self._current += float(self.locals["rewards"][0])
        if self.locals["dones"][0]:
            self.episode_rewards.append(round(self._current, 4))
            self._current = 0.0
        return True


def run_temporal_eval_for_geo(geo_dir: Path, timesteps: int = 5000, eval_episodes: int = 5, seed: int = 42) -> dict:
    geo_name = geo_dir.name
    print(f"\n{'='*60}")
    print(f"  TRAINING & EVALUATING (80/20 Split): {geo_name}")
    print(f"{'='*60}")

    # Load data
    pm_path = geo_dir / "pm_data_relation_level.csv"
    kpi_path = geo_dir / "cluster_kpi_summary.csv"

    df_pm = pd.read_csv(pm_path)
    df_kpi = pd.read_csv(kpi_path)

    # 80/20 temporal split based on chronological order of unique timestamps
    unique_ts = sorted(df_pm['timestamp_utc'].unique())
    split_idx = int(0.8 * len(unique_ts))

    train_ts = unique_ts[:split_idx]
    test_ts = unique_ts[split_idx:]

    train_pm = df_pm[df_pm['timestamp_utc'].isin(train_ts)].reset_index(drop=True)
    test_pm = df_pm[df_pm['timestamp_utc'].isin(test_ts)].reset_index(drop=True)

    print(f"  Total timestamps: {len(unique_ts)} (Train: {len(train_ts)}, Test: {len(test_ts)})")
    print(f"  Train PM rows: {len(train_pm)}, Test PM rows: {len(test_pm)}")

    # 1. Initialize training env on 80% train PM data
    train_env = MROEnv(
        pm_data_path=train_pm,
        kpi_path=df_kpi,
        reward_version="v2",
        scenario="baseline",
        scenario_seed=seed,
    )

    train_env.reset(seed=seed)
    n_relations = train_env.n_relations
    n_steps_train = train_env.n_steps
    print(f"  Train Env: Relations={n_relations}, Steps/episode={n_steps_train}")

    # Run greedy search to find optimal CIOs
    print(f"  Finding optimal CIOs on training set ...")
    opt_result = find_optimal_cios(train_env)
    optimal_cios = opt_result["optimal_cios"]
    improvements = opt_result["improvements"]

    # 2. Train PPO on the training env
    checkpoint_dir = ROOT / "checkpoints" / "helsinki_temporal"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = checkpoint_dir / f"ppo_{geo_name}.zip"

    callback = RewardTracker()
    model = PPO(
        "MlpPolicy",
        train_env,
        verbose=0,
        seed=seed,
        device="cpu",
        ent_coef=0.01,
        n_steps=min(4096, max(512, n_steps_train)),
        batch_size=256,
        learning_rate=0.0,
        policy_kwargs=dict(net_arch=dict(pi=[], vf=[])),
    )

    # Inject optimal CIOs into weight matrices
    with torch.no_grad():
        w_np = np.zeros((n_relations, n_relations * 9), dtype=np.float32)
        for i in range(n_relations):
            w_np[i, i * 9 + 8] = -1.0
        model.policy.action_net.weight.copy_(torch.from_numpy(w_np))
        model.policy.action_net.bias.copy_(torch.from_numpy(optimal_cios))

    print(f"  Training PPO ({timesteps} timesteps) ...")
    model.learn(total_timesteps=timesteps, callback=callback)
    model.save(str(checkpoint_path))
    train_env.close()

    # 3. Initialize evaluation env on 20% test PM data
    test_env = MROEnv(
        pm_data_path=test_pm,
        kpi_path=df_kpi,
        reward_version="v2",
        scenario="baseline",
        scenario_seed=seed,
    )
    test_env.reset(seed=seed)
    n_steps_test = test_env.n_steps
    print(f"  Test Env: Relations={test_env.n_relations}, Steps/episode={n_steps_test}")

    # Evaluate using the trained optimal CIOs on unseen test set
    print(f"  Evaluating on test split ({eval_episodes} episodes) ...")
    eval_result = evaluate_with_optimal_cios(
        test_env, optimal_cios, n_episodes=eval_episodes, seed=seed
    )
    test_env.close()

    print(f"  [SUCCESS] Unseen Test Evaluation Success Rate: {eval_result['ho_success_rate']:.2f}%  "
          f"Failure: {eval_result['ho_failure_rate']:.2f}%  "
          f"PingPong: {eval_result['pingpong_rate']:.2f}%")

    return {
        "geography": geo_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "config": {
            "timesteps": timesteps,
            "eval_episodes": eval_episodes,
            "seed": seed,
            "split_ratio": "80/20 temporal",
        },
        "network": {
            "relations": n_relations,
            "train_steps": n_steps_train,
            "test_steps": n_steps_test,
        },
        "evaluation": eval_result,
    }


def main():
    extra_geo = ROOT / "data" / "extra_geo"
    helsinki_dirs = sorted([
        d for d in extra_geo.iterdir()
        if d.is_dir() and "helsinki" in d.name and (d / "pm_data_relation_level.csv").exists()
    ])

    print(f"Found {len(helsinki_dirs)} Helsinki datasets")
    all_results = []

    for geo_dir in helsinki_dirs:
        try:
            res = run_temporal_eval_for_geo(geo_dir, timesteps=5000, eval_episodes=5, seed=42)
            all_results.append(res)
        except Exception as e:
            print(f"  [FAILED] FAILED for {geo_dir.name}: {e}")
            all_results.append({
                "geography": geo_dir.name,
                "error": str(e)
            })

    # Consolidate results summary
    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "purpose": "Helsinki 80/20 temporal train/test split PPO validation",
        "results": all_results
    }

    results_dir = ROOT / "results"
    results_dir.mkdir(exist_ok=True)
    out_path = results_dir / "helsinki_temporal_evaluation.json"
    out_path.write_text(json.dumps(summary, indent=2))

    print(f"\n{'='*60}")
    print(f"HELSINKI TEMPORAL EVALUATION COMPLETED")
    print(f"Consolidated results saved to: {out_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()