# Speaking Script: AltioStar MRO Platform Migration & Agentic Backend Work Plan
**Target Audience:** Danial & Ahsan (WINNIIO / LifeAtlas)
**Presenter:** Shourya Solanki (Team Lead)
**Goal:** Present the unified architecture, engineering roadmap, 3-month timeline, and task assignments for evolving the MRO platform from Streamlit to Next.js + FastAPI + Supabase with a LangGraph supervisor.

---

## Part 1: Context & Current State (0:00 - 1:30)
> **Visual:** Title slide and "Where We Are" table.

* **What to say:**
  "Good morning Danial, Ahsan. Today, I'm excited to present our team's unified work plan to scale the AltioStar 5G Mobility Robustness Optimization platform. 
  As of today, our core PPO reinforcement learning pipeline is fully functional and stable. We've completed our initial training sweeps across 16 different geographies and 763 relations, achieving a convergent **99.99% handover success rate** and a **0.00% ping-pong rate**, passing all 262 verification tests.
  We demonstrated this Streamlit-based MVP to Nicolas, Claus, and Soumyadeep from Rakuten. Soumyadeep was highly impressed, calling it 'a very good platform.' He gave us specific feedback, and we have already delivered two critical pieces: relation-level granularity in the telemetry data, and the per-relation CIO delta before-and-after export.
  However, Streamlit is a single-threaded frontend-heavy MVP stack that cannot scale to a multi-user, secure production system. To move forward, Nicolas has approved two parallel workstreams: a Platform Migration to a Next.js/FastAPI decoupled architecture, and an Agentic Backend using LangGraph."

---

## Part 2: Workstream 1 — Agentic Backend (1:30 - 3:30)
> **Visual:** "Brain + Reflex" Architecture table and the 4 Agents diagram.

* **What to say:**
  "Let's look at the Agentic Backend. Currently, the PPO pipeline is a 'reflex'—it is brilliant at mathematical optimization through trial and error, but it has no reasoning capability, cannot audit its actions, and cannot read external standards. 
  We are adding a 'Brain' layer on top of this reflex using a LangGraph supervisor loop. We will build four specialized agents:
  1. **The Supervisor:** This is the coordinator. It maintains execution states and uses a PostgreSQL checkpointer to save state histories. Crucially, it provides an 'interrupt gate' so that before any model action is deployed to the cell towers, it pauses and awaits human approval.
  2. **The Spectrum Agent:** This agent monitors the 3GPP portal, TM Forum, and O-RAN Alliance. It scrapes spec documents and embeds standards updates directly into our vector store.
  3. **The Explainer Agent:** It translates complex PPO parameter changes into plain-English auditable reports—answering the client's core question of *why* and *how* the parameters were modified.
  4. **The NOC Copilot:** This is our proposed addition. It is a conversational AI assistant that lets network engineers ask natural language questions about cluster health, query live KPI data, and get direct root-cause recommendations."

---

## Part 3: Workstream 2 — Platform Migration (3:30 - 5:00)
> **Visual:** Tech Stack table and "Current vs Target" architecture map.

* **What to say:**
  "To support this brain, we need to migrate the platform infrastructure. We are moving from a single-threaded Python process to a fully decoupled stack:
  * On the **Frontend**, we are migrating from Streamlit to Next.js (React) to support modern, responsive layouts and multi-user sessions.
  * For the **Backend API**, we are exposing FastAPI endpoints to run REST and WebSockets.
  * For the **Database & Auth**, we are moving from local files to Supabase (PostgreSQL + pgvector) with JWT role-based access.
  * For the **RL Backend**, the model will run as an isolated FastAPI microservice, meaning PPO runs independently of the web server.
  We are keeping our tech stack 100% open-source to avoid vendor lock-in, pinning LangGraph core to `0.3.x` for stability and completely avoiding license traps like n8n."

---

## Part 4: 3-Month Timeline & Milestones (5:00 - 6:30)
> **Visual:** 3-Month Timeline grid and Key Milestones list.

* **What to say:**
  "We have structured a smallest-effort-first schedule over a 3-month period, ensuring a testable demo is ready at the end of each month:
  * **Month 1 (Foundation):** We will set up the FastAPI project skeleton, implement `/infer` and `/retrain` endpoints, establish the Supabase schema, and build the LangGraph supervisor and Explainer stubs.
  * **Month 2 (Integration):** We will replace stubs with the real SB3 PPO model behind FastAPI, expose the model endpoints as MCP tools, compile the Next.js frontend with our WINNIIO design system, and implement Supabase authentication.
  * **Month 3 (Go-Live):** We will launch the conversational NOC Copilot, integrate end-to-end tracing, deploy the frontend to Vercel and the API to Railway, run validation audits, and retire the Streamlit app.
  Our key milestone targets include an API demo in Week 2, a supervisor loop demo in Week 8, and the Next.js platform release in Week 10."

---

## Part 5: Open Questions & Discussion (6:30 - 7:30)
> **Visual:** Discussion Points list.

* **What to say:**
  "To kickstart Week 1 on the right foot, we would like to align on five open questions:
  1. *Approval Scope:* Should the Supervisor agent prompt for human approval on *every* single CIO change, or only those that exceed a safety threshold (e.g. delta > 2dB)?
  2. *Explainer Latency:* Is the target for the Explainer real-time per-action reports, or batch daily summaries?
  3. *Deployment Target:* Does Rakuten prefer their model hosted directly inside their RIC, or standalone in a cloud-hosted Kubernetes pod?
  4. *Compliance Framing:* What exact TM Forum framework (e.g. GB1059) does Soumyadeep expect for our next demonstration?
  5. *Page Prioritization:* Out of the 7 Streamlit pages, are there any that we should deprioritize for the initial Next.js MVP launch?
  I'd love to open the floor to discuss these items and get your feedback on the timeline. Thank you."
