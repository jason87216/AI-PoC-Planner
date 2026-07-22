from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from ai_poc_planner.agent.contracts import PlanningIntent
from ai_poc_planner.app.api import create_app
from ai_poc_planner.providers.fake import FakeModelProvider


class ScriptedToolCallingChatModel(GenericFakeChatModel):
    def bind_tools(self, tools: Sequence[object], **kwargs: object) -> object:
        return self


def _tool_call(intent: PlanningIntent, call_id: str) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": "evaluate_planning_intent",
                "args": {"intent": intent.model_dump(mode="json")},
                "id": call_id,
            }
        ],
    )


def _model_for(*intents: PlanningIntent) -> ScriptedToolCallingChatModel:
    messages: list[AIMessage] = []
    for index, intent in enumerate(intents, start=1):
        messages.extend(
            [_tool_call(intent, f"persisted-{index}"), AIMessage(content="done")]
        )
    return ScriptedToolCallingChatModel(messages=iter(messages))


def _incomplete_intent() -> PlanningIntent:
    return PlanningIntent.model_validate(
        {
            "opportunity_input": {"business_problem_signals": ["improve work"]},
            "deployment_input": {},
        }
    )


def _ready_intent() -> PlanningIntent:
    return PlanningIntent.model_validate(
        {
            "opportunity_input": {
                "business_problem_signals": ["customer support FAQ"],
            },
            "deployment_input": {
                "data_classification": "internal",
                "external_processing_allowed": True,
                "offline_operation_required": False,
            },
            "request_summary": "Customer support FAQ assistance",
        }
    )


def _client(database_path: Path, *intents: PlanningIntent) -> TestClient:
    return TestClient(
        create_app(
            chat_model=_model_for(*intents),
            database_path=database_path,
            assessment_provider=FakeModelProvider(),
        )
    )


def _formal_assessment_answers() -> dict[str, object]:
    return {
        "target_users": ["support agents"],
        "current_workflow": "Agents search internal FAQ before replying.",
        "data_sources": ["internal FAQ"],
        "owner": "customer support lead",
    }


def test_persisted_flow_handles_two_clarification_batches_and_reloads_result(
    tmp_path: Path,
) -> None:
    client = _client(
        tmp_path / "planner.sqlite3",
        _incomplete_intent(),
        _ready_intent(),
        _ready_intent(),
    )

    created = client.post(
        "/v1/planning/runs",
        json={"natural_language_request": "We want to improve work."},
    )

    assert created.status_code == 201
    first = created.json()
    assert first["status"] == "clarification_required"
    assert first["intent"] == _incomplete_intent().model_dump(mode="json")
    assert len(first["clarifying_questions"]) == 4

    first_answers = client.post(
        f"/v1/planning/runs/{first['run_id']}/clarifications",
        json={
            "clarification_answers": {
                "data_classification": "internal",
                "external_processing_allowed": True,
                "offline_operation_required": False,
            }
        },
    )

    assert first_answers.status_code == 200
    second = first_answers.json()
    assert second["status"] == "clarification_required"
    assert [question["field"] for question in second["clarifying_questions"]] == [
        "target_users",
        "current_workflow",
        "data_sources",
        "owner",
    ]
    assert second["intent"] == _ready_intent().model_dump(mode="json")

    completed = client.post(
        f"/v1/planning/runs/{first['run_id']}/clarifications",
        json={
            "clarification_answers": {
                "target_users": ["support agents"],
                "current_workflow": "Agents search internal FAQ before replying.",
                "data_sources": ["internal FAQ"],
                "owner": "customer support lead",
            }
        },
    )

    assert completed.status_code == 200
    completed_payload = completed.json()
    assert completed_payload["status"] == "completed"
    assert completed_payload["assessment"] is not None
    assert completed_payload["proposal"] is not None
    assert completed_payload["markdown_report"]

    connection = sqlite3.connect(tmp_path / "planner.sqlite3")
    try:
        row = connection.execute(
            "SELECT intent_json, known_information_json, clarification_answers_json "
            "FROM planning_runs WHERE id = ?",
            (first["run_id"],),
        ).fetchone()
    finally:
        connection.close()
    assert row is not None
    assert json.loads(row[0]) == _ready_intent().model_dump(mode="json")
    assert "scenario" not in json.loads(row[1])
    assert "opportunity_match" not in json.loads(row[1])
    assert "deployment_posture" not in json.loads(row[1])
    assert "opportunity_match" not in json.loads(row[2])
    assert "deployment_posture" not in json.loads(row[2])

    reloaded = client.get(f"/v1/planning/runs/{first['run_id']}")

    assert reloaded.status_code == 200
    reloaded_payload = reloaded.json()
    assert reloaded_payload.pop("correlation_id")
    assert completed_payload.pop("correlation_id")
    assert reloaded_payload == completed_payload


def test_persisted_routes_require_explicit_database_and_assessment_provider() -> None:
    client = TestClient(create_app(chat_model=_model_for(_ready_intent())))

    response = client.post(
        "/v1/planning/runs",
        json={"natural_language_request": "Sensitive request must not be exposed."},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "persistence_not_configured"
    assert "Sensitive request must not be exposed." not in response.text


def test_persisted_clarification_requires_a_non_empty_answer_batch(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path / "planner.sqlite3", _incomplete_intent())
    created = client.post(
        "/v1/planning/runs",
        json={"natural_language_request": "We want to improve work."},
    )

    response = client.post(
        f"/v1/planning/runs/{created.json()['run_id']}/clarifications",
        json={"clarification_answers": {}},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "request_validation_error"


def test_initial_facts_can_complete_a_persisted_run_immediately(tmp_path: Path) -> None:
    client = _client(tmp_path / "planner.sqlite3", _ready_intent())

    response = client.post(
        "/v1/planning/runs",
        json={
            "natural_language_request": "Support needs FAQ assistance.",
            "clarification_answers": _formal_assessment_answers(),
        },
    )

    assert response.status_code == 201
    assert response.json()["status"] == "completed"


def test_agent_failure_does_not_update_an_existing_persisted_run(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path / "planner.sqlite3", _incomplete_intent())
    created = client.post(
        "/v1/planning/runs",
        json={"natural_language_request": "We want to improve work."},
    )
    run_id = created.json()["run_id"]

    failed = client.post(
        f"/v1/planning/runs/{run_id}/clarifications",
        json={"clarification_answers": {"data_classification": "internal"}},
    )

    assert failed.status_code == 502
    assert failed.json()["error"]["code"] == "agent_execution_failed"

    reloaded = client.get(f"/v1/planning/runs/{run_id}")
    assert reloaded.status_code == 200
    assert reloaded.json()["status"] == "clarification_required"
    assert reloaded.json()["intent"] == _incomplete_intent().model_dump(mode="json")


def test_persisted_run_not_found_returns_safe_404(tmp_path: Path) -> None:
    client = _client(tmp_path / "planner.sqlite3")

    response = client.get(f"/v1/planning/runs/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "planning_run_not_found"


def test_completed_run_rejects_another_clarification_without_calling_agent(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path / "planner.sqlite3", _ready_intent())
    created = client.post(
        "/v1/planning/runs",
        json={
            "natural_language_request": "Support needs FAQ assistance.",
            "clarification_answers": _formal_assessment_answers(),
        },
    )

    response = client.post(
        f"/v1/planning/runs/{created.json()['run_id']}/clarifications",
        json={"clarification_answers": {"owner": "another owner"}},
    )

    assert created.json()["status"] == "completed"
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invalid_planning_run_transition"
