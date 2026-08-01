"""Product home page."""

import streamlit as st

from ai_poc_planner.ui.api_client import ApiClientError
from ai_poc_planner.ui.navigation import open_history, open_new_project
from ai_poc_planner.ui.presentation import (
    connection_label,
    show_api_error,
    status_label,
)
from ai_poc_planner.ui.runtime import (
    load_projects,
    load_provider_status,
    refresh_api_data,
)

st.title("AI PoC Planner")
st.write("把模糊需求整理成可確認的事實、可比較的方案與可追蹤的 PoC 規劃報告。")
st.caption("AI 協助理解與整理；正式推薦、分數與硬性限制由程式規則決定。")
st.caption("開始流程：建立模型設定 → 測試可用性 → 建立專案 → 完成訪談與評估。")

if st.button("建立新專案", icon=":material/add:", type="primary"):
    open_new_project()

if st.button("查看歷史專案", icon=":material/history:"):
    open_history()

if st.button("重新整理", icon=":material/refresh:"):
    refresh_api_data()
    st.rerun()

summary_slot = st.container()
with summary_slot.skeleton():
    try:
        projects = load_projects()
    except ApiClientError as error:
        show_api_error(error)
        projects = []

    try:
        provider_status = load_provider_status()
    except ApiClientError as error:
        provider_status = None
        if error.code != "provider_not_ready":
            show_api_error(error)

    with st.container(horizontal=True):
        st.metric("專案數", len(projects), border=True)
        st.metric(
            "模型連線",
            connection_label(provider_status.get("connection_state"))
            if provider_status
            else "尚未設定",
            border=True,
        )

st.subheader("最近專案")
if not projects:
    st.info("尚未建立專案。請先到「模型設定」建立並測試模型服務，再開始新的需求規劃。")
else:
    recent_rows = [
        {
            "專案": project.get("project_name"),
            "版本": project.get("version_number"),
            "進度": status_label(project.get("status")),
            "模型": project.get("model_name") or "尚未選擇",
        }
        for project in projects[:5]
    ]
    st.dataframe(recent_rows, hide_index=True)
    if st.button("查看歷史專案", icon=":material/history:", key="home_recent_history"):
        open_history()
