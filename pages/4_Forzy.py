"""
Página de análise — Dataset Forzy (2 motores)
CSV: History_32026-05-19T11-46-10-920.csv
Colunas: timestamp | PDI1 | PDI2 | M1_vel | M1_acel | M1_temp | M2_vel | M2_acel | M2_temp
"""

import os
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import streamlit as st
from pathlib import Path

st.set_page_config(page_title="Forzy — Análise de Motores", layout="wide")

# ── Localiza o CSV ─────────────────────────────────────────────────────────────
SEARCH_PATHS = [
    Path(__file__).parent.parent / "data" / "forzy.csv",
    Path.home() / "Downloads" / "History_32026-05-19T11-46-10-920.csv",
]

csv_path = None
for p in SEARCH_PATHS:
    if p.exists():
        csv_path = p
        break

if csv_path is None:
    st.error("CSV não encontrado. Coloque o arquivo em `data/forzy.csv` ou mantenha na pasta Downloads.")
    st.stop()

# ── Carrega e parseia ──────────────────────────────────────────────────────────
@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(
        path,
        sep=";",
        skiprows=3,
        header=None,
        usecols=[0, 3, 4, 5, 6, 7, 8],
        names=["timestamp", "m1_vel", "m1_acel", "m1_temp", "m2_vel", "m2_acel", "m2_temp"],
        decimal=".",
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    for col in ["m1_vel", "m1_acel", "m1_temp", "m2_vel", "m2_acel", "m2_temp"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["m1_vel", "m2_vel"]).sort_values("timestamp").reset_index(drop=True)
    # Resample para reduzir ruído (média de 1s)
    df = df.set_index("timestamp").resample("1s").mean().dropna(how="all").reset_index()
    return df

df = load_data(str(csv_path))

# ── Limiares ──────────────────────────────────────────────────────────────────
VEL_ALERTA  = 3.0   # m/s
VEL_ALARME  = 5.5   # m/s
ACEL_ALERTA = 0.25
ACEL_ALARME = 0.45
TEMP_ALERTA = 35    # °C
TEMP_ALARME = 42    # °C

def classificar(val, lim_alerta, lim_alarme):
    if val >= lim_alarme: return 2
    if val >= lim_alerta: return 1
    return 0

def cor_flag(flag):
    return {0: "#2ecc71", 1: "#f39c12", 2: "#e74c3c"}[flag]

# ── Header ────────────────────────────────────────────────────────────────────
st.title("⚙️ Análise Operacional — Motores Forzy")
st.caption(f"Dataset: {csv_path.name}  ·  {len(df):,} amostras  ·  "
           f"{df['timestamp'].min().strftime('%H:%M:%S')} → {df['timestamp'].max().strftime('%H:%M:%S')}")

# ── Filtros ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Filtros")
    motor_sel = st.radio("Motor", ["Ambos", "Motor 1", "Motor 2"])

    t_min = df["timestamp"].min().to_pydatetime()
    t_max = df["timestamp"].max().to_pydatetime()
    t_range = st.slider(
        "Janela de tempo",
        min_value=t_min, max_value=t_max,
        value=(t_min, t_max),
        format="HH:mm:ss",
    )

    st.divider()
    st.subheader("Limiares")
    vel_alerta  = st.number_input("Vel. alerta (m/s)",  value=VEL_ALERTA,  step=0.1)
    vel_alarme  = st.number_input("Vel. alarme (m/s)",  value=VEL_ALARME,  step=0.1)
    acel_alerta = st.number_input("Acel. alerta",       value=ACEL_ALERTA, step=0.01)
    acel_alarme = st.number_input("Acel. alarme",       value=ACEL_ALARME, step=0.01)
    temp_alerta = st.number_input("Temp. alerta (°C)",  value=float(TEMP_ALERTA), step=1.0)
    temp_alarme = st.number_input("Temp. alarme (°C)",  value=float(TEMP_ALARME), step=1.0)

df_f = df[(df["timestamp"] >= t_range[0]) & (df["timestamp"] <= t_range[1])].copy()

# Flags
for m in ["m1", "m2"]:
    df_f[f"{m}_vel_flag"]  = df_f[f"{m}_vel"].apply(lambda v: classificar(v, vel_alerta, vel_alarme))
    df_f[f"{m}_acel_flag"] = df_f[f"{m}_acel"].apply(lambda v: classificar(v, acel_alerta, acel_alarme))
    df_f[f"{m}_temp_flag"] = df_f[f"{m}_temp"].apply(lambda v: classificar(v, temp_alerta, temp_alarme))

# ── KPIs ──────────────────────────────────────────────────────────────────────
def kpi_row(prefix, label, df_f, vel_alerta, vel_alarme, acel_alerta, acel_alarme, temp_alerta, temp_alarme):
    cur_vel  = df_f[f"{prefix}_vel"].iloc[-1]
    cur_acel = df_f[f"{prefix}_acel"].iloc[-1]
    cur_temp = df_f[f"{prefix}_temp"].iloc[-1]
    max_vel  = df_f[f"{prefix}_vel"].max()
    avg_vel  = df_f[f"{prefix}_vel"].mean()
    n_alarme = int((df_f[f"{prefix}_vel_flag"] == 2).sum())

    flag_vel = classificar(cur_vel, vel_alerta, vel_alarme)
    cores    = {0: "normal", 1: "off", 2: "inverse"}

    st.markdown(f"**{label}**")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Velocidade atual", f"{cur_vel:.2f} m/s",
              delta=["✅ OK", "⚠️ Alerta", "🚨 Alarme"][flag_vel], delta_color=cores[flag_vel])
    c2.metric("Aceleração atual", f"{cur_acel:.3f}")
    c3.metric("Temperatura",      f"{cur_temp:.1f} °C")
    c4.metric("Vel. máxima",      f"{max_vel:.2f} m/s")
    c5.metric("Vel. média",       f"{avg_vel:.2f} m/s")
    c6.metric("Eventos alarme",   str(n_alarme), delta="crítico" if n_alarme > 0 else "normal",
              delta_color="inverse" if n_alarme > 0 else "off")

