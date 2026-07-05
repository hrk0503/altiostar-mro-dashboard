"""Tests for the 3GPP handover rules engine in src.agents.spectrum.

All expected values are hand-computed from the 3GPP inequalities so the test is
an independent check of the implementation, not a mirror of it.
"""
from __future__ import annotations

from src.agents.spectrum import (
    QOFFSET_RANGE_DB,
    CIOChangeVerdict,
    SpectrumAgent,
    a3_entering_condition,
    a3_leaving_condition,
    a3_time_to_trigger_met,
    a3_triggered,
    classify_ho_failure,
    is_ping_pong,
    validate_cio_change,
    validate_cio_value,
)

# ── A3 entering condition: Mn + Ofn + Ocn - Hys > Mp + Ofp + Ocp + Off ────────


def test_a3_entering_triggers_when_neighbor_stronger():
    # Mn=-90, Hys=1 → LHS=-91 ; Mp=-100, Off=2 → RHS=-98 ; -91 > -98 → True
    assert a3_entering_condition(-100.0, -90.0, a3_offset_db=2.0, hysteresis_db=1.0) is True


def test_a3_entering_no_trigger_when_serving_stronger():
    # Mn=-100, Hys=1 → LHS=-101 ; Mp=-90, Off=2 → RHS=-88 ; -101 > -88 → False
    assert a3_entering_condition(-90.0, -100.0, a3_offset_db=2.0, hysteresis_db=1.0) is False


def test_a3_entering_cio_flips_decision():
    # Without CIO: Mn=-98 > Mp=-95 → False.
    assert a3_entering_condition(-95.0, -98.0, a3_offset_db=0.0, hysteresis_db=0.0) is False
    # With neighbour CIO Ocn=+4: LHS=-94 > RHS=-95 → True.
    assert (
        a3_entering_condition(-95.0, -98.0, a3_offset_db=0.0, hysteresis_db=0.0, ocn_db=4.0)
        is True
    )


def test_a3_leaving_condition():
    # Mn=-100, Hys=1 → LHS=-99 ; Mp=-90, Off=2 → RHS=-88 ; -99 < -88 → True
    assert a3_leaving_condition(-90.0, -100.0, a3_offset_db=2.0, hysteresis_db=1.0) is True
    # Neighbour clearly stronger → leaving not satisfied.
    assert a3_leaving_condition(-100.0, -80.0, a3_offset_db=2.0, hysteresis_db=1.0) is False


# ── time-to-trigger ───────────────────────────────────────────────────────────


def test_ttt_met_helper():
    assert a3_time_to_trigger_met(200.0, 160.0) is True
    assert a3_time_to_trigger_met(100.0, 160.0) is False


def test_a3_triggered_over_sequence():
    # Entering holds continuously from t=100..300 (200 ms).
    seq = [
        {"t_ms": 0, "serving_rsrp_dbm": -90.0, "neighbor_rsrp_dbm": -100.0},
        {"t_ms": 100, "serving_rsrp_dbm": -100.0, "neighbor_rsrp_dbm": -90.0},
        {"t_ms": 200, "serving_rsrp_dbm": -100.0, "neighbor_rsrp_dbm": -90.0},
        {"t_ms": 300, "serving_rsrp_dbm": -100.0, "neighbor_rsrp_dbm": -90.0},
    ]
    assert a3_triggered(seq, a3_offset_db=2.0, hysteresis_db=1.0, ttt_ms=160.0) is True
    # Same sequence but a longer TTT than the hold window → no trigger.
    assert a3_triggered(seq, a3_offset_db=2.0, hysteresis_db=1.0, ttt_ms=320.0) is False


def test_a3_triggered_resets_on_break():
    # Condition holds, breaks at 200, resumes at 300 → hold window too short.
    seq = [
        {"t_ms": 100, "serving_rsrp_dbm": -100.0, "neighbor_rsrp_dbm": -90.0},
        {"t_ms": 200, "serving_rsrp_dbm": -90.0, "neighbor_rsrp_dbm": -100.0},
        {"t_ms": 300, "serving_rsrp_dbm": -100.0, "neighbor_rsrp_dbm": -90.0},
        {"t_ms": 400, "serving_rsrp_dbm": -100.0, "neighbor_rsrp_dbm": -90.0},
    ]
    assert a3_triggered(seq, a3_offset_db=2.0, hysteresis_db=1.0, ttt_ms=160.0) is False


