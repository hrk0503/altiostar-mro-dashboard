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

    print(f"✅ Env ran OK | Cell: {info['cell_id']} | Steps: {info['step']}")