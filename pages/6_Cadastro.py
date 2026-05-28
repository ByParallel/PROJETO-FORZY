import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import pandas as pd
import sqlite3
import database as db
from database import DB_PATH as _DB_PATH
from utils.theme import apply as _apply_theme, sidebar_nav as _snav

def _connect_db():
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

st.set_page_config(page_title="Cadastro — IMS Forzy", layout="wide")
_apply_theme()
_snav("cadastro")

# ── CSS específico do cadastro ─────────────────────────────────────────────────
st.markdown("""
<style>
/* Título do formulário */
.form-title {
    font-size: 1.4rem; font-weight: 700; color: #e2eaf4;
    margin-bottom: 24px; padding-bottom: 12px;
    border-bottom: 1px solid #0f2035;
}
/* Labels customizados */
.field-label {
    font-size: .72rem; font-weight: 600; color: #4a7a9b;
    text-transform: uppercase; letter-spacing: .08em;
    margin-bottom: 4px;
}
/* Botão Cadastrar — coral/vermelho */
div[data-testid="stForm"] div[data-testid="stButton"]:last-child > button,
.btn-cadastrar button {
    background: #c0392b !important;
    border: none !important;
    color: #fff !important;
    font-size: .88rem !important;
    font-weight: 700 !important;
    padding: 10px 0 !important;
    border-radius: 6px !important;
    letter-spacing: .04em !important;
    transition: background .15s !important;
}
div[data-testid="stForm"] div[data-testid="stButton"]:last-child > button:hover,
.btn-cadastrar button:hover {
    background: #e74c3c !important;
}
/* Botão Salvar Alterações — azul */
.btn-salvar button {
    background: #1e5fa8 !important;
    border: none !important;
    color: #fff !important;
    font-size: .88rem !important;
    font-weight: 700 !important;
    border-radius: 6px !important;
}
.btn-salvar button:hover { background: #2980b9 !important; }

/* Remove borda padrão do st.form */
div[data-testid="stForm"] {
    border: none !important;
    padding: 0 !important;
}
/* Inputs mais escuros */
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input {
    background: #0a1628 !important;
    border: 1px solid #0f2a45 !important;
    color: #e2eaf4 !important;
    border-radius: 6px !important;
}
div[data-testid="stSelectbox"] > div > div {
    background: #0a1628 !important;
    border: 1px solid #0f2a45 !important;
    border-radius: 6px !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div style="padding:10px 0 18px">
  <div style="font-size:1.3rem;font-weight:700;color:#e2eaf4">Cadastro de Ativos</div>
  <div style="font-size:.78rem;color:#4a7a9b;margin-top:2px">Lista · Novo · Editar</div>
</div>
""", unsafe_allow_html=True)

tab_lista, tab_novo, tab_editar = st.tabs(["Lista de Ativos", "Novo Ativo", "Editar Ativo"])

plantas = db.get_plantas()
areas   = db.get_areas()

def _area_options(planta_id=None):
    if planta_id:
        return [(a["id"], a["nome"]) for a in areas if a["planta_id"] == planta_id]
    return [(a["id"], a["nome"]) for a in areas]

STATUS_OPTS = ["ativo", "manutencao", "inativo"]
IP_OPTS     = ["IP44", "IP54", "IP55", "IP65", "IP66", "IP67"]

# ── Tab Lista ─────────────────────────────────────────────────────────────────
with tab_lista:
    col_f1, col_f2, col_f3 = st.columns(3)
    planta_f = col_f1.selectbox("Planta",  ["Todas"] + [p["nome"] for p in plantas], key="lst_planta")
    status_f = col_f2.selectbox("Status",  ["Todos"] + STATUS_OPTS,                  key="lst_status")
    busca    = col_f3.text_input("Busca",  key="lst_busca", placeholder="Codigo ou descrição")

    pid      = next((p["id"] for p in plantas if p["nome"] == planta_f), None) if planta_f != "Todas" else None
    area_ids = [a["id"] for a in areas if a["planta_id"] == pid] if pid else None

    todos = db.get_ativos_industrial()
    if area_ids is not None:
        todos = [a for a in todos if a["area_id"] in area_ids]
    if status_f != "Todos":
        todos = [a for a in todos if a["status"] == status_f]
    if busca:
        bl = busca.lower()
        todos = [a for a in todos if bl in (a["codigo"] or "").lower() or bl in (a["descricao"] or "").lower()]

    if todos:
        STATUS_COR = {"ativo": "#27ae60", "manutencao": "#f39c12", "inativo": "#e74c3c"}
        df = pd.DataFrame(todos)[["codigo","tag","descricao","fabricante",
                                   "potencia_kw","tensao_v","corrente_nom","ip_rating",
                                   "status","area_nome","planta_nome","localizacao_descricao"]]
        df.columns = ["Codigo","TAG","Descrição","Fabricante","kW","V","A nom","IP",
                      "Status","Área","Planta","Localização"]
        st.dataframe(
            df.style.map(lambda v: f"color:{STATUS_COR.get(v,'#e2eaf4')};font-weight:600",
                         subset=["Status"]),
            use_container_width=True, hide_index=True
        )
        csv = df.to_csv(index=False, sep=";").encode("utf-8")
        st.download_button("Exportar CSV", csv, "ativos.csv", "text/csv")
    else:
        st.info("Nenhum ativo encontrado.")

