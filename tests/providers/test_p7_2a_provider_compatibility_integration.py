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
from collections.abc import Callable, Mapping, Sequence
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
from ai_poc_planner.application import planning_report as planning_report_module
from ai_poc_planner.application.provider_readiness import ConnectionProbe
from ai_poc_planner.config import provider_readiness_timeout_seconds
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
_EXPECTED_GOVERNED_ACCESS_PHASE_NAMES = frozenset(
    GOVERNED_ACCESS["expected"]["must_have_phase_names"]
)
# Derived from assessment/gates.py using governed_access confirmed facts and the
# deterministic human-final-decision/private-endpoint selected option.
_EXPECTED_GOVERNED_ACCESS_GATE_MATRIX = (
    ("HG-01", "blocked"),
    ("HG-03", "assistive_only"),
    ("HG-05", "requires_controls"),
    ("HG-06", "requires_controls"),
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

    matching_status: str
    no_case_reason: str | None
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
    gate_impact_rule_ids: tuple[str, ...]
    first_phase_prohibits_direct_write: bool
    first_phase_prohibits_autonomous_approval: bool


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
    adapter_content_not_persisted: bool | None
    http_response_bodies_not_persisted: bool | None


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
    report_executor_records: tuple[dict[str, object], ...] = ()
    report_semantic_passes: tuple[int, ...] = ()
    deterministic_fallback_invoked: bool = False


@dataclass
class ReportExecutionObservation:
    """Safe report-only observability; never stores prompts or model output."""

    executor_records: list[dict[str, object]]
    semantic_passes: set[int]
    deterministic_fallback_invoked: bool = False


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
        self.budget_calls: list[dict[str, object]] = []

    def record(
        self,
        *,
        operation: str,
        response_format: Any,
        max_tokens: int | None = None,
    ) -> None:
        request = response_format.as_request_value()
        schema_name = getattr(response_format, "name", None) or ""
        call = {
            "operation": "report" if schema_name.startswith("report_") else operation,
            "schema_name": schema_name,
            "mode": str(request["type"]),
        }
        self.calls.append(call)
        if max_tokens is not None:
            self.budget_calls.append({**call, "max_tokens": max_tokens})


def _sqlite_text_or_blob_cells(database_path: Path) -> list[str | bytes]:
    """Read actual TEXT/BLOB cells from every user table without SQL dump rendering."""

    def quote(identifier: str) -> str:
        return '"' + identifier.replace('"', '""') + '"'

    values: list[str | bytes] = []
    with sqlite3.connect(database_path) as connection:
        table_rows = connection.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        for (table_name,) in table_rows:
            columns = connection.execute(
                f"PRAGMA table_info({quote(str(table_name))})"
            ).fetchall()
            for _, column_name, *_ in columns:
                cells = connection.execute(
                    f"SELECT {quote(str(column_name))} "
                    f"FROM {quote(str(table_name))} "
                    f"WHERE typeof({quote(str(column_name))}) IN ('text', 'blob')"
                ).fetchall()
                values.extend(
                    cell for (cell,) in cells if isinstance(cell, (str, bytes))
                )
    return values


def _assert_exact_bodies_absent_from_database_cells(
    database_path: Path, bodies: Sequence[bytes]
) -> None:
    """Reject only a full response persisted as one TEXT/BLOB value, not substrings."""

    cells = _sqlite_text_or_blob_cells(database_path)
    assert bodies
    for body in bodies:
        assert all(
            cell != body
            and (
                not isinstance(cell, str)
                or cell != body.decode("utf-8", errors="surrogateescape")
            )
            for cell in cells
        )


def _assert_text_markers_absent_from_database_cells(
    database_path: Path, markers: Sequence[str]
) -> None:
    """Check configured secrets and authorization markers without SQL rendering."""

    cells = _sqlite_text_or_blob_cells(database_path)
    normalized_cells = [
        cell.casefold()
        if isinstance(cell, str)
        else cell.decode("utf-8", errors="surrogateescape").casefold()
        for cell in cells
    ]
    for marker in markers:
        assert all(marker.casefold() not in cell for cell in normalized_cells)


class ProviderContentEvidence:
    """Keep adapter-returned content in process for the offline fixture only."""

    def __init__(self) -> None:
        self._contents: list[str] = []

    def capture(self, content: str) -> None:
        self._contents.append(content)

    def assert_absent_from_database_cells(self, database_path: Path) -> None:
        _assert_exact_bodies_absent_from_database_cells(
            database_path, [content.encode("utf-8") for content in self._contents]
        )

    def clear(self) -> None:
        self._contents.clear()


class HttpResponseBodyEvidence:
    """Capture HTTP response bytes only in a test-only client response hook."""

    def __init__(self) -> None:
        self._bodies: list[bytes] = []

    @property
    def response_count(self) -> int:
        return len(self._bodies)

    def capture_response(self, response: httpx.Response) -> None:
        response.read()
        self._bodies.append(bytes(response.content))

    def assert_absent_from_database_cells(self, database_path: Path) -> None:
        _assert_exact_bodies_absent_from_database_cells(database_path, self._bodies)

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
        provider_content: ProviderContentEvidence,
        operation: str,
    ) -> None:
        self._delegate = delegate
        self._recorder = recorder
        self._provider_content = provider_content
        self._operation = operation

    def complete(self, **kwargs: object) -> str:
        response_format = kwargs.get("response_format")
        self._recorder.record(
            operation=self._operation,
            response_format=response_format,
            max_tokens=int(kwargs["max_tokens"]),
        )
        body = self._delegate.complete(**kwargs)
        self._provider_content.capture(body)
        return body


