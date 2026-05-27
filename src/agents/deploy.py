"""Deploy Agent — DevOps.

Docker, Helm charts, Robin orchestrator targeting for CU-CP K8s pods.
Outputs: Dockerfile, Helm chart, deployment manifests, CI/CD config.
"""

from pathlib import Path


class DeployAgent:
    """Generates deployment artifacts for trained models."""

    def generate_dockerfile(self, model_path: Path, output_dir: Path) -> Path:
        raise NotImplementedError

    def generate_helm_chart(self, model_path: Path, output_dir: Path) -> Path:
        raise NotImplementedError

    def export_onnx(self, model_path: Path, output_path: Path) -> Path:
        """Export SB3 model to ONNX for CU-CP K8s deployment."""
        raise NotImplementedError
