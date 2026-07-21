from __future__ import annotations

from collections.abc import Sequence

from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from ai_poc_planner.agent.contracts import PlanningIntent
from ai_poc_planner.app.api import create_app


class ScriptedToolCallingChatModel(GenericFakeChatModel):
    """LangChain's official fake model with the minimal tool-binding seam."""

    def bind_tools(self, tools: Sequence[object], **kwargs: object) -> object:
        return self


def _tool_call(intent: PlanningIntent) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": "evaluate_planning_intent",
                "args": {"intent": intent.model_dump(mode="json")},
                "id": "call-api-1",
            }
        ],
    )


def _model_for(intent: PlanningIntent) -> ScriptedToolCallingChatModel:
    return ScriptedToolCallingChatModel(
        messages=iter([_tool_call(intent), AIMessage(content="模型文字不作為結果")])
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
        }
    )


def test_health_is_available_without_exposing_model_configuration() -> None:
    client = TestClient(create_app(chat_model=_model_for(_ready_intent())))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_returns_only_the_actual_typed_tool_evaluation() -> None:
    client = TestClient(create_app(chat_model=_model_for(_ready_intent())))

    response = client.post(
        "/v1/planning/interpret",
        json={"natural_language_request": "客服需要 AI 協助回覆 FAQ。"},
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "ready"
    assert payload["intent"] == _ready_intent().model_dump(mode="json")
    assert payload["opportunity_match"]["candidates"][0]["opportunity_type"] == (
        "customer_service_assist"
    )
    assert "weighted_score" not in payload
    assert "recommendation" not in payload
    assert "hard_gates" not in payload
    assert "proposal" not in payload


def test_api_returns_clarification_then_ready_after_answers_are_resubmitted() -> None:
    incomplete_intent = PlanningIntent.model_validate(
        {
            "opportunity_input": {"business_problem_signals": ["improve work"]},
            "deployment_input": {},
        }
    )
    incomplete_client = TestClient(create_app(chat_model=_model_for(incomplete_intent)))

    clarification = incomplete_client.post(
        "/v1/planning/interpret",
        json={"natural_language_request": "我們想改善工作效率。"},
    )

    assert clarification.status_code == 200
    assert clarification.json()["status"] == "clarification_required"
    assert len(clarification.json()["clarifying_questions"]) == 4

    ready_client = TestClient(create_app(chat_model=_model_for(_ready_intent())))
    ready = ready_client.post(
        "/v1/planning/interpret",
        json={
            "natural_language_request": "我們想改善工作效率。",
            "clarification_answers": {
                "data_classification": "internal",
                "external_processing_allowed": True,
                "offline_operation_required": False,
            },
        },
    )

    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"


def test_api_maps_missing_tool_call_and_invalid_tool_arguments_to_safe_502() -> None:
    no_tool_client = TestClient(
        create_app(
            chat_model=ScriptedToolCallingChatModel(
                messages=iter([AIMessage(content="沒有工具")])
            )
        )
    )
    invalid_tool_client = TestClient(
        create_app(
            chat_model=ScriptedToolCallingChatModel(
                messages=iter(
                    [
                        AIMessage(
                            content="",
                            tool_calls=[
                                {
                                    "name": "evaluate_planning_intent",
                                    "args": {"intent": {}},
                                    "id": "call-invalid-api",
                                }
                            ],
                        ),
                        AIMessage(content="停止"),
                    ]
                )
            )
        )
    )

    for client in (no_tool_client, invalid_tool_client):
        response = client.post(
            "/v1/planning/interpret",
            json={"natural_language_request": "敏感原始需求不可回傳"},
        )

        assert response.status_code == 502
        assert response.json()["error"]["code"] in {
            "no_planning_tool_call",
            "invalid_planning_tool_arguments",
        }
        assert "敏感原始需求不可回傳" not in response.text


def test_api_uses_safe_validation_errors() -> None:
    client = TestClient(create_app(chat_model=_model_for(_ready_intent())))

    response = client.post("/v1/planning/interpret", json={})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "request_validation_error"
    assert "input" not in response.json()["error"]["details"]
