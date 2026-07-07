# WINNIIO Reality Canvas — Phase 1

CesiumJS RAN digital-twin viewer for the Tokyo MRO synthetic dataset. Standalone
Vite + React + TypeScript app (separate from `frontend/`, which is an unrelated
Next.js portal — kept isolated to avoid touching that codebase).

No Cesium ion token required: OpenStreetMap raster imagery + flat
`EllipsoidTerrainProvider` by default. Google Photorealistic 3D Tiles are added
only if `VITE_GOOGLE_3DTILES_KEY` is set — the app runs fully without it.

## Data pipeline (regenerate before first run, or after changing synthetic data)

From the repo root:

```bash
mkdir -p .canvas_mobility
python scripts/generate_relation_pm.py   # only if data/synthetic/pm_data_relation_level.csv is missing
python scripts/generate_mobility_traces.py --out-dir .canvas_mobility/mob21_42   --n-ues 21  --seed 42
python scripts/generate_mobility_traces.py --out-dir .canvas_mobility/mob100_42  --n-ues 100 --seed 42
python scripts/generate_mobility_traces.py --out-dir .canvas_mobility/mob100_99  --n-ues 100 --seed 99
python scripts/generate_mobility_traces.py --out-dir .canvas_mobility/mob500_42  --n-ues 500 --seed 42
python scripts/export_canvas_data.py
```

This writes `reality-canvas/public/data/{sites.json,relations.json,scenes.json,scene-*.czml}`.
All data is SYNTHETIC — labeled as such in the CZML document name and app subtitle.

## Run

```bash
cd reality-canvas
npm install
cp .env.example .env.local   # optional: set VITE_GOOGLE_3DTILES_KEY, override VITE_DEMO_PASSWORD
npm run dev                  # http://localhost:5183
```

Demo login password defaults to `Winniio-2019` (env `VITE_DEMO_PASSWORD`). This
is a demo gate only — SSO is planned for P3.

## Test

```bash
npm run typecheck   # tsc --noEmit
npm run test        # vitest (unit tests: color ramp, wedge geometry, scene lookup, auth, stats)
npm run build        # vite build, must exit 0
npm run e2e          # Playwright, headless chromium; screenshots -> e2e-artifacts/
```

## Where things live

- `src/lib/geo.ts` — pure transforms: success-rate color ramp, sector wedge geometry, frequency-band color, scene lookup
- `src/lib/auth.ts` — demo login gate (sessionStorage)
- `src/lib/stats.ts` — header stats computed from loaded data
- `src/lib/loadData.ts` — fetches `/data/*.json` and `/data/*.czml`
- `src/components/CesiumCanvas.tsx` — imperative Cesium.Viewer wiring (imagery, terrain, beams, relations, CZML load, layer toggles); exposes `window.__viewer` for e2e tests only
- `src/components/ControlPanel.tsx` — NOC-console-styled dark panel: stats, layer checkboxes, relations threshold slider, UE-count/seed selectors, dim-basemap toggle
- `src/constants.ts` — every user-facing string (vertical-agnostic rule)
- `scripts/export_canvas_data.py` (repo root) — CSV -> sites.json / relations.json / scene-*.czml

## Known P1 scope limits (honest, not hidden)

- UE-count/seed selection switches between **4 pre-generated** CZML scenes
  (21/100/500 @ seed 42, 100 @ seed 99). No live regeneration yet — labeled
  "pre-generated scenes (live API in P2)" in the UI.
- Sector beamwidth is a constant 65° placeholder (`site_database.csv` has no
  beamwidth column) — visually indicative, not RF-accurate.
- Login gate is a client-side password check against an env var, not real auth.
