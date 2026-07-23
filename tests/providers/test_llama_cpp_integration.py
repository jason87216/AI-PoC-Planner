"""Opt-in real llama.cpp validation; skipped unless the operator configures it."""

from __future__ import annotations

import os
from pathlib import Path

import httpx
import pytest

from ai_poc_planner.application.provider_readiness import ProviderReadinessService
from ai_poc_planner.persistence.model_profiles import LocalModelProfileRepository
from ai_poc_planner.providers.openai_compatible import OpenAICompatibleChatAdapter

pytestmark = pytest.mark.llama_cpp


def test_user_started_llama_cpp_accepts_connection_test(tmp_path: Path) -> None:
    if os.environ.get("AI_POC_PLANNER_LLAMA_CPP_TEST") != "1":
        pytest.skip("set AI_POC_PLANNER_LLAMA_CPP_TEST=1 to run llama.cpp validation")
    base_url = os.environ.get("AI_POC_PLANNER_LLAMA_CPP_BASE_URL")
    model_name = os.environ.get("AI_POC_PLANNER_LLAMA_CPP_MODEL")
    if not base_url or not model_name:
        pytest.skip("llama.cpp base URL and model environment variables are required")

    repository = LocalModelProfileRepository(path=tmp_path / "model_profiles.json")
    profile = repository.create(
        profile_name="llama.cpp integration",
        base_url=base_url,
        model_name=model_name,
        api_key=os.environ.get("AI_POC_PLANNER_LLAMA_CPP_API_KEY"),
    )
    service = ProviderReadinessService(
        profiles=repository,
        adapter_factory=lambda selected: OpenAICompatibleChatAdapter(
            base_url=str(selected.base_url),
            model_name=selected.model_name,
            api_key=(
                selected.api_key.get_secret_value()
                if selected.api_key is not None
                else None
            ),
            client=httpx.Client(),
        ),
    )

    status = service.test(profile.id)

    assert status.formal_analysis_allowed is True
