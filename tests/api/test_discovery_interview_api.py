from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel

from ai_poc_planner.app.api import create_app
from ai_poc_planner.persistence.model_profiles import LocalModelProfileRepository


class ConnectedAdapter:
    def complete(self, **_: object) -> str:
        return "connected"


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
