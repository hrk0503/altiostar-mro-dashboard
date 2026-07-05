# `pipeline_graph` — LangGraph agentic MRO pipeline

A real [LangGraph](https://langchain-ai.github.io/langgraph/) `StateGraph` that
orchestrates the **existing** MRO pipeline stages into one runnable graph. Every
node is a thin wrapper that imports and calls a function that already lives in
this repo — no logic is re-implemented here, and nothing is faked.

## Honesty first

This folder was written under `docs/METHODOLOGY.md`. The important label:

> The `optimize_cio` node performs **data-driven CIO optimization (not RL)**. It
> calls `scripts.optimize_cio.find_optimal_cios`, an exhaustive per-relation
> search over the PM data. No policy network is trained, no gradients are taken,
> and `model.learn()` is never called.

"Agentic" here means *orchestration* (a typed state machine with conditional
routing), not autonomous learning agents. Each node does exactly what its
docstring says.

## Graph topology

```
ingest → validate ─(pass)→ optimize_cio → evaluate → ship_gate ─(pass)→ report → END
                └─(fail)→ END                                    └─(fail)→ needs_review → END
```

| Node           | Wraps (real function)                                   | What it does |
|----------------|---------------------------------------------------------|--------------|
| `ingest`       | `pandas` + `schema_mapper.infer_schema`                 | Reads CSV shape, detects schema. No transformation. |
| `validate`     | `pipeline.validator.validate_csv`                       | Null / range / type / duplicate checks. |
| `optimize_cio` | `scripts.optimize_cio.find_optimal_cios` + `agents.spectrum.validate_cio_change` | Exhaustive per-relation CIO search (NOT RL), then 3GPP sign-off on each change. |
| `evaluate`     | `scripts.optimize_cio.evaluate_with_optimal_cios`       | Deterministic roll-out of the target-CIO policy in `MROEnv`. |
| `ship_gate`    | `pipeline.ship_gate.check_gate_conditions`              | Strict gate: HOSR > 99%, ping-pong < 5%. |
| `report`       | —                                                       | Terminal: assembles success summary. |
| `needs_review` | —                                                       | Terminal: gate failed → surfaces reasons for human RAN review. |

### Conditional edges

- **after `validate`**: `route_after_validate` → `optimize_cio` if
  `validation_passed`, else stop (`END`) with a clear error in `state["errors"]`.
- **after `ship_gate`**: `route_after_ship_gate` → `report` if `gate_passed`,
  else `needs_review`.

## State

`state.MROState` is a `TypedDict` (JSON-friendly). It carries the dataframe path,
the schema-map result, the optimal CIOs + per-relation improvements, the eval
metrics, and the gate decision. See `state.py` for the full key list.

## Running it

```bash
# Runs on the synthetic Shibuya PM data by default, printing state at each node.
python -m src.pipeline_graph.run_graph --episodes 2
```

- If `langgraph` is installed, this compiles the `StateGraph` and **streams** it,
  printing the state emitted after every node.
- If `langgraph` is **not** installed, it runs `run_sequential()` — a small
  plain-Python reference executor that runs the same nodes in the same order
  (clearly labelled; it is *not* LangGraph). This keeps the pipeline and its
  tests usable before the dependency is installed.

`langgraph` is listed in `requirements.in` and `requirements-dashboard.in`.

> The `optimize_cio` node runs a genuine exhaustive search over the full
> synthetic dataset, so a real run takes a little while. That runtime is real —
> nothing is cached to look fast.

## Programmatic use

```python
from src.pipeline_graph import build_graph, run_sequential, LANGGRAPH_AVAILABLE

if LANGGRAPH_AVAILABLE:
    app = build_graph().compile()
    final = app.invoke({})            # {} → defaults to the synthetic Shibuya CSV
else:
    final = run_sequential({})        # same nodes, same order, no dependency
```

## Tests

`tests/test_pipeline_graph.py` covers node-level state transforms, both
conditional routes, and an end-to-end pass with the heavy calls
(`find_optimal_cios`, `evaluate_with_optimal_cios`, `MROEnv`) mocked by a small
fixture so the suite stays fast.
