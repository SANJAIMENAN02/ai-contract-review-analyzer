"""
Page registry. Pages are plain functions, so navigation (including
programmatic st.switch_page from buttons) never relies on the legacy pages/ folder.
Imports are lazy to avoid circular imports between pages and this module.
"""
from __future__ import annotations

import streamlit as st


def _home():
    from streamlit_app.views import home
    home.render()


def _analyze():
    from streamlit_app.views import analyze
    analyze.render()


def _dashboard():
    from streamlit_app.views import dashboard
    dashboard.render()


def _history():
    from streamlit_app.views import history
    history.render()


def _about():
    from streamlit_app.views import about
    about.render()


PAGES = {
    "home": st.Page(_home, title="Home", icon="🏠", default=True),
    "analyze": st.Page(_analyze, title="Analyze Contract", icon="📄", url_path="analyze"),
    "dashboard": st.Page(_dashboard, title="Dashboard", icon="📊", url_path="dashboard"),
    "history": st.Page(_history, title="History", icon="🕘", url_path="history"),
    "about": st.Page(_about, title="About", icon="ℹ️", url_path="about"),
}


def go(name: str) -> None:
    st.switch_page(PAGES[name])
