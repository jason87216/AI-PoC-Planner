"""Durable Streamlit route helpers for project-centered navigation."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from pathlib import PurePosixPath

import streamlit as st

_NAVIGATION_PENDING_KEY = "navigation_pending"
_STABLE_PAGE_KEY = "stable_page_key"

_PAGE_LABELS = {
    "home": "正在開啟首頁……",
    "new_project": "正在開啟新建專案……",
    "history": "正在開啟專案歷史……",
    "model_settings": "正在開啟模型設定……",
    "model_settings_new": "正在開啟新增模型設定……",
    "model_settings_edit": "正在開啟編輯模型設定……",
    "project": "正在開啟專案……",
    "project-results": "正在開啟評估報告……",
}

_RESULT_STATUSES = {
    "assessed",
    "proposal_generated",
    "complete",
}


def history_destination_for_status(status: object) -> str:
    """Choose the durable history destination from persisted version status."""

    if str(status) in _RESULT_STATUSES:
        return "results"
    return "workspace"


def page_route_key(page_path: str) -> str:
    """Return the stable public route key used by transition state."""

    name = PurePosixPath(page_path.replace("\\", "/")).stem
    return {"discovery": "project", "results": "project-results"}.get(name, name)


def page_transition_label(page_key: str) -> str:
    return _PAGE_LABELS.get(page_key, "正在開啟頁面……")


def mark_navigation_pending(page_path: str) -> None:
    """Remember a switch target until its destination finishes rendering."""

    page_key = page_route_key(page_path)
    stable_page_key = st.session_state.get(_STABLE_PAGE_KEY)
    if page_key == stable_page_key:
        st.session_state.pop(_NAVIGATION_PENDING_KEY, None)
        return
    st.session_state[_NAVIGATION_PENDING_KEY] = {
        "page_key": page_key,
        "label": page_transition_label(page_key),
    }


def switch_page(
    page_path: str,
    *,
    query_params: Mapping[str, str | list[str]] | None = None,
) -> None:
    """Mark a destination before invoking Streamlit's public page switch API."""

    mark_navigation_pending(page_path)
    st.switch_page(page_path, query_params=query_params)


def transition_for_page(page_key: str) -> tuple[bool, str]:
    """Return whether this render is a real page transition and its label."""

    previous = st.session_state.get(_STABLE_PAGE_KEY)
    pending = st.session_state.get(_NAVIGATION_PENDING_KEY)
    pending_key = pending.get("page_key") if isinstance(pending, dict) else None
    if pending_key == page_key:
        label = str(pending.get("label") or page_transition_label(page_key))
        return True, label
    if previous != page_key:
        return True, page_transition_label(page_key)
    return False, ""


def finish_page_render(page_key: str) -> None:
    """Commit a stable page after render; keep source pending state across reruns."""

    pending = st.session_state.get(_NAVIGATION_PENDING_KEY)
    pending_key = pending.get("page_key") if isinstance(pending, dict) else None
    if pending_key not in (None, page_key):
        # The current script was interrupted by st.switch_page. The target
        # marker must survive until the destination page starts.
        return
    st.session_state[_STABLE_PAGE_KEY] = page_key
    st.session_state.pop(_NAVIGATION_PENDING_KEY, None)


def open_new_project() -> None:
    st.query_params.clear()
    switch_page("app_pages/new_project.py")


def open_history() -> None:
    st.query_params.clear()
    switch_page("app_pages/history.py")


def open_model_settings_new() -> None:
    st.query_params.clear()
    switch_page("app_pages/model_settings_new.py")


def open_model_settings_edit(profile_id: str) -> None:
    switch_page(
        "app_pages/model_settings_edit.py",
        query_params={"profile_id": profile_id},
    )


def open_workspace(project_id: str, version_number: int) -> None:
    _open_project_page(
        "app_pages/discovery.py",
        project_id,
        version_number,
    )


def open_results(project_id: str, version_number: int) -> None:
    """Open the persisted results for an explicit project/version target."""

    _open_project_page("app_pages/results.py", project_id, version_number)


def _open_project_page(page_path: str, project_id: str, version_number: int) -> None:
    st.session_state["selected_project"] = {
        "project_id": project_id,
        "version_number": version_number,
    }
    switch_page(
        page_path,
        query_params={
            "workspace": workspace_route_key(project_id),
            "version": str(version_number),
        },
    )


def workspace_route_key(project_id: str) -> str:
    """Create a non-reversible route key so raw project IDs stay out of the URL."""

    return hashlib.sha256(project_id.encode("utf-8")).hexdigest()[:16]


def workspace_target_from_query() -> tuple[str, int] | None:
    route_key = st.query_params.get("workspace")
    version = st.query_params.get("version")
    if not isinstance(route_key, str) or not route_key or not isinstance(version, str):
        return None
    try:
        version_number = int(version)
    except ValueError:
        return None
    return route_key, version_number
