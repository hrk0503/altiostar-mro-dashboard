# Extra Geo / Multi-Season MRO Datasets

12 additional handover datasets — **3 network footprints × 4 seasons** — to feed
the MRO pipeline / RL env beyond the original Tokyo + Berlin/Seoul clusters.

| Footprint | Bands | Vendor | Clutter | Why it's distinct |
|---|---|---|---|---|
| **Kyiv** (continental) | Band 1, Band 3 (FDD) | Ericsson | Dense Urban → Suburban | Harsh snowy winter (RSRP↓, fail↑); early/normal-dominated failures |
| **Nagano rural** (mountain) | Band 1, Band 3 (FDD) | NEC | Rural / Open | Wide-spaced cells → **too-late HO dominated**; winter ski load + snow |
| **Downtown Tokyo** (coastal) | Band 1, **Band 41 (TDD)** | Rakuten | Dense Urban / High-Rise | Band 41 TDD + Tokyo Bay → summer/autumn **tropospheric ducting** → wrong-cell + ping-pong |

Seasons: `winter` (Jan), `spring` (Apr), `summer` (Jul), `autumn` (Oct), 2026.
Each season applies climate-/band-specific RF physics (foliage, snow/ice,
ducting, typhoon, traffic) — see [SEASONAL_RESEARCH.md](SEASONAL_RESEARCH.md).

## Layout
```
extra_geo/<location>_<season>/
  site_database.csv            # committed
  neighbor_relations.csv       # committed
  cluster_kpi_summary.csv      # committed
  pm_data_relation_level.csv   # gitignored — regenerate (see below)
```

## Regenerate everything (deterministic, fixed seeds)
```bash
python scripts/generate_extra_geo_data.py
```
Produces all 12 datasets under `data/extra_geo/` (~283 MB, 4.44 M PM rows total).

## Feeding the env
Relation-level format — `MROEnv` auto-detects it via the `source_cell_id` column
and prefers it over cell-level PM. Example:
```python
from src.env.mro_env import MROEnv
env = MROEnv(pm_data_path="data/extra_geo/tokyo_summer/pm_data_relation_level.csv")
```

All four CSVs pass the strict `src/pipeline/models.py` validators
(`SiteRecord` band whitelist, `RelationPMRecord`, `ClusterKPISummary`).
Data is **synthetic** and labelled as such.
