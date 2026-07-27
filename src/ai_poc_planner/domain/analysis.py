"""Phase 4 evidence-backed analysis contracts, separate from legacy Assessment."""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, StringConstraints, model_validator

from ai_poc_planner.domain.case_centered import CaseCenteredAssessment
from ai_poc_planner.domain.catalog import NonAiAlternativeDirection, OpportunityType
from ai_poc_planner.domain.enums import (
    AnalysisConclusion,
    AnalysisOptionKind,
    DecisionAuthority,
    GateDisposition,
    ProcessingBoundary,
    ScoreDimension,
)
from ai_poc_planner.domain.models import (
    ContractModel,
    JSONValue,
    NonEmptyStr,
    UtcDateTime,
)

FactToken = Annotated[str, StringConstraints(pattern=r"^F[0-9]{3}$")]
OptionKey = Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9_-]{0,39}$")]

GateSignalName = Literal[
    "authorization",
    "lawful_basis",
    "accountable_owner",
    "prohibited_use",
    "high_impact_domain",
    "personal_or_sensitive_data",
    "minimization",
    "retention",
    "access_control",
    "security_controls",
    "governance_controls",
    "audit_controls",
    "data_availability",
    "digitization",
    "validation_sample",
    "data_boundary",
]


class CatalogOpportunity(ContractModel):
    kind: Literal["catalog"]
    opportunity_type: OpportunityType
    display_rationale: NonEmptyStr
    fact_refs: list[FactToken] = Field(min_length=1)


class UnstandardizedCandidate(ContractModel):
    kind: Literal["unstandardized_candidate"]
    candidate_name: NonEmptyStr
    candidate_definition: NonEmptyStr
    why_existing_catalog_is_insufficient: NonEmptyStr
    fact_refs: list[FactToken] = Field(min_length=1)


OpportunityReference = CatalogOpportunity | UnstandardizedCandidate


class AnalysisOptionDraft(ContractModel):
    option_key: OptionKey
    title: NonEmptyStr
    option_kind: AnalysisOptionKind
    summary: NonEmptyStr
    expected_benefits: list[NonEmptyStr] = Field(min_length=1)
    limitations: list[NonEmptyStr] = Field(min_length=1)
    prerequisites: list[NonEmptyStr] = Field(min_length=1)
    risks: list[NonEmptyStr] = Field(min_length=1)
    fact_refs: list[FactToken] = Field(min_length=1)
    decision_authority: DecisionAuthority
    processing_boundary: ProcessingBoundary
    human_review_points: list[NonEmptyStr] = Field(default_factory=list)
    ai_opportunity: OpportunityReference | None = None
    non_ai_directions: list[NonAiAlternativeDirection] = Field(default_factory=list)

    @model_validator(mode="after")
    def kind_has_required_direction(self) -> AnalysisOptionDraft:
        if self.option_kind is AnalysisOptionKind.AI and self.ai_opportunity is None:
            raise ValueError("AI options require an AI opportunity reference")
        if self.option_kind is AnalysisOptionKind.NON_AI and not self.non_ai_directions:
            raise ValueError("non-AI options require a non-AI direction")
        if self.option_kind is AnalysisOptionKind.HYBRID and (
            self.ai_opportunity is None or not self.non_ai_directions
        ):
            raise ValueError("hybrid options require AI and non-AI directions")
        if self.option_kind is AnalysisOptionKind.FOUNDATIONS_FIRST and (
            not self.non_ai_directions
        ):
            raise ValueError("foundations-first options require non-AI directions")
        return self


class RubricRatingDraft(ContractModel):
    dimension: ScoreDimension
    rating: int = Field(ge=1, le=5)
    rationale: NonEmptyStr
    evidence_fact_refs: list[FactToken] = Field(min_length=1)
    gap_fact_refs: list[FactToken] = Field(default_factory=list)
    data_gaps: list[NonEmptyStr] = Field(default_factory=list)
    risks: list[NonEmptyStr] = Field(default_factory=list)
    improvement_conditions: list[NonEmptyStr] = Field(default_factory=list)

    @model_validator(mode="after")
    def lower_ratings_require_improvement(self) -> RubricRatingDraft:
        if self.rating < 5 and not self.improvement_conditions:
            raise ValueError("ratings below five require improvement_conditions")
        return self


class GateSignalDraft(ContractModel):
    """Evidence-backed input to the program-owned gate evaluator."""

    signal_name: GateSignalName
    value: JSONValue
    fact_refs: list[FactToken] = Field(min_length=1)
    rationale: NonEmptyStr


