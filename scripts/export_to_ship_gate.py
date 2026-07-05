import json
from pathlib import Path


def main():
    results_dir = Path("results")
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
            
        for run in data.get("runs", []):
            seed = run.get("run_index", 1) + 41
            run_name = f"ppo_relation_{version}_seed_{seed}"
            
            # Convert ping_pong_rate fraction to percentage
            pp_rate_pct = run.get("ping_pong_rate", 0.0) * 100.0
            
            output_data = {
                "experiment": run_name,
                "reward_version": version,
                "evaluation": {
                    "ho_success_rate": run.get("ho_success_rate", 0.0),
                    "pingpong_rate": pp_rate_pct
                }
            }
            output_path = results_dir / f"experiment_{run_name}.json"
            output_path.write_text(json.dumps(output_data, indent=2))
            print(f"Exported standard experiment JSON to {output_path}")

if __name__ == "__main__":
    main()
