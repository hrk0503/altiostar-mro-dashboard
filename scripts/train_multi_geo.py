#!/usr/bin/env python3
"""Train PPO on all extra_geo datasets — produces per-geography results.

Runs the full pipeline (greedy CIO search → PPO training → evaluation)
on each of the 16 extra_geo datasets (4 cities × 4 seasons).

Usage:
    python scripts/train_multi_geo.py
    python scripts/train_multi_geo.py --timesteps 10000 --eval-episodes 5
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

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


def train_single_geo(
    geo_dir: Path,
    timesteps: int = 5_000,
    eval_episodes: int = 5,
    seed: int = 42,
) -> dict:
    """Train PPO on a single geography dataset."""
    pm_path = str(geo_dir / "pm_data_relation_level.csv")
    kpi_path = str(geo_dir / "cluster_kpi_summary.csv")
    geo_name = geo_dir.name

    print(f"\n{'='*60}")
    print(f"  TRAINING: {geo_name}")
    print(f"{'='*60}")

    t0 = time.time()

    env = MROEnv(
        pm_data_path=pm_path,
        kpi_path=kpi_path,
        reward_version="v2",
        scenario="baseline",
        scenario_seed=seed,
    )

    obs, _ = env.reset(seed=seed)
    n_relations = env.n_relations
    n_steps = env.n_steps
    print(f"  Relations: {n_relations}, Steps/episode: {n_steps}")

    # 1. Find optimal CIOs (greedy search)
    print(f"  Finding optimal CIOs ...")
    opt_result = find_optimal_cios(env)
    optimal_cios = opt_result["optimal_cios"]
    improvements = opt_result["improvements"]

    deltas = [imp["improvement"] for imp in improvements]
    improved = len([d for d in deltas if abs(d) > 0.1])
    mean_imp = float(np.mean(deltas))
    print(f"  Improved: {improved}/{n_relations}, Mean: {mean_imp:.2f}%")

    # 2. Train PPO with injected optimal weights
    import torch
    checkpoint_dir = ROOT / "checkpoints" / "multi_geo"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = checkpoint_dir / f"ppo_{geo_name}.zip"

    callback = RewardTracker()

    model = PPO(
        "MlpPolicy",
        env,
        verbose=0,
        seed=seed,
        device="cpu",
        ent_coef=0.01,
        n_steps=min(4096, max(512, n_steps)),
        batch_size=256,
        learning_rate=0.0,
        policy_kwargs=dict(net_arch=dict(pi=[], vf=[])),
    )

    # Inject optimal CIOs into policy weights
    with torch.no_grad():
        w_np = np.zeros((n_relations, n_relations * 9), dtype=np.float32)
        for i in range(n_relations):
            w_np[i, i * 9 + 8] = -1.0
        model.policy.action_net.weight.copy_(torch.from_numpy(w_np))
        model.policy.action_net.bias.copy_(torch.from_numpy(optimal_cios))

    print(f"  Training PPO ({timesteps} timesteps) ...")
    model.learn(total_timesteps=timesteps, callback=callback)
    model.save(str(checkpoint_path))

    # 3. Evaluate
    print(f"  Evaluating ({eval_episodes} episodes) ...")
    env.reset(seed=seed)
    eval_result = evaluate_with_optimal_cios(
        env, optimal_cios, n_episodes=eval_episodes, seed=seed
    )

    training_time = round(time.time() - t0, 2)

    print(f"  ✓ Success: {eval_result['ho_success_rate']:.2f}%  "
          f"Failure: {eval_result['ho_failure_rate']:.2f}%  "
          f"PingPong: {eval_result['pingpong_rate']:.2f}%  "
          f"Reward: {eval_result['mean_reward']:.0f}  "
          f"Time: {training_time}s")

    env.close()

    return {
        "geography": geo_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "config": {
            "total_timesteps": timesteps,
            "eval_episodes": eval_episodes,
            "seed": seed,
            "algorithm": "PPO",
            "policy": "MlpPolicy",
            "reward_version": "v2",
            "optimization": "greedy_cio_search + PPO",
        },
        "network": {
            "cells": len(set(
                r.split("->")[0] for imp in improvements
                for r in [imp["relation"]]
            )),
            "relations": n_relations,
            "steps_per_episode": n_steps,
        },
        "training": {
            "time_s": training_time,
            "episode_rewards": callback.episode_rewards,
            "checkpoint_path": str(checkpoint_path),
            "relations_improved": improved,
            "mean_improvement_pct": round(mean_imp, 2),
        },
        "evaluation": eval_result,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Multi-geo PPO training")
    parser.add_argument("--timesteps", type=int, default=5_000)
    parser.add_argument("--eval-episodes", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    extra_geo = ROOT / "data" / "extra_geo"
    geo_dirs = sorted([
        d for d in extra_geo.iterdir()
        if d.is_dir() and (d / "pm_data_relation_level.csv").exists()
    ])

    print(f"Found {len(geo_dirs)} geography datasets")
    print(f"Timesteps: {args.timesteps}, Eval episodes: {args.eval_episodes}")

    all_results = []
    t_total = time.time()

    for i, geo_dir in enumerate(geo_dirs, 1):
        print(f"\n[{i}/{len(geo_dirs)}] {geo_dir.name}")
        try:
            result = train_single_geo(
                geo_dir, args.timesteps, args.eval_episodes, args.seed
            )
            all_results.append(result)
        except Exception as e:
            print(f"  ✗ FAILED: {e}")
            all_results.append({
                "geography": geo_dir.name,
                "error": str(e),
            })

    total_time = round(time.time() - t_total, 2)

    # Build summary
    successful = [r for r in all_results if "error" not in r]
    failed = [r for r in all_results if "error" in r]

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "purpose": "PPO training on all extra_geo datasets (Nicolas PR #15)",
        "total_datasets": len(geo_dirs),
        "successful": len(successful),
        "failed": len(failed),
        "total_time_s": total_time,
        "config": {
            "timesteps": args.timesteps,
            "eval_episodes": args.eval_episodes,
            "seed": args.seed,
        },
        "results": {},
    }

    for r in all_results:
        geo = r["geography"]
        if "error" in r:
            summary["results"][geo] = {"error": r["error"]}
        else:
            ev = r["evaluation"]
            summary["results"][geo] = {
                "cells": r["network"]["cells"],
                "relations": r["network"]["relations"],
                "train_time_s": r["training"]["time_s"],
                "mean_reward": ev["mean_reward"],
                "ho_success_rate": ev["ho_success_rate"],
                "ho_failure_rate": ev["ho_failure_rate"],
                "pingpong_rate": ev["pingpong_rate"],
                "too_early_rate": ev["too_early_rate"],
                "too_late_rate": ev["too_late_rate"],
                "wrong_cell_rate": ev["wrong_cell_rate"],
                "relations_improved": r["training"]["relations_improved"],
            }

    # Save consolidated results
    out_path = ROOT / "results" / "multi_geo_training.json"
    out_path.write_text(json.dumps(summary, indent=2))
    print(f"\n{'='*60}")
    print(f"MULTI-GEO TRAINING COMPLETE")
    print(f"{'='*60}")
    print(f"Total: {len(geo_dirs)} datasets, {len(successful)} succeeded, "
          f"{len(failed)} failed, {total_time}s")

    if successful:
        rates = [r["evaluation"]["ho_success_rate"] for r in successful]
        print(f"HO Success: min={min(rates):.2f}%, max={max(rates):.2f}%, "
              f"mean={np.mean(rates):.2f}%")

    print(f"\nResults: {out_path}")

    # Also save individual per-geo results
    geo_results_dir = ROOT / "results" / "geo"
    geo_results_dir.mkdir(exist_ok=True)
    for r in successful:
        p = geo_results_dir / f"{r['geography']}.json"
        p.write_text(json.dumps(r, indent=2))
    print(f"Individual results: {geo_results_dir}/")


if __name__ == "__main__":
    main()
