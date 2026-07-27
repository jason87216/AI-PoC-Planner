"""Durable Streamlit route helpers for project-centered navigation."""

from __future__ import annotations

import streamlit as st


def open_new_project() -> None:
    st.query_params.clear()
    st.switch_page("app_pages/new_project.py")


def open_history() -> None:
    st.query_params.clear()
    st.switch_page("app_pages/history.py")


def open_workspace(project_id: str, version_number: int) -> None:
    st.switch_page(
        "app_pages/discovery.py",
        query_params={
            "project_id": project_id,
            "version": str(version_number),
        },
    )


def workspace_target_from_query() -> tuple[str, int] | None:
    project_id = st.query_params.get("project_id")
    version = st.query_params.get("version")
    if (
        not isinstance(project_id, str)
        or not project_id
        or not isinstance(version, str)
    ):
        return None
    try:
        version_number = int(version)
    except ValueError:
        return None
    return project_id, version_number
