import numpy as np

from src.env.mro_env import MROEnv

DATA_DIR = "data/synthetic"


def test_env_runs_random_policy():
    env = MROEnv(
        pm_data_path=f"{DATA_DIR}/pm_data_relation_level.csv",
        kpi_path=f"{DATA_DIR}/cluster_kpi_summary.csv",
    )
    obs, info = env.reset()
    assert obs.shape == (env.n_relations, 9)

    for _ in range(10):  # Run 10 steps to verify stepping
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        if terminated:
            break

    assert info["step"] > 0
    assert "total_attempts" in info


def test_env_termination_and_reset():
    env = MROEnv(
        pm_data_path=f"{DATA_DIR}/pm_data_relation_level.csv",
        kpi_path=f"{DATA_DIR}/cluster_kpi_summary.csv",
    )
    obs, info = env.reset()

    # Fast-forward to the last step to trigger termination on the next step
    env.current_step = env.n_steps - 1
    action = env.action_space.sample()
    obs_term, reward, terminated, truncated, info_term = env.step(action)

    assert terminated
    # Observation after termination should be all zeros
    assert np.all(obs_term == 0.0)
    assert obs_term.shape == (env.n_relations, 9)

    # Verify reset works correctly after termination
    obs_reset, info_reset = env.reset()
    assert obs_reset.shape == (env.n_relations, 9)
    assert info_reset["step"] == 0

    # Test random_start option
    obs_rand, info_rand = env.reset(options={"random_start": True})
    assert obs_rand.shape == (env.n_relations, 9)
    assert 0 <= info_rand["step"] < env.n_steps
