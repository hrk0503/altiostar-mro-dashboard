# Altiostar MRO Pipeline — REVISED PLAN (May 29, 2026)

**This replaces the phase-gated plan for the remaining 4 weeks. Read `ALTIOSTAR-PLAN.md` for background — this file is the execution reality.**

---

## Honest State (May 29)

| What the old plan says | What actually exists |
|------------------------|---------------------|
| "Phase 0 at 90%" | Schema mapper can't load any of the 5 CSVs (20/65 tests fail) |
| "7 autonomous agents" | 200 lines of `raise NotImplementedError` stubs across 7 files |
| "Interns are QA, not developers" | Interns wrote 100% of the working code (806 lines src + 556 lines tests) |
| "Gymnasium env boots with random policy" | `step()` returns random noise, reward = 0.0, no data connection |
| "RL env from YAML config" | Config loads but env ignores it — no simulation, no state tracking |

### The Three Naming Conventions Problem

| Source | Example field | For "serving cell" |
|--------|--------------|-------------------|
| `pipeline/models.py` | `source_cell` | idealized names |
| `models/cell_data.py` | `source_cell_id` | Nicolas scaffold |
| Actual CSVs | `serving_cell` | real column names |

These are **three incompatible naming conventions** for the same data. The schema mapper bridges none of them. This must be resolved FIRST.

---

## What the Product Must Do (external-grade, reusable)

This is internal work but built to external standards. If SD walked in unannounced, it should stand up. If a different operator handed us their CSVs tomorrow, same pipeline should work.

1. **Ingest any operator's PM CSV** — auto-detect schema, validate, normalize. Relation-level (serving -> neighbor per 15-min ROP) or cell-level.
2. **Train an RL model that improves HO success rate** — from ~97-98% baseline to >99.5% at relation level. Reproducible (seeded, logged).
3. **Produce a before/after KPI chart** — the one artifact that sells the platform to any decision-maker.
4. **Ship in a Docker container** — `docker run` on any machine, no setup beyond CSV input.
5. **Work on fresh data with zero code changes** — same pipeline, different CSV = different results. YAML config, not hardcoded.

NOT needed: agent orchestration, EPIC metrics, scenario engines, ONNX export, Helm charts. Those are post-revenue polish.

---

## June 5 Session (Nicolas presents the platform)

Nicolas owns this. Interns are NOT presenting, NOT asking SD to verify anything. The session is about WINNIIO's intelligence layer — the intern pipeline is internal capability proof.

What Nicolas needs from the pipeline BY June 4 EOD:
1. Schema mapper that loads all 5 CSVs without errors (proves data ingestion works)
2. Env that boots from relation-level CSV (proves we understand the granularity)
3. Architecture diagram showing CSV -> validate -> env -> train -> evaluate -> dashboard flow
4. One slide: "here's how the pipeline handles YOUR data format" with actual column mappings

---

## 4-Week Sprint (May 29 - Jun 27)

**480 person-hours. One goal: trained model that beats random baseline with before/after chart.**

### Week 1 (May 29 - Jun 2): Fix the foundation — ALL HANDS

| Day | Task | Who | Done when |
|-----|------|-----|-----------|
| Thu-Fri | Fix naming: pick ONE convention, align CSVs + models + mapper | Ananyaa + Harshit | All 5 CSVs load via `auto_map_and_load()`, 0 test failures |
| Thu-Fri | Delete duplicate model file — ONE models.py with ALL 5 schemas | Shourya | `src/models/cell_data.py` deleted, all imports updated |
| Thu-Fri | Env reads relation-level CSV, tracks state per relation | Devika + Shourya | `env.reset()` loads data, `env.step()` uses it |

### Week 2 (Jun 3 - Jun 6): Transition model + reward — THE HARD PART

| Task | Who | Done when |
|------|-----|-----------|
| Data-driven transition model: given (current CIO, relation KPIs) + action (CIO delta), predict next-step HO outcomes using historical CSV averages | Harshit + Ananyaa | `step()` returns realistic obs based on action, not random noise |
| Reward function v0: +1 per successful HO, -10 per failure, -3 per ping-pong, weighted by relation traffic volume | Shourya | Reward correlates with HO success rate improvement |
| Pipeline demo-ready for Nicolas: all 5 CSVs load, env boots from relation data, arch diagram | All | Nicolas can screen-share the running pipeline without embarrassment |
| Wire relation-level CSV as env data source via YAML config path | Devika | `config.yaml` points to CSV, env loads it |

### Week 3 (Jun 9 - Jun 13): Train + measure

| Task | Who | Done when |
|------|-----|-----------|
| PPO training loop (SB3, CPU, 5 seeds) | Harshit | Training curve shows improvement over random in 5/5 seeds |
| Baseline comparison: random policy vs trained on same env | Ananyaa | Table: HO success %, failure %, ping-pong % — random vs trained |
| Streamlit dashboard: training curves + KPI comparison | Devika | `streamlit run dashboard.py` shows live charts |
| MLflow logging (optional but nice): track experiments | Shourya | Experiments visible in MLflow UI |

### Week 4 (Jun 16 - Jun 20 + Jun 23-27): Ship + polish

| Task | Who | Done when |
|------|-----|-----------|
| Docker container: `docker build && docker run` reproduces training | Shourya | README instructions work on a clean machine |
| Before/after chart: cell-level and relation-level KPI improvement | Ananyaa | The one chart that sells the platform to any operator VP |
| End-to-end test: fresh CSV -> train -> evaluate -> dashboard | Harshit | Script runs unattended, produces results |
| 5-slide deck: problem -> approach -> results -> next steps (reusable for any operator pitch) | Devika | Ready for demo day Jun 27 |
| Stretch: second reward variant for comparison | Anyone with time | Shows methodology rigor |

---

## What Was Cut (and why)

| Cut | Why |
|-----|-----|
| 7 autonomous agents | 200 lines of stubs. Call them "modules." No agent orchestration needed for a training pipeline. |
| Phase 2 (3 reward variants, scenario engine, adversarial) | No time. One working reward variant > three half-built ones. |
| Phase 3 BONUS (ONNX, generalization proof, human-vs-agent) | Fantasy for 4 interns in 4 weeks. |
| EPIC metric from paper | Research project, not an intern deliverable. |
| Leadership rotation | Destabilizing mid-sprint. Ananyaa leads through demo day. |
| "Interns are QA" framing | Interns ARE the developers. Own it. They wrote the code, they should be proud of it. |

---

## Success Criteria (demo day Jun 27)

| Metric | Target | Stretch |
|--------|--------|---------|
| Schema mapper loads all 5 CSVs | Yes | - |
| Env runs on relation-level data | Yes | - |
| PPO beats random baseline | >5% improvement on HO success rate | >10% |
| Before/after chart exists | Yes, for 1 reward variant | 2 variants |
| Docker container runs | Yes | Helm chart |
| Streamlit dashboard | Training curves + KPIs | Live inference |
| Fresh CSV produces results with 0 code changes | Yes (test with shuffled column order) | Different city topology |

---

## The One Thing That Matters

**Build the transition model.** Everything else is plumbing. If `step()` returns realistic state transitions based on CIO changes, PPO will learn. If it returns random noise, nothing else matters.

The transition model approach: for each (source_cell, target_cell) relation, compute the historical distribution of HO outcomes at each CIO value from the 2.2M row CSV. When the agent changes CIO, look up the nearest historical CIO value and sample outcomes from that distribution. Simple, data-driven, no physics model needed.

This is Week 2's task. It is the make-or-break.
