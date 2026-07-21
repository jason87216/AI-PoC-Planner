"""Single-Agent LangChain orchestration around one typed planning tool."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.language_models import BaseChatModel

from ai_poc_planner.agent.contracts import (
    PlanningEvaluation,
    PlanningIntent,
    PlanningResult,
)
from ai_poc_planner.application.catalog_matching import match_opportunities
from ai_poc_planner.application.deployment_posture import assess_deployment_posture
from ai_poc_planner.domain.catalog import DeploymentAssessmentStatus
from ai_poc_planner.domain.models import ClarifyingQuestion


class PlanningAgentExecutionError(RuntimeError):
    """A safe, stable error raised when the Agent cannot execute the typed tool."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass
class _PlanningToolCapture:
    evaluation: PlanningEvaluation | None = None
    invalid_arguments: bool = False


_QUESTION_TEMPLATES = {
    "business_problem_signals": (
        "請說明要改善的業務結果、資料型態，以及人工覆核邊界。",
        "目前無法對應可信的 AI opportunity candidate。",
    ),
    "data_classification": (
        (
            "資料保密等級為何？請選擇 public、internal、confidential 或 "
            "highly_confidential。"
        ),
        "部署姿態需要資料分類。",
    ),
    "external_processing_allowed": (
        "是否允許受控的外部環境處理此工作負載？",
        "部署姿態需要確認外部處理限制。",
    ),
    "offline_operation_required": (
        "此 PoC 是否必須完全離線運作？",
        "部署姿態需要確認離線需求。",
    ),
    "approved_isolated_environment": (
        "是否已有核准的隔離雲端或地端環境可處理高度機密資料？",
        "高度機密資料需要核准的隔離環境。",
    ),
}

_QUESTION_ORDER = tuple(_QUESTION_TEMPLATES)


def evaluate_planning_intent(intent: PlanningIntent) -> PlanningEvaluation:
    """Run the existing deterministic planning services for one validated intent."""

    return PlanningEvaluation(
        intent=intent,
        opportunity_match=match_opportunities(intent.opportunity_input),
        deployment_posture=assess_deployment_posture(intent.deployment_input),
    )


def _planning_tool(capture: _PlanningToolCapture) -> Any:
    @tool
    def evaluate_planning_intent_tool(intent: PlanningIntent) -> dict[str, object]:
        """Evaluate a validated intent with the approved local planning rules."""

        evaluation = evaluate_planning_intent(intent)
        capture.evaluation = evaluation
        return evaluation.model_dump(mode="json")

    evaluate_planning_intent_tool.name = "evaluate_planning_intent"

    def handle_validation_error(_: Exception) -> str:
        capture.invalid_arguments = True
        return "Invalid planning tool arguments."

    evaluate_planning_intent_tool.handle_validation_error = handle_validation_error
    return evaluate_planning_intent_tool


class PlanningAgent:
    """Invoke one LangChain Agent and accept only its successful tool output."""

    def __init__(self, chat_model: BaseChatModel) -> None:
        self._chat_model = chat_model

    def interpret(
        self,
        *,
        natural_language_request: str,
        clarification_answers: dict[str, object],
    ) -> PlanningEvaluation:
        capture = _PlanningToolCapture()
        agent = create_agent(
            model=self._chat_model,
            tools=[_planning_tool(capture)],
            system_prompt=(
                "Extract a PlanningIntent from the user's natural-language request and "
                "clarification answers. Call evaluate_planning_intent with it. Do not "
                "produce scores, recommendations, hard-gate decisions, proposals, or "
                "reports."
            ),
        )
        try:
            agent.invoke(
                {
                    "messages": [
                        {
                            "role": "user",
                            "content": json.dumps(
                                {
                                    "natural_language_request": (
                                        natural_language_request
                                    ),
                                    "clarification_answers": clarification_answers,
                                },
                                ensure_ascii=False,
                            ),
                        }
                    ]
                }
            )
        except Exception as error:
            raise PlanningAgentExecutionError("agent_execution_failed") from error
        if capture.invalid_arguments:
            raise PlanningAgentExecutionError("invalid_planning_tool_arguments")
        if capture.evaluation is None:
            raise PlanningAgentExecutionError("no_planning_tool_call")
        return capture.evaluation


def build_planning_result(evaluation: PlanningEvaluation) -> PlanningResult:
    """Turn deterministic gaps into fixed, bounded Traditional-Chinese questions."""

    needed_fields: set[str] = set(
        evaluation.deployment_posture.missing_deployment_information
    )
    if not evaluation.opportunity_match.candidates:
        needed_fields.add("business_problem_signals")
    questions = [
        _clarifying_question(field, priority)
        for priority, field in enumerate(_QUESTION_ORDER, start=1)
        if field in needed_fields
    ][:4]
    requires_clarification = (
        not evaluation.opportunity_match.candidates
        or evaluation.deployment_posture.status
        is DeploymentAssessmentStatus.CLARIFICATION_REQUIRED
    )
    return PlanningResult(
        **evaluation.model_dump(),
        status="clarification_required" if requires_clarification else "ready",
        clarifying_questions=questions,
    )


def _clarifying_question(field: str, priority: int) -> ClarifyingQuestion:
    question, reason = _QUESTION_TEMPLATES[field]
    return ClarifyingQuestion(
        field=field,
        question=question,
        reason=reason,
        priority=priority,
    )
