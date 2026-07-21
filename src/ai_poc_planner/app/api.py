"""Minimal FastAPI boundary for the LangChain planning slice."""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from langchain_core.language_models import BaseChatModel
from pydantic import Field

from ai_poc_planner.agent.contracts import PlanningResult
from ai_poc_planner.agent.planning import (
    PlanningAgent,
    PlanningAgentExecutionError,
    build_planning_result,
)
from ai_poc_planner.domain.models import ContractModel, JSONValue, NonEmptyStr


class PlanningInterpretRequest(ContractModel):
    natural_language_request: NonEmptyStr
    clarification_answers: dict[str, JSONValue] = Field(default_factory=dict)


class PlanningInterpretResponse(PlanningResult):
    correlation_id: UUID


def _error_response(
    status_code: int,
    code: str,
    correlation_id: UUID,
    *,
    details: dict[str, object] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": "The planning request could not be completed.",
                "details": details or {},
                "correlation_id": str(correlation_id),
            }
        },
    )


def create_app(*, chat_model: BaseChatModel) -> FastAPI:
    """Compose an API only from the caller-provided LangChain chat model."""

    app = FastAPI(title="AI PoC Planner", version="0.1.0")
    planning_agent = PlanningAgent(chat_model)

    @app.exception_handler(RequestValidationError)
    async def request_validation_error(
        _: Request,
        error: RequestValidationError,
    ) -> JSONResponse:
        correlation_id = uuid4()
        fields = [
            ".".join(str(part) for part in item["loc"]) for item in error.errors()
        ]
        return _error_response(
            422,
            "request_validation_error",
            correlation_id,
            details={"fields": fields},
        )

    @app.exception_handler(PlanningAgentExecutionError)
    async def planning_agent_error(
        _: Request,
        error: PlanningAgentExecutionError,
    ) -> JSONResponse:
        return _error_response(502, error.code, uuid4())

    @app.exception_handler(Exception)
    async def unexpected_error(_: Request, __: Exception) -> JSONResponse:
        return _error_response(500, "internal_error", uuid4())

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/planning/interpret", response_model=PlanningInterpretResponse)
    def interpret(request: PlanningInterpretRequest) -> PlanningInterpretResponse:
        evaluation = planning_agent.interpret(
            natural_language_request=request.natural_language_request,
            clarification_answers=request.clarification_answers,
        )
        return PlanningInterpretResponse(
            **build_planning_result(evaluation).model_dump(),
            correlation_id=uuid4(),
        )

    return app
