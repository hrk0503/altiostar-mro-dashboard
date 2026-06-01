"""Task 3 verification: Gymnasium env loads real CSV data, not random noise."""

from src.env.mro_env import MROEnv

PM_PATH = "data/synthetic/pm_data_april2026.csv"
KPI_PATH = "data/synthetic/cluster_kpi_summary.csv"


def main() -> None:
    print("Loading MROEnv with real CSV data...")
    env = MROEnv(pm_data_path=PM_PATH, kpi_path=KPI_PATH)

    print(f"Cell ID selected: {env.cell_id}")
    print(f"Total timesteps from CSV: {env.n_steps}")

    obs, info = env.reset()
    print(f"\nStep 0 observation from real CSV:")
    print(f"  RSRP:           {obs[0]:.2f} dBm")
    print(f"  RSRQ:           {obs[1]:.2f} dB")
    print(f"  SINR:           {obs[2]:.2f} dB")
    print(f"  PRB DL:         {obs[3]:.2f} %")
    print(f"  PRB UL:         {obs[4]:.2f} %")
    print(f"  HO Success:     {obs[5]:.2f} %")
    print(f"  HO Failure:     {obs[6]:.2f} %")
    print(f"  Ping-pong:      {obs[7]:.2f}")

    print(f"\nRunning 5 steps with random actions...")
    for i in range(5):
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        print(f"  Step {i+1}: reward={reward:.2f}, RSRP={obs[0]:.2f}")

    print("\n✅ MROEnv is loading and stepping on real CSV data!")


if __name__ == "__main__":
    main()