# ── CIO range / granularity ───────────────────────────────────────────────────


def test_cio_value_valid():
    assert validate_cio_value(0.0) == []
    assert validate_cio_value(-24.0) == []
    assert validate_cio_value(24.0) == []
    assert validate_cio_value(3.5) == []  # on 0.5 grid, in range


def test_cio_value_out_of_range():
    assert validate_cio_value(-25.0)  # non-empty → violation
    assert validate_cio_value(30.0)


def test_cio_value_off_grid():
    v = validate_cio_value(0.25)
    assert any("granularity" in msg for msg in v)


def test_qoffset_enumeration_constant():
    # Standard set has 31 entries and is symmetric around 0.
    assert len(QOFFSET_RANGE_DB) == 31
    assert 0 in QOFFSET_RANGE_DB and 24 in QOFFSET_RANGE_DB and -24 in QOFFSET_RANGE_DB
    assert 7 not in QOFFSET_RANGE_DB  # 7 dB is not a valid Q-OffsetRange step


# ── MRO classification ────────────────────────────────────────────────────────


def test_classify_too_late():
    assert (
        classify_ho_failure(
            rlf_before_ho=True,
            time_in_target_ms=0.0,
            reestablish_cell="B",
            source_cell="A",
            target_cell="B",
        )
        == "too_late_ho"
    )


def test_classify_too_early():
    assert (
        classify_ho_failure(
            rlf_before_ho=False,
            time_in_target_ms=200.0,
            reestablish_cell="A",
            source_cell="A",
            target_cell="B",
            min_time_of_stay_ms=1000.0,
        )
        == "too_early_ho"
    )


def test_classify_wrong_cell():
    assert (
        classify_ho_failure(
            rlf_before_ho=False,
            time_in_target_ms=200.0,
            reestablish_cell="C",
            source_cell="A",
            target_cell="B",
            min_time_of_stay_ms=1000.0,
        )
        == "wrong_cell_ho"
    )


def test_classify_none_when_stayed_long_enough():
    assert (
        classify_ho_failure(
            rlf_before_ho=False,
            time_in_target_ms=2000.0,
            reestablish_cell="A",
            source_cell="A",
            target_cell="B",
            min_time_of_stay_ms=1000.0,
        )
        == "none"
    )


def test_ping_pong():
    assert is_ping_pong(1000.0, 1500.0, 1000.0) is True   # returned in 500 ms
    assert is_ping_pong(1000.0, 3000.0, 1000.0) is False  # stayed 2000 ms


# ── validate_cio_change verdict ───────────────────────────────────────────────


def test_cio_change_valid():
    verdict = validate_cio_change("A", "B", 0.0, 4.0)
    assert isinstance(verdict, CIOChangeVerdict)
    assert verdict.valid is True
    assert verdict.violations == []
    assert verdict.delta == 4.0
    assert verdict.warnings == []


def test_cio_change_out_of_range_is_violation():
    verdict = validate_cio_change("A", "B", 0.0, 25.0)
    assert verdict.valid is False
    assert verdict.violations


def test_cio_change_large_swing_is_warning_not_violation():
    verdict = validate_cio_change("A", "B", 0.0, 10.0)
    assert verdict.valid is True
    assert any("swing" in w for w in verdict.warnings)


def test_cio_change_nonstandard_step_warns():
    verdict = validate_cio_change("A", "B", 0.0, 3.5)
    assert verdict.valid is True
    assert any("Q-OffsetRange" in w for w in verdict.warnings)


# ── backward-compatible agent façade ──────────────────────────────────────────


def test_agent_facade():
    agent = SpectrumAgent()
    assert agent.validate_cio_range(0.0) is True
    assert agent.validate_cio_range(-25.0) is False
    assert agent.validate_neighbor_list(["c"] * 10) is True
    assert agent.validate_neighbor_list(["c"] * 50) is False
    report = agent.validate_actions({"A->B": 4.0, "C->D": 99.0})
    assert report.valid is False
    assert any("C->D" in v for v in report.violations)
