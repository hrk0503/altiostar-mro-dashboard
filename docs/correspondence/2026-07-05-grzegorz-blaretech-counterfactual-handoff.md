# Correspondence — Blaretech counterfactual data handoff

- **Date sent:** 2026-07-05
- **From:** Nicolas Waern (ceo@winniio.io)
- **To:** Grzegorz Hawrot (grzegorz.hawrot@blare.tech)
- **Bcc:** nicolaswaern@gmail.com
- **Subject:** Altiostar/Rakuten — the WINNIIO↔Blaretech data handoff (sorry for the delay)
- **Package (OneDrive, view-only):** `WINNIIO_Blaretech_Counterfactual_Package_20260705.zip`
- **Status:** SENT
- **Context:** First formal WINNIIO→Blaretech data handoff implementing the counterfactual contract (see `docs/COUNTERFACTUAL.md`, `src/integration/blaretech_export.py`).

---

## Message (as sent)

Hi Grzegorz,

Apologies for the delay getting this to you — I found some things in our pipeline that needed fixing before I could hand you something I trust, so I took the time to do it properly rather than send you something half-right. Worth it: what came out of it actually makes the joint story stronger.

**The insight (2 minutes):** operator PM data records each handover relation at the *one* CIO value it was actually running. To recommend a *better* CIO, our optimizer needs to know what handovers would do at *other* CIO values — and raw data can't tell us, because those settings were never tried. We proved it by re-running our optimizer honestly: on raw data it finds **zero** improvement (one CIO per relation = nothing to search over). The optimization only becomes real once something simulates the outcomes at other CIO values — and that something is your RF/propagation layer.

So the two platforms aren't two products — they're one loop: **WINNIIO finds where handovers fail and lists the CIOs to test → Blaretech simulates the outcome at each → WINNIIO optimizes over the results.** That's the whole platform in one sentence, and it's the most honest, most compelling thing we can put in front of Soumyadeep.

**The package (OneDrive link):** WINNIIO_Blaretech_Counterfactual_Package_20260705.zip — built on synthetic Shibuya data in Rakuten's exact schema, so you can build ingestion now and swap in the real cluster when it lands under NDA:

- `01_counterfactual_request.csv` — 6,867 rows (763 relations × 9 candidate CIOs), each with source/target lat-lon, azimuth, tilt, band, clutter, distance, current CIO + success
- `02_sites.geojson` — 75 georeferenced sites (WGS84, azimuth/tilt/band) to drop onto your map / RF world
- `03_relations.geojson` — 763 relation lines, priority-flagged
- `RETURN_SCHEMA.csv` + `README.md` / `README.pdf`

**What we need back from you:** the same 6,867 rows with your simulation's predicted counters per (relation × CIO) — `sim_ho_attempts, sim_ho_successes, sim_ho_failures, sim_too_early, sim_too_late, sim_wrong_cell, sim_ping_pong`. That's the RETURN_SCHEMA. We re-ingest it and the optimizer runs on a real search space.

**Two quick questions:** (a) does this format ingest cleanly into your platform, and (b) what complementary geometry would you want from us to make the propagation sim faithful — clutter tiles, building data, beam patterns? Whatever you need, tell me and I'll get it into the next package.

The one thing we're both ultimately waiting on is Soumyadeep's real cluster data under NDA — but we don't need it to build and test the interface. If this format works, this *is* the combined platform we demo to Rakuten.

Talk soon,
Nicolas

---

## Awaiting reply
- [ ] Does the format ingest cleanly into Blaretech's platform?
- [ ] Complementary geometry Blaretech wants (clutter / buildings / beam patterns)?
- [ ] Filled `RETURN_SCHEMA.csv` (6,867 simulated rows) → re-ingest to run the real CIO search.
