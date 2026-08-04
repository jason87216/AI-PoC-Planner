"""Shared Streamlit resources and explicitly short-lived API data caches."""

from __future__ import annotations

import os
from typing import Any

import streamlit as st

from ai_poc_planner.ui.api_client import ApiClient
from ai_poc_planner.ui.recovery import StateAwareApiClient


@st.cache_resource
def get_api_client(
    base_url: str | None = None, expected_instance_id: str | None = None
) -> ApiClient:
    del expected_instance_id
    return StateAwareApiClient(
        base_url=base_url or os.environ.get("AI_POC_PLANNER_API_BASE_URL")
    )


def validate_streamlit_runtime() -> None:
    get_api_client().validate_runtime(os.environ.get("AI_POC_PLANNER_INSTANCE_ID"))


@st.cache_data(ttl=10)
def load_projects() -> list[dict[str, Any]]:
    return get_api_client().list_projects()


@st.cache_data(ttl=10)
def load_profiles() -> list[dict[str, Any]]:
    return get_api_client().list_profiles()


@st.cache_data(ttl=10)
def load_provider_status() -> dict[str, Any]:
    return get_api_client().provider_status()


@st.cache_data(ttl=10)
def load_discovery_session(project_id: str, version_number: int) -> dict[str, Any]:
    return get_api_client().get_discovery_session(project_id, version_number)


@st.cache_data(ttl=10)
def load_visible_messages(project_id: str, version_number: int) -> list[dict[str, Any]]:
    return get_api_client().list_visible_messages(project_id, version_number)


@st.cache_data(ttl=10)
def load_current_facts(project_id: str, version_number: int) -> list[dict[str, Any]]:
    return get_api_client().list_current_facts(project_id, version_number)


@st.cache_data(ttl=10)
def load_interview_questions(
    project_id: str, version_number: int
) -> list[dict[str, Any]]:
    return get_api_client().list_interview_questions(project_id, version_number)


@st.cache_data(ttl=10)
def load_project_version(project_id: str, version_number: int) -> dict[str, Any]:
    return get_api_client().get_project_version(project_id, version_number)


@st.cache_data(ttl=10)
def load_analysis(project_id: str, version_number: int) -> dict[str, Any]:
    return get_api_client().get_analysis(project_id, version_number)


@st.cache_data(ttl=10)
def load_report(project_id: str, version_number: int) -> dict[str, Any]:
    return get_api_client().get_report(project_id, version_number)


def refresh_api_data() -> None:
    load_projects.clear()
    load_profiles.clear()
    load_provider_status.clear()
    load_discovery_session.clear()
    load_visible_messages.clear()
    load_current_facts.clear()
    load_interview_questions.clear()
    load_project_version.clear()
    load_analysis.clear()
    load_report.clear()
