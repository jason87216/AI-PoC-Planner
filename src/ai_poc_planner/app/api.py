"""Minimal FastAPI boundary for the LangChain planning slice."""

# ruff: noqa: E501

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import asynccontextmanager, contextmanager
from datetime import UTC, datetime
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
from ai_poc_planner.application.discovery_interview import (
    DiscoveryError,
    DiscoveryInterviewService,
)
from ai_poc_planner.application.evidence_analysis import (
    EvidenceAnalysisError,
    EvidenceAnalysisService,
)
from ai_poc_planner.application.persisted_planning import (
    PersistedPlanningFlow,
    PersistedPlanningOutcome,
)
from ai_poc_planner.application.planning_report import (
    PlanningReportError,
    PlanningReportService,
)
from ai_poc_planner.application.planning_runs import PlanningRunService
from ai_poc_planner.application.project_history import ProjectHistoryService
from ai_poc_planner.application.projects import AnalysisProjectService
from ai_poc_planner.application.provider_readiness import (
    ChatCompletionAdapter,
    ProviderReadinessError,
    ProviderReadinessService,
)
from ai_poc_planner.config import provider_readiness_timeout_seconds
from ai_poc_planner.domain.analysis import ValidatedAnalysisResult
from ai_poc_planner.domain.catalog import (
    DeploymentPostureAssessment,
    OpportunityMatchResult,
)
from ai_poc_planner.domain.discovery import (
    DiscoverySession,
    InitialBrief,
    InterviewQuestion,
    InterviewRoundAnswerSubmission,
    NaturalLanguageFeedback,
    NormalizedInitialBrief,
    UnderstandingCorrectionSubmission,
)
from ai_poc_planner.domain.enums import (
    FactStatus,
    InterviewRole,
    PlanningRunStatus,
    VisibleMessageKind,
)
from ai_poc_planner.domain.models import (
    ClarifyingQuestion,
    ContractModel,
    JSONValue,
    NonEmptyStr,
    PocProposal,
)
from ai_poc_planner.domain.planning_report import PersistedPlanningReport
from ai_poc_planner.domain.project_history import (
    FactRevision,
    PlanningProject,
    ProjectHistorySummary,
    ProjectVersion,
    VisibleConversationMessage,
)
from ai_poc_planner.domain.workflow import Assessment
from ai_poc_planner.persistence.analysis import SQLiteAnalysisRepository
from ai_poc_planner.persistence.connection import database_connection
from ai_poc_planner.persistence.discovery import SQLiteDiscoveryRepository
from ai_poc_planner.persistence.errors import (
    CompletedVersionImmutableError,
    CurrentVersionRequiredError,
    DatabasePreflightError,
    FactConfirmationInvalidError,
    FactConflictError,
    FactCorrectionInvalidError,
    FactCorrectionRequiredError,
    FactNotCurrentError,
    FactNotFoundError,
    FactReferenceInvalidError,
    InitialBriefAlreadyExistsError,
    InterviewAnswersIncompleteError,
    InterviewQuestionAlreadyAnsweredError,
    InterviewQuestionInvalidError,
    InterviewRoundLimitReachedError,
    InterviewSessionNotFoundError,
    InvalidInterviewTransitionError,
    InvalidPlanningRunTransitionError,
    InvalidProjectVersionTransitionError,
    InvalidVisibleMessageError,
    PersistenceError,
    PlanningRunNotFoundError,
    ProjectNotFoundError,
    ProjectVersionNotFoundError,
    UnderstandingAlreadyConfirmedError,
    UnderstandingConfirmationRequiredError,
)
from ai_poc_planner.persistence.model_profiles import (
    LocalModelProfileRepository,
    ModelProfileNotFoundError,
    ModelProfileRepositoryError,
)
from ai_poc_planner.persistence.planning_runs import SQLitePlanningRunRepository
from ai_poc_planner.persistence.project_history import SQLiteProjectHistoryRepository
from ai_poc_planner.persistence.projects import SQLiteProjectRepository
from ai_poc_planner.persistence.report import SQLitePlanningReportRepository
from ai_poc_planner.persistence.schema import (
    ensure_database_schema,
    initialize_database,
    validate_database_schema,
)
from ai_poc_planner.persistence.solution_catalog import SQLiteSolutionCatalogRepository
from ai_poc_planner.providers.base import (
    ModelProvider,
    ReasoningEffort,
    StructuredOutputMode,
)
from ai_poc_planner.providers.capabilities import OpenAICompatibleCapabilities
from ai_poc_planner.providers.errors import (
    ProviderOperation,
    ProviderOperationError,
    SafeProviderFailure,
)
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
    structured_output_mode: StructuredOutputMode | None = None
    reasoning_effort: ReasoningEffort | None = None
    capabilities: OpenAICompatibleCapabilities | None = None
    is_enabled: bool = True