# ── Tab Novo ──────────────────────────────────────────────────────────────────
with tab_novo:
    # Sem planta → criar planta primeiro
    if not plantas:
        st.warning("Nenhuma planta cadastrada. Crie uma planta antes de adicionar ativos.")
        with st.form("form_planta"):
            st.markdown('<div class="form-title">Criar Planta</div>', unsafe_allow_html=True)
            nome_p = st.text_input("Nome da Planta *", placeholder="Planta São Paulo")
            desc_p = st.text_input("Descrição",        placeholder="Unidade principal")
            if st.form_submit_button("Criar Planta", use_container_width=True):
                if nome_p.strip():
                    with _connect_db() as conn:
                        conn.execute("INSERT INTO plantas (nome, descricao) VALUES (?,?)",
                                     (nome_p.strip(), desc_p))
                    st.success(f"Planta '{nome_p}' criada.")
                    st.rerun()
                else:
                    st.error("Nome obrigatório.")
        st.stop()

    # ── Formulário principal ───────────────────────────────────────────────────
    st.markdown('<div class="form-title">Cadastrar Novo Ativo</div>', unsafe_allow_html=True)

    with st.form("form_novo", clear_on_submit=False):

        # Planta e Área
        c_pl, c_ar = st.columns(2)
        planta_n = c_pl.selectbox("Planta", [p["nome"] for p in plantas], key="n_planta")
        pid_n    = next((p["id"] for p in plantas if p["nome"] == planta_n), None)
        area_opts = _area_options(pid_n) if pid_n else []
        area_n   = c_ar.selectbox("Área",   [x[1] for x in area_opts] or ["— sem área —"], key="n_area")
        area_id_n = next((x[0] for x in area_opts if x[1] == area_n), None)

        # Código e TAG
        c_cod, c_tag = st.columns(2)
        codigo = c_cod.text_input("Código *", placeholder="MTR-001")
        tag    = c_tag.text_input("TAG",       placeholder="MTR-001")

        # Descrição
        descricao = st.text_input("Descrição *", placeholder="Motor Bomba Secundária")

        # Fabricante e IP
        c_fab, c_ip = st.columns(2)
        fabricante = c_fab.text_input("Fabricante", placeholder="WEG")
        ip_rating  = c_ip.selectbox("IP Rating",   IP_OPTS, index=1)

        # Status
        status = st.selectbox("Status", STATUS_OPTS)

        # Specs elétricas
        c_kw, c_v, c_a = st.columns(3)
        potencia = c_kw.number_input("Potência (kW)",     min_value=0.0, value=0.0,   step=0.5)
        tensao   = c_v.number_input("Tensão (V)",         min_value=0.0, value=380.0, step=10.0)
        corrente = c_a.number_input("Corrente Nominal (A)", min_value=0.0, value=0.0, step=1.0)

        # Localização e data
        loc_desc  = st.text_input("Localização", placeholder="Bloco 1 - Sala de Máquinas")
        data_inst = st.date_input("Data de Instalação")

        # Coordenadas (colapsável)
        with st.expander("Coordenadas GPS (opcional)"):
            c_lat, c_lon = st.columns(2)
            lat = c_lat.number_input("Latitude",  value=-23.5505, format="%.6f")
            lon = c_lon.number_input("Longitude", value=-46.6333, format="%.6f")

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        submitted = st.form_submit_button("Cadastrar Ativo", use_container_width=True)

    if submitted:
        if not codigo.strip():
            st.error("Código é obrigatório.")
        elif not descricao.strip():
            st.error("Descrição é obrigatória.")
        elif not area_id_n:
            st.error("Selecione uma área válida.")
        else:
            try:
                db.criar_ativo_industrial({
                    "codigo": codigo.strip(), "tag": tag.strip() or codigo.strip(),
                    "area_id": area_id_n, "descricao": descricao.strip(),
                    "fabricante": fabricante, "potencia_kw": potencia,
                    "tensao_v": tensao, "corrente_nom": corrente,
                    "ip_rating": ip_rating, "status": status,
                    "latitude": lat, "longitude": lon,
                    "localizacao_descricao": loc_desc,
                    "data_install": str(data_inst),
                })
                st.success(f"Ativo **{codigo}** cadastrado com sucesso.")
                st.balloons()
            except Exception as e:
                st.error(f"Erro ao cadastrar: {e}")

