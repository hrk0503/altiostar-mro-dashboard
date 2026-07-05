# Migration to Full Owner Control

Goal: the production dashboard deploys **directly from `LifeAtlas/altiostar-tokyo-mro`**
(the org repo you control) — not from any personal fork or mirror.

## Background (what it was)

Until 2026-07-05, a cron workflow (`.github/workflows/sync-upstream.yml`)
force-pushed this repo's `staging` every 15 minutes into a **personal** repo,
`hrk0503/altiostar-mro-dashboard`, and Streamlit Community Cloud served the app
from *that* personal repo. Consequences: production depended on a departed
contributor's account, deployed dependencies were silently rewritten, and the
owner had no direct control.

That workflow has been **removed**. Complete the two owner-only steps below to
finish the cutover (they require logging into Streamlit Cloud — cannot be
scripted from the repo).

## Owner steps (≈10 minutes, one time)

1. **Re-point the Streamlit Cloud app to the org repo.**
   - Go to https://share.streamlit.io → your workspace → the
     `altiostar-mro-dashboard` app → **Settings › General**.
   - Change **Repository** to `LifeAtlas/altiostar-tokyo-mro`,
     **Branch** = `staging`, **Main file path** = `src/dashboard/app.py`.
   - (If the platform won't let you re-point an existing app, delete it and
     **New app › from existing repo** with the same three values. The public
     URL can be reclaimed on the new app.)

2. **Set the app secret** (the password stays as-is per your instruction).
   - App **Settings › Secrets**, add:
     ```
     DASHBOARD_PASSWORD = "Winniio-2019"
     ```
   - Deploy. The app installs from the repo's pinned `requirements.txt`
     (no more heredoc rewrite).

## Verify

- Push a trivial change to `staging` → the Cloud app rebuilds from the org repo.
- Confirm the login gate works and the sidebar shows the Rakuten profile
  (Japan-only datasets).
- The old personal repo `hrk0503/altiostar-mro-dashboard` can then be archived
  or deleted — nothing depends on it anymore.

## Result

One repo, one owner, one deploy path. No private-fork archaeology, no cron, no
external account in the critical path.
