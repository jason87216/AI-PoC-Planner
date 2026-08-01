"""Small presentation helpers that never expose raw API error content."""

from __future__ import annotations

from typing import Any

import streamlit as st

from ai_poc_planner.ui.api_client import ApiClientError

_STATUS_LABELS = {
    "draft": "草稿",
    "interviewing": "訪談中",
    "clarification_required": "待釐清",
    "ready_for_assessment": "待評估",
    "assessed": "已評估",
    "proposal_generated": "已產生提案",
    "complete": "已完成",
    "failed": "需要處理",
}

_CONNECTION_LABELS = {
    "untested": "尚未測試",
    "testing": "測試中",
    "connected": "已連線",
    "failed": "連線失敗",
    "disabled": "已停用",
}


def status_label(value: object) -> str:
    return _STATUS_LABELS.get(str(value), "處理中")


def connection_label(value: object) -> str:
    return _CONNECTION_LABELS.get(str(value), "尚未測試")


def profile_label(profile: dict[str, Any]) -> str:
    selected = "（目前使用）" if profile.get("is_selected") else ""
    profile_name = profile.get("profile_name", "未命名設定")
    model_name = profile.get("model_name", "")
    return f"{profile_name} — {model_name}{selected}"


def profile_options(profiles: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Keep selections stable even when two profiles share a display label."""

    return {str(profile["id"]): profile for profile in profiles}


def show_api_error(error: ApiClientError) -> None:
    user_message = error.user_message
    user_action = error.user_action
    if error.code == "provider_not_ready":
        user_message = "模型尚未通過可用性測試。"
        user_action = (
            "請前往模型設定確認端點、模型名稱、驗證方式與結構化輸出能力後重新測試。"
        )
    st.error(f"目前無法完成這項操作：{user_message}")
    if user_action:
        st.info(f"建議：{user_action}")
    if error.retryable:
        st.caption("修正設定後或稍後再試即可；系統不會改用未選定的模型服務。")
