"""
Streamlit entry point:  streamlit run streamlit_app/app.py

Talks to the FastAPI backend over HTTP only (see api_client.py).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # make `streamlit_app` importable

import streamlit as st  # noqa: E402

from streamlit_app import api_client, config  # noqa: E402
from streamlit_app.nav import PAGES  # noqa: E402
from streamlit_app.theme import inject_css, render_html  # noqa: E402

st.set_page_config(page_title=config.APP_NAME, page_icon="⚖️", layout="wide", initial_sidebar_state="expanded")
inject_css()

# Session state used across pages
for key in ("current_contract_id", "current_analysis", "current_filename"):
    st.session_state.setdefault(key, None)
st.session_state.setdefault("report_cache", {})


@st.cache_data(ttl=5, show_spinner=False)
def _backend_online() -> bool:
    return api_client.check_health()


with st.sidebar:
    render_html(f'<div class="side-title">{config.APP_NAME}</div><div class="side-sub">Automated contract review</div>')
    for name in ("home", "analyze", "dashboard", "history", "about"):
        st.page_link(PAGES[name])
    st.write("")
    if _backend_online():
        render_html('<div class="api-status"><b>API Status</b><br><span class="dot-ok">●</span> Connected</div>')
    else:
        render_html('<div class="api-status"><b>API Status</b><br><span class="dot-bad">●</span> Backend Offline</div>')
        st.caption(f"Expected at {config.API_BASE_URL}")

st.navigation(list(PAGES.values()), position="hidden").run()
