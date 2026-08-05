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


class InitialGapDiscoveryAdapter:
    def __init__(self, *, premature_completion: bool = False) -> None:
        self.calls = 0
        self.premature_completion = premature_completion

    def complete(self, **_: object) -> str:
        self.calls += 1
        if self.calls == 1:
            return json.dumps(
                {
                    "concise_requirement_summary": "目前流程仍有人工處理。",
                    "current_workflow_understanding": "資料由人工整理。",
                    "desired_outcome_understanding": "希望降低重工。",
                    "available_data_understanding": "資料狀態仍待確認。",
                    "proposed_assumptions": [],
                    "detected_contradictions_or_ambiguities": [],
                }
            )
        if self.premature_completion:
            return json.dumps({"interview_complete": True, "questions": []})
        return json.dumps(
            {
                "interview_complete": False,
                "questions": [
                    {
                        "fact_key": "desired_outcome",
                        "question": "希望改善的成果是什麼？",
                        "why_it_matters": "這會影響成功方向。",
                        "affected_judgement": "success direction",
                        "example": "描述希望改善的結果即可。",
                    }
                ],
            }
        )


class SemanticDuplicateDiscoveryAdapter:
    def __init__(self) -> None:
        self.calls = 0

    def complete(self, **_: object) -> str:
        self.calls += 1
        if self.calls == 1:
            return json.dumps(
                {
                    "concise_requirement_summary": "Manual workflow.",
                    "current_workflow_understanding": "Manual workflow.",
                    "desired_outcome_understanding": "Improve throughput.",
                    "available_data_understanding": "Data exists.",
                    "proposed_assumptions": [],
                    "detected_contradictions_or_ambiguities": [],
                }
            )
        if self.calls == 2:
            return json.dumps(
                {
                    "interview_complete": False,
                    "questions": [
                        {
                            "fact_key": "desired_outcome",
                            "question": "What outcome should improve?",
                            "why_it_matters": "It affects the hard gate.",
                            "affected_judgement": "hard gate",
                            "example": "A concise goal is enough.",
                        }
                    ],
                }
            )
        return json.dumps(
            {
                "interview_complete": False,
                "questions": [
                    {
                        "fact_key": "objective_detail",
                        "question": "What specific goal should this project achieve?",
                        "why_it_matters": "It affects the scope.",
                        "affected_judgement": "scope",
                        "example": "A concise goal is enough.",
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


def _client_with_interview_adapter(tmp_path: Path, adapter: object) -> TestClient:
    profiles = LocalModelProfileRepository(path=tmp_path / "model_profiles.json")
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


def test_semantic_duplicate_round_is_completed_without_persisting_a_question(
    tmp_path: Path,
) -> None:
    client = _client_with_interview_adapter(
        tmp_path, SemanticDuplicateDiscoveryAdapter()
    )
    profile_id = _ready_profile(client)
    created = client.post(
        "/v1/discovery-projects",
        json={
            "project_name": "Semantic duplicate",
            "current_workflow_problem": "Manual workflow",
            "model_profile_id": profile_id,
        },
    )
    project_id = created.json()["project"]["id"]
    assert (
        client.post(f"/v1/projects/{project_id}/versions/1/understanding").status_code
        == 200
    )
    assert (
        client.post(
            f"/v1/projects/{project_id}/versions/1/understanding/confirm"
        ).status_code
        == 200
    )
    first_round = client.post(f"/v1/projects/{project_id}/versions/1/interview-rounds")
    assert first_round.status_code == 200
    first_question = first_round.json()[0]
    answered = client.post(
        f"/v1/projects/{project_id}/versions/1/interview-answers",
        json={
            "answers": [
                {
                    "question_id": first_question["id"],
                    "answer_status": "answered",
                    "answer": "Improve throughput",
                }
            ]
        },
    )
    assert answered.status_code == 200
    assert answered.json()["status"] == "ready_for_next_round"

    second_round = client.post(f"/v1/projects/{project_id}/versions/1/interview-rounds")
    assert second_round.status_code == 200
    assert second_round.json() == []
    assert (
        len(
            client.get(
                f"/v1/projects/{project_id}/versions/1/interview-questions"
            ).json()
        )
        == 1
    )
    assert (
        client.get(f"/v1/projects/{project_id}/versions/1/discovery").json()["status"]
        == "ready_for_assessment"
    )


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


def test_initial_missing_canonical_fact_is_asked_and_revised_from_answer(
    tmp_path: Path,
) -> None:
    client = _client_with_interview_adapter(tmp_path, InitialGapDiscoveryAdapter())
    profile_id = _ready_profile(client)
    created = client.post(
        "/v1/discovery-projects",
        json={
            "project_name": "Initial gap",
            "current_workflow_problem": "多年資料尚未整理",
            "desired_outcome": "",
            "available_data": "",
            "users_and_owners": "",
            "known_constraints": "",
            "model_profile_id": profile_id,
        },
    )
    project_id = created.json()["project"]["id"]
    client.post(f"/v1/projects/{project_id}/versions/1/understanding")
    client.post(f"/v1/projects/{project_id}/versions/1/understanding/confirm")
    questions = client.post(f"/v1/projects/{project_id}/versions/1/interview-rounds")

    assert questions.status_code == 200
    question = questions.json()[0]
    answered = client.post(
        f"/v1/projects/{project_id}/versions/1/interview-answers",
        json={
            "answers": [
                {
                    "question_id": question["id"],
                    "answer_status": "answered",
                    "answer": "減少人工重工。",
                }
            ]
        },
    )

    assert answered.status_code == 200
    current = client.get(f"/v1/projects/{project_id}/versions/1/facts").json()
    desired = next(item for item in current if item["fact_key"] == "desired_outcome")
    assert desired["status"] == "confirmed"
    assert desired["value"] == "減少人工重工。"
    history = client.get(f"/v1/projects/{project_id}/versions/1/facts/history").json()
    desired_history = [
        item for item in history if item["fact_key"] == "desired_outcome"
    ]
    assert [item["status"] for item in desired_history] == ["missing", "confirmed"]
    assert desired_history[-1]["supersedes_fact_id"] == desired_history[0]["id"]
    assert desired_history[-1]["reference_message_ids"]


def test_minimal_brief_cannot_complete_when_provider_claims_no_questions(
    tmp_path: Path,
) -> None:
    client = _client_with_interview_adapter(
        tmp_path, InitialGapDiscoveryAdapter(premature_completion=True)
    )
    profile_id = _ready_profile(client)
    created = client.post(
        "/v1/discovery-projects",
        json={
            "project_name": "Premature completion",
            "current_workflow_problem": "多年資料尚未整理",
            "model_profile_id": profile_id,
        },
    )
    project_id = created.json()["project"]["id"]
    client.post(f"/v1/projects/{project_id}/versions/1/understanding")
    client.post(f"/v1/projects/{project_id}/versions/1/understanding/confirm")

    failed = client.post(f"/v1/projects/{project_id}/versions/1/interview-rounds")

    assert failed.status_code == 502
    assert failed.json()["error"]["code"] == "interview_questions_unavailable"
    session = client.get(f"/v1/projects/{project_id}/versions/1/discovery").json()
    version = client.get(f"/v1/projects/{project_id}/versions/1").json()
    assert session["status"] == "ready_for_interview"
    assert version["status"] == "interviewing"


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


def test_analysis_category_mismatch_has_stable_safe_actionable_409(
    tmp_path: Path, monkeypatch
) -> None:
    def fail_closed(
        _: EvidenceAnalysisService, project_id: object, version_number: int
    ) -> object:
        del project_id, version_number
        raise EvidenceAnalysisError("solution_category_mismatch")

    monkeypatch.setattr(EvidenceAnalysisService, "create", fail_closed)
    client = TestClient(
        create_app(
            chat_model=GenericFakeChatModel(messages=iter([])),
            database_path=tmp_path / "analysis-category-mismatch.sqlite3",
            model_profile_repository=LocalModelProfileRepository(
                path=tmp_path / "analysis-category-mismatch.json"
            ),
        )
    )

    response = client.post(
        "/v1/projects/10000000-0000-0000-0000-000000000001/versions/1/analysis"
    )

    assert response.status_code == 409
    payload = response.json()
    assert payload["error"]["code"] == "solution_category_mismatch"
    assert payload["error"]["details"] == {
        "operation": "analysis",
        "retryable": False,
        "user_action": (
            "請檢查核准方案目錄與正式評估類別的設定；修正後可安全重試評估。"
        ),
    }
    assert "raw" not in response.text


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
