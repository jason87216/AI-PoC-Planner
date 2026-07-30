"""P7.2a representative governed_access compatibility coverage.

Live endpoint execution is deliberately opt-in.  The offline portion keeps the
fixture and deterministic expectations in one place while exercising both
capability declarations through the same structured-output executor.
"""

# ruff: noqa: E501

from __future__ import annotations

import copy
import json
import os
import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
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
from ai_poc_planner.ui.results import markdown_download

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
_REQUIRED_DISCOVERY_FACT_KEYS = frozenset(
    {
        "permission_template_requirements",
        "required_field_validation",
        "application_workflow_state",
        "audit_trail_requirements",
    }
)
_GOVERNED_ACCESS_UAT_FACTS = (
    {
        "fact_key": "permission_template_requirements",
        "status": "confirmed",
        "value": "第一階段以已核准的職務與權限範本作為申請依據。",
    },
    {
        "fact_key": "required_field_validation",
        "status": "confirmed",
        "value": "送出申請時檢查必填欄位與已知的規則衝突。",
    },
    {
        "fact_key": "application_workflow_state",
        "status": "confirmed",
        "value": "申請必須保留待主管核准與待 IT 開通的工作流程狀態。",
    },
    {
        "fact_key": "audit_trail_requirements",
        "status": "confirmed",
        "value": "保留申請、規則結果、核准人與時間的稽核紀錄。",
    },
)


@dataclass(frozen=True)
class GovernedAccessDeterministicResult:
    """Normalized product facts returned by the production API."""

    recommendation_category: str
    decision_authority: str
    processing_boundary: str
    automatic_approval_allowed: bool
    direct_permission_write_allowed: bool
    unapproved_external_pii_allowed: bool
    high_risk_provisioning_allowed: bool
    required_prerequisites: tuple[str, ...]
    case_ids: tuple[str, ...]
    phase_names: tuple[str, ...]
    gate_dispositions: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class OperationCountMatrix:
    after_readiness: int
    after_discovery: int
    after_analysis: int
    after_duplicate_analysis: int
    after_report: int
    after_duplicate_report: int
    after_history: int
    after_markdown_download: int
    after_restart: int


@dataclass(frozen=True)
class SecurityEvidence:
    api_key_not_persisted: bool
    authorization_not_persisted: bool
    raw_provider_bodies_not_persisted: bool


@dataclass(frozen=True)
class LiveEndpointEvidence:
    """Safe evidence produced by one isolated governed-access endpoint run."""

    endpoint: str
    analysis: dict[str, Any]
    report: dict[str, Any]
    facts: dict[str, dict[str, Any]]
    normalized_result: GovernedAccessDeterministicResult
    recorder: OperationCallRecorder
    count_matrix: OperationCountMatrix
    security: SecurityEvidence
    database_path: Path
    profile_path: Path
    project_id: str


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


class OperationCallRecorder:
    """Record safe operation/schema/mode metadata only."""

    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def record(self, *, operation: str, response_format: Any) -> None:
        request = response_format.as_request_value()
        schema_name = getattr(response_format, "name", None) or ""
        self.calls.append(
            {
                "operation": "report"
                if schema_name.startswith("report_")
                else operation,
                "schema_name": schema_name,
                "mode": str(request["type"]),
            }
        )


class RawProviderBodyEvidence:
    """Keep exact provider bodies in process just long enough to check persistence."""

    def __init__(self) -> None:
        self._bodies: list[str] = []

    def capture(self, body: str) -> None:
        self._bodies.append(body)

    def assert_absent_from_database(self, database_path: Path) -> None:
        with sqlite3.connect(database_path) as connection:
            dump = "\n".join(str(row) for row in connection.iterdump()).casefold()
        assert self._bodies
        assert all(body.casefold() not in dump for body in self._bodies)

    def clear(self) -> None:
        self._bodies.clear()


class OfflineGovernedAccessAdapter:
    """Return bounded valid DTOs while the real public API owns the result."""

    def __init__(self) -> None:
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


