#!/usr/bin/env python3
"""Run the MRO pipeline graph on the synthetic Shibuya data, printing each step.

Usage::

    python -m src.pipeline_graph.run_graph [--episodes N] [--data PATH]

If ``langgraph`` is installed this streams the compiled ``StateGraph`` and prints
the state emitted after every node. If it is not installed, it runs the
dependency-free reference executor (same nodes, same order) and prints the same
progression, with a clear banner saying so.

Note: the ``optimize_cio`` node runs an exhaustive per-relation CIO search, which
is genuinely compute-heavy on the full synthetic dataset — expect it to take a
little while. Nothing here is faked or cached to look fast.
"""
from __future__ import annotations

import argparse
import json
from typing import Any

from src.pipeline_graph import nodes
from src.pipeline_graph.graph import LANGGRAPH_AVAILABLE, build_graph
from src.pipeline_graph.state import MROState

# Keys worth showing per node (keeps the console output readable).
_SHOW_KEYS = (
    "csv_name",
    "n_rows",
    "n_cols",
    "schema_matched_model",
    "validation_passed",
    "n_relations",
    "spectrum_review",
    "eval_metrics",
    "gate_passed",
    "gate_reasons",
    "status",
)


def _compact(state: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k in _SHOW_KEYS:
        if k in state:
            out[k] = state[k]
    return out


def _print_state(label: str, state: dict[str, Any]) -> None:
    print(f"\n{'-' * 70}\n[node: {label}]")
    print(json.dumps(_compact(state), indent=2, default=str))


def _run_streamed(initial: MROState, episodes: int) -> MROState:
    """Compile + stream the real LangGraph graph, printing each node's output."""
    print("LangGraph detected — streaming the compiled StateGraph.\n")
    app = build_graph().compile()
    final: MROState = dict(initial)  # type: ignore[assignment]
    for chunk in app.stream(initial):
        for node_name, update in chunk.items():
            if isinstance(update, dict):
                final.update(update)
            _print_state(node_name, final)
    return final


def _run_sequential_verbose(initial: MROState, episodes: int) -> MROState:
    """Reference executor with per-node prints (no langgraph)."""
    print("LangGraph NOT installed — running the reference sequential executor.")
    print("(Install langgraph to run the real StateGraph; same nodes, same order.)\n")
    state: MROState = dict(initial)  # type: ignore[assignment]

    state = nodes.node_ingest(state)
    _print_state("ingest", state)

    state = nodes.node_validate(state)
    _print_state("validate", state)
    if nodes.route_after_validate(state) == "stop":
        state["status"] = "validation_failed"
        _print_state("STOP (validation failed)", state)
        return state

    state = nodes.node_optimize_cio(state)
    _print_state("optimize_cio", state)

    state = nodes.node_evaluate(state, n_episodes=episodes)
    _print_state("evaluate", state)

    state = nodes.node_ship_gate(state)
    _print_state("ship_gate", state)

    if nodes.route_after_ship_gate(state) == "report":
        state = nodes.node_report(state)
        _print_state("report", state)
    else:
        state = nodes.node_needs_review(state)
        _print_state("needs_review", state)
    return state


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--episodes",
        type=int,
        default=2,
        help="evaluation episodes (sequential mode only; streamed graph uses the node default)",
    )
    parser.add_argument("--data", type=str, default=None, help="override input CSV path")
    args = parser.parse_args()

    initial: MROState = {}
    if args.data:
        initial["data_path"] = args.data

    print("=" * 70)
    print("MRO agentic pipeline: ingest -> validate -> optimize_cio -> evaluate")
    print("                      -> ship_gate -> report / needs_review")
    print("=" * 70)

    if LANGGRAPH_AVAILABLE:
        final = _run_streamed(initial, args.episodes)
    else:
        final = _run_sequential_verbose(initial, args.episodes)

    print(f"\n{'=' * 70}\nFINAL STATUS: {final.get('status', 'unknown')}\n{'=' * 70}")


if __name__ == "__main__":
    main()
