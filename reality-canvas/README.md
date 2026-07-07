# WINNIIO Reality Canvas — Phase 1-4

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
- `src/lib/loadData.ts` — fetches `/data/*.json` and `/data/*.czml` (offline path)
- `src/lib/api.ts` — live API client: config parsing, health check, `/czml`, `/simulate`, `/jobs/{id}/result`
- `src/lib/results.ts` — indexes a simulate job's per-relation results for the before/after color overlay
- `src/components/SimulatePanel.tsx` — "Run MRO Optimization" button, summary card, before/after toggle
- `src/components/CesiumCanvas.tsx` — imperative Cesium.Viewer wiring (imagery, terrain, beams, relations, CZML load, layer toggles); exposes `window.__viewer` for e2e tests only
- `src/components/ControlPanel.tsx` — NOC-console-styled dark panel: stats, layer checkboxes, relations threshold slider, UE-count/seed selectors, dim-basemap toggle
- `src/constants.ts` — every user-facing string (vertical-agnostic rule)
- `scripts/export_canvas_data.py` (repo root) — CSV -> sites.json / relations.json / scene-*.czml

## Live API mode (P4)

The app runs fully offline by default (pre-generated scenes only, as in P1).
Setting `VITE_API_URL` opts into live mode:

```bash
cp .env.example .env.local
# .env.local
VITE_API_URL=http://localhost:8600
VITE_API_TOKEN=devtoken
```

Full-stack local demo (from the repo root, two terminals):

```bash
# Terminal 1 — backend
WINNIIO_API_TOKEN=devtoken WINNIIO_ALLOWED_ORIGINS=http://localhost:5183 \
  python -m uvicorn backend.app.main:app --port 8600

# Terminal 2 — frontend
cd reality-canvas
npm run dev   # http://localhost:5183
```

What live mode changes:

- On load, the app pings the API root. If reachable, the mode indicator
  (top-left) switches from "Pre-generated (offline)" to "Live API".
  Unreachable/misconfigured → automatic, silent fallback to the bundled
  pre-generated scenes. This fallback is never removed.
- UE count + seed become free-form number inputs (1-500 / any seed) and fetch
  `GET /api/v1/czml` live instead of picking from the 4 fixed scenes.
- A new "MRO Optimization" panel appears with a **Run MRO Optimization
  (synthetic)** button → `POST /api/v1/simulate` → summary card (relations
  count, avg before → after, the `NOT_A_PERFORMANCE_CLAIM` honesty banner in
  amber). A **Before/After** toggle then fetches
  `GET /api/v1/jobs/{id}/result` (added in P4 — serves the per-relation
  before/after CSV as JSON) and recolors the matched relation polylines with
  the same red/amber/green success-rate ramp.
- If the API is configured but a request fails mid-session (simulate error,
  network drop), the panel shows an explicit error state — it never silently
  swallows the failure or fakes a result.

## Known P1 scope limits (honest, not hidden)

- UE-count/seed selection switches between **4 pre-generated** CZML scenes
  (21/100/500 @ seed 42, 100 @ seed 99). No live regeneration yet — labeled
  "pre-generated scenes (live API in P2)" in the UI.
- Sector beamwidth is a constant 65° placeholder (`site_database.csv` has no
  beamwidth column) — visually indicative, not RF-accurate.
- Login gate is a client-side password check against an env var, not real auth.
