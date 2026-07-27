"""Durable project history page."""

import streamlit as st

from ai_poc_planner.ui.api_client import ApiClientError
from ai_poc_planner.ui.presentation import show_api_error, status_label
from ai_poc_planner.ui.runtime import load_projects, refresh_api_data

st.title("專案歷史")
st.caption("只顯示可閱讀的專案進度與已選模型，不顯示內部識別資料。")


def _selection_label(project: dict[str, object]) -> str:
    return f"{project.get('project_name')} · 第 {project.get('version_number')} 版"


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
    for project in projects:
        with st.container(border=True):
            st.subheader(_selection_label(project))
            st.caption(
                f"{status_label(project.get('status'))}｜最近更新：{project.get('updated_at')}"
            )
            st.write("可回看既有需求與目前工作階段。")
            if st.button(
                "繼續處理" if project.get("status") != "complete" else "查看專案",
                key=f"open_project_{project.get('project_id')}",
                icon=":material/folder_open:",
            ):
                st.session_state["selected_project"] = {
                    "project_id": project.get("project_id"),
                    "version_number": project.get("version_number"),
                }
                st.switch_page("app_pages/discovery.py")
