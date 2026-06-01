# Altiostar Team — Start Here (June 1, 2026)

**Read this FIRST. Ignore every other .md file until you've done these steps.**

---

## What this project is

You are building a **reusable MRO training pipeline** for 5G handover optimization.

Input: CSV files with handover data from any mobile operator.
Output: A trained AI model that improves handover success rate, with a before/after chart.

The pipeline must work on NEW data without changing any code. CSV in, results out.

---

## Your repo structure (what matters)

```
altiostar-tokyo-mro/
  data/synthetic/          ← 5 CSV files (your training data)
  src/
    pipeline/
      models.py            ← Pydantic data models (THESE define the internal schema)
      schema_mapper.py     ← Auto-detects CSV type and maps columns
      validator.py         ← Data quality checks
      loader.py            ← Loads CSV into models
    env/
      mro_env.py           ← Gymnasium RL environment (THE CORE)
    models/
      cell_data.py         ← DUPLICATE models file (see Task 1 below)
  tests/                   ← pytest test suite
  scripts/
    generate_relation_pm.py ← Generates the relation-level CSV
```

---

## The 5 CSV files you're working with

| File | Rows | What it is |
|------|------|-----------|
| `site_database.csv` | 75 | 25 cell towers, 3 sectors each. Location, antenna config. |
| `neighbor_relations.csv` | 763 | Which cells can hand off to which. CIO offset values. |
| `pm_data_april2026.csv` | 216,000 | Performance data per CELL per 15-min interval. HO counts, signal quality. |
| `pm_data_relation_level.csv` | 2.2M | Performance data per CELL PAIR per 15-min interval. **This is the key one.** |
| `cluster_kpi_summary.csv` | 75 | Monthly summary per cell. Problem cells flagged. |

The relation-level CSV doesn't exist in git (too large). Generate it:
```
python scripts/generate_relation_pm.py
```

---

## THE PROBLEM RIGHT NOW

The schema mapper (`schema_mapper.py`) cannot load any of the 5 CSVs. The reason: the column names in the CSVs don't match the field names in the Pydantic models. There are THREE different naming conventions across the codebase:

| Where | "serving cell" column | "HO attempts" column |
|-------|----------------------|---------------------|
| `pipeline/models.py` | `source_cell` | `ho_attempt` |
| `models/cell_data.py` | `source_cell_id` | `ho_attempts` |
| Actual CSV files | `serving_cell` | `ho_attempts_intra` |

This must be fixed before anything else works.

---

## TASKS — Do these in order

### Task 1: Consolidate models (Shourya)

There are TWO model files that define the same things differently:
- `src/pipeline/models.py` (4 models: SiteRecord, NeighborRelation, PMRecord, ClusterKPISummary)
- `src/models/cell_data.py` (5 models: CellSite, NeighborRelation, PMRecord, RelationPMRecord, ClusterKPISummary)

**What to do:**
1. Pick ONE file: `src/pipeline/models.py`
2. Add the `RelationPMRecord` model from `cell_data.py` into `models.py`
3. Delete `src/models/cell_data.py`
4. Update all imports across the codebase (`grep -r "from src.models" src/ tests/`)
5. Run `python -m pytest tests/ -v` — fix any import errors

**Done when:** Only ONE models file exists. All imports work. `pytest` runs (failures OK for now).

---

### Task 2: Fix the naming mismatch (Ananyaa + Harshit)

The models use idealized field names. The CSVs use real column names. The schema mapper's `_SIGNATURES` dict tries to match them but uses wrong column names.

**What to do:**

1. Open each CSV and note the ACTUAL column names (first row):
   ```
   head -1 data/synthetic/site_database.csv
   head -1 data/synthetic/neighbor_relations.csv
   head -1 data/synthetic/pm_data_april2026.csv
   head -1 data/synthetic/cluster_kpi_summary.csv
   ```
   (For relation-level, generate it first: `python scripts/generate_relation_pm.py`, then `head -1 data/synthetic/pm_data_relation_level.csv`)

