"""Página de análise espectral — recalcula FFT sobre janelas das leituras."""
import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_autorefresh import st_autorefresh

import database

ATIVO_ID = "MTR-MPU-01"

st.set_page_config(page_title="Análise Espectral — Digital TWIN", layout="wide")
st_autorefresh(interval=5000, key="espectral_refresh")

st.title("Análise Espectral de Vibração")
st.caption("FFT sobre a janela de leituras selecionada")

rows = database.get_leituras(ativo_id=ATIVO_ID, limit=500)
if not rows:
    st.warning("Sem dados. Inicie o serial_reader.py.")
    st.stop()

df = pd.DataFrame(rows)
df["coletado_em"] = pd.to_datetime(df["coletado_em"])
df = df.sort_values("coletado_em")

# ── Controles ──────────────────────────────────────────────────────────────────
col1, col2 = st.columns([3, 1])
with col1:
    janela = st.slider("Janela de análise (últimas N leituras)", 50, 500, 200, 10)
with col2:
    eixo = st.selectbox("Eixo", ["mag_rms", "ax_rms", "ay_rms", "az_rms"])

df_win = df.tail(janela)

if eixo not in df_win.columns or df_win[eixo].isna().all():
    st.info("Coluna não disponível nos dados. Rode com ESP32 real ou --simulate.")
    st.stop()

sinal = df_win[eixo].dropna().values.astype(float)

# Remove DC e aplica janela Hanning
sinal -= sinal.mean()
sinal *= np.hanning(len(sinal))

# FFT
N = len(sinal)
fs = 1.0  # 1 leitura/s vinda do banco (o ESP já pré-processou a 200 Hz)
freqs = np.fft.rfftfreq(N, d=1.0 / fs)
amplitudes = np.abs(np.fft.rfft(sinal)) * 2 / N

# ── Gráfico espectral ──────────────────────────────────────────────────────────
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=freqs, y=amplitudes,
    mode="lines", fill="tozeroy",
    line=dict(color="#9b59b6", width=1.5),
    name="Amplitude",
))

# Pico dominante
idx_pico = np.argmax(amplitudes[1:]) + 1
freq_pico = freqs[idx_pico]
amp_pico = amplitudes[idx_pico]
fig.add_vline(x=freq_pico, line_dash="dash", line_color="#e74c3c",
              annotation_text=f"Pico: {freq_pico:.3f} Hz")

fig.update_layout(
    title=f"Espectro FFT — eixo {eixo.upper()} (janela={N} amostras a 1 Sa/s)",
    xaxis_title="Frequência (Hz)",
    yaxis_title="Amplitude (g)",
    height=400,
    margin=dict(l=40, r=20, t=50, b=40),
)
st.plotly_chart(fig, use_container_width=True)

st.metric("Frequência dominante", f"{freq_pico:.3f} Hz",
          help="Pico de maior amplitude no espectro")

# ── Tabela de peaks históricos ─────────────────────────────────────────────────
st.subheader("Picos reportados pelo ESP32 (campo peaks)")
if "peaks" in df.columns:
    peaks_flat = []
    for _, row in df.tail(100).iterrows():
        raw = row.get("peaks")
        if raw:
            try:
                pks = json.loads(raw) if isinstance(raw, str) else raw
                for p in pks:
                    peaks_flat.append({"coletado_em": row["coletado_em"], "freq_hz": p})
            except Exception:
                pass
    if peaks_flat:
        df_peaks = pd.DataFrame(peaks_flat)
        fig_pk = go.Figure(go.Scatter(
            x=df_peaks["coletado_em"], y=df_peaks["freq_hz"],
            mode="markers", marker=dict(size=4, color="#e67e22"),
        ))
        fig_pk.update_layout(
            title="Frequências de pico ao longo do tempo",
            xaxis_title="Tempo", yaxis_title="Hz",
            height=250, margin=dict(l=40, r=20, t=40, b=30),
        )
        st.plotly_chart(fig_pk, use_container_width=True)
