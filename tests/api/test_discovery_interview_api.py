from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel

from ai_poc_planner.app.api import create_app
from ai_poc_planner.persistence.model_profiles import LocalModelProfileRepository
from ai_poc_planner.providers.openai_compatible import OpenAICompatibleProviderError


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
    assert answered.json()["status"] == "ready_for_next_round"


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
