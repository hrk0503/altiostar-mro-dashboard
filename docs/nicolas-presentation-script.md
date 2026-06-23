# Presentation Script: Altiostar MRO Deep-Dive
**Target Audience:** Nicolas (CEO/PO)
**Goal:** Demonstrate engineering depth, data pipeline robustness, Gymnasium mechanics, and multi-agent roles.

---

## Slide 1: Title & Overview (0:00 - 0:30)
> **Visual:** Title slide ("5G MRO RL Pipeline Deep-Dive")

* **What to say:**
  "Hi Nicolas. Today, I'm going to take you under the hood of the Altiostar 5G Mobility Robustness Optimization (MRO) training pipeline. 
  Instead of presenting just a one-shot proof-of-concept, we have built a **fully automated, reusable training machine**. It ingests raw operator CSVs, maps them dynamically, runs a data-driven simulation environment, trains a PPO reinforcement learning agent, verifies it against strict ship gates, and outputs K8s-ready ONNX models. 
  Let's walk through how the data flows from raw files to trained policy."

---

## Slide 2: SPIN Context — Situation & Problems (0:30 - 1:00)
> **Visual:** Bullet list detailing Situation (O-RAN CU/DU disaggregation, high-density 5G Shibuya/Shinjuku cells) and Problems (suboptimal CIOs triggering handover anomalies, empirical models unable to capture blockages).

* **What to say:**
  "To provide the industry context, let's look at the Situation and Problems using the SPIN framework.
  **First, the Situation:** The cellular industry is shifting towards disaggregated Open Radio Access Networks (O-RAN), splitting baseband processing into vCU, vDU, and RIC nodes. At the same time, operators are deploying dense, high-frequency 5G clusters (sub-6 GHz n77/n78 and mmWave n257) in high-traffic corridors like Tokyo. Handovers occur constantly as subscribers travel on trains and expressways.
  **Second, the Problems:** Traditional manual parameter tuning is empirical and too slow. Suboptimal Cell Individual Offsets (CIO) trigger handover anomalies like too-early or too-late handovers, causing dropped calls or resource-wasting Ping-Pongs. Furthermore, standard empirical formulas (like Okumura-Hata) cannot model complex building blockages for high-frequency 28 GHz mmWave signals."

---

## Slide 3: SPIN Context — Implications & Needs (1:00 - 1:30)
> **Visual:** Bullet list detailing Implications (2 million dropped calls daily, high OPEX, subscriber churn) and Needs (automated real-time CIO tuning, data-driven GPU ray-traced twins, automated Ship Gates).

* **What to say:**
  "Now let's examine the Implications and Needs:
  **Third, the Implications:** Handover issues have massive business impacts. A minor 2.5% handover failure rate translates to 2 million dropped connections daily in a major metropolis like Tokyo. Manual drive testing and NOC triage overhead inflate operational costs (OPEX), while call drops damage operator reputation and drive subscriber churn to competitors.
  **Fourth, the Needs:** Operators need near-real-time automated optimization to dynamically compute and update CIO offsets per relation at millisecond scales. To do this safely, we need a high-fidelity, physics-informed digital twin to train and test Reinforcement Learning policies before deploying them to live baseband nodes, overseen by automated validation gates to guarantee SLA compliance."

---

## Slide 4: The Ingestion Data Pipeline (1:30 - 2:30)
> **Visual:** Data engineering slide (Schema Mapper, 2.2M compilation, Caching)

* **What to say:**
  "Let's start with our data ingestion pipeline. We ingest four raw CSV files from the operator: the site database, neighbor relations, PM counters, and KPI summaries.
  Our first challenge was that columns vary across operators. To make this pipeline reusable, we built the **Schema Mapper** (`schema_mapper.py`). It uses set-based signatures—checking if expected keys are subsets of the CSV columns—which means the pipeline is completely immune to column shuffling. If an operator swaps columns around, it still maps and loads perfectly with zero code changes.
  We compile these files into a unified 2.2M-row relation-level PM dataset. To ensure the RL environment can boot and step instantly, we implemented a **double-caching store**. The grouped slices are cached in memory so that env transitions take less than a millisecond, cutting training prep from minutes to under 50 milliseconds."

---

## Slide 5: Gymnasium Environment Simulation (2:30 - 3:30)
> **Visual:** Under-the-hood simulation (9D observation, continuous action, nearest CIO sampling)

* **What to say:**
  "The core of our pipeline is the digital twin, which is a Gymnasium reinforcement learning environment (`mro_env.py`).
  Under the hood, the observation space is a 9-dimensional vector per neighbor relation. It tracks handover attempts, successes, failures (categorized as too early, too late, or wrong cell), ping-pongs, and signal quality (RSRP/SINR).
  The action space consists of continuous CIO delta modifications bounded to `[-2.0, 2.0]` dB.
  To simulate network transitions, we chose a **data-driven lookup model** instead of a slow physics-based radio propagation model. When the PPO agent takes a CIO delta action, the env performs an $O(1)$ binary search on our cached PM records to find the nearest historical CIO value and samples outcomes directly from that real distribution. This gives us high-fidelity simulator steps that execute in microseconds."

