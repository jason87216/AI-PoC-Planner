"""Product home page."""

import streamlit as st

from ai_poc_planner.ui.api_client import ApiClientError
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
st.write("將需求訪談、可驗證評估與規劃報告整理為可持續追蹤的 PoC。")

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
    st.info("尚未建立專案。請先在模型設定完成可用模型的建立與測試。")
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
