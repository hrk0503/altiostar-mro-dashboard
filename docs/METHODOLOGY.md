# Methodology & Honest Artifact Status

This file exists so nobody — internal or client — is ever misled about what the
numbers in this repo mean. It is the single source of truth for how results are
produced. Read it before quoting any figure.

## What the platform actually does (today)

**Data-driven CIO optimization.** For each source→target cell relation, the
optimizer (`scripts/optimize_cio.py :: find_optimal_cios`) searches the
relation-level PM data for the Cell Individual Offset (CIO) that minimizes
handover failures, and reports the before/after handover success per relation.

This is a legitimate, defensible technique. On **real** operator data (where no
optimum is pre-planted) it produces genuine, actionable CIO recommendations.

## What it is NOT (yet)

**It is not learned reinforcement learning.** The relation-mode path in
`run_experiment.py` sets `learning_rate=0.0` and injects the optimizer's answer
directly into the policy weights. `model.learn()` is a no-op there. Do not
describe this as "PPO" or "the agent learned" — describe it as "data-driven CIO
optimization". Genuine RL (real learning rate, non-empty network, held-out
evaluation, multi-objective reward) is Phase 2, once real cluster data lands.

## Known artifact caveats (synthetic data)

| Artifact | Caveat |
|---|---|
| `results/random_baseline.json` (79.25%) | Computed under a success definition where ~20% of handovers are unaccounted. The honest "before" on the augmented dataset is ~98%, not 79%. |
| `experiment_*_baseline.json` (99.99%) | Environment-level metric on a synthetic env whose generator plants a zero-failure optimum. It is the *designed ceiling*, not proof of real-world gain. |
| `results/multi_geo_training.json` | 16-geography runs are 95.0–97.7% HOSR — NOT "99.99% across 16 geographies". |
| `results/cio_exports/*_cio_changes.csv` (non-shibuya) | Baseline column unpopulated (export bug) — do not ship until regenerated. `shibuya_cio_changes.csv` is valid. |
| Dashboard "Simulation" scenario KPIs | Illustrative (computed in the UI layer), not simulation output. Labelled as such or not shown to clients. |

## The rule

Every externally quoted number must trace to a real artifact under this
methodology. Synthetic results demonstrate the *pipeline*; the *proof* is real
cluster data validated against ground truth. Removed on 2026-07-05:
`scripts/patch_baseline_failures.py` (rewrote training metadata) and the
`train_ppo.py` synthetic-curve block (fabricated convergence plots).
