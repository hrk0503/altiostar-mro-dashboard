"""RF provider seam: a common interface for the counterfactual RF/propagation
sim step (see src/integration/counterfactual_loop.py and
src/integration/blaretech_export.py for the request/return contract).

Each provider consumes a request directory (built by
src.integration.blaretech_export.build_export) and returns the path to a
filled RETURN_SCHEMA.csv-shaped file.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class RFProvider(ABC):
    """A source of counterfactual handover outcomes for candidate CIOs."""

    name: str

    @abstractmethod
    def simulate(self, request_dir: Path) -> Path:
        """Consume request_dir/01_counterfactual_request.csv, return the path
        to a RETURN_SCHEMA-shaped CSV of simulated counterfactuals."""
        raise NotImplementedError
