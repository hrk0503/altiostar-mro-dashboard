# Altiostar MRO Training Pipeline

Reusable AI/ML pipeline for Mobility Robustness Optimization: CSV data in → trained RL model + management dashboard out.

**Stream 4** of [AMITY 2026](https://github.com/Life-Atlas/amity-2026) | **Plan:** [ALTIOSTAR-PLAN.md](https://github.com/Life-Atlas/amity-2026/blob/main/streams/ALTIOSTAR-PLAN.md)

## Quick Start

```bash
git clone https://github.com/Life-Atlas/altiostar-tokyo-mro.git
cd altiostar-tokyo-mro
pip install -e ".[dev]"
pre-commit install
pytest
```

## Architecture: 7 Autonomous Agents

```
Operator CSV (any format)
     │
     ├──→ Pipeline Agent (auto-detect schema → normalize → Parquet)
     │         │
     ├──→ Spectrum Agent (3GPP domain validation, RF constraints)
     │         │
     ├──→ Forge Agent (Gymnasium env from YAML → PPO training)
     │         │
     ├──→ Sentinel Agent (property-based tests, adversarial attacks)
     │         │
     ├──→ Deploy Agent (Docker, Helm, Robin orchestrator)
     │         │
     └──→ Lens Agent (Streamlit dashboard, PPTX report)
              │
         Atlas Agent (orchestrates all, manages gates)
```

## Project Structure

```
src/
  agents/          7 agent modules (atlas, pipeline, spectrum, forge, deploy, lens, sentinel)
  env/             Gymnasium RL environment (YAML-configurable)
  pipeline/        Schema mapper, data quality, normalization
  models/          Pydantic data models
configs/           YAML environment configs (scenarios, reward variants)
data/synthetic/    4 synthetic CSVs (75-cell Shibuya cluster)
tests/             pytest + Hypothesis property-based tests
docs/logs/         Daily intern logs (one per person per day)
```

## Synthetic Data

| File | Rows | Description |
|------|------|-------------|
| `site_database.csv` | 75 | 25 sites × 3 sectors, Shibuya area |
| `neighbor_relations.csv` | 763 | 8-12 neighbors per cell, CIO values |
| `pm_data_april2026.csv` | 216,000 | 15-min ROPs, April 2026, 20 KPIs |
| `cluster_kpi_summary.csv` | 75 | Monthly aggregates, 6 problem cells |

## Phases

| Phase | Gate | Key Deliverable |
|-------|------|-----------------|
| 0 | Dev env + data loaded + RL env boots | Schema mapper, Gymnasium env, CI |
| 1 | PPO trains, beats random baseline | Training pipeline, KPI extraction, Streamlit |
| 2 | 2-3 reward variants compared | Reward engineering, scenario engine |
| 3 | Ship gate passes, demo runs clean | End-to-end, ONNX export, management deck |

## Team

| Name | Role |
|------|------|
| Ananyaa M | Phase 0 Lead |
| Shourya Solanki | Phase 1 Lead |
| Harshit Kumar | Phase 2 Lead |
| Devika Hooda | Phase 3 Lead |

**Supervisor:** Danial, Nicolas

## CI

Every push runs: `ruff check` → `mypy` → `pytest`. See `.github/workflows/ci.yml`.

## Legacy

The original Tokyo Cesium 3D demo is preserved on the [`legacy/tokyo-demo`](https://github.com/Life-Atlas/altiostar-tokyo-mro/tree/legacy/tokyo-demo) branch.