class RecordingLiveAdapter:
    """Delegate to the real adapter while recording safe call metadata only."""

    def __init__(
        self,
        delegate: OpenAICompatibleChatAdapter,
        recorder: OperationCallRecorder,
        operation: str,
    ) -> None:
        self._delegate = delegate
        self._recorder = recorder
        self._operation = operation

    def complete(self, **kwargs: object) -> str:
        response_format = kwargs.get("response_format")
        self._recorder.record(
            operation=self._operation,
            response_format=response_format,
            max_tokens=int(kwargs["max_tokens"]),
        )
        return self._delegate.complete(**kwargs)


def _live_app(
    database_path: Path,
    profile_path: Path,
    recorder: OperationCallRecorder,
    http_response_bodies: HttpResponseBodyEvidence,
) -> tuple[Any, httpx.Client]:
    provider_client = httpx.Client(
        trust_env=False,
        event_hooks={"response": [http_response_bodies.capture_response]},
    )

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

    readiness_timeout = provider_readiness_timeout_seconds()

    app = create_app(
        chat_model=GenericFakeChatModel(messages=iter(())),
        database_path=database_path,
        model_profile_repository=LocalModelProfileRepository(path=profile_path),
        connection_adapter_factory=factory_for("readiness", readiness_timeout),
        interview_adapter_factory=factory_for("discovery", 300),
        analysis_adapter_factory=factory_for("analysis", 240),
        runtime_mode="uat",
    )
    return app, provider_client


def _run_live_endpoint_pair(
    root_path: Path,
    runner: Callable[[str, Path], LiveEndpointEvidence],
) -> tuple[LiveEndpointEvidence, LiveEndpointEvidence]:
    """Run the local compatibility gate before the remote NVIDIA endpoint."""

    llama = runner("llama_cpp", root_path / "llama_cpp")
    nvidia = runner("nvidia", root_path / "nvidia")
    return llama, nvidia


def _assert_response(response: Any, status_code: int, label: str) -> Any:
    assert response.status_code == status_code, f"{label}: {response.text}"
    return response.json()


_SAFE_LIVE_OPERATION_CODES = frozenset(
    {
        "provider_auth_required",
        "provider_auth_failed",
        "provider_parameter_unsupported",
        "provider_structured_output_unsupported",
        "provider_not_found",
        "provider_timeout",
        "provider_connection_failed",
        "provider_rate_limited",
        "provider_unavailable",
        "provider_http_error",
        "provider_invalid_response",
        "provider_output_truncated",
        "provider_output_invalid",
        "provider_schema_invalid",
    }
)
_SAFE_LIVE_OPERATIONS = frozenset({"readiness", "discovery", "analysis", "report"})


