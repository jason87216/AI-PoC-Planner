"""Minimal FastAPI boundary for the LangChain planning slice."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from langchain_core.language_models import BaseChatModel
from pydantic import Field

from ai_poc_planner.agent.contracts import (
    PlanningIntent,
    PlanningResult,
)
from ai_poc_planner.agent.planning import (
    PlanningAgent,
    PlanningAgentExecutionError,
    build_planning_result,
)
from ai_poc_planner.application.persisted_planning import (
    PersistedPlanningFlow,
    PersistedPlanningOutcome,
)
from ai_poc_planner.application.planning_runs import PlanningRunService
from ai_poc_planner.application.projects import AnalysisProjectService
from ai_poc_planner.domain.catalog import (
    DeploymentPostureAssessment,
    OpportunityMatchResult,
)
from ai_poc_planner.domain.enums import PlanningRunStatus
from ai_poc_planner.domain.models import (
    ClarifyingQuestion,
    ContractModel,
    JSONValue,
    NonEmptyStr,
    PocProposal,
)
from ai_poc_planner.domain.workflow import Assessment
from ai_poc_planner.persistence.connection import database_connection
from ai_poc_planner.persistence.errors import (
    InvalidPlanningRunTransitionError,
    PersistenceError,
    PlanningRunNotFoundError,
)
from ai_poc_planner.persistence.planning_runs import SQLitePlanningRunRepository
from ai_poc_planner.persistence.projects import SQLiteProjectRepository
from ai_poc_planner.persistence.schema import initialize_database
from ai_poc_planner.providers.base import ModelProvider


class PlanningInterpretRequest(ContractModel):
    natural_language_request: NonEmptyStr
    clarification_answers: dict[str, JSONValue] = Field(default_factory=dict)


class PlanningInterpretResponse(PlanningResult):
    correlation_id: UUID


class PlanningRunCreateRequest(ContractModel):
    natural_language_request: NonEmptyStr
    clarification_answers: dict[str, JSONValue] = Field(default_factory=dict)


class PlanningRunClarificationRequest(ContractModel):
    clarification_answers: dict[str, JSONValue] = Field(min_length=1)


class PersistedPlanningRunResponse(ContractModel):
    run_id: UUID
    status: PlanningRunStatus
    original_request: NonEmptyStr
    known_information: dict[str, JSONValue]
    clarification_answers: dict[str, JSONValue]
    intent: PlanningIntent
    opportunity_match: OpportunityMatchResult
    deployment_posture: DeploymentPostureAssessment
    clarifying_questions: list[ClarifyingQuestion]
    assessment: Assessment | None
    proposal: PocProposal | None
    markdown_report: NonEmptyStr | None
    correlation_id: UUID


class PersistedPlanningUnavailableError(RuntimeError):
    code = "persistence_not_configured"


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


def create_app(
    *,
    chat_model: BaseChatModel,
    database_path: str | Path | None = None,
    assessment_provider: ModelProvider | None = None,
) -> FastAPI:
    """Compose an API only from the caller-provided LangChain chat model."""

    app = FastAPI(title="AI PoC Planner", version="0.1.0")
    planning_agent = PlanningAgent(chat_model)

    @contextmanager
    def persisted_flow() -> Iterator[PersistedPlanningFlow]:
        if database_path is None or assessment_provider is None:
            raise PersistedPlanningUnavailableError
        connection = database_connection(database_path)
        try:
            initialize_database(connection)
            project_repository = SQLiteProjectRepository(connection)
            yield PersistedPlanningFlow(
                planning_agent=planning_agent,
                projects=AnalysisProjectService(project_repository),
                planning_runs=PlanningRunService(
                    SQLitePlanningRunRepository(connection),
                    project_repository,
                ),
                project_reader=project_repository,
                assessment_provider=assessment_provider,
            )
        finally:
            connection.close()

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

    @app.exception_handler(PersistedPlanningUnavailableError)
    async def persisted_planning_unavailable(
        _: Request,
        __: PersistedPlanningUnavailableError,
    ) -> JSONResponse:
        return _error_response(503, "persistence_not_configured", uuid4())

    @app.exception_handler(PersistenceError)
    async def persistence_error(_: Request, error: PersistenceError) -> JSONResponse:
        if isinstance(error, PlanningRunNotFoundError):
            return _error_response(404, error.code, uuid4())
        if isinstance(error, InvalidPlanningRunTransitionError):
            return _error_response(409, error.code, uuid4())
        return _error_response(500, error.code, uuid4())

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

    @app.post(
        "/v1/planning/runs",
        response_model=PersistedPlanningRunResponse,
        status_code=201,
    )
    def create_planning_run(
        request: PlanningRunCreateRequest,
    ) -> PersistedPlanningRunResponse:
        with persisted_flow() as flow:
            return _persisted_response(
                flow.start(
                    request.natural_language_request,
                    request.clarification_answers,
                )
            )

    @app.post(
        "/v1/planning/runs/{run_id}/clarifications",
        response_model=PersistedPlanningRunResponse,
    )
    def submit_planning_clarification(
        run_id: UUID,
        request: PlanningRunClarificationRequest,
    ) -> PersistedPlanningRunResponse:
        with persisted_flow() as flow:
            return _persisted_response(
                flow.submit_clarification(run_id, request.clarification_answers)
            )

    @app.get(
        "/v1/planning/runs/{run_id}",
        response_model=PersistedPlanningRunResponse,
    )
    def get_planning_run(run_id: UUID) -> PersistedPlanningRunResponse:
        with persisted_flow() as flow:
            return _persisted_response(flow.load(run_id))

    return app


def _persisted_response(
    outcome: PersistedPlanningOutcome,
) -> PersistedPlanningRunResponse:
    run = outcome.run
    return PersistedPlanningRunResponse(
        run_id=run.id,
        status=run.status,
        original_request=run.original_request,
        known_information=run.known_information,
        clarification_answers=run.clarification_answers,
        intent=outcome.evaluation.intent,
        opportunity_match=outcome.evaluation.opportunity_match,
        deployment_posture=outcome.evaluation.deployment_posture,
        clarifying_questions=run.clarifying_questions,
        assessment=run.assessment,
        proposal=run.proposal,
        markdown_report=run.markdown_report,
        correlation_id=uuid4(),
    )
