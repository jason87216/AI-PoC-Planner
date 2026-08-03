"""Edit one model profile through the public FastAPI boundary."""

from __future__ import annotations

import streamlit as st

from ai_poc_planner.ui.api_client import ApiClientError
from ai_poc_planner.ui.model_profile_form import (
    capability_help,
    capability_label,
    profile_payload,
)
from ai_poc_planner.ui.navigation import switch_page
from ai_poc_planner.ui.presentation import profile_label, show_api_error
from ai_poc_planner.ui.runtime import get_api_client, load_profiles, refresh_api_data


def _capability_error(
    preferred_mode: str,
    reasoning_parameter: str,
    reasoning_effort: str,
    supports_json_schema: bool,
    supports_json_object: bool,
) -> str | None:
    if not (supports_json_schema or supports_json_object):
        return "至少要選擇一種結構化輸出模式。"
    if preferred_mode == "json_schema" and not supports_json_schema:
        return "首選模式必須包含在已支援的模式中。"
    if preferred_mode == "json_object" and not supports_json_object:
        return "首選模式必須包含在已支援的模式中。"
    if reasoning_parameter == "unsupported" and reasoning_effort:
        return "目前端點不支援推理強度，請選擇「不傳送推理強度」。"
    return None


st.title("編輯模型設定")
st.caption("只修改已存在的設定；已保存的 API key 不會回顯。")
if st.button("返回模型設定", icon=":material/arrow_back:"):
    switch_page("app_pages/model_settings.py")

profile_id = st.query_params.get("profile_id")
try:
    profiles = load_profiles()
except ApiClientError as error:
    show_api_error(error)
    profiles = []

selected_profile = next(
    (profile for profile in profiles if str(profile.get("id")) == profile_id),
    None,
)
if selected_profile is None:
    st.warning("找不到要編輯的模型設定，請回到模型設定首頁重新選擇。")
    st.stop()

st.subheader(profile_label(selected_profile))
capabilities = selected_profile.get("capabilities") or {}
auth_options = ["bearer_optional", "bearer_required", "none"]
token_options = ["max_tokens", "max_completion_tokens"]
reasoning_options = ["unsupported", "reasoning_effort"]
preferred_mode = (
    "json_schema"
    if selected_profile.get("structured_output_mode") == "json_schema"
    else "json_object"
)

with st.form("update_model_profile"):
    updated_name = st.text_input("設定名稱（留白則不變）")
    updated_endpoint = st.text_input("服務端點（留白則不變）")
    updated_model_name = st.text_input("模型名稱（留白則不變）")
    updated_api_key = st.text_input(
        "新的 API key（留白則保留；清除請勾選下方選項）",
        type="password",
    )
    st.caption("API key 不會回顯；此欄留白會保留原值。現行保存方式仍是本機明文設定檔。")
    enabled = st.checkbox("啟用此設定", value=bool(selected_profile["is_enabled"]))

    with st.expander("相容性設定（技術人員）"):
        st.caption(
            "多數使用者只需要依模型服務文件填寫；不確定時請先使用服務商建議值，"
            "再執行模型可用性測試。"
        )
        authentication = st.selectbox(
            "認證方式",
            auth_options,
            index=auth_options.index(
                capabilities.get("authentication", "bearer_optional")
            ),
            format_func=lambda value: capability_label("authentication", value),
            help=capability_help("authentication"),
        )
        token_parameter = st.selectbox(
            "輸出長度參數",
            token_options,
            index=token_options.index(
                capabilities.get("token_parameter", "max_tokens")
            ),
            format_func=lambda value: capability_label("token_parameter", value),
            help=capability_help("token_parameter"),
        )
        reasoning_parameter = st.selectbox(
            "推理參數能力",
            reasoning_options,
            index=reasoning_options.index(
                capabilities.get("reasoning_parameter", "unsupported")
            ),
            format_func=lambda value: capability_label("reasoning_parameter", value),
            help=capability_help("reasoning_parameter"),
        )
        current_effort = selected_profile.get("reasoning_effort") or ""
        reasoning_effort = st.selectbox(
            "推理強度（選填）",
            ["", "low", "medium", "high"]
            if reasoning_parameter != "unsupported"
            else [""],
            index=(
                ["", "low", "medium", "high"].index(current_effort)
                if reasoning_parameter != "unsupported"
                and current_effort in {"low", "medium", "high"}
                else 0
            ),
            format_func=lambda value: {
                "": "不指定",
                "low": "低",
                "medium": "中",
                "high": "高",
            }[value],
            disabled=reasoning_parameter == "unsupported",
        )
        supports_json_schema = st.checkbox(
            "支援嚴格結構化輸出（JSON Schema）",
            value=bool(capabilities.get("json_schema", False)),
        )
        supports_json_object = st.checkbox(
            "支援一般 JSON 輸出（JSON Object）",
            value=bool(capabilities.get("json_object", True)),
        )
        preferred_mode = st.selectbox(
            "優先結構化輸出模式",
            ["json_schema", "json_object"],
            index=0 if preferred_mode == "json_schema" else 1,
            format_func=lambda value: capability_label("structured_output", value),
            help=capability_help("preferred_mode"),
        )
        clear_api_key = st.checkbox(
            "清除已保存的 API key",
            help="若改用不需要 API key 的認證方式，必須勾選此項。",
        )

    submitted = st.form_submit_button("儲存變更", icon=":material/save:")

if submitted:
    validation_error = _capability_error(
        preferred_mode,
        reasoning_parameter,
        reasoning_effort,
        supports_json_schema,
        supports_json_object,
    )
    if authentication == "none" and not clear_api_key:
        validation_error = "選擇「不需要 API key」時，請同時勾選清除已保存的 API key。"
    if validation_error:
        st.error(validation_error)
    else:
        try:
            get_api_client().update_profile(
                str(profile_id),
                profile_payload(
                    profile_name=updated_name,
                    base_url=updated_endpoint,
                    model_name=updated_model_name,
                    api_key=updated_api_key,
                    structured_output_mode=preferred_mode,
                    reasoning_effort=reasoning_effort,
                    authentication=authentication,
                    token_parameter=token_parameter,
                    reasoning_parameter=reasoning_parameter,
                    supports_json_schema=supports_json_schema,
                    supports_json_object=supports_json_object,
                    clear_api_key=clear_api_key,
                    is_enabled=enabled,
                    include_required_fields=False,
                ),
            )
        except ApiClientError as error:
            show_api_error(error)
        else:
            refresh_api_data()
            st.success("模型設定已更新。")

with st.expander("移除此模型設定"):
    confirm_delete = st.checkbox("我確認要移除此模型設定")
    if st.button(
        "移除設定",
        icon=":material/delete:",
        type="secondary",
        disabled=not confirm_delete,
    ):
        try:
            get_api_client().delete_profile(str(profile_id))
        except ApiClientError as error:
            show_api_error(error)
        else:
            refresh_api_data()
            st.success("模型設定已移除。")
