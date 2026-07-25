"""Shared Streamlit resources and explicitly short-lived API data caches."""

from __future__ import annotations

import os
from typing import Any

import streamlit as st

from ai_poc_planner.ui.api_client import ApiClient


@st.cache_resource
def get_api_client() -> ApiClient:
    return ApiClient(base_url=os.environ.get("AI_POC_PLANNER_API_BASE_URL"))


@st.cache_data(ttl=10)
def load_projects() -> list[dict[str, Any]]:
    return get_api_client().list_projects()


@st.cache_data(ttl=10)
def load_profiles() -> list[dict[str, Any]]:
    return get_api_client().list_profiles()


@st.cache_data(ttl=10)
def load_provider_status() -> dict[str, Any]:
    return get_api_client().provider_status()


def refresh_api_data() -> None:
    load_projects.clear()
    load_profiles.clear()
    load_provider_status.clear()
