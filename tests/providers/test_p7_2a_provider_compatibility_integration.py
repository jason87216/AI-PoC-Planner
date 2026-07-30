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
from ai_poc_planner.domain.planning_report import REPORT_SECTION_KEYS
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


class OfflineGovernedAccessAdapter:
    """Return bounded valid DTOs while the real public API owns the result."""

    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []
        self._interview_rounds = 0
        self._json_object_discovery_calls = 0

    def complete(
        self,
        *,
        messages: Sequence[Mapping[str, str]],
        temperature: float,
        max_tokens: int,
        response_format: Any,
        reasoning_effort: ReasoningEffort | None = None,
    ) -> str:
        del temperature, max_tokens, reasoning_effort
        request = response_format.as_request_value()
        schema_name = response_format.name or ""
        operation = "report" if schema_name.startswith("report_") else schema_name
        self.calls.append(
            {
                "operation": operation,
                "schema_name": schema_name,
                "mode": str(request["type"]),
            }
        )
        if schema_name == "connection_probe":
            return '{"status":"ok"}'
        json_object_understanding = (
            schema_name == "interview_round" and request["type"] == "json_object"
        )
        if schema_name == "requirement_understanding" or (
            json_object_understanding and self._json_object_discovery_calls < 2
        ):
            if json_object_understanding:
                self._json_object_discovery_calls += 1
            return json.dumps(
                {
                    "concise_requirement_summary": "先標準化權限申請流程，再評估後續輔助。",
                    "current_workflow_understanding": "目前以電子郵件與試算表處理申請。",
                    "desired_outcome_understanding": "減少漏填並提高規則檢查一致性。",
                    "available_data_understanding": "已有員工資料與既有權限清單。",
                    "users_and_owners_understanding": "主管核准，IT 負責實際開通。",
                    "known_constraints_understanding": "第一階段不得自動核准或直接寫入權限。",
                    "proposed_assumptions": [],
                    "detected_contradictions_or_ambiguities": [],
                },
                ensure_ascii=False,
            )
        if schema_name == "interview_round":
            if json_object_understanding:
                self._json_object_discovery_calls += 1
                round_number = self._json_object_discovery_calls - 2
            else:
                self._interview_rounds += 1
                round_number = self._interview_rounds
            if round_number == 1:
                return json.dumps(
                    {
                        "interview_complete": False,
                        "questions": [
                            {
                                "fact_key": "permission_process_detail",
                                "question": "第一階段要如何記錄申請與核准狀態？",
                                "why_it_matters": "用於界定流程與稽核驗收。",
                                "affected_judgement": "rules_first recommendation",
                                "example": "例如保留申請、核准人與時間。",
                            }
                        ],
                    },
                    ensure_ascii=False,
                )
            return '{"interview_complete":true,"questions":[]}'
        if schema_name == "analysis_options_a0":
            payload = json.loads(messages[-1]["content"])
            token = payload["fact_catalog"][0]["token"]
            return json.dumps(
                {
                    "recommended_option_index": 1,
                    "recommendation_rationale": "已確認需求以流程、規則與人工核准為主。",
                    "recommendation_fact_refs": [token],
                    "options": [
                        {
                            "option_title": "標準表單、固定規則檢查與人工核准",
                            "option_kind": "non_ai",
                            "summary": "先把申請欄位、規則與核准流程固定下來。",
                            "fact_refs": [token],
                        },
                        {
                            "option_title": "規則流程搭配受控 AI 輔助",
                            "option_kind": "hybrid",
                            "summary": "在治理條件完成後，再以 AI 輔助整理例外。",
                            "fact_refs": [token],
                        },
                    ],
                },
                ensure_ascii=False,
            )
        if schema_name == "analysis_option_detail":
            payload = json.loads(messages[-1]["content"])
            option = payload["option"]
            token = option["fact_refs"][0]
            body: dict[str, object] = {
                "expected_benefits": ["減少漏填並提高流程一致性。"],
                "limitations": ["仍需先整理規則、權限範本與例外流程。"],
                "prerequisites": ["確認申請欄位、權限範本與人工責任。"],
                "risks": ["錯誤權限不得由系統自動核准或開通。"],
                "human_review_points": ["主管保留最終核准，IT 負責實際開通。"],
                "fact_refs": [token],
                "decision_authority": "human_final_decision",
                "processing_boundary": "private_endpoint",
            }
            if option["option_kind"] == "non_ai":
                body["non_ai_directions"] = ["rule_based_automation"]
            else:
                body.update(
                    {
                        "opportunity_source_kind": "catalog",
                        "opportunity_type": "enterprise_knowledge_and_professional_document_assist",
                        "candidate_name": "受控申請輔助",
                        "opportunity_rationale": "僅在治理條件完成後協助整理例外。",
                        "candidate_definition": "以人工核准為前提的受控輔助。",
                        "why_existing_catalog_is_insufficient": "目前需求仍以規則流程為主。",
                        "non_ai_directions": ["rule_based_automation"],
                    }
                )
            return json.dumps(body, ensure_ascii=False)
        if schema_name in {"report_part_a", "report_part_b"}:
            sections = (
                REPORT_SECTION_KEYS[:9]
                if schema_name == "report_part_a"
                else REPORT_SECTION_KEYS[9:]
            )
            return json.dumps(
                {
                    key: {
                        "content": "以已確認事實補充受控的 PoC 說明。",
                        "fact_refs": ["F001"],
                    }
                    for key in sections
                },
                ensure_ascii=False,
            )
        raise AssertionError(f"unexpected offline schema: {schema_name}")


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


