"""Small structured provider boundaries independent of any model vendor."""

from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from pydantic import Field, model_validator

from ai_poc_planner.domain.facts import AssessmentFacts
from ai_poc_planner.domain.models import (
    AnalysisProject,
    ClarifyingQuestion,
    ContractModel,
    EvidenceReference,
    JSONValue,
)
from ai_poc_planner.domain.tools import (
    AssessBusinessValueRoiAndKpisInput,
    AssessDataReadinessInput,
    AssessTechnicalFitAndArchitectureInput,
    EstimatePocScopeInput,
    EvaluateRiskAndHardGatesInput,
    RetrieveSimilarCasesInput,
)


class ProviderError(RuntimeError):
    """Normalized failure raised by any model-provider adapter."""


class PreparationStatus(StrEnum):
    READY = "ready"
    CLARIFICATION_REQUIRED = "clarification_required"


class ProviderConnectionState(StrEnum):
    UNTESTED = "untested"
    TESTING = "testing"
    CONNECTED = "connected"
    FAILED = "failed"
    DISABLED = "disabled"


class ProviderConnectionMessage(StrEnum):
    UNTESTED = "Connection has not been tested."
    TESTING = "Connection test is in progress."
    CONNECTED = "Connection succeeded."
    FAILED = "Connection test failed. Check the profile settings and try again."
    DISABLED = "This model profile is disabled."


class ProviderCapabilities(ContractModel):
    structured_output: bool
    tool_calling: bool
    streaming: bool
    model_identifier: str = Field(min_length=1)


class ProviderRequest(ContractModel):
    """Validated interview context accepted by a model provider."""

    project: AnalysisProject
    session_id: UUID
    interview_answers: dict[str, JSONValue] = Field(default_factory=dict)
    evidence: list[EvidenceReference] = Field(default_factory=list)


class AssessmentToolInputs(ContractModel):
    retrieve_similar_cases: RetrieveSimilarCasesInput
    assess_data_readiness: AssessDataReadinessInput
    assess_technical_fit_and_architecture: AssessTechnicalFitAndArchitectureInput
    evaluate_risk_and_hard_gates: EvaluateRiskAndHardGatesInput
    assess_business_value_roi_and_kpis: AssessBusinessValueRoiAndKpisInput
    estimate_poc_scope: EstimatePocScopeInput


class ProviderPreparation(ContractModel):
    """Exclusive ready-or-clarification structured provider response."""

    schema_version: str = "1.0"
    status: PreparationStatus
    facts: AssessmentFacts | None = None
    tool_inputs: AssessmentToolInputs | None = None
    clarifying_questions: list[ClarifyingQuestion] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_status_payload(self) -> ProviderPreparation:
        if self.status is PreparationStatus.READY:
            if self.facts is None or self.tool_inputs is None:
                raise ValueError("ready preparation requires facts and tool_inputs")
            if self.clarifying_questions:
                raise ValueError(
                    "ready preparation cannot include clarifying questions"
                )
            return self
        if self.facts is not None or self.tool_inputs is not None:
            raise ValueError("clarification preparation cannot include assessment data")
        if not 1 <= len(self.clarifying_questions) <= 5:
            raise ValueError("clarification preparation requires one to five questions")
        return self


class ModelProvider(Protocol):
    """Extension seam for future structured-output model adapters."""

    @property
    def capabilities(self) -> ProviderCapabilities:
        """Describe only capabilities required by orchestration."""
        ...

    def prepare_assessment(self, request: ProviderRequest) -> ProviderPreparation:
        """Extract facts and typed tool inputs, or request clarification."""
        ...


class EmbeddingProvider(Protocol):
    @property
    def dimensions(self) -> int:
        """Return the stable vector width."""
        ...

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one typed vector per input string."""
        ...
