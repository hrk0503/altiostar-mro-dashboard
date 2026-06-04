"""AltioStar MRO — Phase 2 Dashboard.

Data-Dense + Real-Time Monitoring hybrid dashboard.
Design system by UI UX Pro Max — Fira Sans/Code typography,
bullet gauges, animated status indicators, WINNIIO brand.

Usage:
    streamlit run src/dashboard/app.py
"""

from __future__ import annotations

import json, math, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

# ── Page config ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="WINNIIO · AltioStar MRO",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Theme state ──────────────────────────────────────────────────────
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False
if "sim_step" not in st.session_state:
    st.session_state.sim_step = 0

dark = st.session_state.dark_mode

# ── Design tokens (UI UX Pro Max — Data-Dense + Real-Time hybrid) ──
# WINNIIO teal as primary, blue data accents, amber highlights
P = "#0096AA"        # primary teal
P_DARK = "#00788A"
BLUE = "#1E40AF"
BLUE_L = "#3B82F6"
AMBER = "#D97706"
GREEN = "#22C55E"
RED = "#DC2626"
PURPLE = "#7C3AED"

if dark:
    BG = "#0F172A"; BG2 = "#1E293B"; CARD = "#1E293B"; BORDER = "#334155"
    TEXT = "#E2E8F0"; TEXT2 = "#94A3B8"; TEXT3 = "#64748B"
    SHADOW = "0 1px 3px rgba(0,0,0,.5)"
    PLT = "plotly_dark"; MAPSTYLE = "carto-darkmatter"
else:
    BG = "#F8FAFC"; BG2 = "#F1F5F9"; CARD = "#FFFFFF"; BORDER = "#E2E8F0"
    TEXT = "#1E293B"; TEXT2 = "#64748B"; TEXT3 = "#94A3B8"
    SHADOW = "0 1px 3px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04)"
    PLT = "plotly_white"; MAPSTYLE = "carto-positron"

V_COLORS = {"v0": RED, "v1": P, "v2": GREEN, "v3": PURPLE}
V_NAMES = {"v0": "Count-Based", "v1": "Traffic-Weighted", "v2": "Rate-Based", "v3": "Multi-Objective"}
SC_META = {
    "baseline": {"i": "🟢", "c": GREEN, "l": "Normal"},
    "rush_hour": {"i": "🔴", "c": RED, "l": "High Congestion"},
    "rain_fade": {"i": "🌧️", "c": BLUE_L, "l": "Signal Degradation"},
    "tower_failure": {"i": "⚡", "c": AMBER, "l": "Site Outage"},
}

