"""Synthetic RF provider -- wraps src.integration.synthetic_rf_return.

Deterministic stand-in for the real RF layer (Blaretech / Sionna). See
src/integration/synthetic_rf_return.py for the honesty caveats: nothing here
is calibrated to a real cluster, it is illustrative only.
"""
from __future__ import annotations

from pathlib import Path

from backend.app.rf.provider import RFProvider
from src.integration.synthetic_rf_return import generate


class SyntheticRFProvider(RFProvider):
    name = "synthetic"

    def simulate(self, request_dir: Path) -> Path:
        request_csv = request_dir / "01_counterfactual_request.csv"
        out_csv = request_dir / "RETURN_synthetic.csv"
        generate(request_csv, out_csv)
        return out_csv
