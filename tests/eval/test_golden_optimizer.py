"""Golden eval harness — the optimizer's known-answer regression guard.

>=20 cases with a known best CIO. ANY change to the optimizer must keep these
green. This is the safety net the Claude-founder lens demanded: build the eval
before you touch the feature.
"""
from __future__ import annotations

import pytest

from src.integration.counterfactual_loop import optimize

# (space, expected_best_cio) — hand-authored known answers.
GOLDEN = [
    ({-2.0: 80.0, 0.0: 99.0, 2.0: 85.0}, 0.0),
    ({-6.0: 70.0, -2.0: 95.0, 0.0: 90.0}, -2.0),
    ({0.0: 88.0, 1.0: 88.5, 2.0: 99.9}, 2.0),
    ({-1.0: 99.1, 0.0: 99.0, 1.0: 98.9}, -1.0),
    ({-4.0: 72.0, -1.0: 84.0, 4.0: 91.0}, 4.0),
    ({-6.0: 99.9, 6.0: 70.0}, -6.0),
    ({0.0: 50.0, 2.0: 51.0, 4.0: 52.0, 6.0: 99.0}, 6.0),
    ({-2.0: 91.0, -1.0: 92.0, 0.0: 93.0, 1.0: 92.5}, 0.0),
    ({-6.0: 60.0, -4.0: 65.0, -2.0: 70.0, 0.0: 99.5}, 0.0),
    ({1.0: 97.0, 2.0: 97.0001}, 2.0),
    ({-3.0: 88.0, -2.0: 88.0, -1.0: 99.0}, -1.0),
    ({0.0: 79.25, 2.0: 99.99}, 2.0),
    ({-1.0: 95.5, 0.0: 95.4, 1.0: 95.6}, 1.0),
    ({-6.0: 71.0, -4.0: 99.0, -2.0: 98.0}, -4.0),
    ({4.0: 90.0, 6.0: 90.5}, 6.0),
    ({-2.0: 100.0, 0.0: 99.9}, -2.0),
    ({0.0: 84.32, 1.0: 94.22}, 1.0),
    ({-4.0: 77.0, 0.0: 77.0, 4.0: 78.0}, 4.0),
    ({-1.0: 93.84, 0.0: 83.81}, -1.0),
    ({-6.0: 70.0, -2.0: 70.0, 2.0: 70.0, 6.0: 70.1}, 6.0),
    ({0.0: 99.0, 2.0: 99.0, 4.0: 88.0}, 0.0),  # ties -> first (max stable)
]


@pytest.mark.parametrize("space,expected", GOLDEN)
def test_golden_best_cio(space, expected):
    df = optimize({("S", "T"): space})
    assert df.iloc[0]["optimal_cio_db"] == expected


def test_golden_count():
    assert len(GOLDEN) >= 20  # the harness must stay substantial