if motor_sel in ("Ambos", "Motor 1"):
    kpi_row("m1", "🔵 Motor 1", df_f, vel_alerta, vel_alarme, acel_alerta, acel_alarme, temp_alerta, temp_alarme)
if motor_sel == "Ambos":
    st.markdown("")
if motor_sel in ("Ambos", "Motor 2"):
    kpi_row("m2", "🔴 Motor 2", df_f, vel_alerta, vel_alarme, acel_alerta, acel_alarme, temp_alerta, temp_alarme)

st.divider()

# ── Gráfico de Velocidade com colorização por zona ────────────────────────────
st.subheader("📈 Timeline de Velocidade")

fig_vel = go.Figure()

vel_max_plot = max(df_f["m1_vel"].max(), df_f["m2_vel"].max()) * 1.15

# Faixas de fundo
fig_vel.add_hrect(y0=0, y1=vel_alerta, fillcolor="#2ecc71", opacity=0.07,
                  annotation_text="Normal", annotation_position="left")
fig_vel.add_hrect(y0=vel_alerta, y1=vel_alarme, fillcolor="#f39c12", opacity=0.07,
                  annotation_text="Alerta", annotation_position="left")
fig_vel.add_hrect(y0=vel_alarme, y1=vel_max_plot, fillcolor="#e74c3c", opacity=0.07,
                  annotation_text="Alarme", annotation_position="left")

def segmentos_coloridos(df_f, col_vel, col_flag, cor_base, nome):
    """Desenha linha com marcadores coloridos por zona."""
    # Linha base
    fig_vel.add_trace(go.Scatter(
        x=df_f["timestamp"], y=df_f[col_vel],
        mode="lines", name=nome,
        line=dict(color=cor_base, width=1.5),
        hovertemplate=f"<b>{nome}</b><br>Tempo: %{{x}}<br>Vel: %{{y:.3f}} m/s<extra></extra>",
    ))
    # Marcadores de alarme
    alarm_pts = df_f[df_f[col_flag] == 2]
    if not alarm_pts.empty:
        fig_vel.add_trace(go.Scatter(
            x=alarm_pts["timestamp"], y=alarm_pts[col_vel],
            mode="markers", name=f"{nome} — Alarme",
            marker=dict(color="#e74c3c", size=7, symbol="x"),
            showlegend=True,
        ))
    # Marcadores de alerta
    alerta_pts = df_f[df_f[col_flag] == 1]
    if not alerta_pts.empty:
        fig_vel.add_trace(go.Scatter(
            x=alerta_pts["timestamp"], y=alerta_pts[col_vel],
            mode="markers", name=f"{nome} — Alerta",
            marker=dict(color="#f39c12", size=5, symbol="triangle-up"),
            showlegend=True,
        ))

