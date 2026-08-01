"""Model-profile management page backed by safe public HTTP contracts."""

from __future__ import annotations

import streamlit as st

from ai_poc_planner.ui.api_client import ApiClientError
from ai_poc_planner.ui.model_profile_form import (
    capability_help,
    capability_label,
    create_profile_authentication_error,
    profile_payload,
)
from ai_poc_planner.ui.presentation import (
    connection_label,
    profile_label,
    profile_options,
    show_api_error,
)
from ai_poc_planner.ui.runtime import (
    get_api_client,
    load_profiles,
    refresh_api_data,
)


def _optional_choice(value: str) -> str | None:
    return value or None


def _refresh_after_change(message: str) -> None:
    refresh_api_data()
    st.success(message)


st.title("模型設定")
st.caption(
    "在這裡建立、測試並選擇專案要使用的模型服務。設定只經由本機服務儲存；"
    "已保存的 API key 不會再次顯示。MVP 目前會以明文保存於 "
    "private model_profiles.json；"
    "請勿在共用電腦或截圖中暴露 key。"
)

if st.button("重新整理模型設定", icon=":material/refresh:"):
    refresh_api_data()
    st.rerun()

try:
    profiles = load_profiles()
except ApiClientError as error:
    show_api_error(error)
    profiles = []

st.subheader("目前設定")
if not profiles:
    st.info("尚未建立模型設定。請先建立一筆設定並完成模型可用性測試，才能建立專案。")
else:
    for profile in profiles:
        with st.container(border=True):
            st.subheader(str(profile.get("profile_name", "未命名設定")))
            st.write(str(profile.get("model_name", "")))
            st.caption("目前使用" if profile.get("is_selected") else "可供選擇")
            st.caption("已啟用" if profile.get("is_enabled") else "已停用")

st.subheader("新增模型設定")
with st.form("create_model_profile", clear_on_submit=True):
    profile_name = st.text_input("設定名稱", help="用容易辨識的名稱區分不同模型服務。")
    base_url = st.text_input(
        "服務端點",
        help="填入 OpenAI-compatible /v1 base URL；請確認端點由你自行管理。",
    )
    model_name = st.text_input("模型名稱", help="填入端點實際提供的模型名稱或 alias。")
    api_key = st.text_input(
        "API key（選填）",
        type="password",
        help="僅在端點需要 Bearer 認證時填寫；保存後不會在 UI 顯示。",
    )
    structured_output_mode = st.selectbox(
        "偏好的結構化輸出模式（選填）",
        options=["", "json_schema", "json_object"],
        format_func=lambda value: {
            "": "不指定",
            "json_schema": capability_label("structured_output", "json_schema"),
            "json_object": capability_label("structured_output", "json_object"),
        }[value],
        help=capability_help("preferred_mode"),
    )
    reasoning_parameter = st.selectbox(
        "推理參數能力",
        ["unsupported", "reasoning_effort"],
        format_func=lambda value: capability_label("reasoning_parameter", value),
        help=capability_help("reasoning_parameter"),
    )
    reasoning_effort = st.selectbox(
        "推理強度（選填）",
        options=(
            ["", "low", "medium", "high"]
            if reasoning_parameter != "unsupported"
            else [""]
        ),
        format_func=lambda value: {
            "": "不指定",
            "low": "低",
            "medium": "中",
            "high": "高",
        }[value],
    )
    is_enabled = st.checkbox("建立後啟用", value=True)
    create_submitted = st.form_submit_button("建立設定", icon=":material/add:")

    with st.expander("進階相容性設定"):
        st.caption("請依端點文件確認能力；產品不會根據品牌或模型名稱自動猜測。")
        authentication = st.selectbox(
            "認證方式",
            ["bearer_optional", "bearer_required", "none"],
            format_func=lambda value: capability_label("authentication", value),
            help=capability_help("authentication"),
        )
        token_parameter = st.selectbox(
            "輸出預算欄位",
            ["max_tokens", "max_completion_tokens"],
            format_func=lambda value: capability_label("token_parameter", value),
            help=capability_help("token_parameter"),
        )
        supports_json_schema = st.checkbox(
            "支援 JSON Schema",
            value=True,
            help="端點能否接受巢狀的 OpenAI JSON Schema response format。",
        )
        supports_json_object = st.checkbox(
            "支援 JSON Object",
            value=True,
            help="端點能否要求回傳 JSON object；這是較寬鬆的結構化模式。",
        )
        preferred_mode = st.selectbox(
            "首選結構化輸出模式",
            ["json_schema", "json_object"],
            format_func=lambda value: capability_label("structured_output", value),
            help=capability_help("preferred_mode"),
        )

if create_submitted and not (supports_json_schema or supports_json_object):
    st.error("至少要選擇一種結構化輸出模式。")
elif create_submitted and (
    (preferred_mode == "json_schema" and not supports_json_schema)
    or (preferred_mode == "json_object" and not supports_json_object)
):
    st.error("首選模式必須包含在已支援的模式中。")
elif create_submitted and reasoning_parameter == "unsupported" and reasoning_effort:
    st.error("目前端點不支援推理強度，請選擇「不傳送推理參數」。")
elif create_submitted and (
    authentication_error := create_profile_authentication_error(authentication, api_key)
):
    st.error(authentication_error)
elif create_submitted:
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
        _refresh_after_change("模型設定已建立。")

