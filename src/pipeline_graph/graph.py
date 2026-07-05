"""Assemble the MRO pipeline as a LangGraph ``StateGraph``.

Topology::

    ingest → validate ─(pass)→ optimize_cio → evaluate → ship_gate ─(pass)→ report → END
                    └─(fail)→ END                                   └─(fail)→ needs_review → END

``build_graph()`` returns a real, compilable LangGraph ``StateGraph``. LangGraph
is an optional dependency (see ``requirements.in`` / ``requirements-dashboard.in``);
if it is not installed, ``build_graph()`` raises a clear error and callers can
fall back to ``run_sequential()`` — a small plain-Python executor that runs the
exact same nodes in the exact same order (it is NOT LangGraph, just a reference
driver so the pipeline and its tests work without the dependency installed).
"""
from __future__ import annotations

from typing import Any

from src.pipeline_graph import nodes
from src.pipeline_graph.state import MROState

try:  # LangGraph is optional.
    from langgraph.graph import END, StateGraph

    LANGGRAPH_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only when dep is absent
    END = "__end__"
    StateGraph = None  # type: ignore[assignment,misc]
    LANGGRAPH_AVAILABLE = False


def build_graph() -> Any:
    """Build and return the (uncompiled) LangGraph ``StateGraph``.

    Raises
    ------
    RuntimeError
        If ``langgraph`` is not installed. Install it (``pip install langgraph``)
        or use :func:`run_sequential` for a dependency-free run.
    """
    if not LANGGRAPH_AVAILABLE:
        raise RuntimeError(
            "langgraph is not installed. Add it (see requirements.in) and "
            "`pip install langgraph`, or call run_sequential() instead."
        )

    graph = StateGraph(MROState)

    graph.add_node("ingest", nodes.node_ingest)
    graph.add_node("validate", nodes.node_validate)
    graph.add_node("optimize_cio", nodes.node_optimize_cio)
    graph.add_node("evaluate", nodes.node_evaluate)
    graph.add_node("ship_gate", nodes.node_ship_gate)
    graph.add_node("report", nodes.node_report)
    graph.add_node("needs_review", nodes.node_needs_review)

    graph.set_entry_point("ingest")
    graph.add_edge("ingest", "validate")
    graph.add_conditional_edges(
        "validate",
        nodes.route_after_validate,
        {"optimize_cio": "optimize_cio", "stop": END},
    )
    graph.add_edge("optimize_cio", "evaluate")
    graph.add_edge("evaluate", "ship_gate")
    graph.add_conditional_edges(
        "ship_gate",
        nodes.route_after_ship_gate,
        {"report": "report", "needs_review": "needs_review"},
    )
    graph.add_edge("report", END)
    graph.add_edge("needs_review", END)
    return graph


def run_sequential(initial_state: MROState | None = None) -> MROState:
    """Dependency-free reference executor (NOT LangGraph).

    Runs the identical nodes in the identical order, honouring the same two
    conditional branches. Used by ``run_graph.py`` when langgraph is not
    installed, and by tests to verify wiring deterministically. When langgraph
    IS installed, prefer ``build_graph().compile().invoke(state)``.
    """
    state: MROState = dict(initial_state or {})  # type: ignore[assignment]

    state = nodes.node_ingest(state)
    state = nodes.node_validate(state)
    if nodes.route_after_validate(state) == "stop":
        state["status"] = "validation_failed"
        state["summary"] = {
            "status": "validation_failed",
            "csv_name": state.get("csv_name"),
            "validation_report": state.get("validation_report"),
            "errors": state.get("errors", []),
        }
        return state

    state = nodes.node_optimize_cio(state)
    state = nodes.node_evaluate(state)
    state = nodes.node_ship_gate(state)

    if nodes.route_after_ship_gate(state) == "report":
        return nodes.node_report(state)
    return nodes.node_needs_review(state)
