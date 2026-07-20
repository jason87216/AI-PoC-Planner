"""Pydantic input/output contracts for the six bounded assessment tools."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from ai_poc_planner.domain.enums import (
    DataBoundary,
    DecisionImpact,
    DigitizationLevel,
    GateDisposition,
    ScoreDimension,
)
from ai_poc_planner.domain.models import (
    ArchitectureOption,
    ContractModel,
    EvidenceReference,
    HardGateResult,
    JSONValue,
    NonEmptyStr,
    SchemaVersion,
    ScoreDimensionResult,
    SimilarCase,
)


def _ensure_unique(values: list[object], field_name: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{field_name} must not contain duplicates")


def _validate_output_envelope(
    error: ToolError | None,
    success_payload: dict[str, object | None],
) -> bool:
    """Require exactly one of a complete success payload or a tool error."""
    populated = [name for name, value in success_payload.items() if value is not None]
    missing = [name for name, value in success_payload.items() if value is None]
    if error is not None:
        if populated:
            raise ValueError("error output must not include success payload")
        return False
    if missing:
        raise ValueError(
            "successful output requires fields: " + ", ".join(sorted(missing))
        )
    return True


class ToolContract(ContractModel):
    schema_version: SchemaVersion
    correlation_id: UUID
    project_id: UUID
    session_id: UUID


class ToolError(ContractModel):
    code: NonEmptyStr
    message: NonEmptyStr
    retryable: bool
    details: dict[str, JSONValue] = Field(default_factory=dict)


class ToolOutputContract(ToolContract):
    error: ToolError | None = None


class RetrieveSimilarCasesInput(ToolContract):
    normalized_problem: NonEmptyStr
    industries: list[NonEmptyStr] = Field(default_factory=list)
    data_filters: dict[str, JSONValue] = Field(default_factory=dict)
    risk_filters: dict[str, JSONValue] = Field(default_factory=dict)
    top_k: int = Field(ge=1, le=20)

    @model_validator(mode="after")
    def filters_are_unique(self) -> RetrieveSimilarCasesInput:
        _ensure_unique(self.industries, "industries")
        return self


class RetrieveSimilarCasesOutput(ToolOutputContract):
    cases: list[SimilarCase] | None = None
    evidence: list[EvidenceReference] | None = None

    @model_validator(mode="after")
    def references_are_unique(self) -> RetrieveSimilarCasesOutput:
        if not _validate_output_envelope(
            self.error, {"cases": self.cases, "evidence": self.evidence}
        ):
            return self
        assert self.cases is not None
        assert self.evidence is not None
        _ensure_unique([case.case_id for case in self.cases], "case IDs")
        _ensure_unique([item.id for item in self.evidence], "evidence IDs")
        return self


class AssessDataReadinessInput(ToolContract):
    data_sources: list[NonEmptyStr] = Field(min_length=1)
    access_confirmed: bool
    digitization: DigitizationLevel
    quality_notes: list[NonEmptyStr] = Field(default_factory=list)
    labels_available: bool | None
    validation_sample_available: bool

    @model_validator(mode="after")
    def data_descriptors_are_unique(self) -> AssessDataReadinessInput:
        _ensure_unique(self.data_sources, "data_sources")
        _ensure_unique(self.quality_notes, "quality_notes")
        return self


class AssessDataReadinessOutput(ToolOutputContract):
    score: ScoreDimensionResult | None = None
    gaps: list[NonEmptyStr] | None = None
    prerequisites: list[NonEmptyStr] | None = None
    rationale: NonEmptyStr | None = None

    @model_validator(mode="after")
    def score_uses_data_dimension(self) -> AssessDataReadinessOutput:
        if not _validate_output_envelope(
            self.error,
            {
                "score": self.score,
                "gaps": self.gaps,
                "prerequisites": self.prerequisites,
                "rationale": self.rationale,
            },
        ):
            return self
        assert self.score is not None
        assert self.gaps is not None
        assert self.prerequisites is not None
        if self.score.dimension is not ScoreDimension.DATA_READINESS:
            raise ValueError("data readiness output requires data_readiness score")
        _ensure_unique(self.gaps, "gaps")
        _ensure_unique(self.prerequisites, "prerequisites")
        return self


class AssessTechnicalFitAndArchitectureInput(ToolContract):
    task_pattern: NonEmptyStr
    required_reasoning: list[NonEmptyStr]
    required_tools: list[NonEmptyStr]
    integrations: list[NonEmptyStr]
    deployment_constraints: list[NonEmptyStr]

    @model_validator(mode="after")
    def technical_inputs_are_unique(
        self,
    ) -> AssessTechnicalFitAndArchitectureInput:
        for field_name in (
            "required_reasoning",
            "required_tools",
            "integrations",
            "deployment_constraints",
        ):
            _ensure_unique(getattr(self, field_name), field_name)
        return self


class AssessTechnicalFitAndArchitectureOutput(ToolOutputContract):
    technical_fit: ScoreDimensionResult | None = None
    architecture_controllability: ScoreDimensionResult | None = None
    architecture_options: list[ArchitectureOption] | None = Field(
        default=None, min_length=1
    )
    rationale: NonEmptyStr | None = None

    @model_validator(mode="after")
    def scores_use_technical_dimensions(
        self,
    ) -> AssessTechnicalFitAndArchitectureOutput:
        if not _validate_output_envelope(
            self.error,
            {
                "technical_fit": self.technical_fit,
                "architecture_controllability": self.architecture_controllability,
                "architecture_options": self.architecture_options,
                "rationale": self.rationale,
            },
        ):
            return self
        assert self.technical_fit is not None
        assert self.architecture_controllability is not None
        assert self.architecture_options is not None
        if self.technical_fit.dimension is not ScoreDimension.TECHNICAL_FIT:
            raise ValueError("technical_fit must use technical_fit dimension")
        if (
            self.architecture_controllability.dimension
            is not ScoreDimension.ARCHITECTURE_CONTROLLABILITY
        ):
            raise ValueError(
                "architecture_controllability must use its normative dimension"
            )
        _ensure_unique(
            [option.name for option in self.architecture_options],
            "architecture option names",
        )
        return self


class EvaluateRiskAndHardGatesInput(ToolContract):
    domain: NonEmptyStr
    decision_impact: DecisionImpact
    personal_data: bool
    sensitive_data: bool
    data_boundary: DataBoundary
    human_review_available: bool
    authorization_confirmed: bool


class EvaluateRiskAndHardGatesOutput(ToolOutputContract):
    rule_version: SchemaVersion | None = None
    hard_gates: list[HardGateResult] | None = None
    gate_disposition: GateDisposition | None = None
    governance_readiness: ScoreDimensionResult | None = None

    @model_validator(mode="after")
    def gate_ids_are_unique(self) -> EvaluateRiskAndHardGatesOutput:
        if not _validate_output_envelope(
            self.error,
            {
                "rule_version": self.rule_version,
                "hard_gates": self.hard_gates,
                "gate_disposition": self.gate_disposition,
                "governance_readiness": self.governance_readiness,
            },
        ):
            return self
        assert self.hard_gates is not None
        assert self.governance_readiness is not None
        _ensure_unique([gate.rule_id for gate in self.hard_gates], "hard gate IDs")
        if (
            self.governance_readiness.dimension
            is not ScoreDimension.GOVERNANCE_READINESS
        ):
            raise ValueError(
                "governance_readiness must use governance_readiness dimension"
            )
        return self


class AssessBusinessValueRoiAndKpisInput(ToolContract):
    owner: NonEmptyStr
    baseline_description: NonEmptyStr
    monthly_volume: int | None = Field(default=None, ge=0)
    current_cost: float | None = Field(default=None, ge=0)
    current_time_minutes: float | None = Field(default=None, ge=0)
    expected_change: NonEmptyStr
    adoption_evidence: list[NonEmptyStr]

    @model_validator(mode="after")
    def adoption_evidence_is_unique(self) -> AssessBusinessValueRoiAndKpisInput:
        _ensure_unique(self.adoption_evidence, "adoption_evidence")
        return self


class KpiProposal(ContractModel):
    name: NonEmptyStr
    unit: NonEmptyStr
    baseline: float | None = None
    target: float | None = None
    direction: Literal["increase", "decrease", "maintain"]


class AssessBusinessValueRoiAndKpisOutput(ToolOutputContract):
    business_value: ScoreDimensionResult | None = None
    user_adoption: ScoreDimensionResult | None = None
    roi_assumptions: list[NonEmptyStr] | None = None
    kpi_proposals: list[KpiProposal] | None = None
    rationale: NonEmptyStr | None = None

    @model_validator(mode="after")
    def scores_use_business_dimensions(
        self,
    ) -> AssessBusinessValueRoiAndKpisOutput:
        if not _validate_output_envelope(
            self.error,
            {
                "business_value": self.business_value,
                "user_adoption": self.user_adoption,
                "roi_assumptions": self.roi_assumptions,
                "kpi_proposals": self.kpi_proposals,
                "rationale": self.rationale,
            },
        ):
            return self
        assert self.business_value is not None
        assert self.user_adoption is not None
        assert self.roi_assumptions is not None
        assert self.kpi_proposals is not None
        if self.business_value.dimension is not ScoreDimension.BUSINESS_VALUE:
            raise ValueError("business_value must use business_value dimension")
        if self.user_adoption.dimension is not ScoreDimension.USER_ADOPTION:
            raise ValueError("user_adoption must use user_adoption dimension")
        _ensure_unique(self.roi_assumptions, "roi_assumptions")
        _ensure_unique(
            [proposal.name for proposal in self.kpi_proposals],
            "KPI proposal names",
        )
        return self


class EstimatePocScopeInput(ToolContract):
    requires_ocr: bool
    integration_count: int = Field(ge=0)
    requires_review_ui: bool
    evaluation_data_available: bool
    handles_sensitive_data: bool
    department_count: int = Field(ge=1)


class EstimatePocScopeOutput(ToolOutputContract):
    estimated_weeks: int | None = Field(default=None, ge=1)
    roles: list[NonEmptyStr] | None = Field(default=None, min_length=1)
    complexity_points: int | None = Field(default=None, ge=0)
    assumptions: list[NonEmptyStr] | None = None

    @model_validator(mode="after")
    def scope_lists_are_unique(self) -> EstimatePocScopeOutput:
        if not _validate_output_envelope(
            self.error,
            {
                "estimated_weeks": self.estimated_weeks,
                "roles": self.roles,
                "complexity_points": self.complexity_points,
                "assumptions": self.assumptions,
            },
        ):
            return self
        assert self.roles is not None
        assert self.assumptions is not None
        _ensure_unique(self.roles, "roles")
        _ensure_unique(self.assumptions, "assumptions")
        return self


class AssessmentToolOutputs(ContractModel):
    """Typed output bundle; optional fields support pre-assessment workflow state."""

    retrieve_similar_cases: RetrieveSimilarCasesOutput | None = None
    assess_data_readiness: AssessDataReadinessOutput | None = None
    assess_technical_fit_and_architecture: (
        AssessTechnicalFitAndArchitectureOutput | None
    ) = None
    evaluate_risk_and_hard_gates: EvaluateRiskAndHardGatesOutput | None = None
    assess_business_value_roi_and_kpis: AssessBusinessValueRoiAndKpisOutput | None = (
        None
    )
    estimate_poc_scope: EstimatePocScopeOutput | None = None
