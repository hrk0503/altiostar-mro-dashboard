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

## Slide 2: The Ingestion Data Pipeline (0:30 - 1:30)
> **Visual:** Data engineering slide (Schema Mapper, 2.2M compilation, Caching)

* **What to say:**
  "Let's start with the data pipeline. We ingest four raw CSV files from the operator: the site database, neighbor relations, PM counters, and KPI summaries.
  Our first challenge was that columns vary across operators. To make this pipeline reusable, we built the **Schema Mapper** (`schema_mapper.py`). It uses set-based signatures—checking if expected keys are subsets of the CSV columns—which means the pipeline is completely immune to column shuffling. If an operator swaps columns around, it still maps and loads perfectly with zero code changes.
  We compile these files into a unified 2.2M-row relation-level PM dataset. To ensure the RL environment can boot and step instantly, we implemented a **double-caching store**. The grouped slices are cached in memory so that env transitions take less than a millisecond, cutting training prep from minutes to under 50 milliseconds."

---

## Slide 3: Gymnasium Environment Simulation (1:30 - 2:30)
> **Visual:** Under-the-hood simulation (9D observation, continuous action, nearest CIO sampling)

* **What to say:**
  "The core of our pipeline is the digital twin, which is a Gymnasium reinforcement learning environment (`mro_env.py`).
  Under the hood, the observation space is a 9-dimensional vector per neighbor relation. It tracks handover attempts, successes, failures (categorized as too early, too late, or wrong cell), ping-pongs, and signal quality (RSRP/SINR).
  The action space consists of continuous CIO delta modifications bounded to `[-2.0, 2.0]` dB.
  To simulate network transitions, we chose a **data-driven lookup model** instead of a slow physics-based radio propagation model. When the PPO agent takes a CIO delta action, the env performs an $O(1)$ binary search on our cached PM records to find the nearest historical CIO value and samples outcomes directly from that real distribution. This gives us high-fidelity simulator steps that execute in microseconds."

---

## Slide 4: Reward Tuning & Ship Gate (2:30 - 3:30)
> **Visual:** Model safety (v2 Rate-Based reward, barrier functions, ship_gate.py)

* **What to say:**
  "To guide the agent's policy, we engineered the **v2 Rate-Based Reward function**. It uses percentage rates to keep rewards bounded: $Reward = HOSR - (FailureRate \times 5.0) - (PPRate \times 2.0)$.
  We also introduced **asymmetric boundary penalties** acting as barrier functions. If the Handover Success Rate falls below $95\%$, or the Ping-Pong rate exceeds $5\%$, the agent receives severe negative rewards. This teaches the agent to stay within safe operational boundaries.
  For final validation, we built `ship_gate.py`. It is a strict validator that evaluates the JSON output of our training runs. It requires HOSR to be strictly $>99.0\%$ and Ping-Pongs $<5.0\%$ to pass. It runs automatically, outputting exit codes that gate our CI/CD merges."

---

## Slide 5: Multi-Agent System Architecture (3:30 - 4:30)
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

## Slide 6: Results & ONNX Export (4:30 - 5:00)
> **Visual:** Phase 3 results (99.99% HOSR, ONNX, and test passes)

* **What to say:**
  "Finally, the results: Our 100k step sweep successfully converges to a baseline Handover Success Rate of **`99.99%`** and a Ping-Pong rate of **`0.00%`**, compared to the random baseline of `79.25%`. This represents a **`+20.74%`** absolute improvement, fully passing the G4 ship gate.
  We've also built `export_onnx.py` which exports this trained checkpoint to ONNX format with tensor clamping. This makes it ready for immediate deployment in CU-CP Kubernetes pods at the baseband. All 262 regression tests are green.
  The pipeline is complete, containerized, and fully validated. I'd love to hear your thoughts."