def _assert_governed_access_result(
    analysis: dict[str, Any], report: dict[str, Any]
) -> dict[str, Any]:
    """Validate product invariants from returned API data, not from the fixture."""

    case_centered = analysis.get("case_centered")
    assert isinstance(case_centered, dict)
    assert case_centered["recommendation_category"] == "rules_first"
    assert case_centered["recommendation_title"]
    matched_cases = case_centered.get("matched_cases")
    assert isinstance(matched_cases, list)
    case_ids = [item["case"]["case_id"] for item in matched_cases]
    assert len(case_ids) == len(set(case_ids))

    combined = json.dumps({"analysis": analysis, "report": report}, ensure_ascii=False)
    assert "主管保留最終核准" in combined
    assert "不得自動開通" in combined
    for required_terms in (
        ("權限範本", "職位—權限"),
        ("欄位", "申請欄位"),
        ("狀態", "流程"),
        ("稽核", "紀錄"),
    ):
        assert any(term in combined for term in required_terms), required_terms
    for forbidden in GOVERNED_ACCESS["expected"]["must_not_have_conclusions"]:
        assert forbidden.casefold() not in combined.casefold()

    markdown = str(report.get("markdown", ""))
    assert markdown
    assert markdown.startswith("# 專案評估報告")
    assert "## 4. 方案、成熟案例與專案差距比較" in markdown
    return {
        "recommendation_category": case_centered["recommendation_category"],
        "recommendation_title": case_centered["recommendation_title"],
        "case_ids": case_ids,
        "phase_names": [
            item["phase_name"] for item in case_centered.get("phased_path", [])
        ],
        "gate_dispositions": [
            (item["rule_id"], item["disposition"])
            for item in analysis.get("gate_results", [])
        ],
        "markdown_headings": [
            line for line in markdown.splitlines() if line.startswith("#")
        ],
    }


def _offline_app(
    database_path: Path,
    profile_path: Path,
    adapter: OfflineGovernedAccessAdapter,
) -> Any:
    return create_app(
        chat_model=GenericFakeChatModel(messages=iter(())),
        database_path=database_path,
        model_profile_repository=LocalModelProfileRepository(path=profile_path),
        connection_adapter_factory=lambda _: adapter,
        interview_adapter_factory=lambda _: adapter,
        analysis_adapter_factory=lambda _: adapter,
        runtime_mode="uat",
    )