class RecordingOfflineAdapter:
    """Attach a safe operation label to a deterministic offline script response."""

    def __init__(
        self,
        delegate: OfflineGovernedAccessAdapter,
        recorder: OperationCallRecorder,
        raw_bodies: RawProviderBodyEvidence,
        operation: str,
    ) -> None:
        self._delegate = delegate
        self._recorder = recorder
        self._raw_bodies = raw_bodies
        self._operation = operation

    def complete(self, **kwargs: object) -> str:
        response_format = kwargs.get("response_format")
        self._recorder.record(
            operation=self._operation, response_format=response_format
        )
        body = self._delegate.complete(**kwargs)
        self._raw_bodies.capture(body)
        return body


class RecordingLiveAdapter:
    """Delegate to the real adapter without retaining prompts, keys, or responses."""

    def __init__(
        self,
        delegate: OpenAICompatibleChatAdapter,
        recorder: OperationCallRecorder,
        raw_bodies: RawProviderBodyEvidence,
        operation: str,
    ) -> None:
        self._delegate = delegate
        self._recorder = recorder
        self._raw_bodies = raw_bodies
        self._operation = operation

    def complete(self, **kwargs: object) -> str:
        response_format = kwargs.get("response_format")
        self._recorder.record(
            operation=self._operation, response_format=response_format
        )
        body = self._delegate.complete(**kwargs)
        self._raw_bodies.capture(body)
        return body


