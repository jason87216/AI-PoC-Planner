from __future__ import annotations

from collections.abc import Sequence

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from ai_poc_planner.agent.contracts import PlanningIntent
from ai_poc_planner.agent.planning import (
    PlanningAgent,
    PlanningAgentExecutionError,
    build_planning_result,
    evaluate_planning_intent,
)


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
                "id": "call-planning-1",
            }
        ],
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
            "request_summary": "客服 FAQ 輔助",
        }
    )


def test_agent_uses_typed_tool_result_instead_of_final_model_claim() -> None:
    model = ScriptedToolCallingChatModel(
        messages=iter([_tool_call(_ready_intent()), AIMessage(content="任意最終文字")])
    )

    result = PlanningAgent(model).interpret(
        natural_language_request="客服團隊想用內部 FAQ 協助回覆客戶問題。",
        clarification_answers={},
    )

    assert result.intent == _ready_intent()
    assert result.opportunity_match.candidates[0].opportunity_type.value == (
        "customer_service_assist"
    )
    assert result.deployment_posture.recommended_posture is not None
    assert "weighted_score" not in type(result).model_fields
    assert "recommendation" not in type(result).model_fields


def test_agent_rejects_a_trajectory_without_a_successful_planning_tool_call() -> None:
    model = ScriptedToolCallingChatModel(
        messages=iter([AIMessage(content="沒有呼叫工具")])
    )

    with pytest.raises(PlanningAgentExecutionError) as error:
        PlanningAgent(model).interpret(
            natural_language_request="請幫我規劃 AI 專案。",
            clarification_answers={},
        )

    assert error.value.code == "no_planning_tool_call"


def test_agent_reports_invalid_tool_arguments_with_a_stable_error() -> None:
    model = ScriptedToolCallingChatModel(
        messages=iter(
            [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "evaluate_planning_intent",
                            "args": {"intent": {"opportunity_input": {}}},
                            "id": "call-invalid-1",
                        }
                    ],
                ),
                AIMessage(content="工具參數不正確"),
            ]
        )
    )

    with pytest.raises(PlanningAgentExecutionError) as error:
        PlanningAgent(model).interpret(
            natural_language_request="請幫我規劃 AI 專案。",
            clarification_answers={},
        )

    assert error.value.code == "invalid_planning_tool_arguments"


def test_clarification_is_deterministic_limited_and_ordered() -> None:
    result = build_planning_result(
        evaluate_planning_intent(
            PlanningIntent.model_validate(
                {
                    "opportunity_input": {"business_problem_signals": ["improve work"]},
                    "deployment_input": {},
                }
            )
        )
    )

    assert result.status == "clarification_required"
    assert [question.field for question in result.clarifying_questions] == [
        "business_problem_signals",
        "data_classification",
        "external_processing_allowed",
        "offline_operation_required",
    ]
    assert len(result.clarifying_questions) == 4