def _offline_endpoint_config(endpoint: str) -> dict[str, Any]:
    if endpoint == "nvidia":
        return {
            "profile_name": "Offline NVIDIA governed_access",
            "base_url": "https://integrate.api.nvidia.com/v1",
            "model_name": "offline-nvidia-model",
            "api_key": "offline-nvidia-key",
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
    return {
        "profile_name": "Offline llama.cpp governed_access",
        "base_url": "http://127.0.0.1:8080/v1",
        "model_name": "offline-llama-model",
        "api_key": None,
        "structured_output_mode": "json_object",
        "reasoning_effort": None,
        "capabilities": {
            "authentication": "bearer_optional",
            "token_parameter": "max_tokens",
            "reasoning_parameter": "unsupported",
            "json_schema": False,
            "json_object": True,
        },
    }


def _run_offline_governed_access(
    endpoint: str, tmp_path: Path
) -> tuple[dict[str, Any], dict[str, Any], OfflineGovernedAccessAdapter, str, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    adapter = OfflineGovernedAccessAdapter()
    database_path = tmp_path / f"{endpoint}-offline-governed-access.sqlite3"
    profile_path = tmp_path / f"{endpoint}-offline-governed-access-profiles.json"
    with TestClient(_offline_app(database_path, profile_path, adapter)) as client:
        profile = _assert_response(
            client.post("/v1/model-profiles", json=_offline_endpoint_config(endpoint)),
            201,
            "offline create profile",
        )
        profile_id = profile["id"]
        _assert_response(
            client.post(f"/v1/model-profiles/{profile_id}/select"),
            200,
            "offline select profile",
        )
        readiness = _assert_response(
            client.post(f"/v1/model-profiles/{profile_id}/test"),
            200,
            "offline readiness",
        )
        assert readiness["connection_state"] == "connected"

        project = _assert_response(
            client.post(
                "/v1/discovery-projects",
                json={
                    **GOVERNED_ACCESS["initial_brief"],
                    "model_profile_id": profile_id,
                },
            ),
            201,
            "offline create project",
        )
        project_id = project["project"]["id"]
        understanding_path = f"/v1/projects/{project_id}/versions/1/understanding"
        _assert_response(client.post(understanding_path), 200, "offline understanding")
        _assert_response(
            client.post(
                f"{understanding_path}/feedback",
                json={"feedback": GOVERNED_ACCESS["understanding_correction"]},
            ),
            200,
            "offline understanding feedback",
        )
        _assert_response(
            client.post(understanding_path), 200, "offline corrected understanding"
        )
        confirmed = _assert_response(
            client.post(f"{understanding_path}/confirm"),
            200,
            "offline understanding confirmation",
        )
        assert confirmed["status"] == "ready_for_interview"

        for round_number in range(1, 3):
            questions = _assert_response(
                client.post(f"/v1/projects/{project_id}/versions/1/interview-rounds"),
                200,
                f"offline interview round {round_number}",
            )
            if not questions:
                break
            session = _live_answers(client, project_id, questions, round_number)
            if session["status"] == "ready_for_assessment":
                break

        version = _assert_response(
            client.get(f"/v1/projects/{project_id}/versions/1"),
            200,
            "offline ready version",
        )
        assert version["status"] == "ready_for_assessment"
        before_analysis = len(adapter.calls)
        analysis = _assert_response(
            client.post(f"/v1/projects/{project_id}/versions/1/analysis"),
            201,
            "offline analysis",
        )
        analysis_call_count = len(adapter.calls)
        assert analysis_call_count > before_analysis
        duplicate_analysis = client.post(
            f"/v1/projects/{project_id}/versions/1/analysis"
        )
        assert duplicate_analysis.status_code == 201
        assert duplicate_analysis.json() == analysis
        assert len(adapter.calls) == analysis_call_count

        report = _assert_response(
            client.post(f"/v1/projects/{project_id}/versions/1/report"),
            201,
            "offline report",
        )
        report_call_count = len(adapter.calls)
        duplicate_report = client.post(f"/v1/projects/{project_id}/versions/1/report")
        assert duplicate_report.status_code == 409
        assert len(adapter.calls) == report_call_count
        _assert_governed_access_result(analysis, report)

        # These are the same persisted API payloads consumed by Results and by
        # app_pages/results.py's st.download_button boundary.
        assert (
            client.get(f"/v1/projects/{project_id}/versions/1/analysis").json()
            == analysis
        )
        assert (
            client.get(f"/v1/projects/{project_id}/versions/1/report").json() == report
        )
        first_download = str(report["markdown"]).encode("utf-8")
        assert first_download.decode("utf-8") == report["markdown"]
        assert len(adapter.calls) == report_call_count

        # Refresh/history-style reads must remain read-only and must not invoke
        # the provider again.
        assert client.get("/v1/projects").status_code == 200
        assert client.get(f"/v1/projects/{project_id}/versions").status_code == 200
        assert (
            client.get(f"/v1/projects/{project_id}/versions/1/report").json() == report
        )
        second_download = str(
            client.get(f"/v1/projects/{project_id}/versions/1/report").json()[
                "markdown"
            ]
        ).encode("utf-8")
        assert second_download == first_download
        assert len(adapter.calls) == report_call_count

    return analysis, report, adapter, project_id, database_path


def test_offline_governed_access_public_api_matches_across_capability_profiles(
    tmp_path: Path,
) -> None:
    nvidia = _run_offline_governed_access("nvidia", tmp_path / "nvidia")
    llama = _run_offline_governed_access("llama_cpp", tmp_path / "llama_cpp")
    assert _assert_governed_access_result(
        nvidia[0], nvidia[1]
    ) == _assert_governed_access_result(llama[0], llama[1])
    for _, _, adapter, _, database_path in (nvidia, llama):
        assert all(
            set(call) == {"operation", "schema_name", "mode"} for call in adapter.calls
        )
        with sqlite3.connect(database_path) as connection:
            dump = "\n".join(str(row) for row in connection.iterdump()).casefold()
        for marker in (
            '"authorization":',
            "authorization: bearer",
            "offline-nvidia-key",
            "raw provider body",
        ):
            assert marker not in dump


def test_governed_access_result_helper_rejects_missing_product_invariant() -> None:
    valid_analysis = {
        "case_centered": {
            "recommendation_category": "rules_first",
            "recommendation_title": "權限申請標準化、規則檢查與人工核准",
            "matched_cases": [],
            "phased_path": [],
        },
        "gate_results": [],
    }
    valid_report = {
        "markdown": (
            "# 專案評估報告\n## 4. 方案、成熟案例與專案差距比較\n"
            "主管保留最終核准；不得自動開通；權限範本；欄位；狀態；稽核紀錄"
        )
    }
    _assert_governed_access_result(valid_analysis, valid_report)
    invalid = json.loads(json.dumps(valid_report, ensure_ascii=False))
    invalid["markdown"] = invalid["markdown"].replace("稽核紀錄", "")
    with pytest.raises(AssertionError):
        _assert_governed_access_result(valid_analysis, invalid)


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
            analysis_call_count = len(recorder.calls)
            assert analysis_call_count > before_analysis_duplicate
            duplicate_analysis = client.post(
                f"/v1/projects/{project_id}/versions/1/analysis"
            )
            assert duplicate_analysis.status_code == 201
            assert duplicate_analysis.json() == analysis
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
            _assert_governed_access_result(analysis, report)

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
        configured_key = config.get("api_key")
        if isinstance(configured_key, str) and configured_key:
            assert configured_key.casefold() not in dump
        for marker in (
            '"authorization":',
            "authorization: bearer",
        ):
            assert marker not in dump
        assert all(
            set(call) == {"operation", "schema_name", "mode"} for call in recorder.calls
        )
    finally:
        provider_client.close()