---

## Slide 6: Reward Tuning & Ship Gate (3:30 - 4:30)
> **Visual:** Model safety (v2 Rate-Based reward, barrier functions, ship_gate.py)

* **What to say:**
  "To guide the agent's policy, we engineered the **v2 Rate-Based Reward function**. It uses percentage rates to keep rewards bounded: $Reward = HOSR - (FailureRate \times 5.0) - (PPRate \times 2.0)$.
  We also introduced **asymmetric boundary penalties** acting as barrier functions. If the Handover Success Rate falls below $95\%$, or the Ping-Pong rate exceeds $5\%$, the agent receives severe negative rewards. This teaches the agent to stay within safe operational boundaries.
  For final validation, we built `ship_gate.py`. It is a strict validator that evaluates the JSON output of our training runs. It requires HOSR to be strictly $>99.0\%$ and Ping-Pongs $<5.0\%$ to pass. It runs automatically, outputting exit codes that gate our CI/CD merges."

---

## Slide 7: Multi-Agent System Architecture (4:30 - 5:30)
> **Visual:** Agent execution roles (Atlas, Pipeline, Spectrum, Forge, Deploy, Lens, Sentinel)

* **What to say:**
  "Behind the code is a structured multi-agent architecture where agents generate work and humans act as QA:
  * **Atlas** manages the scrum backlog and daily reports.
  * **Pipeline** handles CSV ingestion and schema mapping.
  * **Spectrum** validates RF domain constraints and CIO boundaries.
  * **Forge** orchestrates the Gymnasium environment and training runs.
  * **Deploy** handles Docker containerization and K8s targeting.
  * **Lens** powers the Streamlit dashboard, presentations, and reports.
  * **Sentinel** runs property-based testing and verifies the ship gate.
  This orchestration ensures that every module is built to external standards."

---

## Slide 8: O-RAN MRO Technical Architecture (5:30 - 6:00)
> **Visual:** Full-screen end-to-end system architecture diagram showing Raw Ingest -> Cache -> Gymnasium Simulator -> PPO Training -> Ship Gate -> ONNX Exporter -> K8s target.

* **What to say:**
  "Now that we've seen the human roles, let's look at the technical architecture of our system. 
  This diagram displays the closed-loop workflow we have built. It starts with raw operator CSV ingestion on the top left, maps the schema automatically, compiles the relation PM records, and caches them in memory.
  This cache feeds our Gymnasium simulator, which transitions states via database lookups. The PPO reinforcement learning policy interacts with this environment, computing continuous CIO offset actions. 
  Before final deployment, every trained model is evaluated by our Ship Gate validator. If it passes, it is exported as an ONNX model targeted for Kubernetes pods at the baseband. Let's break down each block."

---

## Slide 9: Technical Pipeline Architecture Breakdown (6:00 - 6:30)
> **Visual:** Bullet list detailing: Raw Ingest & Schema Mapper, In-Memory Double Cache Slices, Gymnasium RL Simulator, and PPO Sweep & Ship Gate Validation.

* **What to say:**
  "Let's look under the hood of these architectural blocks.
  First, **Raw Ingestion & Schema Mapper**: We read PM counters, site databases, and neighbor relation CSVs. The Schema Mapper maps columns dynamically using order-independent set signature matching, ensuring the ingestion is completely robust against shuffled or modified column files.
  Second, the **In-Memory Double Cache**: Slicing and caching our 2.2M compiled relation-level PM records reduces environment boot and transition lookup times to under 50 microseconds.
  Third, the **Gymnasium RL Simulator**: It uses continuous CIO actions bounded to `[-2.0, 2.0]` dB delta and exposes a 9D observation space (HOSR, failures, ping-pongs, signal quality).
  Fourth, the **PPO Sweep & Ship Gate**: Stable-Baselines3 PPO models are optimized using Optuna swept parameters across 4 variants. A strict Ship Gate validator ensures SLA targets are met before ONNX model export with PyTorch output clamping is performed."

---

## Slide 10: Streamlit Management Dashboard - Overview & Health (6:30 - 7:00)
> **Visual:** Dashboard screenshot showing cell health distribution donut chart (23 Healthy, 46 Warning, 6 Critical) and active KPIs.

* **What to say:**
  "Now, let's transition to the operation and monitoring front. To present these capabilities to you and the team, we built an interactive Streamlit management dashboard.
  As you can see from this screen, the home page provides a high-level view of our cluster's health. The donut chart visualizes our 75-cell cluster in Shibuya: 23 cells are completely healthy, 46 cells are in a warning state, and 6 are in a critical state.
  Below that, it lists the degraded cells by health category. This allows our operations team to identify problematic sectors at a glance and prioritize engineering efforts where handovers fail most frequently."

---

## Slide 11: Interactive Cell Map & Site Inspector (7:00 - 7:30)
> **Visual:** Map visualization of Shibuya cluster with connection lines and cell inspector panel on the right.