def _begin_report_observability() -> tuple[
    ReportExecutionObservation,
    tuple[Callable[..., Any], Callable[..., Any], Callable[..., Any]],
]:
    """Install temporary report metadata hooks without capturing sensitive data."""

    observation = ReportExecutionObservation(executor_records=[], semantic_passes=set())
    original_execute = StructuredOutputExecutor.execute
    original_call = planning_report_module.PlanningReportService._call
    original_fallback = planning_report_module._fallback_report_draft

    def wrapped_execute(executor: StructuredOutputExecutor, *args: Any, **kwargs: Any):
        if kwargs.get("operation") is not ProviderOperation.REPORT:
            return original_execute(executor, *args, **kwargs)
        schema_name = str(kwargs.get("schema_name", ""))
        logical_max_tokens = kwargs.get("logical_max_tokens")
        try:
            result = original_execute(executor, *args, **kwargs)
        except Exception as error:
            safe_code = getattr(error, "code", None)
            if safe_code not in _SAFE_LIVE_OPERATION_CODES:
                safe_code = "unknown_safe_code"
            observation.executor_records.append(
                {
                    "operation": "report",
                    "schema_name": schema_name,
                    "logical_max_tokens": logical_max_tokens,
                    "success": False,
                    "attempt_count": None,
                    "mode_used": None,
                    "fallback_used": False,
                    "safe_failure_code": safe_code,
                    "retryable": getattr(error, "retryable", None),
                }
            )
            raise
        observation.executor_records.append(
            {
                "operation": "report",
                "schema_name": schema_name,
                "logical_max_tokens": logical_max_tokens,
                "success": True,
                "attempt_count": result.attempt_count,
                "mode_used": getattr(result.mode_used, "value", str(result.mode_used)),
                "fallback_used": result.fallback_used,
                "safe_failure_code": None,
                "retryable": None,
            }
        )
        return result

    def wrapped_call(
        service: Any,
        profile: Any,
        payload: dict[str, object],
        contract: Any,
        name: str,
        *,
        semantic_repair: bool = False,
    ):
        if name in {"report_part_a", "report_part_b"}:
            observation.semantic_passes.add(2 if semantic_repair else 1)
        return original_call(
            service,
            profile,
            payload,
            contract,
            name,
            semantic_repair=semantic_repair,
        )

    def wrapped_fallback(*args: Any, **kwargs: Any):
        observation.deterministic_fallback_invoked = True
        return original_fallback(*args, **kwargs)

    StructuredOutputExecutor.execute = wrapped_execute
    planning_report_module.PlanningReportService._call = wrapped_call
    planning_report_module._fallback_report_draft = wrapped_fallback
    return observation, (original_execute, original_call, original_fallback)


def _end_report_observability(
    originals: tuple[Callable[..., Any], Callable[..., Any], Callable[..., Any]],
) -> None:
    original_execute, original_call, original_fallback = originals
    StructuredOutputExecutor.execute = original_execute
    planning_report_module.PlanningReportService._call = original_call
    planning_report_module._fallback_report_draft = original_fallback


def _assert_live_operation_response(
    response: Any,
    expected_status: int,
    *,
    endpoint: str,
    label: str,
    recorder: OperationCallRecorder,
) -> Any:
    """Assert a live operation without exposing provider/API response bodies."""

    if response.status_code == expected_status:
        try:
            return response.json()
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            raise AssertionError(
                f"endpoint={endpoint}; label={label}; HTTP status={response.status_code}; "
                f"safe_error_contract=false; last_operation="
                f"{recorder.calls[-1].get('operation') if recorder.calls else None}; "
                f"schema_name={recorder.calls[-1].get('schema_name') if recorder.calls else None}; "
                f"mode={recorder.calls[-1].get('mode') if recorder.calls else None}; "
                f"recorder_call_count={len(recorder.calls)}"
            ) from error

    safe_error_contract = False
    error_code: str | None = None
    operation: str | None = None
    retryable: bool | None = None
    try:
        body = response.json()
    except (TypeError, ValueError, json.JSONDecodeError):
        body = None
    if isinstance(body, Mapping):
        error = body.get("error")
        details = error.get("details") if isinstance(error, Mapping) else None
        candidate_code = error.get("code") if isinstance(error, Mapping) else None
        candidate_operation = (
            details.get("operation") if isinstance(details, Mapping) else None
        )
        candidate_retryable = (
            details.get("retryable") if isinstance(details, Mapping) else None
        )
        if (
            isinstance(candidate_code, str)
            and candidate_code in _SAFE_LIVE_OPERATION_CODES
            and isinstance(candidate_operation, str)
            and candidate_operation in _SAFE_LIVE_OPERATIONS
            and isinstance(candidate_retryable, bool)
        ):
            safe_error_contract = True
            error_code = candidate_code
            operation = candidate_operation
            retryable = candidate_retryable

    last_call = recorder.calls[-1] if recorder.calls else {}
    raise AssertionError(
        f"endpoint={endpoint}; label={label}; HTTP status={response.status_code}; "
        f"safe_error_contract={safe_error_contract}; error.code={error_code}; "
        f"operation={operation}; retryable={retryable}; "
        f"last_operation={last_call.get('operation')}; "
        f"schema_name={last_call.get('schema_name')}; mode={last_call.get('mode')}; "
        f"recorder_call_count={len(recorder.calls)}"
    )


