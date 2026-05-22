"""
Player / Timelapse — Dataset Forzy
Animação Plotly nativa com Play / Pause / Scrubbing
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from pathlib import Path

st.set_page_config(page_title="Player — Timelapse Forzy", layout="wide")

# ── CSV ────────────────────────────────────────────────────────────────────────
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
    df = pd.read_csv(
        path, sep=";", skiprows=3, header=None,
        usecols=[0, 3, 4, 5, 6, 7, 8],
        names=["timestamp", "m1_vel", "m1_acel", "m1_temp",
                              "m2_vel", "m2_acel", "m2_temp"],
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    for c in df.columns[1:]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna().sort_values("timestamp").reset_index(drop=True)
    return df

df_raw = load_data(str(csv_path))

# ── Sidebar ────────────────────────────────────────────────────────────────────
st.sidebar.header("⏱ Configurações do Player")

frame_interval = st.sidebar.select_slider(
    "Intervalo por frame (dados reais)",
    options=["5s", "10s", "15s", "30s", "1min", "2min", "5min"],
    value="30s",
)
speed_ms = st.sidebar.select_slider(
    "Velocidade de reprodução",
    options=[50, 100, 150, 200, 300, 500, 800],
    value=150,
    format_func=lambda x: f"{x} ms/frame",
)
transition_ms = min(speed_ms - 30, 80) if speed_ms > 80 else 0

VEL_ALERTA  = st.sidebar.number_input("Vel. alerta (m/s)", value=3.0, step=0.5)
VEL_ALARME  = st.sidebar.number_input("Vel. alarme (m/s)", value=5.5, step=0.5)

motores = st.sidebar.multiselect("Mostrar", ["Motor 1", "Motor 2"],
                                  default=["Motor 1", "Motor 2"])

# ── Resample para frames ────────────────────────────────────────────────────────
freq_map = {"5s":"5s","10s":"10s","15s":"15s","30s":"30s",
            "1min":"1min","2min":"2min","5min":"5min"}
freq = freq_map[frame_interval]

df = (df_raw.set_index("timestamp")
            .resample(freq).mean()
            .dropna(how="all")
            .reset_index())

# Timestamps dos frames (máx 300 para não travar o browser)
timestamps = df["timestamp"].tolist()
if len(timestamps) > 300:
    step = len(timestamps) // 300
    timestamps = timestamps[::step]
    df = df[df["timestamp"].isin(timestamps)].reset_index(drop=True)

N = len(df)

st.title("▶ Player — Timelapse Operacional")
st.caption(f"{N} frames  ·  {df['timestamp'].min().strftime('%H:%M:%S')} → "
           f"{df['timestamp'].max().strftime('%H:%M:%S')}  ·  "
           f"intervalo {frame_interval}")

# ── Cores e helpers ────────────────────────────────────────────────────────────
COR_M1, COR_M2 = "#3498db", "#e74c3c"
VEL_MAX = max(df["m1_vel"].max(), df["m2_vel"].max()) * 1.15

def vel_color(v):
    if v >= VEL_ALARME: return "#e74c3c"
    if v >= VEL_ALERTA: return "#f39c12"
    return "#2ecc71"

# ── Constrói frames da animação ───────────────────────────────────────────────
frames = []
slider_steps = []

for i in range(1, N + 1):
    sub = df.iloc[:i]
    last = sub.iloc[-1]

    traces = []

    # Faixas de zona (invisíveis nos frames — já estão no layout)
    # Motor 1 velocidade
    if "Motor 1" in motores:
        traces.append(go.Scatter(
            x=sub["timestamp"], y=sub["m1_vel"],
            mode="lines", line=dict(color=COR_M1, width=2),
            name="M1 Velocidade", legendgroup="m1",
            hovertemplate="M1: %{y:.2f} m/s<extra></extra>",
        ))
        # Ponto atual
        traces.append(go.Scatter(
            x=[last["timestamp"]], y=[last["m1_vel"]],
            mode="markers",
            marker=dict(color=vel_color(last["m1_vel"]), size=12,
                        line=dict(color="white", width=2)),
            name="M1 atual", legendgroup="m1", showlegend=False,
            hovertemplate="M1 agora: %{y:.2f} m/s<extra></extra>",
        ))

    # Motor 2 velocidade
    if "Motor 2" in motores:
        traces.append(go.Scatter(
            x=sub["timestamp"], y=sub["m2_vel"],
            mode="lines", line=dict(color=COR_M2, width=2),
            name="M2 Velocidade", legendgroup="m2",
            hovertemplate="M2: %{y:.2f} m/s<extra></extra>",
        ))
        traces.append(go.Scatter(
            x=[last["timestamp"]], y=[last["m2_vel"]],
            mode="markers",
            marker=dict(color=vel_color(last["m2_vel"]), size=12,
                        line=dict(color="white", width=2)),
            name="M2 atual", legendgroup="m2", showlegend=False,
        ))

    frames.append(go.Frame(data=traces, name=str(i)))

    slider_steps.append(dict(
        args=[[str(i)], {"frame": {"duration": speed_ms, "redraw": True},
                         "mode": "immediate",
                         "transition": {"duration": transition_ms}}],
        label=last["timestamp"].strftime("%H:%M:%S"),
        method="animate",
    ))

# ── Figura inicial (frame 1) ───────────────────────────────────────────────────
first = df.iloc[:1]
last0 = df.iloc[0]

init_traces = []
if "Motor 1" in motores:
    init_traces += [
        go.Scatter(x=first["timestamp"], y=first["m1_vel"],
                   mode="lines", line=dict(color=COR_M1, width=2),
                   name="Motor 1", legendgroup="m1"),
        go.Scatter(x=[last0["timestamp"]], y=[last0["m1_vel"]],
                   mode="markers",
                   marker=dict(color=vel_color(last0["m1_vel"]), size=12,
                               line=dict(color="white", width=2)),
                   name="M1 atual", legendgroup="m1", showlegend=False),
    ]
if "Motor 2" in motores:
    init_traces += [
        go.Scatter(x=first["timestamp"], y=first["m2_vel"],
                   mode="lines", line=dict(color=COR_M2, width=2),
                   name="Motor 2", legendgroup="m2"),
        go.Scatter(x=[last0["timestamp"]], y=[last0["m2_vel"]],
                   mode="markers",
                   marker=dict(color=vel_color(last0["m2_vel"]), size=12,
                               line=dict(color="white", width=2)),
                   name="M2 atual", legendgroup="m2", showlegend=False),
    ]

# ── Layout com botões Play/Pause e slider ─────────────────────────────────────
layout = go.Layout(
    height=520,
    xaxis=dict(
        title="Tempo",
        range=[df["timestamp"].min(), df["timestamp"].max()],
        type="date",
    ),
    yaxis=dict(
        title="Velocidade (m/s)",
        range=[0, VEL_MAX],
    ),
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
    margin=dict(l=50, r=20, t=60, b=120),

    # Faixas ISO de fundo
    shapes=[
        dict(type="rect", xref="paper", x0=0, x1=1,
             yref="y", y0=0, y1=VEL_ALERTA,
             fillcolor="#2ecc71", opacity=0.06, line_width=0),
        dict(type="rect", xref="paper", x0=0, x1=1,
             yref="y", y0=VEL_ALERTA, y1=VEL_ALARME,
             fillcolor="#f39c12", opacity=0.06, line_width=0),
        dict(type="rect", xref="paper", x0=0, x1=1,
             yref="y", y0=VEL_ALARME, y1=VEL_MAX,
             fillcolor="#e74c3c", opacity=0.06, line_width=0),
    ],
    annotations=[
        dict(xref="paper", x=0.01, yref="y", y=VEL_ALERTA/2,
             text="Normal", showarrow=False, font=dict(color="#2ecc71", size=11)),
        dict(xref="paper", x=0.01, yref="y", y=(VEL_ALERTA+VEL_ALARME)/2,
             text="Alerta", showarrow=False, font=dict(color="#f39c12", size=11)),
        dict(xref="paper", x=0.01, yref="y", y=VEL_ALARME+(VEL_MAX-VEL_ALARME)/2,
             text="Alarme", showarrow=False, font=dict(color="#e74c3c", size=11)),
    ],

    # Botões Play / Pause
    updatemenus=[dict(
        type="buttons",
        showactive=False,
        y=1.18, x=0.5, xanchor="center",
        buttons=[
            dict(
                label="▶  Play",
                method="animate",
                args=[None, {
                    "frame": {"duration": speed_ms, "redraw": True},
                    "fromcurrent": True,
                    "transition": {"duration": transition_ms},
                }],
            ),
            dict(
                label="⏸  Pause",
                method="animate",
                args=[[None], {
                    "frame": {"duration": 0, "redraw": False},
                    "mode": "immediate",
                    "transition": {"duration": 0},
                }],
            ),
            dict(
                label="⏮  Reset",
                method="animate",
                args=[["1"], {
                    "frame": {"duration": 0, "redraw": True},
                    "mode": "immediate",
                }],
            ),
        ],
        font=dict(size=14),
        bgcolor="#1e1e2e",
        bordercolor="#444",
    )],

    # Slider de scrubbing
    sliders=[dict(
        active=0,
        currentvalue=dict(
            prefix="⏱ ",
            visible=True,
            xanchor="center",
            font=dict(size=13),
        ),
        pad=dict(t=50, b=10),
        len=1.0, x=0,
        steps=slider_steps,
    )],
)

fig = go.Figure(data=init_traces, layout=layout, frames=frames)
st.plotly_chart(fig, use_container_width=True)

# ── Mini KPIs embaixo do player ────────────────────────────────────────────────
st.markdown("---")
st.caption("📊 Estatísticas do período completo")
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("M1 Vel. máx",  f"{df['m1_vel'].max():.2f} m/s")
c2.metric("M1 Vel. média", f"{df['m1_vel'].mean():.2f} m/s")
c3.metric("M1 Temp. máx", f"{df['m1_temp'].max():.1f} °C")
c4.metric("M2 Vel. máx",  f"{df['m2_vel'].max():.2f} m/s")
c5.metric("M2 Vel. média", f"{df['m2_vel'].mean():.2f} m/s")
c6.metric("M2 Temp. máx", f"{df['m2_temp'].max():.1f} °C")
