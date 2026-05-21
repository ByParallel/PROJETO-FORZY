import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit_autorefresh import st_autorefresh

import database

ATIVO_ID = "MTR-MPU-01"

# ISO 10816 Classe I
ISO_OK = 1.8
ISO_ALERTA = 4.5

FLAG_COLOR = {0: "#2ecc71", 1: "#f39c12", 2: "#e74c3c"}
FLAG_LABEL = {0: "OK", 1: "ALERTA", 2: "ALARME"}

st.set_page_config(page_title="Dashboard — Digital TWIN", layout="wide")
st_autorefresh(interval=2000, key="dashboard_refresh")

st.title("Dashboard de Vibração — Motor MTR-MPU-01")
st.caption("Dados em tempo real via ESP32 + MPU6050 | ISO 10816 Classe I")

# ── Carregar dados ─────────────────────────────────────────────────────────────
rows = database.get_leituras(ativo_id=ATIVO_ID, limit=300)

if not rows:
    st.warning("Nenhuma leitura encontrada. Inicie o serial_reader.py (ou use --simulate).")
    st.stop()

df = pd.DataFrame(rows)
df["coletado_em"] = pd.to_datetime(df["coletado_em"])
df = df.sort_values("coletado_em")

ultima = df.iloc[-1]
flag_atual = int(ultima.get("flag_anomalia", 0))

# ── KPIs ──────────────────────────────────────────────────────────────────────
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    vib = ultima.get("vibracao_mm_s") or 0
    st.metric("Vibração RMS", f"{vib:.3f} mm/s",
              delta=f"{FLAG_LABEL[flag_atual]}",
              delta_color="off")

with col2:
    temp = ultima.get("temperatura_c") or 0
    st.metric("Temperatura", f"{temp:.1f} °C")

with col3:
    freq = ultima.get("freq_hz") or 0
    st.metric("Freq. dominante", f"{freq:.1f} Hz")

with col4:
    mag = ultima.get("mag_rms") or 0
    st.metric("Aceleração RMS", f"{mag*1000:.2f} mg")

with col5:
    total = len(df)
    alarmes = int((df["flag_anomalia"] == 2).sum())
    st.metric("Leituras (alarmes)", f"{total} ({alarmes})")

st.divider()

# ── Status ISO 10816 ───────────────────────────────────────────────────────────
cor = FLAG_COLOR[flag_atual]
label = FLAG_LABEL[flag_atual]
st.markdown(
    f"""<div style="background:{cor};color:white;padding:12px 20px;
    border-radius:8px;font-size:1.2rem;font-weight:bold;text-align:center;">
    Status ISO 10816: {label} — {vib:.3f} mm/s
    </div>""",
    unsafe_allow_html=True,
)
st.markdown("")

# ── Gráfico de vibração temporal ───────────────────────────────────────────────
fig_vib = go.Figure()

fig_vib.add_trace(go.Scatter(
    x=df["coletado_em"], y=df["vibracao_mm_s"],
    mode="lines", name="Vibração RMS",
    line=dict(color="#3498db", width=1.5),
))

# Faixas ISO
fig_vib.add_hrect(y0=0, y1=ISO_OK, fillcolor="#2ecc71", opacity=0.08,
                  annotation_text="OK", annotation_position="left")
fig_vib.add_hrect(y0=ISO_OK, y1=ISO_ALERTA, fillcolor="#f39c12", opacity=0.08,
                  annotation_text="Alerta", annotation_position="left")
fig_vib.add_hrect(y0=ISO_ALERTA, y1=max(ISO_ALERTA * 2, df["vibracao_mm_s"].max() * 1.2),
                  fillcolor="#e74c3c", opacity=0.08,
                  annotation_text="Alarme", annotation_position="left")

fig_vib.update_layout(
    title="Velocidade de Vibração RMS (mm/s)",
    xaxis_title="Tempo",
    yaxis_title="mm/s",
    height=350,
    margin=dict(l=40, r=20, t=40, b=30),
    hovermode="x unified",
)
st.plotly_chart(fig_vib, use_container_width=True)

# ── Gráfico de aceleração por eixo ─────────────────────────────────────────────
col_a, col_b = st.columns(2)

with col_a:
    if {"ax_rms", "ay_rms", "az_rms"}.issubset(df.columns):
        fig_accel = go.Figure()
        for eixo, cor_eixo in [("ax_rms", "#e74c3c"), ("ay_rms", "#2ecc71"), ("az_rms", "#3498db")]:
            fig_accel.add_trace(go.Scatter(
                x=df["coletado_em"], y=df[eixo] * 1000,
                mode="lines", name=eixo.upper().replace("_RMS", ""),
                line=dict(color=cor_eixo, width=1.2),
            ))
        fig_accel.update_layout(
            title="Aceleração RMS por Eixo (mg)",
            xaxis_title="Tempo", yaxis_title="mg",
            height=300, margin=dict(l=40, r=20, t=40, b=30),
        )
        st.plotly_chart(fig_accel, use_container_width=True)

with col_b:
    if "temperatura_c" in df.columns:
        fig_temp = px.line(df, x="coletado_em", y="temperatura_c",
                           title="Temperatura (°C)", labels={"temperatura_c": "°C", "coletado_em": "Tempo"})
        fig_temp.update_traces(line_color="#e67e22")
        fig_temp.update_layout(height=300, margin=dict(l=40, r=20, t=40, b=30))
        st.plotly_chart(fig_temp, use_container_width=True)

# ── Histograma de vibração + ISO ───────────────────────────────────────────────
st.subheader("Distribuição de Vibração")
fig_hist = px.histogram(
    df, x="vibracao_mm_s", nbins=40,
    color_discrete_sequence=["#3498db"],
    labels={"vibracao_mm_s": "Vibração RMS (mm/s)"},
)
fig_hist.add_vline(x=ISO_OK, line_dash="dash", line_color="#f39c12",
                   annotation_text="1.8 mm/s (alerta)")
fig_hist.add_vline(x=ISO_ALERTA, line_dash="dash", line_color="#e74c3c",
                   annotation_text="4.5 mm/s (alarme)")
fig_hist.update_layout(height=280, margin=dict(l=40, r=20, t=30, b=30))
st.plotly_chart(fig_hist, use_container_width=True)

# ── Tabela das últimas leituras ────────────────────────────────────────────────
with st.expander("Últimas leituras brutas"):
    colunas = ["coletado_em", "vibracao_mm_s", "freq_hz", "temperatura_c",
               "ax_rms", "ay_rms", "az_rms", "mag_rms", "flag_anomalia", "fonte"]
    colunas_disponiveis = [c for c in colunas if c in df.columns]
    st.dataframe(df[colunas_disponiveis].tail(50).iloc[::-1], use_container_width=True)
