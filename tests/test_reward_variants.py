import sys
import json
from pathlib import Path

# Add repo root to path so imports work from any location
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import pandas as pd
import numpy as np
from src.env.mro_env import MROEnv


def run_reward_comparison(num_episodes: int = 3, steps_per_episode: int = 10, scenario: str = "baseline"):
    """
    Compare reward variants v0-v3 over multiple episodes and steps.
    
    Args:
        num_episodes: Number of full episode resets to run
        steps_per_episode: Number of steps per episode
        scenario: Scenario name ('baseline', 'rain_fade', etc.)
    """
    variants = ["v0", "v1", "v2", "v3"]
    results = []
    
    print(f"\n{'=' * 85}")
    print(f"  REWARD VARIANT COMPARISON")
    print(f"  Scenario: {scenario} | Episodes: {num_episodes} | Steps/Episode: {steps_per_episode}")
    print(f"{'=' * 85}\n")
    
    for variant in variants:
        print(f"Testing variant {variant.upper()}...", end=" ", flush=True)
        
        try:
            # Initialize environment
            env = MROEnv(reward_version=variant, scenario=scenario)
            
            variant_rewards = []
            variant_success_rates = []
            variant_failure_rates = []
            variant_pingpong_metrics = []
            
            # Run multiple episodes
            for ep in range(num_episodes):
                obs, info = env.reset()
                ep_rewards = []
                
                # Run steps within episode
                for step_num in range(steps_per_episode):
                    dummy_action = env.action_space.sample()
                    obs, reward, terminated, truncated, step_info = env.step(dummy_action)
                    ep_rewards.append(reward)
                    
                    if terminated:
                        break
                
                variant_rewards.extend(ep_rewards)
            
            # After all episodes, extract latest KPIs from episode_history
            if env.mode == "relation":
                # Relation mode: episode_history has aggregated per-step metrics
                if env.episode_history:
                    latest = env.episode_history[-1]
                    success_rate = latest.get("ho_success_rate_pct", 0.0)
                    failure_rate = latest.get("ho_failure_rate_pct", 0.0)
                    pingpong_metric = latest.get("pingpong_rate_pct", 0.0)
                    pingpong_label = "Ping-Pong Rate (%)"
                else:
                    success_rate = failure_rate = pingpong_metric = 0.0
                    pingpong_label = "Ping-Pong Rate (%)"
            else:
                # Cell mode: use cell_pm_df (which is static from init + updated by steps)
                if len(env.cell_pm_df) > 0:
                    latest = env.cell_pm_df.iloc[-1]
                    success_rate = latest.get("ho_success_rate_pct", 0.0)
                    failure_rate = latest.get("ho_failure_rate_pct", 0.0)
                    pingpong_metric = latest.get("ho_pingpong_count", 0.0)
                    pingpong_label = "Ping-Pong Count"
                else:
                    success_rate = failure_rate = pingpong_metric = 0.0
                    pingpong_label = "Ping-Pong Count"
            
            avg_reward = np.mean(variant_rewards) if variant_rewards else 0.0
            
            results.append({
                "Variant": variant.upper(),
                "Mode": env.mode.upper(),
                "Avg Reward": round(avg_reward, 3),
                "HO Success %": round(success_rate, 1),
                "HO Failure %": round(failure_rate, 1),
                pingpong_label: round(pingpong_metric, 2),
                "Num Steps": len(variant_rewards),
            })
            
            print("✓")
            
        except Exception as e:
            print(f"✗ ERROR: {str(e)[:60]}")
            results.append({
                "Variant": variant.upper(),
                "Mode": "ERROR",
                "Avg Reward": "N/A",
                "HO Success %": "N/A",
                "HO Failure %": "N/A",
                "Ping-Pong": "N/A",
                "Num Steps": 0,
            })
    
    # Display results table
    df = pd.DataFrame(results)
    
    print(f"\n{'-' * 85}")
    print(f"  KPI SUMMARY TABLE")
    print(f"{'-' * 85}")
    print(df.to_string(index=False))
    print(f"{'-' * 85}\n")
    
    # V0 excluded: count-based scale (~3000+) not comparable to rate-based v1-v3 (~70-75)
    if all(r["Avg Reward"] != "N/A" for r in results):
        normalized = [r for r in results if r["Variant"] != "V0"]
        best_variant = max(normalized, key=lambda x: float(x["Avg Reward"]))
        print(f"  Note: V0 excluded from ranking (count-based, ~40x scale vs v1-v3)")
        print(f"  Best Performer (v1-v3): {best_variant['Variant']} (avg reward: {best_variant['Avg Reward']})")
    

    # Save results to JSON for dashboard
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)
    output = {
        "generated": "reward_variant_comparison",
        "scenario": scenario,
        "episodes": num_episodes,
        "steps_per_episode": steps_per_episode,
        "note": "V0 excluded from best_performer ranking — count-based scale (~3000+) vs rate-based v1-v3 (~70-75)",
        "best_performer": best_variant["Variant"],
        "variants": results,
    }
    out_path = results_dir / "reward_variant_comparison.json"
    out_path.write_text(json.dumps(output, indent=2))
    print(f"  Saved to {out_path}\n")
    return df


if __name__ == "__main__":
    # Run baseline scenario
    run_reward_comparison(num_episodes=3, steps_per_episode=10, scenario="baseline")
    
    # Optionally test rain_fade scenario
    # run_reward_comparison(num_episodes=3, steps_per_episode=10, scenario="rain_fade")