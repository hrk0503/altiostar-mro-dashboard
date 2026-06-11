# MRO Dashboard — Deployment Guide
**Project:** WINNIIO Altiostar MRO | **Branch:** `staging` | **Phase:** 3

---

## Pre-Push Checklist

- [x] Changes committed and pushed to feature branches before staging
- [x] `requirements-dashboard.txt` present at repo root
- [x] `results/` folder contains all 16 experiment JSONs (v0–v3 × 4 scenarios)
- [x] No hardcoded local paths in `app.py`

---

## Repository Structure

```
project-root/
├── src/
│   ├── dashboard/
│   │   └── app.py
│   └── pipeline/
│       └── kpi_extractor.py
├── results/
│   ├── random_baseline.json
│   ├── v0_baseline.json
│   ...                             ← all 16 JSONs
├── requirements-dashboard.txt
└── .streamlit/
    └── config.toml                 ← optional
```

---

## Live Dashboard
 
🔗 https://altiostar-mro-dashboard.streamlit.app
 
Enter password to access. No setup needed.
 
---

## Running Locally

```powershell
pip install -r requirements-dashboard.txt --break-system-packages
streamlit run src/dashboard/app.py
```

App opens at `localhost:8501`. Enter password to access.

---

## Smoke Test

Run through this on the live URL or locally before any stakeholder session:

| Check | Expected |
|---|---|
| App loads without error | No traceback in UI |
| Login works | Password accepted, dashboard visible |
| Scenario dropdown | baseline / rush_hour / rain_fade / tower_failure |
| KPI table populates | HO success, ping-pong, failure breakdown visible |
| Before/after overlay | Random baseline vs trained comparison renders |
| Grouped bar chart | v1–v3 across 4 scenarios, V0 warning visible |
| V2 callout | Production recommendation shown |

---

## Known Issues & Fixes

| Issue | Fix |
|---|---|
| `ModuleNotFoundError: plotly` | Use `requirements-dashboard.txt`, not `requirements.txt` |
| `FileNotFoundError` for JSON | Ensure `results/` is not in `.gitignore` |
| Mid-session spinner | Cache TTL set to 600s — should not trigger in a normal session |
| V0 scale distortion | V0 warning banner present on Reports delta table |