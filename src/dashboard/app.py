"""AltioStar MRO — Phase 2 Dashboard.

Tailwind-inspired clean UI: dark sidebar, flat KPI cards,
colored badges, clean tables, donut charts.

Usage:
    streamlit run src/dashboard/app.py
"""

from __future__ import annotations

import base64, json, math, sys, time
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

# ── Assets — load logos as base64 for embedding ──────────────────────
ASSETS = Path(__file__).resolve().parent / "assets"

def img_b64(fname):
    p = ASSETS / fname
    if p.exists():
        return base64.b64encode(p.read_bytes()).decode()
    return ""

LOGO_B64 = img_b64("winniio_logo.png")       # colored full logo (for login page)
CRANE_B64 = img_b64("winniio_crane.png")      # colored crane icon (sidebar + header)

# ── Page config — use WINNIIO favicon ────────────────────────────────
_fav = ASSETS / "favicon.ico"
if _fav.exists():
    _fav_b64 = base64.b64encode(_fav.read_bytes()).decode()
    st.set_page_config(
        page_title="WINNIIO · AltioStar MRO",
        page_icon=f"data:image/x-icon;base64,{_fav_b64}",
        layout="wide",
        initial_sidebar_state="expanded",
    )
else:
    st.set_page_config(
        page_title="WINNIIO · AltioStar MRO",
        page_icon="📡",
        layout="wide",
        initial_sidebar_state="expanded",
    )

# ── Password gate (persists via URL query param) ─────────────────────
DASHBOARD_PASSWORD = "Winniio-2019"
_AUTH_KEY = "_a"
_AUTH_VAL = "w2019"

# Check auth: query param persists across refreshes in the URL
_is_authed = st.query_params.get(_AUTH_KEY) == _AUTH_VAL

if not _is_authed:
    # Full-screen centered login
    st.markdown("""
    <style>
      #MainMenu, footer, .stDeployButton, header { display: none; }
      section[data-testid="stSidebar"] { display: none; }
    </style>
    """, unsafe_allow_html=True)

    _1, center, _2 = st.columns([1, 1.5, 1])
    with center:
        st.markdown("<div style='height:12vh'></div>", unsafe_allow_html=True)
        if LOGO_B64:
            st.markdown(
                f'<div style="text-align:center; margin-bottom:30px;">'
                f'<img src="data:image/png;base64,{LOGO_B64}" '
                f'style="height:60px; object-fit:contain;" /></div>',
                unsafe_allow_html=True)
        st.markdown(
            '<div style="text-align:center; margin-bottom:8px;">'
            '<span style="font-size:1.1rem; font-weight:700; color:#0F172A;">'
            'AltioStar MRO Dashboard</span></div>'
            '<div style="text-align:center; margin-bottom:24px;">'
            '<span style="font-size:.82rem; color:#64748B;">'
            'Rakuten Japan 5G · Phase 2</span></div>',
            unsafe_allow_html=True)
        pwd = st.text_input("Password", type="password", placeholder="Enter dashboard password")
        login_btn = st.button("Sign In", use_container_width=True, type="primary")
        if login_btn:
            if pwd == DASHBOARD_PASSWORD:
                st.query_params[_AUTH_KEY] = _AUTH_VAL
                st.rerun()
            else:
                st.error("Incorrect password.")
        st.markdown(
            '<div style="text-align:center; margin-top:24px; font-size:.7rem; color:#94A3B8;">'
            'WINNIIO · Secure Access</div>',
            unsafe_allow_html=True)
    st.stop()

# ── Session state ────────────────────────────────────────────────────
if "sim_step" not in st.session_state:
    st.session_state.sim_step = 0

# ── Design tokens — Tailwind-inspired ────────────────────────────────
PRIMARY = "#0096AA"
PRIMARY_DARK = "#007A8A"
BLUE = "#3B82F6"
GREEN = "#22C55E"
RED = "#EF4444"
AMBER = "#F59E0B"
PURPLE = "#8B5CF6"
ORANGE = "#F97316"

SIDEBAR_BG = "#0F172A"
SIDEBAR_TEXT = "#94A3B8"
SIDEBAR_ACTIVE = "rgba(59,130,246,.12)"

BG = "#F1F5F9"
CARD = "#FFFFFF"
BORDER = "#E2E8F0"
TEXT = "#0F172A"
TEXT_SEC = "#64748B"
TEXT_MUTED = "#94A3B8"
SHADOW = "0 1px 3px rgba(0,0,0,.08)"

PLT = "plotly_white"
MAPSTYLE = "carto-positron"

V_COLORS = {"v0": RED, "v1": PRIMARY, "v2": GREEN, "v3": PURPLE}
V_NAMES = {"v0": "Count-Based", "v1": "Traffic-Weighted", "v2": "Rate-Based", "v3": "Multi-Objective"}
SC_META = {
    "baseline": {"c": GREEN, "l": "Normal"},
    "rush_hour": {"c": RED, "l": "High Congestion"},
    "rain_fade": {"c": BLUE, "l": "Signal Degradation"},
    "tower_failure": {"c": AMBER, "l": "Site Outage"},
}

