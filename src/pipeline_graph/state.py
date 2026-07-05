"""Typed state carried through the MRO pipeline graph.

The state is a plain ``TypedDict`` (JSON-friendly). Each node reads the keys it
needs and writes the keys it produces; nothing is hidden in closures, so the
state is fully inspectable at every step (see ``run_graph.py``).
"""
from __future__ import annotations

from typing import Any, TypedDict


class MROState(TypedDict, total=False):
    """State passed between pipeline nodes.

    Keys are populated progressively as the graph runs:

    ingest      → data_path, csv_name, n_rows, n_cols, schema_matched_model
    validate    → validation_passed, validation_report
    optimize    → n_relations, optimal_cios, improvements, spectrum_review
    evaluate    → eval_metrics
    ship_gate   → gate_passed, gate_reasons
    report /
    needs_review→ status, summary
    (any node)  → errors
    """

    # ── ingest ──
    data_path: str
    csv_name: str
    n_rows: int
    n_cols: int
    schema_matched_model: str | None

    # ── validate ──
    validation_passed: bool
    validation_report: dict[str, Any]

    # ── optimize_cio ──
    n_relations: int
    optimal_cios: list[float]
    improvements: list[dict[str, Any]]
    spectrum_review: dict[str, Any]

    # ── evaluate ──
    eval_metrics: dict[str, Any]

    # ── ship_gate ──
    gate_passed: bool
    gate_reasons: list[str]

    # ── terminal ──
    status: str
    summary: dict[str, Any]

    # ── diagnostics (any node may append) ──
    errors: list[str]
