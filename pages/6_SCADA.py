"""
SCADA 2D / 3D — Planta virtual da bancada Forzy
Timelapse integrado com alerta piscante por temperatura
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from pathlib import Path

st.set_page_config(page_title="SCADA — Forzy", layout="wide")

# ══════════════════════════════════════════════════════════════════════════════
# CSS — alerta piscante
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@keyframes blink-red {
  0%,100% { background:#e74c3c; box-shadow:0 0 18px #e74c3c; opacity:1; }
  50%      { background:#7b1a1a; box-shadow:0 0 4px #e74c3c;  opacity:.5; }
}
@keyframes blink-yellow {
  0%,100% { background:#f39c12; box-shadow:0 0 14px #f39c12; opacity:1; }
  50%      { background:#7d5005; box-shadow:0 0 4px #f39c12;  opacity:.5; }
}
.alert-red    { animation:blink-red    .7s infinite; border-radius:8px;
                padding:10px 20px; color:#fff; font-weight:bold; text-align:center; }
.alert-yellow { animation:blink-yellow 1s infinite;  border-radius:8px;
                padding:10px 20px; color:#fff; font-weight:bold; text-align:center; }
.status-ok    { background:#2ecc71; border-radius:8px;
                padding:10px 20px; color:#fff; font-weight:bold; text-align:center; }
.player-bar   { background:#1a1a2e; border-radius:10px; padding:12px 20px;
                margin-bottom:16px; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# Dados
# ══════════════════════════════════════════════════════════════════════════════
SEARCH_PATHS = [
    Path(__file__).parent.parent / "data" / "forzy.csv",
    Path.home() / "Downloads" / "History_32026-05-19T11-46-10-920.csv",
]
csv_path = next((p for p in SEARCH_PATHS if p.exists()), None)
if not csv_path:
    st.error("CSV não encontrado.")
    st.stop()

@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";", skiprows=3, header=None,
                     usecols=[0,3,4,5,6,7,8],
                     names=["ts","m1_vel","m1_acel","m1_temp",
                                  "m2_vel","m2_acel","m2_temp"])
    df["ts"] = pd.to_datetime(df["ts"])
    for c in df.columns[1:]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna().sort_values("ts").reset_index(drop=True)
    return (df.set_index("ts").resample("5s").mean()
              .dropna(how="all").reset_index())

df = load_data(str(csv_path))
if len(df) > 400:
    df = df.iloc[::len(df)//400].reset_index(drop=True)
N = len(df)

# ══════════════════════════════════════════════════════════════════════════════
# Limiares
# ══════════════════════════════════════════════════════════════════════════════
TEMP_ALERTA  = 35.0
TEMP_ALARME  = 42.0
VEL_ALERTA   = 3.0
VEL_ALARME   = 5.5
ACEL_ALERTA  = 0.25
ACEL_ALARME  = 0.45

def flag(v, a, al): return 2 if v>=al else 1 if v>=a else 0
FLAG_COR  = {0:"#2ecc71", 1:"#f39c12", 2:"#e74c3c"}
FLAG_NOME = {0:"OK", 1:"ALERTA", 2:"ALARME"}

# ══════════════════════════════════════════════════════════════════════════════
# Session state — player
# ══════════════════════════════════════════════════════════════════════════════
for k, v in [("fidx", 0), ("playing", False), ("speed", 200)]:
    if k not in st.session_state:
        st.session_state[k] = v

# Autorefresh SEMPRE ativo — intervalo curto quando tocando, longo quando pausado
# Isso evita que o componente suma/reapareça e perca o estado
_interval = st.session_state.speed if st.session_state.playing else 86_400_000
st_autorefresh(interval=_interval, key="scada_play")

# Avança frame a cada rerun causado pelo autorefresh
if st.session_state.playing:
    st.session_state.fidx = min(st.session_state.fidx + 1, N - 1)
    if st.session_state.fidx >= N - 1:
        st.session_state.playing = False

row = df.iloc[st.session_state.fidx]

# ══════════════════════════════════════════════════════════════════════════════
# Sidebar
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.header("⚙️ SCADA Config")
    vista = st.radio("Vista", ["2D Planta", "3D Motor"], index=0)
    st.divider()
    st.subheader("Limiares")
    TEMP_ALERTA = st.number_input("Temp alerta °C", value=TEMP_ALERTA, step=1.0)
    TEMP_ALARME = st.number_input("Temp alarme °C", value=TEMP_ALARME, step=1.0)
    VEL_ALERTA  = st.number_input("Vel alerta m/s", value=VEL_ALERTA,  step=0.5)
    VEL_ALARME  = st.number_input("Vel alarme m/s", value=VEL_ALARME,  step=0.5)
    st.divider()
    st.caption(f"Frame {st.session_state.fidx+1}/{N}")
    st.caption(f"⏱ {row['ts'].strftime('%H:%M:%S')}")

# ══════════════════════════════════════════════════════════════════════════════
# Header + Player bar
# ══════════════════════════════════════════════════════════════════════════════
st.title("🏭 SCADA — Bancada Forzy")

with st.container():
    st.markdown('<div class="player-bar">', unsafe_allow_html=True)
    pc1, pc2, pc3, pc4, pc5, pc6 = st.columns([1, 1, 1, 1, 5, 1])

    # ⏮ Reset — sempre habilitado
    with pc1:
        if st.button("⏮", use_container_width=True, key="btn_reset"):
            st.session_state.fidx = 0
            st.session_state.playing = False
            st.rerun()

    # ▶ Play — desabilitado se já tocando
    with pc2:
        if st.button("▶", use_container_width=True, key="btn_play",
                     disabled=st.session_state.playing):
            if st.session_state.fidx >= N - 1:
                st.session_state.fidx = 0
            st.session_state.playing = True
            st.rerun()

    # ⏸ Pause — desabilitado se pausado
    with pc3:
        if st.button("⏸", use_container_width=True, key="btn_pause",
                     disabled=not st.session_state.playing):
            st.session_state.playing = False
            st.rerun()

    # Velocidade
    with pc4:
        spd = st.selectbox("", [50, 100, 200, 300, 500],
                           index=[50,100,200,300,500].index(
                               st.session_state.speed)
                               if st.session_state.speed in [50,100,200,300,500] else 2,
                           format_func=lambda x: f"{x} ms",
                           label_visibility="collapsed", key="sel_speed")
        st.session_state.speed = spd

    # Slider — sem key para que value= sempre seja respeitado
    with pc5:
        slider_val = st.slider("", 0, N - 1,
                               value=st.session_state.fidx,
                               label_visibility="collapsed")
        # Só atualiza fidx a partir do slider se o usuário arrastou (não playing)
        if not st.session_state.playing and slider_val != st.session_state.fidx:
            st.session_state.fidx = slider_val
            st.rerun()

    # Timestamp atual
    with pc6:
        st.markdown(
            f"<div style='color:#aaa;font-size:.82rem;padding-top:8px;text-align:center'>"
            f"⏱<br>{row['ts'].strftime('%H:%M:%S')}</div>",
            unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# Alertas piscantes
# ══════════════════════════════════════════════════════════════════════════════
f_m1_temp = flag(row.m1_temp, TEMP_ALERTA, TEMP_ALARME)
f_m2_temp = flag(row.m2_temp, TEMP_ALERTA, TEMP_ALARME)
f_m1_vel  = flag(row.m1_vel,  VEL_ALERTA,  VEL_ALARME)
f_m2_vel  = flag(row.m2_vel,  VEL_ALERTA,  VEL_ALARME)

al1, al2 = st.columns(2)
with al1:
    css = "alert-red" if f_m1_temp==2 else "alert-yellow" if f_m1_temp==1 else "status-ok"
    st.markdown(
        f'<div class="{css}">🔵 MOTOR 1 — Temp {row.m1_temp:.1f}°C '
        f'| Vel {row.m1_vel:.2f} m/s — {FLAG_NOME[max(f_m1_temp,f_m1_vel)]}</div>',
        unsafe_allow_html=True)
with al2:
    css = "alert-red" if f_m2_temp==2 else "alert-yellow" if f_m2_temp==1 else "status-ok"
    st.markdown(
        f'<div class="{css}">🔴 MOTOR 2 — Temp {row.m2_temp:.1f}°C '
        f'| Vel {row.m2_vel:.2f} m/s — {FLAG_NOME[max(f_m2_temp,f_m2_vel)]}</div>',
        unsafe_allow_html=True)

st.markdown("")

# ══════════════════════════════════════════════════════════════════════════════
# TABS — 2D / 3D
# ══════════════════════════════════════════════════════════════════════════════
tab2d, tab3d, tab_hist = st.tabs(["🗺️ Planta 2D", "🧊 Vista 3D", "📈 Histórico"])

# ─────────────────────────────────────────────────────────────────────────────
# helpers de cor com "blink" simulado por frame par/ímpar
# ─────────────────────────────────────────────────────────────────────────────
blink_on = (st.session_state.fidx % 3) < 2   # 2 frames aceso, 1 apagado

def motor_fill(flag_temp, flag_vel):
    f = max(flag_temp, flag_vel)
    if f == 2:
        return FLAG_COR[2] if blink_on else "#4a1010"
    if f == 1:
        return FLAG_COR[1] if blink_on else "#6b4a00"
    return FLAG_COR[0]

mc1 = motor_fill(f_m1_temp, f_m1_vel)
mc2 = motor_fill(f_m2_temp, f_m2_vel)

# ══════════════════════════════════════════════════════════════════════════════
# ABA 2D
# ══════════════════════════════════════════════════════════════════════════════
with tab2d:
    fig2 = go.Figure()

    # Fundo — parede da planta
    fig2.add_shape(type="rect", x0=0,y0=0,x1=24,y1=14,
                   fillcolor="#1a1a2e", line=dict(color="#333",width=2))

    # Grade de piso
    for gx in range(0,25,2):
        fig2.add_shape(type="line",x0=gx,y0=0,x1=gx,y1=14,
                       line=dict(color="#252540",width=1))
    for gy in range(0,15,2):
        fig2.add_shape(type="line",x0=0,y0=gy,x1=24,y1=gy,
                       line=dict(color="#252540",width=1))

    def rect(x0,y0,x1,y1,fill,line_col="#555",lw=2,layer="above"):
        fig2.add_shape(type="rect",x0=x0,y0=y0,x1=x1,y1=y1,layer=layer,
                       fillcolor=fill,line=dict(color=line_col,width=lw))

    def label(x,y,txt,size=11,color="white",anchor="center"):
        fig2.add_annotation(x=x,y=y,text=txt,showarrow=False,
                            font=dict(size=size,color=color),
                            xanchor=anchor,yanchor="middle")

    # ── PAINEL ELÉTRICO ──────────────────────────────────────────────────────
    rect(0.5,5,2.8,9,"#2c3e50","#3498db",2)
    label(1.65,8.4,"PAINEL",9,"#3498db")
    label(1.65,7.7,"ELÉTRICO",8,"#3498db")
    # LEDs do painel
    for yd,cor in [(7.1,"#2ecc71"),(6.6,"#f39c12"),(6.1,"#e74c3c")]:
        fig2.add_shape(type="circle",x0=1.3,y0=yd-.15,x1=1.6,y1=yd+.15,
                       fillcolor=cor,line=dict(color="#111",width=1))

    # ── VFD 1 (inversor motor 1) ──────────────────────────────────────────────
    rect(3.2,8.5,5.0,9.5,"#1e3a5f","#3498db",2)
    label(4.1,9.0,"VFD 1",10,"#7ec8e3")
    # Cabo painel → VFD1
    fig2.add_shape(type="line",x0=2.8,y0=8.0,x1=3.2,y1=9.0,
                   line=dict(color="#3498db",width=2,dash="dot"))

    # ── VFD 2 ─────────────────────────────────────────────────────────────────
    rect(3.2,4.0,5.0,5.0,"#1e3a5f","#e74c3c",2)
    label(4.1,4.5,"VFD 2",10,"#f1948a")
    fig2.add_shape(type="line",x0=2.8,y0=6.0,x1=3.2,y1=4.5,
                   line=dict(color="#e74c3c",width=2,dash="dot"))

    # ── MOTOR 1 ───────────────────────────────────────────────────────────────
    rect(5.5,7.8,9.0,10.2, mc1,"#eee",3)
    # Corpo cilíndrico (elipse decorativa)
    fig2.add_shape(type="circle",x0=5.5,y0=8.3,x1=6.5,y1=9.7,
                   fillcolor="#1a1a2e",line=dict(color="#aaa",width=2))
    fig2.add_shape(type="circle",x0=8.0,y0=8.3,x1=9.0,y1=9.7,
                   fillcolor="#1a1a2e",line=dict(color="#aaa",width=2))
    label(7.25,9.0,"MOTOR 1",11,"white")
    label(7.25,8.5,f"Port 1",9,"#ccc")
    # Cabo VFD1 → Motor 1
    fig2.add_shape(type="line",x0=5.0,y0=9.0,x1=5.5,y1=9.0,
                   line=dict(color="#3498db",width=3))

    # ── SENSOR MPU6050 — Motor 1 ──────────────────────────────────────────────
    rect(6.5,10.2,7.5,11.0,"#8e44ad","#c39bd3",1)
    label(7.0,10.6,"MPU6050",8,"#d7bde2")
    fig2.add_shape(type="line",x0=7.0,y0=10.2,x1=7.0,y1=10.2,
                   line=dict(color="#9b59b6",width=2))

    # ── ACOPLAMENTO + EIXO Motor 1 ────────────────────────────────────────────
    rect(9.0,8.8,9.6,9.2,"#7f8c8d","#bdc3c7",2)
    fig2.add_shape(type="line",x0=9.6,y0=9.0,x1=11.0,y1=9.0,
                   line=dict(color="#95a5a6",width=4))

    # ── CARGA 1 ───────────────────────────────────────────────────────────────
    rect(11.0,7.5,14.5,10.5,"#1c2833","#7f8c8d",2)
    label(12.75,9.2,"CARGA 1",11,"#aaa")
    label(12.75,8.7,"(Máquina)",9,"#666")
    # Engrenagem decorativa
    fig2.add_shape(type="circle",x0=12.0,y0=8.5,x1=13.5,y1=9.9,
                   fillcolor="#2c3e50",line=dict(color="#555",width=2))

    # ── MOTOR 2 ───────────────────────────────────────────────────────────────
    rect(5.5,3.3,9.0,5.7, mc2,"#eee",3)
    fig2.add_shape(type="circle",x0=5.5,y0=3.8,x1=6.5,y1=5.2,
                   fillcolor="#1a1a2e",line=dict(color="#aaa",width=2))
    fig2.add_shape(type="circle",x0=8.0,y0=3.8,x1=9.0,y1=5.2,
                   fillcolor="#1a1a2e",line=dict(color="#aaa",width=2))
    label(7.25,4.5,"MOTOR 2",11,"white")
    label(7.25,4.0,"Port 2",9,"#ccc")
    fig2.add_shape(type="line",x0=5.0,y0=4.5,x1=5.5,y1=4.5,
                   line=dict(color="#e74c3c",width=3))

    # ── SENSOR MPU6050 — Motor 2 ──────────────────────────────────────────────
    rect(6.5,2.5,7.5,3.3,"#8e44ad","#c39bd3",1)
    label(7.0,2.9,"MPU6050",8,"#d7bde2")

    # ── ACOPLAMENTO + EIXO Motor 2 ────────────────────────────────────────────
    rect(9.0,4.3,9.6,4.7,"#7f8c8d","#bdc3c7",2)
    fig2.add_shape(type="line",x0=9.6,y0=4.5,x1=11.0,y1=4.5,
                   line=dict(color="#95a5a6",width=4))

    # ── CARGA 2 ───────────────────────────────────────────────────────────────
    rect(11.0,3.0,14.5,6.0,"#1c2833","#7f8c8d",2)
    label(12.75,4.7,"CARGA 2",11,"#aaa")
    label(12.75,4.2,"(Máquina)",9,"#666")
    fig2.add_shape(type="circle",x0=12.0,y0=4.0,x1=13.5,y1=5.4,
                   fillcolor="#2c3e50",line=dict(color="#555",width=2))

    # ── DADOS ao vivo sobre os motores ────────────────────────────────────────
    for mx, vals, prefix in [
        (16.5, row, "m1"), (16.5, row, "m2")
    ]:
        pass  # feitos como anotações abaixo

    # Painel de dados M1
    rect(15.5,7.5,23.5,10.5,"#0d1117","#3498db",2)
    label(19.5,10.1,"── MOTOR 1 ──",10,"#3498db")
    label(19.5,9.5, f"🌡 Temp:  {row.m1_temp:.1f} °C",10,
          FLAG_COR[f_m1_temp],"center")
    label(19.5,8.9, f"⚡ Acel:  {row.m1_acel:.3f} m/s²",10,"#eee","center")
    label(19.5,8.3, f"🚀 Vel:   {row.m1_vel:.2f} m/s",10,
          FLAG_COR[f_m1_vel],"center")
    label(19.5,7.8, f"Status: {FLAG_NOME[max(f_m1_temp,f_m1_vel)]}",9,
          FLAG_COR[max(f_m1_temp,f_m1_vel)],"center")

    # Painel de dados M2
    rect(15.5,3.0,23.5,6.0,"#0d1117","#e74c3c",2)
    label(19.5,5.6,"── MOTOR 2 ──",10,"#e74c3c")
    label(19.5,5.0, f"🌡 Temp:  {row.m2_temp:.1f} °C",10,
          FLAG_COR[f_m2_temp],"center")
    label(19.5,4.4, f"⚡ Acel:  {row.m2_acel:.3f} m/s²",10,"#eee","center")
    label(19.5,3.8, f"🚀 Vel:   {row.m2_vel:.2f} m/s",10,
          FLAG_COR[f_m2_vel],"center")
    label(19.5,3.3, f"Status: {FLAG_NOME[max(f_m2_temp,f_m2_vel)]}",9,
          FLAG_COR[max(f_m2_temp,f_m2_vel)],"center")

    # Título da planta
    label(12.0,13.3,"BANCADA DE TESTES — FORZY",13,"#ecf0f1")
    label(12.0,12.7,f"⏱ {row['ts'].strftime('%H:%M:%S')}   "
                    f"Frame {st.session_state.fidx+1}/{N}",
          10,"#888")

    # Legenda
    for lx, cor, txt in [(0.7,"#2ecc71","OK"),
                          (3.2,"#f39c12","Alerta"),
                          (5.7,"#e74c3c","Alarme"),
                          (8.5,"#8e44ad","Sensor")]:
        fig2.add_shape(type="rect",x0=lx,y0=0.4,x1=lx+.5,y1=1.2,
                       fillcolor=cor,line=dict(color="#111",width=1))
        label(lx+1.0,0.8,txt,9,"#ccc","left")

    fig2.update_layout(
        xaxis=dict(range=[0,24],showgrid=False,zeroline=False,
                   showticklabels=False),
        yaxis=dict(range=[0,14],showgrid=False,zeroline=False,
                   showticklabels=False,scaleanchor="x",scaleratio=1),
        height=600,
        margin=dict(l=0,r=0,t=10,b=0),
        paper_bgcolor="#0d1117",
        plot_bgcolor="#0d1117",
        showlegend=False,
    )
    st.plotly_chart(fig2, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# ABA 3D
# ══════════════════════════════════════════════════════════════════════════════
with tab3d:
    def cilindro(cx, cy, cz, raio, comprimento, cor, nome, n=40):
        theta = np.linspace(0, 2*np.pi, n)
        z_arr = np.array([0, comprimento])
        theta_g, z_g = np.meshgrid(theta, z_arr)
        x_ = raio * np.cos(theta_g) + cx
        y_ = raio * np.sin(theta_g) + cy
        z_ = z_g + cz
        return go.Surface(x=x_, y=y_, z=z_,
                          colorscale=[[0,cor],[1,cor]],
                          showscale=False, opacity=0.92,
                          name=nome,
                          hovertemplate=f"<b>{nome}</b><extra></extra>")

    def disco(cx, cy, cz, raio, cor, n=40):
        theta = np.linspace(0, 2*np.pi, n)
        r_arr = np.linspace(0, raio, 5)
        t_g, r_g = np.meshgrid(theta, r_arr)
        x_ = r_g * np.cos(t_g) + cx
        y_ = r_g * np.sin(t_g) + cy
        z_ = np.full_like(x_, cz)
        return go.Surface(x=x_, y=y_, z=z_,
                          colorscale=[[0,cor],[1,cor]],
                          showscale=False, opacity=0.95)

    fig3 = go.Figure()

    # ── Motor 1 ───────────────────────────────────────────────────────────────
    fig3.add_trace(cilindro(0,0,0,1.0,3.0,mc1,"Motor 1"))
    fig3.add_trace(disco(0,0,0,  1.0,mc1))
    fig3.add_trace(disco(0,0,3.0,1.0,mc1))
    # Eixo M1
    fig3.add_trace(go.Scatter3d(
        x=[0,0],y=[0,0],z=[3.0,5.0],
        mode="lines",line=dict(color="#95a5a6",width=8),name="Eixo M1"))
    # Sensor M1
    fig3.add_trace(go.Scatter3d(
        x=[0.8],y=[0.8],z=[1.5],
        mode="markers+text",
        marker=dict(size=10,color="#8e44ad",symbol="diamond"),
        text=["MPU6050"],textposition="top center",
        textfont=dict(color="#d7bde2",size=10),name="Sensor M1"))

    # ── Motor 2 ───────────────────────────────────────────────────────────────
    fig3.add_trace(cilindro(4,0,0,1.0,3.0,mc2,"Motor 2"))
    fig3.add_trace(disco(4,0,0,  1.0,mc2))
    fig3.add_trace(disco(4,0,3.0,1.0,mc2))
    fig3.add_trace(go.Scatter3d(
        x=[4,4],y=[0,0],z=[3.0,5.0],
        mode="lines",line=dict(color="#95a5a6",width=8),name="Eixo M2"))
    fig3.add_trace(go.Scatter3d(
        x=[4.8],y=[0.8],z=[1.5],
        mode="markers+text",
        marker=dict(size=10,color="#8e44ad",symbol="diamond"),
        text=["MPU6050"],textposition="top center",
        textfont=dict(color="#d7bde2",size=10),name="Sensor M2"))

    # ── Cargas ────────────────────────────────────────────────────────────────
    for cx_ in [0,4]:
        fig3.add_trace(go.Mesh3d(
            x=[cx_-.8,cx_+.8,cx_+.8,cx_-.8,cx_-.8,cx_+.8,cx_+.8,cx_-.8],
            y=[1.5,1.5,2.5,2.5,1.5,1.5,2.5,2.5],
            z=[0.3,0.3,0.3,0.3,2.7,2.7,2.7,2.7],
            alphahull=0, color="#2c3e50", opacity=0.7,
            name="Carga"))

    # Labels de dados
    for cx_, row_val, nome, fc_t, fc_v in [
        (0, row, "Motor 1", f_m1_temp, f_m1_vel),
        (4, row, "Motor 2", f_m2_temp, f_m2_vel),
    ]:
        cor_txt = FLAG_COR[max(fc_t, fc_v)]
        fig3.add_trace(go.Scatter3d(
            x=[cx_],y=[0],z=[4.0],
            mode="text",
            text=[f"🌡{row_val.m1_temp if 'Motor 1'==nome else row_val.m2_temp:.1f}°C  "
                  f"🚀{row_val.m1_vel if 'Motor 1'==nome else row_val.m2_vel:.2f}m/s"],
            textfont=dict(size=11,color=cor_txt),
            showlegend=False,
        ))

    fig3.update_layout(
        height=580,
        scene=dict(
            xaxis=dict(showgrid=True,gridcolor="#222",backgroundcolor="#0d1117",
                       title="",showticklabels=False),
            yaxis=dict(showgrid=True,gridcolor="#222",backgroundcolor="#0d1117",
                       title="",showticklabels=False),
            zaxis=dict(showgrid=True,gridcolor="#222",backgroundcolor="#0d1117",
                       title="Altura",showticklabels=False),
            bgcolor="#0d1117",
            camera=dict(eye=dict(x=1.8,y=-2.2,z=1.4)),
            aspectmode="manual",
            aspectratio=dict(x=2,y=1,z=1),
        ),
        paper_bgcolor="#0d1117",
        margin=dict(l=0,r=0,t=30,b=0),
        legend=dict(font=dict(color="white"),bgcolor="#1a1a2e"),
        title=dict(text=f"Vista 3D — {row['ts'].strftime('%H:%M:%S')}",
                   font=dict(color="#eee",size=14)),
    )
    st.plotly_chart(fig3, use_container_width=True)

    st.info("💡 Arraste para rotacionar · Scroll para zoom · "
            "Motor colorido conforme status: 🟢 OK  🟡 Alerta  🔴 Alarme")

# ══════════════════════════════════════════════════════════════════════════════
# ABA HISTÓRICO — mini dashboard integrado
# ══════════════════════════════════════════════════════════════════════════════
with tab_hist:
    hist_sub = df.iloc[:st.session_state.fidx+1]

    fig_h = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        subplot_titles=("Velocidade (m/s)", "Aceleração", "Temperatura (°C)"),
        vertical_spacing=0.07,
    )

    for col_m1, col_m2, row_idx, unidade, la, lal in [
        ("m1_vel",  "m2_vel",  1, "m/s", VEL_ALERTA,  VEL_ALARME),
        ("m1_acel", "m2_acel", 2, "",    ACEL_ALERTA,  ACEL_ALARME),
        ("m1_temp", "m2_temp", 3, "°C",  TEMP_ALERTA, TEMP_ALARME),
    ]:
        fig_h.add_trace(go.Scatter(x=hist_sub["ts"], y=hist_sub[col_m1],
            mode="lines", name="Motor 1" if row_idx==1 else None,
            showlegend=(row_idx==1),
            line=dict(color="#3498db",width=1.5)), row=row_idx, col=1)
        fig_h.add_trace(go.Scatter(x=hist_sub["ts"], y=hist_sub[col_m2],
            mode="lines", name="Motor 2" if row_idx==1 else None,
            showlegend=(row_idx==1),
            line=dict(color="#e74c3c",width=1.5)), row=row_idx, col=1)
        fig_h.add_hline(y=la,  line_dash="dash", line_color="#f39c12",
                        line_width=1, row=row_idx, col=1)
        fig_h.add_hline(y=lal, line_dash="dash", line_color="#e74c3c",
                        line_width=1, row=row_idx, col=1)
        # Marcador do frame atual
        if not hist_sub.empty:
            for col_, cor_ in [(col_m1,"#3498db"),(col_m2,"#e74c3c")]:
                fig_h.add_trace(go.Scatter(
                    x=[hist_sub["ts"].iloc[-1]],
                    y=[hist_sub[col_].iloc[-1]],
                    mode="markers",
                    marker=dict(size=9,color=cor_,
                                line=dict(color="white",width=2)),
                    showlegend=False,
                ), row=row_idx, col=1)

    fig_h.update_layout(
        height=520, hovermode="x unified",
        paper_bgcolor="#0d1117", plot_bgcolor="#0d1117",
        font=dict(color="#eee"),
        margin=dict(l=50,r=20,t=40,b=30),
        legend=dict(orientation="h",y=1.05,bgcolor="rgba(0,0,0,0)"),
    )
    fig_h.update_xaxes(gridcolor="#222")
    fig_h.update_yaxes(gridcolor="#222")
    st.plotly_chart(fig_h, use_container_width=True)
