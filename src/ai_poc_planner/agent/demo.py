"""Scripted offline demonstration for the bounded LangChain planning slice."""

from __future__ import annotations

from collections.abc import Sequence

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from ai_poc_planner.agent.contracts import PlanningIntent, PlanningResult
from ai_poc_planner.agent.planning import PlanningAgent, build_planning_result


class ScriptedPlanningDemoChatModel(GenericFakeChatModel):
    """Use LangChain's official fake model to demonstrate a known tool trajectory."""

    def bind_tools(self, tools: Sequence[object], **kwargs: object) -> object:
        return self


def run_scripted_planning_demo() -> PlanningResult:
    """Run one offline Agent invocation.

    It demonstrates orchestration, not NLP quality.
    """

    intent = PlanningIntent.model_validate(
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
    model = ScriptedPlanningDemoChatModel(
        messages=iter(
            [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "evaluate_planning_intent",
                            "args": {"intent": intent.model_dump(mode="json")},
                            "id": "planning-demo-tool-call",
                        }
                    ],
                ),
                AIMessage(content="工具結果已準備完成。"),
            ]
        )
    )
    evaluation = PlanningAgent(model).interpret(
        natural_language_request="客服團隊想用內部 FAQ 協助回覆客戶問題。",
        clarification_answers={},
    )
    return build_planning_result(evaluation)