class ModelProfileUpdateRequest(ContractModel):
    profile_name: NonEmptyStr | None = None
    base_url: str | None = None
    model_name: NonEmptyStr | None = None
    api_key: str | None = None
    structured_output_mode: StructuredOutputMode | None = None
    reasoning_effort: ReasoningEffort | None = None
    capabilities: OpenAICompatibleCapabilities | None = None
    is_enabled: bool | None = None


class ProjectCreateRequest(ContractModel):
    project_name: NonEmptyStr


class VisibleMessageCreateRequest(ContractModel):
    role: InterviewRole
    message_kind: VisibleMessageKind
    content: NonEmptyStr


class FactAssumptionRequest(ContractModel):
    fact_key: NonEmptyStr
    value: JSONValue
    reference_message_ids: list[UUID] = Field(min_length=1)


class FactReferenceRequest(ContractModel):
    fact_key: NonEmptyStr
    reference_message_ids: list[UUID] = Field(min_length=1)


class FactConfirmationRequest(ContractModel):
    reference_message_ids: list[UUID] = Field(min_length=1)


class FactCorrectionRequest(ContractModel):
    status: FactStatus
    value: JSONValue
    correction_reason: NonEmptyStr
    reference_message_ids: list[UUID] = Field(min_length=1)


class DiscoveryProjectResponse(ContractModel):
    project: PlanningProject
    version: ProjectVersion
    selected_model: object | None = None
    session: DiscoverySession
    normalized_brief: NormalizedInitialBrief


class DiscoveryProjectCreateRequest(InitialBrief):
    """Initial brief plus the safe reference to the profile chosen for this project."""

    model_profile_id: UUID | None = None


class ProjectModelProfileRequest(ContractModel):
    """Safe project binding request; provider configuration stays server-side."""

    model_profile_id: UUID


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


def _provider_error_response(
    code: str, operation: ProviderOperation, correlation_id: UUID
) -> JSONResponse:
    failure = SafeProviderFailure.from_code(code, operation)
    status = 502
    if code == "provider_timeout":
        status = 504
    elif code in {
        "provider_connection_failed",
        "provider_rate_limited",
        "provider_unavailable",
    }:
        status = 503
    return _error_response(
        status,
        failure.code,
        correlation_id,
        details={
            "operation": failure.operation.value,
            "retryable": failure.retryable,
            "user_action": failure.user_action,
        },
    )


_SAFE_PROVIDER_CODES = {
    "provider_auth_required",
    "provider_auth_failed",
    "provider_parameter_unsupported",
    "provider_structured_output_unsupported",
    "provider_not_found",
    "provider_timeout",
    "provider_connection_failed",
    "provider_rate_limited",
    "provider_unavailable",
    "provider_http_error",
    "provider_invalid_response",
    "provider_output_truncated",
    "provider_output_invalid",
    "provider_schema_invalid",
}

_SAFE_ANALYSIS_CODES = {
    "analysis_result_invalid": {
        "operation": ProviderOperation.ANALYSIS.value,
        "retryable": False,
        "user_action": "若持續失敗，請重新測試模型設定；問題仍存在時請查看本機啟動日誌。",
    }
}

