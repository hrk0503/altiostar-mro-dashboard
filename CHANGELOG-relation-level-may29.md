# Changelog: Relation-Level Granularity — May 29, 2026

## WHY THIS CHANGE

Soumyadeep confirmed (May 27) that real Altiostar PM counters are at **RELATION level** — each data point is a serving_cell -> neighbor_cell pair per 15-min ROP. Our existing synthetic data (`pm_data_april2026.csv`) is at **CELL level** — aggregated per cell. That's the wrong granularity for MRO optimization, because CIO adjustments happen per neighbor pair, not per cell.

**Cell level**: "Cell RKSB-001-1 had 18 HO attempts this ROP"
**Relation level**: "Cell RKSB-001-1 -> RKSB-001-2 had 5 HO attempts, 2 too-late failures"

The RL agent must learn to tune CIO per neighbor pair. Cell-level data can't teach that.

## WHAT WAS ADDED (all new files, nothing modified)

### 1. `data/synthetic/pm_data_relation_level.csv` (NEW — 2,197,440 rows, 136 MB)
- 763 neighbor relations x 2,880 ROPs (April 2026, 15-min intervals)
- Columns: `source_cell_id, target_cell_id, timestamp_utc, rop_duration_min, ho_attempts, ho_successes, ho_failures, too_early_ho, too_late_ho, wrong_cell, correct_cell, ping_pong, cio_db`
- Relation-level HO counts are distributed from cell-level totals across neighbors (realistic skew, seeded for reproducibility)
- Cell-level totals still sum correctly when aggregated back

### 2. `data/pm_data_relation_level.csv` (copy of above, in main data/ alongside existing CSVs)

### 3. `scripts/generate_relation_pm.py` (NEW — generation script)
- Reads cell-level PM data + neighbor_relations.csv
- Distributes HO counts across neighbor pairs with realistic skew
- Deterministic (seed=42) — re-run produces identical output
- Run: `python scripts/generate_relation_pm.py`

### 4. `src/models/cell_data.py` lines 45-61 — `RelationPMRecord` already exists
- This Pydantic model was already added (pre-existing). Matches the new CSV columns.
- NOT yet registered in schema_mapper.py — that's the intern task.

## WHAT WAS NOT CHANGED

- `data/synthetic/pm_data_april2026.csv` — untouched, still cell-level, still needed
- `data/synthetic/site_database.csv` — untouched
- `data/synthetic/neighbor_relations.csv` — untouched (read-only input for generation)
- `data/synthetic/cluster_kpi_summary.csv` — untouched
- `src/pipeline/schema_mapper.py` — untouched (interns must update)
- `src/pipeline/models.py` — untouched (interns must update)
- All existing tests — untouched

## WHAT INTERNS MUST DO (see TASK-relation-level-may29.md)

Separate task file with exact instructions.