if profiles:
    st.subheader("管理既有設定")
    profiles_by_id = profile_options(profiles)
    profile_id = st.selectbox(
        "選擇要管理的設定",
        options=list(profiles_by_id),
        format_func=lambda value: profile_label(profiles_by_id[value]),
    )
    selected_profile = profiles_by_id[profile_id]

    with st.form("update_model_profile"):
        current_capabilities = selected_profile.get("capabilities") or {}
        update_authentication = st.selectbox(
            "認證方式",
            ["bearer_optional", "bearer_required", "none"],
            format_func=lambda value: capability_label("authentication", value),
            help=capability_help("authentication"),
            index=["bearer_optional", "bearer_required", "none"].index(
                current_capabilities.get("authentication", "bearer_optional")
            ),
        )
        update_token_parameter = st.selectbox(
            "輸出預算欄位",
            ["max_tokens", "max_completion_tokens"],
            format_func=lambda value: capability_label("token_parameter", value),
            help=capability_help("token_parameter"),
            index=["max_tokens", "max_completion_tokens"].index(
                current_capabilities.get("token_parameter", "max_tokens")
            ),
        )
        update_reasoning_parameter = st.selectbox(
            "推理參數能力",
            ["unsupported", "reasoning_effort"],
            format_func=lambda value: capability_label("reasoning_parameter", value),
            help=capability_help("reasoning_parameter"),
            index=["unsupported", "reasoning_effort"].index(
                current_capabilities.get("reasoning_parameter", "unsupported")
            ),
        )
        update_supports_json_schema = st.checkbox(
            "支援 JSON Schema",
            value=bool(current_capabilities.get("json_schema", False)),
            help="端點能否接受巢狀的 OpenAI JSON Schema response format。",
        )
        update_supports_json_object = st.checkbox(
            "支援 JSON Object",
            value=bool(current_capabilities.get("json_object", True)),
            help="端點能否要求回傳 JSON object；這是較寬鬆的結構化模式。",
        )
        update_preferred_mode = st.selectbox(
            "首選結構化輸出模式",
            ["json_schema", "json_object"],
            format_func=lambda value: capability_label("structured_output", value),
            help=capability_help("preferred_mode"),
            index=0
            if selected_profile.get("structured_output_mode") == "json_schema"
            else 1,
        )
        update_reasoning_effort = st.selectbox(
            "推理強度（選填）",
            options=(
                ["", "low", "medium", "high"]
                if update_reasoning_parameter != "unsupported"
                else [""]
            ),
            index=(
                ["", "low", "medium", "high"].index(
                    selected_profile.get("reasoning_effort") or ""
                )
                if update_reasoning_parameter != "unsupported"
                else 0
            ),
            disabled=update_reasoning_parameter == "unsupported",
        )
        update_clear_api_key = st.checkbox(
            "清除已保存的 API key",
            help="留白不會顯示或覆寫原 key；若改用不需要認證的模式，請勾選此項。",
        )
        updated_name = st.text_input("設定名稱（留白則不變）")
        updated_endpoint = st.text_input("新服務端點（留白則不變）")
        updated_model_name = st.text_input("模型名稱（留白則不變）")
        updated_api_key = st.text_input(
            "新的 API key（留白則保留；清除請勾選上方選項）",
            type="password",
        )
        enabled = st.checkbox("啟用此設定", value=bool(selected_profile["is_enabled"]))
        update_submitted = st.form_submit_button("儲存變更", icon=":material/save:")

    if update_submitted and not (
        update_supports_json_schema or update_supports_json_object
    ):
        st.error("至少要選擇一種結構化輸出模式。")
    elif update_submitted and (
        (update_preferred_mode == "json_schema" and not update_supports_json_schema)
        or (update_preferred_mode == "json_object" and not update_supports_json_object)
    ):
        st.error("首選模式必須包含在已支援的模式中。")
    elif (
        update_submitted
        and update_reasoning_parameter == "unsupported"
        and update_reasoning_effort
    ):
        st.error("目前端點不支援推理強度，請選擇「不傳送推理參數」。")
    elif update_submitted:
        try:
            get_api_client().update_profile(
                profile_id,
                profile_payload(
                    profile_name=updated_name,
                    base_url=updated_endpoint,
                    model_name=updated_model_name,
                    api_key=updated_api_key,
                    structured_output_mode=update_preferred_mode,
                    reasoning_effort=update_reasoning_effort,
                    authentication=update_authentication,
                    token_parameter=update_token_parameter,
                    reasoning_parameter=update_reasoning_parameter,
                    supports_json_schema=update_supports_json_schema,
                    supports_json_object=update_supports_json_object,
                    clear_api_key=update_clear_api_key,
                    is_enabled=enabled,
                    include_required_fields=False,
                ),
            )
        except ApiClientError as error:
            show_api_error(error)
        else:
            _refresh_after_change("模型設定已更新。")

    with st.container(horizontal=True):
        if st.button("設為目前使用", icon=":material/check_circle:"):
            try:
                get_api_client().select_profile(profile_id)
            except ApiClientError as error:
                show_api_error(error)
            else:
                _refresh_after_change("已更新目前使用的模型設定。")
        if st.button("測試模型可用性", icon=":material/network_check:"):
            try:
                result = get_api_client().test_profile(profile_id)
            except ApiClientError as error:
                show_api_error(error)
            else:
                refresh_api_data()
                st.info(connection_label(result.get("connection_state")))

    with st.expander("移除此模型設定"):
        confirm_delete = st.checkbox(
            "我確認要移除此模型設定", key="confirm_profile_delete"
        )
        if st.button(
            "移除設定",
            icon=":material/delete:",
            type="secondary",
            disabled=not confirm_delete,
        ):
            try:
                get_api_client().delete_profile(profile_id)
            except ApiClientError as error:
                show_api_error(error)
            else:
                _refresh_after_change("模型設定已移除。")
