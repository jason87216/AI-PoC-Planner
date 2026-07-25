"""Durable project history page."""

import streamlit as st

from ai_poc_planner.ui.api_client import ApiClientError
from ai_poc_planner.ui.presentation import show_api_error, status_label
from ai_poc_planner.ui.runtime import load_projects, refresh_api_data

st.title("專案歷史")
st.caption("只顯示可閱讀的專案進度與已選模型，不顯示內部識別資料。")

if st.button("重新整理歷史", icon=":material/refresh:"):
    refresh_api_data()
    st.rerun()

history_slot = st.container()
with history_slot.skeleton():
    try:
        projects = load_projects()
    except ApiClientError as error:
        show_api_error(error)
        projects = []

if not projects:
    st.info("目前沒有可顯示的專案歷史。")
else:
    rows = [
        {
            "專案": project.get("project_name"),
            "版本": project.get("version_number"),
            "狀態": status_label(project.get("status")),
            "模型設定": project.get("profile_name") or "尚未選擇",
            "模型": project.get("model_name") or "—",
            "最近更新": project.get("updated_at"),
        }
        for project in projects
    ]
    st.dataframe(rows, hide_index=True)