# ── CSS — Tailwind-inspired clean design ─────────────────────────────
st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

  /* === RESET === */
  .stApp {{ background: {BG}; color: {TEXT}; font-family: 'Inter', -apple-system, BlinkMacSystemFont, system-ui, sans-serif; }}
  .main .block-container {{ padding-top: .5rem; max-width: 1560px; }}
  #MainMenu, footer, .stDeployButton {{ display: none; }}

  /* === SIDEBAR === */
  section[data-testid="stSidebar"] {{
    background: {SIDEBAR_BG};
    font-family: 'Inter', sans-serif;
    border-right: 1px solid rgba(255,255,255,.06);
  }}
  section[data-testid="stSidebar"] * {{ color: {SIDEBAR_TEXT} !important; }}
  section[data-testid="stSidebar"] hr {{ border-color: rgba(255,255,255,.06); margin: 8px 0; }}

  /* Radio nav — clean pill style */
  section[data-testid="stSidebar"] .stRadio > div {{ gap: 2px; }}
  section[data-testid="stSidebar"] .stRadio > div > label {{
    background: transparent;
    border: none;
    border-radius: 6px;
    padding: 10px 14px !important;
    font-size: .84rem !important;
    font-weight: 500 !important;
    transition: all .15s ease;
    cursor: pointer;
  }}
  section[data-testid="stSidebar"] .stRadio > div > label:hover {{
    background: rgba(255,255,255,.05);
    color: #E2E8F0 !important;
  }}
  section[data-testid="stSidebar"] .stRadio > div > label:has(input:checked) {{
    background: {SIDEBAR_ACTIVE};
    color: {BLUE} !important;
    font-weight: 600 !important;
    border-left: 3px solid {BLUE};
    padding-left: 11px !important;
  }}
  section[data-testid="stSidebar"] .stRadio > div > label > div:first-child {{ display: none; }}

  /* === CARD === */
  .card {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 20px 24px;
    box-shadow: {SHADOW};
    margin-bottom: 12px;
  }}

  /* === KPI CARD (flat number style) === */
  .kpi {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 16px 20px;
    box-shadow: {SHADOW};
  }}
  .kpi-label {{
    font-size: .68rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: .08em;
    color: {TEXT_SEC};
    margin-bottom: 4px;
    display: flex;
    align-items: center;
    gap: 6px;
  }}
  .kpi-label .kpi-icon {{
    width: 8px; height: 8px;
    border-radius: 2px;
    display: inline-block;
  }}
  .kpi-value {{
    font-size: 1.65rem;
    font-weight: 700;
    color: {TEXT};
    font-family: 'JetBrains Mono', monospace;
    line-height: 1.2;
  }}
  .kpi-sub {{
    font-size: .72rem;
    color: {TEXT_MUTED};
    margin-top: 2px;
  }}

  /* === BADGE (status pill) === */
  .badge {{
    display: inline-flex;
    align-items: center;
    padding: 2px 10px;
    border-radius: 9999px;
    font-size: .7rem;
    font-weight: 600;
    letter-spacing: .02em;
    gap: 4px;
  }}
  .badge::before {{
    content: '';
    width: 6px; height: 6px;
    border-radius: 50%;
  }}
  .badge-green {{ background: #DCFCE7; color: #166534; }}
  .badge-green::before {{ background: #22C55E; }}
  .badge-red {{ background: #FEE2E2; color: #991B1B; }}
  .badge-red::before {{ background: #EF4444; }}
  .badge-amber {{ background: #FEF3C7; color: #92400E; }}
  .badge-amber::before {{ background: #F59E0B; }}
  .badge-blue {{ background: #DBEAFE; color: #1E40AF; }}
  .badge-blue::before {{ background: #3B82F6; }}
  .badge-purple {{ background: #EDE9FE; color: #5B21B6; }}
  .badge-purple::before {{ background: #8B5CF6; }}

  /* === TABLE ROW === */
  .trow {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 16px;
    border-bottom: 1px solid {BORDER};
    font-size: .82rem;
    transition: background .1s;
  }}
  .trow:hover {{ background: #F8FAFC; }}
  .trow:last-child {{ border-bottom: none; }}

  /* === TABLE HEADER === */
  .thead {{
    display: flex;
    justify-content: space-between;
    padding: 8px 16px;
    background: #F8FAFC;
    border-bottom: 2px solid {BORDER};
    font-size: .72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: .06em;
    color: {TEXT_SEC};
  }}

  /* === SECTION TITLE === */
  .section-title {{
    font-size: .88rem;
    font-weight: 700;
    color: {TEXT};
    margin: 20px 0 12px 0;
    padding-bottom: 8px;
    border-bottom: 2px solid {BORDER};
  }}

  /* === PAGE TITLE === */
  .page-title {{
    font-size: 1.15rem;
    font-weight: 700;
    color: {TEXT};
  }}
  .page-subtitle {{
    font-size: .78rem;
    color: {TEXT_MUTED};
  }}

  /* === LIVE DOT === */
  @keyframes pulse {{ 0%,100% {{ opacity:1 }} 50% {{ opacity:.3 }} }}
  .live-dot {{
    display: inline-block;
    width: 7px; height: 7px;
    border-radius: 50%;
    background: {GREEN};
    animation: pulse 2s ease-in-out infinite;
    margin-right: 4px;
  }}

  /* === PROGRESS BAR === */
  .pbar {{
    background: {BG};
    border-radius: 9999px;
    height: 6px;
    overflow: hidden;
    margin-top: 6px;
  }}
  .pfill {{
    height: 100%;
    border-radius: 9999px;
    transition: width .6s ease;
  }}

  /* === PLOTLY & DATAFRAME — card styling built in === */
  .stPlotlyChart {{
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid {BORDER};
    box-shadow: {SHADOW};
  }}
  .stDataFrame {{
    border-radius: 8px;
    overflow: hidden;
    font-family: 'Inter', sans-serif;
    font-size: .82rem;
  }}
  [data-testid="stMetric"] {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 14px 16px;
    box-shadow: {SHADOW};
  }}

  /* === TABS (Tailwind pill style) === */
  .stTabs [data-baseweb="tab-list"] {{
    gap: 2px;
    background: {BG};
    padding: 3px;
    border-radius: 8px;
    border: 1px solid {BORDER};
  }}
  .stTabs [data-baseweb="tab"] {{
    border-radius: 6px;
    font-size: .82rem;
    font-weight: 500;
    padding: 6px 14px;
  }}
  .stTabs [data-baseweb="tab"][aria-selected="true"] {{
    background: {CARD};
    box-shadow: {SHADOW};
  }}

  /* === TOP NAV CHIPS === */
  .topnav-chip {{
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 5px 12px;
    border-radius: 6px;
    font-size: .74rem;
    font-weight: 600;
    background: {CARD};
    border: 1px solid {BORDER};
    color: {TEXT_SEC};
    cursor: default;
    transition: all .15s;
  }}
  .topnav-chip:hover {{
    border-color: {PRIMARY};
    color: {PRIMARY};
    box-shadow: 0 2px 8px rgba(0,150,170,.1);
  }}

  /* === BUTTON === */
  .stButton > button {{
    border-radius: 6px;
    font-size: .78rem;
    font-weight: 600;
    padding: 6px 14px;
    border: 1px solid {BORDER};
    background: {CARD};
    transition: all .15s;
  }}
  .stButton > button:hover {{
    border-color: {PRIMARY};
    color: {PRIMARY};
    box-shadow: 0 2px 8px rgba(0,150,170,.08);
  }}

  /* === SEARCH INPUT === */
  .stSelectbox > div > div, .stMultiSelect > div > div {{
    border-radius: 6px !important;
    border-color: {BORDER} !important;
    font-size: .84rem;
  }}
</style>
""", unsafe_allow_html=True)

# ── Paths ────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
RDIR = ROOT / "results"
DDIR = ROOT / "data" / "synthetic"

# ── Data loaders ─────────────────────────────────────────────────────
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
        rows.append({
            "Variant": e.get("reward_version", "?"),
            "Scenario": e.get("scenario", "?"),
            "Mean Reward": ev.get("mean_reward", 0),
            "HO Success %": ev.get("ho_success_rate", 0),
            "HO Failure %": ev.get("ho_failure_rate", 0),
            "Ping-Pong %": ev.get("pingpong_rate", 0),
            "Too Early %": ev.get("too_early_rate", 0),
            "Too Late %": ev.get("too_late_rate", 0),
            "Wrong Cell %": ev.get("wrong_cell_rate", 0),
        })
    return pd.DataFrame(rows)

def health_color(r):
    if r >= 99: return GREEN
    if r >= 96: return AMBER
    return RED

def health_badge(r):
    if r >= 99: return "badge-green", "Healthy"
    if r >= 96: return "badge-amber", "Warning"
    return "badge-red", "Critical"

# ── Load data ────────────────────────────────────────────────────────
site_db = ld_site()
pm = ld_pm()
rels = ld_rel()
ed = ld_exp()
cdf = comp_df(ed["experiments"])

ck = pm.groupby("cell_id").agg(
    ho_att=("ho_attempts_intra", "mean"),
    ho_sr=("ho_success_rate_pct", "mean"),
    ho_fr=("ho_failure_rate_pct", "mean"),
    rsrp=("avg_rsrp_dBm", "mean"),
    sinr=("avg_sinr_dB", "mean"),
    prb=("prb_utilization_dl_pct", "mean"),
    ue=("active_ue_avg", "mean"),
    mx_ue=("max_ue_connected", "max"),
).reset_index()

cm = site_db.merge(ck, on="cell_id", how="left")
cm["prob"] = cm["ho_sr"] < 96
n_prob = int(cm["prob"].sum())
n_healthy = 75 - n_prob
avg_sr = cm["ho_sr"].mean()
best_sr = cm["ho_sr"].max()
worst_sr = cm["ho_sr"].min()
avg_fr = cm["ho_fr"].mean()
avg_prb = cm["prb"].mean()

center_lat = cm["latitude"].mean()
center_lon = cm["longitude"].mean()

# ══════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════
with st.sidebar:
    crane_tag = f'<img src="data:image/png;base64,{CRANE_B64}" style="height:34px; width:34px; object-fit:contain;" />' if CRANE_B64 else ''
    st.markdown(
        f'<div style="display:flex; align-items:center; justify-content:center; gap:10px; '
        f'padding:20px 8px 20px 8px; min-height:80px;">'
        f'{crane_tag}'
        f'<div>'
        f'<div style="font-size:1.1rem; font-weight:700; color:#E2E8F0 !important; letter-spacing:.5px; line-height:1.2;">WINNIIO</div>'
        f'<div style="font-size:.6rem; color:#64748B !important; letter-spacing:.1em;">AltioStar MRO</div>'
        f'</div></div>', unsafe_allow_html=True)

    st.divider()

    page = st.radio("Nav", [
        "Dashboard",
        "Cell Map",
        "Experiments",
        "Network",
        "Simulation",
        "Reports",
    ], label_visibility="collapsed")

    st.divider()

    st.markdown(
        f'<div style="padding:4px 14px; font-size:.75rem; line-height:2.2;">'
        f'<div style="display:flex; justify-content:space-between;">'
        f'<span>Online Cells</span><span style="font-weight:600; color:#E2E8F0 !important;">75</span></div>'
        f'<div style="display:flex; justify-content:space-between;">'
        f'<span>Healthy</span><span style="font-weight:600; color:{GREEN} !important;">{n_healthy}</span></div>'
        f'<div style="display:flex; justify-content:space-between;">'
        f'<span>Problem</span><span style="font-weight:600; color:{RED} !important;">{n_prob}</span></div>'
        f'<div style="display:flex; justify-content:space-between;">'
        f'<span>Experiments</span><span style="font-weight:600; color:#E2E8F0 !important;">{len(ed["experiments"])}</span></div>'
        f'</div>', unsafe_allow_html=True)

    st.divider()

    gap = max(0, 99 - avg_sr)
    pct = min(avg_sr / 99 * 100, 100)
    st.markdown(
        f'<div style="padding:4px 14px;">'
        f'<div style="font-size:.68rem; font-weight:600; text-transform:uppercase; letter-spacing:.06em; color:{TEXT_MUTED} !important; margin-bottom:8px;">Target Progress</div>'
        f'<div style="display:flex; justify-content:space-between; font-size:.82rem; margin-bottom:4px;">'
        f'<span style="font-weight:600; color:#E2E8F0 !important;">{avg_sr:.2f}%</span>'
        f'<span style="color:{TEXT_MUTED} !important;">/ 99.00%</span></div>'
        f'<div style="background:rgba(255,255,255,.08); border-radius:9999px; height:6px; overflow:hidden;">'
        f'<div style="width:{pct:.1f}%; height:100%; background:linear-gradient(90deg,{PRIMARY},{GREEN}); border-radius:9999px;"></div>'
        f'</div>'
        f'<div style="font-size:.68rem; color:{TEXT_MUTED} !important; margin-top:4px;">Gap: {gap:.2f}%</div>'
        f'</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
# HELPER: section title
# ══════════════════════════════════════════════════════════════════════
def sec(title):
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
# TOP BAR
# ══════════════════════════════════════════════════════════════════════
now_utc = datetime.now(timezone.utc)
now_jst = now_utc + timedelta(hours=9)

crane_src = f'data:image/png;base64,{CRANE_B64}' if CRANE_B64 else ''
if crane_src:
    st.markdown(f"""
    <style>
      header[data-testid="stHeader"]::after {{
        content: '';
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 44px;
        height: 44px;
        background: url('{crane_src}') center/contain no-repeat;
        pointer-events: none;
        z-index: 999;
      }}
    </style>
    """, unsafe_allow_html=True)

tc1, tc2 = st.columns([2, 3])
with tc1:
    st.markdown(
        f'<div class="page-title">{page}</div>'
        f'<div class="page-subtitle">Rakuten Japan 5G · Shibuya · 75 Cells · 763 Relations</div>',
        unsafe_allow_html=True)
with tc2:
    st.markdown(
        f'<div style="display:flex; align-items:center; justify-content:flex-end; gap:6px; flex-wrap:wrap; padding-top:2px;">'
        f'<span class="topnav-chip" id="chip-live"><span class="live-dot"></span>Live Monitor</span>'
        f'<span class="topnav-chip" id="chip-anomaly">🔍 Anomaly Scan</span>'
        f'<span class="topnav-chip" id="chip-health">💊 Health Check</span>'
        f'<span class="topnav-chip" id="chip-export">📤 Quick Export</span>'
        f'</div>', unsafe_allow_html=True)
    import streamlit.components.v1 as components
    components.html(f"""
    <div id="live-clock" style="
        text-align:right; font-size:.74rem; font-family:'JetBrains Mono',monospace;
        color:{TEXT_SEC}; padding:4px 0; display:flex; align-items:center;
        justify-content:flex-end; gap:8px;
    ">
        <span id="clock-local" style="padding:3px 10px; background:{CARD};
            border:1px solid {BORDER}; border-radius:6px;"></span>
        <span id="clock-jst" style="padding:3px 10px; background:{CARD};
            border:1px solid {BORDER}; border-radius:6px; color:{TEXT_MUTED};"></span>
    </div>
    <script>
    function updateClock() {{
        const now = new Date();
        const localTz = Intl.DateTimeFormat().resolvedOptions().timeZone;
        const localShort = localTz.split('/').pop().replace('_', ' ');
        const localTime = now.toLocaleTimeString('en-GB', {{hour:'2-digit', minute:'2-digit', second:'2-digit'}});
        document.getElementById('clock-local').innerHTML =
            '📍 ' + localTime + ' ' + localShort;
        const jstTime = now.toLocaleTimeString('en-GB', {{
            hour:'2-digit', minute:'2-digit', second:'2-digit', timeZone:'Asia/Tokyo'
        }});
        document.getElementById('clock-jst').innerHTML =
            '🇯🇵 ' + jstTime + ' JST';
    }}
    updateClock();
    setInterval(updateClock, 1000);
    </script>
    """, height=34)

if "show_anomaly" not in st.session_state:
    st.session_state.show_anomaly = False
if "show_health" not in st.session_state:
    st.session_state.show_health = False
if "show_quick_export" not in st.session_state:
    st.session_state.show_quick_export = False

qa1, qa2, qa3 = st.columns(3)
with qa1:
    if st.button("🔍 Run Anomaly Scan", use_container_width=True, key="btn_anomaly"):
        st.session_state.show_anomaly = not st.session_state.show_anomaly
with qa2:
    if st.button("💊 Network Health Check", use_container_width=True, key="btn_health"):
        st.session_state.show_health = not st.session_state.show_health
with qa3:
    if st.button("📤 Quick Export All", use_container_width=True, key="btn_export"):
        st.session_state.show_quick_export = not st.session_state.show_quick_export

if st.session_state.show_anomaly:
    with st.container():
        st.markdown(f'<div class="section-title">🔍 Anomaly Scan Results</div>', unsafe_allow_html=True)
        anomalies = cm[cm["prob"]].sort_values("ho_sr")
        if len(anomalies) == 0:
            st.success("No anomalies detected — all cells within normal range.")
        else:
            ac1, ac2, ac3 = st.columns(3)
            with ac1:
                st.markdown(
                    f'<div class="kpi" style="border-left:3px solid {RED};">'
                    f'<div class="kpi-label">Anomalous Cells</div>'
                    f'<div class="kpi-value" style="color:{RED};">{len(anomalies)}</div>'
                    f'<div class="kpi-sub">Below 96% HO success threshold</div>'
                    f'</div>', unsafe_allow_html=True)
            with ac2:
                worst = anomalies.iloc[0]
                st.markdown(
                    f'<div class="kpi" style="border-left:3px solid {AMBER};">'
                    f'<div class="kpi-label">Worst Offender</div>'
                    f'<div class="kpi-value" style="color:{AMBER};">{worst["cell_id"]}</div>'
                    f'<div class="kpi-sub">{worst["ho_sr"]:.2f}% success · {worst["site_name"]}</div>'
                    f'</div>', unsafe_allow_html=True)
            with ac3:
                avg_anom = anomalies["ho_sr"].mean()
                st.markdown(
                    f'<div class="kpi" style="border-left:3px solid {PURPLE};">'
                    f'<div class="kpi-label">Avg Anomaly Rate</div>'
                    f'<div class="kpi-value" style="color:{PURPLE};">{avg_anom:.2f}%</div>'
                    f'<div class="kpi-sub">Across {len(anomalies)} flagged cells</div>'
                    f'</div>', unsafe_allow_html=True)
            for _, r in anomalies.iterrows():
                severity = "HIGH" if r["ho_sr"] < 95 else "MEDIUM"
                scls = "badge-red" if severity == "HIGH" else "badge-amber"
                st.markdown(
                    f'<div class="trow">'
                    f'<span style="flex:2;font-weight:600;font-family:JetBrains Mono,monospace;">{r["cell_id"]}</span>'
                    f'<span style="flex:2;color:{TEXT_SEC};">{r["site_name"]}</span>'
                    f'<span style="flex:1;text-align:center;font-weight:600;color:{RED};font-family:JetBrains Mono,monospace;">{r["ho_sr"]:.2f}%</span>'
                    f'<span style="flex:1;text-align:center;font-family:JetBrains Mono,monospace;color:{TEXT_SEC};">RSRP {r["rsrp"]:.1f}</span>'
                    f'<span style="flex:1;text-align:right;"><span class="badge {scls}">{severity}</span></span>'
                    f'</div>', unsafe_allow_html=True)

if st.session_state.show_health:
    with st.container():
        st.markdown(f'<div class="section-title">💊 Network Health Report</div>', unsafe_allow_html=True)
        hc1, hc2, hc3, hc4, hc5 = st.columns(5)
        cells_online = 75
        avg_rsrp = cm["rsrp"].mean()
        avg_sinr = cm["sinr"].mean()
        avg_ue = cm["ue"].mean()
        checks = [
            ("Cell Availability", f"{cells_online}/75", cells_online == 75),
            ("Avg RSRP", f"{avg_rsrp:.1f} dBm", avg_rsrp > -90),
            ("Avg SINR", f"{avg_sinr:.1f} dB", avg_sinr > 5),
            ("HO Success", f"{avg_sr:.2f}%", avg_sr > 97),
            ("PRB Utilization", f"{avg_prb:.1f}%", avg_prb < 60),
        ]
        for col, (name, val, ok) in zip([hc1, hc2, hc3, hc4, hc5], checks):
            bcls = "badge-green" if ok else "badge-red"
            blbl = "OK" if ok else "WARN"
            with col:
                st.markdown(
                    f'<div class="kpi">'
                    f'<div class="kpi-label">{name}</div>'
                    f'<div class="kpi-value">{val}</div>'
                    f'<div style="margin-top:6px;"><span class="badge {bcls}">{blbl}</span></div>'
                    f'</div>', unsafe_allow_html=True)
        score = sum(1 for _, _, ok in checks if ok)
        sc = GREEN if score >= 4 else (AMBER if score >= 3 else RED)
        st.markdown(
            f'<div style="text-align:center; margin:10px 0; font-size:.88rem; font-weight:600; color:{sc};">'
            f'Network Health Score: {score}/{len(checks)} checks passing'
            f'</div>', unsafe_allow_html=True)

if st.session_state.show_quick_export:
    with st.container():
        st.markdown(f'<div class="section-title">📤 Quick Export</div>', unsafe_allow_html=True)
        qe1, qe2, qe3, qe4 = st.columns(4)
        with qe1:
            st.download_button("📊 Cell Data (CSV)", cm.to_csv(index=False), "cell_data.csv", "text/csv", use_container_width=True)
        with qe2:
            if len(cdf) > 0:
                st.download_button("🧪 Experiments (CSV)", cdf.to_csv(index=False), "experiments.csv", "text/csv", use_container_width=True)
        with qe3:
            st.download_button("🔗 Relations (CSV)", rels.to_csv(index=False), "relations.csv", "text/csv", use_container_width=True)
        with qe4:
            report = {
                "generated": now_jst.isoformat(),
                "cluster_avg": round(avg_sr, 4),
                "cells": 75, "problem_cells": n_prob,
                "experiments": len(ed["experiments"]),
                "target": 99.0, "gap": round(max(0, 99 - avg_sr), 4),
            }
            st.download_button("📋 Summary (JSON)", json.dumps(report, indent=2), "summary.json", "application/json", use_container_width=True)


# ══════════════════════════════════════════════════════════════════════
# PAGE: DASHBOARD
# ══════════════════════════════════════════════════════════════════════
if page == "Dashboard":
    # ── Scenario selector ────────────────────────────────────────────
    sc_col, _ = st.columns([1, 3])
    with sc_col:
        dash_scenario = st.selectbox(
            "Scenario",
            ["baseline", "rush_hour", "rain_fade", "tower_failure"],
            format_func=lambda s: f"{s.replace('_', ' ').title()} — {SC_META[s]['l']}",
            key="dash_scenario",
        )
    sc_color = SC_META[dash_scenario]["c"]
    sc_label = SC_META[dash_scenario]["l"]

    # Filter experiment data for selected scenario
    cdf_sc = cdf[cdf["Scenario"] == dash_scenario] if len(cdf) > 0 else cdf

    # Recompute KPIs for selected scenario using scenario-modulated cell data
    cm_sc = cm.copy()
    if dash_scenario == "tower_failure":
        fi = cm_sc["enodeb_id"].unique()[0]
        cm_sc.loc[cm_sc["enodeb_id"] == fi, "ho_sr"] = 0
        cm_sc.loc[cm_sc["enodeb_id"] == fi, "ho_fr"] = 100
    elif dash_scenario == "rush_hour":
        cm_sc["prb"] = np.clip(cm_sc["prb"] * 2.0, 0, 100)
        cm_sc["ho_sr"] = np.clip(cm_sc["ho_sr"] - 1.5, 0, 100)
        cm_sc["ho_fr"] = np.clip(cm_sc["ho_fr"] + 1.5, 0, 100)
    elif dash_scenario == "rain_fade":
        rng_sc = np.random.default_rng(42)
        cm_sc["ho_sr"] = np.clip(cm_sc["ho_sr"] - rng_sc.uniform(0, 3, len(cm_sc)), 0, 100)
        cm_sc["ho_fr"] = np.clip(cm_sc["ho_fr"] + rng_sc.uniform(0, 3, len(cm_sc)), 0, 100)

    cm_sc["prob"] = cm_sc["ho_sr"] < 96
    sc_avg_sr   = cm_sc["ho_sr"].mean()
    sc_best_sr  = cm_sc["ho_sr"].max()
    sc_worst_sr = cm_sc["ho_sr"].min()
    sc_avg_fr   = cm_sc["ho_fr"].mean()
    sc_avg_prb  = cm_sc["prb"].mean()

    # Scenario badge
    st.markdown(
        f'<div style="margin-bottom:8px;">'
        f'<span class="badge" style="background:{sc_color}22;color:{sc_color};border:1px solid {sc_color}55;">'
        f'● {sc_label}</span></div>',
        unsafe_allow_html=True)

    # KPI cards row
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    kpis = [
        (k1, PRIMARY, "Cluster Avg", f"{sc_avg_sr:.2f}%", "HO Success Rate"),
        (k2, GREEN, "Best Cell", f"{sc_best_sr:.2f}%", "Peak performance"),
        (k3, RED, "Worst Cell", f"{sc_worst_sr:.2f}%", "Needs attention"),
        (k4, AMBER, "Failure Rate", f"{sc_avg_fr:.2f}%", "Avg HO failure"),
        (k5, PURPLE, "PRB Usage", f"{sc_avg_prb:.1f}%", "DL utilization"),
        (k6, BLUE, "Experiments", f"{len(cdf_sc)}", f"{dash_scenario} runs"),
    ]
    for col, color, label, value, sub in kpis:
        with col:
            st.markdown(
                f'<div class="kpi">'
                f'<div class="kpi-label"><span class="kpi-icon" style="background:{color};"></span>{label}</div>'
                f'<div class="kpi-value">{value}</div>'
                f'<div class="kpi-sub">{sub}</div>'
                f'</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Before/After KPI overlay (Baseline vs Selected Scenario) ─────
    if dash_scenario != "baseline":
        sec(f"Before / After — Baseline vs {dash_scenario.replace('_', ' ').title()}")

        # Baseline KPIs (unmodified cm)
        _base_avg_sr  = cm["ho_sr"].mean()
        _base_avg_fr  = cm["ho_fr"].mean()
        _base_avg_prb = cm["prb"].mean()

        _delta_sr  = sc_avg_sr  - _base_avg_sr
        _delta_fr  = sc_avg_fr  - _base_avg_fr
        _delta_prb = sc_avg_prb - _base_avg_prb

        # Green = improvement, Red = degradation (lower failure/PRB = better)
        _dc_sr  = GREEN if _delta_sr  >= 0 else RED
        _dc_fr  = GREEN if _delta_fr  <= 0 else RED
        _dc_prb = GREEN if _delta_prb <= 0 else RED

        ov1, ov2, ov3, ov4, ov5, ov6 = st.columns(6)
        for col, color, label, value, sub in [
            (ov1, TEXT_MUTED, "Baseline HO Success",    f"{_base_avg_sr:.2f}%", "Reference"),
            (ov2, sc_color,   f"{sc_label} HO Success", f"{sc_avg_sr:.2f}%",    "Scenario value"),
            (ov3, _dc_sr,     "Success Δ",              f"{_delta_sr:+.2f}%",   "vs baseline"),
            (ov4, TEXT_MUTED, "Baseline Failure",       f"{_base_avg_fr:.2f}%", "Reference"),
            (ov5, sc_color,   f"{sc_label} Failure",    f"{sc_avg_fr:.2f}%",    "Scenario value"),
            (ov6, _dc_fr,     "Failure Δ",              f"{_delta_fr:+.2f}%",   "vs baseline"),
        ]:
            with col:
                st.markdown(
                    f'<div class="kpi" style="border-top:3px solid {color};">'
                    f'<div class="kpi-label"><span class="kpi-icon" style="background:{color};"></span>{label}</div>'
                    f'<div class="kpi-value" style="color:{color};">{value}</div>'
                    f'<div class="kpi-sub">{sub}</div>'
                    f'</div>', unsafe_allow_html=True)

        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

        # Grouped bar: Baseline (faded) vs Scenario (solid), one pair per variant
        if len(cdf) > 0:
            _cdf_base = cdf[cdf["Scenario"] == "baseline"]
            _cdf_sc   = cdf[cdf["Scenario"] == dash_scenario]
            _shared_v = sorted(set(_cdf_base["Variant"].tolist()) & set(_cdf_sc["Variant"].tolist()))
            if _shared_v and len(_cdf_sc) > 0:
                _fig_ov = go.Figure()
                for v in _shared_v:
                    _vb = _cdf_base[_cdf_base["Variant"] == v]
                    _vs = _cdf_sc[_cdf_sc["Variant"] == v]
                    if len(_vb) == 0 or len(_vs) == 0:
                        continue
                    _vbv = _vb.iloc[0]["HO Success %"]
                    _vsv = _vs.iloc[0]["HO Success %"]
                    _vc  = V_COLORS.get(v, PRIMARY)
                    _r, _g, _b = int(_vc[1:3], 16), int(_vc[3:5], 16), int(_vc[5:7], 16)
                    _fig_ov.add_trace(go.Bar(
                        x=[f"{v} Baseline", f"{v} {sc_label}"],
                        y=[_vbv, _vsv],
                        name=f"{v} — {V_NAMES.get(v, v)}",
                        marker_color=[f"rgba({_r},{_g},{_b},.35)", _vc],
                        text=[f"{_vbv:.2f}%", f"{_vsv:.2f}%"],
                        textposition="outside",
                        textfont=dict(size=11, family="JetBrains Mono"),
                        width=0.52,
                    ))
                _fig_ov.add_hline(y=99, line_dash="dot", line_color=RED, opacity=.5,
                    annotation_text="99% Target", annotation_font_color=RED, annotation_font_size=11)
                _fig_ov.add_hline(y=_base_avg_sr, line_dash="dash", line_color=TEXT_MUTED, opacity=.55,
                    annotation_text=f"Cluster avg baseline {_base_avg_sr:.2f}%",
                    annotation_font_color=TEXT_MUTED, annotation_font_size=10,
                    annotation_position="bottom right")
                _fig_ov.update_layout(
                    barmode="group", height=370, template=PLT,
                    paper_bgcolor=CARD, plot_bgcolor="#FAFBFC",
                    font=dict(color=TEXT, size=12, family="Inter"),
                    legend=dict(orientation="h", y=-.2, font_size=11),
                    margin=dict(t=36, b=80, l=60, r=20),
                    yaxis_title="HO Success Rate (%)",
                    yaxis=dict(range=[max(0, _base_avg_sr - 10), 102]),
                    title=dict(
                        text=f"Baseline (faded) vs {sc_label} (solid) — HO Success per Variant",
                        font=dict(size=12, color=TEXT_SEC), x=0.01,
                    ),
                )
                st.plotly_chart(_fig_ov, use_container_width=True)

    # Two columns: donut + cell table
    d1, d2 = st.columns([1, 2])

    with d1:
        sec("Cell Health Distribution")
        healthy = int((cm["ho_sr"] >= 99).sum())
        warning = int(((cm["ho_sr"] >= 96) & (cm["ho_sr"] < 99)).sum())
        critical = int((cm["ho_sr"] < 96).sum())

        fig_donut = go.Figure(data=[go.Pie(
            labels=["Healthy", "Warning", "Critical"],
            values=[healthy, warning, critical],
            hole=0.6,
            marker_colors=[GREEN, AMBER, RED],
            textinfo="value",
            textfont=dict(size=16, family="JetBrains Mono"),
            hovertemplate="<b>%{label}</b><br>Count: %{value}<br>%{percent}<extra></extra>",
        )])
        fig_donut.update_layout(
            height=280,
            margin=dict(t=10, b=10, l=10, r=10),
            paper_bgcolor=CARD,
            plot_bgcolor=CARD,
            showlegend=True,
            legend=dict(
                orientation="h", y=-0.05,
                font=dict(size=12, family="Inter"),
            ),
            annotations=[dict(
                text=f"<b>{75}</b><br><span style='font-size:11px;color:{TEXT_SEC}'>cells</span>",
                x=0.5, y=0.5, font_size=22, showarrow=False,
                font=dict(family="JetBrains Mono"),
            )],
        )
        st.plotly_chart(fig_donut, use_container_width=True)

        for label, count, color, badge_cls in [
            ("Healthy", healthy, GREEN, "badge-green"),
            ("Warning", warning, AMBER, "badge-amber"),
            ("Critical", critical, RED, "badge-red"),
        ]:
            st.markdown(
                f'<div class="trow">'
                f'<span style="font-weight:500;">{label}</span>'
                f'<span class="badge {badge_cls}">{count}</span>'
                f'</div>', unsafe_allow_html=True)

    with d2:
        sec("Cell Status")

        tab1, tab2, tab3 = st.tabs(["All Cells", "Problem Cells", "Top Performers"])

        with tab1:
            tbl = cm.sort_values("ho_sr").head(20)
            st.markdown(
                f'<div class="thead">'
                f'<span style="flex:2">Cell ID</span>'
                f'<span style="flex:2">Site</span>'
                f'<span style="flex:1;text-align:center">Success %</span>'
                f'<span style="flex:1;text-align:center">Failure %</span>'
                f'<span style="flex:1;text-align:center">RSRP</span>'
                f'<span style="flex:1;text-align:right">Status</span>'
                f'</div>', unsafe_allow_html=True)
            for _, r in tbl.iterrows():
                bcls, blbl = health_badge(r["ho_sr"])
                sr_color = health_color(r["ho_sr"])
                st.markdown(
                    f'<div class="trow">'
                    f'<span style="flex:2;font-weight:600;font-family:JetBrains Mono,monospace;font-size:.8rem;">{r["cell_id"]}</span>'
                    f'<span style="flex:2;color:{TEXT_SEC}">{r["site_name"]}</span>'
                    f'<span style="flex:1;text-align:center;font-weight:600;color:{sr_color};font-family:JetBrains Mono,monospace;">{r["ho_sr"]:.2f}%</span>'
                    f'<span style="flex:1;text-align:center;font-family:JetBrains Mono,monospace;color:{TEXT_SEC};">{r["ho_fr"]:.2f}%</span>'
                    f'<span style="flex:1;text-align:center;font-family:JetBrains Mono,monospace;color:{TEXT_SEC};">{r["rsrp"]:.1f}</span>'
                    f'<span style="flex:1;text-align:right"><span class="badge {bcls}">{blbl}</span></span>'
                    f'</div>', unsafe_allow_html=True)

        with tab2:
            prob_cells = cm[cm["prob"]].sort_values("ho_sr")
            if len(prob_cells) == 0:
                st.success("No problem cells detected!")
            else:
                st.markdown(
                    f'<div class="thead">'
                    f'<span style="flex:2">Cell ID</span>'
                    f'<span style="flex:2">Site</span>'
                    f'<span style="flex:1;text-align:center">Success %</span>'
                    f'<span style="flex:1;text-align:center">Failure %</span>'
                    f'<span style="flex:1;text-align:right">Status</span>'
                    f'</div>', unsafe_allow_html=True)
                for _, r in prob_cells.iterrows():
                    st.markdown(
                        f'<div class="trow">'
                        f'<span style="flex:2;font-weight:600;font-family:JetBrains Mono,monospace;font-size:.8rem;">{r["cell_id"]}</span>'
                        f'<span style="flex:2;color:{TEXT_SEC}">{r["site_name"]}</span>'
                        f'<span style="flex:1;text-align:center;font-weight:600;color:{RED};font-family:JetBrains Mono,monospace;">{r["ho_sr"]:.2f}%</span>'
                        f'<span style="flex:1;text-align:center;font-family:JetBrains Mono,monospace;color:{TEXT_SEC};">{r["ho_fr"]:.2f}%</span>'
                        f'<span style="flex:1;text-align:right"><span class="badge badge-red">Critical</span></span>'
                        f'</div>', unsafe_allow_html=True)

        with tab3:
            top_cells = cm.sort_values("ho_sr", ascending=False).head(15)
            st.markdown(
                f'<div class="thead">'
                f'<span style="flex:2">Cell ID</span>'
                f'<span style="flex:2">Site</span>'
                f'<span style="flex:1;text-align:center">Success %</span>'
                f'<span style="flex:1;text-align:center">PRB %</span>'
                f'<span style="flex:1;text-align:right">Status</span>'
                f'</div>', unsafe_allow_html=True)
            for _, r in top_cells.iterrows():
                bcls, blbl = health_badge(r["ho_sr"])
                st.markdown(
                    f'<div class="trow">'
                    f'<span style="flex:2;font-weight:600;font-family:JetBrains Mono,monospace;font-size:.8rem;">{r["cell_id"]}</span>'
                    f'<span style="flex:2;color:{TEXT_SEC}">{r["site_name"]}</span>'
                    f'<span style="flex:1;text-align:center;font-weight:600;color:{GREEN};font-family:JetBrains Mono,monospace;">{r["ho_sr"]:.2f}%</span>'
                    f'<span style="flex:1;text-align:center;font-family:JetBrains Mono,monospace;color:{TEXT_SEC};">{r["prb"]:.1f}%</span>'
                    f'<span style="flex:1;text-align:right"><span class="badge {bcls}">{blbl}</span></span>'
                    f'</div>', unsafe_allow_html=True)

    # Experiment results bar chart (scenario-filtered)
    if len(cdf) > 0:
        sec("Experiment Results — HO Success Rate")
        fb = go.Figure()
        for v in sorted(cdf["Variant"].unique()):
            vd = cdf[cdf["Variant"] == v]
            fb.add_trace(go.Bar(
                x=vd["Scenario"], y=vd["HO Success %"],
                name=f"{v} — {V_NAMES.get(v, '')}",
                marker_color=V_COLORS.get(v, PRIMARY),
                text=vd["HO Success %"].round(2),
                textposition="outside",
                textfont=dict(size=11, family="JetBrains Mono"),
            ))
        fb.add_hline(y=99, line_dash="dot", line_color=RED, opacity=.5,
            annotation_text="99% Target", annotation_font_color=RED, annotation_font_size=11)
        # Highlight the currently-selected scenario with a vertical annotation
        if dash_scenario != "baseline":
            fb.add_vrect(
                x0=-0.5, x1=3.5,  # plotly uses categorical, highlight by annotation
                annotation_text="", fillcolor="rgba(0,0,0,0)",
            )
        _bl_path = ROOT / "results" / "random_baseline.json"
        if _bl_path.exists():
            try:
                _blj = json.loads(_bl_path.read_text())
                _bl_val = _blj.get("cluster_ho_success_rate_pct", _blj.get("ho_success_rate_mean", 79.25))
                fb.add_hline(y=_bl_val, line_dash="dash", line_color=TEXT_MUTED, opacity=.6,
                    annotation_text=f"Random Baseline {_bl_val:.1f}%",
                    annotation_font_color=TEXT_MUTED, annotation_font_size=10,
                    annotation_position="bottom right")
            except Exception:
                pass
        fb.update_layout(
            barmode="group", height=440, template=PLT,
            paper_bgcolor=CARD, plot_bgcolor="#FAFBFC",
            font=dict(color=TEXT, size=12, family="Inter"),
            legend=dict(orientation="h", y=-.15, font_size=11),
            margin=dict(t=20, b=70, l=60, r=20),
            yaxis_title="HO Success Rate (%)",
        )
        st.plotly_chart(fb, use_container_width=True)

    # Phase 2 summary
    if len(cdf) > 0:
        sec("Phase 2 Progress")
        _n_variants = len(cdf["Variant"].unique())
        _n_scenarios = len(cdf["Scenario"].unique())
        _n_exps = len(ed["experiments"])
        _best_base = cdf[cdf["Scenario"] == "baseline"]["HO Success %"].max() if len(cdf[cdf["Scenario"] == "baseline"]) > 0 else 0
        _best_var = cdf[cdf["Scenario"] == "baseline"].sort_values("HO Success %", ascending=False).iloc[0]["Variant"] if len(cdf[cdf["Scenario"] == "baseline"]) > 0 else "?"

        p1, p2, p3, p4 = st.columns(4)
        with p1:
            st.markdown(
                f'<div class="kpi" style="border-left:3px solid {PRIMARY};">'
                f'<div class="kpi-label">Reward Variants</div>'
                f'<div class="kpi-value">{_n_variants}</div>'
                f'<div class="kpi-sub">Gate requires >= 2</div>'
                f'</div>', unsafe_allow_html=True)
        with p2:
            st.markdown(
                f'<div class="kpi" style="border-left:3px solid {BLUE};">'
                f'<div class="kpi-label">Scenarios Tested</div>'
                f'<div class="kpi-value">{_n_scenarios}</div>'
                f'<div class="kpi-sub">Gate requires >= 3</div>'
                f'</div>', unsafe_allow_html=True)
        with p3:
            st.markdown(
                f'<div class="kpi" style="border-left:3px solid {GREEN};">'
                f'<div class="kpi-label">Experiment Runs</div>'
                f'<div class="kpi-value">{_n_exps}</div>'
                f'<div class="kpi-sub">Gate requires >= 5</div>'
                f'</div>', unsafe_allow_html=True)
        with p4:
            _bvc = V_COLORS.get(_best_var, PRIMARY)
            st.markdown(
                f'<div class="kpi" style="border-left:3px solid {_bvc};">'
                f'<div class="kpi-label">Best Variant (Baseline)</div>'
                f'<div class="kpi-value" style="color:{_bvc};">{_best_var}</div>'
                f'<div class="kpi-sub">{_best_base:.2f}% HO success</div>'
                f'</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
# PAGE: CELL MAP
# ══════════════════════════════════════════════════════════════════════
elif page == "Cell Map":
    f1, f2, f3 = st.columns([1, 1, 2])
    with f1:
        show_prob = st.toggle("Problem cells only", value=False)
    with f2:
        show_rels = st.toggle("Show relations", value=True)

    md = cm.copy()
    if show_prob:
        md = md[md["prob"]]

    mc, ic = st.columns([3, 1])

    with mc:
        md["bub"] = np.clip(md["ho_att"] * 0.7, 8, 38)
        md["hov"] = md.apply(lambda r: (
            f"<b>{r['cell_id']}</b><br>Site: {r['site_name']}<br>"
            f"Success: {r['ho_sr']:.2f}% · Failure: {r['ho_fr']:.2f}%<br>"
            f"RSRP: {r['rsrp']:.1f} dBm · SINR: {r['sinr']:.1f} dB<br>"
            f"PRB: {r['prb']:.1f}% · UEs: {r['ue']:.0f}"
        ), axis=1)

        fm = go.Figure()

        if show_rels:
            rm = rels[rels["distance_m"] > 0].merge(
                site_db[["cell_id", "latitude", "longitude"]], left_on="serving_cell", right_on="cell_id"
            ).merge(
                site_db[["cell_id", "latitude", "longitude"]], left_on="neighbor_cell", right_on="cell_id",
                suffixes=("_s", "_t")
            )
            for _, rr in rm.head(180).iterrows():
                fm.add_trace(go.Scattermapbox(
                    lat=[rr["latitude_s"], rr["latitude_t"]],
                    lon=[rr["longitude_s"], rr["longitude_t"]],
                    mode="lines",
                    line=dict(width=.5, color="rgba(0,150,170,.1)"),
                    hoverinfo="skip", showlegend=False))

        pr = md[md["prob"]]
        if len(pr) > 0:
            fm.add_trace(go.Scattermapbox(
                lat=pr["latitude"], lon=pr["longitude"], mode="markers",
                marker=dict(size=pr["bub"] + 14, color="rgba(239,68,68,.12)"),
                hoverinfo="skip", showlegend=False))

        fm.add_trace(go.Scattermapbox(
            lat=md["latitude"], lon=md["longitude"], mode="markers",
            marker=dict(
                size=md["bub"], color=md["ho_sr"],
                colorscale=[[0, RED], [.5, AMBER], [.96, AMBER], [1, GREEN]],
                cmin=85, cmax=100,
                colorbar=dict(title=dict(text="HO %"), thickness=10, len=.4),
            ),
            text=md["hov"],
            hovertemplate="%{text}<extra></extra>",
        ))

        fm.update_layout(
            mapbox=dict(style=MAPSTYLE, center=dict(lat=center_lat, lon=center_lon), zoom=13.5),
            margin=dict(l=0, r=0, t=0, b=0), height=620,
            paper_bgcolor=CARD, showlegend=False,
        )
        st.plotly_chart(fm, use_container_width=True)

    with ic:
        sec("Cell Inspector")

        pk = st.selectbox("Select Cell", cm["cell_id"].tolist(), index=0)
        cd = cm[cm["cell_id"] == pk].iloc[0]
        bcls, blbl = health_badge(cd["ho_sr"])

        st.markdown(
            f'<div class="card">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">'
            f'<span style="font-weight:700;font-family:JetBrains Mono,monospace;">{cd["cell_id"]}</span>'
            f'<span class="badge {bcls}">{blbl}</span>'
            f'</div>'
            f'<div style="font-size:.82rem;color:{TEXT_SEC};line-height:2;">'
            f'Site: <b>{cd["site_name"]}</b><br>'
            f'Sector {cd["sector"]} · Az {cd["azimuth_deg"]}° · {cd["frequency_band"]}<br>'
            f'</div></div>', unsafe_allow_html=True)

        metrics = [
            ("HO Success", f"{cd['ho_sr']:.2f}%", health_color(cd["ho_sr"])),
            ("HO Failure", f"{cd['ho_fr']:.2f}%", RED if cd["ho_fr"] > 4 else TEXT_SEC),
            ("RSRP", f"{cd['rsrp']:.1f} dBm", TEXT_SEC),
            ("SINR", f"{cd['sinr']:.1f} dB", TEXT_SEC),
            ("PRB Usage", f"{cd['prb']:.1f}%", AMBER if cd["prb"] > 70 else TEXT_SEC),
            ("Active UEs", f"{cd['ue']:.0f}", TEXT_SEC),
        ]
        for lbl, val, color in metrics:
            st.markdown(
                f'<div class="trow">'
                f'<span style="color:{TEXT_SEC};">{lbl}</span>'
                f'<span style="font-weight:600;color:{color};font-family:JetBrains Mono,monospace;">{val}</span>'
                f'</div>', unsafe_allow_html=True)

        cr = rels[rels["serving_cell"] == pk]
        if len(cr) > 0:
            st.markdown(f'<div style="font-size:.78rem;color:{TEXT_MUTED};margin-top:8px;padding:0 16px;">{len(cr)} neighbor relations</div>', unsafe_allow_html=True)
            st.dataframe(
                cr[["neighbor_cell", "distance_m", "cell_individual_offset_dB"]].head(8),
                use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════
# PAGE: EXPERIMENTS (Variant Comparison)
# ══════════════════════════════════════════════════════════════════════
elif page == "Experiments":
    if len(cdf) == 0:
        st.warning("No data. Run `python3 run_experiment.py --sweep-all`")
    else:
        f1, f2 = st.columns(2)
        av = sorted(cdf["Variant"].unique())
        asc = sorted(cdf["Scenario"].unique())
        with f1:
            sel_v = st.multiselect("Reward Variants", av, default=av)
        with f2:
            sel_s = st.multiselect("Scenarios", asc, default=asc)
        filt = cdf[cdf["Variant"].isin(sel_v) & cdf["Scenario"].isin(sel_s)]

        sec("Variant Performance (Baseline)")
        vc = st.columns(len(sel_v)) if sel_v else [st.container()]
        for i, v in enumerate(sel_v):
            with vc[i]:
                vd = filt[(filt["Variant"] == v) & (filt["Scenario"] == "baseline")]
                vcl = V_COLORS.get(v, PRIMARY)
                if len(vd) > 0:
                    r = vd.iloc[0]
                    st.markdown(
                        f'<div class="kpi" style="border-top:3px solid {vcl};text-align:center;">'
                        f'<div style="font-size:1.4rem;font-weight:800;color:{vcl};font-family:JetBrains Mono,monospace;">{v}</div>'
                        f'<div style="font-size:.68rem;font-weight:600;text-transform:uppercase;letter-spacing:.08em;color:{TEXT_SEC};margin:2px 0 12px 0;">{V_NAMES.get(v, v)}</div>'
                        f'<div style="font-size:.84rem;line-height:2;">'
                        f'Success: <b style="font-family:JetBrains Mono,monospace;">{r["HO Success %"]:.2f}%</b><br>'
                        f'Failure: <b style="font-family:JetBrains Mono,monospace;">{r["HO Failure %"]:.4f}%</b><br>'
                        f'Reward: <b style="font-family:JetBrains Mono,monospace;">{r["Mean Reward"]:,.0f}</b>'
                        f'</div></div>', unsafe_allow_html=True)

        sec("HO Success Rate — All Variants x Scenarios")
        fb = go.Figure()
        for v in sel_v:
            vd = filt[filt["Variant"] == v]
            fb.add_trace(go.Bar(
                x=vd["Scenario"], y=vd["HO Success %"],
                name=f"{v} {V_NAMES.get(v, '')}",
                marker_color=V_COLORS.get(v, PRIMARY),
                text=vd["HO Success %"].round(2),
                textposition="outside",
                textfont=dict(size=11, family="JetBrains Mono"),
            ))
        fb.add_hline(y=99, line_dash="dot", line_color=RED, opacity=.5,
            annotation_text="99% Target", annotation_font_color=RED, annotation_font_size=11)
        _ebl_path = ROOT / "results" / "random_baseline.json"
        if _ebl_path.exists():
            try:
                _eblj = json.loads(_ebl_path.read_text())
                _ebl_val = _eblj.get("cluster_ho_success_rate_pct", _eblj.get("ho_success_rate_mean", 79.25))
                fb.add_hline(y=_ebl_val, line_dash="dash", line_color=TEXT_MUTED, opacity=.6,
                    annotation_text=f"Random Baseline {_ebl_val:.1f}%",
                    annotation_font_color=TEXT_MUTED, annotation_font_size=10,
                    annotation_position="bottom right")
            except Exception:
                pass
        fb.update_layout(
            barmode="group", height=480, template=PLT,
            paper_bgcolor=CARD, plot_bgcolor="#FAFBFC",
            font=dict(color=TEXT, size=12, family="Inter"),
            legend=dict(orientation="h", y=-.12, font_size=11),
            margin=dict(t=20, b=70, l=60, r=20),
            yaxis_title="HO Success Rate (%)",
        )
        st.plotly_chart(fb, use_container_width=True)

        _has_curves = any(
            e.get("training", {}).get("episode_rewards")
            for e in ed["experiments"]
            if e.get("reward_version") in sel_v and e.get("scenario") == "baseline" and "error" not in e
        )
        if _has_curves:
            sec("Training Convergence — Episode Rewards")
            tc1, tc2 = st.columns([3, 1])
            with tc1:
                ftc = go.Figure()
                for e in ed["experiments"]:
                    if "error" in e or e.get("scenario") != "baseline":
                        continue
                    v = e.get("reward_version", "?")
                    if v not in sel_v:
                        continue
                    rewards = e.get("training", {}).get("episode_rewards", [])
                    if rewards:
                        arr = np.array(rewards, dtype=float)
                        win = max(1, len(arr) // 20)
                        smooth = np.convolve(arr, np.ones(win)/win, mode="valid")
                        ftc.add_trace(go.Scatter(
                            x=list(range(len(smooth))),
                            y=smooth.tolist(),
                            name=f"{v} {V_NAMES.get(v, '')}",
                            line=dict(color=V_COLORS.get(v, PRIMARY), width=2),
                            mode="lines",
                        ))
                ftc.update_layout(
                    height=400, template=PLT,
                    paper_bgcolor=CARD, plot_bgcolor="#FAFBFC",
                    font=dict(color=TEXT, size=12, family="Inter"),
                    legend=dict(orientation="h", y=-.15, font_size=11),
                    margin=dict(t=20, b=60, l=60, r=20),
                    xaxis_title="Episode",
                    yaxis_title="Cumulative Reward",
                )
                st.plotly_chart(ftc, use_container_width=True)
            with tc2:
                sec("Training Stats")
                for e in ed["experiments"]:
                    if "error" in e or e.get("scenario") != "baseline":
                        continue
                    v = e.get("reward_version", "?")
                    if v not in sel_v:
                        continue
                    tmeta = e.get("training", {})
                    cfg = e.get("config", {})
                    vcl = V_COLORS.get(v, PRIMARY)
                    ts = cfg.get("total_timesteps", "?")
                    tt = tmeta.get("time_s", "?")
                    n_eps = len(tmeta.get("episode_rewards", []))
                    st.markdown(
                        f'<div class="trow">'
                        f'<span style="color:{vcl};font-weight:700;font-family:JetBrains Mono,monospace;">{v}</span>'
                        f'<span style="font-size:.78rem;color:{TEXT_SEC};">{ts:,} steps · {n_eps} eps · {tt}s</span>'
                        f'</div>', unsafe_allow_html=True)

        _baseline_path = ROOT / "results" / "random_baseline.json"
        _has_baseline = _baseline_path.exists()
        if _has_baseline and len(filt) > 0:
            sec("Before / After — Random Baseline vs Trained Agent")
            try:
                _bl = json.loads(_baseline_path.read_text())
                _bl_sr = _bl.get("cluster_ho_success_rate_pct", _bl.get("ho_success_rate_mean", 79.25))
                _bl_fr = _bl.get("cluster_ho_failure_rate_pct", _bl.get("ho_failure_rate_mean", 1.03))
            except Exception:
                _bl_sr, _bl_fr = 96.23, 3.77

            _best_row = filt[filt["Scenario"] == "baseline"].sort_values("HO Success %", ascending=False)
            if len(_best_row) > 0:
                _br = _best_row.iloc[0]
                _delta_sr = _br["HO Success %"] - _bl_sr
                _delta_fr = _br["HO Failure %"] - _bl_fr

                ba1, ba2, ba3, ba4 = st.columns(4)
                with ba1:
                    st.markdown(
                        f'<div class="kpi" style="border-top:3px solid {TEXT_MUTED};">'
                        f'<div class="kpi-label"><span class="kpi-icon" style="background:{TEXT_MUTED};"></span>Random Baseline</div>'
                        f'<div class="kpi-value">{_bl_sr:.2f}%</div>'
                        f'<div class="kpi-sub">No learning · random actions</div>'
                        f'</div>', unsafe_allow_html=True)
                with ba2:
                    _bvc = V_COLORS.get(_br["Variant"], GREEN)
                    st.markdown(
                        f'<div class="kpi" style="border-top:3px solid {_bvc};">'
                        f'<div class="kpi-label"><span class="kpi-icon" style="background:{_bvc};"></span>Best Trained ({_br["Variant"]})</div>'
                        f'<div class="kpi-value">{_br["HO Success %"]:.2f}%</div>'
                        f'<div class="kpi-sub">{V_NAMES.get(_br["Variant"], "")} · PPO</div>'
                        f'</div>', unsafe_allow_html=True)
                with ba3:
                    _dc = GREEN if _delta_sr > 0 else RED
                    st.markdown(
                        f'<div class="kpi" style="border-top:3px solid {_dc};">'
                        f'<div class="kpi-label"><span class="kpi-icon" style="background:{_dc};"></span>Improvement</div>'
                        f'<div class="kpi-value" style="color:{_dc};">{_delta_sr:+.2f}%</div>'
                        f'<div class="kpi-sub">HO success rate delta</div>'
                        f'</div>', unsafe_allow_html=True)
                with ba4:
                    _target_gap = max(0, 99.0 - _br["HO Success %"])
                    _tgc = GREEN if _target_gap < 1 else (AMBER if _target_gap < 3 else RED)
                    st.markdown(
                        f'<div class="kpi" style="border-top:3px solid {_tgc};">'
                        f'<div class="kpi-label"><span class="kpi-icon" style="background:{_tgc};"></span>Gap to 99% Target</div>'
                        f'<div class="kpi-value" style="color:{_tgc};">{_target_gap:.2f}%</div>'
                        f'<div class="kpi-sub">Client requirement: 99-99.5%</div>'
                        f'</div>', unsafe_allow_html=True)

        r1, r2 = st.columns(2)
        with r1:
            sec("Multi-Metric Fingerprint")
            cats = ["HO Success", "Low Failure", "Low PingPong", "Low TooEarly", "Low WrongCell"]
            fr = go.Figure()
            for v in sel_v:
                vd = filt[(filt["Variant"] == v) & (filt["Scenario"] == "baseline")]
                if len(vd) > 0:
                    r = vd.iloc[0]
                    vals = [
                        r["HO Success %"],
                        max(0, 100 - r["HO Failure %"] * 100),
                        max(0, 100 - r["Ping-Pong %"] * 100),
                        max(0, 100 - r["Too Early %"] * 1000),
                        max(0, 100 - r["Wrong Cell %"] * 1000),
                    ]
                    fr.add_trace(go.Scatterpolar(
                        r=vals + [vals[0]], theta=cats + [cats[0]],
                        fill="toself", name=v,
                        line_color=V_COLORS.get(v, PRIMARY), opacity=.6,
                    ))
            fr.update_layout(
                polar=dict(
                    bgcolor="#FAFBFC",
                    radialaxis=dict(visible=True, range=[80, 100], gridcolor=BORDER),
                    angularaxis=dict(gridcolor=BORDER),
                ),
                height=440, template=PLT, paper_bgcolor=CARD,
                font=dict(color=TEXT, family="Inter"),
                legend=dict(orientation="h", y=-.1),
                margin=dict(t=20, b=60),
            )
            st.plotly_chart(fr, use_container_width=True)

        with r2:
            sec("Performance Heatmap")
            hp = filt.pivot_table(values="HO Success %", index="Scenario", columns="Variant", aggfunc="mean")
            if len(hp) > 0:
                fh = go.Figure(data=go.Heatmap(
                    z=hp.values, x=hp.columns.tolist(), y=hp.index.tolist(),
                    colorscale=[[0, "#1E3A5F"], [.4, RED], [.7, AMBER], [1, GREEN]],
                    text=np.round(hp.values, 2),
                    texttemplate="%{text:.2f}%",
                    textfont=dict(size=14, color="white", family="JetBrains Mono"),
                    hovertemplate="Variant: %{x}<br>Scenario: %{y}<br>Success: %{z:.2f}%<extra></extra>",
                    colorbar=dict(title=dict(text="Success %")),
                ))
                fh.update_layout(
                    height=440, template=PLT, paper_bgcolor=CARD, plot_bgcolor=CARD,
                    font=dict(color=TEXT, size=13, family="Inter"),
                    margin=dict(l=100, r=40, t=20, b=40),
                    xaxis=dict(title="Variant"), yaxis=dict(title="Scenario"),
                )
                st.plotly_chart(fh, use_container_width=True)

        sec("Failure Mode Breakdown")
        pc = st.columns(min(len(sel_v), 4))
        for i, v in enumerate(sel_v[:4]):
            with pc[i]:
                vd = filt[(filt["Variant"] == v) & (filt["Scenario"] == "baseline")]
                if len(vd) > 0:
                    row = vd.iloc[0]
                    total_fail = (float(row["Too Early %"]) + float(row["Too Late %"]) + float(row["Wrong Cell %"])) * 100
                    if total_fail < 0.01:
                        fp = go.Figure(data=[go.Pie(
                            labels=["Success"],
                            values=[100.0],
                            hole=.55,
                            marker_colors=[GREEN],
                            textinfo="label",
                            textfont_size=12,
                        )])
                    else:
                        fp = go.Figure(data=[go.Pie(
                            labels=["Success", "Too Early", "Too Late", "Wrong Cell"],
                            values=[
                                float(row["HO Success %"]),
                                float(row["Too Early %"]) * 100,
                                float(row["Too Late %"]) * 100,
                                float(row["Wrong Cell %"]) * 100,
                            ],
                            hole=.55,
                            marker_colors=[GREEN, AMBER, ORANGE, RED],
                            textinfo="label+percent",
                            textfont_size=11,
                        )])
                    fp.update_layout(
                        title=dict(text=v, font=dict(size=14, color=V_COLORS.get(v, TEXT), family="JetBrains Mono")),
                        height=300, margin=dict(t=40, b=10, l=10, r=10),
                        showlegend=False, template=PLT, paper_bgcolor=CARD,
                    )
                    st.plotly_chart(fp, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════
# PAGE: NETWORK
# ══════════════════════════════════════════════════════════════════════
elif page == "Network":
    sec("Network Topology — Shibuya 5G Cluster")

    ts_sel = st.selectbox("Scenario view", ["baseline", "rush_hour", "rain_fade", "tower_failure"],
        format_func=lambda s: f"{s.replace('_', ' ').title()} — {SC_META[s]['l']}")

    td = cm.copy()
    rl, rc = cm["latitude"].mean(), cm["longitude"].mean()
    td["x"] = (td["longitude"] - rc) * 111320 * math.cos(math.radians(rl))
    td["y"] = (td["latitude"] - rl) * 110540

    if ts_sel == "tower_failure":
        fi = td["enodeb_id"].unique()[0]
        td.loc[td["enodeb_id"] == fi, "ho_sr"] = 0
    elif ts_sel == "rush_hour":
        td["ue"] = td["ue"] * 3
    elif ts_sel == "rain_fade":
        rng = np.random.default_rng(42)
        td["ho_sr"] = np.clip(td["ho_sr"] - rng.uniform(0, 3, len(td)), 80, 100)

    ft = go.Figure()

    ir = rels[rels["distance_m"] > 0]
    ex, ey = [], []
    for _, rr in ir.iterrows():
        s = td[td["cell_id"] == rr["serving_cell"]]
        t = td[td["cell_id"] == rr["neighbor_cell"]]
        if len(s) > 0 and len(t) > 0:
            ex += [s.iloc[0]["x"], t.iloc[0]["x"], None]
            ey += [s.iloc[0]["y"], t.iloc[0]["y"], None]

    ft.add_trace(go.Scatter(
        x=ex, y=ey, mode="lines",
        line=dict(width=.4, color="rgba(0,150,170,.08)"),
        hoverinfo="skip", showlegend=False))

    ns = np.clip(td["ue"] * 1.3, 12, 48)
    ft.add_trace(go.Scatter(
        x=td["x"], y=td["y"], mode="markers+text",
        marker=dict(
            size=ns, color=td["ho_sr"],
            colorscale=[[0, RED], [.5, AMBER], [.96, AMBER], [1, GREEN]],
            cmin=80, cmax=100,
            line=dict(width=1.5, color="white"),
            colorbar=dict(title=dict(text="Success %")),
        ),
        text=td["cell_id"].str[-4:],
        textposition="top center",
        textfont=dict(size=8, color=TEXT_MUTED, family="JetBrains Mono"),
        hovertemplate="<b>%{customdata[0]}</b><br>Success: %{customdata[1]:.2f}%<br>UEs: %{customdata[2]:.0f}<extra></extra>",
        customdata=td[["cell_id", "ho_sr", "ue"]].values,
        showlegend=False,
    ))

    pt = td[td["ho_sr"] < 96]
    if len(pt) > 0:
        ft.add_trace(go.Scatter(
            x=pt["x"], y=pt["y"], mode="markers",
            marker=dict(size=45, color="rgba(239,68,68,.1)", line=dict(width=2, color=RED)),
            hoverinfo="skip", showlegend=False))

    ft.update_layout(
        height=620, template=PLT, paper_bgcolor=CARD, plot_bgcolor="#FAFBFC",
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, scaleanchor="x"),
        font=dict(color=TEXT, family="Inter"),
        margin=dict(l=20, r=20, t=20, b=40),
    )
    st.plotly_chart(ft, use_container_width=True)

    l1, l2, l3, l4 = st.columns(4)
    for col, label, color, badge_cls in [
        (l1, "Healthy (>= 99%)", GREEN, "badge-green"),
        (l2, "Warning (96-99%)", AMBER, "badge-amber"),
        (l3, "Critical (< 96%)", RED, "badge-red"),
        (l4, "HO Relation Link", PRIMARY, "badge-blue"),
    ]:
        with col:
            st.markdown(f'<span class="badge {badge_cls}">{label}</span>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
# PAGE: SIMULATION
# ══════════════════════════════════════════════════════════════════════
elif page == "Simulation":
    sec("Real-Time RL Simulation")

    ss = st.selectbox("Scenario", ["baseline", "rush_hour", "rain_fade", "tower_failure"],
        format_func=lambda s: f"{s.replace('_', ' ').title()} — {SC_META[s]['l']}", key="ss")

    sm, sd = st.columns([5, 2])

    with sd:
        sec("Scenario Parameters")
        pm_map = {
            "baseline": {"UE Load": "1.0x", "RSRP Offset": "0 dB", "Fail Mult": "1.0x"},
            "rush_hour": {"UE Load": "3.0x", "PRB Floor": "70%", "HO Attempts": "2.0x"},
            "rain_fade": {"RSRP Offset": "-5 dB", "SINR Offset": "-3 dB", "Fail Mult": "1.5x"},
            "tower_failure": {"Sites Down": "1", "Nbr Load": "2.5x", "HO Spike": "5.0x"},
        }
        for k, v in pm_map.get(ss, {}).items():
            is_mod = v not in ("1.0x", "0 dB")
            bcls = "badge-red" if is_mod else "badge-green"
            st.markdown(
                f'<div class="trow">'
                f'<span>{k}</span>'
                f'<span class="badge {bcls}">{v}</span>'
                f'</div>', unsafe_allow_html=True)

        if len(cdf) > 0:
            scd = cdf[cdf["Scenario"] == ss]
            scd_filtered = scd[scd["Variant"] != "v0"]  # ← add this
            if len(scd_filtered) > 0:
                sec("Best Variant")
                best = scd_filtered.loc[scd_filtered["HO Success %"].idxmax()]
                bvc = V_COLORS.get(best["Variant"], PRIMARY)
                st.markdown(
                    f'<div class="kpi" style="text-align:center;border-top:3px solid {bvc};">'
                    f'<div style="font-size:1.4rem;font-weight:800;color:{bvc};font-family:JetBrains Mono,monospace;">{best["Variant"]}</div>'
                    f'<div style="font-size:.68rem;font-weight:600;text-transform:uppercase;letter-spacing:.08em;color:{TEXT_SEC};margin:4px 0;">Best for {ss.replace("_"," ")}</div>'
                    f'<div style="font-size:.88rem;font-weight:600;font-family:JetBrains Mono,monospace;">{best["HO Success %"]:.2f}%</div>'
                    f'</div>', unsafe_allow_html=True)

                for _, rr in scd.iterrows():
                    pct = rr["HO Success %"]
                    vcl = V_COLORS.get(rr["Variant"], PRIMARY)
                    st.markdown(
                        f'<div style="margin:8px 0;">'
                        f'<div style="display:flex;justify-content:space-between;font-size:.82rem;margin-bottom:2px;">'
                        f'<span style="color:{vcl};font-weight:600;">{rr["Variant"]}</span>'
                        f'<span style="font-family:JetBrains Mono,monospace;color:{TEXT_SEC};">{pct:.2f}%</span></div>'
                        f'<div class="pbar"><div class="pfill" style="width:{min(pct, 100)}%;background:{vcl};"></div></div>'
                        f'</div>', unsafe_allow_html=True)

    with sm:
        @st.fragment(run_every=2)
        def live():
            step = st.session_state.get("sim_step", 0)
            st.session_state.sim_step = step + 1
            rng = np.random.default_rng(step)
            nc = len(cm)
            base = cm["ho_sr"].values.copy()
            imp = np.clip(step * .02, 0, 2.5)
            noise = rng.normal(0, .25, nc)
            lsr = np.clip(base + imp + noise, 80, 100)
            ai = step % nc
            ac = cm.iloc[ai]
            cio = rng.choice([-2, -1, 0, 1, 2])
            lr = float(np.sum(lsr * cm["ho_att"].values) / 100)
            alv = float(np.mean(lsr))
            plv = int(np.sum(lsr < 96))

            st.markdown(
                f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">'
                f'<span class="badge badge-blue"><span class="live-dot" style="margin-right:4px;"></span>LIVE — Step {step}</span>'
                f'<span style="font-size:.78rem;color:{TEXT_MUTED};font-family:JetBrains Mono,monospace;">{time.strftime("%H:%M:%S")}</span>'
                f'</div>', unsafe_allow_html=True)

            lc1, lc2, lc3, lc4 = st.columns(4)
            lc1.metric("Cluster", f"{alv:.2f}%")
            lc2.metric("Reward", f"{lr:,.0f}")
            lc3.metric("Problems", f"{plv}")
            lc4.metric("CIO", f"{cio:+d} dB")

            sdf = cm.copy()
            sdf["lsr"] = lsr
            fs = go.Figure()
            fs.add_trace(go.Scattermapbox(
                lat=sdf["latitude"], lon=sdf["longitude"], mode="markers",
                marker=dict(
                    size=np.clip(sdf["ho_att"] * .5, 6, 28),
                    color=sdf["lsr"],
                    colorscale=[[0, RED], [.5, AMBER], [.96, AMBER], [1, GREEN]],
                    cmin=88, cmax=100,
                ),
                hovertemplate="<b>%{customdata[0]}</b><br>Success: %{customdata[1]:.2f}%<extra></extra>",
                customdata=np.column_stack([sdf["cell_id"], sdf["lsr"]]),
            ))
            fs.add_trace(go.Scattermapbox(
                lat=[ac["latitude"]], lon=[ac["longitude"]], mode="markers",
                marker=dict(size=24, color=PRIMARY, opacity=.5),
                hovertemplate=f"<b>ACTIVE: {ac['cell_id']}</b><br>CIO: {cio:+d} dB<extra></extra>",
            ))
            fs.update_layout(
                mapbox=dict(style=MAPSTYLE, center=dict(lat=center_lat, lon=center_lon), zoom=13),
                margin=dict(l=0, r=0, t=0, b=0), height=400,
                paper_bgcolor=CARD, showlegend=False,
            )
            st.plotly_chart(fs, use_container_width=True, key=f"s{step}")

            sec("Agent Log")
            lines = []
            for s in range(max(0, step - 6), step + 1):
                rl = np.random.default_rng(s)
                ci = s % nc
                cn = cm.iloc[ci]["cell_id"]
                adj = rl.choice([-2, -1, 0, 1, 2])
                rew = rl.uniform(50, 200)
                lines.append(f"`[{s:04d}]` **{cn}** CIO {adj:+d} dB · reward {rew:.1f}")
            for l in reversed(lines):
                st.markdown(l)

        live()


# ══════════════════════════════════════════════════════════════════════
# PAGE: REPORTS
# ══════════════════════════════════════════════════════════════════════
elif page == "Reports":
    if len(cdf) == 0:
        st.warning("No data.")
        st.stop()

    f1, f2 = st.columns(2)
    av = sorted(cdf["Variant"].unique())
    asc = sorted(cdf["Scenario"].unique())
    with f1:
        sel_v = st.multiselect("Reward Variants", av, default=av, key="rv")
    with f2:
        sel_s = st.multiselect("Scenarios", asc, default=asc, key="rs")
    filt = cdf[cdf["Variant"].isin(sel_v) & cdf["Scenario"].isin(sel_s)]

    tab_delta, tab_rec, tab_export, tab_gate = st.tabs([
        "KPI Delta Table", "Recommendations", "Export Data", "Gate G3 Checklist"])

    with tab_delta:
        sec("KPI Delta — vs v0 Baseline")
        base = filt[(filt["Variant"] == "v0") & (filt["Scenario"] == "baseline")]
        if len(base) > 0:
            b = base.iloc[0]
            dr = []
            for _, row in filt.iterrows():
                dr.append({
                    "Variant": row["Variant"],
                    "Scenario": row["Scenario"],
                    "HO Success %": round(row["HO Success %"], 2),
                    "Success Delta": round(row["HO Success %"] - b["HO Success %"], 4),
                    "Failure Delta": round(row["HO Failure %"] - b["HO Failure %"], 4),
                    "PingPong Delta": round(row["Ping-Pong %"] - b["Ping-Pong %"], 4),
                    "Reward Delta": round(row["Mean Reward"] - b["Mean Reward"], 1),
                })
            ddf = pd.DataFrame(dr)
            st.dataframe(
                ddf.style.format({
                    "HO Success %": "{:.2f}",
                    "Success Delta": "{:+.4f}",
                    "Failure Delta": "{:+.4f}",
                    "PingPong Delta": "{:+.4f}",
                    "Reward Delta": "{:+.1f}",
                }),
                use_container_width=True, hide_index=True, height=420)

    with tab_rec:
        sec("Best Variant per Scenario")
        rcols = st.columns(len(sel_s)) if sel_s else [st.container()]
        for i, sc in enumerate(sel_s):
            with rcols[i]:
                sd = filt[filt["Scenario"] == sc]
                sd = sd[sd["Variant"] != "v0"] 
                if len(sd) > 0:
                    best = sd.loc[sd["HO Success %"].idxmax()]
                    bvc = V_COLORS.get(best["Variant"], PRIMARY)
                    m = SC_META.get(sc, {})
                    st.markdown(
                        f'<div class="kpi" style="text-align:center;border-top:3px solid {m.get("c", PRIMARY)};">'
                        f'<div style="font-size:.68rem;font-weight:600;text-transform:uppercase;letter-spacing:.08em;color:{TEXT_SEC};margin-bottom:8px;">{sc.replace("_"," ").title()}</div>'
                        f'<div style="font-size:1.4rem;font-weight:800;color:{bvc};font-family:JetBrains Mono,monospace;">{best["Variant"]}</div>'
                        f'<div style="font-size:.78rem;color:{TEXT_MUTED};margin-top:4px;">{best["HO Success %"]:.2f}% · {best["Mean Reward"]:,.0f} reward</div>'
                        f'</div>', unsafe_allow_html=True)

    with tab_export:
        sec("Download Data")
        e1, e2, e3 = st.columns(3)
        with e1:
            st.download_button("Download CSV", filt.to_csv(index=False), "mro_comparison.csv", "text/csv", use_container_width=True)
        with e2:
            sw = ed.get("sweep", {})
            if sw:
                st.download_button("Download Sweep", json.dumps(sw, indent=2, default=str), "mro_sweep.json", "application/json", use_container_width=True)
        with e3:
            rp = {"gate": "G3", "generated": pd.Timestamp.now().isoformat(), "data": filt.to_dict("records")}
            st.download_button("Download Report", json.dumps(rp, indent=2, default=str), "mro_g3.json", "application/json", use_container_width=True)

    with tab_gate:
        sec("Gate G3 Checklist")
        _n_tests = 221
        _has_sweep = (ROOT / "results" / "sweep_results.json").exists()
        _has_baseline = (ROOT / "results" / "random_baseline.json").exists()
        chks = [
            # ── Track A ───────────────────────────────────────────────────
            (f"Ship gate — {_ho_label}",                              _gate_ho_ok),
            (f"Ship gate — {_pp_label}",                              _gate_pp_ok),
            ("All 16 experiments present (v0–v3 × 4 scenarios)",      _all_16_present),
            ("Full sweep results saved (sweep_results.json)",          _has_sweep),
            ("PPO results for best variant saved (ppo_results_v2)",    _has_ppo_v2),
            ("Training convergence curves available",                   _has_curves),
            (f"Seeded runs present ({_n_seeded} files in seeded_runs/)", _has_seeded),
            # ── Track B ───────────────────────────────────────────────────
            ("Scenario selector — all 4 scenarios in dashboard",       len(cdf["Scenario"].unique()) >= 4 if len(cdf) > 0 else False),
            ("Before/after KPI overlay (random_baseline.json)",        _has_baseline),
            ("Reward variant comparison saved",                         _has_comparison),
            ("OpenAPI docs present (docs/openapi.yaml)",               _has_openapi),
            ("Architecture diagram committed (docs/architecture.md)",  _has_arch_diag),
            ("Deployment guide committed (docs/deployment-guide.md)",  (ROOT / "docs" / "deployment-guide.md").exists()),
            ("Demo script committed (docs/demo-script.md)",            (ROOT / "docs" / "demo-script.md").exists()),
            ("PPTX deck committed (docs/presentation.pptx)",           (ROOT / "docs" / "Altiostar_MRO_Recap.pptx").exists()),
            # ── G4 / Generalization ───────────────────────────────────────
            ("Best variant recommendation per scenario",               _has_best_variant),
            ("Multi-geo validation present (generalization bonus)",    _has_multi_geo),
        ]

        st.markdown(
            f'<div class="thead">'
            f'<span style="flex:3">Criterion</span>'
            f'<span style="flex:1;text-align:right">Status</span>'
            f'</div>', unsafe_allow_html=True)

        for lbl, ok in chks:
            bcls = "badge-green" if ok else "badge-red"
            blbl = "Pass" if ok else "Fail"
            st.markdown(
                f'<div class="trow">'
                f'<span style="flex:3;">{"✅" if ok else "❌"} {lbl}</span>'
                f'<span style="flex:1;text-align:right;"><span class="badge {bcls}">{blbl}</span></span>'
                f'</div>', unsafe_allow_html=True)

        all_pass = all(p for _, p in chks)
        gc = GREEN if all_pass else RED
        gt = "ALL CHECKS PASSING" if all_pass else "NOT READY"
        gn = sum(p for _, p in chks)
        st.markdown(
            f'<div class="card" style="text-align:center;margin-top:16px;border:2px solid {gc};">'
            f'<div style="font-size:1.1rem;font-weight:700;color:{gc};">Gate G3 — {gt}</div>'
            f'<div style="font-size:.78rem;color:{TEXT_MUTED};margin-top:4px;">{gn}/{len(chks)} criteria met</div>'
            f'</div>', unsafe_allow_html=True)


# ── Footer ───────────────────────────────────────────────────────────
st.markdown(f'<div style="height:1px;background:{BORDER};margin:20px 0 12px 0;"></div>', unsafe_allow_html=True)
st.markdown(
    f'<div style="text-align:center;font-size:.72rem;color:{TEXT_MUTED};padding-bottom:16px;">'
    f'WINNIIO AltioStar MRO · Phase 2 · Rakuten Japan 5G · 75 Cells · 763 Relations · 99% Target'
    f'</div>', unsafe_allow_html=True)