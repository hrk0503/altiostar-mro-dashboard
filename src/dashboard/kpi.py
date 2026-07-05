"""Dashboard KPI helpers (Sprint 01, Epic 4.2).

Attempt-weighted cluster HOSR — the fix for Soumyadeep's objection that the
headline number was an unweighted mean of per-cell rates (which over-weights
tiny cells). The honest cluster figure weights each cell by its HO attempts.
"""
from __future__ import annotations

from collections.abc import Sequence


def attempt_weighted_hosr(rates: Sequence[float], attempts: Sequence[float]) -> float:
    """Σ(rate·attempts) / Σ(attempts). Falls back to a plain mean if no attempts."""
    rates = list(rates)
    attempts = list(attempts)
    total = sum(attempts)
    if total <= 0:
        return sum(rates) / len(rates) if rates else 0.0
    return sum(r * a for r, a in zip(rates, attempts)) / total
