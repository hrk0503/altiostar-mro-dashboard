"""LangGraph agentic MRO pipeline.

Orchestrates the existing MRO pipeline stages (ingest → validate → optimize_cio
→ evaluate → ship_gate → report) as a single runnable LangGraph ``StateGraph``.
Every node is a thin, honest wrapper around a real function already in this repo.
See ``README.md`` in this folder and ``run_graph.py`` for a runnable demo.
"""
from __future__ import annotations

from src.pipeline_graph.graph import (
    LANGGRAPH_AVAILABLE,
    build_graph,
    run_sequential,
)
from src.pipeline_graph.state import MROState

__all__ = [
    "LANGGRAPH_AVAILABLE",
    "MROState",
    "build_graph",
    "run_sequential",
]
