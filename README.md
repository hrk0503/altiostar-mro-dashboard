# Altiostar MRO Training Pipeline

Reusable AI/ML pipeline for Mobility Robustness Optimization: CSV data in → trained RL model + management dashboard out.

**Stream 4** of [AMITY 2026](https://github.com/Life-Atlas/amity-2026) | **Plan:** [ALTIOSTAR-PLAN.md](https://github.com/Life-Atlas/amity-2026/blob/main/streams/ALTIOSTAR-PLAN.md)

### Consolidated Staging Branch
The consolidated integration branch containing the combined work of all team members is:
👉 **`staging`**

## Pre-requisites & Quick Start

### Pre-requisites
- **Python**: version 3.10 to 3.14.
- **Operating System**: macOS or Linux.
- **Virtual Environment**: Recommended to isolate library dependencies.

### Setup
```bash
git clone https://github.com/Life-Atlas/altiostar-tokyo-mro.git
cd altiostar-tokyo-mro
git checkout staging
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dashboard.txt
```

### Running the Project Commands

- **Run the Pytest Suite**:
  ```bash
  PYTHONPATH=. venv/bin/pytest tests/ -v
  ```
- **Launch the Streamlit Dashboard**:
  ```bash
  # On macOS, prefix with OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES to avoid thread forks crashing
  OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES venv/bin/streamlit run src/dashboard/app.py
  ```
- **Compile the Widescreen Presentation Deck**:
  ```bash
  venv/bin/python scripts/generate_pptx.py
  ```
- **Run the SLA Ship Gate Validator**:
  ```bash
  venv/bin/python src/pipeline/ship_gate.py --results-dir results/seeded_runs
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

## Troubleshooting (macOS)

If you run into a macOS system popup stating **"Python quit unexpectedly"** (SIGSEGV/EXC_BAD_ACCESS) when launching scripts or loading the Streamlit dashboard, this is due to macOS's safety checks for multi-threaded processes calling `fork()`.

To resolve this, set the following environment variable in your terminal before running the commands:
```bash
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
```
Or prefix the command directly:
```bash
OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES venv/bin/streamlit run src/dashboard/app.py
```

## Things Done

- **Robust Ingestion**: Built `schema_mapper.py` supporting dynamic set-based signatures to auto-detect operator CSV columns.
- **High-fidelity Simulation**: Designed a custom Gymnasium environment (`mro_env.py`) that transitions states using database lookups in microseconds rather than empirical curve physics.
- **Reward Calibration**: Engineered a `v2` Rate-Based Reward function with asymmetric boundary penalties for HOSR and Ping-Pongs.
- **Statistical Variant Sweeps**: Trained 4 reward variants over 100k timesteps across baseline, rain fade, rush hour, and tower failure scenarios.
- **Ship Gate Validator**: Built `ship_gate.py` to ensure every production model meets SLA targets (HOSR > 99%, Ping-Pong < 5%).
- **ONNX Deployment Exporter**: Developed `export_onnx.py` with output clamping to match deterministic Stable-Baselines3 actions.
- **Streamlit Dashboard**: Created a dark-themed operator control dashboard featuring geographic maps, cell inspectors, variant benchmarks, and a real-time simulator.
- **3D Spatial Digital Twin**: Built a CesiumJS digital twin simulator visualizing NVIDIA Sionna ray-tracing coverage and UE handover trajectories.

## Next Steps & Improvements

- **Live 5G Integration**: Interface the ONNX inference model with real vCU-CP/vDU nodes via the standard E2 interface.
- **Hardware-in-the-Loop Testing**: Validate policy execution speeds on ARM-based O-RAN edge processors.
- **Scale to Larger Datasets**: Extend the Schema Mapper and double-caching mechanism to handle multi-gigabyte operator datasets with millions of relations.
- **Enhanced Spatial Modeling**: Load higher resolution building models (e.g. from Project PLATEAU) into the 3D twin to improve millimeter-wave propagation accuracy.