# ── Tab Editar ────────────────────────────────────────────────────────────────
with tab_editar:
    todos_edit  = db.get_ativos_industrial()
    codigos_edit = [a["codigo"] for a in todos_edit]

    if not codigos_edit:
        st.info("Nenhum ativo cadastrado ainda.")
    else:
        cod_sel = st.selectbox("Selecione o ativo para editar", codigos_edit, key="edit_sel")
        a = db.get_ativo_por_codigo(cod_sel)

        if a:
            st.markdown(f'<div class="form-title">Editar — {a["codigo"]}</div>', unsafe_allow_html=True)

            with st.form("form_editar", clear_on_submit=False):
                pid_e_default = a.get("planta_id")
                c_pl_e, c_ar_e = st.columns(2)
                planta_e = c_pl_e.selectbox("Planta", [p["nome"] for p in plantas],
                    index=next((i for i, p in enumerate(plantas) if p["id"] == pid_e_default), 0),
                    key="e_planta")
                pid_e       = next(p["id"] for p in plantas if p["nome"] == planta_e)
                area_opts_e = _area_options(pid_e)
                area_e      = c_ar_e.selectbox("Área", [x[1] for x in area_opts_e],
                    index=next((i for i, (aid, _) in enumerate(area_opts_e) if aid == a["area_id"]), 0),
                    key="e_area")
                area_id_e = next((x[0] for x in area_opts_e if x[1] == area_e), None)

                c_cod_e, c_tag_e = st.columns(2)
                c_cod_e.text_input("Código", value=a["codigo"], disabled=True)
                tag_e = c_tag_e.text_input("TAG", value=a["tag"] or "")

                descricao_e = st.text_input("Descrição", value=a["descricao"] or "")

                c_fab_e, c_ip_e = st.columns(2)
                fabricante_e = c_fab_e.text_input("Fabricante", value=a["fabricante"] or "")
                ip_e         = c_ip_e.selectbox("IP Rating", IP_OPTS,
                    index=IP_OPTS.index(a["ip_rating"]) if a["ip_rating"] in IP_OPTS else 1)

                status_e = st.selectbox("Status", STATUS_OPTS,
                    index=STATUS_OPTS.index(a["status"]) if a["status"] in STATUS_OPTS else 0)

                c_kw_e, c_v_e, c_a_e = st.columns(3)
                potencia_e = c_kw_e.number_input("Potência (kW)", value=float(a["potencia_kw"] or 0), step=0.5)
                tensao_e   = c_v_e.number_input("Tensão (V)",     value=float(a["tensao_v"] or 0),    step=10.0)
                corrente_e = c_a_e.number_input("Corrente Nom (A)", value=float(a["corrente_nom"] or 0), step=1.0)

                loc_e = st.text_input("Localização", value=a["localizacao_descricao"] or "")

                with st.expander("Coordenadas GPS"):
                    c_lat_e, c_lon_e = st.columns(2)
                    lat_e = c_lat_e.number_input("Latitude",  value=float(a["latitude"] or -23.5505), format="%.6f")
                    lon_e = c_lon_e.number_input("Longitude", value=float(a["longitude"] or -46.6333), format="%.6f")

                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                salvar = st.form_submit_button("Salvar Alterações", use_container_width=True)

            if salvar:
                try:
                    db.editar_ativo_industrial(cod_sel, {
                        "tag": tag_e, "area_id": area_id_e, "descricao": descricao_e,
                        "fabricante": fabricante_e, "potencia_kw": potencia_e,
                        "tensao_v": tensao_e, "corrente_nom": corrente_e,
                        "ip_rating": ip_e, "status": status_e,
                        "latitude": lat_e, "longitude": lon_e,
                        "localizacao_descricao": loc_e,
                        "data_install": a.get("data_install"),
                    })
                    st.success(f"Ativo {cod_sel} atualizado com sucesso.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro: {e}")
