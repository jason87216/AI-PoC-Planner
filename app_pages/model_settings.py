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
    if api_key:
        payload["api_key"] = api_key
    if structured_output_mode:
        payload["structured_output_mode"] = structured_output_mode
    if reasoning_effort:
        payload["reasoning_effort"] = reasoning_effort
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
    reasoning_effort = st.selectbox(
        "推理強度（選填）",
        options=["", "low", "medium", "high"],
        format_func=lambda value: {
            "": "不指定",
            "low": "低",
            "medium": "中",
            "high": "高",
        }[value],
    )
    is_enabled = st.checkbox("建立後啟用", value=True)
    create_submitted = st.form_submit_button("建立設定", icon=":material/add:")

if create_submitted:
    try:
        get_api_client().create_profile(
            _profile_payload(
                profile_name=profile_name,
                base_url=base_url,
                model_name=model_name,
                api_key=api_key,
                structured_output_mode=structured_output_mode,
                reasoning_effort=reasoning_effort,
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
        updated_name = st.text_input("設定名稱（留白則不變）")
        updated_endpoint = st.text_input("新服務端點（留白則不變）")
        updated_model_name = st.text_input("模型名稱（留白則不變）")
        updated_api_key = st.text_input("新的 API key（留白則不變）", type="password")
        enabled = st.checkbox("啟用此設定", value=bool(selected_profile["is_enabled"]))
        update_submitted = st.form_submit_button("儲存變更", icon=":material/save:")

    if update_submitted:
        try:
            get_api_client().update_profile(
                profile_id,
                _profile_payload(
                    profile_name=updated_name,
                    base_url=updated_endpoint,
                    model_name=updated_model_name,
                    api_key=updated_api_key,
                    structured_output_mode="",
                    reasoning_effort="",
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