_SAFE_ANALYSIS_CONFLICT_CODES = {
    "solution_category_mismatch": {
        "operation": ProviderOperation.ANALYSIS.value,
        "retryable": False,
        "user_action": (
            "請檢查核准方案目錄與正式評估類別的設定；修正後可安全重試評估。"
        ),
    },
}

_SAFE_REPORT_CODES = {
    "fact_reference_invalid": {
        "operation": ProviderOperation.REPORT.value,
        "retryable": False,
        "user_action": "請重新測試模型設定後再試；若持續發生，請查看本機啟動日誌。",
    },
}

_SAFE_DISCOVERY_CODES = {
    "interview_questions_unavailable": {
        "operation": ProviderOperation.DISCOVERY.value,
        "retryable": True,
        "user_action": "請重新產生訪談問題；若持續失敗，請重新測試模型設定並查看本機啟動日誌。",
    }
}

_SAFE_PROFILE_CODES = {
    "model_profile_auth_required",
    "model_profile_auth_forbidden",
    "model_profile_reasoning_unsupported",
    "model_profile_structured_output_invalid",
}


def create_app(
    *,
    chat_model: BaseChatModel,
    database_path: str | Path | None = None,
    assessment_provider: ModelProvider | None = None,
    model_profile_repository: LocalModelProfileRepository | None = None,
    connection_adapter_factory: (
        Callable[[ModelProfile], ChatCompletionAdapter] | None
    ) = None,
    interview_adapter_factory: (
        Callable[[ModelProfile], ChatCompletionAdapter] | None
    ) = None,
    analysis_adapter_factory: (
        Callable[[ModelProfile], ChatCompletionAdapter] | None
    ) = None,
    runtime_mode: str = "test",
    instance_id: str = "test-instance",
    started_at: datetime | None = None,
) -> FastAPI:
    """Compose an API only from the caller-provided LangChain chat model."""

    @asynccontextmanager
    async def lifespan(lifespan_app: FastAPI) -> AsyncIterator[None]:
        if database_path is not None:
            connection = database_connection(database_path)
            try:
                initialize_database(connection)
                validate_database_schema(connection)
            except Exception as error:
                raise DatabasePreflightError(
                    "local database preflight failed"
                ) from error
            finally:
                connection.close()
        try:
            yield
        finally:
            owned_client = getattr(lifespan_app.state, "provider_http_client", None)
            if isinstance(owned_client, httpx.Client) and not owned_client.is_closed:
                owned_client.close()

    app = FastAPI(title="AI PoC Planner", version="0.1.0", lifespan=lifespan)
    app.state.runtime_info = {
        "application": "ai-poc-planner",
        "api_contract_version": "1",
        "runtime_mode": runtime_mode,
        "instance_id": instance_id,
        "started_at": (started_at or datetime.now(UTC)).isoformat(),
        "data_persistence": "persistent"
        if runtime_mode in {"local", "uat"}
        else "temporary",
    }
    planning_agent = PlanningAgent(chat_model)
    profile_repository = model_profile_repository or LocalModelProfileRepository()
    readiness_timeout_seconds = provider_readiness_timeout_seconds()

    def app_owned_provider_client() -> httpx.Client:
        client = getattr(app.state, "provider_http_client", None)
        if isinstance(client, httpx.Client) and not client.is_closed:
            return client
        # Provider profiles are explicit endpoints; ambient proxy settings must not
        # silently redirect a local app's credential-bearing provider request.
        client = httpx.Client(trust_env=False)
        app.state.provider_http_client = client
        return client

    def default_adapter(profile: ModelProfile) -> ChatCompletionAdapter:
        return OpenAICompatibleChatAdapter(
            base_url=str(profile.base_url),
            model_name=profile.model_name,
            api_key=(profile.api_key.get_secret_value() if profile.api_key else None),
            client=app_owned_provider_client(),
            timeout_seconds=readiness_timeout_seconds,
            reasoning_effort=profile.reasoning_effort,
            capabilities=profile.effective_capabilities,
        )

    def default_interview_adapter(profile: ModelProfile) -> ChatCompletionAdapter:
        """Allow bounded local structured output without weakening connection tests."""

        return OpenAICompatibleChatAdapter(
            base_url=str(profile.base_url),
            model_name=profile.model_name,
            api_key=(profile.api_key.get_secret_value() if profile.api_key else None),
            client=app_owned_provider_client(),
            timeout_seconds=300,
            reasoning_effort=profile.reasoning_effort,
            capabilities=profile.effective_capabilities,
        )

    def default_analysis_adapter(profile: ModelProfile) -> ChatCompletionAdapter:
        return OpenAICompatibleChatAdapter(
            base_url=str(profile.base_url),
            model_name=profile.model_name,
            api_key=(profile.api_key.get_secret_value() if profile.api_key else None),
            client=app_owned_provider_client(),
            timeout_seconds=240,
            reasoning_effort=profile.reasoning_effort,
            capabilities=profile.effective_capabilities,
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
            ensure_database_schema(connection)
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

    @contextmanager
    def project_history_flow() -> Iterator[ProjectHistoryService]:
        if database_path is None:
            raise PersistedPlanningUnavailableError
        connection = database_connection(database_path)
        try:
            ensure_database_schema(connection)
            yield ProjectHistoryService(
                SQLiteProjectHistoryRepository(connection),
                selected_profile_getter=profile_repository.get_selected,
            )
        finally:
            connection.close()

    @contextmanager
    def discovery_flow() -> Iterator[DiscoveryInterviewService]:
        if database_path is None:
            raise PersistedPlanningUnavailableError
        connection = database_connection(database_path)
        try:
            ensure_database_schema(connection)
            history = ProjectHistoryService(
                SQLiteProjectHistoryRepository(connection),
                selected_profile_getter=profile_repository.get_selected,
            )
            yield DiscoveryInterviewService(
                history=history,
                sessions=SQLiteDiscoveryRepository(connection),
                readiness=readiness,
                selected_profile_getter=profile_repository.get_selected,
                profile_getter=profile_repository.get,
                adapter_factory=interview_adapter_factory or default_interview_adapter,
            )
        finally:
            connection.close()

    @contextmanager
    def analysis_flow() -> Iterator[EvidenceAnalysisService]:
        if database_path is None:
            raise PersistedPlanningUnavailableError
        connection = database_connection(database_path)
        try:
            ensure_database_schema(connection)
            history = ProjectHistoryService(
                SQLiteProjectHistoryRepository(connection),
                selected_profile_getter=profile_repository.get_selected,
            )
            yield EvidenceAnalysisService(
                history=history,
                sessions=SQLiteDiscoveryRepository(connection),
                analyses=SQLiteAnalysisRepository(connection),
                readiness=readiness,
                selected_profile_getter=profile_repository.get_selected,
                profile_getter=profile_repository.get,
                adapter_factory=analysis_adapter_factory or default_analysis_adapter,
                catalog=SQLiteSolutionCatalogRepository(connection),
            )
        finally:
            connection.close()

    @contextmanager
    def report_flow() -> Iterator[PlanningReportService]:
        if database_path is None:
            raise PersistedPlanningUnavailableError
        connection = database_connection(database_path)
        try:
            ensure_database_schema(connection)
            yield PlanningReportService(
                history=ProjectHistoryService(
                    SQLiteProjectHistoryRepository(connection),
                    selected_profile_getter=profile_repository.get_selected,
                ),
                sessions=SQLiteDiscoveryRepository(connection),
                analyses=SQLiteAnalysisRepository(connection),
                reports=SQLitePlanningReportRepository(connection),
                readiness=readiness,
                selected_profile_getter=profile_repository.get_selected,
                profile_getter=profile_repository.get,
                adapter_factory=analysis_adapter_factory or default_analysis_adapter,
                catalog=SQLiteSolutionCatalogRepository(connection),
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
        for item in error.errors():
            message = str(item.get("msg", ""))
            for code in _SAFE_PROFILE_CODES:
                if code in message:
                    return _error_response(422, code, correlation_id)
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
        if isinstance(
            error,
            (
                PlanningRunNotFoundError,
                ProjectNotFoundError,
                ProjectVersionNotFoundError,
                FactNotFoundError,
                InterviewSessionNotFoundError,
            ),
        ):
            return _error_response(404, error.code, uuid4())
        if isinstance(
            error,
            (
                InvalidPlanningRunTransitionError,
                InvalidProjectVersionTransitionError,
                CompletedVersionImmutableError,
                CurrentVersionRequiredError,
                FactConfirmationInvalidError,
                FactConflictError,
                FactCorrectionInvalidError,
                FactCorrectionRequiredError,
                FactNotCurrentError,
                FactReferenceInvalidError,
                InvalidVisibleMessageError,
                InitialBriefAlreadyExistsError,
                InvalidInterviewTransitionError,
                UnderstandingConfirmationRequiredError,
                UnderstandingAlreadyConfirmedError,
                InterviewRoundLimitReachedError,
                InterviewAnswersIncompleteError,
                InterviewQuestionInvalidError,
                InterviewQuestionAlreadyAnsweredError,
            ),
        ):
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
        if error.failure is not None:
            return _provider_error_response(
                error.code, error.failure.operation, uuid4()
            )
        return _error_response(409, error.code, uuid4())

    @app.exception_handler(ProviderOperationError)
    async def provider_operation_error(
        _: Request, error: ProviderOperationError
    ) -> JSONResponse:
        return _provider_error_response(error.code, error.operation, uuid4())

    @app.exception_handler(DiscoveryError)
    async def discovery_error(_: Request, error: DiscoveryError) -> JSONResponse:
        if error.code in _SAFE_PROVIDER_CODES:
            return _provider_error_response(
                error.code, ProviderOperation.DISCOVERY, uuid4()
            )
        if error.code in _SAFE_DISCOVERY_CODES:
            return _error_response(
                502,
                error.code,
                uuid4(),
                details=_SAFE_DISCOVERY_CODES[error.code],
            )
        return _error_response(
            502 if error.code == "provider_output_invalid" else 409, error.code, uuid4()
        )

    @app.exception_handler(EvidenceAnalysisError)
    async def analysis_error(_: Request, error: EvidenceAnalysisError) -> JSONResponse:
        if error.code in _SAFE_PROVIDER_CODES:
            return _provider_error_response(
                error.code, ProviderOperation.ANALYSIS, uuid4()
            )
        if error.code in _SAFE_ANALYSIS_CODES:
            return _error_response(
                502,
                error.code,
                uuid4(),
                details=_SAFE_ANALYSIS_CODES[error.code],
            )
        if error.code in _SAFE_ANALYSIS_CONFLICT_CODES:
            return _error_response(
                409,
                error.code,
                uuid4(),
                details=_SAFE_ANALYSIS_CONFLICT_CODES[error.code],
            )
        status = 502 if error.code == "provider_output_invalid" else 409
        if error.code == "analysis_not_found":
            status = 404
        return _error_response(status, error.code, uuid4())

    @app.exception_handler(PlanningReportError)
    async def report_error(_: Request, error: PlanningReportError) -> JSONResponse:
        if error.code in _SAFE_PROVIDER_CODES:
            return _provider_error_response(
                error.code, ProviderOperation.REPORT, uuid4()
            )
        if error.code in _SAFE_REPORT_CODES:
            return _error_response(
                409,
                error.code,
                uuid4(),
                details=_SAFE_REPORT_CODES[error.code],
            )
        status = 502 if error.code == "provider_output_invalid" else 409
        if error.code in {"report_not_found", "analysis_not_found"}:
            status = 404
        return _error_response(status, error.code, uuid4())

    @app.exception_handler(Exception)
    async def unexpected_error(_: Request, __: Exception) -> JSONResponse:
        return _error_response(500, "internal_error", uuid4())

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/v1/runtime-info")
    def runtime_info() -> dict[str, str]:
        """Return a secret-free identity contract for local runtime validation."""

        return app.state.runtime_info

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
            structured_output_mode=request.structured_output_mode,
            reasoning_effort=request.reasoning_effort,
            capabilities=request.capabilities,
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

    @app.get(
        "/v1/model-profiles/{profile_id}/status",
        response_model=ProviderConnectionStatus,
    )
    def model_profile_status(profile_id: UUID) -> ProviderConnectionStatus:
        return readiness.status_for(profile_repository.get(profile_id))

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

    @app.post(
        "/v1/discovery-projects",
        response_model=DiscoveryProjectResponse,
        status_code=201,
    )
    def create_discovery_project(
        request: DiscoveryProjectCreateRequest,
    ) -> DiscoveryProjectResponse:
        with discovery_flow() as discovery:
            profile = (
                profile_repository.get(request.model_profile_id)
                if request.model_profile_id is not None
                else None
            )
            project, version, session, normalized = discovery.create_initial_brief(
                InitialBrief(**request.model_dump(exclude={"model_profile_id"})),
                selected_profile=profile,
            )
            return DiscoveryProjectResponse(
                project=project,
                version=version,
                selected_model=version.selected_model,
                session=session,
                normalized_brief=normalized,
            )

    @app.get(
        "/v1/projects/{project_id}/versions/{version_number}/discovery",
        response_model=DiscoverySession,
    )
    def get_discovery_session(
        project_id: UUID, version_number: int
    ) -> DiscoverySession:
        with discovery_flow() as discovery:
            return discovery.get_session(project_id, version_number)

    @app.post(
        "/v1/projects/{project_id}/versions/{version_number}/understanding",
        response_model=DiscoverySession,
    )
    def generate_requirement_understanding(
        project_id: UUID, version_number: int
    ) -> DiscoverySession:
        with discovery_flow() as discovery:
            session, _ = discovery.generate_understanding(project_id, version_number)
            return session

    @app.post(
        "/v1/projects/{project_id}/versions/{version_number}/understanding/confirm",
        response_model=DiscoverySession,
    )
    def confirm_requirement_understanding(
        project_id: UUID, version_number: int
    ) -> DiscoverySession:
        with discovery_flow() as discovery:
            return discovery.confirm_understanding(project_id, version_number)

    @app.post(
        "/v1/projects/{project_id}/versions/{version_number}/understanding/corrections",
        response_model=DiscoverySession,
    )
    def submit_understanding_corrections(
        project_id: UUID,
        version_number: int,
        request: UnderstandingCorrectionSubmission,
    ) -> DiscoverySession:
        with discovery_flow() as discovery:
            return discovery.submit_corrections(project_id, version_number, request)

    @app.post(
        "/v1/projects/{project_id}/versions/{version_number}/understanding/feedback",
        response_model=DiscoverySession,
    )
    def submit_understanding_feedback(
        project_id: UUID,
        version_number: int,
        request: NaturalLanguageFeedback,
    ) -> DiscoverySession:
        with discovery_flow() as discovery:
            return discovery.submit_natural_language_feedback(
                project_id, version_number, request
            )

    @app.post(
        "/v1/projects/{project_id}/versions/{version_number}/interview-rounds",
        response_model=list[InterviewQuestion],
    )
    def generate_interview_round(
        project_id: UUID, version_number: int
    ) -> list[InterviewQuestion]:
        with discovery_flow() as discovery:
            _, questions = discovery.generate_round(project_id, version_number)
            return questions

    @app.get(
        "/v1/projects/{project_id}/versions/{version_number}/interview-questions",
        response_model=list[InterviewQuestion],
    )
    def list_interview_questions(
        project_id: UUID, version_number: int
    ) -> list[InterviewQuestion]:
        with discovery_flow() as discovery:
            return discovery.list_questions(project_id, version_number)

    @app.post(
        "/v1/projects/{project_id}/versions/{version_number}/interview-answers",
        response_model=DiscoverySession,
    )
    def submit_interview_answers(
        project_id: UUID, version_number: int, request: InterviewRoundAnswerSubmission
    ) -> DiscoverySession:
        with discovery_flow() as discovery:
            return discovery.submit_round_answers(project_id, version_number, request)

    @app.post("/v1/projects", response_model=ProjectVersion, status_code=201)
    def create_project(request: ProjectCreateRequest) -> ProjectVersion:
        with project_history_flow() as history:
            _, version = history.create_project(request.project_name)
            return version

    @app.get("/v1/projects", response_model=list[ProjectHistorySummary])
    def list_projects() -> list[ProjectHistorySummary]:
        with project_history_flow() as history:
            return history.list_projects()

    @app.delete("/v1/projects/{project_id}", status_code=204)
    def archive_project(project_id: UUID) -> None:
        with project_history_flow() as history:
            history.archive_project(project_id)

    @app.get("/v1/projects/{project_id}", response_model=PlanningProject)
    def get_project(project_id: UUID) -> PlanningProject:
        with project_history_flow() as history:
            return history.get_project(project_id)

    @app.get("/v1/projects/{project_id}/versions", response_model=list[ProjectVersion])
    def list_project_versions(project_id: UUID) -> list[ProjectVersion]:
        with project_history_flow() as history:
            return history.list_versions(project_id)

    @app.get(
        "/v1/projects/{project_id}/versions/{version_number}",
        response_model=ProjectVersion,
    )
    def get_project_version(project_id: UUID, version_number: int) -> ProjectVersion:
        with project_history_flow() as history:
            return history.get_version(project_id, version_number)

    @app.post(
        "/v1/projects/{project_id}/versions/{version_number}/model-profile",
        response_model=ProjectVersion,
    )
    def bind_project_model_profile(
        project_id: UUID,
        version_number: int,
        request: ProjectModelProfileRequest,
    ) -> ProjectVersion:
        profile = profile_repository.get(request.model_profile_id)
        readiness.require_profile_ready(profile.id)
        with project_history_flow() as history:
            return history.bind_model_profile(project_id, version_number, profile)

    @app.post(
        "/v1/projects/{project_id}/versions/{version_number}/complete",
        response_model=ProjectVersion,
    )
    def complete_project_version(
        project_id: UUID, version_number: int
    ) -> ProjectVersion:
        with project_history_flow() as history:
            return history.complete_version(project_id, version_number)

    @app.post(
        "/v1/projects/{project_id}/versions/{version_number}/next",
        response_model=ProjectVersion,
        status_code=201,
    )
    def create_next_project_version(
        project_id: UUID, version_number: int
    ) -> ProjectVersion:
        with project_history_flow() as history:
            return history.create_next_version(project_id, version_number)

    @app.post(
        "/v1/projects/{project_id}/versions/{version_number}/messages",
        response_model=VisibleConversationMessage,
        status_code=201,
    )
    def append_visible_message(
        project_id: UUID,
        version_number: int,
        request: VisibleMessageCreateRequest,
    ) -> VisibleConversationMessage:
        with project_history_flow() as history:
            return history.append_message(
                project_id,
                version_number,
                role=request.role,
                message_kind=request.message_kind.value,
                content=request.content,
            )

    @app.get(
        "/v1/projects/{project_id}/versions/{version_number}/messages",
        response_model=list[VisibleConversationMessage],
    )
    def list_visible_messages(
        project_id: UUID, version_number: int
    ) -> list[VisibleConversationMessage]:
        with project_history_flow() as history:
            return history.list_messages(project_id, version_number)

    @app.post(
        "/v1/projects/{project_id}/versions/{version_number}/facts/assumptions",
        response_model=FactRevision,
        status_code=201,
    )
    def propose_fact_assumption(
        project_id: UUID,
        version_number: int,
        request: FactAssumptionRequest,
    ) -> FactRevision:
        with project_history_flow() as history:
            return history.propose_assumption(
                project_id,
                version_number,
                fact_key=request.fact_key,
                value=request.value,
                reference_message_ids=request.reference_message_ids,
            )

    @app.post(
        "/v1/projects/{project_id}/versions/{version_number}/facts/unknown",
        response_model=FactRevision,
        status_code=201,
    )
    def record_unknown_fact(
        project_id: UUID,
        version_number: int,
        request: FactReferenceRequest,
    ) -> FactRevision:
        with project_history_flow() as history:
            return history.record_unknown_or_missing(
                project_id,
                version_number,
                fact_key=request.fact_key,
                status=FactStatus.UNKNOWN,
                reference_message_ids=request.reference_message_ids,
            )

    @app.post(
        "/v1/projects/{project_id}/versions/{version_number}/facts/missing",
        response_model=FactRevision,
        status_code=201,
    )
    def record_missing_fact(
        project_id: UUID,
        version_number: int,
        request: FactReferenceRequest,
    ) -> FactRevision:
        with project_history_flow() as history:
            return history.record_unknown_or_missing(
                project_id,
                version_number,
                fact_key=request.fact_key,
                status=FactStatus.MISSING,
                reference_message_ids=request.reference_message_ids,
            )

    @app.post(
        "/v1/projects/{project_id}/versions/{version_number}/facts/{fact_id}/confirm",
        response_model=FactRevision,
    )
    def confirm_fact_assumption(
        project_id: UUID,
        version_number: int,
        fact_id: UUID,
        request: FactConfirmationRequest,
    ) -> FactRevision:
        with project_history_flow() as history:
            return history.confirm_assumption(
                project_id,
                version_number,
                fact_id,
                reference_message_ids=request.reference_message_ids,
            )

    @app.post(
        "/v1/projects/{project_id}/versions/{version_number}/facts/{fact_id}/correct",
        response_model=FactRevision,
    )
    def correct_current_fact(
        project_id: UUID,
        version_number: int,
        fact_id: UUID,
        request: FactCorrectionRequest,
    ) -> FactRevision:
        with project_history_flow() as history:
            return history.correct_fact(
                project_id,
                version_number,
                fact_id,
                status=request.status,
                value=request.value,
                correction_reason=request.correction_reason,
                reference_message_ids=request.reference_message_ids,
            )

    @app.get(
        "/v1/projects/{project_id}/versions/{version_number}/facts",
        response_model=list[FactRevision],
    )
    def list_current_facts(project_id: UUID, version_number: int) -> list[FactRevision]:
        with project_history_flow() as history:
            return history.list_current_facts(project_id, version_number)

    @app.get(
        "/v1/projects/{project_id}/versions/{version_number}/facts/history",
        response_model=list[FactRevision],
    )
    def list_fact_history(project_id: UUID, version_number: int) -> list[FactRevision]:
        with project_history_flow() as history:
            return history.list_fact_history(project_id, version_number)

    @app.post(
        "/v1/projects/{project_id}/versions/{version_number}/analysis",
        response_model=ValidatedAnalysisResult,
        status_code=201,
    )
    def create_analysis(
        project_id: UUID, version_number: int
    ) -> ValidatedAnalysisResult:
        with analysis_flow() as analysis:
            return analysis.create(project_id, version_number)

    @app.get(
        "/v1/projects/{project_id}/versions/{version_number}/analysis",
        response_model=ValidatedAnalysisResult,
    )
    def get_analysis(project_id: UUID, version_number: int) -> ValidatedAnalysisResult:
        with analysis_flow() as analysis:
            return analysis.get(project_id, version_number)

    @app.post(
        "/v1/projects/{project_id}/versions/{version_number}/report",
        response_model=PersistedPlanningReport,
        status_code=201,
    )
    def create_report(project_id: UUID, version_number: int) -> PersistedPlanningReport:
        with report_flow() as report:
            return report.create(project_id, version_number)

    @app.get(
        "/v1/projects/{project_id}/versions/{version_number}/report",
        response_model=PersistedPlanningReport,
    )
    def get_report(project_id: UUID, version_number: int) -> PersistedPlanningReport:
        with report_flow() as report:
            return report.get(project_id, version_number)

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
