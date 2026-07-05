"""Spectrum Agent — 3GPP handover rules engine (honest, deterministic).

This module encodes a set of KNOWN, published 3GPP handover constraints so that
CIO changes proposed by the optimizer can be checked against the standard before
anyone acts on them. It is a *rules engine*, not a model: every function here is
a direct, auditable implementation of a documented 3GPP inequality or parameter
range. Nothing is learned; nothing is inferred from data.

References
----------
- 3GPP TS 36.331 (RRC) §5.5.4.4  — Event A3 entering/leaving condition.
- 3GPP TS 36.331 (RRC) §6.3.5    — MeasConfig IEs: Hysteresis, a3-Offset,
                                    timeToTrigger, Q-OffsetRange (CIO).
- 3GPP TS 36.300 §22.4.2         — MRO connection-failure classification
                                    (Too-Late HO, Too-Early HO, HO to Wrong Cell).

HONESTY / SCOPE NOTE
--------------------
This encodes well-established 3GPP rules only. It is **not** a substitute for an
RF / RAN engineer signing off on novel configurations. Real networks add
vendor-specific behaviour, per-band offsets, load-based thresholds and
measurement error that are outside the standard inequalities implemented here.
Treat a "valid" verdict as "does not violate the encoded 3GPP rules", never as
"safe to deploy". Novel or borderline cases must go to a human RAN expert.

A specific, deliberately flagged mismatch: the RL environment in this repo steps
CIO in **integer** dB, whereas 3GPP `cellIndividualOffset` (Q-OffsetRange) is a
*discrete enumerated set* (see ``QOFFSET_RANGE_DB``), and the finer measurement
IEs (Hysteresis, a3-Offset) use a 0.5 dB grid. ``validate_cio_value`` checks the
0.5 dB grid the client asked for and separately warns when a value is not one of
the standard Q-OffsetRange steps.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

# ── 3GPP parameter ranges (TS 36.331) ────────────────────────────────────────

# cellIndividualOffset / Q-OffsetRange: the client (Soumyadeep) specified a
# working range of -24..+24 dB on a 0.5 dB grid. We honour that as the accepted
# range/granularity, and ALSO expose the true standard enumerated set below so a
# reviewer can see the difference.
CIO_MIN_DB: float = -24.0
CIO_MAX_DB: float = 24.0
CIO_GRANULARITY_DB: float = 0.5

# TS 36.331 Q-OffsetRange enumerated values (dB). Real cellIndividualOffset may
# only take these values — it is NOT a continuous 0.5 dB grid across the range.
QOFFSET_RANGE_DB: tuple[float, ...] = (
    -24, -22, -20, -18, -16, -14, -12, -10, -8, -6, -5, -4, -3, -2, -1,
    0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24,
)

# Hysteresis IE: 0..30 raw → 0..15 dB in 0.5 dB steps.
HYSTERESIS_MIN_DB: float = 0.0
HYSTERESIS_MAX_DB: float = 15.0

# a3-Offset IE: -30..30 raw → -15..15 dB in 0.5 dB steps.
A3_OFFSET_MIN_DB: float = -15.0
A3_OFFSET_MAX_DB: float = 15.0

# timeToTrigger enumerated values (ms), TS 36.331.
TTT_VALUES_MS: tuple[int, ...] = (
    0, 40, 64, 80, 100, 128, 160, 256, 320, 480, 512, 640, 1024, 1280, 2560, 5120,
)

# 3GPP neighbour-list practical limit (per frequency, informative).
MAX_NEIGHBORS: int = 32


def _is_on_grid(value: float, grid: float, *, tol: float = 1e-9) -> bool:
    """True if ``value`` is an integer multiple of ``grid`` (within tolerance)."""
    if grid <= 0:
        return True
    ratio = value / grid
    return abs(ratio - round(ratio)) <= tol


# ── CIO validation ───────────────────────────────────────────────────────────

def validate_cio_value(
    cio_db: float,
    *,
    granularity_db: float = CIO_GRANULARITY_DB,
) -> list[str]:
    """Validate a single CIO value against 3GPP range + granularity rules.

    Returns a list of violation strings (empty ⇒ valid). Being out of the
    enumerated Q-OffsetRange set is returned as a violation-free *warning* by
    :func:`cio_warnings`; this function only enforces the hard range/grid.
    """
    violations: list[str] = []
    if cio_db < CIO_MIN_DB or cio_db > CIO_MAX_DB:
        violations.append(
            f"CIO {cio_db} dB out of range [{CIO_MIN_DB}, {CIO_MAX_DB}] dB"
        )
    if not _is_on_grid(cio_db, granularity_db):
        violations.append(
            f"CIO {cio_db} dB not on {granularity_db} dB granularity grid"
        )
    return violations


def cio_warnings(cio_db: float) -> list[str]:
    """Non-fatal domain warnings for a CIO value (does not affect validity)."""
    warnings: list[str] = []
    if cio_db not in QOFFSET_RANGE_DB:
        warnings.append(
            f"CIO {cio_db} dB is not one of the standard 3GPP Q-OffsetRange "
            f"steps; a real eNodeB may snap it to the nearest allowed value"
        )
    return warnings


# ── Event A3 (TS 36.331 §5.5.4.4) ────────────────────────────────────────────

def a3_entering_condition(
    serving_rsrp_dbm: float,
    neighbor_rsrp_dbm: float,
    a3_offset_db: float,
    hysteresis_db: float,
    *,
    ofn_db: float = 0.0,
    ocn_db: float = 0.0,
    ofp_db: float = 0.0,
    ocp_db: float = 0.0,
) -> bool:
    """Return True if the A3 *entering* condition (inequality A3-1) is satisfied.

    3GPP TS 36.331 §5.5.4.4, condition A3-1::

        Mn + Ofn + Ocn - Hys > Mp + Ofp + Ocp + Off

    where
      - ``Mp`` = serving/PCell measurement (``serving_rsrp_dbm``),
      - ``Mn`` = neighbour measurement (``neighbor_rsrp_dbm``),
      - ``Ofp``/``Ofn`` = serving/neighbour frequency-specific offsets,
      - ``Ocp``/``Ocn`` = serving/neighbour cell-specific offsets (``Ocn`` is the
        neighbour CIO / cellIndividualOffset),
      - ``Hys`` = hysteresis, ``Off`` = a3-Offset.

    This is the instantaneous inequality only; timeToTrigger is applied
    separately (see :func:`a3_time_to_trigger_met` / :func:`a3_triggered`).
    """
    mn = neighbor_rsrp_dbm + ofn_db + ocn_db
    mp = serving_rsrp_dbm + ofp_db + ocp_db
    return (mn - hysteresis_db) > (mp + a3_offset_db)


def a3_leaving_condition(
    serving_rsrp_dbm: float,
    neighbor_rsrp_dbm: float,
    a3_offset_db: float,
    hysteresis_db: float,
    *,
    ofn_db: float = 0.0,
    ocn_db: float = 0.0,
    ofp_db: float = 0.0,
    ocp_db: float = 0.0,
) -> bool:
    """Return True if the A3 *leaving* condition (inequality A3-2) is satisfied.

    TS 36.331 §5.5.4.4, condition A3-2::

        Mn + Ofn + Ocn + Hys < Mp + Ofp + Ocp + Off
    """
    mn = neighbor_rsrp_dbm + ofn_db + ocn_db
    mp = serving_rsrp_dbm + ofp_db + ocp_db
    return (mn + hysteresis_db) < (mp + a3_offset_db)


def a3_time_to_trigger_met(condition_hold_ms: float, ttt_ms: float) -> bool:
    """True if the entering condition has held for at least timeToTrigger.

    3GPP fires the A3 report only after condition A3-1 has been continuously
    satisfied for ``timeToTrigger`` milliseconds.
    """
    return condition_hold_ms >= ttt_ms


def a3_triggered(
    measurements: list[dict[str, float]],
    a3_offset_db: float,
    hysteresis_db: float,
    ttt_ms: float,
    *,
    ofn_db: float = 0.0,
    ocn_db: float = 0.0,
    ofp_db: float = 0.0,
    ocp_db: float = 0.0,
) -> bool:
    """Evaluate A3 over a time-ordered measurement sequence (with TTT).

    ``measurements`` is a list of dicts, each with keys ``t_ms`` (timestamp),
    ``serving_rsrp_dbm`` and ``neighbor_rsrp_dbm``. Returns True if the A3
    entering condition holds continuously for at least ``ttt_ms``.
    """
    hold_start: float | None = None
    for m in sorted(measurements, key=lambda x: x["t_ms"]):
        entering = a3_entering_condition(
            m["serving_rsrp_dbm"],
            m["neighbor_rsrp_dbm"],
            a3_offset_db,
            hysteresis_db,
            ofn_db=ofn_db,
            ocn_db=ocn_db,
            ofp_db=ofp_db,
            ocp_db=ocp_db,
        )
        if entering:
            if hold_start is None:
                hold_start = m["t_ms"]
            elif a3_time_to_trigger_met(m["t_ms"] - hold_start, ttt_ms):
                return True
        else:
            hold_start = None
    return False


# ── MRO connection-failure classification (TS 36.300 §22.4.2) ─────────────────

def is_ping_pong(
    ho_out_time_ms: float,
    ho_back_time_ms: float,
    min_time_of_stay_ms: float,
) -> bool:
    """True if A→B then B→A happened inside the minimum-time-of-stay window.

    A ping-pong is an unnecessary back-and-forth handover: the UE is handed from
    the source to a neighbour and then returns to the source before staying for
    ``min_time_of_stay_ms``.
    """
    return 0 <= (ho_back_time_ms - ho_out_time_ms) < min_time_of_stay_ms


def classify_ho_failure(
    *,
    rlf_before_ho: bool,
    time_in_target_ms: float,
    reestablish_cell: str,
    source_cell: str,
    target_cell: str,
    min_time_of_stay_ms: float = 1000.0,
) -> str:
    """Classify a handover-related radio-link failure per 3GPP MRO definitions.

    Returns one of: ``"too_late_ho"``, ``"too_early_ho"``, ``"wrong_cell_ho"``,
    ``"none"``.

    3GPP TS 36.300 §22.4.2:
      - **Too-Late HO**: RLF occurs in the source *before* HO is triggered; UE
        re-establishes at a *different* (target) cell → HO should have happened
        earlier.
      - **Too-Early HO**: RLF shortly *after* a successful HO to the target; UE
        re-establishes back at the *source* cell → HO happened too soon.
      - **HO to Wrong Cell**: RLF shortly after a successful HO; UE
        re-establishes at a cell that is *neither* source nor target.
    """
    if rlf_before_ho:
        # Failure happened before/around trigger — the HO came too late.
        if reestablish_cell != source_cell:
            return "too_late_ho"
        return "none"

    # Failure happened after a completed HO into the target.
    if time_in_target_ms >= min_time_of_stay_ms:
        # Stayed long enough — not attributable to the HO decision.
        return "none"
    if reestablish_cell == source_cell:
        return "too_early_ho"
    if reestablish_cell != target_cell:
        return "wrong_cell_ho"
    return "none"


# ── Structured CIO-change verdict ────────────────────────────────────────────

class CIOChangeVerdict(BaseModel):
    """Structured result of validating a proposed CIO change on a relation."""

    source: str
    target: str
    cio_before: float
    cio_after: float
    delta: float
    valid: bool
    violations: list[str]
    warnings: list[str]


# Aggressive-swing threshold (dB). Not a 3GPP hard limit — a practical guard so a
# single step does not jump the offset wildly. Flagged as a warning, not a
# violation.
LARGE_SWING_DB: float = 6.0


def validate_cio_change(
    source: str,
    target: str,
    cio_before: float,
    cio_after: float,
    *,
    granularity_db: float = CIO_GRANULARITY_DB,
) -> CIOChangeVerdict:
    """Validate a proposed CIO change for a source→target relation.

    Hard rules (→ violations, ``valid=False``): target CIO must be within the
    3GPP range and on the granularity grid. Soft rules (→ warnings only):
    non-standard Q-OffsetRange step, or an aggressive single-step swing.
    """
    violations = validate_cio_value(cio_after, granularity_db=granularity_db)
    warnings = cio_warnings(cio_after)

    delta = cio_after - cio_before
    if abs(delta) > LARGE_SWING_DB:
        warnings.append(
            f"Large CIO swing {delta:+.1f} dB (>|{LARGE_SWING_DB}| dB) on "
            f"{source}->{target}; verify against ping-pong / coverage impact"
        )

    return CIOChangeVerdict(
        source=source,
        target=target,
        cio_before=cio_before,
        cio_after=cio_after,
        delta=delta,
        valid=len(violations) == 0,
        violations=violations,
        warnings=warnings,
    )


# ── Backward-compatible agent wrapper ────────────────────────────────────────

class DomainValidationReport(BaseModel):
    valid: bool
    violations: list[str]
    cio_range: tuple[float, float]
    max_neighbors: int
    frequency_bands: list[str]


@dataclass
class SpectrumAgent:
    """Thin façade over the module-level 3GPP rules engine.

    Retained for backward compatibility with existing callers/tests. All real
    logic lives in the module-level functions above; this class just forwards.
    """

    granularity_db: float = CIO_GRANULARITY_DB
    max_neighbors: int = MAX_NEIGHBORS
    frequency_bands: list[str] = field(default_factory=list)

    def validate_cio_range(self, cio: float) -> bool:
        """CIO must be within 3GPP spec: -24 to +24 dB (range check only)."""
        return CIO_MIN_DB <= cio <= CIO_MAX_DB

    def validate_neighbor_list(self, neighbors: list[str], max_neighbors: int | None = None) -> bool:
        """3GPP limits neighbour-list size."""
        limit = self.max_neighbors if max_neighbors is None else max_neighbors
        return len(neighbors) <= limit

    def validate_cio_change(
        self, source: str, target: str, cio_before: float, cio_after: float
    ) -> CIOChangeVerdict:
        """Forward to :func:`validate_cio_change` with the agent's granularity."""
        return validate_cio_change(
            source, target, cio_before, cio_after, granularity_db=self.granularity_db
        )

    def validate_actions(self, actions: dict[str, Any]) -> DomainValidationReport:
        """Validate a batch of proposed CIO values (relation → CIO dB).

        ``actions`` maps a relation label to a proposed CIO value in dB. Returns
        a :class:`DomainValidationReport` aggregating all hard violations.
        """
        violations: list[str] = []
        for relation, cio in actions.items():
            for v in validate_cio_value(float(cio), granularity_db=self.granularity_db):
                violations.append(f"{relation}: {v}")
        return DomainValidationReport(
            valid=len(violations) == 0,
            violations=violations,
            cio_range=(CIO_MIN_DB, CIO_MAX_DB),
            max_neighbors=self.max_neighbors,
            frequency_bands=list(self.frequency_bands),
        )
