"""Conexão IoT / ESP32 — Monitoramento ao Vivo"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="IoT · ESP32", layout="wide")
import sys; sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))
from utils.theme import apply as _apply_theme, sidebar_header as _sh
_apply_theme(); _sh()


# ── CSS da página ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
.conn-card {
    background:#08111f; border:1px solid #0f2035;
    border-radius:8px; padding:18px 20px; margin-bottom:12px;
}
.status-dot {
    width:10px; height:10px; border-radius:50%;
    display:inline-block; margin-right:6px;
}
.dot-online  { background:#2ecc71; box-shadow:0 0 8px #2ecc71; }
.dot-offline { background:#e74c3c; box-shadow:0 0 8px #e74c3c; }
.dot-waiting { background:#f39c12; box-shadow:0 0 8px #f39c12; animation:pulse 1.2s infinite; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }
.channel-row {
    display:flex; justify-content:space-between; align-items:center;
    padding:8px 0; border-bottom:1px solid #0f2035; font-size:.82rem;
}
.channel-row:last-child { border-bottom:none; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="background:#08111f;border:1px solid #0f2035;border-radius:10px;
            padding:18px 28px;margin-bottom:20px">
  <div style="font-size:1.15rem;font-weight:700;color:#e2eaf4">
    📡 Conexão IoT — Sensor VIM32PL via ESP32
  </div>
  <div style="font-size:.8rem;color:#2a5a7a;margin-top:4px">
    Interface de monitoramento ao vivo · IO-Link 1.1 → ESP32 → Dashboard
  </div>
</div>
""", unsafe_allow_html=True)

# ── Sidebar de configuração ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:16px;border-bottom:1px solid #0f2035;margin-bottom:8px">
      <div style="font-size:.65rem;color:#2a5a7a;text-transform:uppercase;letter-spacing:.1em">
        Configuração Hardware
      </div>
    </div>
    """, unsafe_allow_html=True)

    modo = st.radio("Fonte de dados", ["🔴 Simulação (sem hardware)", "🟢 ESP32 Real (USB)"],
                    index=0)
    st.divider()
    porta = st.selectbox("Porta Serial", ["COM3","COM4","COM5","COM6","COM7","AUTO"],
                         disabled="Simulação" in modo)
    baud  = st.selectbox("Baud Rate", [115200, 9600, 57600], disabled="Simulação" in modo)
    st.divider()
    st.caption("**Sensor VIM32PL**")
    st.caption("Protocolo: IO-Link 1.1")
    st.caption("Transfer rate: COM2 (38,4 kBit/s)")
    st.caption("Ciclo mín: 5 ms")

# ── Status de conexão ─────────────────────────────────────────────────────────
c1, c2, c3 = st.columns(3)

is_sim = "Simulação" in modo

with c1:
    dot = "dot-waiting" if is_sim else "dot-offline"
    status_txt = "SIMULAÇÃO" if is_sim else "DESCONECTADO"
    status_cor = "#f39c12" if is_sim else "#e74c3c"
    st.markdown(f"""
    <div class="conn-card">
      <div style="font-size:.7rem;color:#2a5a7a;text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px">
        Status da Conexão
      </div>
      <div style="display:flex;align-items:center;gap:8px">
        <span class="status-dot {dot}"></span>
        <span style="font-size:1rem;font-weight:700;color:{status_cor}">{status_txt}</span>
      </div>
      <div style="font-size:.78rem;color:#4a7a9b;margin-top:8px">
        {'Modo demonstração ativo' if is_sim else f'Porta: {porta} · {baud} baud'}
      </div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown("""
    <div class="conn-card">
      <div style="font-size:.7rem;color:#2a5a7a;text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px">
        Protocolo IO-Link
      </div>
      <div class="channel-row">
        <span style="color:#4a7a9b">Canal ①</span>
        <span style="color:#e2eaf4">Velocidade RMS (mm/s)</span>
      </div>
      <div class="channel-row">
        <span style="color:#4a7a9b">Canal ②</span>
        <span style="color:#e2eaf4">Aceleração Pico (g)</span>
      </div>
      <div class="channel-row">
        <span style="color:#4a7a9b">Canal ③</span>
        <span style="color:#e2eaf4">Aceleração RMS (g)</span>
      </div>
      <div class="channel-row">
        <span style="color:#4a7a9b">Canal ④</span>
        <span style="color:#e2eaf4">Temperatura (°C)</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown("""
    <div class="conn-card">
      <div style="font-size:.7rem;color:#2a5a7a;text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px">
        Hardware Requerido
      </div>
      <div style="font-size:.8rem;color:#4a7a9b;line-height:2">
        🔩 Sensor VIM32PL-E1AC8<br>
        🤖 ESP32 Dev Module<br>
        🔌 Cabo USB-Serial (CP210x)<br>
        📦 Driver CP210x / CH340
      </div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ── Leituras ao vivo ──────────────────────────────────────────────────────────
st.markdown("#### 📊 Leituras em Tempo Real")

from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=2000, key="iot_refresh")

if "iot_hist" not in st.session_state:
    st.session_state.iot_hist = []
    st.session_state.iot_t = 0.0

st.session_state.iot_t += 2.0
t = st.session_state.iot_t

# Simula dados VIM32PL
import math, random
rng = random.Random(int(t))
base = 1.1 + 0.9*math.sin(t/30)
vib  = max(0.02, base + rng.gauss(0,0.12))
apeak= vib * 0.085 + rng.gauss(0,0.003)
arms = apeak * 0.63
temp = 38 + vib*1.5 + rng.gauss(0,0.8)