def _assert_readiness_connected(readiness: Mapping[str, Any], endpoint: str) -> None:
    """Assert readiness while exposing only the public safe failure metadata."""

    if readiness.get("connection_state") != "connected":
        failure = readiness.get("failure")
        failure_mapping = failure if isinstance(failure, Mapping) else {}
        raise AssertionError(
            f"endpoint={endpoint}; "
            f"connection_state={readiness.get('connection_state')}; "
            f"failure.code={failure_mapping.get('code')}; "
            f"failure.operation={failure_mapping.get('operation')}; "
            f"failure.retryable={failure_mapping.get('retryable')}; "
            f"mode_used={readiness.get('mode_used')}; "
            f"fallback_used={readiness.get('fallback_used')}"
        )
    assert readiness.get("mode_used") in {"json_schema", "json_object"}
    assert readiness.get("fallback_used") is False


def test_readiness_failure_assertion_exposes_only_safe_metadata() -> None:
    raw_marker = "raw-response-marker-p72a"
    message = "authorization-marker-p72a"
    readiness = {
        "connection_state": "failed",
        "failure": {
            "code": "provider_timeout",
            "operation": "readiness",
            "retryable": True,
            "user_action": message,
            "raw": raw_marker,
        },
        "mode_used": None,
        "fallback_used": False,
        "content": raw_marker,
        "reasoning_content": raw_marker,
    }

    with pytest.raises(AssertionError) as error:
        _assert_readiness_connected(readiness, "llama_cpp")

    text = str(error.value)
    assert "endpoint=llama_cpp" in text
    assert "connection_state=failed" in text
    assert "failure.code=provider_timeout" in text
    assert "failure.operation=readiness" in text
    assert "failure.retryable=True" in text
    assert "mode_used=None" in text
    assert "fallback_used=False" in text
    assert raw_marker not in text
    assert message not in text


def test_readiness_connected_assertion_accepts_safe_success_contract() -> None:
    _assert_readiness_connected(
        {
            "connection_state": "connected",
            "mode_used": "json_object",
            "fallback_used": False,
        },
        "llama_cpp",
    )


def test_live_analysis_failure_assertion_exposes_only_safe_metadata() -> None:
    recorder = OperationCallRecorder()
    recorder.calls.append(
        {
            "operation": "analysis",
            "schema_name": "analysis_option_detail",
            "mode": "json_schema",
        }
    )
    marker = "raw-provider-response-marker-p72a"
    response = httpx.Response(
        502,
        json={
            "error": {
                "code": "provider_output_truncated",
                "message": marker,
                "details": {
                    "operation": "analysis",
                    "retryable": False,
                    "user_action": "secret-action-marker-p72a",
                },
            }
        },
    )

    with pytest.raises(AssertionError) as error:
        _assert_live_operation_response(
            response,
            201,
            endpoint="llama_cpp",
            label="analysis",
            recorder=recorder,
        )

    text = str(error.value)
    assert "endpoint=llama_cpp" in text
    assert "label=analysis" in text
    assert "HTTP status=502" in text
    assert "provider_output_truncated" in text
    assert "operation=analysis" in text
    assert "retryable=False" in text
    assert "schema_name=analysis_option_detail" in text
    assert "mode=json_schema" in text
    assert "recorder_call_count=1" in text
    assert marker not in text
    assert "secret-action-marker-p72a" not in text


def test_live_report_failure_assertion_exposes_last_report_schema() -> None:
    recorder = OperationCallRecorder()
    recorder.calls.append(
        {
            "operation": "report",
            "schema_name": "report_part_a",
            "mode": "json_schema",
        }
    )
    response = httpx.Response(
        502,
        json={
            "error": {
                "code": "provider_invalid_response",
                "details": {"operation": "report", "retryable": False},
            }
        },
    )

    with pytest.raises(AssertionError, match="schema_name=report_part_a"):
        _assert_live_operation_response(
            response,
            201,
            endpoint="llama_cpp",
            label="report",
            recorder=recorder,
        )


def test_live_operation_non_json_failure_does_not_expose_body() -> None:
    recorder = OperationCallRecorder()
    marker = "raw-body-marker-p72a"
    response = httpx.Response(502, content=marker.encode("utf-8"))

    with pytest.raises(AssertionError) as error:
        _assert_live_operation_response(
            response,
            201,
            endpoint="llama_cpp",
            label="analysis",
            recorder=recorder,
        )

    text = str(error.value)
    assert "safe_error_contract=False" in text
    assert marker not in text


