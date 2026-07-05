# Onboarding — WINNIIO 5G MRO Platform

Welcome. This document gets any engineer productive on this project regardless of
who worked on it before. It is deliberately vendor- and person-neutral: it
describes the system, an honest verdict on its current state, and exactly what to
do in your first hours, days, and weeks. Read `docs/METHODOLOGY.md` alongside it —
that file governs what every number in this repo actually means.

---

## 1. What this project is

A reusable **Mobility Resource Optimization (MRO)** pipeline for 5G RAN. It ingests
relation-level performance-management (PM) data, finds the Cell Individual Offset
(CIO) changes per source→target cell relation that reduce handover failures, and
presents the result — failing relations, before/after handover success, and the
specific CIO moves — in a dashboard.

**The customer** is a telecom operator/vendor. The pitch is a two-layer platform:

- **Intelligence layer (this repo):** ingest any operator's PM data → optimize CIO →
  explainable before/after → drop-in for any cluster.
- **Reality layer (partner, e.g. Blaretech):** RF propagation / ray-tracing that
  explains *why* a relation fails and generates mobility scenarios. Integrated
  two-way, the two layers form one digital-twin platform.

## 2. Architecture at a glance

```
Operator CSV (relation-level PM, 15-min ROP)
   → src/pipeline/       schema map, validate, Pydantic models   (SOLID, tested)
   → src/env/mro_env.py  Gymnasium environment                   (works; see caveats)
   → scripts/optimize_cio.py  data-driven CIO optimization       (the real engine)
   → results/            JSON metrics + results/cio_exports/*.csv (see METHODOLOGY)
   → src/dashboard/app.py  Streamlit dashboard (the demo)        (the product surface)
```

The `src/agents/` folder holds seven **pipeline-stage classes** — Atlas (gate
orchestration), Pipeline (data), Spectrum (3GPP/RF validation), Forge (training),
Sentinel (QA), Deploy (Docker/Helm/ONNX), Lens (reporting). Today they are thin
stubs (20–130 lines), not autonomous agents. They are the *intended stage
architecture* for §6, not working automation yet.

## 3. Honest verdict on current state

A CRUCIBLE audit (2026-07-05) scored the repo **2.8/10** against a production floor.
The plumbing is good; the scientific story was overstated. In plain terms:

**What is genuinely good**
- Relation-level PM data and the relation drill-down are real and correct.
- The pipeline layer (loader/validator/schema-mapper/models) is properly tested.
- Data-driven CIO optimization is a legitimate, sellable technique.
- Seasonal synthetic data generation is grounded and documented.

**What was wrong (now flagged or fixed)**
- The "PPO reinforcement learning" claim was false: the answer was injected into
  frozen weights (`learning_rate=0.0`). Now clearly labelled in code and
  `docs/METHODOLOGY.md`. Report it as "data-driven CIO optimization", never "RL".
- Two fabrication scripts were removed (metadata patcher, synthetic learning curve).
- The "79→99.99%" delta is partly an accounting artifact; honest delta ≈ 98→99.99
  on synthetic. Real proof requires real cluster data.
- Deploy previously ran through a personal repo (fixed — see `docs/MIGRATION.md`).
- The 2,600-line dashboard, backend, and frontend have ~0% test coverage.

**Golden rule:** every number you show anyone must trace to a real artifact under
`docs/METHODOLOGY.md`. When unsure, say "synthetic — pending real-data validation."

## 4. First hours (get it running, understand it)

1. Clone; Python 3.11. `pip install -r requirements.txt` and
   `pip install -r requirements-dashboard.txt` for dev.
2. Run the dashboard: `streamlit run src/dashboard/app.py`
   (set `DASHBOARD_PASSWORD` locally via `.streamlit/secrets.toml` — see
   `secrets.toml.example`).
3. Click every page. Note which numbers are real vs illustrative (§3, METHODOLOGY).
4. Run the tests: `python -m pytest tests/ -q`. Read `tests/conftest.py` and one
   test per module to learn the data contracts.
5. Read `docs/METHODOLOGY.md`, `docs/MIGRATION.md`, and `run_experiment.py`
   top-to-bottom (especially the relation-mode disclosure block).

## 5. First days (make it trustworthy)

Do these before adding features — they close the trust gaps a technical customer
will probe:

- **Attempt-weight the headline KPI.** The Dashboard "Cluster Avg" is an unweighted
  per-cell mean; make it `sum(successes)/sum(attempts)` like the drill-down already
  does (`src/dashboard/app.py`).
- **Sector rendering.** Site DB already has azimuths; draw per-sector wedges on the
  Cell Map instead of stacked circles.
- **Regenerate or remove the broken multi-geo CIO exports** (baseline column = 0).
- **Add a persistent "SYNTHETIC DATA" badge** and relabel operator/vendor names as
  profiles, so synthetic data is never mistaken for real operator data.
- **Provenance label** on the CIO Explainability tab: state the method is exhaustive
  CIO search, not a trained policy.
- **First tests on the product surface:** Streamlit `AppTest` smoke test per page.

## 6. First weeks (get to the next stage) — multi-agent build

Bring the `src/agents/` stages to life, each with a clear contract, tests, and a
human gate. Build in this order; each stage is a promotable unit of work:

| Stage (agent) | First real job | Gate (who signs off) |
|---|---|---|
| **Pipeline** | Real drop-in ingestion: synonym/alias column mapping so an operator's renamed CSV maps without code changes (`src/pipeline/schema_mapper.py` currently only *detects*). | Data lead: real CSV ingests clean |
| **Spectrum** | Enforce 3GPP reality: CIO 0.5 dB granularity, valid range, and A3/TTT/hysteresis event modelling in the env. | Telecom lead: constraints match spec |
| **Forge** | Restore *genuine* RL on real data: real learning rate, non-empty net, train/test split, held-out evaluation, per-iteration CIO logging. | ML lead: learning curve is real, eval is held-out |
| **Sentinel** | Property-based tests on env dynamics + reward bounds; reject any 0-baseline export in CI. | QA: invariants hold |
| **Lens** | Explainability from the trained policy's actual actions (not the greedy table); real per-iteration CIO trajectory. | Owner: numbers trace to artifacts |
| **Deploy** | ONNX export in CI from a versioned checkpoint; container to CU-CP K8s. | DevOps: reproducible artifact |
| **Atlas** | Wire the gates: a stage cannot advance until the prior gate's artifact exists and CI is green. | Owner |

**Cross-cutting (the partner integration):** define the two-way contract with the
RF/reality layer — WINNIIO exports failing relations + candidate CIO moves; the RF
tool returns per-relation propagation outcomes and mobility-scenario results; the
optimizer/validator consumes them. This is what turns "which relation fails" into
"which relation fails and *why*", and is the core of the combined-platform pitch.

## 7. Working agreement (non-negotiables)

- Branch off `staging`; PR into `staging`; never force-push shared branches.
- CI (`.github/workflows/ci.yml`) must be green: ruff + pytest. No red on `staging`.
- No fabricated data or metrics, ever. Illustrative values must be labelled.
- Checkpoints and large data go to an artifact store, never absolute laptop paths.
- Every externally quoted number traces to a real artifact (`docs/METHODOLOGY.md`).
- Rollback point: git tag `AFTER-INTERNSHIP-PHASE-1-20260705`.
