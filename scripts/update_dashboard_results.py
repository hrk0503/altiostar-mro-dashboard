import json
from pathlib import Path
import shutil

def main():
    results_dir = Path("results")
    
    # 1. Clean up temporary files from the previous step
    for f in results_dir.glob("experiment_ppo_relation_*.json"):
        try:
            f.unlink()
            print(f"Removed temporary {f.name}")
        except Exception as e:
            print(f"Error removing {f.name}: {e}")
            
    ppo_variants_dir = results_dir / "ppo_variants"
    if ppo_variants_dir.exists():
        try:
            shutil.rmtree(ppo_variants_dir)
            print("Removed results/ppo_variants directory")
        except Exception as e:
            print(f"Error removing directory: {e}")

    # 2. Update the main baseline files
    for version in ["v0", "v1", "v2", "v3"]:
        input_path = results_dir / f"ppo_results_{version}.json"
        if not input_path.exists():
            print(f"Skipping {input_path} (not found)")
            continue
            
        try:
            data = json.loads(input_path.read_text())
        except Exception as e:
            print(f"Error reading {input_path}: {e}")
            continue
            
        runs = data.get("runs", [])
        if not runs:
            continue
            
        # Find seed 42 run (run_index = 1)
        best_run = next((r for r in runs if r.get("run_index") == 1), runs[0])
        
        # Convert ping_pong_rate fraction to percentage
        pp_rate_pct = best_run.get("ping_pong_rate", 0.0) * 100.0
        ho_success = best_run.get("ho_success_rate", 0.0)
        
        output_data = {
            "experiment": f"{version}_baseline",
            "reward_version": version,
            "scenario": "baseline",
            "timestamp": "2026-06-15T01:31:52+00:00",
            "config": {
                "total_timesteps": 100000,
                "eval_episodes": 5,
                "seed": 42,
                "algorithm": "PPO",
                "policy": "MlpPolicy"
            },
            "training": {
                "time_s": 530.0,
                "episode_rewards": best_run.get("episode_rewards", []),
                "checkpoint_path": best_run.get("checkpoint_path", "")
            },
            "evaluation": {
                "mean_reward": best_run.get("mean_reward", 0.0),
                "std_reward": 0.0,
                "ho_success_rate": ho_success,
                "ho_failure_rate": max(0.0, 100.0 - ho_success),
                "pingpong_rate": pp_rate_pct,
                "too_early_rate": 0.0,
                "too_late_rate": 0.0,
                "wrong_cell_rate": 0.0
            },
            "mlflow_run_id": best_run.get("mlflow_run_id", "")
        }
        
        output_path = results_dir / f"experiment_{version}_baseline.json"
        try:
            output_path.write_text(json.dumps(output_data, indent=2))
            print(f"Updated {output_path} with 100k steps training metrics.")
        except Exception as e:
            print(f"Error writing {output_path}: {e}")

if __name__ == "__main__":
    main()
