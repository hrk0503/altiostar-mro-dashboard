# The Counterfactual Problem — why the intelligence layer needs the reality layer

This is the single most important thing to understand about the platform. It
is honest, it is provable from the code, and it is the reason WINNIIO and the
RF/reality layer (Blaretech / Sionna) are one platform, not two products.

## ELI10 (professional)

Think of each cell-to-cell handover relation as a knob (the **CIO**, Cell
Individual Offset). The knob decides how eagerly a phone hands over from one
cell to its neighbor. Set it wrong and calls drop (too-early / too-late
handovers) or bounce back and forth (ping-pong).

The operator's data tells us, for each relation, how handovers went **at the
one knob setting they were actually using.** It does *not* tell us how they
would go at a *different* setting — because that setting was never tried.

So if we want to say "turn this knob from 0 to +2 and failures drop," we need
to know what happens at +2. Raw data can't answer that. Only one of two things
can:

1. **History** — the operator changed that knob in the past and logged it, or
2. **A simulator** — an RF/propagation model computes what *would* happen.

That simulator is the reality layer. It generates the **counterfactuals** —
the "what if the knob were here instead" answers. Once we have those, our
optimizer can compare settings and pick the best one. Without them, it has a
single data point per relation and literally nothing to optimize.

## Proof from our own code (not a claim — a measurement)

We re-ran the honest optimizer on the baseline synthetic dataset:

| | HO success | Relations improved |
|---|---|---|
| Committed claim (old) | 99.99% | 763 |
| **Honest re-run** | **79.27%** | **0** |
| Random baseline | 79.25% | — |

Why zero improvement? Because the baseline dataset has **exactly one CIO value
per relation** (verified: 0 of 763 relations have more than one). The search
has nothing to search over. The old 99.99% came only from an *augmented*
dataset that synthesised 9 CIO values per relation with a pre-planted optimum —
i.e. a simulator's job, done synthetically with the answer known in advance.

Real operator data will also have one CIO per relation. So the counterfactual
generator is not optional — it is the mathematical prerequisite for the
optimizer to be non-trivial.

## The handoff (stop / start)

```
WINNIIO (intelligence)          BLARETECH / Sionna (reality)      WINNIIO (intelligence)
──────────────────────          ────────────────────────────      ──────────────────────
ingest operator PM              receive request                   re-ingest counterfactuals
find failing relations   ─────► for each (relation, CIO):  ─────► run CIO search
attach geometry                   simulate HO outcome             recommend best CIO/relation
list candidate CIOs             return simulated PM               validate (3GPP) → ship
= export package                = RETURN_SCHEMA.csv               = optimized network
```

The export that implements the left box is `src/integration/blaretech_export.py`.
The return contract is `RETURN_SCHEMA.csv`. The re-ingest + search is the
existing `find_optimal_cios` / pipeline graph, now with a real search space.

## Why this is the pitch, not a weakness

It converts "we have an AI optimizer" (weak — it needs data it doesn't have)
into "we have the intelligence layer, and here is exactly the reality-layer
interface that makes it work" (strong, honest, and it explains precisely why
the partnership is a single platform). It is the most credible thing to say to
a telecom buyer: your PM data shows *where* handovers fail; the reality layer
shows *what fixes them*; together that's a closed optimization loop.
