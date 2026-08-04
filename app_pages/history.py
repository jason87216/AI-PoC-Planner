"""Durable project history page."""

import streamlit as st

from ai_poc_planner.ui.api_client import ApiClientError
from ai_poc_planner.ui.navigation import (
    open_new_project,
    open_results,
    open_workspace,
)
from ai_poc_planner.ui.presentation import show_api_error, status_label
from ai_poc_planner.ui.project_copy import build_project_copy_prefill
from ai_poc_planner.ui.runtime import (
    get_api_client,
    load_current_facts,
    load_projects,
    refresh_api_data,
)

st.title("專案歷史")
st.caption(
    "只顯示可閱讀的專案進度與已選模型，不顯示內部識別資料；重新進入只會讀取已保存進度。"
)


def _selection_label(project: dict[str, object]) -> str:
    return f"{project.get('project_name')} · 第 {project.get('version_number')} 版"


def _primary_action(status: object) -> tuple[str, str]:
    return {
        "assessed": ("繼續生成報告", "results"),
        "proposal_generated": ("查看報告", "results"),
        "complete": ("查看報告", "results"),
    }.get(str(status), ("繼續修改", "workspace"))


def _copy_project(project: dict[str, object]) -> None:
    project_id = str(project.get("project_id"))
    version_number = int(project.get("version_number"))
    try:
        facts = load_current_facts(project_id, version_number)
    except ApiClientError as error:
        show_api_error(error)
        return
    st.session_state["new_project_prefill"] = build_project_copy_prefill(
        str(project.get("project_name") or "未命名專案"), facts
    )
    open_new_project()


def _delete_project(project: dict[str, object]) -> None:
    project_id = str(project.get("project_id"))
    project_name = str(project.get("project_name") or "未命名專案")
    delete_key = f"confirm_delete_{project_id}"
    with st.expander("刪除專案", expanded=False):
        st.warning("刪除後，這個專案將不再顯示於專案歷史，也無法從目前介面重新開啟。")
        confirmed = st.checkbox(f"我確認要刪除「{project_name}」", key=delete_key)
        if st.button(
            "確認刪除專案",
            key=f"delete_project_{project_id}",
            type="secondary",
            disabled=not confirmed,
        ):
            try:
                get_api_client().delete_project(project_id)
            except ApiClientError as error:
                show_api_error(error)
            else:
                selected = st.session_state.get("selected_project")
                if (
                    isinstance(selected, dict)
                    and selected.get("project_id") == project_id
                ):
                    st.session_state.pop("selected_project", None)
                st.session_state.pop(delete_key, None)
                refresh_api_data()
                st.rerun()


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
            status = str(project.get("status"))
            action_label, destination = _primary_action(status)
            if st.button(
                action_label,
                key=f"open_project_{project.get('project_id')}",
                icon=":material/folder_open:",
            ):
                project_id = str(project.get("project_id"))
                version_number = int(project.get("version_number"))
                if destination == "results":
                    open_results(project_id, version_number)
                else:
                    open_workspace(project_id, version_number)
            copy_label = (
                "複製並修改"
                if status in {"complete", "proposal_generated"}
                else "複製為新專案"
            )
            if st.button(
                copy_label,
                key=f"copy_project_{project.get('project_id')}",
                icon=":material/content_copy:",
            ):
                _copy_project(project)
            _delete_project(project)
