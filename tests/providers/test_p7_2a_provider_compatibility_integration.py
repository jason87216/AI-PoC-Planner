"""P7.2a representative governed_access compatibility coverage.

Live endpoint execution is deliberately opt-in.  The offline portion keeps the
fixture and deterministic expectations in one place while exercising both
capability declarations through the same structured-output executor.
"""

# ruff: noqa: E501

from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx
import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel

from ai_poc_planner.app.api import create_app
from ai_poc_planner.application.provider_readiness import ConnectionProbe
from ai_poc_planner.persistence.model_profiles import LocalModelProfileRepository
from ai_poc_planner.providers.base import ReasoningEffort, StructuredOutputMode
from ai_poc_planner.providers.capabilities import (
    AuthenticationMode,
    OpenAICompatibleCapabilities,
    ReasoningParameter,
    TokenParameter,
)
from ai_poc_planner.providers.errors import ProviderOperation
from ai_poc_planner.providers.openai_compatible import OpenAICompatibleChatAdapter
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
_NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
_NVIDIA_MODEL = "openai/gpt-oss-20b"


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


class LiveCallRecorder:
    """Record safe operation/schema/mode metadata only for a real UAT run."""

    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def record(self, *, operation: str, response_format: Any) -> None:
        request = response_format.as_request_value()
        schema_name = getattr(response_format, "name", None) or ""
        self.calls.append(
            {
                "operation": (
                    "report" if schema_name.startswith("report_") else operation
                ),
                "schema_name": schema_name,
                "mode": str(request["type"]),
            }
        )


class RecordingLiveAdapter:
    """Delegate to the real adapter without retaining prompts, keys, or responses."""

    def __init__(
        self,
        delegate: OpenAICompatibleChatAdapter,
        recorder: LiveCallRecorder,
        operation: str,
    ) -> None:
        self._delegate = delegate
        self._recorder = recorder
        self._operation = operation

    def complete(self, **kwargs: object) -> str:
        response_format = kwargs.get("response_format")
        self._recorder.record(
            operation=self._operation, response_format=response_format
        )
        return self._delegate.complete(**kwargs)


def _live_app(
    database_path: Path,
    profile_path: Path,
    recorder: LiveCallRecorder,
) -> tuple[Any, httpx.Client]:
    provider_client = httpx.Client(trust_env=False)

    def factory_for(operation: str, timeout_seconds: float):
        def factory(profile: ModelProfile) -> RecordingLiveAdapter:
            adapter = OpenAICompatibleChatAdapter(
                base_url=str(profile.base_url),
                model_name=profile.model_name,
                api_key=(
                    profile.api_key.get_secret_value()
                    if profile.api_key is not None
                    else None
                ),
                client=provider_client,
                timeout_seconds=timeout_seconds,
                reasoning_effort=profile.reasoning_effort,
                capabilities=profile.effective_capabilities,
            )
            return RecordingLiveAdapter(adapter, recorder, operation)

        return factory

    app = create_app(
        chat_model=GenericFakeChatModel(messages=iter(())),
        database_path=database_path,
        model_profile_repository=LocalModelProfileRepository(path=profile_path),
        connection_adapter_factory=factory_for("readiness", 10),
        interview_adapter_factory=factory_for("discovery", 300),
        analysis_adapter_factory=factory_for("analysis", 240),
        runtime_mode="uat",
    )
    return app, provider_client


def _assert_response(response: Any, status_code: int, label: str) -> Any:
    assert response.status_code == status_code, f"{label}: {response.text}"
    return response.json()


def _live_facts(client: TestClient, project_id: str) -> dict[str, dict[str, Any]]:
    body = _assert_response(
        client.get(f"/v1/projects/{project_id}/versions/1/facts"), 200, "facts"
    )
    return {item["fact_key"].strip().casefold(): item for item in body}


def _live_answers(
    client: TestClient,
    project_id: str,
    questions: list[dict[str, Any]],
    round_number: int,
) -> dict[str, Any]:
    facts = _live_facts(client, project_id)
    fixture_answers = GOVERNED_ACCESS["interview_answers"]
    answers = []
    question_keys = {
        str(question["fact_key"]).strip().casefold() for question in questions
    }
    for index, question in enumerate(questions):
        existing = facts.get(str(question["fact_key"]).strip().casefold())
        if existing is not None and existing["status"] == "confirmed":
            answer_status = "answered"
            answer = existing["value"]
        else:
            answer_status = "answered"
            answer = fixture_answers[(index + round_number - 1) % len(fixture_answers)][
                "answer"
            ]
        answers.append(
            {
                "question_id": question["id"],
                "answer_status": answer_status,
                "answer": answer,
            }
        )

    additional_facts = []
    for item in GOVERNED_ACCESS["facts"]:
        key = item["fact_key"].strip().casefold()
        if key in facts or key in question_keys:
            continue
        additional_facts.append(
            {
                "fact_key": item["fact_key"],
                "status": item["status"],
                "value": item["value"],
            }
        )
    return _assert_response(
        client.post(
            f"/v1/projects/{project_id}/versions/1/interview-answers",
            json={
                "answers": answers,
                "additional_facts": additional_facts,
                "supplementary_note": GOVERNED_ACCESS["understanding_correction"],
            },
        ),
        200,
        "interview answers",
    )


