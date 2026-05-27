"""Tests for MRO Gymnasium environment."""


from src.env.mro_env import MROEnv


class TestMROEnv:
    def test_env_creates(self):
        env = MROEnv()
        assert env.observation_space is not None
        assert env.action_space is not None

    def test_reset_returns_valid_obs(self):
        env = MROEnv()
        obs, info = env.reset(seed=42)
        assert obs.shape == (75, 10)
        assert isinstance(info, dict)

    def test_step_returns_valid_tuple(self):
        env = MROEnv()
        env.reset(seed=42)
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        assert obs.shape == (75, 10)
        assert isinstance(reward, float)
        assert isinstance(terminated, bool)
        assert isinstance(truncated, bool)

    def test_env_with_config(self, tmp_path):
        config = tmp_path / "test_config.yaml"
        config.write_text("n_cells: 10\nn_obs_features: 5\nn_actions: 3\nreward_version: v0\n")
        env = MROEnv(config_path=config)
        obs, _ = env.reset()
        assert obs.shape == (10, 5)