class AIAnalysisDraft(ContractModel):
    """Only provider-owned proposals; scores and gates stay program-owned."""

    schema_version: Literal["1.0"]
    requirement_summary: NonEmptyStr
    options: list[AnalysisOptionDraft] = Field(min_length=2, max_length=4)
    recommended_option_key: OptionKey
    conclusion: AnalysisConclusion
    conclusion_rationale: NonEmptyStr
    conclusion_fact_refs: list[FactToken] = Field(min_length=1)
    rubric_ratings: list[RubricRatingDraft] = Field(min_length=6, max_length=6)
    gate_signals: list[GateSignalDraft] = Field(default_factory=list)
    overall_risks: list[NonEmptyStr] = Field(default_factory=list)
    unresolved_gaps: list[NonEmptyStr] = Field(default_factory=list)

    @model_validator(mode="after")
    def options_and_ratings_are_complete(self) -> AIAnalysisDraft:
        keys = [option.option_key for option in self.options]
        if len(keys) != len(set(keys)) or self.recommended_option_key not in keys:
            raise ValueError("recommended option must be a unique listed option")
        recommended = next(
            option
            for option in self.options
            if option.option_key == self.recommended_option_key
        )
        expected = {
            AnalysisConclusion.SUITABLE_FOR_AI: AnalysisOptionKind.AI,
            AnalysisConclusion.BETTER_SUITED_TO_NON_AI: AnalysisOptionKind.NON_AI,
            AnalysisConclusion.ESTABLISH_NON_AI_FOUNDATIONS_BEFORE_AI: (
                AnalysisOptionKind.FOUNDATIONS_FIRST
            ),
            AnalysisConclusion.HYBRID_AI_AND_NON_AI: AnalysisOptionKind.HYBRID,
        }
        if recommended.option_kind is not expected[self.conclusion]:
            raise ValueError("recommended option kind conflicts with conclusion")
        dimensions = [rating.dimension for rating in self.rubric_ratings]
        if len(set(dimensions)) != len(ScoreDimension) or set(dimensions) != set(
            ScoreDimension
        ):
            raise ValueError("rubric_ratings must contain each dimension exactly once")
        return self


class ProgramScore(ContractModel):
    dimension: ScoreDimension
    rating: int = Field(ge=1, le=5)
    weight: int = Field(ge=0, le=100)
    weighted_points: int = Field(ge=0, le=100)
    rationale: NonEmptyStr
    evidence_fact_refs: list[FactToken] = Field(min_length=1)
    gap_fact_refs: list[FactToken] = Field(default_factory=list)
    data_gaps: list[NonEmptyStr] = Field(default_factory=list)
    risks: list[NonEmptyStr] = Field(default_factory=list)
    improvement_conditions: list[NonEmptyStr] = Field(default_factory=list)
    evaluation_subject: NonEmptyStr = "目前專案在現階段採用實施路徑的可行性與準備程度"
    unknown_fact_refs: list[FactToken] = Field(default_factory=list)
    unknown_impact: NonEmptyStr = "未知資料不視為通過；需在後續階段確認。"


class ProgramGateResult(ContractModel):
    rule_id: NonEmptyStr
    disposition: GateDisposition
    reason: NonEmptyStr
    required_controls: list[NonEmptyStr] = Field(default_factory=list)
    human_review_required: bool
    affected_stage: NonEmptyStr = "目前 PoC 階段"
    does_not_limit: list[NonEmptyStr] = Field(
        default_factory=lambda: ["流程整理、規則檢查與人工輔助仍可進行。"]
    )
    release_conditions: list[NonEmptyStr] = Field(default_factory=list)


class ValidatedAnalysisResult(ContractModel):
    id: UUID
    version_id: UUID
    rubric_version: Literal["1.0"]
    hard_gate_version: Literal["legacy-1", "case-centered-1"]
    requirement_summary: NonEmptyStr
    options: list[AnalysisOptionDraft] = Field(min_length=2, max_length=4)
    recommended_option_key: OptionKey
    conclusion: AnalysisConclusion
    conclusion_rationale: NonEmptyStr
    conclusion_fact_refs: list[FactToken] = Field(min_length=1)
    scores: list[ProgramScore] = Field(min_length=6, max_length=6)
    weighted_total: int = Field(ge=0, le=100)
    gate_results: list[ProgramGateResult]
    gate_disposition: GateDisposition
    overall_risks: list[NonEmptyStr] = Field(default_factory=list)
    unresolved_gaps: list[NonEmptyStr] = Field(default_factory=list)
    created_at: UtcDateTime
    case_centered: CaseCenteredAssessment | None = None
