import numpy as np

from src.env.mro_env import MROEnv

DATA_DIR = "data"


def test_env_runs_random_policy():
    env = MROEnv(
        pm_data_path=f"{DATA_DIR}/pm_data_april2026.csv",
        kpi_path=f"{DATA_DIR}/cluster_kpi_summary.csv",
    )
    obs, info = env.reset()
    assert obs.shape == (8,)

    for _ in range(100):
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        if terminated:
            break

    assert info["step"] > 0
    assert "action_effect" in info
    assert info["action_effect"] == "simulated transition physics v1"



def test_env_termination_and_reset():
    env = MROEnv(
        pm_data_path=f"{DATA_DIR}/pm_data_april2026.csv",
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
    assert obs_term.shape == (8,)

    # Verify reset works correctly after termination
    obs_reset, info_reset = env.reset()
    assert obs_reset.shape == (8,)
    assert info_reset["step"] == 0

    # Test random_start option
    obs_rand, info_rand = env.reset(options={"random_start": True})
    assert obs_rand.shape == (8,)
    # random_start should set current_step to something between 0 and n_steps - 1
    assert 0 <= info_rand["step"] < env.n_steps
