"""Repeatable scripted fake-mode composition for the local Streamlit demo."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from ai_poc_planner.agent.contracts import PlanningIntent
from ai_poc_planner.app.api import create_app
from ai_poc_planner.providers.fake import FakeModelProvider

_DEMO_DEPLOYMENT_FIELDS = {
    "data_classification",
    "external_processing_allowed",
    "offline_operation_required",
}

_INCOMPLETE_INTENT = PlanningIntent.model_validate(
    {
        "opportunity_input": {"business_problem_signals": ["improve work"]},
        "deployment_input": {},
        "request_summary": "固定展示：需要補充部署資訊",
    }
)

_READY_INTENT = PlanningIntent.model_validate(
    {
        "opportunity_input": {
            "business_problem_signals": ["customer support FAQ"],
        },
        "deployment_input": {
            "data_classification": "internal",
            "external_processing_allowed": True,
            "offline_operation_required": False,
        },
        "request_summary": "固定展示：客服 FAQ 輔助",
    }
)


class ScriptedDemoChatModel(GenericFakeChatModel):
    """Return one of two fixed tool calls; this does not analyse user language."""

    def bind_tools(self, tools: Sequence[object], **kwargs: object) -> object:
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        del stop, run_manager, kwargs
        if isinstance(messages[-1], ToolMessage):
            return ChatResult(
                generations=[ChatGeneration(message=AIMessage(content="展示工具結果已完成。"))]
            )
        answers = _clarification_answers(messages)
        intent = (
            _READY_INTENT
            if _DEMO_DEPLOYMENT_FIELDS.issubset(answers)
            else _INCOMPLETE_INTENT
        )
        return ChatResult(
            generations=[
                ChatGeneration(
                    message=AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "name": "evaluate_planning_intent",
                                "args": {"intent": intent.model_dump(mode="json")},
                                "id": "scripted-demo-planning-call",
                            }
                        ],
                    )
                )
            ]
        )


def _clarification_answers(messages: list[BaseMessage]) -> set[str]:
    content = messages[-1].content
    if not isinstance(content, str):
        return set()
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return set()
    answers = payload.get("clarification_answers", {})
    return set(answers) if isinstance(answers, dict) else set()


def create_demo_app(
    database_path: str | Path = Path("artifacts/streamlit-demo.sqlite3"),
) -> FastAPI:
    """Create the explicit local fake-mode server without a live provider."""

    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return create_app(
        chat_model=ScriptedDemoChatModel(messages=iter(())),
        database_path=path,
        assessment_provider=FakeModelProvider(),
    )