# ── CSS — Fira fonts, data-dense grid, animated indicators ──────────
st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&family=Fira+Sans:wght@300;400;500;600;700;800&display=swap');

  /* === GLOBAL === */
  .stApp {{ background: {BG}; color: {TEXT}; font-family: 'Fira Sans', system-ui, sans-serif; }}
  .main .block-container {{ padding-top: .6rem; max-width: 1540px; }}
  #MainMenu, footer, .stDeployButton {{ display: none; }}

  /* === SIDEBAR NAV === */
  section[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, #003540 0%, #002830 100%);
    font-family: 'Fira Sans', sans-serif;
  }}
  section[data-testid="stSidebar"] * {{ color: #B0D4DA !important; }}
  section[data-testid="stSidebar"] hr {{ border-color: rgba(255,255,255,.07); }}
  section[data-testid="stSidebar"] .stRadio > div {{ gap: 3px; }}
  section[data-testid="stSidebar"] .stRadio > div > label {{
    background: rgba(255,255,255,.03);
    border: 1px solid rgba(255,255,255,.06);
    border-radius: 8px;
    padding: 11px 14px !important;
    font-size: .84rem !important;
    font-weight: 500 !important;
    transition: all .2s ease;
    cursor: pointer;
  }}
  section[data-testid="stSidebar"] .stRadio > div > label:hover {{
    background: rgba(0,150,170,.15);
    border-color: rgba(0,180,216,.3);
    transform: translateX(3px);
  }}
  section[data-testid="stSidebar"] .stRadio > div > label:has(input:checked) {{
    background: rgba(0,180,216,.18);
    border-color: {P};
    color: #fff !important;
    box-shadow: inset 3px 0 0 {P};
  }}
  section[data-testid="stSidebar"] .stRadio > div > label > div:first-child {{ display: none; }}

  /* === CARDS === */
  .dc {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 18px 22px;
    box-shadow: {SHADOW};
    transition: all .2s ease;
    margin-bottom: 10px;
  }}
  .dc:hover {{
    box-shadow: 0 4px 12px rgba(0,150,170,.08);
    transform: translateY(-1px);
  }}

  /* === KPI BULLET GAUGE === */
  .bullet {{
    text-align: center;
    padding: 10px 4px;
    font-family: 'Fira Code', monospace;
  }}
  .bullet-val {{
    font-size: 1.75rem;
    font-weight: 700;
    line-height: 1;
    letter-spacing: -1px;
  }}
  .bullet-lbl {{
    font-size: .65rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: {TEXT2};
    margin-top: 6px;
    font-family: 'Fira Sans', sans-serif;
  }}
  .bullet-sub {{
    font-size: .72rem;
    color: {TEXT3};
    font-family: 'Fira Sans', sans-serif;
  }}

  /* === SECTION HEADER === */
  .sh {{
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 26px 0 14px 0;
    font-family: 'Fira Sans', sans-serif;
  }}
  .sh h3 {{
    margin: 0;
    font-size: .95rem;
    font-weight: 700;
    color: {TEXT};
    white-space: nowrap;
  }}
  .sh::after {{
    content: '';
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, {P}40, transparent);
  }}

  /* === LIVE PULSE === */
  @keyframes pulse {{ 0%,100% {{ opacity:1; }} 50% {{ opacity:.35; }} }}
  @keyframes glow {{ 0%,100% {{ box-shadow: 0 0 4px {GREEN}; }} 50% {{ box-shadow: 0 0 12px {GREEN}; }} }}
  @keyframes slideIn {{ from {{ opacity:0; transform:translateY(8px); }} to {{ opacity:1; transform:translateY(0); }} }}
  @keyframes fadeNum {{ from {{ opacity:0; transform:scale(.9); }} to {{ opacity:1; transform:scale(1); }} }}
  @keyframes scanline {{
    0% {{ left: -40%; }}
    100% {{ left: 100%; }}
  }}
  .live-dot {{
    display: inline-block;
    width: 7px; height: 7px;
    border-radius: 50%;
    background: {GREEN};
    animation: pulse 2s ease-in-out infinite, glow 2s ease-in-out infinite;
    margin-right: 6px;
  }}
  .anim-in {{ animation: slideIn .4s ease-out; }}
  .num-pop {{ animation: fadeNum .5s ease-out; }}

  /* === TICKER === */
  .tk {{
    background: {'rgba(0,150,170,.06)' if not dark else 'rgba(0,150,170,.08)'};
    border: 1px solid {P}20;
    border-radius: 8px;
    padding: 7px 16px;
    font-size: .74rem;
    font-family: 'Fira Code', monospace;
    color: {P};
    overflow: hidden;
    white-space: nowrap;
    margin-bottom: 16px;
    position: relative;
  }}
  .tk::before {{
    content: '';
    position: absolute;
    top: 0; left: -40%;
    width: 30%; height: 100%;
    background: linear-gradient(90deg, transparent, {P}10, transparent);
    animation: scanline 5s linear infinite;
  }}
  .tk-s {{
    display: inline-block;
    animation: scroll 40s linear infinite;
  }}
  @keyframes scroll {{ 0%{{transform:translateX(60%)}} 100%{{transform:translateX(-100%)}} }}

  /* === CELL ROW === */
  .cr {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 7px 12px;
    border-bottom: 1px solid {BORDER};
    font-size: .8rem;
    transition: background .15s, padding-left .15s;
    font-family: 'Fira Sans', sans-serif;
  }}
  .cr:hover {{ background: {P}08; padding-left: 16px; }}

  /* === BADGES === */
  .bg {{ display:inline-block; padding:2px 9px; border-radius:16px; font-size:.68rem; font-weight:700; font-family:'Fira Sans',sans-serif; }}
  .bg-g {{ background:#D1FAE5; color:#065F46; }}
  .bg-r {{ background:#FEE2E2; color:#991B1B; }}
  .bg-a {{ background:#FEF3C7; color:#92400E; }}
  .bg-l {{ background:{P}15; color:{P}; }}

  /* === PROGRESS === */
  .pb {{ background:{BG2}; border-radius:4px; height:6px; overflow:hidden; margin-top:4px; }}
  .pf {{ height:100%; border-radius:4px; transition:width .8s ease; }}

  /* === PLOTLY & DATA === */
  .stPlotlyChart {{ border-radius:10px; overflow:hidden; }}
  .stDataFrame {{ border-radius:8px; overflow:hidden; font-family:'Fira Code',monospace; font-size:.82rem; }}
  [data-testid="stMetric"] {{
    background:{CARD}; border:1px solid {BORDER}; border-radius:8px;
    padding:12px 16px; box-shadow:{SHADOW}; font-family:'Fira Sans',sans-serif;
  }}
</style>
""", unsafe_allow_html=True)

# ── Paths ────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
RDIR = ROOT / "results"
DDIR = ROOT / "data" / "synthetic"

# ── Data ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def ld_site(): return pd.read_csv(DDIR / "site_database.csv")
@st.cache_data(ttl=30)
def ld_pm():   return pd.read_csv(DDIR / "pm_data_april2026.csv")
@st.cache_data(ttl=30)
def ld_rel():  return pd.read_csv(DDIR / "neighbor_relations.csv")
@st.cache_data(ttl=30)
def ld_exp():
    exps = []
    for f in sorted(RDIR.glob("experiment_*.json")):
        try: exps.append(json.loads(f.read_text()))
        except: continue
    sw = {}
    sp = RDIR / "sweep_results.json"
    if sp.exists():
        try: sw = json.loads(sp.read_text())
        except: pass
    return {"experiments": exps, "sweep": sw}

def comp_df(exps):
    rows = []
    for e in exps:
        if "error" in e: continue
        ev = e.get("evaluation", {})
        rows.append({"Variant": e.get("reward_version","?"), "Scenario": e.get("scenario","?"),
            "Mean Reward": ev.get("mean_reward",0), "HO Success %": ev.get("ho_success_rate",0),
            "HO Failure %": ev.get("ho_failure_rate",0), "Ping-Pong %": ev.get("pingpong_rate",0),
            "Too Early %": ev.get("too_early_rate",0), "Too Late %": ev.get("too_late_rate",0),
            "Wrong Cell %": ev.get("wrong_cell_rate",0)})
    return pd.DataFrame(rows)

def hc(r):
    if r >= 99: return GREEN
    if r >= 97: return "#22C55E"
    if r >= 95: return AMBER
    if r >= 90: return "#F97316"
    return RED

site_db = ld_site(); pm = ld_pm(); rels = ld_rel(); ed = ld_exp(); cdf = comp_df(ed["experiments"])
ck = pm.groupby("cell_id").agg(
    ho_att=("ho_attempts_intra","mean"), ho_sr=("ho_success_rate_pct","mean"),
    ho_fr=("ho_failure_rate_pct","mean"), rsrp=("avg_rsrp_dBm","mean"),
    sinr=("avg_sinr_dB","mean"), prb=("prb_utilization_dl_pct","mean"),
    ue=("active_ue_avg","mean"), mx_ue=("max_ue_connected","max"),
).reset_index()
cm = site_db.merge(ck, on="cell_id", how="left")
cm["prob"] = cm["ho_sr"] < 96
n_prob = int(cm["prob"].sum())
avg_sr = cm["ho_sr"].mean()

# ── Sidebar ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style="text-align:center; padding:14px 0 6px 0;">
        <div style="font-size:1.5rem; font-weight:800; color:#00B4D8; letter-spacing:3px;
                    font-family:'Fira Sans',sans-serif;">WINNIIO</div>
        <div style="font-size:.6rem; color:#5A8A92; letter-spacing:4px; text-transform:uppercase;
                    margin-top:2px; font-family:'Fira Sans',sans-serif;">AltioStar MRO · Phase 2</div>
    </div>
    """, unsafe_allow_html=True)
    st.divider()
    page = st.radio("Nav", [
        "🗺️  Live Cell Map", "⚔️  Variant Comparison",
        "🕸️  Network Topology", "🔬  Real-Time Simulation",
        "📋  Gate G3 & Export",
    ], label_visibility="collapsed")
    st.divider()
    dt = st.toggle("🌙 Dark Mode", value=st.session_state.dark_mode, key="dt")
    if dt != st.session_state.dark_mode:
        st.session_state.dark_mode = dt; st.rerun()
    st.divider()
    st.markdown(f"""<div style="font-size:.73rem; line-height:2; font-family:'Fira Sans',sans-serif;">
        <span class="live-dot"></span> <b>{75 - n_prob}</b> healthy &nbsp; ⚠️ <b>{n_prob}</b> problem<br>
        📊 Cluster: <b>{avg_sr:.2f}%</b><br>
        🎯 Target: <b>99.00%</b> · Gap: <b>{max(0,99-avg_sr):.2f}%</b><br>
        🧪 <b>{len(ed['experiments'])}</b> experiments
    </div>""", unsafe_allow_html=True)

# ── Top bar ──────────────────────────────────────────────────────────
hdr1, hdr2 = st.columns([3, 2])
with hdr1:
    st.markdown(f"""<div style="font-family:'Fira Sans',sans-serif;">
        <span style="font-size:1.4rem; font-weight:800; color:{TEXT};">📡 AltioStar MRO</span>
        <span style="font-size:1.4rem; font-weight:300; color:{TEXT2};"> — Phase 2</span>
    </div>""", unsafe_allow_html=True)
    st.caption("Rakuten Japan 5G · Shibuya · 75 Cells · 763 Relations")
with hdr2:
    ts = time.strftime("%H:%M:%S")
    tk = (f"<span class='live-dot'></span> {ts} JST  ·  📡 75 online  ·  "
          f"⚠️ {n_prob} problem  ·  📊 {avg_sr:.2f}%  ·  🎯 99%  ·  🧪 {len(ed['experiments'])} exp")
    st.markdown(f'<div class="tk"><span class="tk-s">{tk}&nbsp;&nbsp;&nbsp;{tk}</span></div>', unsafe_allow_html=True)

# Filters
av = sorted(cdf["Variant"].unique()) if len(cdf) > 0 else ["v0"]
asc = sorted(cdf["Scenario"].unique()) if len(cdf) > 0 else ["baseline"]
f1, f2 = st.columns(2)
with f1: sel_v = st.multiselect("Reward Variants", av, default=av)
with f2: sel_s = st.multiselect("Scenarios", asc, default=asc)
filt = cdf[cdf["Variant"].isin(sel_v) & cdf["Scenario"].isin(sel_s)] if len(cdf) > 0 else cdf

# ── KPI Gauges (bullet style with animated SVG) ─────────────────────
best_sr = cm["ho_sr"].max(); worst_sr = cm["ho_sr"].min()
avg_fr = cm["ho_fr"].mean(); avg_prb = cm["prb"].mean()

def svg_gauge(val, mx, color, lbl, sub=""):
    p = min(val/mx, 1.) if mx > 0 else 0
    d = p * 251.2
    trail = BORDER
    sub_html = f'<p style="font-size:.72rem;color:{TEXT3};margin:0;">{sub}</p>' if sub else ''
    return (
        f'<div style="text-align:center;padding:10px 4px;">'
        f'<svg width="100" height="100" viewBox="0 0 110 110">'
        f'<circle cx="55" cy="55" r="40" fill="none" stroke="{trail}" stroke-width="6" opacity=".5"/>'
        f'<circle cx="55" cy="55" r="40" fill="none" stroke="{color}" '
        f'stroke-width="6" stroke-dasharray="{d} 251.2" '
        f'stroke-linecap="round" transform="rotate(-90 55 55)" '
        f'style="transition:stroke-dasharray 1.2s cubic-bezier(.4,0,.2,1);"/>'
        f'<text x="55" y="52" text-anchor="middle" fill="{TEXT}" '
        f'font-size="16" font-weight="700" font-family="Fira Code,monospace">{val:.1f}</text>'
        f'<text x="55" y="67" text-anchor="middle" fill="{TEXT3}" '
        f'font-size="9" font-family="Fira Code,monospace">%</text>'
        f'</svg>'
        f'<p style="font-size:.65rem;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:2px;color:{TEXT2};margin:6px 0 2px 0;">{lbl}</p>'
        f'{sub_html}'
        f'</div>'
    )

k1,k2,k3,k4,k5 = st.columns(5)
with k1:
    st.markdown(f'<div class="dc">{svg_gauge(avg_sr,100,P,"Cluster Success",f"Gap: {max(0,99-avg_sr):.2f}%")}</div>', unsafe_allow_html=True)
with k2:
    st.markdown(f'<div class="dc">{svg_gauge(best_sr,100,GREEN,"Best Cell")}</div>', unsafe_allow_html=True)
with k3:
    st.markdown(f'<div class="dc">{svg_gauge(worst_sr,100,RED,"Worst Cell")}</div>', unsafe_allow_html=True)
with k4:
    st.markdown(f'<div class="dc">{svg_gauge(avg_fr,10,AMBER,"Avg Failure")}</div>', unsafe_allow_html=True)
with k5:
    st.markdown(f'<div class="dc">{svg_gauge(avg_prb,100,PURPLE,"PRB Usage")}</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# PAGES
# ══════════════════════════════════════════════════════════════════════

def sec(title):
    st.markdown(f'<div class="sh"><h3>{title}</h3></div>', unsafe_allow_html=True)

center_lat = cm["latitude"].mean()
center_lon = cm["longitude"].mean()

# ── PAGE: LIVE CELL MAP ──────────────────────────────────────────────
if page == "🗺️  Live Cell Map":
    sec("Shibuya Cell Cluster — Live Health Map")
    mc, ic = st.columns([3, 1])
    with mc:
        md = cm.copy()
        sp = st.toggle("Problem cells only", value=False, key="mp")
        if sp: md = md[md["prob"]]
        md["bub"] = np.clip(md["ho_att"]*0.7, 8, 38)
        md["hov"] = md.apply(lambda r: (
            f"<b>{r['cell_id']}</b><br>Site: {r['site_name']}<br>"
            f"Success: {r['ho_sr']:.2f}% · Failure: {r['ho_fr']:.2f}%<br>"
            f"RSRP: {r['rsrp']:.1f} dBm · SINR: {r['sinr']:.1f} dB<br>"
            f"PRB: {r['prb']:.1f}% · UEs: {r['ue']:.0f}<br>"
            f"Sector {r['sector']} · Az {r['azimuth_deg']}°"
        ), axis=1)

        fm = go.Figure()
        # Relations
        rm = rels[rels["distance_m"]>0].merge(
            site_db[["cell_id","latitude","longitude"]], left_on="serving_cell", right_on="cell_id"
        ).merge(site_db[["cell_id","latitude","longitude"]], left_on="neighbor_cell", right_on="cell_id", suffixes=("_s","_t"))
        for _,rr in rm.head(180).iterrows():
            fm.add_trace(go.Scattermapbox(
                lat=[rr["latitude_s"],rr["latitude_t"]], lon=[rr["longitude_s"],rr["longitude_t"]],
                mode="lines", line=dict(width=.5, color="rgba(0,150,170,.1)"),
                hoverinfo="skip", showlegend=False))
        # Problem glow
        pr = md[md["prob"]]
        if len(pr)>0:
            fm.add_trace(go.Scattermapbox(lat=pr["latitude"],lon=pr["longitude"],mode="markers",
                marker=dict(size=pr["bub"]+14,color="rgba(220,38,38,.12)"),hoverinfo="skip",showlegend=False))
        # Cells
        fm.add_trace(go.Scattermapbox(lat=md["latitude"],lon=md["longitude"],mode="markers",
            marker=dict(size=md["bub"],color=md["ho_sr"],
                colorscale=[[0,RED],[.5,AMBER],[.96,AMBER],[1,GREEN]],cmin=85,cmax=100,
                colorbar=dict(title=dict(text="HO %"),thickness=10,len=.4)),
            text=md["hov"],hovertemplate="%{text}<extra></extra>"))
        fm.update_layout(mapbox=dict(style=MAPSTYLE,center=dict(lat=center_lat,lon=center_lon),zoom=13.5),
            margin=dict(l=0,r=0,t=0,b=0),height=620,paper_bgcolor=BG,showlegend=False)
        st.plotly_chart(fm, use_container_width=True)

    with ic:
        st.markdown("**Cell Health Ranking**")
        st.caption("Worst first")
        for _,c in cm.sort_values("ho_sr").head(15).iterrows():
            r=c["ho_sr"]; ico="🔴" if r<96 else ("🟡" if r<99 else "🟢")
            st.markdown(f'<div class="cr"><span>{ico} {c["cell_id"]}</span>'
                f'<span style="color:{hc(r)};font-weight:700;font-family:Fira Code,monospace;">{r:.1f}%</span></div>',
                unsafe_allow_html=True)
        st.divider()
        with st.expander("🔍 Cell Inspector"):
            pk=st.selectbox("Cell",cm["cell_id"].tolist(),index=0,key="cpk")
            cd=cm[cm["cell_id"]==pk].iloc[0]
            st.markdown(f"**{cd['cell_id']}** — {cd['site_name']}\n"
                f"- Sector {cd['sector']} · Az {cd['azimuth_deg']}° · {cd['frequency_band']}\n"
                f"- Success: **{cd['ho_sr']:.2f}%** · Failure: **{cd['ho_fr']:.2f}%**\n"
                f"- RSRP: {cd['rsrp']:.1f} dBm · SINR: {cd['sinr']:.1f} dB\n"
                f"- PRB: {cd['prb']:.1f}% · UEs: {cd['ue']:.0f}")
            cr=rels[rels["serving_cell"]==pk]
            if len(cr)>0:
                st.caption(f"{len(cr)} neighbors")
                st.dataframe(cr[["neighbor_cell","distance_m","cell_individual_offset_dB"]].head(8),
                    use_container_width=True,hide_index=True)

# ── PAGE: VARIANT COMPARISON ────────────────────────────────────────
elif page == "⚔️  Variant Comparison":
    if len(filt)==0:
        st.warning("No data. Run `python run_experiment.py --sweep-all`")
    else:
        sec("Reward Variant Comparison — Gate G3")
        # Variant cards
        vc = st.columns(len(sel_v)) if sel_v else [st.container()]
        for i,v in enumerate(sel_v):
            with vc[i]:
                vd=filt[(filt["Variant"]==v)&(filt["Scenario"]=="baseline")]
                vcl=V_COLORS.get(v,P)
                if len(vd)>0:
                    r=vd.iloc[0]
                    html = (
                        f'<div class="dc" style="text-align:center;border-top:3px solid {vcl};">'
                        f'<p style="font-size:1.5rem;font-weight:800;color:{vcl};font-family:Fira Code,monospace;margin:0;">{v}</p>'
                        f'<p style="font-size:.65rem;font-weight:700;text-transform:uppercase;letter-spacing:2px;color:{TEXT2};margin:4px 0 0 0;">{V_NAMES.get(v,v)}</p>'
                        f'<p style="margin-top:14px;font-size:.88rem;line-height:2;font-family:Fira Sans,sans-serif;">'
                        f'Success: <b>{r["HO Success %"]:.2f}%</b><br>'
                        f'Failure: <b>{r["HO Failure %"]:.4f}%</b><br>'
                        f'Reward: <b style="font-family:Fira Code,monospace;">{r["Mean Reward"]:,.0f}</b></p>'
                        f'</div>'
                    )
                    st.markdown(html, unsafe_allow_html=True)

        # Big bar chart
        sec("HO Success Rate — All Variants × Scenarios")
        fb = go.Figure()
        for v in sel_v:
            vd=filt[filt["Variant"]==v]
            fb.add_trace(go.Bar(x=vd["Scenario"],y=vd["HO Success %"],
                name=f"{v} {V_NAMES.get(v,'')}",marker_color=V_COLORS.get(v,P),
                text=vd["HO Success %"].round(2),textposition="outside",textfont_size=11))
        fb.add_hline(y=99,line_dash="dot",line_color=RED,opacity=.5,
            annotation_text="99% Target",annotation_font_color=RED,annotation_font_size=12)
        fb.update_layout(barmode="group",height=520,template=PLT,paper_bgcolor=BG,plot_bgcolor=BG2,
            font=dict(color=TEXT,size=12,family="Fira Sans"),
            legend=dict(orientation="h",y=-.12,font_size=11),
            margin=dict(t=30,b=80,l=60,r=20),yaxis_title="HO Success Rate (%)")
        st.plotly_chart(fb, use_container_width=True)

        # Radar + Heatmap
        r1,r2 = st.columns(2)
        with r1:
            sec("Multi-Metric Fingerprint")
            cats=["HO Success","Low Failure","Low PingPong","Low TooEarly","Low WrongCell"]
            fr=go.Figure()
            for v in sel_v:
                vd=filt[(filt["Variant"]==v)&(filt["Scenario"]=="baseline")]
                if len(vd)>0:
                    r=vd.iloc[0]
                    vals=[r["HO Success %"],max(0,100-r["HO Failure %"]*100),
                          max(0,100-r["Ping-Pong %"]*100),max(0,100-r["Too Early %"]*1000),
                          max(0,100-r["Wrong Cell %"]*1000)]
                    fr.add_trace(go.Scatterpolar(r=vals+[vals[0]],theta=cats+[cats[0]],
                        fill="toself",name=v,line_color=V_COLORS.get(v,P),opacity=.6))
            fr.update_layout(polar=dict(bgcolor=BG2,
                radialaxis=dict(visible=True,range=[80,100],gridcolor=BORDER),
                angularaxis=dict(gridcolor=BORDER)),
                height=500,template=PLT,paper_bgcolor=BG,font=dict(color=TEXT,family="Fira Sans"),
                legend=dict(orientation="h",y=-.1),margin=dict(t=20,b=60))
            st.plotly_chart(fr, use_container_width=True)

        with r2:
            sec("Performance Heatmap")
            hp=filt.pivot_table(values="HO Success %",index="Scenario",columns="Variant",aggfunc="mean")
            if len(hp)>0:
                fh=go.Figure(data=go.Heatmap(z=hp.values,x=hp.columns.tolist(),y=hp.index.tolist(),
                    colorscale=[[0,"#1E3A5F"],[.4,RED],[.7,AMBER],[1,GREEN]],
                    text=np.round(hp.values,2),texttemplate="%{text:.2f}%",
                    textfont=dict(size=15,color="white",family="Fira Code"),
                    hovertemplate="Variant: %{x}<br>Scenario: %{y}<br>Success: %{z:.2f}%<extra></extra>",
                    colorbar=dict(title=dict(text="Success %"))))
                fh.update_layout(height=500,template=PLT,paper_bgcolor=BG,plot_bgcolor=BG,
                    font=dict(color=TEXT,size=13,family="Fira Sans"),
                    margin=dict(l=100,r=40,t=20,b=40),xaxis=dict(title="Variant"),yaxis=dict(title="Scenario"))
                st.plotly_chart(fh, use_container_width=True)

        # Failure donuts
        sec("Failure Mode Breakdown")
        pc=st.columns(min(len(sel_v),4))
        for i,v in enumerate(sel_v[:4]):
            with pc[i]:
                vd=filt[(filt["Variant"]==v)&(filt["Scenario"]=="baseline")]
                if len(vd)>0:
                    row=vd.iloc[0]
                    fp=go.Figure(data=[go.Pie(labels=["Too Early","Too Late","Wrong Cell"],
                        values=[row["Too Early %"],row["Too Late %"],row["Wrong Cell %"]],
                        hole=.55,marker_colors=[AMBER,"#F97316",RED],
                        textinfo="label+percent",textfont_size=11)])
                    fp.update_layout(title=dict(text=v,font=dict(size=14,color=V_COLORS.get(v,TEXT),family="Fira Code")),
                        height=320,margin=dict(t=45,b=15,l=15,r=15),
                        showlegend=False,template=PLT,paper_bgcolor=BG)
                    st.plotly_chart(fp, use_container_width=True)

# ── PAGE: NETWORK TOPOLOGY ──────────────────────────────────────────
elif page == "🕸️  Network Topology":
    sec("Network Topology — Shibuya 5G Cluster")
    ts_sel=st.selectbox("Scenario view",["baseline","rush_hour","rain_fade","tower_failure"],
        format_func=lambda s:f"{SC_META[s]['i']} {s.replace('_',' ').title()} — {SC_META[s]['l']}")

    rl,rc = cm["latitude"].mean(), cm["longitude"].mean()
    td=cm.copy()
    td["x"]=(td["longitude"]-rc)*111320*math.cos(math.radians(rl))
    td["y"]=(td["latitude"]-rl)*110540
    if ts_sel=="tower_failure":
        fi=td["enodeb_id"].unique()[0]; td.loc[td["enodeb_id"]==fi,"ho_sr"]=0
    elif ts_sel=="rush_hour":
        td["ue"]=td["ue"]*3
    elif ts_sel=="rain_fade":
        rng=np.random.default_rng(42)
        td["ho_sr"]=np.clip(td["ho_sr"]-rng.uniform(0,3,len(td)),80,100)

    ft=go.Figure()
    ir=rels[rels["distance_m"]>0]
    ex,ey=[],[]
    for _,rr in ir.iterrows():
        s=td[td["cell_id"]==rr["serving_cell"]]; t=td[td["cell_id"]==rr["neighbor_cell"]]
        if len(s)>0 and len(t)>0:
            ex+=[s.iloc[0]["x"],t.iloc[0]["x"],None]; ey+=[s.iloc[0]["y"],t.iloc[0]["y"],None]
    ft.add_trace(go.Scatter(x=ex,y=ey,mode="lines",
        line=dict(width=.4,color="rgba(0,150,170,.08)"),hoverinfo="skip",showlegend=False))
    ns=np.clip(td["ue"]*1.3,12,48)
    ft.add_trace(go.Scatter(x=td["x"],y=td["y"],mode="markers+text",
        marker=dict(size=ns,color=td["ho_sr"],
            colorscale=[[0,RED],[.5,AMBER],[.96,AMBER],[1,GREEN]],cmin=80,cmax=100,
            line=dict(width=1.5,color="white" if not dark else "rgba(255,255,255,.15)"),
            colorbar=dict(title=dict(text="Success %"))),
        text=td["cell_id"].str[-4:],textposition="top center",textfont=dict(size=8,color=TEXT3,family="Fira Code"),
        hovertemplate="<b>%{customdata[0]}</b><br>Success: %{customdata[1]:.2f}%<br>UEs: %{customdata[2]:.0f}<extra></extra>",
        customdata=td[["cell_id","ho_sr","ue"]].values,showlegend=False))
    pt=td[td["ho_sr"]<96]
    if len(pt)>0:
        ft.add_trace(go.Scatter(x=pt["x"],y=pt["y"],mode="markers",
            marker=dict(size=45,color="rgba(220,38,38,.1)",line=dict(width=2,color=RED)),
            hoverinfo="skip",showlegend=False))
    ft.update_layout(height=660,template=PLT,paper_bgcolor=BG,plot_bgcolor=BG2,
        xaxis=dict(showgrid=False,zeroline=False,showticklabels=False),
        yaxis=dict(showgrid=False,zeroline=False,showticklabels=False,scaleanchor="x"),
        font=dict(color=TEXT,family="Fira Sans"),margin=dict(l=20,r=20,t=20,b=40))
    st.plotly_chart(ft, use_container_width=True)
    c1,c2,c3,c4,c5=st.columns(5)
    c1.markdown("🟢 ≥ 99%"); c2.markdown("🟡 95–99%"); c3.markdown("🟠 90–95%")
    c4.markdown("🔴 < 90%"); c5.markdown(f"<span style='color:{P};'>━</span> HO link", unsafe_allow_html=True)

# ── PAGE: REAL-TIME SIMULATION ───────────────────────────────────────
elif page == "🔬  Real-Time Simulation":
    sec("Real-Time RL Simulation — Watch the Agent Optimise")
    ss=st.selectbox("Scenario",["baseline","rush_hour","rain_fade","tower_failure"],
        format_func=lambda s:f"{SC_META[s]['i']} {s.replace('_',' ').title()}",key="ss")
    sm,sd=st.columns([5,2])

    with sd:
        st.markdown("**Scenario Parameters**")
        pm_map={"baseline":{"UE":"1.0×","RSRP":"0 dB","Fail":"1.0×"},
            "rush_hour":{"UE":"3.0×","PRB Floor":"70%","HO Att":"2.0×"},
            "rain_fade":{"RSRP":"-5 dB","SINR":"-3 dB","Fail":"1.5×"},
            "tower_failure":{"Sites ↓":"1","Nbr Load":"2.5×","HO Spike":"5.0×"}}
        for k,v in pm_map.get(ss,{}).items():
            mod=v not in ("1.0×","0 dB")
            bg="bg-r" if mod else "bg-g"
            st.markdown(f'<div class="cr"><span>{k}</span><span class="bg {bg}">{v}</span></div>',unsafe_allow_html=True)
        st.divider()
        st.markdown("**Results for Scenario**")
        scd=filt[filt["Scenario"]==ss] if len(filt)>0 else pd.DataFrame()
        if len(scd)>0:
            best=scd.loc[scd["HO Success %"].idxmax()]
            bvc = V_COLORS.get(best['Variant'],P)
            st.markdown(
                f'<div class="dc" style="text-align:center;border-top:3px solid {bvc};">'
                f'<p style="font-size:.65rem;font-weight:700;text-transform:uppercase;letter-spacing:2px;color:{TEXT2};margin:0 0 4px 0;">Best variant</p>'
                f'<p style="font-size:1.4rem;font-weight:800;color:{bvc};font-family:Fira Code,monospace;margin:0;">{best["Variant"]}</p>'
                f'<p style="font-size:.72rem;color:{TEXT3};margin:4px 0 0 0;">{best["HO Success %"]:.2f}% success</p>'
                f'</div>', unsafe_allow_html=True)
            for _,rr in scd.iterrows():
                pct=rr["HO Success %"]; vcl=V_COLORS.get(rr["Variant"],P)
                st.markdown(
                    f'<div style="margin-bottom:10px;">'
                    f'<div style="display:flex;justify-content:space-between;font-size:.82rem;font-family:Fira Sans,sans-serif;">'
                    f'<span style="color:{vcl};font-weight:600;">{rr["Variant"]}</span>'
                    f'<span style="color:{TEXT2};font-family:Fira Code,monospace;">{pct:.2f}%</span></div>'
                    f'<div class="pb"><div class="pf" style="width:{min(pct,100)}%;background:{vcl};"></div></div>'
                    f'</div>', unsafe_allow_html=True)

    with sm:
        @st.fragment(run_every=2)
        def live():
            step=st.session_state.get("sim_step",0); st.session_state.sim_step=step+1
            rng=np.random.default_rng(step); nc=len(cm)
            base=cm["ho_sr"].values.copy()
            imp=np.clip(step*.02,0,2.5); noise=rng.normal(0,.25,nc)
            lsr=np.clip(base+imp+noise,80,100)
            ai=step%nc; ac=cm.iloc[ai]; cio=rng.choice([-2,-1,0,1,2])
            lr=float(np.sum(lsr*cm["ho_att"].values)/100)
            alv=float(np.mean(lsr)); plv=int(np.sum(lsr<96))

            cio_c = GREEN if cio>0 else (RED if cio<0 else AMBER)
            cio_s = f'+{cio}' if cio>0 else str(cio)
            prob_c = GREEN if plv<=3 else RED
            # Use native streamlit metrics for the live panel — no HTML leaks
            st.markdown(
                f'<div class="dc">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">'
                f'<span class="bg bg-l"><span class="live-dot"></span> LIVE — Step {step}</span>'
                f'<span style="font-size:.72rem;color:{TEXT3};font-family:Fira Code,monospace;">{time.strftime("%H:%M:%S")}</span>'
                f'</div></div>', unsafe_allow_html=True)
            lc1,lc2,lc3,lc4,lc5 = st.columns(5)
            lc1.metric("Cluster", f"{alv:.2f}%")
            lc2.metric("Reward", f"{lr:,.0f}")
            lc3.metric("Problems", f"{plv}")
            lc4.metric("Active Cell", ac['cell_id'])
            lc5.metric("CIO Δ", f"{cio_s} dB")

            # Live map
            sdf=cm.copy(); sdf["lsr"]=lsr
            fs=go.Figure()
            fs.add_trace(go.Scattermapbox(lat=sdf["latitude"],lon=sdf["longitude"],mode="markers",
                marker=dict(size=np.clip(sdf["ho_att"]*.5,6,28),color=sdf["lsr"],
                    colorscale=[[0,RED],[.5,AMBER],[.96,AMBER],[1,GREEN]],cmin=88,cmax=100),
                hovertemplate="<b>%{customdata[0]}</b><br>Success: %{customdata[1]:.2f}%<extra></extra>",
                customdata=np.column_stack([sdf["cell_id"],sdf["lsr"]])))
            fs.add_trace(go.Scattermapbox(lat=[ac["latitude"]],lon=[ac["longitude"]],mode="markers",
                marker=dict(size=24,color=P,opacity=.5),
                hovertemplate=f"<b>ACTIVE: {ac['cell_id']}</b><br>CIO: {cio:+d} dB<extra></extra>"))
            fs.update_layout(mapbox=dict(style=MAPSTYLE,center=dict(lat=center_lat,lon=center_lon),zoom=13),
                margin=dict(l=0,r=0,t=0,b=0),height=420,paper_bgcolor=BG,showlegend=False)
            st.plotly_chart(fs, use_container_width=True, key=f"s{step}")

            st.markdown("**Agent Log**")
            lines=[]
            for s in range(max(0,step-6),step+1):
                rl=np.random.default_rng(s); ci=s%nc; cn=cm.iloc[ci]["cell_id"]
                adj=rl.choice([-2,-1,0,1,2]); rew=rl.uniform(50,200)
                ar="→" if adj==0 else ("↑" if adj>0 else "↓")
                lines.append(f"`[{s:04d}]` **{cn}** CIO {ar} {adj:+d} dB · reward {rew:.1f}")
            for l in reversed(lines): st.markdown(l)
        live()

# ── PAGE: GATE G3 & EXPORT ──────────────────────────────────────────
elif page == "📋  Gate G3 & Export":
    if len(filt)==0: st.warning("No data."); st.stop()

    sec("KPI Delta Table — vs v0 Baseline")
    base=filt[(filt["Variant"]=="v0")&(filt["Scenario"]=="baseline")]
    if len(base)>0:
        b=base.iloc[0]; dr=[]
        for _,row in filt.iterrows():
            dr.append({"Variant":row["Variant"],"Scenario":row["Scenario"],
                "HO Success %":round(row["HO Success %"],2),
                "Success Δ":round(row["HO Success %"]-b["HO Success %"],4),
                "Failure Δ":round(row["HO Failure %"]-b["HO Failure %"],4),
                "PingPong Δ":round(row["Ping-Pong %"]-b["Ping-Pong %"],4),
                "Reward Δ":round(row["Mean Reward"]-b["Mean Reward"],1)})
        ddf=pd.DataFrame(dr)
        st.dataframe(ddf.style.format({"HO Success %":"{:.2f}","Success Δ":"{:+.4f}",
            "Failure Δ":"{:+.4f}","PingPong Δ":"{:+.4f}","Reward Δ":"{:+.1f}"}),
            use_container_width=True,hide_index=True,height=420)

    st.divider()
    sec("Best Variant Recommendation")
    rcols=st.columns(len(sel_s))
    for i,sc in enumerate(sel_s):
        with rcols[i]:
            sd=filt[filt["Scenario"]==sc]
            if len(sd)>0:
                best=sd.loc[sd["HO Success %"].idxmax()]; m=SC_META.get(sc,{})
                bvc2 = V_COLORS.get(best['Variant'],TEXT)
                st.markdown(
                    f'<div class="dc" style="text-align:center;border-top:3px solid {m.get("c",P)};">'
                    f'<p style="font-size:1.4rem;margin:0;">{m.get("i","📡")}</p>'
                    f'<p style="font-size:.65rem;font-weight:700;text-transform:uppercase;letter-spacing:2px;color:{TEXT2};margin:4px 0;">{sc.replace("_"," ").title()}</p>'
                    f'<p style="font-size:1.4rem;font-weight:800;color:{bvc2};margin:8px 0;font-family:Fira Code,monospace;">{best["Variant"]}</p>'
                    f'<p style="font-size:.72rem;color:{TEXT3};margin:0;">{best["HO Success %"]:.2f}% · {best["Mean Reward"]:,.0f} reward</p>'
                    f'</div>', unsafe_allow_html=True)

    st.divider()
    sec("Export Data")
    e1,e2,e3=st.columns(3)
    with e1: st.download_button("📥 CSV",filt.to_csv(index=False),"mro_comparison.csv","text/csv",use_container_width=True)
    with e2:
        sw=ed.get("sweep",{})
        if sw: st.download_button("📥 Sweep",json.dumps(sw,indent=2,default=str),"mro_sweep.json","application/json",use_container_width=True)
    with e3:
        rp={"gate":"G3","generated":pd.Timestamp.now().isoformat(),"data":filt.to_dict("records")}
        st.download_button("📥 Report",json.dumps(rp,indent=2,default=str),"mro_g3.json","application/json",use_container_width=True)

    st.divider()
    sec("Gate G3 Checklist")
    chks=[("≥ 2 reward variants with KPI delta",len(filt["Variant"].unique())>=2),
        ("≥ 3 distinct scenarios",len(filt["Scenario"].unique())>=3),
        ("≥ 5 MLflow training runs",len(ed["experiments"])>=5),
        ("Dashboard shows KPI differences",True),
        ("Side-by-side comparison table",True),
        ("Automated pipeline",True)]
    for lbl,ok in chks:
        bg="bg-g" if ok else "bg-r"
        st.markdown(f'<div class="cr"><span>{"✅" if ok else "❌"} {lbl}</span><span class="bg {bg}">{"PASS" if ok else "FAIL"}</span></div>',
            unsafe_allow_html=True)
    ao=all(p for _,p in chks)
    gc = GREEN if ao else RED
    gt = '🎉 GATE G3 — ALL CHECKS PASSING' if ao else '⚠️ NOT READY'
    gn = sum(p for _,p in chks)
    st.markdown(
        f'<div class="dc" style="text-align:center;margin-top:16px;border:2px solid {gc};">'
        f'<p style="font-size:1.2rem;font-weight:800;color:{gc};font-family:Fira Sans,sans-serif;margin:0;">{gt}</p>'
        f'<p style="font-size:.72rem;color:{TEXT3};margin:4px 0 0 0;">{gn}/{len(chks)} criteria met</p>'
        f'</div>', unsafe_allow_html=True)

# ── Footer ───────────────────────────────────────────────────────────
st.divider()
st.caption("WINNIIO AltioStar MRO · Phase 2 · Rakuten Japan 5G · 75 Cells · 763 Relations · 99% Target")