if motor_sel in ("Ambos", "Motor 1"):
    segmentos_coloridos(df_f, "m1_vel", "m1_vel_flag", "#3498db", "Motor 1")
if motor_sel in ("Ambos", "Motor 2"):
    segmentos_coloridos(df_f, "m2_vel", "m2_vel_flag", "#e74c3c", "Motor 2")

fig_vel.add_hline(y=vel_alerta, line_dash="dash", line_color="#f39c12", line_width=1)
fig_vel.add_hline(y=vel_alarme, line_dash="dash", line_color="#e74c3c", line_width=1)

fig_vel.update_layout(
    height=380, xaxis_title="Tempo", yaxis_title="Velocidade (m/s)",
    hovermode="x unified", margin=dict(l=50, r=20, t=30, b=40),
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
)
st.plotly_chart(fig_vel, use_container_width=True)

# ── Aceleração e Temperatura lado a lado ──────────────────────────────────────
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("⚡ Aceleração")
    fig_acel = go.Figure()
    fig_acel.add_hrect(y0=acel_alerta, y1=acel_alarme, fillcolor="#f39c12", opacity=0.1)
    fig_acel.add_hrect(y0=acel_alarme, y1=df_f[["m1_acel","m2_acel"]].max().max()*1.2,
                       fillcolor="#e74c3c", opacity=0.1)
    if motor_sel in ("Ambos", "Motor 1"):
        fig_acel.add_trace(go.Scatter(x=df_f["timestamp"], y=df_f["m1_acel"],
            mode="lines", name="Motor 1", line=dict(color="#3498db", width=1.3)))
    if motor_sel in ("Ambos", "Motor 2"):
        fig_acel.add_trace(go.Scatter(x=df_f["timestamp"], y=df_f["m2_acel"],
            mode="lines", name="Motor 2", line=dict(color="#e74c3c", width=1.3)))
    fig_acel.add_hline(y=acel_alerta, line_dash="dash", line_color="#f39c12", line_width=1)
    fig_acel.add_hline(y=acel_alarme, line_dash="dash", line_color="#e74c3c", line_width=1)
    fig_acel.update_layout(height=280, margin=dict(l=40, r=10, t=20, b=40),
                           xaxis_title="Tempo", yaxis_title="Aceleração")
    st.plotly_chart(fig_acel, use_container_width=True)

with col_b:
    st.subheader("🌡️ Temperatura")
    fig_temp = go.Figure()
    fig_temp.add_hrect(y0=temp_alerta, y1=temp_alarme, fillcolor="#f39c12", opacity=0.1)
    fig_temp.add_hrect(y0=temp_alarme, y1=max(df_f[["m1_temp","m2_temp"]].max().max()*1.1, temp_alarme+5),
                       fillcolor="#e74c3c", opacity=0.1)
    if motor_sel in ("Ambos", "Motor 1"):
        fig_temp.add_trace(go.Scatter(x=df_f["timestamp"], y=df_f["m1_temp"],
            mode="lines", name="Motor 1", line=dict(color="#3498db", width=1.5)))
    if motor_sel in ("Ambos", "Motor 2"):
        fig_temp.add_trace(go.Scatter(x=df_f["timestamp"], y=df_f["m2_temp"],
            mode="lines", name="Motor 2", line=dict(color="#e74c3c", width=1.5)))
    fig_temp.add_hline(y=temp_alerta, line_dash="dash", line_color="#f39c12", line_width=1)
    fig_temp.add_hline(y=temp_alarme, line_dash="dash", line_color="#e74c3c", line_width=1)
    fig_temp.update_layout(height=280, margin=dict(l=40, r=10, t=20, b=40),
                           xaxis_title="Tempo", yaxis_title="Temperatura (°C)")
    st.plotly_chart(fig_temp, use_container_width=True)

st.divider()

# ── Comparação direta M1 vs M2 ────────────────────────────────────────────────
st.subheader("🔁 Comparação Motor 1 vs Motor 2")

fig_comp = make_subplots(
    rows=1, cols=3,
    subplot_titles=("Velocidade (m/s)", "Aceleração", "Temperatura (°C)"),
    shared_xaxes=False,
)

