"""IMS — Industrial Monitoring System · Forzy"""
import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

st.set_page_config(
    page_title="IMS · Forzy Industrial",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════════════
# CSS GLOBAL — aplicado em TODAS as páginas via 1_Inicio
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }

/* ── Fundo ── */
[data-testid="stAppViewContainer"]  { background:#060d18; }
[data-testid="stSidebar"]           { background:#080f1c; border-right:1px solid #0f2035; }
[data-testid="stHeader"]            { background:#060d18; border-bottom:1px solid #0f2035; }
section[data-testid="stSidebarContent"] { padding-top:0 !important; }

/* ── Sidebar nav links ── */
[data-testid="stSidebarNavLink"] {
    color:#4a7a9b !important;
    font-size:.82rem;
    font-weight:500;
    border-radius:6px;
    padding:8px 12px !important;
    transition:all .15s;
}
[data-testid="stSidebarNavLink"]:hover {
    background:#0f2035 !important;
    color:#7ec8e3 !important;
}
[data-testid="stSidebarNavLink"][aria-current="page"] {
    background:#0d2040 !important;
    color:#7ec8e3 !important;
    border-left:3px solid #3498db;
}

/* ── Métricas ── */
[data-testid="metric-container"] {
    background:#0a1628;
    border:1px solid #0f2a45;
    border-radius:8px;
    padding:14px 16px 10px;
}
[data-testid="stMetricLabel"] { color:#4a7a9b !important; font-size:.72rem; text-transform:uppercase; letter-spacing:.07em; }
[data-testid="stMetricValue"] { color:#e2eaf4 !important; font-size:1.4rem; font-weight:700; }
[data-testid="stMetricDelta"] svg { display:none; }

/* ── Tabs ── */
[data-testid="stTabs"] [role="tablist"] { border-bottom:1px solid #0f2035; gap:2px; }
[data-testid="stTabs"] button[role="tab"] {
    color:#4a7a9b; font-size:.8rem; font-weight:600;
    letter-spacing:.05em; padding:8px 20px;
    border-radius:4px 4px 0 0;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color:#7ec8e3 !important;
    background:#0a1628 !important;
    border-bottom:2px solid #3498db;
}

/* ── Divider ── */
hr { border-color:#0f2035 !important; margin:10px 0 !important; }

/* ── Expander ── */
[data-testid="stExpander"] {
    border:1px solid #0f2035 !important;
    border-radius:8px !important;
    background:#08111f !important;
}

/* ── Botões ── */
[data-testid="stButton"] > button {
    background:#0d2040; border:1px solid #1e3d60;
    color:#7ec8e3; border-radius:6px;
    font-size:.8rem; font-weight:600;
    transition:all .15s;
}
[data-testid="stButton"] > button:hover {
    background:#1e3d60; border-color:#3498db; color:#fff;
}

/* ── Download button ── */
[data-testid="stDownloadButton"] > button {
    background:#0d2040; border:1px solid #1e3d60;
    color:#7ec8e3; border-radius:6px;
    font-size:.8rem; font-weight:600;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width:4px; }
::-webkit-scrollbar-track { background:#060d18; }
::-webkit-scrollbar-thumb { background:#1e3d60; border-radius:4px; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR — identidade do sistema
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style="padding:20px 16px 16px;border-bottom:1px solid #0f2035;margin-bottom:8px">
      <div style="font-size:1.1rem;font-weight:700;color:#e2eaf4;letter-spacing:.04em">
        🏭 IMS · Forzy
      </div>
      <div style="font-size:.72rem;color:#2a5a7a;margin-top:3px;letter-spacing:.06em;text-transform:uppercase">
        Industrial Monitoring System
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="padding:6px 16px 12px;border-bottom:1px solid #0f2035;margin-bottom:6px">
      <div style="font-size:.65rem;color:#2a5a7a;text-transform:uppercase;letter-spacing:.1em;margin-bottom:8px">
        Navegação
      </div>
    </div>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# Carrega dados para o overview
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data
def load_overview():
    csv = next((p for p in [
        Path(__file__).parent/"data"/"forzy.csv",
        Path.home()/"Downloads"/"History_32026-05-19T11-46-10-920.csv",
    ] if p.exists()), None)
    if not csv:
        return None
    df = pd.read_csv(csv, sep=";", skiprows=3, header=None,
        usecols=[0,3,4,5,6,7,8],
        names=["ts","m1_vel","m1_acel","m1_temp","m2_vel","m2_acel","m2_temp"])
    df["ts"] = pd.to_datetime(df["ts"])
    for c in df.columns[1:]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna(subset=["m1_vel","m2_vel"]).sort_values("ts").reset_index(drop=True)

df = load_overview()

VEL_AL, VEL_ALM = 1.8, 4.5
TEMP_AL, TEMP_ALM = 35.0, 42.0

def flag(v,a,al): return 2 if v>=al else 1 if v>=a else 0
COR  = {0:"#2ecc71",1:"#f39c12",2:"#e74c3c"}
NOME = {0:"NORMAL",1:"ALERTA",2:"ALARME"}

# ══════════════════════════════════════════════════════════════════════════════
# HEADER PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════
now = datetime.now().strftime("%d/%m/%Y  %H:%M")

if df is not None:
    v1,v2 = df.m1_vel.iloc[-1], df.m2_vel.iloc[-1]
    t1,t2 = df.m1_temp.iloc[-1], df.m2_temp.iloc[-1]
    f1 = max(flag(v1,VEL_AL,VEL_ALM), flag(t1,TEMP_AL,TEMP_ALM))
    f2 = max(flag(v2,VEL_AL,VEL_ALM), flag(t2,TEMP_AL,TEMP_ALM))
    pior = max(f1,f2)
    sys_status = NOME[pior]
    sys_cor    = COR[pior]
else:
    sys_status = "SEM DADOS"
    sys_cor    = "#3498db"
    f1 = f2 = pior = 0

st.markdown(f"""
<div style="background:linear-gradient(90deg,#080f1c 0%,#060d18 100%);
            border:1px solid #0f2035;border-radius:10px;
            padding:18px 28px;margin-bottom:20px;
            display:flex;align-items:center;justify-content:space-between">
  <div>
    <div style="font-size:1.35rem;font-weight:700;color:#e2eaf4;letter-spacing:.03em">
      Sistema de Monitoramento Industrial
    </div>
    <div style="font-size:.8rem;color:#2a5a7a;margin-top:4px">
      Bancada Forzy · Monitoramento de Bombas Centrífugas · Sensor VIM32PL IO-Link
    </div>
  </div>
  <div style="text-align:right">
    <div style="display:inline-block;padding:5px 16px;border-radius:5px;
                border:1px solid {sys_cor};background:{sys_cor}18;
                font-size:.78rem;font-weight:700;color:{sys_cor};letter-spacing:.08em">
      ● {sys_status}
    </div>
    <div style="font-size:.72rem;color:#2a5a7a;margin-top:6px">⏱ {now}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# STATUS RÁPIDO DOS ATIVOS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("#### 🏗️ Status dos Ativos")

col1, col2, col3, col4 = st.columns(4)

if df is not None:
    n_alarmes_m1 = int((df.m1_vel >= VEL_ALM).sum())
    n_alarmes_m2 = int((df.m2_vel >= VEL_ALM).sum())

    for col, nome, vel, temp, f_status, n_al in [
        (col1, "Motor 1 — Bomba Principal", v1, t1, f1, n_alarmes_m1),
        (col2, "Motor 2 — Bomba Auxiliar",  v2, t2, f2, n_alarmes_m2),
    ]:
        with col:
            st.markdown(f"""
            <div style="background:#08111f;border:1.5px solid {COR[f_status]};
                        border-radius:8px;padding:16px 18px">
              <div style="font-size:.72rem;color:#2a5a7a;text-transform:uppercase;
                          letter-spacing:.08em;margin-bottom:10px">{nome}</div>
              <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
                <span style="font-size:1.3rem;font-weight:700;color:{COR[f_status]}">{NOME[f_status]}</span>
              </div>
              <div style="font-size:.82rem;color:#aac;line-height:1.9">
                📳 Vel: <b style="color:#e2eaf4">{vel:.3f} mm/s</b><br>
                🌡 Temp: <b style="color:#e2eaf4">{temp:.1f} °C</b><br>
                🚨 Alarmes: <b style="color:{'#e74c3c' if n_al>0 else '#2ecc71'}">{n_al}</b>
              </div>
            </div>
            """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div style="background:#08111f;border:1px solid #0f2035;
                border-radius:8px;padding:16px 18px">
      <div style="font-size:.72rem;color:#2a5a7a;text-transform:uppercase;
                  letter-spacing:.08em;margin-bottom:10px">Sensor</div>
      <div style="font-size:.82rem;color:#aac;line-height:1.9">
        🔩 VIM32PL-E1AC8<br>
        🔗 IO-Link 1.1<br>
        📡 38,4 kBit/s<br>
        ✅ <b style="color:#2ecc71">Ativo</b>
      </div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    if df is not None:
        dur = df.ts.max() - df.ts.min()
        h, m = divmod(int(dur.total_seconds()), 3600)
        m //= 60
        st.markdown(f"""
        <div style="background:#08111f;border:1px solid #0f2035;
                    border-radius:8px;padding:16px 18px">
          <div style="font-size:.72rem;color:#2a5a7a;text-transform:uppercase;
                      letter-spacing:.08em;margin-bottom:10px">Dataset</div>
          <div style="font-size:.82rem;color:#aac;line-height:1.9">
            📊 {len(df):,} amostras<br>
            🕐 {df.ts.min().strftime('%H:%M')} → {df.ts.max().strftime('%H:%M')}<br>
            ⏱ Duração: {h}h {m:02d}min<br>
            📁 forzy.csv
          </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# CARDS DE NAVEGAÇÃO
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("#### 🗂️ Módulos do Sistema")

nav_cols = st.columns(3)
cards = [
    ("📊", "Monitoramento",
     "Dados em tempo real com gauges, health score e modo de falha simulado.",
     "#3498db", "pages/2_Monitoramento.py"),
    ("🔬", "Análise Espectral",
     "FFT com marcadores de harmônicas, espectrograma e cenários de falha.",
     "#9b59b6", "pages/3_Espectral.py"),
    ("🏭", "SCADA Visual",
     "Planta 2D com modelo STP real + Vista 3D interativa com alertas ao vivo.",
     "#1abc9c", "pages/6_SCADA.py"),
    ("⚙️", "Análise Operacional",
     "Timeline completa, análise de distribuição, correlação e log de eventos.",
     "#e67e22", "pages/4_Operacional.py"),
    ("▶️", "Histórico / Player",
     "Reprodução animada do histórico de operação com scrubbing de timeline.",
     "#e74c3c", "pages/5_Historico.py"),
    ("📡", "Conexão IoT / ESP32",
     "Interface para monitoramento ao vivo via ESP32 + VIM32PL em produção.",
     "#2ecc71", "pages/7_IoT.py"),
]

for i, (icon, titulo, desc, cor, _) in enumerate(cards):
    with nav_cols[i % 3]:
        st.markdown(f"""
        <div style="background:#08111f;border:1px solid {cor}30;
                    border-radius:8px;padding:18px 20px;margin-bottom:12px;
                    border-left:3px solid {cor};">
          <div style="font-size:1.5rem">{icon}</div>
          <div style="font-size:.9rem;font-weight:700;color:#e2eaf4;
                      margin:8px 0 6px">{titulo}</div>
          <div style="font-size:.78rem;color:#4a7a9b;line-height:1.5">{desc}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# RESUMO ISO 10816
# ══════════════════════════════════════════════════════════════════════════════
with st.expander("📏 Referência — Normas ISO 10816 / 20816", expanded=False):
    c1, c2 = st.columns(2)
    with c1:
        st.caption("**ISO 10816 — Classe I (< 15 kW)**")
        st.table({"Zona":["✅ Normal","⚠️ Alerta","🚨 Alarme"],
                  "RMS (mm/s)":["< 1,8","1,8 – 4,5","> 4,5"]})
    with c2:
        st.caption("**ISO 20816 — Classe II (15–75 kW)**")
        st.table({"Zona":["✅ Normal","⚠️ Alerta","🚨 Alarme"],
                  "RMS (mm/s)":["< 2,3","2,3 – 7,1","> 7,1"]})

# ══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="border-top:1px solid #0f2035;margin-top:16px;padding-top:12px;
            display:flex;justify-content:space-between;align-items:center">
  <span style="font-size:.72rem;color:#1a3a5a">
    IMS · Forzy Industrial Monitoring System
  </span>
  <span style="font-size:.72rem;color:#1a3a5a">
    Sensor: Pepperl+Fuchs VIM32PL · ISO 10816 / 20816
  </span>
</div>
""", unsafe_allow_html=True)
