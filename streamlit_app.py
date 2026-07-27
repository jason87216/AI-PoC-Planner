"""Streamlit entry point for the AI PoC Planner product UI."""

import streamlit as st

st.set_page_config(
    page_title="AI PoC Planner", page_icon=":material/insights:", layout="wide"
)
st.session_state.setdefault("selected_project", None)

page = st.navigation(
    [
        st.Page("app_pages/home.py", title="首頁", icon=":material/home:"),
        st.Page("app_pages/new_project.py", title="新建專案", icon=":material/add:"),
        st.Page("app_pages/history.py", title="專案歷史", icon=":material/history:"),
        st.Page(
            "app_pages/model_settings.py",
            title="模型設定",
            icon=":material/tune:",
        ),
    ],
    position="top",
)
page.run()