2. Update `_SIGNATURES` in `schema_mapper.py` to use the ACTUAL CSV column names:
   ```python
   _SIGNATURES = {
       "SiteRecord": {"cell_id", "enodeb_id", "sector", "azimuth_deg", "antenna_height_m"},
       "NeighborRelation": {"serving_cell", "neighbor_cell", "cell_individual_offset_db"},
       "PMRecord": {"cell_id", "timestamp_utc", "ho_attempts_intra", "ho_success_intra", "avg_rsrp_dbm"},
       "RelationPMRecord": {"source_cell_id", "target_cell_id", "too_early_ho", "wrong_cell", "cio_db"},
       "ClusterKPISummary": {"cell_id", "ho_failure_rate_pct", "problem_cell", "total_ho_attempts"},
   }
   ```

3. Add `RelationPMRecord` to `KNOWN_SCHEMAS` dict and import it.

4. **Verify:**
   ```python
   python -c "
   from src.pipeline.schema_mapper import infer_schema
   from pathlib import Path
   for f in ['site_database.csv', 'neighbor_relations.csv', 'pm_data_april2026.csv', 'cluster_kpi_summary.csv', 'pm_data_relation_level.csv']:
       r = infer_schema(Path(f'data/synthetic/{f}'))
       print(f'{f:40s} -> {r.matched_model}')
   "
   ```
   All 5 must show their correct model name.

**Done when:** The verify script prints 5 correct matches. Zero `None`.

---

### Task 3: Make the RL environment use real data (Devika + Shourya)

Right now `src/env/mro_env.py` does this:
- `reset()` → returns random numbers
- `step()` → returns random numbers, reward = 0.0

It needs to:
- `reset()` → load relation-level CSV, set initial state from real data
- `step(action)` → given a CIO change, look up how HO outcomes change based on historical data
- Return a reward based on HO success rate

**What to do:**

1. In `reset()`: load `pm_data_relation_level.csv` into a DataFrame. Group by (source_cell_id, target_cell_id). Set observation = current KPIs per relation.

2. In `step(action)`: action = CIO delta per relation. For each relation, look up the nearest CIO value in the historical data and sample HO outcomes from that distribution.

3. Reward = sum of (ho_successes - 10*ho_failures - 3*ping_pong) across all relations.

4. **Verify:**
   ```python
   from src.env.mro_env import MROEnv
   env = MROEnv()
   obs, info = env.reset()
   print(f"Observation shape: {obs.shape}")
   obs2, reward, done, trunc, info = env.step(env.action_space.sample())
   print(f"Reward: {reward}")  # Should NOT be 0.0
   ```

**Done when:** `reward != 0.0` and observation comes from real CSV data, not random noise.

---

### Task 4: Train and measure (Week 2-3, after Tasks 1-3)

Only start this when Tasks 1-3 are done.

1. PPO training with Stable Baselines3:
   ```python
   from stable_baselines3 import PPO
   model = PPO("MlpPolicy", env, verbose=1)
   model.learn(total_timesteps=100_000)
   ```

2. Compare: random policy vs trained policy on same env.

3. Before/after chart: HO success rate improvement.

4. Streamlit dashboard: `streamlit run dashboard.py`

---

## Rules

1. **One branch per person, PR to staging.** Never push directly to master.
2. **Run `python -m ruff check src/ tests/` before every commit.** Fix all errors.
3. **Daily log in `docs/logs/YYYY-MM-DD-YourName.md`.** No log = absent.
4. **Stuck > 30 min → ask your lead. Lead stuck > 30 min → ask Danial/Nicolas.**
5. **Don't rename CSVs.** The pipeline adapts to whatever columns the CSV has. That's the point.

---

## Who to ask

- **Ananyaa** — team lead, schema mapper, data models
- **Danial** — technical supervisor, architecture questions
- **Nicolas** — product/business questions, approvals
- **This file** — re-read it if you're confused about what to do next