def _live_endpoint_config(endpoint: str) -> dict[str, Any]:
    if endpoint == "nvidia":
        if os.environ.get("AI_POC_PLANNER_P7_2A_NVIDIA_TEST") != "1":
            pytest.skip(
                "set AI_POC_PLANNER_P7_2A_NVIDIA_TEST=1 to run NVIDIA governed_access UAT"
            )
        api_key = os.environ.get("NVIDIA_API_KEY")
        if not api_key:
            pytest.skip("NVIDIA_API_KEY is required for NVIDIA governed_access UAT")
        return {
            "profile_name": "P7.2a NVIDIA governed_access",
            "base_url": _NVIDIA_BASE_URL,
            "model_name": _NVIDIA_MODEL,
            "api_key": api_key,
            "structured_output_mode": "json_schema",
            "reasoning_effort": "low",
            "capabilities": {
                "authentication": "bearer_required",
                "token_parameter": "max_tokens",
                "reasoning_parameter": "reasoning_effort",
                "json_schema": True,
                "json_object": True,
            },
        }

    if os.environ.get("AI_POC_PLANNER_P7_2A_LLAMA_CPP_TEST") != "1":
        pytest.skip(
            "set AI_POC_PLANNER_P7_2A_LLAMA_CPP_TEST=1 to run llama.cpp governed_access UAT"
        )
    base_url = os.environ.get("AI_POC_PLANNER_LLAMA_CPP_BASE_URL")
    model_name = os.environ.get("AI_POC_PLANNER_LLAMA_CPP_MODEL")
    if not base_url or not model_name:
        pytest.skip("llama.cpp base URL and model environment variables are required")
    json_schema = os.environ.get("AI_POC_PLANNER_LLAMA_CPP_JSON_SCHEMA") == "1"
    json_object = os.environ.get("AI_POC_PLANNER_LLAMA_CPP_JSON_OBJECT", "1") == "1"
    if not json_schema and not json_object:
        pytest.skip(
            "declare at least one llama.cpp structured-output capability with "
            "AI_POC_PLANNER_LLAMA_CPP_JSON_SCHEMA/JSON_OBJECT"
        )
    preferred = os.environ.get("AI_POC_PLANNER_LLAMA_CPP_PREFERRED_MODE")
    preferred = preferred or ("json_schema" if json_schema else "json_object")
    if (preferred == "json_schema" and not json_schema) or (
        preferred == "json_object" and not json_object
    ):
        pytest.skip("llama.cpp preferred mode must be one of its declared capabilities")
    return {
        "profile_name": "P7.2a llama.cpp governed_access",
        "base_url": base_url,
        "model_name": model_name,
        "api_key": os.environ.get("AI_POC_PLANNER_LLAMA_CPP_API_KEY"),
        "structured_output_mode": preferred,
        "reasoning_effort": None,
        "capabilities": {
            "authentication": "bearer_optional",
            "token_parameter": "max_tokens",
            "reasoning_parameter": "unsupported",
            "json_schema": json_schema,
            "json_object": json_object,
        },
    }


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


