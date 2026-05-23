"""CSS global do IMS · Forzy — importar no topo de cada página."""
import streamlit as st


def apply():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family:'Inter',sans-serif !important; }

[data-testid="stAppViewContainer"]  { background:#060d18; }
[data-testid="stSidebar"]           { background:#080f1c; border-right:1px solid #0f2035; }
[data-testid="stHeader"]            { background:#060d18; border-bottom:1px solid #0f2035; }
section[data-testid="stSidebarContent"] { padding-top:0 !important; }

[data-testid="stSidebarNavLink"] {
    color:#4a7a9b !important; font-size:.82rem; font-weight:500;
    border-radius:6px; padding:8px 12px !important; transition:all .15s;
}
[data-testid="stSidebarNavLink"]:hover { background:#0f2035 !important; color:#7ec8e3 !important; }
[data-testid="stSidebarNavLink"][aria-current="page"] {
    background:#0d2040 !important; color:#7ec8e3 !important;
    border-left:3px solid #3498db;
}

[data-testid="metric-container"] {
    background:#0a1628; border:1px solid #0f2a45;
    border-radius:8px; padding:14px 16px 10px;
}
[data-testid="stMetricLabel"] { color:#4a7a9b !important; font-size:.72rem; text-transform:uppercase; letter-spacing:.07em; }
[data-testid="stMetricValue"] { color:#e2eaf4 !important; font-size:1.4rem; font-weight:700; }
[data-testid="stMetricDelta"] svg { display:none; }

[data-testid="stTabs"] [role="tablist"] { border-bottom:1px solid #0f2035; gap:2px; }
[data-testid="stTabs"] button[role="tab"] {
    color:#4a7a9b; font-size:.8rem; font-weight:600;
    letter-spacing:.05em; padding:8px 20px; border-radius:4px 4px 0 0;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color:#7ec8e3 !important; background:#0a1628 !important;
    border-bottom:2px solid #3498db;
}

hr { border-color:#0f2035 !important; margin:10px 0 !important; }

[data-testid="stExpander"] {
    border:1px solid #0f2035 !important; border-radius:8px !important;
    background:#08111f !important;
}

[data-testid="stButton"] > button {
    background:#0d2040; border:1px solid #1e3d60;
    color:#7ec8e3; border-radius:6px; font-size:.8rem; font-weight:600;
}
[data-testid="stButton"] > button:hover {
    background:#1e3d60; border-color:#3498db; color:#fff;
}
[data-testid="stDownloadButton"] > button {
    background:#0d2040; border:1px solid #1e3d60;
    color:#7ec8e3; border-radius:6px; font-size:.8rem; font-weight:600;
}

::-webkit-scrollbar { width:4px; }
::-webkit-scrollbar-track { background:#060d18; }
::-webkit-scrollbar-thumb { background:#1e3d60; border-radius:4px; }
</style>
""", unsafe_allow_html=True)


def sidebar_header():
    """Cabeçalho padrão da sidebar em todas as páginas."""
    import streamlit as st
    with st.sidebar:
        st.markdown("""
        <div style="padding:20px 16px 16px;border-bottom:1px solid #0f2035;margin-bottom:8px">
          <div style="font-size:1.05rem;font-weight:700;color:#e2eaf4;letter-spacing:.04em">
            🏭 IMS · Forzy
          </div>
          <div style="font-size:.7rem;color:#2a5a7a;margin-top:3px;letter-spacing:.06em;text-transform:uppercase">
            Industrial Monitoring System
          </div>
        </div>
        """, unsafe_allow_html=True)
