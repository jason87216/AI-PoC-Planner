from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel

from ai_poc_planner.app.api import create_app
from ai_poc_planner.application.evidence_analysis import (
    EvidenceAnalysisError,
    EvidenceAnalysisService,
)
from ai_poc_planner.domain.enums import DiscoverySessionStatus, ProjectStatus
from ai_poc_planner.persistence.connection import database_connection
from ai_poc_planner.persistence.discovery import SQLiteDiscoveryRepository
from ai_poc_planner.persistence.model_profiles import LocalModelProfileRepository
from ai_poc_planner.persistence.project_history import SQLiteProjectHistoryRepository
from ai_poc_planner.providers.openai_compatible import OpenAICompatibleProviderError
from ai_poc_planner.ui.api_client import ApiClient, ApiClientError
from tests.providers.test_p7_2a_provider_compatibility_integration import (
    OfflineGovernedAccessAdapter,
)


class ConnectedAdapter:
    def complete(self, **_: object) -> str:
        return '{"status":"ok"}'


class DiscoveryAdapter:
    def __init__(self) -> None:
        self.calls = 0

    def complete(self, **_: object) -> str:
        self.calls += 1
        if self.calls == 1:
            return json.dumps(
                {
                    "concise_requirement_summary": "Route incoming requests faster.",
                    "current_workflow_understanding": "Manual routing.",
                    "desired_outcome_understanding": "Reduce routing time.",
                    "available_data_understanding": "Export data exists.",
                    "proposed_assumptions": [],
                    "detected_contradictions_or_ambiguities": [],
                }
            )
        return json.dumps(
            {
                "interview_complete": False,
                "questions": [
                    {
                        "fact_key": "daily_volume",
                        "question": "How many requests arrive on a normal day?",
                        "why_it_matters": "It affects sizing.",
                        "affected_judgement": "data readiness",
                        "example": "A rough daily range is enough.",
                    }
                ],
            }
        )


class AuthFailingDiscoveryAdapter:
    def complete(self, **kwargs: object) -> str:
        response_format = kwargs["response_format"]
        if response_format.name == "connection_probe":
            return '{"status":"ok"}'
        raise OpenAICompatibleProviderError("provider_auth_failed")


def _client(tmp_path: Path) -> TestClient:
    profiles = LocalModelProfileRepository(path=tmp_path / "model_profiles.json")
    adapter = DiscoveryAdapter()
    return TestClient(
        create_app(
            chat_model=GenericFakeChatModel(messages=iter([])),
            database_path=tmp_path / "discovery.sqlite3",
            model_profile_repository=profiles,
            connection_adapter_factory=lambda _: ConnectedAdapter(),
            interview_adapter_factory=lambda _: adapter,
        )
    )


def _auth_failing_client(tmp_path: Path) -> TestClient:
    profiles = LocalModelProfileRepository(path=tmp_path / "auth-failing.json")
    return TestClient(
        create_app(
            chat_model=GenericFakeChatModel(messages=iter([])),
            database_path=tmp_path / "auth-failing.sqlite3",
            model_profile_repository=profiles,
            connection_adapter_factory=lambda _: ConnectedAdapter(),
            interview_adapter_factory=lambda _: AuthFailingDiscoveryAdapter(),
        )
    )


def _ready_profile(client: TestClient) -> str:
    profile = client.post(
        "/v1/model-profiles",
        json={
            "profile_name": "Local",
            "base_url": "http://127.0.0.1:8080/v1",
            "model_name": "local-model",
            "api_key": "safe-test-marker",
        },
    ).json()
    client.post(f"/v1/model-profiles/{profile['id']}/select")
    assert client.post(f"/v1/model-profiles/{profile['id']}/test").status_code == 200
    return profile["id"]


