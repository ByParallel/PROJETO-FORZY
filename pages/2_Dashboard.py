"""Dashboard consolidado — Monitoramento · Espectral · Operacional · Histórico"""
import math
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import streamlit as st
from pathlib import Path
from datetime import datetime

st.set_page_config(page_title="Dashboard — IMS Forzy", layout="wide")
import sys; sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.theme import apply as _apply_theme, sidebar_header as _sh
_apply_theme(); _sh()

import database
from utils.mock_data import gerar_leitura_simulada, gerar_historico_simulado
from utils.mock_data import MODO_NORMAL, MODO_DESBALANCO, MODO_CAVITACAO, MODO_DESALINHAMENTO

# ── Autorefresh opcional ──────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("#### ⚙️ Configurações Globais")
    auto_ref = st.toggle("Auto-refresh (Monitoramento)", value=True)
    if auto_ref:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=2000, key="dash_global_refresh")

# ── Tabs principais ───────────────────────────────────────────────────────────
tab_mon, tab_esp, tab_oper, tab_hist = st.tabs([
    "📊 Monitoramento",
    "🔬 Espectral",
    "📈 Operacional",
    "⏱ Histórico",
])

# ═════════════════════════════════════════════════════════════════════════════
# TAB 1 — MONITORAMENTO
# ═════════════════════════════════════════════════════════════════════════════
with tab_mon:
    ATIVO_ID = "MTR-VIM32-01"
    LIMITES = {
        "ISO 10816 (< 15 kW)":  {"alerta": 1.8, "alarme": 4.5},
        "ISO 20816 (15–75 kW)": {"alerta": 2.3, "alarme": 7.1},
    }
    FLAG_COLOR = {0: "#2ecc71", 1: "#f39c12", 2: "#e74c3c"}
    FLAG_LABEL = {0: "OK", 1: "ALERTA", 2: "ALARME"}

    # Controles inline
    ctrl1, ctrl2, ctrl3 = st.columns([2, 2, 3])
    with ctrl1:
        norma = st.selectbox("Norma ISO", list(LIMITES.keys()), key="mon_norma")
    with ctrl2:
        modo_demo = st.toggle("Modo Demo", value=True, key="mon_demo")
    with ctrl3:
        if modo_demo:
            modo_falha = st.selectbox("Cenário", [MODO_NORMAL, MODO_DESBALANCO, MODO_CAVITACAO, MODO_DESALINHAMENTO],
                format_func=lambda x: {"normal":"✅ Normal","desbalanco":"⚠️ Desbalanceamento",
                                       "cavitacao":"🌊 Cavitação","desalinhamento":"❌ Desalinhamento"}[x],
                key="mon_falha")
        else:
            modo_falha = MODO_NORMAL

    ISO_ALERTA = LIMITES[norma]["alerta"]
    ISO_ALARME = LIMITES[norma]["alarme"]

    # Dados
    if modo_demo:
        if "demo_hist" not in st.session_state:
            st.session_state.demo_hist = gerar_historico_simulado(300, incluir_falha=False)
            st.session_state.demo_t = 300.0
        st.session_state.demo_t += 1.0
        nova = gerar_leitura_simulada(t=st.session_state.demo_t, modo=modo_falha)
        st.session_state.demo_hist.append(nova)
        if len(st.session_state.demo_hist) > 400:
            st.session_state.demo_hist = st.session_state.demo_hist[-400:]
        rows = st.session_state.demo_hist
    else:
        rows = database.get_leituras(ativo_id=ATIVO_ID, limit=300)
        if not rows:
            st.warning("Sem dados no banco. Ative o **Modo Demo**.")
            st.stop()

    df_mon = pd.DataFrame(rows)
    if "coletado_em" in df_mon.columns:
        df_mon["coletado_em"] = pd.to_datetime(df_mon["coletado_em"])
        df_mon = df_mon.sort_values("coletado_em")
    else:
        df_mon["coletado_em"] = pd.date_range(end=pd.Timestamp.now(), periods=len(df_mon), freq="2s")

    ultima = df_mon.iloc[-1]
    vib   = float(ultima.get("vibracao_mm_s") or 0)
    temp  = float(ultima.get("temperatura_c") or 0)
    apeak = float(ultima.get("a_peak_g") or 0)
    arms  = float(ultima.get("mag_rms") or 0)
    freq  = float(ultima.get("freq_hz") or 0)
    flag_atual = 2 if vib >= ISO_ALARME else (1 if vib >= ISO_ALERTA else 0)

    # Health Score
    vib_ratio  = min(vib / ISO_ALARME, 1.0)
    temp_ratio = min(max((temp - 35) / 45, 0), 1.0)
    peak_ratio = min(apeak / 5.0, 1.0)
    health = max(0, round(100 - 60*vib_ratio - 25*temp_ratio - 15*peak_ratio))
    health_cor = "#2ecc71" if health >= 70 else ("#f39c12" if health >= 40 else "#e74c3c")

    # Banner
    cor = FLAG_COLOR[flag_atual]
    st.markdown(f'<div style="border-radius:8px;padding:10px 20px;font-size:1rem;font-weight:bold;'
                f'text-align:center;color:white;background:{cor};margin:8px 0">'
                f'Status {norma}: {FLAG_LABEL[flag_atual]} — {vib:.3f} mm/s</div>',
                unsafe_allow_html=True)
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:12px;margin:6px 0 14px 0">'
        f'<span style="color:#aaa;font-size:.9rem">Health Score</span>'
        f'<div style="flex:1;background:#333;border-radius:8px;height:14px;overflow:hidden">'
        f'<div style="width:{health}%;background:{health_cor};height:14px;border-radius:8px"></div></div>'
        f'<span style="color:{health_cor};font-weight:bold">{health}/100</span></div>',
        unsafe_allow_html=True)

    # KPIs
    k1,k2,k3,k4,k5,k6 = st.columns(6)
    k1.metric("Vibração RMS",    f"{vib:.3f} mm/s", FLAG_LABEL[flag_atual], delta_color="off")
    k2.metric("Acel. Pico",      f"{apeak:.3f} g")
    k3.metric("Acel. RMS",       f"{arms:.4f} g")
    k4.metric("Temperatura",     f"{temp:.1f} °C")
    k5.metric("Freq. dominante", f"{freq:.1f} Hz")
    k6.metric("Alarmes", str(int((df_mon["flag_anomalia"] >= 2).sum() if "flag_anomalia" in df_mon.columns else 0)))

    st.divider()

    # Gauges
    st.subheader("Gauges — Estado Atual")
    g1,g2,g3,g4 = st.columns(4)

    def _gauge(val, title, maximo, unidade, lim_a, lim_al):
        fv = 2 if val>=lim_al else (1 if val>=lim_a else 0)
        fig = go.Figure(go.Indicator(
            mode="gauge+number", value=val,
            title={"text":title,"font":{"size":13}},
            number={"suffix":f" {unidade}","font":{"size":18}},
            gauge={"axis":{"range":[0,maximo]},
                   "bar":{"color":FLAG_COLOR[fv]},
                   "steps":[{"range":[0,lim_a],"color":"#1a2e1a"},
                             {"range":[lim_a,lim_al],"color":"#2e2200"},
                             {"range":[lim_al,maximo],"color":"#2e0d0d"}],
                   "threshold":{"line":{"color":"#e74c3c","width":3},"thickness":0.85,"value":lim_al}},
        ))
        fig.update_layout(height=220, margin=dict(l=20,r=20,t=30,b=10),
                          paper_bgcolor="rgba(0,0,0,0)", font_color="#eee")
        return fig

    with g1: st.plotly_chart(_gauge(vib,"Vibração RMS (mm/s)",max(ISO_ALARME*2,10),"mm/s",ISO_ALERTA,ISO_ALARME), use_container_width=True, key="mon_g1")
    with g2: st.plotly_chart(_gauge(apeak,"Acel. Pico (g)",5.0,"g",0.3,0.5), use_container_width=True, key="mon_g2")
    with g3: st.plotly_chart(_gauge(arms,"Acel. RMS (g)",3.0,"g",0.2,0.4), use_container_width=True, key="mon_g3")
    with g4: st.plotly_chart(_gauge(temp,"Temperatura (°C)",85.0,"°C",60.0,75.0), use_container_width=True, key="mon_g4")

    st.divider()

    # Gráfico vibração
    st.subheader("Velocidade de Vibração RMS — Histórico")
    fig_vib = go.Figure()
    fig_vib.add_trace(go.Scatter(x=df_mon["coletado_em"], y=df_mon["vibracao_mm_s"],
        mode="lines", name="Vibração RMS", line=dict(color="#3498db",width=1.5),
        fill="tozeroy", fillcolor="rgba(52,152,219,0.08)"))
    vib_max_plot = max(ISO_ALARME*2, df_mon["vibracao_mm_s"].max()*1.2)
    fig_vib.add_hrect(y0=0, y1=ISO_ALERTA, fillcolor="#2ecc71", opacity=0.07,
                      annotation_text="OK", annotation_position="left")
    fig_vib.add_hrect(y0=ISO_ALERTA, y1=ISO_ALARME, fillcolor="#f39c12", opacity=0.07,
                      annotation_text="Alerta", annotation_position="left")
    fig_vib.add_hrect(y0=ISO_ALARME, y1=vib_max_plot, fillcolor="#e74c3c", opacity=0.07,
                      annotation_text="Alarme", annotation_position="left")
    fig_vib.add_hline(y=ISO_ALERTA, line_dash="dash", line_color="#f39c12", line_width=1)
    fig_vib.add_hline(y=ISO_ALARME, line_dash="dash", line_color="#e74c3c", line_width=1)
    fig_vib.update_layout(height=300, xaxis_title="Tempo", yaxis_title="mm/s",
                          hovermode="x unified", margin=dict(l=50,r=20,t=30,b=40),
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                          font_color="#eee", xaxis=dict(gridcolor="#222"), yaxis=dict(gridcolor="#222"))
    st.plotly_chart(fig_vib, use_container_width=True, key="mon_vib")

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Aceleração de Pico (g)")
        y_apeak = df_mon.get("a_peak_g", df_mon.get("mag_rms", pd.Series([0]*len(df_mon))))
        fig_pk = go.Figure(go.Scatter(x=df_mon["coletado_em"], y=y_apeak,
            mode="lines", line=dict(color="#9b59b6",width=1.4),
            fill="tozeroy", fillcolor="rgba(155,89,182,0.07)"))
        fig_pk.add_hline(y=0.3, line_dash="dash", line_color="#f39c12", line_width=1)
        fig_pk.add_hline(y=0.5, line_dash="dash", line_color="#e74c3c", line_width=1)
        fig_pk.update_layout(height=260, margin=dict(l=50,r=20,t=20,b=40),
                             paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                             font_color="#eee", xaxis=dict(gridcolor="#222"), yaxis=dict(gridcolor="#222"))
        st.plotly_chart(fig_pk, use_container_width=True, key="mon_pk")

    with col_b:
        st.subheader("Temperatura (°C)")
        fig_temp = go.Figure(go.Scatter(x=df_mon["coletado_em"], y=df_mon["temperatura_c"],
            mode="lines", line=dict(color="#e67e22",width=1.5),
            fill="tozeroy", fillcolor="rgba(230,126,34,0.07)"))
        fig_temp.add_hline(y=60, line_dash="dash", line_color="#f39c12", line_width=1)
        fig_temp.add_hline(y=75, line_dash="dash", line_color="#e74c3c", line_width=1)
        fig_temp.update_layout(height=260, margin=dict(l=50,r=20,t=20,b=40),
                               paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                               font_color="#eee", xaxis=dict(gridcolor="#222"), yaxis=dict(gridcolor="#222"))
        st.plotly_chart(fig_temp, use_container_width=True, key="mon_temp")

    st.subheader("Distribuição Estatística — Vibração RMS")
    fig_hist_mon = px.histogram(df_mon, x="vibracao_mm_s", nbins=40,
                                color_discrete_sequence=["#3498db"],
                                labels={"vibracao_mm_s":"Vibração RMS (mm/s)"})
    fig_hist_mon.add_vline(x=ISO_ALERTA, line_dash="dash", line_color="#f39c12")
    fig_hist_mon.add_vline(x=ISO_ALARME, line_dash="dash", line_color="#e74c3c")
    fig_hist_mon.update_layout(height=240, margin=dict(l=40,r=20,t=20,b=30),
                               paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#eee")
    st.plotly_chart(fig_hist_mon, use_container_width=True, key="mon_hist")

    with st.expander("Últimas leituras brutas"):
        cols_show = [c for c in ["coletado_em","vibracao_mm_s","a_peak_g","mag_rms",
                                  "freq_hz","temperatura_c","flag_anomalia","fonte"] if c in df_mon.columns]
        st.dataframe(df_mon[cols_show].tail(50).iloc[::-1], use_container_width=True)


# ═════════════════════════════════════════════════════════════════════════════
# TAB 2 — ESPECTRAL
# ═════════════════════════════════════════════════════════════════════════════
with tab_esp:
    st.subheader("🔬 Análise Espectral de Vibração")
    st.caption("FFT simulada — sensor VIM32PL (faixa real 10–1000 Hz)")

    ec1, ec2, ec3, ec4 = st.columns(4)
    with ec1: rpm = st.slider("RPM", 1000, 4000, 2980, 10, key="esp_rpm")
    with ec2: modo_esp = st.selectbox("Cenário", [MODO_NORMAL, MODO_DESBALANCO, MODO_CAVITACAO, MODO_DESALINHAMENTO],
                  format_func=lambda x: {"normal":"✅ Normal","desbalanco":"⚠️ Desbalanceamento",
                                         "cavitacao":"🌊 Cavitação","desalinhamento":"❌ Desalinhamento"}[x], key="esp_modo")
    with ec3: fs = st.selectbox("Amostragem (Sa/s)", [200, 500, 1000], key="esp_fs")
    with ec4: janela_s = st.slider("Janela (s)", 2, 20, 5, key="esp_janela")

    ec5, ec6 = st.columns(2)
    with ec5: mostrar_harmonicas = st.toggle("Marcar harmônicas RPM", value=True, key="esp_harm")
    with ec6: mostrar_bandas = st.toggle("Marcar bandas de falha", value=True, key="esp_bandas")

    freq_rot = rpm / 60.0

    def _gerar_sinal(fs, dur, modo, freq_rot):
        rng = np.random.default_rng(seed=42)
        N = int(fs * dur)
        t = np.linspace(0, dur, N, endpoint=False)
        sinal = rng.normal(0, 0.005, N)
        if modo == MODO_NORMAL:
            sinal += 0.04*np.sin(2*np.pi*freq_rot*t) + 0.01*np.sin(2*np.pi*freq_rot*2*t)
        elif modo == MODO_DESBALANCO:
            sinal += 0.18*np.sin(2*np.pi*freq_rot*t) + 0.04*np.sin(2*np.pi*freq_rot*2*t) + 0.01*np.sin(2*np.pi*freq_rot*3*t)
        elif modo == MODO_CAVITACAO:
            sinal += rng.normal(0,0.05,N) + 0.06*np.sin(2*np.pi*freq_rot*0.5*t) + 0.03*np.sin(2*np.pi*freq_rot*t)
        elif modo == MODO_DESALINHAMENTO:
            sinal += 0.05*np.sin(2*np.pi*freq_rot*t) + 0.16*np.sin(2*np.pi*freq_rot*2*t) + 0.07*np.sin(2*np.pi*freq_rot*3*t)
        return sinal

    sinal = _gerar_sinal(fs, janela_s, modo_esp, freq_rot)
    N = len(sinal)
    sinal -= sinal.mean()
    sinal_w = sinal * np.hanning(N)
    freqs = np.fft.rfftfreq(N, d=1.0/fs)
    amplitudes = np.abs(np.fft.rfft(sinal_w)) * 2 / N
    idx_pico = np.argmax(amplitudes[1:]) + 1
    freq_pico = freqs[idx_pico]
    amp_pico  = amplitudes[idx_pico]

    fig_esp = go.Figure()
    fig_esp.add_trace(go.Scatter(x=freqs, y=amplitudes, mode="lines", fill="tozeroy",
        line=dict(color="#9b59b6",width=1.5), fillcolor="rgba(155,89,182,0.12)", name="Amplitude (g)"))
    fig_esp.add_vline(x=freq_pico, line_dash="dash", line_color="#e74c3c",
                      annotation_text=f"Pico: {freq_pico:.2f} Hz", annotation_font_color="#e74c3c")
    if mostrar_harmonicas:
        for h, cor, label in [(1,"#3498db","1x"),(2,"#2ecc71","2x"),(3,"#f39c12","3x"),(4,"#e67e22","4x")]:
            fx = freq_rot * h
            if fx < freqs[-1]:
                fig_esp.add_vline(x=fx, line_dash="dot", line_color=cor, line_width=1,
                                  annotation_text=f"{label} {fx:.1f}Hz", annotation_font_color=cor,
                                  annotation_position="top")
    if mostrar_bandas:
        fig_esp.add_vrect(x0=freq_rot*0.4, x1=freq_rot*0.6, fillcolor="rgba(52,152,219,0.06)",
                          annotation_text="Sub-harm.", annotation_font_size=10)
        fig_esp.add_vrect(x0=freq_rot*0.9, x1=freq_rot*1.1, fillcolor="rgba(230,126,34,0.07)",
                          annotation_text="Desbal.", annotation_font_size=10)
    fig_esp.update_layout(title=f"Espectro FFT — {modo_esp} · {rpm} RPM · fs={fs} Sa/s",
        xaxis_title="Frequência (Hz)", yaxis_title="Amplitude (g)", height=400,
        margin=dict(l=50,r=30,t=60,b=50), paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", font_color="#eee",
        xaxis=dict(gridcolor="#222"), yaxis=dict(gridcolor="#222"), hovermode="x unified")
    st.plotly_chart(fig_esp, use_container_width=True, key="esp_fft")

    m1,m2,m3,m4 = st.columns(4)
    m1.metric("Pico dominante", f"{freq_pico:.2f} Hz")
    m2.metric("Amplitude do pico", f"{amp_pico:.4f} g")
    m3.metric("Freq. rotação (1x)", f"{freq_rot:.2f} Hz")
    m4.metric("Relação pico/1x", f"{freq_pico/freq_rot:.2f}x")

    st.divider()
    st.subheader("Espectrograma — Evolução Temporal")

    n_frames = 30
    frame_len = fs
    sinal_long = _gerar_sinal(fs, n_frames, modo_esp, freq_rot)
    Z = []
    for i in range(n_frames):
        seg = sinal_long[i*frame_len:(i+1)*frame_len]
        seg -= seg.mean(); seg *= np.hanning(len(seg))
        Z.append(np.abs(np.fft.rfft(seg)) * 2 / len(seg))
    Z = np.array(Z)
    f_ax = np.fft.rfftfreq(frame_len, 1.0/fs)

    fig_wf = go.Figure(go.Heatmap(z=Z, x=f_ax, y=list(range(n_frames)), colorscale="Plasma",
        colorbar=dict(title=dict(text="g",font=dict(color="#eee")),tickfont=dict(color="#eee")),
        hovertemplate="Freq: %{x:.1f} Hz<br>t: %{y}s<br>Amp: %{z:.5f} g<extra></extra>"))
    if mostrar_harmonicas:
        for h, cor in [(1,"#3498db"),(2,"#2ecc71"),(3,"#f39c12")]:
            fx = freq_rot * h
            if fx < f_ax[-1]:
                fig_wf.add_vline(x=fx, line_color=cor, line_width=1.5, line_dash="dot")
    fig_wf.update_layout(xaxis_title="Frequência (Hz)", yaxis_title="Tempo (s)", height=350,
                         margin=dict(l=50,r=20,t=20,b=50),
                         paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#eee")
    st.plotly_chart(fig_wf, use_container_width=True, key="esp_wf")

    with st.expander("Top 10 picos espectrais"):
        top_idx = np.argsort(amplitudes[1:])[::-1][:10] + 1
        df_picos = pd.DataFrame({"Frequência (Hz)":freqs[top_idx].round(2),
                                 "Amplitude (g)":amplitudes[top_idx].round(6),
                                 "Relação 1x RPM":(freqs[top_idx]/freq_rot).round(2)})
        st.dataframe(df_picos, use_container_width=True, hide_index=True)


# ═════════════════════════════════════════════════════════════════════════════
# TAB 3 — OPERACIONAL (Dataset Forzy)
# ═════════════════════════════════════════════════════════════════════════════
with tab_oper:
    SEARCH_PATHS = [
        Path(__file__).parent.parent / "data" / "forzy.csv",
        Path.home() / "Downloads" / "History_32026-05-19T11-46-10-920.csv",
    ]
    csv_path = next((p for p in SEARCH_PATHS if p.exists()), None)
    if not csv_path:
        st.error("CSV não encontrado. Coloque em `data/forzy.csv`.")
    else:
        @st.cache_data
        def _load_forzy(path):
            df = pd.read_csv(path, sep=";", skiprows=3, header=None,
                usecols=[0,3,4,5,6,7,8],
                names=["timestamp","m1_vel","m1_acel","m1_temp","m2_vel","m2_acel","m2_temp"])
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            for c in df.columns[1:]:
                df[c] = pd.to_numeric(df[c], errors="coerce")
            df = df.dropna(subset=["m1_vel","m2_vel"]).sort_values("timestamp").reset_index(drop=True)
            df = (df.set_index("timestamp").groupby(level=0).mean()
                    .resample("1s").mean().interpolate("linear").reset_index())
            rng = np.random.default_rng(42)
            t   = np.arange(len(df))
            for p in ["m1","m2"]:
                v = df[f"{p}_vel"].values; a = df[f"{p}_acel"].values
                df[f"{p}_vel"]  = np.clip(v + v*0.10*np.sin(2*np.pi*0.15*t) + v*0.05*np.sin(2*np.pi*0.35*t+0.8) + rng.normal(0, np.clip(v*0.04,0.003,0.12)), 0, None)
                df[f"{p}_acel"] = np.clip(a + a*0.12*np.sin(2*np.pi*0.20*t+0.4) + rng.normal(0, np.clip(a*0.05,0.001,0.04)), 0, None)
            return df

        @st.cache_data
        def _compute_flags(path, va, val, aa, aal, ta, tal, t0, t1):
            df = _load_forzy(path)
            df = df[(df.timestamp >= t0) & (df.timestamp <= t1)].copy()
            for m in ["m1","m2"]:
                df[f"{m}_vel_flag"]  = np.where(df[f"{m}_vel"]  >= val, 2, np.where(df[f"{m}_vel"]  >= va,  1, 0)).astype("int8")
                df[f"{m}_acel_flag"] = np.where(df[f"{m}_acel"] >= aal, 2, np.where(df[f"{m}_acel"] >= aa,  1, 0)).astype("int8")
                df[f"{m}_temp_flag"] = np.where(df[f"{m}_temp"] >= tal, 2, np.where(df[f"{m}_temp"] >= ta,  1, 0)).astype("int8")
            return df

        df_forzy = _load_forzy(str(csv_path))
        MAX_DISPLAY = 3000

        def _downsample(df):
            if len(df) <= MAX_DISPLAY: return df
            return df.iloc[::len(df)//MAX_DISPLAY].reset_index(drop=True)

        # Controles inline
        oc1, oc2 = st.columns([2,3])
        with oc1:
            motor_sel = st.radio("Exibir", ["Ambos os motores","Motor 1","Motor 2"],
                                 horizontal=True, key="oper_motor")
        with oc2:
            t_min = df_forzy["timestamp"].min().to_pydatetime()
            t_max = df_forzy["timestamp"].max().to_pydatetime()
            t_range = st.slider("Janela de tempo", min_value=t_min, max_value=t_max,
                                value=(t_min,t_max), format="HH:mm:ss", key="oper_trange")

        with st.expander("⚙️ Limiares ISO 10816", expanded=False):
            oc3,oc4,oc5,oc6,oc7,oc8 = st.columns(6)
            vel_alerta  = oc3.number_input("Vel. alerta",  value=1.8,  step=0.1, format="%.1f", key="oper_va")
            vel_alarme  = oc4.number_input("Vel. alarme",  value=4.5,  step=0.1, format="%.1f", key="oper_val")
            acel_alerta = oc5.number_input("Acel. alerta", value=0.25, step=0.01,format="%.2f", key="oper_aa")
            acel_alarme = oc6.number_input("Acel. alarme", value=0.45, step=0.01,format="%.2f", key="oper_aal")
            temp_alerta = oc7.number_input("Temp. alerta", value=35.0, step=1.0, format="%.1f", key="oper_ta")
            temp_alarme = oc8.number_input("Temp. alarme", value=42.0, step=1.0, format="%.1f", key="oper_tal")

        df_f = _compute_flags(str(csv_path), vel_alerta, vel_alarme, acel_alerta, acel_alarme,
                              temp_alerta, temp_alarme, str(t_range[0]), str(t_range[1]))
        df_plot = _downsample(df_f)

        COR_O  = {0:"#2ecc71", 1:"#f39c12", 2:"#e74c3c"}
        NOME_O = {0:"OK", 1:"ALERTA", 2:"ALARME"}
        BADGE_O= {0:"#0d3320", 1:"#2e1f00", 2:"#2e0d0d"}
        PLOT_O = dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font_color="#cdd9e5", margin=dict(l=50,r=20,t=30,b=40),
                      xaxis=dict(gridcolor="#1a2d3a"), yaxis=dict(gridcolor="#1a2d3a"),
                      hovermode="x unified")

        def _flag_o(v, a, al): return 2 if v>=al else 1 if v>=a else 0

        v1  = df_f.m1_vel.iloc[-1];   v2  = df_f.m2_vel.iloc[-1]
        a1  = df_f.m1_acel.iloc[-1];  a2  = df_f.m2_acel.iloc[-1]
        t1_ = df_f.m1_temp.iloc[-1];  t2_ = df_f.m2_temp.iloc[-1]
        f1  = max(_flag_o(v1,vel_alerta,vel_alarme), _flag_o(a1,acel_alerta,acel_alarme), _flag_o(t1_,temp_alerta,temp_alarme))
        f2  = max(_flag_o(v2,vel_alerta,vel_alarme), _flag_o(a2,acel_alerta,acel_alarme), _flag_o(t2_,temp_alerta,temp_alarme))

        # Cards dos motores
        cc1, cc2 = st.columns(2)
        for col_w, prefix, nome, cor_n, fv, vel, acel, temp_, f_g in [
            (cc1,"m1","⚙️ Motor 1","#3498db",_flag_o(v1,vel_alerta,vel_alarme),v1,a1,t1_,f1),
            (cc2,"m2","⚙️ Motor 2","#e74c3c",_flag_o(v2,vel_alerta,vel_alarme),v2,a2,t2_,f2),
        ]:
            with col_w:
                n_al = int((df_f[f"{prefix}_vel_flag"]==2).sum())
                st.markdown(f'<div style="background:#0d1b2e;border:1.5px solid {COR_O[f_g]};'
                            f'border-radius:8px;padding:12px 16px;margin-bottom:8px">'
                            f'<span style="font-weight:700;color:{cor_n}">{nome}</span>'
                            f'<span style="float:right;background:{BADGE_O[f_g]};color:{COR_O[f_g]};'
                            f'padding:2px 8px;border-radius:4px;font-size:.75rem">{NOME_O[f_g]}</span></div>',
                            unsafe_allow_html=True)
                mc1,mc2,mc3,mc4 = st.columns(4)
                mc1.metric("Velocidade", f"{vel:.3f} mm/s")
                mc2.metric("Aceleração", f"{acel:.3f} g")
                mc3.metric("Temperatura",f"{temp_:.1f} °C")
                mc4.metric("Alarmes",    str(n_al))

        st.divider()

        # Sub-tabs do Operacional
        sub1, sub2, sub3, sub4, sub5 = st.tabs(["📈 Timeline","🔬 Análise","⚖️ Comparação","🚨 Eventos","📊 Estatísticas"])

        with sub1:
            fig_vel_o = go.Figure()
            for col_v, col_fl, nome, cor in [("m1_vel","m1_vel_flag","Motor 1","#3498db"),
                                              ("m2_vel","m2_vel_flag","Motor 2","#e74c3c")]:
                if "Motor" in motor_sel and nome not in motor_sel: continue
                fig_vel_o.add_trace(go.Scattergl(x=df_plot.timestamp, y=df_plot[col_v],
                    mode="lines", name=nome, line=dict(color=cor,width=1.4)))
                alm = df_plot[df_plot[col_fl]==2]
                if not alm.empty:
                    fig_vel_o.add_trace(go.Scattergl(x=alm.timestamp, y=alm[col_v], mode="markers",
                        name=f"{nome} Alarme", marker=dict(color="#e74c3c",size=4,symbol="x")))
            ymax_o = max(vel_alarme*1.4, df_plot.m1_vel.max(), df_plot.m2_vel.max())*1.1
            fig_vel_o.add_hline(y=vel_alerta, line_dash="dot", line_color="#f39c12", line_width=1)
            fig_vel_o.add_hline(y=vel_alarme, line_dash="dot", line_color="#e74c3c", line_width=1)
            fig_vel_o.update_layout(height=320, title="Velocidade RMS (mm/s)", **PLOT_O,
                                    yaxis=dict(gridcolor="#1a2d3a", range=[0,ymax_o]))
            st.plotly_chart(fig_vel_o, use_container_width=True, key="oper_vel")

            col_t_o, col_a_o = st.columns(2)
            for fig_col, c1_, c2_, titulo, unidade, la, lal in [
                (col_t_o,"m1_temp","m2_temp","Temperatura","°C",temp_alerta,temp_alarme),
                (col_a_o,"m1_acel","m2_acel","Aceleração","g",acel_alerta,acel_alarme),
            ]:
                fig_s = go.Figure()
                for cv, nome, cor in [(c1_,"Motor 1","#3498db"),(c2_,"Motor 2","#e74c3c")]:
                    if "Motor" in motor_sel and nome not in motor_sel: continue
                    fig_s.add_trace(go.Scattergl(x=df_plot.timestamp, y=df_plot[cv],
                        mode="lines", name=nome, line=dict(color=cor,width=1.3)))
                fig_s.add_hline(y=la, line_dash="dot", line_color="#f39c12", line_width=1)
                fig_s.add_hline(y=lal, line_dash="dot", line_color="#e74c3c", line_width=1)
                fig_s.update_layout(height=220, title=f"{titulo} ({unidade})", **PLOT_O)
                with fig_col: st.plotly_chart(fig_s, use_container_width=True, key=f"oper_{titulo}")

        with sub2:
            cg1, cg2 = st.columns(2)
            def _gauge_o(val, title, maximo, la, lal, unit):
                fv = _flag_o(val, la, lal)
                fig = go.Figure(go.Indicator(mode="gauge+number", value=val,
                    title=dict(text=title,font=dict(size=12,color="#6b8cae")),
                    number=dict(suffix=f" {unit}",font=dict(size=18,color="#e8f0fe")),
                    gauge=dict(axis=dict(range=[0,maximo]),bar=dict(color=COR_O[fv],thickness=0.25),
                               bgcolor="#0a0f1a",borderwidth=1,bordercolor="#1e3a5c",
                               steps=[dict(range=[0,la],color="#0d1f0d"),
                                      dict(range=[la,lal],color="#1f1400"),
                                      dict(range=[lal,maximo],color="#1f0505")],
                               threshold=dict(line=dict(color="#e74c3c",width=3),thickness=0.8,value=lal))))
                fig.update_layout(height=180,paper_bgcolor="rgba(0,0,0,0)",margin=dict(l=20,r=20,t=30,b=10))
                return fig
            vmax_g = max(vel_alarme*1.5, df_f.m1_vel.max()*1.1, df_f.m2_vel.max()*1.1)
            with cg1:
                st.markdown("#### ⚙️ Motor 1")
                ga,gb,gc = st.columns(3)
                ga.plotly_chart(_gauge_o(v1,"Velocidade",vmax_g,vel_alerta,vel_alarme,"mm/s"), use_container_width=True, key="oper_g1v")
                gb.plotly_chart(_gauge_o(a1,"Aceleração",1.0,acel_alerta,acel_alarme,"g"), use_container_width=True, key="oper_g1a")
                gc.plotly_chart(_gauge_o(t1_,"Temperatura",85,temp_alerta,temp_alarme,"°C"), use_container_width=True, key="oper_g1t")
            with cg2:
                st.markdown("#### ⚙️ Motor 2")
                ga,gb,gc = st.columns(3)
                ga.plotly_chart(_gauge_o(v2,"Velocidade",vmax_g,vel_alerta,vel_alarme,"mm/s"), use_container_width=True, key="oper_g2v")
                gb.plotly_chart(_gauge_o(a2,"Aceleração",1.0,acel_alerta,acel_alarme,"g"), use_container_width=True, key="oper_g2a")
                gc.plotly_chart(_gauge_o(t2_,"Temperatura",85,temp_alerta,temp_alarme,"°C"), use_container_width=True, key="oper_g2t")

            st.divider()
            st.markdown("#### Tendência Preditiva — próximos 30s")
            fig_trend = go.Figure()
            for col_v, nome, cor in [("m1_vel","Motor 1","#3498db"),("m2_vel","Motor 2","#e74c3c")]:
                if "Motor" in motor_sel and nome not in motor_sel: continue
                y = df_plot[col_v].values; x = np.arange(len(y))
                coef = np.polyfit(x, y, 1)
                ts_fut = pd.date_range(df_f.timestamp.iloc[-1], periods=31, freq="1s")[1:]
                y_fut = np.polyval(coef, np.arange(len(y), len(y)+30))
                fig_trend.add_trace(go.Scattergl(x=df_plot.timestamp,y=y,mode="lines",name=nome,line=dict(color=cor,width=1.5)))
                fig_trend.add_trace(go.Scattergl(x=ts_fut,y=y_fut,mode="lines",name=f"{nome} (tendência)",line=dict(color=cor,width=2,dash="dash")))
            fig_trend.add_hline(y=vel_alerta, line_dash="dot", line_color="#f39c12", line_width=1)
            fig_trend.add_hline(y=vel_alarme, line_dash="dot", line_color="#e74c3c", line_width=1)
            fig_trend.update_layout(height=260, **PLOT_O)
            st.plotly_chart(fig_trend, use_container_width=True, key="oper_trend")

        with sub3:
            cb1, cb2 = st.columns([3,2])
            with cb1:
                fig_box = make_subplots(1,3,subplot_titles=("Velocidade","Aceleração","Temperatura"))
                for i,(c1__,c2__) in enumerate([("m1_vel","m2_vel"),("m1_acel","m2_acel"),("m1_temp","m2_temp")],1):
                    fig_box.add_trace(go.Box(y=df_f[c1__],name="M1",marker_color="#3498db",boxmean=True,showlegend=(i==1)),1,i)
                    fig_box.add_trace(go.Box(y=df_f[c2__],name="M2",marker_color="#e74c3c",boxmean=True,showlegend=(i==1)),1,i)
                fig_box.update_layout(height=300,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
                                      font_color="#cdd9e5",margin=dict(l=40,r=10,t=40,b=30),
                                      legend=dict(orientation="h",y=1.1,bgcolor="rgba(0,0,0,0)"))
                fig_box.update_xaxes(gridcolor="#1a2d3a"); fig_box.update_yaxes(gridcolor="#1a2d3a")
                st.plotly_chart(fig_box, use_container_width=True, key="oper_box")
            with cb2:
                cols_corr = ["m1_vel","m1_acel","m1_temp","m2_vel","m2_acel","m2_temp"]
                labels_c  = ["M1 Vel","M1 Acel","M1 Temp","M2 Vel","M2 Acel","M2 Temp"]
                corr = df_f[cols_corr].corr().round(2)
                fig_heat = go.Figure(go.Heatmap(z=corr.values,x=labels_c,y=labels_c,
                    colorscale="RdBu",zmid=0,zmin=-1,zmax=1,
                    text=corr.values.round(2),texttemplate="%{text}",textfont=dict(size=9),
                    colorbar=dict(tickfont=dict(color="#aaa"),thickness=12)))
                fig_heat.update_layout(height=300,paper_bgcolor="rgba(0,0,0,0)",
                                       margin=dict(l=10,r=10,t=20,b=10),font_color="#cdd9e5")
                st.plotly_chart(fig_heat, use_container_width=True, key="oper_heat")

        with sub4:
            eventos = []
            for prefix, nome in [("m1","Motor 1"),("m2","Motor 2")]:
                for var, la, lal, unit in [("vel",vel_alerta,vel_alarme,"mm/s"),
                                            ("acel",acel_alerta,acel_alarme,"g"),
                                            ("temp",temp_alerta,temp_alarme,"°C")]:
                    col_f, col_v = f"{prefix}_{var}_flag", f"{prefix}_{var}"
                    for fval, tipo in [(2,"🚨 ALARME"),(1,"⚠️ Alerta")]:
                        pts = df_f[df_f[col_f]==fval]
                        if not pts.empty:
                            eventos.append({"Motor":nome,"Variável":var.capitalize(),"Tipo":tipo,
                                "Primeiro":pts.timestamp.min().strftime("%H:%M:%S"),
                                "Último":pts.timestamp.max().strftime("%H:%M:%S"),
                                "Pico":f"{pts[col_v].max():.3f} {unit}",
                                "Duração (s)":round((pts.timestamp.max()-pts.timestamp.min()).total_seconds(),1),
                                "Ocorrências":len(pts)})
            if eventos:
                st.dataframe(pd.DataFrame(eventos).sort_values(["Tipo","Motor"]), use_container_width=True, hide_index=True)
            else:
                st.success("✅ Nenhum evento no período.")

        with sub5:
            stats_cols = {"M1 Vel (mm/s)":"m1_vel","M1 Acel (g)":"m1_acel","M1 Temp (°C)":"m1_temp",
                          "M2 Vel (mm/s)":"m2_vel","M2 Acel (g)":"m2_acel","M2 Temp (°C)":"m2_temp"}
            stats = {label:{"Mín":df_f[col].min(),"Média":df_f[col].mean(),"Máx":df_f[col].max(),
                             "Desvio":df_f[col].std(),"P95":df_f[col].quantile(0.95)}
                     for label,col in stats_cols.items()}
            st.dataframe(pd.DataFrame(stats).T.round(4), use_container_width=True)
            st.download_button("⬇️ Exportar CSV", df_f.to_csv(index=False).encode("utf-8"),
                               "forzy_export.csv","text/csv", use_container_width=True)


# ═════════════════════════════════════════════════════════════════════════════
# TAB 4 — HISTÓRICO / PLAYER
# ═════════════════════════════════════════════════════════════════════════════
with tab_hist:
    st.subheader("▶ Player — Timelapse Operacional")

    SEARCH_PATHS_H = [
        Path(__file__).parent.parent / "data" / "forzy.csv",
        Path.home() / "Downloads" / "History_32026-05-19T11-46-10-920.csv",
    ]
    csv_path_h = next((p for p in SEARCH_PATHS_H if p.exists()), None)
    if not csv_path_h:
        st.error("CSV não encontrado.")
    else:
        @st.cache_data
        def _load_hist(path):
            df = pd.read_csv(path, sep=";", skiprows=3, header=None,
                usecols=[0,3,4,5,6,7,8],
                names=["timestamp","m1_vel","m1_acel","m1_temp","m2_vel","m2_acel","m2_temp"])
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            for c in df.columns[1:]:
                df[c] = pd.to_numeric(df[c], errors="coerce")
            df = df.dropna().sort_values("timestamp").reset_index(drop=True)
            df = (df.set_index("timestamp").groupby(level=0).mean()
                    .resample("200ms").mean().interpolate("linear").reset_index())
            rng = np.random.default_rng(42)
            t   = np.arange(len(df)) * 0.2
            for prefix in ["m1","m2"]:
                v = df[f"{prefix}_vel"].values; a = df[f"{prefix}_acel"].values
                df[f"{prefix}_vel"]  = np.clip(v + v*0.12*np.sin(2*np.pi*0.8*t) + v*0.06*np.sin(2*np.pi*1.7*t+0.8) + rng.normal(0, np.clip(v*0.04,0.003,0.15)), 0, None)
                df[f"{prefix}_acel"] = np.clip(a + a*0.15*np.sin(2*np.pi*1.1*t+0.4) + a*0.07*np.sin(2*np.pi*2.3*t+1.1) + rng.normal(0, np.clip(a*0.05,0.001,0.05)), 0, None)
            return df

        df_raw_h = _load_hist(str(csv_path_h))

        VARIAVEIS_H = {
            "🚀 Velocidade": dict(col_m1="m1_vel",col_m2="m2_vel",unidade="mm/s",ylabel="Velocidade (mm/s)",lim_alerta=1.8,lim_alarme=4.5,fmt=".3f"),
            "⚡ Aceleração": dict(col_m1="m1_acel",col_m2="m2_acel",unidade="g",ylabel="Aceleração (g)",lim_alerta=0.25,lim_alarme=0.45,fmt=".3f"),
            "🌡️ Temperatura": dict(col_m1="m1_temp",col_m2="m2_temp",unidade="°C",ylabel="Temperatura (°C)",lim_alerta=35.0,lim_alarme=42.0,fmt=".1f"),
        }

        hc1, hc2, hc3 = st.columns(3)
        with hc1: variavel_sel = st.radio("Variável", list(VARIAVEIS_H.keys()), horizontal=True, key="hist_var")
        with hc2: frame_interval = st.select_slider("Intervalo/frame", ["5s","10s","15s","30s","1min","2min","5min"], value="30s", key="hist_fi")
        with hc3: speed_ms = st.select_slider("Velocidade", [50,100,150,200,300,500,800], value=150,
                                               format_func=lambda x:f"{x} ms/frame", key="hist_spd")
        motores_h = st.multiselect("Motores", ["Motor 1","Motor 2"], default=["Motor 1","Motor 2"], key="hist_mot")

        cfg_h = VARIAVEIS_H[variavel_sel]
        transition_ms = min(speed_ms-30, 80) if speed_ms > 80 else 0

        df_h = (df_raw_h.set_index("timestamp").resample(frame_interval).mean()
                        .dropna(how="all").reset_index())
        if len(df_h) > 300:
            df_h = df_h.iloc[::len(df_h)//300].reset_index(drop=True)

        N_h = len(df_h)
        COL_M1_H = cfg_h["col_m1"]; COL_M2_H = cfg_h["col_m2"]
        Y_MAX_H  = max(df_h[COL_M1_H].max(), df_h[COL_M2_H].max()) * 1.15
        la_h, lal_h = cfg_h["lim_alerta"], cfg_h["lim_alarme"]

        def _ponto_cor_h(v):
            return "#e74c3c" if v>=lal_h else ("#f39c12" if v>=la_h else "#2ecc71")

        frames_h, steps_h = [], []
        for i in range(1, N_h+1):
            sub = df_h.iloc[:i]; last = sub.iloc[-1]
            traces = []
            for col, nome, cor in [(COL_M1_H,"Motor 1","#3498db"),(COL_M2_H,"Motor 2","#e74c3c")]:
                if nome not in motores_h: continue
                traces.append(go.Scatter(x=sub["timestamp"],y=sub[col],mode="lines",line=dict(color=cor,width=2),name=nome))
                traces.append(go.Scatter(x=[last["timestamp"]],y=[last[col]],mode="markers",
                    marker=dict(color=_ponto_cor_h(last[col]),size=12,line=dict(color="white",width=2)),showlegend=False))
            frames_h.append(go.Frame(data=traces,name=str(i)))
            steps_h.append(dict(args=[[str(i)],{"frame":{"duration":speed_ms,"redraw":True},"mode":"immediate","transition":{"duration":transition_ms}}],
                                label=last["timestamp"].strftime("%H:%M:%S"),method="animate"))

        first_h = df_h.iloc[:1]; last0_h = df_h.iloc[0]
        init_traces_h = []
        for col, nome, cor in [(COL_M1_H,"Motor 1","#3498db"),(COL_M2_H,"Motor 2","#e74c3c")]:
            if nome not in motores_h: continue
            init_traces_h += [
                go.Scatter(x=first_h["timestamp"],y=first_h[col],mode="lines",line=dict(color=cor,width=2),name=nome),
                go.Scatter(x=[last0_h["timestamp"]],y=[last0_h[col]],mode="markers",
                           marker=dict(color=_ponto_cor_h(last0_h[col]),size=12,line=dict(color="white",width=2)),showlegend=False),
            ]

        layout_h = go.Layout(
            height=480, hovermode="x unified",
            xaxis=dict(title="Tempo",range=[df_h["timestamp"].min(),df_h["timestamp"].max()],type="date"),
            yaxis=dict(title=cfg_h["ylabel"],range=[0,Y_MAX_H]),
            legend=dict(orientation="h",yanchor="bottom",y=1.02),
            margin=dict(l=60,r=20,t=70,b=130),
            shapes=[
                dict(type="rect",xref="paper",x0=0,x1=1,yref="y",y0=0,y1=la_h,fillcolor="#2ecc71",opacity=0.07,line_width=0),
                dict(type="rect",xref="paper",x0=0,x1=1,yref="y",y0=la_h,y1=lal_h,fillcolor="#f39c12",opacity=0.07,line_width=0),
                dict(type="rect",xref="paper",x0=0,x1=1,yref="y",y0=lal_h,y1=Y_MAX_H,fillcolor="#e74c3c",opacity=0.07,line_width=0),
            ],
            updatemenus=[dict(type="buttons",showactive=False,y=1.20,x=0.5,xanchor="center",
                buttons=[
                    dict(label="▶  Play",method="animate",args=[None,{"frame":{"duration":speed_ms,"redraw":True},"fromcurrent":True,"transition":{"duration":transition_ms}}]),
                    dict(label="⏸  Pause",method="animate",args=[[None],{"frame":{"duration":0,"redraw":False},"mode":"immediate"}]),
                    dict(label="⏮  Reset",method="animate",args=[["1"],{"frame":{"duration":0,"redraw":True},"mode":"immediate"}]),
                ], font=dict(size=14),bgcolor="#1e1e2e",bordercolor="#555")],
            sliders=[dict(active=0,currentvalue=dict(prefix="⏱ ",visible=True,xanchor="center",font=dict(size=13)),
                          pad=dict(t=50,b=10),len=1.0,x=0,steps=steps_h)],
        )

        st.plotly_chart(go.Figure(data=init_traces_h,layout=layout_h,frames=frames_h),
                        use_container_width=True, key="hist_player")

        st.divider()
        st.caption(f"📊 Estatísticas — {variavel_sel}")
        hk1,hk2,hk3,hk4,hk5,hk6 = st.columns(6)
        hk1.metric("M1 Máx",   f"{df_h[COL_M1_H].max():{cfg_h['fmt']}} {cfg_h['unidade']}")
        hk2.metric("M1 Média", f"{df_h[COL_M1_H].mean():{cfg_h['fmt']}} {cfg_h['unidade']}")
        hk3.metric("M1 Desvio",f"{df_h[COL_M1_H].std():{cfg_h['fmt']}} {cfg_h['unidade']}")
        hk4.metric("M2 Máx",   f"{df_h[COL_M2_H].max():{cfg_h['fmt']}} {cfg_h['unidade']}")
        hk5.metric("M2 Média", f"{df_h[COL_M2_H].mean():{cfg_h['fmt']}} {cfg_h['unidade']}")
        hk6.metric("M2 Desvio",f"{df_h[COL_M2_H].std():{cfg_h['fmt']}} {cfg_h['unidade']}")
