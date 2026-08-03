"""Model-profile overview backed by the public FastAPI boundary."""

from __future__ import annotations

import streamlit as st

from ai_poc_planner.ui.api_client import ApiClientError
from ai_poc_planner.ui.navigation import (
    open_model_settings_edit,
    open_model_settings_new,
)
from ai_poc_planner.ui.presentation import (
    connection_label,
    profile_label,
    show_api_error,
)
from ai_poc_planner.ui.runtime import (
    get_api_client,
    load_profiles,
    refresh_api_data,
)


def _refresh_after_change(message: str) -> None:
    refresh_api_data()
    st.success(message)


st.title("模型設定")
st.caption(
    "管理目前使用的模型服務；新增與編輯會在獨立頁面完成。"
    "已保存的 API key 不會再次顯示。"
)
st.warning(
    "API key 保存後不會再次顯示。此 MVP 目前會將 key 明文保存在本機 "
    "private model_profiles.json；請勿在共用電腦使用，也不要在截圖、日誌或版本控制中"
    "暴露。"
)

with st.container(horizontal=True):
    if st.button("新增模型設定", icon=":material/add:", type="primary"):
        open_model_settings_new()
    if st.button("重新整理模型設定", icon=":material/refresh:"):
        refresh_api_data()
        st.rerun()

try:
    profiles = load_profiles()
except ApiClientError as error:
    show_api_error(error)
    profiles = []

st.subheader("目前模型")
if not profiles:
    st.info("尚未建立模型設定。請先新增設定，再測試模型可用性。")
else:
    client = get_api_client()
    for profile in profiles:
        profile_id = str(profile["id"])
        with st.container(border=True):
            st.subheader(profile_label(profile))
            st.write(f"模型：{profile.get('model_name', '')}")
            st.caption(
                "啟用狀態：已啟用" if profile.get("is_enabled") else "啟用狀態：已停用"
            )
            try:
                status = client.profile_status(profile_id)
                st.caption(
                    f"模型狀態：{connection_label(status.get('connection_state'))}"
                )
            except ApiClientError as error:
                st.caption("模型狀態：尚未取得")
                show_api_error(error)

            with st.container(horizontal=True):
                if st.button(
                    "測試模型可用性",
                    key=f"test_{profile_id}",
                    icon=":material/network_check:",
                ):
                    try:
                        result = client.test_profile(profile_id)
                    except ApiClientError as error:
                        show_api_error(error)
                    else:
                        refresh_api_data()
                        st.success(
                            f"模型狀態：{connection_label(result.get('connection_state'))}"
                        )
                if not profile.get("is_selected") and st.button(
                    "設為目前使用",
                    key=f"select_{profile_id}",
                    icon=":material/check_circle:",
                ):
                    try:
                        client.select_profile(profile_id)
                    except ApiClientError as error:
                        show_api_error(error)
                    else:
                        _refresh_after_change("已更新目前使用的模型設定。")
                if st.button(
                    "編輯",
                    key=f"edit_{profile_id}",
                    icon=":material/edit:",
                ):
                    open_model_settings_edit(profile_id)