def test_live_operation_success_returns_json_without_extra_metadata() -> None:
    recorder = OperationCallRecorder()
    response = httpx.Response(201, json={"ok": True})

    assert _assert_live_operation_response(
        response,
        201,
        endpoint="llama_cpp",
        label="analysis",
        recorder=recorder,
    ) == {"ok": True}


def test_offline_governed_access_preserves_stage_specific_token_budgets(
    tmp_path: Path,
) -> None:
    evidence = _run_offline_governed_access("llama_cpp", tmp_path / "budget")
    budgets = evidence.recorder.budget_calls

    assert [
        item["max_tokens"] for item in budgets if item["operation"] == "readiness"
    ] == [256]
    assert [
        item["max_tokens"] for item in budgets if item["operation"] == "discovery"
    ] == [
        4096,
        4096,
        4096,
        4096,
    ]
    analysis_budgets = [
        (item["schema_name"], item["max_tokens"])
        for item in budgets
        if item["operation"] == "analysis"
    ]
    assert analysis_budgets == [
        ("analysis_options_a0", 1024),
        ("analysis_option_detail", 2048),
        ("analysis_option_detail", 2048),
    ]
    assert [
        item["max_tokens"] for item in budgets if item["operation"] == "report"
    ] == [
        2048,
        2048,
    ]
    assert len([item for item in budgets if item["operation"] == "analysis"]) == 3


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


def _live_profile_contract(config: Mapping[str, Any], profile_id: int) -> ModelProfile:
    """Validate the same profile contract that the live API will persist later."""

    return ModelProfile.model_validate(
        {
            "id": UUID(int=profile_id),
            **config,
            "is_selected": True,
            "is_enabled": True,
            "created_at": NOW,
            "updated_at": NOW,
        }
    )


def _preflight_live_dual_endpoints() -> None:
    """Run only cheap discovery before the local full compatibility gate."""

    nvidia_config = _live_endpoint_config("nvidia")
    llama_config = _live_endpoint_config("llama_cpp")
    _live_profile_contract(nvidia_config, 91)
    _live_profile_contract(llama_config, 92)

    response_bodies = HttpResponseBodyEvidence()
    llama_client = httpx.Client(
        trust_env=False,
        event_hooks={"response": [response_bodies.capture_response]},
    )
    try:
        response = llama_client.get(
            f"{str(llama_config['base_url']).rstrip('/')}/models", timeout=10
        )
        if response.is_error:
            pytest.fail(
                "llama.cpp model discovery did not return a successful response"
            )
        payload = response.json()
        models = payload.get("data") if isinstance(payload, Mapping) else None
        if not isinstance(models, list) or not any(
            isinstance(model, Mapping) and model.get("id") == llama_config["model_name"]
            for model in models
        ):
            pytest.fail("llama.cpp model discovery did not list the configured model")
    finally:
        response_bodies.clear()
        llama_client.close()


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
    gate_dispositions = tuple(
        (str(gate["rule_id"]), str(gate["disposition"]))
        for gate in gate_results
        if isinstance(gate, Mapping)
    )
    gate_impacts = case_centered.get("gate_impacts")
    assert isinstance(gate_impacts, list)
    gate_impact_rule_ids = tuple(
        str(impact["rule_id"]) for impact in gate_impacts if isinstance(impact, Mapping)
    )
    enterprise_action_blocked = (
        "HG-01",
        "blocked",
    ) in gate_dispositions and "HG-01" in gate_impact_rule_ids
    high_impact_workflow_is_assistive_only = (
        "HG-03",
        "assistive_only",
    ) in gate_dispositions and "HG-03" in gate_impact_rule_ids
    external_data_controls_required = (
        "HG-05",
        "requires_controls",
    ) in gate_dispositions and "HG-05" in gate_impact_rule_ids
    prerequisites = tuple(
        sorted(
            fact_key
            for fact_key, fact in facts.items()
            if fact_key in _REQUIRED_DISCOVERY_FACT_KEYS
            and fact.get("status") == "confirmed"
        )
    )
    return GovernedAccessDeterministicResult(
        matching_status=str(case_centered.get("matching_status")),
        no_case_reason=(
            str(case_centered["no_case_reason"])
            if case_centered.get("no_case_reason") is not None
            else None
        ),
        recommendation_category=str(case_centered.get("recommendation_category")),
        decision_authority=str(selected.get("decision_authority")),
        processing_boundary=str(selected.get("processing_boundary")),
        automatic_approval_allowed=selected.get("decision_authority")
        == "autonomous_action",
        direct_permission_write_allowed=(
            selected.get("decision_authority") == "autonomous_action"
            and not enterprise_action_blocked
        ),
        unapproved_external_pii_allowed=(
            selected.get("processing_boundary") == "external_endpoint"
            and not external_data_controls_required
        ),
        high_risk_provisioning_allowed=(
            selected.get("decision_authority") == "autonomous_action"
            and not high_impact_workflow_is_assistive_only
        ),
        required_prerequisites=prerequisites,
        case_ids=case_ids,
        phase_names=tuple(
            str(phase["phase_name"])
            for phase in phased_path
            if isinstance(phase, Mapping) and isinstance(phase.get("phase_name"), str)
        ),
        gate_dispositions=gate_dispositions,
        gate_impact_rule_ids=gate_impact_rule_ids,
        first_phase_prohibits_direct_write="不直接寫入真實企業系統" in not_doing,
        first_phase_prohibits_autonomous_approval="不自主核准" in not_doing,
    )