@pytest.mark.parametrize("endpoint", ["nvidia", "llama_cpp"])
def test_live_p7_2a_governed_access_public_api_flow(
    endpoint: str, tmp_path: Path
) -> None:
    config = _live_endpoint_config(endpoint)
    database_path = tmp_path / f"{endpoint}-governed-access.sqlite3"
    profile_path = tmp_path / f"{endpoint}-governed-access-profiles.json"
    recorder = LiveCallRecorder()
    app, provider_client = _live_app(database_path, profile_path, recorder)

    try:
        with TestClient(app) as client:
            created_profile = _assert_response(
                client.post("/v1/model-profiles", json=config),
                201,
                "create profile",
            )
            profile_id = created_profile["id"]
            assert "api_key" not in created_profile
            assert created_profile["capabilities"] == config["capabilities"]
            _assert_response(
                client.post(f"/v1/model-profiles/{profile_id}/select"),
                200,
                "select profile",
            )

            readiness = _assert_response(
                client.post(f"/v1/model-profiles/{profile_id}/test"),
                200,
                "readiness",
            )
            assert readiness["connection_state"] == "connected"
            assert readiness["mode_used"] in {"json_schema", "json_object"}
            assert readiness["fallback_used"] is False

            project = _assert_response(
                client.post(
                    "/v1/discovery-projects",
                    json={
                        **GOVERNED_ACCESS["initial_brief"],
                        "model_profile_id": profile_id,
                    },
                ),
                201,
                "create governed_access project",
            )
            project_id = project["project"]["id"]
            understanding_path = f"/v1/projects/{project_id}/versions/1/understanding"
            _assert_response(client.post(understanding_path), 200, "understanding")
            _assert_response(
                client.post(
                    f"{understanding_path}/feedback",
                    json={"feedback": GOVERNED_ACCESS["understanding_correction"]},
                ),
                200,
                "understanding feedback",
            )
            _assert_response(
                client.post(understanding_path), 200, "corrected understanding"
            )
            confirmed = _assert_response(
                client.post(f"{understanding_path}/confirm"),
                200,
                "understanding confirmation",
            )
            assert confirmed["status"] == "ready_for_interview"

            for round_number in range(1, 3):
                questions = _assert_response(
                    client.post(
                        f"/v1/projects/{project_id}/versions/1/interview-rounds"
                    ),
                    200,
                    f"interview round {round_number}",
                )
                if not questions:
                    break
                assert 1 <= len(questions) <= 3
                session = _live_answers(client, project_id, questions, round_number)
                if session["status"] == "ready_for_assessment":
                    break

            version = _assert_response(
                client.get(f"/v1/projects/{project_id}/versions/1"),
                200,
                "ready version",
            )
            assert version["status"] == "ready_for_assessment"

            before_analysis_duplicate = len(recorder.calls)
            analysis = _assert_response(
                client.post(f"/v1/projects/{project_id}/versions/1/analysis"),
                201,
                "analysis",
            )
            assert (
                analysis["case_centered"]["recommendation_category"]
                == (GOVERNED_ACCESS["expected"]["recommendation_category"])
            )
            assert (
                "主管保留最終核准"
                in GOVERNED_ACCESS["expected"]["human_decision_boundary"]
            )
            analysis_call_count = len(recorder.calls)
            assert analysis_call_count > before_analysis_duplicate
            duplicate_analysis = client.post(
                f"/v1/projects/{project_id}/versions/1/analysis"
            )
            assert duplicate_analysis.status_code == 409
            assert len(recorder.calls) == analysis_call_count

            report = _assert_response(
                client.post(f"/v1/projects/{project_id}/versions/1/report"),
                201,
                "report",
            )
            markdown = report["markdown"]
            assert markdown
            report_call_count = len(recorder.calls)
            duplicate_report = client.post(
                f"/v1/projects/{project_id}/versions/1/report"
            )
            assert duplicate_report.status_code == 409
            assert len(recorder.calls) == report_call_count

            assert (
                client.get(f"/v1/projects/{project_id}/versions/1/analysis").json()
                == analysis
            )
            assert (
                client.get(f"/v1/projects/{project_id}/versions/1/report").json()
                == report
            )
            assert client.get("/v1/projects").status_code == 200
            assert client.get(f"/v1/projects/{project_id}/versions").status_code == 200
            assert len(recorder.calls) == report_call_count
            assert {call["operation"] for call in recorder.calls} >= {
                "readiness",
                "discovery",
                "analysis",
                "report",
            }

        restart_recorder = LiveCallRecorder()
        restarted_app, restarted_provider_client = _live_app(
            database_path, profile_path, restart_recorder
        )
        try:
            with TestClient(restarted_app) as restarted:
                assert (
                    restarted.get(
                        f"/v1/projects/{project_id}/versions/1/analysis"
                    ).status_code
                    == 200
                )
                persisted_report = _assert_response(
                    restarted.get(f"/v1/projects/{project_id}/versions/1/report"),
                    200,
                    "reloaded report",
                )
                assert persisted_report["markdown"] == markdown
                assert restarted.get("/v1/projects").status_code == 200
                assert (
                    restarted.get(f"/v1/projects/{project_id}/versions").status_code
                    == 200
                )
                assert restart_recorder.calls == []
        finally:
            restarted_provider_client.close()

        dump = ""
        with sqlite3.connect(database_path) as connection:
            dump = "\n".join(str(row) for row in connection.iterdump()).casefold()
        for marker in (
            "authorization",
            "bearer ",
            "raw provider body marker",
            "synthetic system prompt marker",
        ):
            assert marker not in dump
        assert all(
            set(call) == {"operation", "schema_name", "mode"} for call in recorder.calls
        )
    finally:
        provider_client.close()
