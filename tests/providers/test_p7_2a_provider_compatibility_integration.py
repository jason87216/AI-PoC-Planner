"""P7.2a representative governed_access compatibility coverage.

Live endpoint execution is deliberately opt-in.  The offline portion keeps the
fixture and deterministic expectations in one place while exercising both
capability declarations through the same structured-output executor.
"""

# ruff: noqa: E501

from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

from ai_poc_planner.application.provider_readiness import ConnectionProbe
from ai_poc_planner.providers.base import ReasoningEffort, StructuredOutputMode
from ai_poc_planner.providers.capabilities import (
    AuthenticationMode,
    OpenAICompatibleCapabilities,
    ReasoningParameter,
    TokenParameter,
)
from ai_poc_planner.providers.errors import ProviderOperation
from ai_poc_planner.providers.profiles import ModelProfile
from ai_poc_planner.providers.structured_output import StructuredOutputExecutor

SCENARIOS_PATH = (
    Path(__file__).parents[1] / "fixtures" / "product_acceptance" / "scenarios.json"
)
GOVERNED_ACCESS = next(
    item
    for item in json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))
    if item["scenario_id"] == "governed_access"
)
NOW = datetime(2026, 7, 30, tzinfo=UTC)


class CallRecorder:
    """Record only safe call metadata; never prompts, headers, keys, or responses."""

    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def complete(
        self,
        *,
        messages: Sequence[Mapping[str, str]],
        temperature: float,
        max_tokens: int,
        response_format: Any,
        reasoning_effort: ReasoningEffort | None = None,
    ) -> str:
        del messages, temperature, max_tokens, reasoning_effort
        request = response_format.as_request_value()
        self.calls.append(
            {
                "operation": "readiness",
                "schema_name": response_format.name or "",
                "mode": str(request["type"]),
            }
        )
        return '{"status":"ok"}'


def _profile(
    *,
    name: str,
    capabilities: OpenAICompatibleCapabilities,
    api_key: str | None,
    preferred: StructuredOutputMode,
) -> ModelProfile:
    return ModelProfile.model_validate(
        {
            "id": UUID(int=1 if name == "NVIDIA" else 2),
            "profile_name": name,
            "base_url": "https://provider.example.test/v1",
            "model_name": "representative-model",
            "api_key": api_key,
            "structured_output_mode": preferred,
            "reasoning_effort": "low" if name == "NVIDIA" else None,
            "capabilities": capabilities,
            "is_selected": True,
            "is_enabled": True,
            "created_at": NOW,
            "updated_at": NOW,
        }
    )


@pytest.mark.parametrize(
    ("profile", "expected_mode"),
    [
        (
            _profile(
                name="NVIDIA",
                api_key="synthetic-nvidia-key",
                preferred=StructuredOutputMode.JSON_SCHEMA,
                capabilities=OpenAICompatibleCapabilities(
                    authentication=AuthenticationMode.BEARER_REQUIRED,
                    token_parameter=TokenParameter.MAX_TOKENS,
                    reasoning_parameter=ReasoningParameter.REASONING_EFFORT,
                    json_schema=True,
                    json_object=True,
                ),
            ),
            "json_schema",
        ),
        (
            _profile(
                name="llama.cpp",
                api_key=None,
                preferred=StructuredOutputMode.JSON_OBJECT,
                capabilities=OpenAICompatibleCapabilities(
                    authentication=AuthenticationMode.BEARER_OPTIONAL,
                    token_parameter=TokenParameter.MAX_TOKENS,
                    reasoning_parameter=ReasoningParameter.UNSUPPORTED,
                    json_schema=False,
                    json_object=True,
                ),
            ),
            "json_object",
        ),
    ],
)
def test_governed_access_representative_profiles_share_executor_policy(
    profile: ModelProfile, expected_mode: str
) -> None:
    recorder = CallRecorder()
    result = StructuredOutputExecutor().execute(
        adapter=recorder,
        capabilities=profile.effective_capabilities,
        preferred_mode=profile.effective_structured_output_mode,
        operation=ProviderOperation.READINESS,
        schema_name="connection_probe",
        provider_contract=ConnectionProbe,
        messages=[{"role": "user", "content": "synthetic probe"}],
        logical_max_tokens=64,
        temperature=0,
        reasoning_effort=profile.reasoning_effort,
    )

    assert result.value.status == "ok"
    assert recorder.calls == [
        {
            "operation": "readiness",
            "schema_name": "connection_probe",
            "mode": expected_mode,
        }
    ]
    assert profile.api_key is None or "synthetic" in profile.api_key.get_secret_value()


def test_governed_access_fixture_keeps_deterministic_product_expectations() -> None:
    expected = GOVERNED_ACCESS["expected"]
    assert expected["recommendation_category"] == "rules_first"
    assert "主管保留最終核准" in expected["human_decision_boundary"]
    assert "不得自動開通" in expected["deployment_constraint"]
    assert expected["must_not_have_conclusions"] == [
        "AI 自動核准",
        "AI 直接寫入權限",
        "將個人資料送到未核准外部服務",
    ]


@pytest.mark.parametrize(
    ("flag", "required_env"),
    [
        ("AI_POC_PLANNER_P7_2A_NVIDIA_TEST", "NVIDIA_API_KEY"),
        ("AI_POC_PLANNER_P7_2A_LLAMA_CPP_TEST", "AI_POC_PLANNER_LLAMA_CPP_BASE_URL"),
    ],
)
def test_live_p7_2a_requires_explicit_endpoint_opt_in(
    flag: str, required_env: str
) -> None:
    if os.environ.get(flag) != "1":
        pytest.skip(f"set {flag}=1 to run the governed_access endpoint UAT")
    if not os.environ.get(required_env):
        pytest.skip(f"set {required_env} to run the governed_access endpoint UAT")
    pytest.skip(
        "Live governed_access UAT is run only in the controlled endpoint harness; "
        "this test does not substitute a fake provider for an opted-in endpoint."
    )
