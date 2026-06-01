# TASK: Wire Up Relation-Level Data — ASAP (blocks Phase 1)

**Assigned to:** Altiostar team (Ananyaa lead, all 4 contribute)
**Priority:** BLOCKING — Phase 1 cannot start without this
**Context:** See `CHANGELOG-relation-level-may29.md` for why

---

## Background

A new CSV has been added: `data/synthetic/pm_data_relation_level.csv` (2.2M rows). This is the granularity that matches real Altiostar data — HO counters per serving_cell -> neighbor_cell pair per 15-min ROP. The RL agent in Phase 1 needs this to learn CIO adjustments per neighbor pair.

The Pydantic model `RelationPMRecord` already exists in `src/models/cell_data.py:45-61`. But the pipeline code (`src/pipeline/`) doesn't know about it yet.

---

## Task 1: Add RelationPMRecord to pipeline/models.py

**File:** `src/pipeline/models.py`
**What:** Add a `RelationPMRecord` class matching the one in `src/models/cell_data.py:45-61`

Fields (from the new CSV columns):
```
source_cell_id: str
target_cell_id: str
timestamp: datetime
ho_attempts: int (>= 0)
ho_successes: int (>= 0, <= ho_attempts)
ho_failures: int (>= 0)
too_early_ho: int (>= 0)
too_late_ho: int (>= 0)
wrong_cell: int (>= 0)
correct_cell: int (>= 0)
ping_pong: int (>= 0)
cio_db: float (-24.0 to 24.0)
```

Add validator: `ho_successes <= ho_attempts`

---

## Task 2: Register in schema_mapper.py

**File:** `src/pipeline/schema_mapper.py`

1. Import `RelationPMRecord` from `src.pipeline.models`
2. Add to `KNOWN_SCHEMAS` dict:
   ```python
   "RelationPMRecord": RelationPMRecord,
   ```
3. Add signature to `_SIGNATURES` dict. These columns uniquely identify the relation-level CSV:
   ```python
   "RelationPMRecord": {"source_cell_id", "target_cell_id", "too_early_ho", "wrong_cell", "cio_db"},
   ```

**Verify it works:**
```python
from src.pipeline.schema_mapper import infer_schema
from pathlib import Path
r = infer_schema(Path('data/synthetic/pm_data_relation_level.csv'))
assert r.matched_model == 'RelationPMRecord'
```

---

## Task 3: Write tests

**File:** `tests/test_relation_pm.py` (new file)

Tests to write:
1. `test_infer_relation_pm` — schema mapper identifies the CSV as RelationPMRecord
2. `test_relation_pm_row_count` — CSV has 2,197,440 rows
3. `test_ho_success_le_attempts` — no row has ho_successes > ho_attempts
4. `test_all_relations_covered` — every pair in neighbor_relations.csv appears in the relation PM data
5. `test_cell_level_aggregation` — sum of relation-level ho_attempts per cell per ROP equals the cell-level total in pm_data_april2026.csv (pick 5 random cells to test, not all 216K)

---

## Task 4: Update existing schema_mapper signatures (BONUS — fixes 20 test failures)

The existing `_SIGNATURES` dict uses field names that don't match the actual CSV columns. This is why `test_schema_mapper.py` has failures. Fix:

| Schema | Current signature (wrong) | Correct signature (matches CSV) |
|--------|--------------------------|-------------------------------|
| SiteRecord | `cell_id, site_id, sector, azimuth, tx_power_dbm` | `cell_id, enodeb_id, sector, azimuth_deg, antenna_height_m` |
| NeighborRelation | `source_cell, target_cell, cio_db` | `serving_cell, neighbor_cell, cell_individual_offset_db` |
| PMRecord | `cell_id, timestamp, ho_attempt, ho_success, rsrp_dbm` | `cell_id, timestamp_utc, ho_attempts_intra, ho_success_intra, avg_rsrp_dbm` |
| ClusterKPISummary | `cell_id, monthly_ho_success_rate, problem_flag` | `cell_id, ho_failure_rate_pct, problem_cell, total_ho_attempts` |

**After this fix:** Schema mapper will correctly DETECT all 5 CSV types. Loading still fails because model fields != CSV columns — that's a separate task (column rename mapping).

---

## Definition of Done

- [ ] `python -c "from src.pipeline.schema_mapper import infer_schema; ..."` matches all 5 CSVs
- [ ] `pytest tests/test_relation_pm.py` — all 5 tests green
- [ ] No existing tests broken by these changes
- [ ] PR to staging with this task file linked in the description

---

## Files to read first

1. `CHANGELOG-relation-level-may29.md` — what was added and why
2. `src/models/cell_data.py:45-61` — existing RelationPMRecord reference
3. `data/synthetic/pm_data_relation_level.csv` (first 10 rows) — see the actual data
4. `src/pipeline/schema_mapper.py` — understand how signature matching works
