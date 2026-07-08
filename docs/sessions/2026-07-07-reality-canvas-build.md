# Session — Reality Canvas build + Rakuten Jul 7 follow-through

**Dates:** 2026-07-06 → 2026-07-08 · **Repo:** LifeAtlas/altiostar-tokyo-mro · **Branch:** staging

## Commits / PRs merged to staging
| PR | What |
|----|------|
| #19 | QA: dead top-bar chips → real controls + 3-layer interaction test net (v0.2.0) |
| #20 | Reality Canvas P1 — Cesium viewer (timeline, UE slider, seed scenes) |
| #21 | Reality Canvas P2 — API: /czml, /datasets upload, /simulate + RF provider seam |
| #22 | Reality Canvas P4 — live API mode + Simulate loop (before/after on globe) |
| direct | P0 — `--seed` + CZML exporter; mobility UE height (AGL) + env + caveats; RSRP export context; metamorphic flake fix; parameterized `--n-ues`/`--sample-hz` + numpy nearest |

## What was built
- **Mobility generator**: `--n-ues` (500-ready), `--seed`, `--sample-hz`; UE height AGL (3GPP TR 38.901); numpy nearest (seconds for 500 UEs). Tests: tests/test_mobility.py.
- **CZML exporter** `src/exporters/czml.py`: traces+sites → time-dynamic Cesium doc (clock, site markers, UE trails, HO markers at instant). tests/test_czml_export.py.
- **Reality Canvas** `reality-canvas/` (Vite+React+TS+Cesium, sibling to the existing Next.js `frontend/`): OSM basemap (no keys), Google 3D Tiles behind env slot, sector beams by band, relations colored by HO success + hide-slider, moving UEs, UE slider 21→500, seed switch, dim toggle, NOC-dark UI, demo gate, live-API mode + offline fallback, Simulate → before/after recolor. Vitest 35, Playwright 9.
- **Backend API** `backend/app/routers/{czml,datasets,simulate}.py` + `rf/` provider seam (synthetic works; blaretech honest 501). WebSocket token moved out of query string. tests/backend/test_api.py.
- **RSRP export context** in `src/integration/blaretech_export.py` (SD ask).

## Test status (verified)
- Full pytest: **395 passed, 3 skipped** (12m). ruff clean.
- Frontend: Vitest 35, Playwright 9, tsc + vite build exit 0 (51 KB gz).
- Full-stack smoke verified: `/czml?n_ues=50&seed=7` → 200 (421 KB); `/simulate` → 763 relations, 79.16→99.0, NOT_A_PERFORMANCE_CLAIM banner.

## In flight at session end (NOT merged — resume from these branches)
- `feat/reality-canvas-security` — export UUID/TTL/deletion receipts, upload hardening, P3 tenancy code + RLS migrations, tier caps.
- `feat/reality-canvas-agents` — deterministic anomaly detector + grounded explainer + ≥20 golden evals + supervisor gate.

## Open / owner-blocked
- P3 deploy: new Supabase project + Vercel. P5 Sionna RT: GPU + **Blaretech IP contract first**. Google 3D Tiles key (env slot ready). Rakuten NDA → masked Japan data.
- Clutter-class sandbox (SD's greenfield ask) — planned, sequenced after security branch.
- Streamlit Cloud deploy of the Altiostar dashboard still owner-gated.

## Deliverables (OneDrive/WINNIIO 2026/ALTIO STAR RAKUTEN/)
- Jul 7 meeting as-is + MRO map (HTML); Reality Canvas Master Plan (GLASS-scored, HTML); mobility packages v2 + 500-UE; Grzegorz emails sent.
