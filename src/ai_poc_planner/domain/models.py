"""Pydantic contracts shared by future API, tools and provider adapters."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from ai_poc_planner.domain.enums import (
    GateDisposition,
    InterviewRole,
    ProjectStatus,
    Recommendation,
    ScoreDimension,
)

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
JSONScalar = str | int | float | bool | None
JSONValue = JSONScalar | list[str]

SCORE_WEIGHTS: dict[ScoreDimension, int] = {
    ScoreDimension.BUSINESS_VALUE: 25,
    ScoreDimension.DATA_READINESS: 20,
    ScoreDimension.TECHNICAL_FIT: 15,
    ScoreDimension.ARCHITECTURE_CONTROLLABILITY: 15,
    ScoreDimension.GOVERNANCE_READINESS: 15,
    ScoreDimension.USER_ADOPTION: 10,
}


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=False)


class AnalysisProject(ContractModel):
    id: UUID = Field(description="Stable project identifier.")
    title: NonEmptyStr = Field(description="Human-readable analysis title.")
    problem_statement: NonEmptyStr = Field(
        description="Business problem to investigate, without a preselected solution."
    )
    status: ProjectStatus = Field(description="Current project lifecycle state.")
    created_at: datetime = Field(description="Timezone-aware UTC creation time.")
    updated_at: datetime = Field(description="Timezone-aware UTC update time.")

    @field_validator("created_at", "updated_at")
    @classmethod
    def normalize_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def updated_at_is_not_earlier(self) -> AnalysisProject:
        if self.updated_at < self.created_at:
            raise ValueError("updated_at must not be earlier than created_at")
        return self


class InterviewTurn(ContractModel):
    id: UUID = Field(description="Stable interview turn identifier.")
    session_id: UUID = Field(description="Owning interview session identifier.")
    sequence: int = Field(ge=1, description="One-based order within the session.")
    role: InterviewRole = Field(description="Author of this interview turn.")
    content: NonEmptyStr = Field(description="Raw local interview content.")
    normalized_answers: dict[str, JSONValue] = Field(
        default_factory=dict,
        description="Accepted structured answers extracted from this turn.",
    )
    created_at: datetime = Field(description="Timezone-aware UTC creation time.")

    @field_validator("created_at")
    @classmethod
    def normalize_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        return value.astimezone(UTC)


class ClarifyingQuestion(ContractModel):
    field: NonEmptyStr = Field(description="Missing or contradictory field to resolve.")
    question: NonEmptyStr = Field(description="Question shown to the user.")
    reason: NonEmptyStr = Field(description="Why this answer is needed.")
    priority: int = Field(ge=1, le=5, description="Priority from 1 to 5.")


class ScoreDimensionResult(ContractModel):
    dimension: ScoreDimension = Field(description="Normative scoring dimension.")
    rating: int = Field(ge=1, le=5, description="Rubric rating from 1 to 5.")
    weight: int = Field(ge=1, le=100, description="Normative percentage weight.")
    weighted_points: float = Field(
        ge=0, le=100, description="rating / 5 multiplied by weight."
    )
    rationale: NonEmptyStr = Field(description="Reason for this rating.")
    evidence_refs: list[str] = Field(
        default_factory=list, description="Local evidence identifiers."
    )

    @model_validator(mode="after")
    def values_match_normative_weight(self) -> ScoreDimensionResult:
        expected_weight = SCORE_WEIGHTS[self.dimension]
        if self.weight != expected_weight:
            raise ValueError(
                f"weight for {self.dimension.value} must be {expected_weight}"
            )
        expected_points = self.rating / 5 * self.weight
        if abs(self.weighted_points - expected_points) > 1e-9:
            raise ValueError("weighted_points must equal rating / 5 * weight")
        return self


class HardGateResult(ContractModel):
    rule_id: NonEmptyStr = Field(description="Versioned hard-gate rule identifier.")
    disposition: GateDisposition = Field(description="Rule outcome before scoring.")
    reason: NonEmptyStr = Field(description="Evidence-based gate rationale.")
    required_controls: list[str] = Field(
        default_factory=list, description="Controls required before proceeding."
    )
    human_review_required: bool = Field(
        description="Whether a qualified human must review this outcome."
    )


class SimilarCase(ContractModel):
    case_id: NonEmptyStr
    title: NonEmptyStr
    similarity: float = Field(ge=0, le=1)
    fit_summary: NonEmptyStr
    source_ref: NonEmptyStr


class ArchitectureOption(ContractModel):
    name: NonEmptyStr
    summary: NonEmptyStr
    deployment: Literal["local", "private-cloud", "on-prem"]
    components: list[NonEmptyStr] = Field(min_length=1)
    assumptions: list[NonEmptyStr] = Field(default_factory=list)


_GATE_PRIORITY = {
    GateDisposition.PASS: 0,
    GateDisposition.REQUIRES_CONTROLS: 1,
    GateDisposition.ASSISTIVE_ONLY: 2,
    GateDisposition.BLOCKED: 3,
}


class PocProposal(ContractModel):
    schema_version: Literal["1.0"]
    recommendation: Recommendation
    gate_disposition: GateDisposition
    problem_statement: NonEmptyStr
    target_users: list[NonEmptyStr] = Field(min_length=1)
    current_workflow_summary: NonEmptyStr
    known_information: dict[str, JSONValue]
    missing_information: list[str]
    clarifying_questions: list[ClarifyingQuestion]
    similar_cases: list[SimilarCase]
    scores: list[ScoreDimensionResult]
    weighted_score: int = Field(ge=0, le=100)
    hard_gates: list[HardGateResult]
    architecture_options: list[ArchitectureOption]
    required_data: list[str]
    integrations: list[str]
    risks: list[str]
    human_review_points: list[str]
    roi_assumptions: list[str]
    success_metrics: list[str]
    estimated_weeks: int = Field(ge=1)
    estimated_team: list[NonEmptyStr] = Field(min_length=1)
    next_actions: list[NonEmptyStr] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_contract_invariants(self) -> PocProposal:
        dimensions = [score.dimension for score in self.scores]
        if len(dimensions) != len(SCORE_WEIGHTS) or set(dimensions) != set(
            SCORE_WEIGHTS
        ):
            raise ValueError("scores must contain each dimension exactly once")
        if sum(score.weight for score in self.scores) != 100:
            raise ValueError("score weights must total 100")
        if self.weighted_score != round(
            sum(score.weighted_points for score in self.scores)
        ):
            raise ValueError("weighted_score does not match score dimensions")

        strongest_gate = max(
            (gate.disposition for gate in self.hard_gates),
            key=lambda disposition: _GATE_PRIORITY[disposition],
            default=GateDisposition.PASS,
        )
        if self.gate_disposition is not strongest_gate:
            raise ValueError("gate_disposition must equal the strongest hard gate")
        if (
            strongest_gate is GateDisposition.BLOCKED
            and self.recommendation is not Recommendation.NOT_RECOMMENDED
        ):
            raise ValueError("blocked proposals must be 暫不建議")
        if strongest_gate in {
            GateDisposition.ASSISTIVE_ONLY,
            GateDisposition.REQUIRES_CONTROLS,
        } and self.recommendation is Recommendation.RECOMMENDED:
            raise ValueError("unresolved gates cap recommendation at 條件式建議")
        if (
            strongest_gate is GateDisposition.ASSISTIVE_ONLY
            and not self.human_review_points
        ):
            raise ValueError(
                "assistive_only proposals require at least one human review point"
            )
        return self