flag_v = 2 if vib>=4.5 else (1 if vib>=1.8 else 0)
COR = {0:"#2ecc71", 1:"#f39c12", 2:"#e74c3c"}
NOME= {0:"NORMAL",  1:"ALERTA",  2:"ALARME"}

st.session_state.iot_hist.append({
    "ts": datetime.now(), "vel":vib, "apeak":apeak,
    "arms":arms, "temp":temp, "flag":flag_v,
})
if len(st.session_state.iot_hist) > 150:
    st.session_state.iot_hist = st.session_state.iot_hist[-150:]

df_live = pd.DataFrame(st.session_state.iot_hist)

# KPIs instantâneos
k1,k2,k3,k4,k5 = st.columns(5)
k1.metric("Vel. RMS",    f"{vib:.3f} mm/s",   NOME[flag_v],
          delta_color="inverse" if flag_v>0 else "off")
k2.metric("Acel. Pico",  f"{apeak:.4f} g")
k3.metric("Acel. RMS",   f"{arms:.4f} g")
k4.metric("Temperatura", f"{temp:.1f} °C")
k5.metric("Status ISO",  NOME[flag_v],
          delta_color="off")

# Gráfico live
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=df_live["ts"], y=df_live["vel"],
    mode="lines", name="Vel RMS (mm/s)",
    line=dict(color="#3498db", width=1.8, shape="spline", smoothing=0.5),
    fill="tozeroy", fillcolor="rgba(52,152,219,0.06)",
))
fig.add_hline(y=1.8, line_dash="dot", line_color="#f39c12", line_width=1)
fig.add_hline(y=4.5, line_dash="dot", line_color="#e74c3c", line_width=1)
fig.add_hrect(y0=0,   y1=1.8, fillcolor="#2ecc71", opacity=0.04)
fig.add_hrect(y0=1.8, y1=4.5, fillcolor="#f39c12", opacity=0.05)
fig.add_hrect(y0=4.5, y1=10,  fillcolor="#e74c3c", opacity=0.05)

# Marca último ponto
fig.add_trace(go.Scatter(
    x=[df_live["ts"].iloc[-1]], y=[vib],
    mode="markers",
    marker=dict(color=COR[flag_v], size=10,
                line=dict(color="white", width=2)),
    name="Atual", showlegend=True,
))
fig.update_layout(
    title=dict(text="Velocidade de Vibração RMS — Sensor VIM32PL (ao vivo)",
               font=dict(size=13, color="#7ec8e3")),
    height=300,
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font_color="#cdd9e5",
    margin=dict(l=50,r=20,t=40,b=40),
    xaxis=dict(gridcolor="#0f2035", showline=True, linecolor="#0f2035"),
    yaxis=dict(gridcolor="#0f2035", showline=True, linecolor="#0f2035",
               title="mm/s", range=[0,10]),
    hovermode="x unified",
    legend=dict(orientation="h", y=1.08, bgcolor="rgba(0,0,0,0)"),
)
st.plotly_chart(fig, use_container_width=True)

# Segunda linha: aceleração + temperatura
col_a, col_t = st.columns(2)
for col_w, col_y, titulo, cor, unidade in [
    (col_a, "apeak", "Aceleração de Pico (g)",   "#9b59b6", "g"),
    (col_t, "temp",  "Temperatura do Sensor (°C)","#e67e22", "°C"),
]:
    fig_s = go.Figure(go.Scatter(
        x=df_live["ts"], y=df_live[col_y],
        mode="lines", line=dict(color=cor, width=1.5, shape="spline", smoothing=0.5),
        fill="tozeroy", fillcolor=f"{cor}10",
    ))
    fig_s.update_layout(
        title=dict(text=titulo, font=dict(size=12, color=cor)),
        height=210, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#cdd9e5", margin=dict(l=50,r=20,t=40,b=30),
        xaxis=dict(gridcolor="#0f2035"), yaxis=dict(gridcolor="#0f2035", title=unidade),
        showlegend=False,
    )
    with col_w:
        st.plotly_chart(fig_s, use_container_width=True)

st.divider()

# ── Instruções de conexão ─────────────────────────────────────────────────────
with st.expander("🔧 Como conectar o hardware real", expanded=False):
    st.markdown("""
    **1. Instalar driver USB-Serial**
    - [CP210x (Silicon Labs)](https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers)
    - [CH340 (WCH)](http://www.wch.cn/downloads/CH341SER_EXE.html)

    **2. Gravar firmware no ESP32**
    ```
    Abra: firmware/esp32_mpu6050_rms.ino no Arduino IDE
    Placa: ESP32 Dev Module
    Conexão VIM32PL → ESP32:
      Pin 1 (L+)  → 3.3V
      Pin 2 (I/Q) → GPIO 34 (analog)
      Pin 3 (L-)  → GND
      Pin 4 (C/Q) → GPIO 35 (IO-Link master)
    ```

    **3. Iniciar leitura**
    ```powershell
    python serial_reader.py --port COM3 --sensor vim32pl
    ```

    **4. Selecionar "ESP32 Real" nesta página e escolher a porta COM correta.**
    """)

st.markdown("""
<div style="text-align:center;margin-top:20px;font-size:.72rem;color:#1a3a5a">
  ⚠️ Modo simulação ativo — dados gerados sinteticamente para demonstração
</div>
""", unsafe_allow_html=True)