for col_idx, (m1c, m2c, titulo) in enumerate([
    ("m1_vel",  "m2_vel",  "Velocidade"),
    ("m1_acel", "m2_acel", "Aceleração"),
    ("m1_temp", "m2_temp", "Temperatura"),
], start=1):
    fig_comp.add_trace(go.Box(y=df_f[m1c], name="Motor 1",
                               marker_color="#3498db", showlegend=(col_idx==1)), row=1, col=col_idx)
    fig_comp.add_trace(go.Box(y=df_f[m2c], name="Motor 2",
                               marker_color="#e74c3c", showlegend=(col_idx==1)), row=1, col=col_idx)

fig_comp.update_layout(height=320, margin=dict(l=30, r=10, t=40, b=30),
                       legend=dict(orientation="h", y=1.1))
st.plotly_chart(fig_comp, use_container_width=True)

# ── Correlação Velocidade × Aceleração ───────────────────────────────────────
st.subheader("🔗 Correlação Velocidade × Aceleração")
col_c1, col_c2 = st.columns(2)

for col_widget, prefix, nome, cor in [
    (col_c1, "m1", "Motor 1", "#3498db"),
    (col_c2, "m2", "Motor 2", "#e74c3c"),
]:
    with col_widget:
        fig_sc = px.scatter(
            df_f, x=f"{prefix}_vel", y=f"{prefix}_acel",
            color=f"{prefix}_vel_flag",
            color_discrete_map={0: "#2ecc71", 1: "#f39c12", 2: "#e74c3c"},
            labels={f"{prefix}_vel": "Velocidade (m/s)", f"{prefix}_acel": "Aceleração",
                    f"{prefix}_vel_flag": "Zona"},
            title=nome, opacity=0.6,
        )
        fig_sc.update_layout(height=280, margin=dict(l=40, r=10, t=40, b=30))
        st.plotly_chart(fig_sc, use_container_width=True)

st.divider()

# ── Log de Eventos ────────────────────────────────────────────────────────────
st.subheader("🚨 Log de Eventos (alarmes e alertas)")

eventos = []
for prefix, nome in [("m1", "Motor 1"), ("m2", "Motor 2")]:
    for var, lim_a, lim_al, unidade in [
        ("vel",  vel_alerta,  vel_alarme,  "m/s"),
        ("acel", acel_alerta, acel_alarme, ""),
        ("temp", temp_alerta, temp_alarme, "°C"),
    ]:
        col_flag = f"{prefix}_{var}_flag"
        col_val  = f"{prefix}_{var}"
        for flag_val, tipo in [(2, "🚨 ALARME"), (1, "⚠️ Alerta")]:
            pts = df_f[df_f[col_flag] == flag_val]
            if not pts.empty:
                pico = pts[col_val].max()
                primeiro = pts["timestamp"].min()
                eventos.append({
                    "Motor": nome,
                    "Variável": var.capitalize(),
                    "Tipo": tipo,
                    "Primeiro evento": primeiro.strftime("%H:%M:%S"),
                    "Pico": f"{pico:.3f} {unidade}",
                    "Ocorrências": len(pts),
                })

if eventos:
    df_ev = pd.DataFrame(eventos).sort_values("Tipo", ascending=False)
    st.dataframe(df_ev, use_container_width=True, hide_index=True)
else:
    st.success("Nenhum evento de alerta ou alarme no período selecionado.")

# ── Estatísticas ──────────────────────────────────────────────────────────────
with st.expander("📊 Estatísticas completas"):
    stats_cols = {
        "M1 Velocidade": "m1_vel", "M1 Aceleração": "m1_acel", "M1 Temperatura": "m1_temp",
        "M2 Velocidade": "m2_vel", "M2 Aceleração": "m2_acel", "M2 Temperatura": "m2_temp",
    }
    stats = {
        label: {
            "Mín": df_f[col].min(),
            "Máx": df_f[col].max(),
            "Média": df_f[col].mean(),
            "Desvio": df_f[col].std(),
            "P95": df_f[col].quantile(0.95),
        }
        for label, col in stats_cols.items()
    }
    df_stats = pd.DataFrame(stats).T.round(4)
    st.dataframe(df_stats, use_container_width=True)

# ── Dados brutos ──────────────────────────────────────────────────────────────
with st.expander("🗃️ Dados brutos (últimas 100 linhas)"):
    st.dataframe(df_f.tail(100).iloc[::-1], use_container_width=True)
