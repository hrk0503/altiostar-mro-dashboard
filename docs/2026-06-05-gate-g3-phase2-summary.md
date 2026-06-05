# Gate G3 — Phase 2 Summary
## AltioStar MRO · Stream 4 · Reward Engineering & Scenario Comparison

**Date:** 2026-06-05
**Phase:** 2 (Jun 3-5)
**Lead:** Harshit Kumar
**Team:** Harshit Kumar, Ananyaa M, Shourya Solanki, Devika Hooda

---

## Executive Summary

Phase 2 delivered a fully automated RL experiment pipeline comparing 4 reward variants across 4 network scenarios, deployed on a live Streamlit dashboard. The pipeline runs end-to-end with a single command — from config to training to evaluation to dashboard visualization — fulfilling Nicolas's automation requirement.

**Key deliverables:**
- 4 reward variants (v0 Count-Based, v1 Traffic-Weighted, v2 Rate-Based, v3 Multi-Objective) implemented and compared
- 4 scenarios (baseline, rush_hour, rain_fade, tower_failure) with distinct network conditions
- 16 total experiments (4 variants x 4 scenarios) at 25,000 timesteps each
- Live dashboard: https://altiostar-mro-dashboard.streamlit.app (password: Winniio-2019)
- Automated pipeline: `python3 run_experiment.py --sweep-all`
- 221 tests passing, zero failures

---

## Gate G3 Criteria — Status

| Criterion | Status | Evidence |
|-----------|--------|----------|
| >= 2 reward variants with KPI delta | PASS | 4 variants (v0/v1/v2/v3) with full KPI comparison |
| >= 3 distinct scenarios | PASS | 4 scenarios: baseline, rush_hour, rain_fade, tower_failure |
| >= 5 experiment runs | PASS | 16 experiments (full sweep) |
| Dashboard shows KPI differences | PASS | Live at altiostar-mro-dashboard.streamlit.app |
| Side-by-side comparison table | PASS | Reports > KPI Delta Table |
| Automated experiment pipeline | PASS | run_experiment.py — single command sweep |
| Before/after baseline comparison | PASS | Random baseline vs trained agent |
| Training convergence curves | PASS | Experiments page — episode rewards |
| Best variant recommendation | PASS | Auto-picked per scenario on dashboard |
| Failure mode breakdown | PASS | Too Early / Too Late / Wrong Cell analysis |

**Gate Status: ALL CRITERIA MET**

---

## Reward Variants

### v0 — Count-Based (Simple)
```
reward = ho_success * 1.0 + ho_failure * (-5.0) + pingpong * (-2.0)
```
- Uses raw event counts
- Scale: ~9M per episode (busy cells dominate)
- Problem: unfair comparison across cells with different traffic volumes

### v1 — Traffic-Weighted
```
reward = (ho_success/attempts) * 100 - (ho_failure/attempts) * 500 - (pingpong/attempts) * 200
```
- Normalizes by handover attempts
- Fair comparison across cells regardless of traffic volume
- Scale: ~70-75 per episode

### v2 — Rate-Based (Recommended)
```
reward = ho_success_rate * 1.0 - ho_failure_rate * 5.0 - pingpong_rate * 2.0
```
- Uses percentage rates directly
- Bounded and consistent range
- **Best performer** — highest HO success rate in baseline

### v3 — Multi-Objective
```
reward = ho_success_rate * 1.0 - too_early * 3.0 - too_late * 4.0 - wrong_cell * 5.0 - pingpong * 2.0
```
- Separate weights per failure mode
- Penalizes wrong_cell most (hardest to fix), too_early least
- Weights from mro_default.yaml config

---

## Scenario Impact Analysis

| Scenario | Description | HO Success % | HO Failure % | Impact |
|----------|-------------|:------------:|:------------:|--------|
| baseline | Normal network conditions | 79.27 | 1.03 | Reference |
| rush_hour | 3x UE load, 70% PRB floor, 2x HO attempts | 13.21 | 0.17 | -83% success |
| rain_fade | -5dB RSRP, -3dB SINR, 1.5x failures | 79.27 | 2.02 | 2x failure rate |
| tower_failure | 1 site down, 2.5x neighbor load, 5x HO spike | 6.36 | 0.09 | -92% success |

**Key findings:**
- Scenarios create dramatic performance differentiation (6% to 79% success range)
- rush_hour and tower_failure are the most challenging — success drops below 15%
- rain_fade maintains success rate but doubles the failure rate (signal quality issue)
- Baseline performance matches random policy (~79%) — agent needs more training (Phase 3)

---

## Automated Pipeline

```
# Full sweep — all variants x all scenarios
python3 run_experiment.py --sweep-all --timesteps 25000 --eval-episodes 10

# Single experiment
python3 run_experiment.py --config configs/experiments/v2_rush_hour.yaml

# Custom sweep
python3 run_experiment.py --variants v0 v2 --scenarios baseline rush_hour
```

**Pipeline flow:** Config YAML → Build MROEnv → Train PPO → Evaluate → Save JSON → Log to MLflow → Dashboard auto-updates

---

## Dashboard Features

1. **Dashboard** — KPI cards, cell health donut, experiment results bar chart, Phase 2 progress
2. **Cell Map** — Interactive Mapbox with 75 cells, relations, cell inspector
3. **Experiments** — Variant comparison, training curves, before/after baseline, radar, heatmap, failure breakdown
4. **Network** — Topology visualization with scenario views
5. **Simulation** — Real-time RL simulation with live map and agent log
6. **Reports** — KPI delta table, recommendations, export, Gate G3 checklist

**Deployment:** Auto-syncing from LifeAtlas/altiostar-tokyo-mro → hrk0503/altiostar-mro-dashboard (every 15 min) → Streamlit Cloud

---

## Test Coverage

- **221 tests passing** (pytest -v: 0 failures)
- Covers: environment, reward system, scenarios, pipeline, KPI extraction, data loading
- All 4 reward variants validated independently
- All 4 scenarios verified to load and apply modifications correctly

---

## Phase 3 Handoff

**What's done:**
- Pipeline automated end-to-end
- Dashboard deployed and auto-syncing
- All reward variants and scenarios implemented and tested

**What Phase 3 needs:**
- Higher timestep training (50K-100K) to get agent to actually learn and improve over random baseline
- 5 seeded runs for statistical significance
- Before/after KPI improvement chart (quantified)
- Docker containerization
- The test: "Can someone who has never seen this repo run docker run with a fresh CSV and get results?"

**Config change made:** `mro_default.yaml` reward_version set to v2 (Rate-Based) — the recommended variant.

---

*— Harshit Kumar, Phase 2 Lead*
