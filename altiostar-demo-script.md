# WINNIIO Altiostar Pre-Workshop Demo — Presentation Script

**Duration:** 25-30 minutes
**Audience:** Soumyadeep Mukherjee + Altiostar/Rakuten Symphony engineering team
**Setup:** Screen share with `python -m http.server 8787` running, browser at localhost:8787/altiostar-tokyo-demo.html
**Notebook:** sionna-tokyo-mro-v3.ipynb open in Colab tab (pre-run, cells expanded)

---

## ACT 1: "This Is Your Network" (5 min)

**[Open Cesium demo — Overview camera]**

> "Let me show you something. This is central Tokyo — your network — rendered with Japan's PLATEAU 3D building data. Every building you see here is from MLIT's open CityGML dataset. 23 million buildings, real measured heights."

**[Click Shinjuku button]**

> "22 towers. Your site database — Shinjuku, Shibuya, Minato, Ikebukuro, all the way to Skytree in Sumida. Three status categories: active, degraded, and your handover-critical corridor sites."

**[Click a tower → info panel opens]**

> "Each tower carries its full engineering context. Band, power, azimuth, tilt, CIO values. Intel COTS hardware — your core differentiator. vDU, vCU, RIC interfaces. E2 for near-real-time, A1 for policy. This isn't a PowerPoint — this is a spatial database."

**[Click "Neighbors: ON"]**

> "Neighbor relationships visualized in 3D. You can immediately see coverage gaps, overlapping sectors, places where the topology doesn't match the terrain."

---

## ACT 2: "Physics, Not Curves" (7 min)

**[Click "Sionna RT: OFF" → turns ON. Select n77]**

> "Now here's where it gets interesting. This overlay isn't Okumura-Hata. This is NVIDIA Sionna — open-source GPU ray-tracing. Apache 2.0 license. A million rays per transmitter, bouncing off concrete and glass with ITU-R P.2040 material properties. Diffraction around building edges. Real physics."

**[Let the 3D extruded coverage load — green/yellow/red pillars]**

> "The height of each cell represents signal strength. Green pillars — strong coverage. Yellow — moderate, handover zone territory. Red — weak, potential failure zones. You're looking at the output of a full ray-tracing simulation, not an empirical model."

**[Switch to n78]**

> "3.5 gig — your n78 band. Different propagation characteristics, different coverage pattern. Same physics engine."

**[Switch to n257]**

> "28 gigahertz millimeter wave. This is where ray-tracing matters most — mmWave is almost entirely line-of-sight. Empirical models can't handle this. You need the buildings, you need the geometry, you need the diffraction. At 28 gig, glass and wet ground materials aren't valid in the ITU model, so we substitute concrete — which is the conservative, correct approach."

---

## ACT 3: "Where Handovers Break" (5 min)

**[Click "Simulate UE"]**

> "Now let's follow a user. This UE is moving from Nishi-Shinjuku south through Shibuya, down the Meguro River corridor — your degraded cell HO-002 — then across to Shinagawa and back up through Minato to Tokyo Station."

**[Watch the simulation — UE moves, serving line changes color]**

> "Watch the serving cell line. Green means clean handover. When it turns red — that's a failure. The UE drops to RLF, has to re-establish. That's your Meguro corridor problem. And here — Shuto Expressway C1 — ping-pong handover. The UE bounces between HO-003 and CTR-002 because the CIO values aren't tuned for that geometry."

**[Click "UE Traces: OFF" → turns ON]**

> "These are five mobility traces from the Sionna notebook. Train route along the Yamanote Line — Shibuya to Ikebukuro. Shuto Expressway at 80 km/h. Pedestrian in Ginza. Each one samples RSRP from the ray-traced coverage map at every 50 meters and classifies every handover event: success, failure, or ping-pong."

---

## ACT 4: "The Numbers" (5 min)

**[Switch to Colab tab — scroll to ROI Calculator cell output]**

> "Let's talk business impact. Your network: 50,000 sites, 10 million subscribers. 80 million handover events per day. At a 2.5% failure rate — which is typical for a dense urban deployment without ML optimization — that's 2 million failures per day."

> "With an ML-optimized CIO policy trained in this digital twin, industry benchmarks show you can get below 0.5%. That's 1.6 million fewer failures per day. Even at a conservative cost model — half a yen per failure blended across NOC triage, churn risk, and QoE degradation — that's billions of yen annually."