def _assert_governed_access_deterministic_boundaries(
    result: GovernedAccessDeterministicResult,
) -> None:
    """Assert the deterministic policy and readiness boundaries, not narrative text."""

    assert result.matching_status == "matched"
    assert result.no_case_reason is None
    assert result.recommendation_category == "rules_first"
    assert result.decision_authority == "human_final_decision"
    assert result.processing_boundary == "private_endpoint"
    assert not result.automatic_approval_allowed
    assert not result.direct_permission_write_allowed
    assert not result.unapproved_external_pii_allowed
    assert not result.high_risk_provisioning_allowed
    assert set(result.required_prerequisites) == _REQUIRED_DISCOVERY_FACT_KEYS
    assert result.case_ids
    assert len(result.case_ids) == len(set(result.case_ids))
    assert set(result.phase_names) >= _EXPECTED_GOVERNED_ACCESS_PHASE_NAMES
    assert result.gate_dispositions == _EXPECTED_GOVERNED_ACCESS_GATE_MATRIX
    assert set(result.gate_impact_rule_ids) == {
        rule_id for rule_id, _ in _EXPECTED_GOVERNED_ACCESS_GATE_MATRIX
    }
    # The following two checks are structured display-contract assertions over
    # ImplementationPhase.not_doing, supplementing the typed authority/gates.
    assert result.first_phase_prohibits_direct_write
    assert result.first_phase_prohibits_autonomous_approval


