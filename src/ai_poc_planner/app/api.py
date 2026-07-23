"""Minimal FastAPI boundary for the LangChain planning slice."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from uuid import UUID, uuid4

import httpx
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
from ai_poc_planner.application.provider_readiness import (
    ChatCompletionAdapter,
    ProviderReadinessError,
    ProviderReadinessService,
)
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
from ai_poc_planner.persistence.model_profiles import (
    LocalModelProfileRepository,
    ModelProfileNotFoundError,
    ModelProfileRepositoryError,
)
from ai_poc_planner.persistence.planning_runs import SQLitePlanningRunRepository
from ai_poc_planner.persistence.projects import SQLiteProjectRepository
from ai_poc_planner.persistence.schema import initialize_database
from ai_poc_planner.providers.base import ModelProvider
from ai_poc_planner.providers.openai_compatible import OpenAICompatibleChatAdapter
from ai_poc_planner.providers.profiles import (
    ModelProfile,
    ModelProfilePublic,
    ProviderConnectionStatus,
)


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


class ModelProfileCreateRequest(ContractModel):
    profile_name: NonEmptyStr
    base_url: str
    model_name: NonEmptyStr
    api_key: str | None = None
    is_enabled: bool = True


class ModelProfileUpdateRequest(ContractModel):
    profile_name: NonEmptyStr | None = None
    base_url: str | None = None
    model_name: NonEmptyStr | None = None
    api_key: str | None = None
    is_enabled: bool | None = None


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
    model_profile_repository: LocalModelProfileRepository | None = None,
    connection_adapter_factory: (
        Callable[[ModelProfile], ChatCompletionAdapter] | None
    ) = None,
) -> FastAPI:
    """Compose an API only from the caller-provided LangChain chat model."""

    @asynccontextmanager
    async def lifespan(lifespan_app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            owned_client = getattr(lifespan_app.state, "provider_http_client", None)
            if isinstance(owned_client, httpx.Client) and not owned_client.is_closed:
                owned_client.close()

    app = FastAPI(title="AI PoC Planner", version="0.1.0", lifespan=lifespan)
    planning_agent = PlanningAgent(chat_model)
    profile_repository = model_profile_repository or LocalModelProfileRepository()

    def app_owned_provider_client() -> httpx.Client:
        client = getattr(app.state, "provider_http_client", None)
        if isinstance(client, httpx.Client) and not client.is_closed:
            return client
        client = httpx.Client()
        app.state.provider_http_client = client
        return client

    def default_adapter(profile: ModelProfile) -> ChatCompletionAdapter:
        return OpenAICompatibleChatAdapter(
            base_url=str(profile.base_url),
            model_name=profile.model_name,
            api_key=(profile.api_key.get_secret_value() if profile.api_key else None),
            client=app_owned_provider_client(),
        )

    readiness = ProviderReadinessService(
        profiles=profile_repository,
        adapter_factory=connection_adapter_factory or default_adapter,
    )
    app.state.provider_readiness = readiness

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

    @app.exception_handler(ModelProfileRepositoryError)
    async def model_profile_error(
        _: Request, error: ModelProfileRepositoryError
    ) -> JSONResponse:
        status_code = 404 if isinstance(error, ModelProfileNotFoundError) else 409
        return _error_response(status_code, error.code, uuid4())

    @app.exception_handler(ProviderReadinessError)
    async def provider_readiness_error(
        _: Request, error: ProviderReadinessError
    ) -> JSONResponse:
        return _error_response(409, error.code, uuid4())

    @app.exception_handler(Exception)
    async def unexpected_error(_: Request, __: Exception) -> JSONResponse:
        return _error_response(500, "internal_error", uuid4())

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/v1/model-profiles", response_model=list[ModelProfilePublic])
    def list_model_profiles() -> list[ModelProfilePublic]:
        return [profile.to_public() for profile in profile_repository.list()]

    @app.post(
        "/v1/model-profiles",
        response_model=ModelProfilePublic,
        status_code=201,
    )
    def create_model_profile(request: ModelProfileCreateRequest) -> ModelProfilePublic:
        return profile_repository.create(
            profile_name=request.profile_name,
            base_url=request.base_url,
            model_name=request.model_name,
            api_key=request.api_key,
            is_enabled=request.is_enabled,
        ).to_public()

    @app.get("/v1/model-profiles/{profile_id}", response_model=ModelProfilePublic)
    def get_model_profile(profile_id: UUID) -> ModelProfilePublic:
        return profile_repository.get(profile_id).to_public()

    @app.patch("/v1/model-profiles/{profile_id}", response_model=ModelProfilePublic)
    def update_model_profile(
        profile_id: UUID, request: ModelProfileUpdateRequest
    ) -> ModelProfilePublic:
        updates = request.model_dump(exclude_unset=True)
        profile = profile_repository.update(profile_id, **updates)
        readiness.invalidate(profile_id)
        return profile.to_public()

    @app.delete("/v1/model-profiles/{profile_id}", status_code=204)
    def delete_model_profile(profile_id: UUID) -> None:
        profile_repository.delete(profile_id)
        readiness.invalidate(profile_id)

    @app.post(
        "/v1/model-profiles/{profile_id}/select",
        response_model=ModelProfilePublic,
    )
    def select_model_profile(profile_id: UUID) -> ModelProfilePublic:
        profile = profile_repository.select(profile_id)
        return profile.to_public()

    @app.post(
        "/v1/model-profiles/{profile_id}/test",
        response_model=ProviderConnectionStatus,
    )
    def test_model_profile(profile_id: UUID) -> ProviderConnectionStatus:
        return readiness.test(profile_id)

    @app.get("/v1/provider-status", response_model=ProviderConnectionStatus)
    def selected_provider_status() -> ProviderConnectionStatus:
        status = readiness.selected_status()
        if status is None:
            raise ProviderReadinessError("provider_not_ready")
        return status

    @app.get("/v1/provider-readiness", response_model=ProviderConnectionStatus)
    def formal_analysis_readiness() -> ProviderConnectionStatus:
        """Expose only the guard; legacy fake planning endpoints are not wired here."""

        return readiness.require_formal_analysis_ready()

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
        intent=outcome.evaluation.intent,
        opportunity_match=outcome.evaluation.opportunity_match,
        deployment_posture=outcome.evaluation.deployment_posture,
        clarifying_questions=run.clarifying_questions,
        assessment=run.assessment,
        proposal=run.proposal,
        markdown_report=run.markdown_report,
        correlation_id=uuid4(),
    )
