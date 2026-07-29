"""Model-profile management page backed by safe public HTTP contracts."""

from __future__ import annotations

from typing import Any

import streamlit as st

from ai_poc_planner.ui.api_client import ApiClientError
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


def _profile_payload(
    *,
    profile_name: str,
    base_url: str,
    model_name: str,
    api_key: str,
    structured_output_mode: str,
    reasoning_effort: str,
    authentication: str,
    token_parameter: str,
    reasoning_parameter: str,
    supports_json_schema: bool,
    supports_json_object: bool,
    clear_api_key: bool,
    is_enabled: bool,
    include_required_fields: bool,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"is_enabled": is_enabled}
    if include_required_fields or profile_name:
        payload["profile_name"] = profile_name
    if include_required_fields or base_url:
        payload["base_url"] = base_url
    if include_required_fields or model_name:
        payload["model_name"] = model_name
    if clear_api_key:
        payload["api_key"] = None
    elif api_key:
        payload["api_key"] = api_key
    if structured_output_mode:
        payload["structured_output_mode"] = structured_output_mode
    if reasoning_parameter == "unsupported":
        # Explicitly clear a previously saved effort when the capability changes.
        payload["reasoning_effort"] = None
    elif reasoning_effort:
        payload["reasoning_effort"] = reasoning_effort
    if include_required_fields or any(
        [
            authentication,
            token_parameter,
            reasoning_parameter,
            supports_json_schema,
            supports_json_object,
        ]
    ):
        payload["capabilities"] = {
            "authentication": authentication,
            "token_parameter": token_parameter,
            "reasoning_parameter": reasoning_parameter,
            "json_schema": supports_json_schema,
            "json_object": supports_json_object,
        }
    return payload


st.title("模型設定")
st.caption("設定內容僅經由本機 FastAPI 儲存；API key 不會再次顯示於本頁。")

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
    st.info("尚未建立模型設定。")
else:
    for profile in profiles:
        with st.container(border=True):
            st.subheader(str(profile.get("profile_name", "未命名設定")))
            st.write(str(profile.get("model_name", "")))
            st.caption("目前使用" if profile.get("is_selected") else "可供選擇")
            st.caption("已啟用" if profile.get("is_enabled") else "已停用")

st.subheader("新增模型設定")
with st.form("create_model_profile", clear_on_submit=True):
    profile_name = st.text_input("設定名稱")
    base_url = st.text_input("服務端點")
    model_name = st.text_input("模型名稱")
    api_key = st.text_input("API key（選填）", type="password")
    structured_output_mode = st.selectbox(
        "結構化輸出模式（選填）",
        options=["", "json_schema", "json_object"],
        format_func=lambda value: {
            "": "不指定",
            "json_schema": "JSON Schema",
            "json_object": "JSON Object",
        }[value],
    )
    reasoning_parameter = st.selectbox(
        "Reasoning parameter",
        ["unsupported", "reasoning_effort"],
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

    with st.expander("Advanced compatibility settings"):
        authentication = st.selectbox(
            "Authentication mode",
            ["bearer_optional", "bearer_required", "none"],
        )
        token_parameter = st.selectbox(
            "Token parameter", ["max_tokens", "max_completion_tokens"]
        )
        supports_json_schema = st.checkbox("Supports JSON Schema", value=True)
        supports_json_object = st.checkbox("Supports JSON Object", value=True)
        preferred_mode = st.selectbox(
            "Preferred structured-output mode", ["json_schema", "json_object"]
        )
        clear_api_key = st.checkbox("清除已保存 API key")

if create_submitted and not (supports_json_schema or supports_json_object):
    st.error("至少要選擇一種 structured-output mode。")
elif create_submitted and (
    (preferred_mode == "json_schema" and not supports_json_schema)
    or (preferred_mode == "json_object" and not supports_json_object)
):
    st.error("Preferred mode 必須在支援的模式中。")
elif create_submitted and reasoning_parameter == "unsupported" and reasoning_effort:
    st.error("此端點不支援 reasoning effort，請清除該設定。")
elif create_submitted and authentication == "none" and api_key and not clear_api_key:
    st.error("none 認證模式不允許保存 API key，請清除輸入。")
elif create_submitted:
    try:
        get_api_client().create_profile(
            _profile_payload(
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
                clear_api_key=clear_api_key,
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
            "Authentication mode",
            ["bearer_optional", "bearer_required", "none"],
            index=["bearer_optional", "bearer_required", "none"].index(
                current_capabilities.get("authentication", "bearer_optional")
            ),
        )
        update_token_parameter = st.selectbox(
            "Token parameter",
            ["max_tokens", "max_completion_tokens"],
            index=["max_tokens", "max_completion_tokens"].index(
                current_capabilities.get("token_parameter", "max_tokens")
            ),
        )
        update_reasoning_parameter = st.selectbox(
            "Reasoning parameter",
            ["unsupported", "reasoning_effort"],
            index=["unsupported", "reasoning_effort"].index(
                current_capabilities.get("reasoning_parameter", "unsupported")
            ),
        )
        update_supports_json_schema = st.checkbox(
            "Supports JSON Schema",
            value=bool(current_capabilities.get("json_schema", False)),
        )
        update_supports_json_object = st.checkbox(
            "Supports JSON Object",
            value=bool(current_capabilities.get("json_object", True)),
        )
        update_preferred_mode = st.selectbox(
            "Preferred structured-output mode",
            ["json_schema", "json_object"],
            index=0
            if selected_profile.get("structured_output_mode") == "json_schema"
            else 1,
        )
        update_reasoning_effort = st.selectbox(
            "Reasoning effort",
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
        update_clear_api_key = st.checkbox("清除已保存 API key")
        updated_name = st.text_input("設定名稱（留白則不變）")
        updated_endpoint = st.text_input("新服務端點（留白則不變）")
        updated_model_name = st.text_input("模型名稱（留白則不變）")
        updated_api_key = st.text_input("新的 API key（留白則不變）", type="password")
        enabled = st.checkbox("啟用此設定", value=bool(selected_profile["is_enabled"]))
        update_submitted = st.form_submit_button("儲存變更", icon=":material/save:")

    if update_submitted and not (
        update_supports_json_schema or update_supports_json_object
    ):
        st.error("至少要選擇一種 structured-output mode。")
    elif update_submitted and (
        (update_preferred_mode == "json_schema" and not update_supports_json_schema)
        or (update_preferred_mode == "json_object" and not update_supports_json_object)
    ):
        st.error("Preferred mode 必須在支援的模式中。")
    elif (
        update_submitted
        and update_reasoning_parameter == "unsupported"
        and update_reasoning_effort
    ):
        st.error("此端點不支援 reasoning effort，請清除該設定。")
    elif (
        update_submitted
        and update_clear_api_key is False
        and update_authentication == "none"
    ):
        st.error("none 認證模式需要先清除已保存 API key。")
    elif update_submitted:
        try:
            get_api_client().update_profile(
                profile_id,
                _profile_payload(
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
        if st.button("測試連線", icon=":material/network_check:"):
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
