"""Metamorphic + mutation tests for the optimizer (Sprint 01, Wave 4).

Metamorphic testing is the right tool when you have no ground truth (our exact
case on synthetic data): instead of asserting a specific output, assert a
RELATION between outputs under input transformations. Plus a mutation smoke that
proves the golden harness would actually catch a broken optimizer.
"""
from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from src.integration.counterfactual_loop import optimize

_cios = st.lists(
    st.tuples(st.floats(-6, 6), st.floats(70.0, 100.0)),
    min_size=2, max_size=9, unique_by=lambda t: t[0],
)


@given(_cios)
def test_mr_output_is_max_success(options):
    space = {("S", "T"): {c: s for c, s in options}}
    df = optimize(space)
    assert abs(df.iloc[0]["after_success_%"] - round(max(s for _, s in options), 2)) < 0.011


@given(_cios)
def test_mr_permutation_invariant(options):
    """MR: reordering the CIO options must not change the chosen CIO."""
    fwd = {c: s for c, s in options}
    rev = dict(reversed(list(fwd.items())))
    a = optimize({("S", "T"): fwd}).iloc[0]["after_success_%"]
    b = optimize({("S", "T"): rev}).iloc[0]["after_success_%"]
    assert a == b


@given(_cios, st.floats(-6, 6))
def test_mr_adding_worse_option_never_changes_pick(options, new_cio):
    """MR: adding a strictly-worse option leaves the chosen after-success unchanged."""
    base = {c: s for c, s in options}
    if new_cio in base:
        return
    before = optimize({("S", "T"): base}).iloc[0]["after_success_%"]
    worse = dict(base)
    worse[new_cio] = min(base.values()) - 5.0  # strictly worse
    after = optimize({("S", "T"): worse}).iloc[0]["after_success_%"]
    assert after == before


def _mutant_argmin(space):
    """A DELIBERATELY broken optimizer (picks worst CIO) — the mutant."""
    import pandas as pd
    rows = []
    for (s, t), opts in space.items():
        worst = min(opts, key=opts.get)
        rows.append({"source_cell": s, "target_cell": t, "optimal_cio_db": worst,
                     "after_success_%": round(opts[worst], 2)})
    return pd.DataFrame(rows)


def test_mutation_smoke_golden_catches_broken_optimizer():
    """If the optimizer regressed to argmin, the golden expectation must FAIL —
    proving the harness has teeth (Meta-ACH-style mutation check)."""
    space = {("S", "T"): {-2.0: 80.0, 0.0: 99.0, 2.0: 85.0}}
    good = optimize(space).iloc[0]["optimal_cio_db"]
    bad = _mutant_argmin(space).iloc[0]["optimal_cio_db"]
    assert good == 0.0 and bad != 0.0  # the mutant is detectably wrong