def test_initial_brief_requires_a_ready_project_profile(tmp_path: Path) -> None:
    client = _client(tmp_path)
    response = client.post(
        "/v1/discovery-projects",
        json={
            "project_name": "Needs a model",
            "current_workflow_problem": "Manual work",
            "desired_outcome": "A clearer process",
            "available_data": "目前沒有",
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "provider_not_ready"
    assert client.get("/v1/projects").json() == []


def test_phase_three_initial_brief_understanding_and_bounded_round(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    _ready_profile(client)
    created = client.post(
        "/v1/discovery-projects",
        json={
            "project_name": "Discovery",
            "current_workflow_problem": "Manual routing",
            "desired_outcome": "Faster routing",
            "available_data": "不知道",
        },
    )

    assert created.status_code == 201
    body = created.json()
    assert body["version"]["selected_model"]["profile_name"] == "Local"
    assert body["normalized_brief"]["available_data_status"] == "unknown"
    project_id = body["project"]["id"]
    understanding = client.post(f"/v1/projects/{project_id}/versions/1/understanding")
    assert understanding.status_code == 200
    assert (
        client.post(
            f"/v1/projects/{project_id}/versions/1/understanding/confirm"
        ).status_code
        == 200
    )
    questions = client.post(f"/v1/projects/{project_id}/versions/1/interview-rounds")
    assert questions.status_code == 200
    assert len(questions.json()) == 1
    question = questions.json()[0]
    answered = client.post(
        f"/v1/projects/{project_id}/versions/1/interview-answers",
        json={
            "answers": [
                {
                    "question_id": question["id"],
                    "answer_status": "unknown",
                    "answer": None,
                }
            ],
        },
    )
    assert answered.status_code == 200
    assert answered.json()["status"] == "ready_for_assessment"


def test_minimal_initial_brief_persists_optional_fields_as_missing(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    profile_id = _ready_profile(client)
    created = client.post(
        "/v1/discovery-projects",
        json={
            "project_name": "Minimal brief",
            "current_workflow_problem": "Manual routing",
            "desired_outcome": "",
            "available_data": "",
            "users_and_owners": " ",
            "known_constraints": None,
            "model_profile_id": profile_id,
        },
    )

    assert created.status_code == 201
    assert created.json()["normalized_brief"]["desired_outcome"] is None
    assert created.json()["normalized_brief"]["available_data"] is None
    project_id = created.json()["project"]["id"]
    facts = client.get(f"/v1/projects/{project_id}/versions/1/facts").json()
    fact_statuses = {fact["fact_key"]: fact["status"] for fact in facts}
    assert fact_statuses["desired_outcome"] == "missing"
    assert fact_statuses["available_data"] == "missing"
    assert fact_statuses["users_and_owners"] == "missing"
    assert fact_statuses["known_constraints"] == "missing"


def test_discovery_provider_auth_failure_is_safe_and_does_not_persist_assistant_output(
    tmp_path: Path,
) -> None:
    client = _auth_failing_client(tmp_path)
    _ready_profile(client)
    created = client.post(
        "/v1/discovery-projects",
        json={
            "project_name": "Auth failure",
            "current_workflow_problem": "Manual routing",
            "desired_outcome": "Faster routing",
            "available_data": "Unknown",
        },
    )
    project_id = created.json()["project"]["id"]

    failed = client.post(f"/v1/projects/{project_id}/versions/1/understanding")

    assert failed.status_code == 502
    assert failed.json()["error"]["code"] == "provider_auth_failed"
    assert failed.json()["error"]["details"]["operation"] == "discovery"
    messages = client.get(f"/v1/projects/{project_id}/versions/1/messages").json()
    assert all(message["role"] != "assistant" for message in messages)


def test_analysis_validation_failure_is_safe_and_not_generic_internal_error(
    tmp_path: Path, monkeypatch
) -> None:
    def fail_closed(
        _: EvidenceAnalysisService, project_id: object, version_number: int
    ) -> object:
        del project_id, version_number
        raise EvidenceAnalysisError("analysis_result_invalid")

    monkeypatch.setattr(EvidenceAnalysisService, "create", fail_closed)
    client = TestClient(
        create_app(
            chat_model=GenericFakeChatModel(messages=iter([])),
            database_path=tmp_path / "analysis-failure.sqlite3",
            model_profile_repository=LocalModelProfileRepository(
                path=tmp_path / "analysis-failure.json"
            ),
        )
    )

    response = client.post(
        "/v1/projects/10000000-0000-0000-0000-000000000001/versions/1/analysis"
    )

    assert response.status_code == 502
    payload = response.json()
    assert payload["error"]["code"] == "analysis_result_invalid"
    assert payload["error"]["details"] == {
        "operation": "analysis",
        "retryable": False,
        "user_action": (
            "若持續失敗，請重新測試模型設定；問題仍存在時請查看本機啟動日誌。"
        ),
    }
    assert "internal_error" not in response.text
    assert "raw" not in response.text
    assert "prompt" not in response.text

    api = ApiClient(client=client)
    with pytest.raises(ApiClientError) as parsed:
        api.create_analysis("10000000-0000-0000-0000-000000000001", 1)
    assert parsed.value.user_message == "評估結果格式無法驗證，請重新嘗試。"
    assert (
        parsed.value.user_action
        == "若持續失敗，請重新測試模型設定；問題仍存在時請查看本機啟動日誌。"
    )
    assert all(
        marker not in str(parsed.value)
        for marker in ("raw", "prompt", "SQL", "secret", "10000000")
    )


def test_analysis_validation_failure_preserves_persistence_and_allows_retry(
    tmp_path: Path, monkeypatch
) -> None:
    database_path = tmp_path / "analysis-retry.sqlite3"
    profiles = LocalModelProfileRepository(path=tmp_path / "analysis-retry.json")
    adapter = OfflineGovernedAccessAdapter()
    client = TestClient(
        create_app(
            chat_model=GenericFakeChatModel(messages=iter([])),
            database_path=database_path,
            model_profile_repository=profiles,
            connection_adapter_factory=lambda _: ConnectedAdapter(),
            analysis_adapter_factory=lambda _: adapter,
        )
    )
    profile_id = _ready_profile(client)
    created = client.post(
        "/v1/discovery-projects",
        json={
            "project_name": "Analysis retry",
            "current_workflow_problem": "Manual routing",
            "desired_outcome": "Faster routing",
            "available_data": "Export data",
            "users_and_owners": "Operations",
            "known_constraints": "Human review remains required",
            "model_profile_id": profile_id,
        },
    )
    assert created.status_code == 201
    project_id = UUID(created.json()["project"]["id"])

    connection = database_connection(database_path)
    try:
        history = SQLiteProjectHistoryRepository(connection)
        version = history.get_version(project_id, 1)
        now = datetime.now(UTC)
        history.update_version(
            version.model_copy(
                update={"status": ProjectStatus.READY_FOR_ASSESSMENT, "updated_at": now}
            ),
            now,
        )
        sessions = SQLiteDiscoveryRepository(connection)
        session = sessions.get_session_for_version(version.id)
        with history.transaction():
            sessions.update_session(
                session.model_copy(
                    update={
                        "status": DiscoverySessionStatus.READY_FOR_ASSESSMENT,
                        "current_round": 1,
                        "updated_at": now,
                    }
                )
            )
        message_count = len(history.list_messages(version.id))
    finally:
        connection.close()

    original_validated_result = EvidenceAnalysisService._validated_result
    fail_once = True

    def fail_domain_assembly(self, *args: object, **kwargs: object):
        nonlocal fail_once
        if fail_once:
            fail_once = False
            raise ValueError("raw-analysis-marker")
        return original_validated_result(self, *args, **kwargs)

    monkeypatch.setattr(
        EvidenceAnalysisService, "_validated_result", fail_domain_assembly
    )

    failed = client.post(f"/v1/projects/{project_id}/versions/1/analysis")
    assert failed.status_code == 502
    assert failed.json()["error"]["code"] == "analysis_result_invalid"
    assert failed.json()["error"]["details"]["operation"] == "analysis"
    assert "raw-analysis-marker" not in failed.text
    assert "internal_error" not in failed.text
    assert "prompt" not in failed.text
    assert str(database_path) not in failed.text

    connection = database_connection(database_path)
    try:
        history = SQLiteProjectHistoryRepository(connection)
        version = history.get_version(project_id, 1)
        assert version.status is ProjectStatus.READY_FOR_ASSESSMENT
        assert len(history.list_messages(version.id)) == message_count
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM planning_analysis_results"
            ).fetchone()[0]
            == 0
        )
    finally:
        connection.close()

    retried = client.post(f"/v1/projects/{project_id}/versions/1/analysis")
    assert retried.status_code == 201

    connection = database_connection(database_path)
    try:
        history = SQLiteProjectHistoryRepository(connection)
        version = history.get_version(project_id, 1)
        assert version.status is ProjectStatus.ASSESSED
        assert len(history.list_messages(version.id)) == message_count
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM planning_analysis_results"
            ).fetchone()[0]
            == 1
        )
    finally:
        connection.close()


def test_requirement_feedback_accepts_natural_language_without_fact_ids(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    _ready_profile(client)
    created = client.post(
        "/v1/discovery-projects",
        json={
            "project_name": "Discovery",
            "current_workflow_problem": "Manual routing",
            "desired_outcome": "Faster routing",
            "available_data": "Unknown",
        },
    )
    project_id = created.json()["project"]["id"]
    assert (
        client.post(f"/v1/projects/{project_id}/versions/1/understanding").status_code
        == 200
    )

    response = client.post(
        f"/v1/projects/{project_id}/versions/1/understanding/feedback",
        json={"feedback": "The requester needs human review before any decision."},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "correction_pending"


def test_initial_brief_requires_a_tested_selected_provider_and_safe_errors(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    response = client.post(
        "/v1/discovery-projects",
        json={
            "project_name": "x",
            "current_workflow_problem": "x",
            "desired_outcome": "x",
            "available_data": "x",
            "system_prompt": "raw-secret-marker",
        },
    )
    assert response.status_code == 422
    assert "raw-secret-marker" not in response.text
