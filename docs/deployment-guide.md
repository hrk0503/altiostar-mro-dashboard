# MRO Dashboard — Deployment Guide
**Project:** WINNIIO Altiostar MRO | **Branch:** `staging` | **Phase:** 3

---

## Pre-Push Checklist

- [x] Changes committed and pushed to feature branches before staging
- [x] `requirements-dashboard.txt` present at repo root
- [x] `results/` folder contains all 16 experiment JSONs (v0–v3 × 4 scenarios)
- [x] `results/random_baseline.json` present (before/after overlay depends on it)
- [x] `data/synthetic/` CSVs committed — app hard-crashes without them
- [x] `.streamlit/secrets.toml` exists locally (never commit this file)
- [x] `DASHBOARD_PASSWORD` set in Streamlit Cloud secrets (see §Secrets below)
- [x] No hardcoded local paths in `app.py`

---

## Repository Structure

```
project-root/
├── src/
│   ├── dashboard/
│   │   ├── app.py
│   │   └── assets/
│   │       ├── winniio_logo.png
│   │       ├── winniio_crane.png
│   │       └── favicon.ico
│   └── pipeline/
│       └── kpi_extractor.py
├── data/
│   └── synthetic/
│       ├── site_database.csv         ← REQUIRED — app crashes without this
│       ├── pm_data_april2026.csv     ← REQUIRED
│       ├── neighbor_relations.csv   ← REQUIRED
|       ├── cluster_kpi_summary.csv
|       └── pm_data_relation_level.csv
├── results/
│   ├── random_baseline.json         ← before/after overlay
│   ├── experiment_v0_baseline.json
│   ...                               ← all 16 experiment JSONs
├── requirements-dashboard.txt
└── .streamlit/
    ├── configs.toml
    └── secrets.toml                  ← local only, never commit
```

---

## Live Dashboard

🔗 https://altiostar-mro-dashboard.streamlit.app

Enter password to access. No setup needed for stakeholder review.

---

## Secrets Setup

### Local development

Create `.streamlit/secrets.toml` at project root (not committed to git):

```toml
DASHBOARD_PASSWORD = "your_password_here"
```

Add to `.gitignore` if not already there:
```
.streamlit/secrets.toml
```

### Streamlit Cloud (production)

1. Go to [share.streamlit.io](https://share.streamlit.io) → your app → **Settings → Secrets**
2. Add:
   ```toml
   DASHBOARD_PASSWORD = "your_password_here"
   ```
3. Save. App restarts automatically.

If `DASHBOARD_PASSWORD` is missing from secrets, the app crashes immediately with `KeyError` before rendering anything.

---

## Fresh Clone — Full Steps

```powershell
git clone https://github.com/LifeAtlas/altiostar-tokyo-mro.git
cd altiostar-tokyo-mro
git checkout staging

pip install -r requirements-dashboard.txt --break-system-packages

# Create local secrets file
New-Item -Path ".streamlit" -ItemType Directory -Force
Set-Content .streamlit/secrets.toml 'DASHBOARD_PASSWORD = "your_password_here"'

streamlit run src/dashboard/app.py
```

App opens at `localhost:8501`.

---

## Python Version

Python **3.10+** required. Streamlit Cloud defaults to 3.10; no `runtime.txt` needed unless you need to pin a specific version.

---

## Redeployment (Streamlit Cloud)

Pushing to `staging` triggers automatic redeploy. To force a redeploy manually: **Settings → Reboot app** in the Streamlit Cloud UI.

---

## Smoke Test

Run this checklist on the live URL or locally before any stakeholder session:

| # | Check | Expected |
|---|---|---|
| 1 | App loads without error | No traceback in UI |
| 2 | Login works | Password accepted, dashboard visible |
| 3 | Dashboard page — KPI cards | 6 metric cards render (Cluster Avg, Best, Worst, Failure %, PRB, Experiments) |
| 4 | Dashboard page — donut chart | Cell health distribution renders (Healthy/Warning/Critical) |
| 5 | Dashboard page — bar chart | Grouped bars for v0–v3 across all scenarios |
| 6 | Experiments page — scenario filter | baseline / rush_hour / rain_fade / tower_failure all present |
| 7 | Experiments page — before/after overlay | "Before / After — Random Baseline vs Trained Agent" section renders |
| 8 | Experiments page — improvement delta | Green/red delta card vs random baseline |
| 9 | Experiments page — heatmap | 4×4 grid (variants × scenarios) renders |
| 10 | Network page — scenario selector | 4 scenarios in dropdown, topology redraws on change |
| 11 | Simulation page — live map | Map pulses, agent log updates every 2s |
| 12 | Reports page — Gate checklist | All criteria shown (note: label says G3 — cosmetic, being updated) |
| 13 | Quick Export | CSV downloads functional |
| 14 | Anomaly Scan | Runs and returns flagged cells |

---

## Known Issues & Fixes

| Issue | Fix |
|---|---|
| `KeyError: 'DASHBOARD_PASSWORD'` on load | Add secret to `.streamlit/secrets.toml` (local) or Streamlit Cloud Secrets (prod) — see §Secrets above |
| `ModuleNotFoundError: plotly` | Use `requirements-dashboard.txt`, not `requirements.txt` |
| `FileNotFoundError` for CSVs | Ensure `data/synthetic/` is committed and not in `.gitignore` |
| `FileNotFoundError` for experiment JSONs | Ensure `results/` is committed; Experiments page shows empty state gracefully if missing |
| Before/after overlay missing | Ensure `results/random_baseline.json` is committed; section silently omitted if absent |
| Mid-session spinner / cache miss | Cache TTL is 600s — normal for first load after cold start |
| V0 reward scale distortion | Expected — V0 uses raw count reward (~9M) vs V1–V3 rate-based (~210K). Warning banner shown on Reports delta table. |
| Reports Gate label says "G3" | Cosmetic — currently showing Gate G3 checklist; update `_n_tests` and label in `app.py` before G4 review |

---

## Gate G4 — Pre-Demo Fix Needed in `app.py`

On the **Reports → Gate G3 Checklist** tab, the section title and tab label reference G3. Before the Nicolas meeting, update these two lines in `app.py`:

```python
# Line ~860 (tab_gate):
tab_delta, tab_rec, tab_export, tab_gate = st.tabs([
    "KPI Delta Table", "Recommendations", "Export Data", "Gate G4 Checklist"])  # ← G3 → G4

# Line ~900 (gate header):
sec("Gate G4 Checklist")  # ← G3 → G4

# Line ~940 (gate card):
f'<div style="font-size:1.1rem;font-weight:700;color:{gc};">Gate G4 — {gt}</div>'  # ← G3 → G4
```

---

*WINNIIO · AltioStar MRO · Phase 3 · Last updated: June 2026*