def _offline_app(
    database_path: Path,
    profile_path: Path,
    adapter: OfflineGovernedAccessAdapter,
    recorder: OperationCallRecorder,
    provider_content: ProviderContentEvidence,
) -> Any:
    def factory_for(operation: str):
        return lambda _: RecordingOfflineAdapter(
            adapter, recorder, provider_content, operation
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
    provider_content = ProviderContentEvidence()
    database_path = root_path / f"{endpoint}-offline-governed-access.sqlite3"
    profile_path = root_path / f"{endpoint}-offline-governed-access-profiles.json"
    with TestClient(
        _offline_app(database_path, profile_path, adapter, recorder, provider_content)
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
        _assert_readiness_connected(readiness, endpoint)
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
    restart_provider_content = ProviderContentEvidence()
    with TestClient(
        _offline_app(
            database_path,
            profile_path,
            restart_adapter,
            restart_recorder,
            restart_provider_content,
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
        provider_content.assert_absent_from_database_cells(database_path)
        configured_key = _offline_endpoint_config(endpoint).get("api_key")
        _assert_text_markers_absent_from_database_cells(
            database_path,
            [
                '"authorization":',
                "authorization: bearer",
                *([str(configured_key)] if configured_key else []),
            ],
        )
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
                adapter_content_not_persisted=True,
                http_response_bodies_not_persisted=None,
            ),
            database_path=database_path,
            profile_path=profile_path,
            project_id=project_id,
        )
    finally:
        provider_content.clear()
        restart_provider_content.clear()


def test_offline_governed_access_public_api_matches_across_capability_profiles(
    tmp_path: Path,
) -> None:
    nvidia = _run_offline_governed_access("nvidia", tmp_path / "nvidia")
    llama = _run_offline_governed_access("llama_cpp", tmp_path / "llama_cpp")
    assert nvidia.normalized_result == llama.normalized_result
    for evidence in (nvidia, llama):
        assert evidence.normalized_result.matching_status == "matched"
        assert evidence.normalized_result.no_case_reason is None
        assert evidence.normalized_result.case_ids
        assert set(evidence.normalized_result.phase_names) >= {
            "目前階段",
            "第一階段 PoC",
            "第二階段與後續擴展",
        }
        assert evidence.normalized_result.gate_dispositions == (
            ("HG-01", "blocked"),
            ("HG-03", "assistive_only"),
            ("HG-05", "requires_controls"),
            ("HG-06", "requires_controls"),
        )
        assert all(
            set(call) == {"operation", "schema_name", "mode"}
            for call in evidence.recorder.calls
        )
        assert evidence.security == SecurityEvidence(
            api_key_not_persisted=True,
            authorization_not_persisted=True,
            adapter_content_not_persisted=True,
            http_response_bodies_not_persisted=None,
        )
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

    missing_gate_analysis = copy.deepcopy(evidence.analysis)
    missing_gate_analysis["gate_results"].pop()
    assert_rejected(missing_gate_analysis, copy.deepcopy(evidence.facts))

    incorrect_gate_analysis = copy.deepcopy(evidence.analysis)
    incorrect_gate_analysis["gate_results"][0]["disposition"] = "pass"
    assert_rejected(incorrect_gate_analysis, copy.deepcopy(evidence.facts))

    missing_phase_analysis = copy.deepcopy(evidence.analysis)
    missing_phase_analysis["case_centered"]["phased_path"] = [
        phase
        for phase in missing_phase_analysis["case_centered"]["phased_path"]
        if phase["phase_name"] != "第二階段與後續擴展"
    ]
    assert_rejected(missing_phase_analysis, copy.deepcopy(evidence.facts))

    invalid_boundary_analysis = copy.deepcopy(evidence.analysis)
    invalid_boundary_selected = next(
        option
        for option in invalid_boundary_analysis["options"]
        if option["option_key"] == invalid_boundary_analysis["recommended_option_key"]
    )
    invalid_boundary_selected["processing_boundary"] = "unsupported_boundary"
    assert_rejected(invalid_boundary_analysis, copy.deepcopy(evidence.facts))

    no_match_analysis = copy.deepcopy(evidence.analysis)
    no_match_analysis["case_centered"]["matching_status"] = "no_suitable_reviewed_case"
    no_match_analysis["case_centered"]["no_case_reason"] = "incorrectly removed"
    assert_rejected(no_match_analysis, copy.deepcopy(evidence.facts))


def test_http_response_body_evidence_captures_success_and_error_responses(
    tmp_path: Path,
) -> None:
    """The hook reads response bytes once without storing headers or requests."""

    evidence = HttpResponseBodyEvidence()
    success_body = b'{"id":"success","choices":[]}'
    error_body = b'{"error":{"code":"unsupported_parameter"}}'

    def provider_response(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("error"):
            return httpx.Response(400, content=error_body, request=request)
        return httpx.Response(200, content=success_body, request=request)

    with httpx.Client(
        transport=httpx.MockTransport(provider_response),
        event_hooks={"response": [evidence.capture_response]},
    ) as client:
        assert client.get("https://provider.example.test/success").json() == {
            "id": "success",
            "choices": [],
        }
        assert client.get("https://provider.example.test/error").status_code == 400

    database_path = tmp_path / "response-body-evidence.sqlite3"
    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE evidence (body_text TEXT, body_blob BLOB)")
        connection.commit()
    assert evidence.response_count == 2
    evidence.assert_absent_from_database_cells(database_path)

    with sqlite3.connect(database_path) as connection:
        connection.execute("INSERT INTO evidence (body_blob) VALUES (?)", (error_body,))
        connection.commit()
    with pytest.raises(AssertionError):
        evidence.assert_absent_from_database_cells(database_path)

    text_database_path = tmp_path / "response-text-evidence.sqlite3"
    with sqlite3.connect(text_database_path) as connection:
        connection.execute("CREATE TABLE evidence (body_text TEXT, body_blob BLOB)")
        connection.execute(
            "INSERT INTO evidence (body_text) VALUES (?)", (success_body.decode(),)
        )
        connection.commit()
    with pytest.raises(AssertionError):
        evidence.assert_absent_from_database_cells(text_database_path)
    evidence.clear()
    assert evidence.response_count == 0


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
    http_response_bodies = HttpResponseBodyEvidence()
    app, provider_client = _live_app(
        database_path, profile_path, recorder, http_response_bodies
    )
    report_observation, report_observability_originals = _begin_report_observability()

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
            _assert_readiness_connected(readiness, endpoint)
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

            analysis = _assert_live_operation_response(
                client.post(f"/v1/projects/{project_id}/versions/1/analysis"),
                201,
                endpoint=endpoint,
                label="analysis",
                recorder=recorder,
            )
            analysis_call_count = len(recorder.calls)
            assert analysis_call_count > after_discovery
            duplicate_analysis = _assert_live_operation_response(
                client.post(f"/v1/projects/{project_id}/versions/1/analysis"),
                201,
                endpoint=endpoint,
                label="duplicate analysis",
                recorder=recorder,
            )
            assert duplicate_analysis == analysis
            assert len(recorder.calls) == analysis_call_count

            report = _assert_live_operation_response(
                client.post(f"/v1/projects/{project_id}/versions/1/report"),
                201,
                endpoint=endpoint,
                label="report",
                recorder=recorder,
            )
            report_call_count = len(recorder.calls)
            duplicate_report = _assert_live_operation_response(
                client.post(f"/v1/projects/{project_id}/versions/1/report"),
                409,
                endpoint=endpoint,
                label="duplicate report",
                recorder=recorder,
            )
            assert isinstance(duplicate_report, Mapping)
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
        restart_http_response_bodies = HttpResponseBodyEvidence()
        restarted_app, restarted_provider_client = _live_app(
            database_path,
            profile_path,
            restart_recorder,
            restart_http_response_bodies,
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
            restart_http_response_bodies.clear()

        http_response_bodies.assert_absent_from_database_cells(database_path)
        configured_key = config.get("api_key")
        _assert_text_markers_absent_from_database_cells(
            database_path,
            [
                '"authorization":',
                "authorization: bearer",
                *(
                    [configured_key]
                    if isinstance(configured_key, str) and configured_key
                    else []
                ),
            ],
        )
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
                adapter_content_not_persisted=None,
                http_response_bodies_not_persisted=True,
            ),
            database_path=database_path,
            profile_path=profile_path,
            project_id=project_id,
            report_executor_records=tuple(report_observation.executor_records),
            report_semantic_passes=tuple(sorted(report_observation.semantic_passes)),
            deterministic_fallback_invoked=report_observation.deterministic_fallback_invoked,
        )
    finally:
        _end_report_observability(report_observability_originals)
        http_response_bodies.clear()
        provider_client.close()


def test_live_p7_2a_governed_access_public_api_flow(tmp_path: Path) -> None:
    """Run local full compatibility before the remote NVIDIA endpoint gate."""

    _require_live_dual_endpoint_environment()
    _preflight_live_dual_endpoints()
    llama, nvidia = _run_live_endpoint_pair(tmp_path, _run_live_governed_access)

    assert nvidia.normalized_result == llama.normalized_result
    for evidence in (nvidia, llama):
        assert evidence.security == SecurityEvidence(
            api_key_not_persisted=True,
            authorization_not_persisted=True,
            adapter_content_not_persisted=None,
            http_response_bodies_not_persisted=True,
        )
        assert evidence.count_matrix.after_restart == 0
        assert all(
            set(call) == {"operation", "schema_name", "mode"}
            for call in evidence.recorder.calls
        )
        assert evidence.report_executor_records
        assert {
            record["schema_name"] for record in evidence.report_executor_records
        } == {"report_part_a", "report_part_b"}
        assert all(
            record["success"] is True
            and record["mode_used"] == "json_schema"
            and record["logical_max_tokens"] == 2048
            and record["fallback_used"] is False
            for record in evidence.report_executor_records
        )
        assert evidence.report_semantic_passes
        assert evidence.deterministic_fallback_invoked is False


def test_live_endpoint_pair_does_not_call_nvidia_after_local_failure(
    tmp_path: Path,
) -> None:
    calls: list[str] = []

    def runner(endpoint: str, _: Path) -> LiveEndpointEvidence:
        calls.append(endpoint)
        if endpoint == "llama_cpp":
            raise AssertionError("local endpoint failed")
        raise AssertionError("NVIDIA must not run")

    with pytest.raises(AssertionError, match="local endpoint failed"):
        _run_live_endpoint_pair(tmp_path, runner)

    assert calls == ["llama_cpp"]


def test_live_endpoint_pair_runs_nvidia_once_after_local_success(
    tmp_path: Path,
) -> None:
    calls: list[str] = []

    def runner(endpoint: str, _: Path) -> LiveEndpointEvidence:
        calls.append(endpoint)
        return object()  # type: ignore[return-value]

    llama, nvidia = _run_live_endpoint_pair(tmp_path, runner)

    assert calls == ["llama_cpp", "nvidia"]
    assert llama is not nvidia
