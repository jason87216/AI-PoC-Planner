"""Independent new-project route using only the public FastAPI boundary."""

from __future__ import annotations

import streamlit as st

from ai_poc_planner.ui.api_client import ApiClientError
from ai_poc_planner.ui.presentation import profile_label, show_api_error
from ai_poc_planner.ui.runtime import get_api_client, load_profiles, refresh_api_data


def _profile_choice(profile: dict[str, object]) -> str:
    enabled = "可使用" if profile.get("is_enabled") else "已停用"
    return f"{profile_label(profile)}｜{enabled}"


st.title("新建專案")
st.caption("選擇並測試本專案使用的模型，再建立可持續追蹤的規劃。")
prefill = st.session_state.pop("new_project_prefill", None)
if isinstance(prefill, dict):
    for key, value in prefill.items():
        st.session_state.setdefault(key, value)
try:
    profiles = load_profiles()
except ApiClientError as error:
    show_api_error(error)
    profiles = []

if not profiles:
    st.warning("尚未建立可用模型設定。請先建立並測試模型。")
    if st.button("前往模型設定", icon=":material/tune:"):
        st.switch_page("app_pages/model_settings.py")
    st.stop()

selected = st.selectbox(
    "本專案使用的模型", profiles, format_func=_profile_choice, key="new_project_profile"
)
profile_id = str(selected["id"])
try:
    readiness = get_api_client().profile_status(profile_id)
except ApiClientError as error:
    show_api_error(error)
    readiness = {"formal_analysis_allowed": False}

if readiness.get("formal_analysis_allowed"):
    st.success("此模型已啟用，且本次 runtime 已完成連線測試。")
else:
    st.warning("此模型尚未完成可用性測試；完成測試後才能建立並整理需求。")
    if st.button("測試連線", icon=":material/network_check:"):
        try:
            tested = get_api_client().test_profile(profile_id)
        except ApiClientError as error:
            show_api_error(error)
        else:
            if tested.get("formal_analysis_allowed"):
                refresh_api_data()
                st.rerun()
            else:
                st.error("模型連線未成功，請檢查設定後再試。")

with st.form("new_project_form"):
    project_name = st.text_input("專案名稱", key="new_project_name")
    current = st.text_area("目前流程與問題", key="new_project_current", height=140)
    outcome = st.text_area("希望改善的成果", key="new_project_outcome", height=120)
    data = st.text_area("現有資料與文件", key="new_project_data", height=120)
    owners = st.text_area("使用者與負責人", key="new_project_owners")
    constraints = st.text_area("已知限制", key="new_project_constraints")
    submitted = st.form_submit_button(
        "建立專案並整理需求",
        type="primary",
        disabled=not readiness.get("formal_analysis_allowed"),
    )

if submitted:
    try:
        created = get_api_client().create_discovery_project(
            {
                "project_name": project_name,
                "current_workflow_problem": current,
                "desired_outcome": outcome,
                "available_data": data,
                "users_and_owners": owners or None,
                "known_constraints": constraints or None,
                "model_profile_id": profile_id,
            }
        )
        project, version = created["project"], created["version"]
        st.session_state["selected_project"] = {
            "project_id": str(project["id"]),
            "version_number": int(version["version_number"]),
        }
        try:
            get_api_client().generate_understanding(
                str(project["id"]), int(version["version_number"])
            )
        except ApiClientError:
            st.warning("專案已建立，但需求理解尚未生成。可在工作區重新整理需求。")
        refresh_api_data()
        st.switch_page("app_pages/discovery.py")
    except ApiClientError as error:
        show_api_error(error)