> "And the churn reduction alone — 0.1% improvement in retention from better handover experience — that's tens of billions in lifetime value."

> "The Phase 1 + Phase 2 engagement is EUR 25,000. The ROI is measured in days, not months."

---

## ACT 5: "How We Get There" (5 min)

**[Scroll to Competitive Positioning cell]**

> "You could use Atoll — great tool, we've used it ourselves. But Atoll is empirical propagation. No ray-tracing, no digital twin, no RL integration. AWE Communications has ray-tracing but no ML pipeline and it's proprietary. Building it in-house on your RCP platform is possible, but it's 6-12 months and dedicated headcount diverted from your core RAN roadmap."

> "What we bring is the methodology to get you from where you are today to a calibrated, ML-ready digital twin in 90 days. Open stack — Sionna, PLATEAU, CesiumJS, Stable Baselines3. Runs on your Intel COTS hardware with NVIDIA GPU. No lock-in. Every component is swappable."

**[Scroll to 90-Day Success Criteria]**

> "Day 0-15: we run a SPIN Twinning workshop — that's Situation, Problems, Implications, Needs — using THIS notebook as the canvas. Your engineers walk through the simulation, we agree on what's real, what's missing, and what matters. You give us your site database, antenna files, and MDT data."

> "Day 15-60: we calibrate. PLATEAU LOD2 buildings with real roof geometry. Your actual antenna patterns instead of our approximation. RMSE below 8 dB against your drive test data. RL agent trained and running in shadow mode."

> "Day 60-90: we validate. A/B comparison — simulated vs. real handover statistics. If the correlation is above 0.8, we scope Phase 3 together based on evidence, not assumptions."

---

## ACT 6: "What You're Looking At" (3 min)

**[Switch back to Cesium demo — Overview]**

> "Everything you've seen today is open source. The notebook runs end-to-end on a free Colab T4 GPU. The Cesium viewer is Apache 2.0. The buildings are Japanese government open data. The RF simulation is NVIDIA's own open-source engine."

> "What we add is the methodology — SMILE — Sustainable Methodology for Impact Lifecycle Enablement. The notebook and the viewer are tools. The SPIN Twinning workshop is the deliverable. We don't scope what we haven't understood."

> "The question for your team is: what should we look at first? Which cluster, which KPIs, which failure modes matter most to you? That's what Phase 1 is for."

**[Pause for questions]**

---

## HANDLING OBJECTIONS

**"This is synthetic data"**
> "Exactly — and that's intentional. We built the full pipeline with representative data so you can see the methodology. Phase 1 swaps in YOUR real data. The calibration cell is ready — CSV in, RMSE out. Garbage in, garbage out applies to every simulation tool. The difference is this one is transparent."

**"How does this integrate with RCP?"**
> "The trained model deploys as an xApp on your near-RT RIC via E2 interface, or as an rApp on non-RT RIC via A1. We're not replacing your orchestration — we're feeding it better decisions. The simulation environment is for training; production runs on your stack."

**"Why not just use NVIDIA Aerial?"**
> "Aerial is excellent — but it requires Omniverse licensing, significant GPU infrastructure, and NVIDIA ecosystem commitment. We use Sionna, which is NVIDIA's own open-source component, without the Omniverse dependency. If you want to upgrade to Aerial in Phase 3, the scene data and pipeline carry over. Zero lock-in."

**"What's your team's telecom experience?"**
> "We've worked with Nokia Bell Labs on 3D scene reconstruction for RAN — Gaussian splatting for radio environment mapping. We co-chair the Digital Twin Consortium's Telecom Working Group. And our expert network includes Lars Harrie at Lund University for CityGML, Dan Isaacs the CTO of the Digital Twin Consortium, and the NVIDIA Sionna team directly."

**"EUR 25K for a workshop seems expensive"**
> "EUR 5K is the workshop — half a day. The other EUR 20K is the concurrent engineering sprint — one month of building the calibrated twin with your data. But let me reframe: one ping-pong handover event on the Shuto Expressway loop, multiplied by every subscriber who drives that route every day, costs you more in NOC triage and churn risk than the entire Phase 1+2 engagement. The question isn't the cost — it's the speed to insight."
