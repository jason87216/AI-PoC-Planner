"""Durable Streamlit route helpers for project-centered navigation."""

from __future__ import annotations

import hashlib

import streamlit as st


def open_new_project() -> None:
    st.query_params.clear()
    st.switch_page("app_pages/new_project.py")


def open_history() -> None:
    st.query_params.clear()
    st.switch_page("app_pages/history.py")


def open_model_settings_new() -> None:
    st.query_params.clear()
    st.switch_page("app_pages/model_settings_new.py")


def open_model_settings_edit(profile_id: str) -> None:
    st.switch_page(
        "app_pages/model_settings_edit.py",
        query_params={"profile_id": profile_id},
    )


def open_workspace(project_id: str, version_number: int) -> None:
    st.switch_page(
        "app_pages/discovery.py",
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
