# Changelog

All notable changes to this project are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/); this
project is pre-1.0, so versioning is semver-ish (`0.MINOR.PATCH`) rather than
strict SemVer guarantees.

## [0.2.0] — 2026-07-06

### Fixed
- **Dead top-bar "Quick Export" chip.** The four top-bar chips (`Live
  Monitor` / `Anomaly Scan` / `Health Check` / `Quick Export`) were
  decorative `<span class="topnav-chip">` HTML with a button-like `:hover`
  glow but no click handler — every prior code review missed this because
  none of them drove the running UI, only read the source.
  - `Anomaly Scan`, `Health Check`, and `Quick Export` chips are now real
    `st.button` widgets that toggle their existing result panels.
  - `Live Monitor` has no backend behind it, so it stays an honest,
    non-interactive status label (renamed CSS class `.status-label`, hover
    glow removed) instead of looking clickable.
  - Removed the now-redundant second row of buttons ("Run Anomaly Scan" /
    "Network Health Check" / "Quick Export All") — one control per action.
- `.streamlit/secrets.toml` (project root) was not in `.gitignore`, even
  though it holds `DASHBOARD_PASSWORD` — closed the gap.

### Added — QA interaction test net (three layers, see `tests/`)
1. **`tests/test_dashboard_interactions.py`** — `streamlit.testing.v1.AppTest`
   effect-tests: every header chip-button is asserted to actually toggle its
   panel (content present after click, absent before/after re-click), the
   Quick Export panel's 4 download buttons are asserted present with real
   registered file payloads, and every nav page renders without exception.
2. **`tests/test_no_dead_controls.py`** — static guard that parses
   `src/dashboard/app.py` for any HTML element styled to look clickable
   (button-like `:hover` affordance or `cursor:pointer`) that isn't backed
   by a real Streamlit widget. Verified to fail against the pre-fix source
   (catches `.topnav-chip:hover`) and pass against the fixed source — this
   is the permanent net against this exact bug recurring.
3. **`tests/e2e/test_dashboard_e2e.py`** — Playwright end-to-end tests that
   launch the real `streamlit run` process and click actual rendered DOM
   elements in Chromium, including asserting a real file download fires and
   that `Live Monitor` carries no pointer cursor. CI-gated via a dedicated
   `playwright` job in `.github/workflows/ci.yml` (needs the fast job).

[0.2.0]: https://github.com/LifeAtlas/altiostar-tokyo-mro/compare/v0.1.0...v0.2.0
