from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from scripts.run_seeded_experiments import main


def test_run_seeded_experiments_workflow(tmp_path, monkeypatch):
    """Test that the run_seeded_experiments CLI executes and routes files correctly."""
    # We mock run_single_experiment to avoid running actual PPO training in unit tests,
    # but verify all directories and file-moving operations are executed correctly.
    mock_result = {
        "experiment": "v2_baseline_seed_1",
        "reward_version": "v2",
        "scenario": "baseline",
        "training": {
            "time_s": 0.1,
            "episode_rewards": [1.0],
            "checkpoint_path": "checkpoints/ppo_v2_baseline_seed_1.zip",
        },
        "evaluation": {
            "mean_reward": 10.0,
            "std_reward": 0.5,
            "ho_success_rate": 99.5,
            "pingpong_rate": 1.2,
        },
        "mlflow_run_id": "mock_id_123",
    }

    # Set up temp directories to simulate working directory
    results_dir = tmp_path / "results"
    checkpoints_dir = tmp_path / "checkpoints"
    results_dir.mkdir()
    checkpoints_dir.mkdir()

    # Stub run_single_experiment to create the temp files and return mock_result
    def stub_run_single_experiment(variant, scenario, timesteps, eval_episodes, seed, run_name):
        # Create the temp files that run_single_experiment would have created
        temp_json = results_dir / f"experiment_{run_name}.json"
        temp_model = checkpoints_dir / f"ppo_{run_name}.zip"
        
        # Write mock data
        run_result = mock_result.copy()
        run_result["experiment"] = run_name
        run_result["training"] = mock_result["training"].copy()
        run_result["training"]["checkpoint_path"] = f"checkpoints/ppo_{run_name}.zip"
        
        temp_json.write_text(json.dumps(run_result))
        temp_model.write_text("dummy model bytes")
        
        return run_result

    # Patch Paths and the runner function
    monkeypatch.chdir(tmp_path)
    
    with patch("scripts.run_seeded_experiments.run_single_experiment", side_effect=stub_run_single_experiment):
        # Run CLI with dummy arguments
        monkeypatch.setattr("sys.argv", ["run_seeded_experiments.py", "--timesteps", "10", "--eval-episodes", "1"])
        main()

    # Check that the files were correctly moved into the seeded_runs subdirectories
    seeded_results_dir = results_dir / "seeded_runs"
    seeded_checkpoints_dir = checkpoints_dir / "seeded_runs"

    assert seeded_results_dir.is_dir()
    assert seeded_checkpoints_dir.is_dir()

    # Assert files exist for all 5 seeds
    for seed in [1, 2, 3, 4, 5]:
        run_name = f"v2_baseline_seed_{seed}"
        
        expected_json = seeded_results_dir / f"experiment_{run_name}.json"
        expected_model = seeded_checkpoints_dir / f"ppo_{run_name}.zip"
        
        assert expected_json.exists()
        assert expected_model.exists()
        
        # Verify JSON content was updated with the new checkpoint path
        with open(expected_json) as f:
            data = json.load(f)
            assert Path(data["training"]["checkpoint_path"]).resolve() == expected_model.resolve()