* **What to say:**
  "Next, we have the geographic Cell Map. This is a spatial representation of the 75 cells across Shibuya.
  It overlays neighbor relation vectors directly onto the map as lines connecting neighboring sites. This makes it easy to visualize network topology, coverage overlaps, and geographic density.
  On the right-hand panel, we have a site inspector. By selecting any cell—such as `RKSB-001-1` here—the operator gets a real-time drill down of its radio parameters: HOSR, failure rates, signal metrics like RSRP and SINR, PRB usage, and neighbor relation offset tables. This bridges geographic placement with analytical metrics."

---

## Slide 12: RL Variant Comparison & Performance Heatmap (7:30 - 8:00)
> **Visual:** Stacked charts showing Handover Success Rate comparison bar chart (top) and Multi-Metric radar fingerprint & scenario performance heatmap (bottom).

* **What to say:**
  "For model evaluation, we built a comparison dashboard that pitches our four agent variants—v0 to v3—against each other across different stress scenarios.
  On the top chart, you can see how the models perform against the 99% SLA target (the dotted red line) and the 79.2% random baseline (the dotted grey line). In normal baseline and rain fade scenarios, all agents perform at a near-perfect 99.99% success rate.
  Below, we display the multi-metric radar fingerprint. It doesn't just evaluate HOSR; it evaluates ping-pongs, too-early handovers, too-late handovers, and wrong-cell handovers simultaneously. The performance heatmap on the right makes it instantly clear how each variant handles extreme situations like rush hour or tower failure."

---

## Slide 13: Real-Time RL Simulation & Sandbox (8:00 - 8:30)
> **Visual:** RL simulation control page showing live parameters, cluster success rate (98.85%), cumulative rewards, and variant leaderboard.

* **What to say:**
  "Finally, we created a Real-Time RL Simulation sandbox. Here, operators can simulate active network scenarios in real-time.
  On this screen, you can see the simulation step telemetry: we are at step 15, the cluster HOSR is at 98.85%, and there are 5 active problem cells.
  The right side allows interactive adjustment of scenario parameters like UE load, RSRP offsets, and failure multipliers. The best variant leaderboard on the bottom right tracks which model is predicting the best outcome—currently showing v0 as best-in-class for the baseline scenario at 99.99%. This sandbox is perfect for training operators and testing agent reactions."

---

## Slide 14: Tokyo 3D Digital Twin Simulation (8:30 - 9:00)
> **Visual:** Full-screen high-fidelity 3D simulation of Tokyo network (Shinjuku and Shibuya areas) rendering macro site towers, serving corridors, and NVIDIA Sionna ray-traced coverage maps.

* **What to say:**
  "Next, I want to showcase the spatial twin of our network: the CesiumJS-based 3D Digital Twin.
  As you can see on this screen, we've modeled the 3D building geometry of Tokyo's densest areas—covering Shibuya, Shinjuku, and Minato-ku. The map displays our cell towers, sectors, neighbor relations, and simulated user equipment mobility paths. 
  This interactive sandbox allows us to visualize how geographic structure and real-world physics impact network KPIs."

---

## Slide 15: 3D Digital Twin — Under the Hood (9:00 - 9:30)
> **Visual:** Bullet list detailing: Urban Spatial Database, NVIDIA Sionna Ray-Tracing, UE Mobility Corridor, and Business ROI.

* **What to say:**
  "Under the hood, the 3D twin operates on four key pillars.
  First, it's an **Urban Spatial Database**. It loads 22 macro sites with full engineering specifications like antenna azimuths, heights, and tilts.
  Second, it uses **NVIDIA Sionna Ray-Tracing**. We don't rely on simplistic empirical coverage models. Instead, we cast millions of radio rays bouncing off building surfaces with real material properties. This is crucial for mmWave n257 bands where buildings create severe coverage blockages.
  Third, it simulates **UE Mobility and Handovers**. It models subscribers moving along real transport corridors like the Yamanote Line, tracking serving towers in green and radio link failures in red.
  And finally, the **Business ROI**: by using reinforcement learning to optimize offsets within this 3D environment, we drop handover failures from 2.5% to 0.5%—saving billing revenue and reducing NOC triage costs."

---

## Slide 16: Results & ONNX Export (9:30 - 10:00)
> **Visual:** Phase 3 results (99.99% HOSR, ONNX, and test passes)

* **What to say:**
  "In summary, the results: Our 100k step sweep successfully converges to a baseline Handover Success Rate of **`99.99%`** and a Ping-Pong rate of **`0.00%`**, compared to the random baseline of `79.25%`. This represents a **`+20.74%`** absolute improvement, fully passing the G4 ship gate.
  We've also built `export_onnx.py` which exports this trained checkpoint to ONNX format with tensor clamping. This makes it ready for immediate deployment in CU-CP Kubernetes pods at the baseband. All 262 regression tests are green.
  The pipeline is complete, containerized, and fully validated. I'd love to hear your thoughts."
