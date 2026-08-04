"""Create one model profile through the public FastAPI boundary."""

from __future__ import annotations

import streamlit as st

from ai_poc_planner.ui.api_client import ApiClientError
from ai_poc_planner.ui.model_profile_form import (
    capability_help,
    capability_label,
    create_profile_authentication_error,
    profile_payload,
)
from ai_poc_planner.ui.navigation import switch_page
from ai_poc_planner.ui.presentation import show_api_error
from ai_poc_planner.ui.runtime import get_api_client, refresh_api_data


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


st.title("新增模型設定")
st.caption("先填寫端點基本資料；技術人員可在相容性設定中確認能力。")
if st.button("返回模型設定", icon=":material/arrow_back:"):
    switch_page("app_pages/model_settings.py")

with st.form("create_model_profile", clear_on_submit=True):
    profile_name = st.text_input("設定名稱")
    base_url = st.text_input(
        "服務端點",
        help=(
            "請使用你有權存取的 OpenAI-compatible 端點，並依服務文件填寫 /v1 base URL。"
        ),
    )
    model_name = st.text_input("模型名稱")
    api_key = st.text_input(
        "API key（選填）",
        type="password",
        help="請依端點文件選擇認證方式；保存後不會在 UI 顯示。",
    )
    st.caption("目前會明文保存在本機私人設定檔。")
    is_enabled = st.checkbox("建立後啟用", value=True)

    with st.expander("相容性設定（技術人員）"):
        st.caption(
            "多數使用者只需要依模型服務文件填寫；不確定時請先使用服務商建議值，"
            "再執行模型可用性測試。"
        )
        authentication = st.selectbox(
            "認證方式",
            ["bearer_optional", "bearer_required", "none"],
            format_func=lambda value: capability_label("authentication", value),
            help=capability_help("authentication"),
        )
        token_parameter = st.selectbox(
            "輸出長度參數",
            ["max_tokens", "max_completion_tokens"],
            format_func=lambda value: capability_label("token_parameter", value),
            help=capability_help("token_parameter"),
        )
        reasoning_parameter = st.selectbox(
            "推理參數能力",
            ["unsupported", "reasoning_effort"],
            format_func=lambda value: capability_label("reasoning_parameter", value),
            help=capability_help("reasoning_parameter"),
        )
        reasoning_effort = st.selectbox(
            "推理強度（選填）",
            ["", "low", "medium", "high"]
            if reasoning_parameter != "unsupported"
            else [""],
            format_func=lambda value: {
                "": "不指定",
                "low": "低",
                "medium": "中",
                "high": "高",
            }[value],
            disabled=reasoning_parameter == "unsupported",
        )
        supports_json_schema = st.checkbox(
            "支援嚴格結構化輸出（JSON Schema）", value=True
        )
        supports_json_object = st.checkbox(
            "支援一般 JSON 輸出（JSON Object）", value=True
        )
        preferred_mode = st.selectbox(
            "優先結構化輸出模式",
            ["json_schema", "json_object"],
            format_func=lambda value: capability_label("structured_output", value),
            help=capability_help("preferred_mode"),
        )

    submitted = st.form_submit_button("建立設定", icon=":material/add:")

if submitted:
    validation_error = _capability_error(
        preferred_mode,
        reasoning_parameter,
        reasoning_effort,
        supports_json_schema,
        supports_json_object,
    ) or create_profile_authentication_error(authentication, api_key)
    if validation_error:
        st.error(validation_error)
    else:
        try:
            get_api_client().create_profile(
                profile_payload(
                    profile_name=profile_name,
                    base_url=base_url,
                    model_name=model_name,
                    api_key=api_key,
                    structured_output_mode=preferred_mode,
                    reasoning_effort=reasoning_effort,
                    authentication=authentication,
                    token_parameter=token_parameter,
                    reasoning_parameter=reasoning_parameter,
                    supports_json_schema=supports_json_schema,
                    supports_json_object=supports_json_object,
                    is_enabled=is_enabled,
                    include_required_fields=True,
                )
            )
        except ApiClientError as error:
            show_api_error(error)
        else:
            refresh_api_data()
            st.success("模型設定已建立。")
