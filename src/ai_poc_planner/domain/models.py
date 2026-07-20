"""Pydantic contracts shared by future API, tools and provider adapters."""

from __future__ import annotations

from datetime import UTC, datetime
from math import isfinite
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from ai_poc_planner.domain.enums import (
    EvidenceSourceType,
    GateDisposition,
    InterviewRole,
    ProjectStatus,
    Recommendation,
    ScoreDimension,
)

NonEmptyStr = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1)
]
SchemaVersion = Annotated[
    str,
    StringConstraints(
        strict=True,
        strip_whitespace=True,
        pattern=r"^[0-9]+\.[0-9]+$",
    ),
]

type RawJSONValue = (
    None | bool | int | float | str | list[RawJSONValue] | dict[str, RawJSONValue]
)


def _validate_json_value(value: object) -> object:
    if value is None or type(value) in {bool, int, str}:
        return value
    if type(value) is float:
        if not isfinite(value):
            raise ValueError("JSON float must be finite")
        return value
    if type(value) is list:
        return [_validate_json_value(item) for item in value]
    if type(value) is dict:
        if not all(type(key) is str for key in value):
            raise ValueError("JSON object keys must be strings")
        return {key: _validate_json_value(item) for key, item in value.items()}
    raise ValueError("value must contain only JSON-compatible types")


JSONValue = Annotated[RawJSONValue, BeforeValidator(_validate_json_value)]


def _normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(UTC)


UtcDateTime = Annotated[datetime, AfterValidator(_normalize_utc)]

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


class EvidenceReference(ContractModel):
    id: UUID = Field(description="Stable evidence identifier.")
    project_id: UUID | None = Field(
        default=None,
        description=(
            "Explicit owner when evidence is used outside an enclosing project."
        ),
    )
    session_id: UUID | None = Field(
        default=None,
        description=(
            "Explicit owner when evidence is used outside an enclosing session."
        ),
    )
    source_type: EvidenceSourceType
    source_ref: NonEmptyStr = Field(description="Inspectable local source reference.")
    label: NonEmptyStr
    metadata: dict[str, JSONValue] = Field(default_factory=dict)


def _require_unique(values: list[object], field_name: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{field_name} must not contain duplicates")


class AnalysisProject(ContractModel):
    id: UUID = Field(description="Stable project identifier.")
    title: NonEmptyStr = Field(description="Human-readable analysis title.")
    problem_statement: NonEmptyStr = Field(
        description="Business problem to investigate, without a preselected solution."
    )
    status: ProjectStatus = Field(description="Current project lifecycle state.")
    created_at: UtcDateTime = Field(description="Timezone-aware UTC creation time.")
    updated_at: UtcDateTime = Field(description="Timezone-aware UTC update time.")

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
    created_at: UtcDateTime = Field(description="Timezone-aware UTC creation time.")


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
    evidence_refs: list[NonEmptyStr] = Field(
        default_factory=list, description="Local evidence identifiers."
    )

    @model_validator(mode="after")
    def weight_matches_normative_dimension(self) -> ScoreDimensionResult:
        expected_weight = SCORE_WEIGHTS[self.dimension]
        if self.weight != expected_weight:
            raise ValueError(
                f"weight for {self.dimension.value} must be {expected_weight}"
            )
        _require_unique(self.evidence_refs, "evidence_refs")
        return self


class HardGateResult(ContractModel):
    rule_id: NonEmptyStr = Field(description="Versioned hard-gate rule identifier.")
    disposition: GateDisposition = Field(description="Rule outcome before scoring.")
    reason: NonEmptyStr = Field(description="Evidence-based gate rationale.")
    required_controls: list[NonEmptyStr] = Field(
        default_factory=list, description="Controls required before proceeding."
    )
    human_review_required: bool = Field(
        description="Whether a qualified human must review this outcome."
    )
    evidence_refs: list[NonEmptyStr] = Field(
        default_factory=list, description="Evidence identifiers supporting the trigger."
    )

    @model_validator(mode="after")
    def controls_are_unique(self) -> HardGateResult:
        _require_unique(self.required_controls, "required_controls")
        _require_unique(self.evidence_refs, "evidence_refs")
        return self


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

    @model_validator(mode="after")
    def architecture_lists_are_unique(self) -> ArchitectureOption:
        _require_unique(self.components, "components")
        _require_unique(self.assumptions, "assumptions")
        return self


class PocProposal(ContractModel):
    schema_version: Literal["1.0"]
    executive_summary: NonEmptyStr | None = None
    recommendation: Recommendation
    gate_disposition: GateDisposition
    problem_statement: NonEmptyStr
    suggested_use_case_boundary: NonEmptyStr | None = None
    target_users: list[NonEmptyStr] = Field(min_length=1)
    current_workflow_summary: NonEmptyStr
    known_information: dict[str, JSONValue]
    missing_information: list[NonEmptyStr]
    clarifying_questions: list[ClarifyingQuestion]
    similar_cases: list[SimilarCase]
    scores: list[ScoreDimensionResult]
    weighted_score: int = Field(ge=0, le=100)
    hard_gates: list[HardGateResult]
    architecture_options: list[ArchitectureOption]
    required_data: list[NonEmptyStr]
    integrations: list[NonEmptyStr]
    risks: list[NonEmptyStr]
    human_review_points: list[NonEmptyStr]
    roi_assumptions: list[NonEmptyStr]
    success_metrics: list[NonEmptyStr]
    estimated_weeks: int = Field(ge=1)
    estimated_team: list[NonEmptyStr] = Field(min_length=1)
    in_scope: list[NonEmptyStr] = Field(default_factory=list)
    out_of_scope: list[NonEmptyStr] = Field(default_factory=list)
    poc_milestones: list[NonEmptyStr] = Field(default_factory=list)
    scope_assumptions: list[NonEmptyStr] = Field(default_factory=list)
    evidence_refs: list[NonEmptyStr] = Field(default_factory=list)
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
        if (
            self.gate_disposition is GateDisposition.ASSISTIVE_ONLY
            and not self.human_review_points
        ):
            raise ValueError(
                "assistive_only proposals require at least one human review point"
            )
        for field_name in (
            "target_users",
            "missing_information",
            "required_data",
            "integrations",
            "risks",
            "human_review_points",
            "roi_assumptions",
            "success_metrics",
            "estimated_team",
            "in_scope",
            "out_of_scope",
            "poc_milestones",
            "scope_assumptions",
            "evidence_refs",
            "next_actions",
        ):
            _require_unique(getattr(self, field_name), field_name)
        _require_unique(
            [question.field for question in self.clarifying_questions],
            "clarifying question fields",
        )
        _require_unique(
            [case.case_id for case in self.similar_cases], "similar case IDs"
        )
        _require_unique([gate.rule_id for gate in self.hard_gates], "hard gate IDs")
        _require_unique(
            [option.name for option in self.architecture_options],
            "architecture option names",
        )
        return self
