from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import json
import pandas as pd
import streamlit as st

from src.pipeline.kpi_extractor import extract_all_kpis

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Altiostar MRO Dashboard",
    page_icon="📡",
    layout="wide",
)

st.title("📡 Altiostar MRO: Training Pipeline Dashboard")
st.caption("Phase 1 · Rakuten Japan · 75-cell cluster · Shibuya area")

# ── Load data ──────────────────────────────────────────────────────────────────
@st.cache_data
def load_kpis() -> pd.DataFrame:
    df = pd.read_csv("data/synthetic/pm_data_april2026.csv")
    return extract_all_kpis(df)


@st.cache_data
def load_baseline() -> dict:
    baseline_path = Path("results/random_baseline.json")
    if baseline_path.exists():
        with open(baseline_path) as f:
            return json.load(f)
    return {}


kpis = load_kpis()
baseline = load_baseline()
problem_cells = kpis[kpis["ho_success_rate_pct"] < 96]

# ── Row 1 — Cluster summary metrics ───────────────────────────────────────────
st.header("Cluster Summary")
col1, col2, col3, col4 = st.columns(4)
col1.metric(
    "Cluster HO Success",
    f"{kpis['ho_success_rate_pct'].mean():.2f}%",
    delta=f"{kpis['ho_success_rate_pct'].mean() - 99:.2f}% vs 99% target",
    delta_color="normal",
)
col2.metric(
    "Problem Cells",
    len(problem_cells),
    delta=f"{len(problem_cells)} of 75 cells",
    delta_color="normal",
)
col3.metric(
    "Avg Ping-Pong Rate",
    f"{kpis['pingpong_rate_pct'].mean():.2f}%",
)
col4.metric(
    "Gap to Target",
    "2.77%",
    delta="PPO agent needs to close this",
    delta_color="normal",
)

st.divider()

# ── Row 2 — KPI table ──────────────────────────────────────────────────────────
st.header("KPI Table — All 75 Cells")
st.dataframe(
    kpis.style.highlight_between(
        subset=["ho_success_rate_pct"], left=0, right=96, color="#ff6b6b"
    ).format("{:.2f}"),
    use_container_width=True,
)

st.divider()

# ── Row 3 — Problem cells ──────────────────────────────────────────────────────
st.header(f"⚠️ Problem Cells ({len(problem_cells)} cells below 96%)")
st.dataframe(
    problem_cells.style.format("{:.2f}"),
    use_container_width=True,
)

st.divider()

# ── Row 4 — Training Curves ────────────────────────────────────────────────────
st.header("Training Curves (Live — Phase 1)")

training_results_path = Path("results/training_results.json")

if training_results_path.exists():
    with open(training_results_path) as f:
        training = json.load(f)
    rewards = training.get("episode_rewards", [])
    if rewards:
        chart_df = pd.DataFrame({"Episode": range(len(rewards)), "Reward": rewards})
        st.line_chart(chart_df.set_index("Episode"))
else:
    st.info("⏳ Waiting for Shourya's PPO training run. File expected at results/training_results.json", icon="📈")

col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Random Policy Baseline")
    if baseline:
        st.metric("Cluster HO Success", f"{baseline['cluster_ho_success_rate_pct']:.2f}%", delta=f"{baseline['cluster_ho_success_rate_pct'] - 99:.2f}% vs 99% target", delta_color="normal")
        st.metric("Problem Cells HO Success", f"{baseline['problem_cells_ho_success_rate_pct']:.2f}%")
        st.metric("Normal Cells HO Success", f"{baseline['normal_cells_ho_success_rate_pct']:.2f}%")
        st.metric("Ping-Pong Rate", f"{baseline['cluster_pingpong_rate_pct']:.2f}%")
        st.metric("Mean Reward per Step", f"{baseline['cluster_mean_reward_per_step']:.2f}")
    else:
        st.warning("results/random_baseline.json not found")

with col_b:
    st.subheader("Trained PPO Agent")
    st.info("Pending — Track A output")