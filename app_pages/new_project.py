"""Independent new-project route using only the public FastAPI boundary."""

from __future__ import annotations

import streamlit as st

from ai_poc_planner.ui.api_client import ApiClientError
from ai_poc_planner.ui.navigation import open_workspace, switch_page
from ai_poc_planner.ui.presentation import profile_label, show_api_error
from ai_poc_planner.ui.runtime import get_api_client, load_profiles, refresh_api_data


def _profile_choice(profile: dict[str, object]) -> str:
    enabled = "可使用" if profile.get("is_enabled") else "已停用"
    return f"{profile_label(profile)}｜{enabled}"


def _optional_text(value: str) -> str | None:
    return value.strip() or None


st.title("新建專案")
st.caption(
    "先選擇並測試本專案使用的模型，再輸入最小需求簡介；模型服務未通過測試時不會建立正式評估。"
)
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
    st.warning("尚未建立可用的模型設定。請先到「模型設定」建立並完成模型可用性測試。")
    if st.button("前往模型設定", icon=":material/tune:"):
        switch_page("app_pages/model_settings.py")
    st.stop()

default_profile_index = next(
    (index for index, profile in enumerate(profiles) if profile.get("is_selected")),
    0,
)
selected = st.selectbox(
    "本專案使用的模型",
    profiles,
    index=default_profile_index,
    format_func=_profile_choice,
    key="new_project_profile",
)
profile_id = str(selected["id"])
try:
    readiness = get_api_client().profile_status(profile_id)
except ApiClientError as error:
    show_api_error(error)
    readiness = {"formal_analysis_allowed": False}

if readiness.get("formal_analysis_allowed"):
    st.success("此模型已啟用，且目前執行環境已完成模型可用性測試。")
else:
    st.warning("尚未完成模型可用性測試；測試成功後才能建立並整理需求。")
    if st.button("測試模型可用性", icon=":material/network_check:"):
        try:
            tested = get_api_client().test_profile(profile_id)
        except ApiClientError as error:
            show_api_error(error)
        else:
            if tested.get("formal_analysis_allowed"):
                refresh_api_data()
                st.rerun()
            else:
                st.error("模型服務尚未連線成功，請檢查端點、模型名稱與能力設定。")

with st.form("new_project_form"):
    project_name = st.text_input(
        "專案名稱", help="用一句話辨識這次要規劃的流程或問題。", key="new_project_name"
    )
    current = st.text_area(
        "目前流程與問題",
        help="描述目前怎麼做、哪裡耗時或容易遺漏。",
        key="new_project_current",
        height=140,
    )
    outcome = st.text_area(
        "希望改善的成果（選填）",
        help="尚未確定可先留白，後續訪談會協助整理期望成果與驗收方式。",
        key="new_project_outcome",
        height=120,
    )
    st.caption("尚未確定可先留白，後續訪談會協助整理期望成果與驗收方式。")
    data = st.text_area(
        "現有資料與文件（選填）",
        help="可列出表單、規範、紀錄或系統資料；不確定可先留白。",
        key="new_project_data",
        height=120,
    )
    st.caption("可列出表單、規範、紀錄或系統資料；不確定可先留白。")
    owners = st.text_area(
        "使用者與負責人（選填）",
        help="可填寫實際使用者、審核者、流程負責人與維運角色；不確定可先留白。",
        key="new_project_owners",
    )
    st.caption("可填寫實際使用者、審核者、流程負責人與維運角色；不確定可先留白。")
    constraints = st.text_area(
        "已知限制（選填）",
        help=(
            "不確定可先留白，後續訪談會協助補充。可填寫預算、時程、"
            "個資、法規、部署環境或人工核准要求。"
        ),
        key="new_project_constraints",
    )
    st.caption(
        "不確定可先留白，後續訪談會協助補充。可填寫預算、時程、"
        "個資、法規、部署環境或人工核准要求。"
    )
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
                "desired_outcome": _optional_text(outcome),
                "available_data": _optional_text(data),
                "users_and_owners": _optional_text(owners),
                "known_constraints": _optional_text(constraints),
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
        open_workspace(str(project["id"]), int(version["version_number"]))
    except ApiClientError as error:
        show_api_error(error)
