#!/usr/bin/env python3
"""PPO Model exporter to ONNX format.

Extracts the policy network from a trained Stable-Baselines3 PPO model
and exports it to ONNX format for efficient deployment and inference.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from stable_baselines3 import PPO


class PPOPolicyOnnxWrapper(nn.Module):
    """Wrapper class to export SB3 PPO policies to ONNX."""

    def __init__(self, policy: nn.Module, action_space=None) -> None:
        super().__init__()
        self.policy = policy
        self.policy.eval()
        self.action_space = action_space

    def forward(self, obs: torch.Tensor) -> torch.Tensor:
        # Extract features from raw observation
        features = self.policy.extract_features(obs)
        # Latent representations (policy network features)
        latent_pi, _ = self.policy.mlp_extractor(features)
        # Bounded or unbounded raw actions from policy head
        mean_actions = self.policy.action_net(latent_pi)

        # Clip actions if action_space has bounds
        if self.action_space is not None and hasattr(self.action_space, "low") and hasattr(self.action_space, "high"):
            low = torch.from_numpy(self.action_space.low).to(mean_actions.device)
            high = torch.from_numpy(self.action_space.high).to(mean_actions.device)
            mean_actions = torch.clamp(mean_actions, low, high)

        return mean_actions


def export_model(model_path: str | Path, output_path: str | Path) -> None:
    """Load SB3 checkpoint, wrap the policy, and export to ONNX."""
    model_path = Path(model_path)
    output_path = Path(output_path)

    if not model_path.exists():
        print(f"Error: Model file '{model_path}' does not exist.", file=sys.stderr)
        sys.exit(1)

    print(f"Loading Stable-Baselines3 model from {model_path}...")
    model = PPO.load(model_path, device="cpu")
    policy = model.policy

    # Extract observation and action shapes
    obs_space = model.observation_space
    action_space = model.action_space
    print(f"Model loaded successfully:")
    print(f"  - Observation space: {obs_space}")
    print(f"  - Action space: {action_space}")

    # Generate dummy input matching the observation shape (with batch dimension 1)
    obs_shape = (1,) + obs_space.shape
    dummy_input = torch.randn(*obs_shape, dtype=torch.float32)

    # Instantiate wrapper
    wrapper = PPOPolicyOnnxWrapper(policy, action_space)

    # Perform evaluation comparison
    print("Verifying policy wrapper against SB3 prediction on dummy observation...")
    with torch.no_grad():
        dummy_np = dummy_input.squeeze(0).numpy()
        # Predict using SB3
        sb3_action, _ = model.predict(dummy_np, deterministic=True)
        # Predict using wrapper
        wrapper_action = wrapper(dummy_input).squeeze(0).numpy()

    # Compare actions
    match = np.allclose(sb3_action, wrapper_action, atol=1e-5)
    if match:
        print("  [SUCCESS] Wrapper actions match SB3 deterministic predictions exactly!")
    else:
        print("  [WARNING] Wrapper actions do not match SB3 predictions exactly.")
        print(f"  SB3 sample (first 5): {sb3_action[:5]}")
        print(f"  Wrapper sample (first 5): {wrapper_action[:5]}")

    print(f"Exporting to ONNX: {output_path} ...")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    torch.onnx.export(
        wrapper,
        dummy_input,
        str(output_path),
        export_params=True,
        opset_version=11,
        do_constant_folding=True,
        input_names=["input_obs"],
        output_names=["output_action"],
        dynamic_axes={
            "input_obs": {0: "batch_size"},
            "output_action": {0: "batch_size"},
        },
    )

    print(f"[SUCCESS] ONNX model successfully saved to: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export PPO model checkpoint to ONNX format.")
    parser.add_argument(
        "--model",
        type=str,
        default="checkpoints/ppo_v2_baseline.zip",
        help="Path to Stable-Baselines3 PPO zip checkpoint (default: checkpoints/ppo_v2_baseline.zip)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Path to save the exported ONNX model (default: same folder/name with .onnx extension)",
    )

    args = parser.parse_args()

    model_path = Path(args.model)
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = model_path.with_suffix(".onnx")

    export_model(model_path, output_path)


if __name__ == "__main__":
    main()
