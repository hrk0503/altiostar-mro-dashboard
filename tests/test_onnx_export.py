from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest
import torch
from stable_baselines3 import PPO

from src.pipeline.export_onnx import PPOPolicyOnnxWrapper, export_model


def test_ppo_policy_onnx_wrapper() -> None:
    """Verify that the wrapper correctly forwards dummy observations and matches model prediction."""
    model_path = Path("checkpoints/ppo_v2_baseline.zip")
    if not model_path.exists():
        pytest.skip("Trained model checkpoint checkpoints/ppo_v2_baseline.zip not found. Skipping test.")

    model = PPO.load(model_path, device="cpu")
    policy = model.policy
    wrapper = PPOPolicyOnnxWrapper(policy, model.action_space)

    # Test observation input shape matching (1, 763, 9)
    obs_space = model.observation_space
    dummy_input = torch.randn((1,) + obs_space.shape, dtype=torch.float32)

    # Predictions
    with torch.no_grad():
        dummy_np = dummy_input.squeeze(0).numpy()
        sb3_action, _ = model.predict(dummy_np, deterministic=True)
        wrapper_action = wrapper(dummy_input).squeeze(0).numpy()

    # The wrapper action must match SB3 prediction
    assert wrapper_action.shape == sb3_action.shape
    assert np.allclose(sb3_action, wrapper_action, atol=1e-5)


def test_export_model_to_file() -> None:
    """Verify that export_model function successfully writes the ONNX file."""
    model_path = Path("checkpoints/ppo_v2_baseline.zip")
    if not model_path.exists():
        pytest.skip("Trained model checkpoint checkpoints/ppo_v2_baseline.zip not found. Skipping test.")

    with tempfile.TemporaryDirectory() as tmpdir:
        temp_onnx_path = Path(tmpdir) / "test_ppo.onnx"
        
        # Run export, skip if dependencies like onnx or onnxscript are missing
        try:
            export_model(model_path, temp_onnx_path)
        except (ModuleNotFoundError, ImportError) as e:
            pytest.skip(f"ONNX export skipped: missing dependency {e}")
        
        # Verify file creation and size
        assert temp_onnx_path.exists()
        assert temp_onnx_path.stat().st_size > 0
