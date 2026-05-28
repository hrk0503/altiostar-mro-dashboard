"""Lens Agent — Output + Visualization.

Streamlit dashboards, PPTX management decks, DOCX POC reports.
Outputs: Streamlit app, POC report (DOCX), management deck (PPTX).
"""

from pathlib import Path

from pydantic import BaseModel


class KPISnapshot(BaseModel):
    ho_success_rate: float
    ping_pong_rate: float
    ho_failure_rate: float
    mean_reward: float
    scenario: str


class LensAgent:
    """Generates visualization and reporting artifacts."""

    def generate_streamlit_app(self, results_dir: Path, output_path: Path) -> Path:
        raise NotImplementedError

    def generate_pptx(self, kpis: list[KPISnapshot], output_path: Path) -> Path:
        """5-slide management deck for Soumyadeep's boss."""
        raise NotImplementedError

    def generate_report(self, kpis: list[KPISnapshot], output_path: Path) -> Path:
        raise NotImplementedError