def _live_app(
    database_path: Path,
    profile_path: Path,
    recorder: OperationCallRecorder,
    raw_bodies: RawProviderBodyEvidence,
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
            return RecordingLiveAdapter(adapter, recorder, raw_bodies, operation)

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
    for item in (*GOVERNED_ACCESS["facts"], *_GOVERNED_ACCESS_UAT_FACTS):
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


def _require_live_dual_endpoint_environment() -> None:
    """Skip both endpoints before creating either client when live UAT is unavailable."""

    missing: list[str] = []
    if os.environ.get("AI_POC_PLANNER_P7_2A_NVIDIA_TEST") != "1":
        missing.append("AI_POC_PLANNER_P7_2A_NVIDIA_TEST=1")
    if not os.environ.get("NVIDIA_API_KEY"):
        missing.append("NVIDIA_API_KEY")
    if os.environ.get("AI_POC_PLANNER_P7_2A_LLAMA_CPP_TEST") != "1":
        missing.append("AI_POC_PLANNER_P7_2A_LLAMA_CPP_TEST=1")
    if not os.environ.get("AI_POC_PLANNER_LLAMA_CPP_BASE_URL"):
        missing.append("AI_POC_PLANNER_LLAMA_CPP_BASE_URL")
    if not os.environ.get("AI_POC_PLANNER_LLAMA_CPP_MODEL"):
        missing.append("AI_POC_PLANNER_LLAMA_CPP_MODEL")
    json_schema = os.environ.get("AI_POC_PLANNER_LLAMA_CPP_JSON_SCHEMA") == "1"
    json_object = os.environ.get("AI_POC_PLANNER_LLAMA_CPP_JSON_OBJECT", "1") == "1"
    if not json_schema and not json_object:
        missing.append("llama.cpp structured-output capability")
    preferred = os.environ.get("AI_POC_PLANNER_LLAMA_CPP_PREFERRED_MODE")
    preferred = preferred or ("json_schema" if json_schema else "json_object")
    if (
        preferred not in {"json_schema", "json_object"}
        or (preferred == "json_schema" and not json_schema)
        or (preferred == "json_object" and not json_object)
    ):
        missing.append("valid llama.cpp preferred structured-output mode")
    if missing:
        pytest.skip(
            "live governed_access dual-endpoint gate unavailable: " + ", ".join(missing)
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


def _normalized_governed_access_result(
    analysis: Mapping[str, Any], facts: Mapping[str, Mapping[str, Any]]
) -> GovernedAccessDeterministicResult:
    """Read governed-access boundaries from structured production API fields."""

    case_centered = analysis.get("case_centered")
    assert isinstance(case_centered, Mapping)
    options = analysis.get("options")
    assert isinstance(options, list)
    recommended_option_key = analysis.get("recommended_option_key")
    selected = next(
        (
            option
            for option in options
            if isinstance(option, Mapping)
            and option.get("option_key") == recommended_option_key
        ),
        None,
    )
    assert isinstance(selected, Mapping)
    phased_path = case_centered.get("phased_path")
    assert isinstance(phased_path, list)
    first_phase = next(
        (
            phase
            for phase in phased_path
            if isinstance(phase, Mapping) and phase.get("phase_name") == "第一階段 PoC"
        ),
        None,
    )
    assert isinstance(first_phase, Mapping)
    not_doing = first_phase.get("not_doing")
    assert isinstance(not_doing, list)
    matched_cases = case_centered.get("matched_cases")
    assert isinstance(matched_cases, list)
    case_ids = tuple(
        str(item["case"]["case_id"])
        for item in matched_cases
        if isinstance(item, Mapping) and isinstance(item.get("case"), Mapping)
    )
    gate_results = analysis.get("gate_results")
    assert isinstance(gate_results, list)
    prerequisites = tuple(
        sorted(
            fact_key
            for fact_key, fact in facts.items()
            if fact_key in _REQUIRED_DISCOVERY_FACT_KEYS
            and fact.get("status") == "confirmed"
        )
    )
    return GovernedAccessDeterministicResult(
        recommendation_category=str(case_centered.get("recommendation_category")),
        decision_authority=str(selected.get("decision_authority")),
        processing_boundary=str(selected.get("processing_boundary")),
        automatic_approval_allowed=selected.get("decision_authority")
        == "autonomous_action",
        direct_permission_write_allowed="不直接寫入真實企業系統" not in not_doing,
        unapproved_external_pii_allowed=selected.get("processing_boundary")
        == "external_endpoint",
        high_risk_provisioning_allowed="不自主核准" not in not_doing,
        required_prerequisites=prerequisites,
        case_ids=case_ids,
        phase_names=tuple(
            str(phase["phase_name"])
            for phase in phased_path
            if isinstance(phase, Mapping) and isinstance(phase.get("phase_name"), str)
        ),
        gate_dispositions=tuple(
            (str(gate["rule_id"]), str(gate["disposition"]))
            for gate in gate_results
            if isinstance(gate, Mapping)
        ),
    )


def _assert_governed_access_deterministic_boundaries(
    result: GovernedAccessDeterministicResult,
) -> None:
    """Assert the deterministic policy and readiness boundaries, not narrative text."""

    assert result.recommendation_category == "rules_first"
    assert result.decision_authority == "human_final_decision"
    assert not result.automatic_approval_allowed
    assert not result.direct_permission_write_allowed
    assert not result.unapproved_external_pii_allowed
    assert not result.high_risk_provisioning_allowed
    assert set(result.required_prerequisites) == _REQUIRED_DISCOVERY_FACT_KEYS
    assert len(result.case_ids) == len(set(result.case_ids))
    assert "第一階段 PoC" in result.phase_names
    assert result.gate_dispositions


def _offline_app(
    database_path: Path,
    profile_path: Path,
    adapter: OfflineGovernedAccessAdapter,
    recorder: OperationCallRecorder,
    raw_bodies: RawProviderBodyEvidence,
) -> Any:
    def factory_for(operation: str):
        return lambda _: RecordingOfflineAdapter(
            adapter, recorder, raw_bodies, operation
        )

    return create_app(
        chat_model=GenericFakeChatModel(messages=iter(())),
        database_path=database_path,
        model_profile_repository=LocalModelProfileRepository(path=profile_path),
        connection_adapter_factory=factory_for("readiness"),
        interview_adapter_factory=factory_for("discovery"),
        analysis_adapter_factory=factory_for("analysis"),
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
    endpoint: str, root_path: Path
) -> LiveEndpointEvidence:
    """Run one isolated offline endpoint through the real FastAPI workflow."""

    root_path.mkdir(parents=True, exist_ok=True)
    adapter = OfflineGovernedAccessAdapter()
    recorder = OperationCallRecorder()
    raw_bodies = RawProviderBodyEvidence()
    database_path = root_path / f"{endpoint}-offline-governed-access.sqlite3"
    profile_path = root_path / f"{endpoint}-offline-governed-access-profiles.json"
    with TestClient(
        _offline_app(database_path, profile_path, adapter, recorder, raw_bodies)
    ) as client:
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
        after_readiness = len(recorder.calls)

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
        after_discovery = len(recorder.calls)
        analysis = _assert_response(
            client.post(f"/v1/projects/{project_id}/versions/1/analysis"),
            201,
            "offline analysis",
        )
        analysis_call_count = len(recorder.calls)
        assert analysis_call_count > after_discovery
        duplicate_analysis = client.post(
            f"/v1/projects/{project_id}/versions/1/analysis"
        )
        assert duplicate_analysis.status_code == 201
        assert duplicate_analysis.json() == analysis
        assert len(recorder.calls) == analysis_call_count

        report = _assert_response(
            client.post(f"/v1/projects/{project_id}/versions/1/report"),
            201,
            "offline report",
        )
        report_call_count = len(recorder.calls)
        duplicate_report = client.post(f"/v1/projects/{project_id}/versions/1/report")
        assert duplicate_report.status_code == 409
        assert len(recorder.calls) == report_call_count
        facts = _live_facts(client, project_id)
        normalized_result = _normalized_governed_access_result(analysis, facts)
        _assert_governed_access_deterministic_boundaries(normalized_result)

        # These are the same persisted API payloads consumed by Results and by
        # app_pages/results.py's st.download_button boundary.
        assert (
            client.get(f"/v1/projects/{project_id}/versions/1/analysis").json()
            == analysis
        )
        assert (
            client.get(f"/v1/projects/{project_id}/versions/1/report").json() == report
        )
        project_name = str(project["project"]["project_name"])
        first_download = markdown_download(report, project_name, 1)
        assert first_download.data.decode("utf-8") == report["markdown"]
        assert len(recorder.calls) == report_call_count

        # Refresh/history-style reads must remain read-only and must not invoke
        # the provider again.
        assert client.get("/v1/projects").status_code == 200
        assert client.get(f"/v1/projects/{project_id}/versions").status_code == 200
        assert (
            client.get(f"/v1/projects/{project_id}/versions/1/report").json() == report
        )
        refreshed_report = client.get(
            f"/v1/projects/{project_id}/versions/1/report"
        ).json()
        second_download = markdown_download(refreshed_report, project_name, 1)
        assert second_download == first_download
        after_history = len(recorder.calls)

    restart_adapter = OfflineGovernedAccessAdapter()
    restart_recorder = OperationCallRecorder()
    restart_raw_bodies = RawProviderBodyEvidence()
    with TestClient(
        _offline_app(
            database_path,
            profile_path,
            restart_adapter,
            restart_recorder,
            restart_raw_bodies,
        )
    ) as restarted:
        assert (
            restarted.get(f"/v1/projects/{project_id}/versions/1/analysis").json()
            == analysis
        )
        reloaded_report = _assert_response(
            restarted.get(f"/v1/projects/{project_id}/versions/1/report"),
            200,
            "offline restarted report",
        )
        assert reloaded_report == report
        reloaded_download = markdown_download(reloaded_report, project_name, 1)
        assert reloaded_download == first_download
        assert restarted.get("/v1/projects").status_code == 200
        assert restarted.get(f"/v1/projects/{project_id}/versions").status_code == 200
        assert restart_recorder.calls == []

    try:
        raw_bodies.assert_absent_from_database(database_path)
        with sqlite3.connect(database_path) as connection:
            dump = "\n".join(str(row) for row in connection.iterdump()).casefold()
        configured_key = _offline_endpoint_config(endpoint).get("api_key")
        assert not configured_key or str(configured_key).casefold() not in dump
        assert '"authorization":' not in dump
        assert "authorization: bearer" not in dump
        assert {call["operation"] for call in recorder.calls} >= {
            "readiness",
            "discovery",
            "analysis",
            "report",
        }
        return LiveEndpointEvidence(
            endpoint=endpoint,
            analysis=analysis,
            report=report,
            facts=facts,
            normalized_result=normalized_result,
            recorder=recorder,
            count_matrix=OperationCountMatrix(
                after_readiness=after_readiness,
                after_discovery=after_discovery,
                after_analysis=analysis_call_count,
                after_duplicate_analysis=analysis_call_count,
                after_report=report_call_count,
                after_duplicate_report=report_call_count,
                after_history=after_history,
                after_markdown_download=after_history,
                after_restart=len(restart_recorder.calls),
            ),
            security=SecurityEvidence(
                api_key_not_persisted=True,
                authorization_not_persisted=True,
                raw_provider_bodies_not_persisted=True,
            ),
            database_path=database_path,
            profile_path=profile_path,
            project_id=project_id,
        )
    finally:
        raw_bodies.clear()
        restart_raw_bodies.clear()


def test_offline_governed_access_public_api_matches_across_capability_profiles(
    tmp_path: Path,
) -> None:
    nvidia = _run_offline_governed_access("nvidia", tmp_path / "nvidia")
    llama = _run_offline_governed_access("llama_cpp", tmp_path / "llama_cpp")
    assert nvidia.normalized_result == llama.normalized_result
    for evidence in (nvidia, llama):
        assert all(
            set(call) == {"operation", "schema_name", "mode"}
            for call in evidence.recorder.calls
        )
        assert evidence.security == SecurityEvidence(True, True, True)
        assert {
            operation: sum(
                call["operation"] == operation for call in evidence.recorder.calls
            )
            for operation in {"readiness", "discovery", "analysis", "report"}
        } == {
            "readiness": 1,
            "discovery": 4,
            "analysis": 3,
            "report": 2,
        }
        assert evidence.count_matrix == OperationCountMatrix(
            after_readiness=1,
            after_discovery=5,
            after_analysis=8,
            after_duplicate_analysis=8,
            after_report=10,
            after_duplicate_report=10,
            after_history=10,
            after_markdown_download=10,
            after_restart=0,
        )


def test_governed_access_normalizer_rejects_each_policy_boundary(
    tmp_path: Path,
) -> None:
    """A structured API regression must fail without relying on report prose."""

    evidence = _run_offline_governed_access("nvidia", tmp_path / "negative")

    def assert_rejected(
        altered_analysis: dict[str, Any], altered_facts: dict[str, dict[str, Any]]
    ) -> None:
        with pytest.raises(AssertionError):
            _assert_governed_access_deterministic_boundaries(
                _normalized_governed_access_result(altered_analysis, altered_facts)
            )

    autonomous_analysis = copy.deepcopy(evidence.analysis)
    autonomous_selected = next(
        option
        for option in autonomous_analysis["options"]
        if option["option_key"] == autonomous_analysis["recommended_option_key"]
    )
    autonomous_selected["decision_authority"] = "autonomous_action"
    assert_rejected(autonomous_analysis, copy.deepcopy(evidence.facts))

    direct_write_analysis = copy.deepcopy(evidence.analysis)
    direct_write_phase = next(
        phase
        for phase in direct_write_analysis["case_centered"]["phased_path"]
        if phase["phase_name"] == "第一階段 PoC"
    )
    direct_write_phase["not_doing"].remove("不直接寫入真實企業系統")
    assert_rejected(direct_write_analysis, copy.deepcopy(evidence.facts))

    external_pii_analysis = copy.deepcopy(evidence.analysis)
    external_pii_selected = next(
        option
        for option in external_pii_analysis["options"]
        if option["option_key"] == external_pii_analysis["recommended_option_key"]
    )
    external_pii_selected["processing_boundary"] = "external_endpoint"
    assert_rejected(external_pii_analysis, copy.deepcopy(evidence.facts))

    high_risk_analysis = copy.deepcopy(evidence.analysis)
    high_risk_phase = next(
        phase
        for phase in high_risk_analysis["case_centered"]["phased_path"]
        if phase["phase_name"] == "第一階段 PoC"
    )
    high_risk_phase["not_doing"].remove("不自主核准")
    assert_rejected(high_risk_analysis, copy.deepcopy(evidence.facts))

    incomplete_prerequisites = copy.deepcopy(evidence.facts)
    incomplete_prerequisites.pop("audit_trail_requirements")
    assert_rejected(copy.deepcopy(evidence.analysis), incomplete_prerequisites)


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
    """Fixture-only contract check; it is not evidence from a UAT runtime."""

    expected = GOVERNED_ACCESS["expected"]
    assert expected["recommendation_category"] == "rules_first"
    assert "主管保留最終核准" in expected["human_decision_boundary"]
    assert "不得自動開通" in expected["deployment_constraint"]
    assert expected["must_not_have_conclusions"] == [
        "AI 自動核准",
        "AI 直接寫入權限",
        "將個人資料送到未核准外部服務",
    ]


def _run_live_governed_access(endpoint: str, root_path: Path) -> LiveEndpointEvidence:
    """Run one real endpoint in its own state, profile, client, and recorder."""

    config = _live_endpoint_config(endpoint)
    root_path.mkdir(parents=True, exist_ok=True)
    database_path = root_path / f"{endpoint}-governed-access.sqlite3"
    profile_path = root_path / f"{endpoint}-governed-access-profiles.json"
    recorder = OperationCallRecorder()
    raw_bodies = RawProviderBodyEvidence()
    app, provider_client = _live_app(database_path, profile_path, recorder, raw_bodies)

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
            after_readiness = len(recorder.calls)

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
            after_discovery = len(recorder.calls)

            analysis = _assert_response(
                client.post(f"/v1/projects/{project_id}/versions/1/analysis"),
                201,
                "analysis",
            )
            analysis_call_count = len(recorder.calls)
            assert analysis_call_count > after_discovery
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
            report_call_count = len(recorder.calls)
            duplicate_report = client.post(
                f"/v1/projects/{project_id}/versions/1/report"
            )
            assert duplicate_report.status_code == 409
            assert len(recorder.calls) == report_call_count
            facts = _live_facts(client, project_id)
            normalized_result = _normalized_governed_access_result(analysis, facts)
            _assert_governed_access_deterministic_boundaries(normalized_result)

            assert (
                client.get(f"/v1/projects/{project_id}/versions/1/analysis").json()
                == analysis
            )
            assert (
                client.get(f"/v1/projects/{project_id}/versions/1/report").json()
                == report
            )
            project_name = str(project["project"]["project_name"])
            first_download = markdown_download(report, project_name, 1)
            assert first_download.data.decode("utf-8") == report["markdown"]
            assert client.get("/v1/projects").status_code == 200
            assert client.get(f"/v1/projects/{project_id}/versions").status_code == 200
            refreshed_report = client.get(
                f"/v1/projects/{project_id}/versions/1/report"
            ).json()
            assert (
                markdown_download(refreshed_report, project_name, 1) == first_download
            )
            assert len(recorder.calls) == report_call_count
            after_history = len(recorder.calls)
            assert {call["operation"] for call in recorder.calls} >= {
                "readiness",
                "discovery",
                "analysis",
                "report",
            }

        restart_recorder = OperationCallRecorder()
        restart_raw_bodies = RawProviderBodyEvidence()
        restarted_app, restarted_provider_client = _live_app(
            database_path, profile_path, restart_recorder, restart_raw_bodies
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
                assert persisted_report == report
                assert (
                    markdown_download(persisted_report, project_name, 1)
                    == first_download
                )
                assert restarted.get("/v1/projects").status_code == 200
                assert (
                    restarted.get(f"/v1/projects/{project_id}/versions").status_code
                    == 200
                )
                assert restart_recorder.calls == []
        finally:
            restarted_provider_client.close()
            restart_raw_bodies.clear()

        raw_bodies.assert_absent_from_database(database_path)
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
        return LiveEndpointEvidence(
            endpoint=endpoint,
            analysis=analysis,
            report=report,
            facts=facts,
            normalized_result=normalized_result,
            recorder=recorder,
            count_matrix=OperationCountMatrix(
                after_readiness=after_readiness,
                after_discovery=after_discovery,
                after_analysis=analysis_call_count,
                after_duplicate_analysis=analysis_call_count,
                after_report=report_call_count,
                after_duplicate_report=report_call_count,
                after_history=after_history,
                after_markdown_download=after_history,
                after_restart=len(restart_recorder.calls),
            ),
            security=SecurityEvidence(
                api_key_not_persisted=True,
                authorization_not_persisted=True,
                raw_provider_bodies_not_persisted=True,
            ),
            database_path=database_path,
            profile_path=profile_path,
            project_id=project_id,
        )
    finally:
        raw_bodies.clear()
        provider_client.close()


def test_live_p7_2a_governed_access_public_api_flow(tmp_path: Path) -> None:
    """One all-or-nothing, two-endpoint real-provider compatibility gate."""

    _require_live_dual_endpoint_environment()
    nvidia = _run_live_governed_access("nvidia", tmp_path / "nvidia")
    llama = _run_live_governed_access("llama_cpp", tmp_path / "llama_cpp")

    assert nvidia.normalized_result == llama.normalized_result
    for evidence in (nvidia, llama):
        assert evidence.security == SecurityEvidence(True, True, True)
        assert evidence.count_matrix.after_restart == 0
        assert all(
            set(call) == {"operation", "schema_name", "mode"}
            for call in evidence.recorder.calls
        )
