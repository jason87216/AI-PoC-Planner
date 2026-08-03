"""Durable project history page."""

import streamlit as st

from ai_poc_planner.ui.api_client import ApiClientError
from ai_poc_planner.ui.navigation import (
    history_destination_for_status,
    open_results,
    open_workspace,
)
from ai_poc_planner.ui.presentation import show_api_error, status_label
from ai_poc_planner.ui.runtime import load_projects, refresh_api_data

st.title("專案歷史")
st.caption(
    "只顯示可閱讀的專案進度與已選模型，不顯示內部識別資料；重新進入只會讀取已保存進度。"
)


def _selection_label(project: dict[str, object]) -> str:
    return f"{project.get('project_name')} · 第 {project.get('version_number')} 版"


def _action_label(status: object) -> str:
    return {
        "draft": "繼續處理",
        "interviewing": "繼續處理",
        "clarification_required": "繼續處理",
        "ready_for_assessment": "繼續評估",
        "assessed": "繼續生成報告",
        "proposal_generated": "查看報告",
        "complete": "查看報告",
        "failed": "查看問題",
    }.get(str(status), "查看專案")


if st.button("重新整理歷史", icon=":material/refresh:"):
    refresh_api_data()
    st.rerun()

history_slot = st.container()
projects: list[dict[str, object]] | None
with history_slot.skeleton():
    try:
        projects = load_projects()
    except ApiClientError as error:
        show_api_error(error)
        projects = None

if projects is None:
    st.stop()
if not projects:
    st.info("目前沒有可顯示的專案歷史。建立第一個專案後，這裡會保留版本與進度。")
else:
    for project in projects:
        with st.container(border=True):
            st.subheader(_selection_label(project))
            st.caption(
                f"{status_label(project.get('status'))}｜最近更新：{project.get('updated_at')}"
            )
            st.write("可回看需求、訪談與評估進度；查看結果不會重新呼叫模型服務。")
            if st.button(
                _action_label(project.get("status")),
                key=f"open_project_{project.get('project_id')}",
                icon=":material/folder_open:",
            ):
                project_id = str(project.get("project_id"))
                version_number = int(project.get("version_number"))
                if history_destination_for_status(project.get("status")) == "results":
                    open_results(project_id, version_number)
                else:
                    open_workspace(project_id, version_number)
