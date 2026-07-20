"""Framework-neutral workflow and persistence-ready contracts."""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, StringConstraints, model_validator

from ai_poc_planner.domain.enums import (
    GateDisposition,
    HumanReviewRequirement,
    InterviewSessionStatus,
    InterviewStage,
    PlanningRunStatus,
    ProjectStatus,
    Recommendation,
    ReportFormat,
)
from ai_poc_planner.domain.facts import AssessmentFacts
from ai_poc_planner.domain.models import (
    SCORE_WEIGHTS,
    ClarifyingQuestion,
    ContractModel,
    EvidenceReference,
    HardGateResult,
    InterviewTurn,
    JSONValue,
    NonEmptyStr,
    PocProposal,
    SchemaVersion,
    ScoreDimensionResult,
    UtcDateTime,
)
from ai_poc_planner.domain.tools import AssessmentToolOutputs

ContentHash = Annotated[
    str,
    StringConstraints(
        strict=True,
        strip_whitespace=True,
        pattern=r"^[0-9a-f]{64}$",
    ),
]


def _require_unique(values: list[object], field_name: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{field_name} must not contain duplicates")


class InterviewSession(ContractModel):
    id: UUID
    project_id: UUID
    status: InterviewSessionStatus
    current_stage: InterviewStage
    state_version: int = Field(ge=0)
    turns: list[InterviewTurn] = Field(default_factory=list)
    created_at: UtcDateTime
    updated_at: UtcDateTime

    @model_validator(mode="after")
    def validate_session_structure(self) -> InterviewSession:
        if self.updated_at < self.created_at:
            raise ValueError("updated_at must not be earlier than created_at")
        if any(turn.session_id != self.id for turn in self.turns):
            raise ValueError("turn session_id must match interview session id")
        sequences = [turn.sequence for turn in self.turns]
        if sequences != list(range(1, len(sequences) + 1)):
            raise ValueError("turn sequences must be contiguous and ordered from 1")
        if (
            self.status is InterviewSessionStatus.COMPLETED
            and self.current_stage is not InterviewStage.COMPLETE
        ):
            raise ValueError("completed session must use complete interview stage")
        if (
            self.current_stage is InterviewStage.COMPLETE
            and self.status is InterviewSessionStatus.ACTIVE
        ):
            raise ValueError("active session cannot use complete interview stage")
        return self


class ConversationStateSnapshot(ContractModel):
    schema_version: SchemaVersion
    session_id: UUID
    version: int = Field(ge=1)
    known_fields: dict[str, JSONValue] = Field(default_factory=dict)
    missing_fields: list[NonEmptyStr] = Field(default_factory=list)
    contradictions: list[NonEmptyStr] = Field(default_factory=list)
    created_at: UtcDateTime

    @model_validator(mode="after")
    def validate_unique_gaps(self) -> ConversationStateSnapshot:
        _require_unique(self.missing_fields, "missing_fields")
        _require_unique(self.contradictions, "contradictions")
        return self


class CaseMetadata(ContractModel):
    id: UUID
    title: NonEmptyStr
    industry: list[NonEmptyStr] = Field(min_length=1)
    problem: NonEmptyStr
    fit_conditions: list[NonEmptyStr]
    non_fit_conditions: list[NonEmptyStr]
    pattern: NonEmptyStr
    risk_flags: list[NonEmptyStr]
    kpis: list[NonEmptyStr]
    human_review: HumanReviewRequirement
    source_path: NonEmptyStr
    content_hash: ContentHash
    created_at: UtcDateTime
    updated_at: UtcDateTime

    @model_validator(mode="after")
    def validate_metadata(self) -> CaseMetadata:
        if self.updated_at < self.created_at:
            raise ValueError("updated_at must not be earlier than created_at")
        for field_name in (
            "industry",
            "fit_conditions",
            "non_fit_conditions",
            "risk_flags",
            "kpis",
        ):
            _require_unique(getattr(self, field_name), field_name)
        return self


class Assessment(ContractModel):
    schema_version: SchemaVersion
    id: UUID
    project_id: UUID
    session_id: UUID
    rule_version: SchemaVersion
    scores: list[ScoreDimensionResult]
    weighted_score: int = Field(ge=0, le=100)
    hard_gates: list[HardGateResult]
    gate_disposition: GateDisposition
    recommendation: Recommendation
    matched_case_ids: list[NonEmptyStr]
    evidence_refs: list[NonEmptyStr]
    rationale: NonEmptyStr
    created_at: UtcDateTime

    @model_validator(mode="after")
    def validate_result_structure(self) -> Assessment:
        dimensions = [score.dimension for score in self.scores]
        if len(dimensions) != len(SCORE_WEIGHTS) or set(dimensions) != set(
            SCORE_WEIGHTS
        ):
            raise ValueError("scores must contain each dimension exactly once")
        if sum(score.weight for score in self.scores) != 100:
            raise ValueError("score weights must total 100")
        _require_unique([gate.rule_id for gate in self.hard_gates], "hard gate IDs")
        _require_unique(self.matched_case_ids, "matched_case_ids")
        _require_unique(self.evidence_refs, "evidence_refs")
        return self


class PlanningRun(ContractModel):
    """One durable clarification-to-result lifecycle for the public demo."""

    id: UUID
    project_id: UUID
    status: PlanningRunStatus
    original_request: NonEmptyStr
    intent: dict[str, JSONValue]
    known_information: dict[str, JSONValue] = Field(default_factory=dict)
    missing_information: list[NonEmptyStr] = Field(default_factory=list)
    clarifying_questions: list[ClarifyingQuestion] = Field(
        default_factory=list,
        max_length=4,
    )
    clarification_answers: dict[str, JSONValue] = Field(default_factory=dict)
    assessment: Assessment | None = None
    proposal: PocProposal | None = None
    markdown_report: NonEmptyStr | None = None
    error_code: NonEmptyStr | None = None
    error_message: NonEmptyStr | None = None
    created_at: UtcDateTime
    updated_at: UtcDateTime
    completed_at: UtcDateTime | None = None

    @model_validator(mode="after")
    def validate_run_state(self) -> PlanningRun:
        if not self.intent:
            raise ValueError("intent must contain at least one structured field")
        if self.updated_at < self.created_at:
            raise ValueError("updated_at must not be earlier than created_at")
        if self.completed_at is not None and not (
            self.created_at <= self.completed_at <= self.updated_at
        ):
            raise ValueError("completed_at must fall within the run timestamps")
        _require_unique(self.missing_information, "missing_information")
        _require_unique(
            [question.field for question in self.clarifying_questions],
            "clarifying question fields",
        )
        _require_unique(
            [question.question for question in self.clarifying_questions],
            "clarifying question text",
        )

        final_values = (self.assessment, self.proposal, self.markdown_report)
        has_any_final = any(value is not None for value in final_values)
        has_all_final = all(value is not None for value in final_values)
        has_any_error = self.error_code is not None or self.error_message is not None

        if self.status is PlanningRunStatus.COMPLETED:
            if not has_all_final or self.completed_at is None:
                raise ValueError(
                    "completed run requires assessment, proposal, report "
                    "and completed_at"
                )
            if has_any_error or self.missing_information:
                raise ValueError(
                    "completed run cannot contain errors or missing information"
                )
            assert self.assessment is not None
            assert self.proposal is not None
            if self.assessment.project_id != self.project_id:
                raise ValueError("completed assessment must belong to the run project")
            if (
                self.assessment.weighted_score != self.proposal.weighted_score
                or self.assessment.gate_disposition
                is not self.proposal.gate_disposition
                or self.assessment.recommendation is not self.proposal.recommendation
            ):
                raise ValueError(
                    "completed assessment and proposal decisions must be consistent"
                )
            return self

        if has_any_final or self.completed_at is not None:
            raise ValueError(
                "non-completed run cannot contain a formal result or completed_at"
            )
        if self.status is PlanningRunStatus.CLARIFICATION_REQUIRED:
            if not self.clarifying_questions:
                raise ValueError(
                    "clarification_required run needs at least one question"
                )
            question_fields = [question.field for question in self.clarifying_questions]
            if question_fields != self.missing_information:
                raise ValueError(
                    "clarification_required questions must match missing information"
                )
            if has_any_error:
                raise ValueError("clarification_required run cannot contain errors")
            return self

        if self.status is PlanningRunStatus.FAILED:
            if self.error_code is None or self.error_message is None:
                raise ValueError("failed run requires error code and safe message")
            return self

        if has_any_error:
            raise ValueError("created run cannot contain errors")
        return self


class PocProposalRecord(ContractModel):
    id: UUID
    project_id: UUID
    assessment_id: UUID
    schema_version: SchemaVersion
    payload: PocProposal
    created_at: UtcDateTime

    @model_validator(mode="after")
    def payload_version_matches_record(self) -> PocProposalRecord:
        if self.schema_version != self.payload.schema_version:
            raise ValueError("record schema_version must match proposal payload")
        return self


class ReportExport(ContractModel):
    id: UUID
    project_id: UUID
    proposal_id: UUID
    format: Literal[ReportFormat.MARKDOWN]
    content_hash: ContentHash
    local_path: NonEmptyStr
    created_at: UtcDateTime


class AssessmentInput(ContractModel):
    schema_version: SchemaVersion
    project_id: UUID
    session_id: UUID
    assessment_id: UUID | None = None
    evaluated_at: UtcDateTime | None = None
    known_information: dict[str, JSONValue]
    facts: AssessmentFacts | None = None
    tool_outputs: AssessmentToolOutputs | None = None
    evidence: list[EvidenceReference] = Field(default_factory=list)

    @model_validator(mode="after")
    def evidence_ids_are_unique(self) -> AssessmentInput:
        _require_unique([item.id for item in self.evidence], "evidence IDs")
        return self


class AgentState(ContractModel):
    """Serializable execution state without Agent framework objects."""

    schema_version: SchemaVersion
    project_id: UUID
    session_id: UUID
    session_project_id: UUID
    workflow_stage: ProjectStatus
    interview_stage: InterviewStage
    known_fields: dict[str, JSONValue] = Field(default_factory=dict)
    missing_fields: list[NonEmptyStr] = Field(default_factory=list)
    contradictions: list[NonEmptyStr] = Field(default_factory=list)
    questions_asked: list[NonEmptyStr] = Field(default_factory=list)
    clarifying_questions: list[ClarifyingQuestion] = Field(default_factory=list)
    similar_case_ids: list[NonEmptyStr] = Field(default_factory=list)
    evidence_refs: list[UUID] = Field(default_factory=list)
    tool_results: dict[str, JSONValue] = Field(default_factory=dict)
    hard_gate_disposition: GateDisposition | None = None
    assessment_id: UUID | None = None
    proposal_id: UUID | None = None
    proposal: PocProposal | None = None

    @model_validator(mode="after")
    def validate_state_references(self) -> AgentState:
        if self.session_project_id != self.project_id:
            raise ValueError("session project ID must match state project ID")
        pre_assessment_stages = {
            ProjectStatus.DRAFT,
            ProjectStatus.INTERVIEWING,
            ProjectStatus.CLARIFICATION_REQUIRED,
        }
        post_interview_stages = {
            ProjectStatus.READY_FOR_ASSESSMENT,
            ProjectStatus.ASSESSED,
            ProjectStatus.PROPOSAL_GENERATED,
            ProjectStatus.COMPLETE,
        }
        if (
            self.interview_stage is InterviewStage.COMPLETE
            and self.workflow_stage in pre_assessment_stages
        ) or (
            self.workflow_stage in post_interview_stages
            and self.interview_stage is not InterviewStage.COMPLETE
        ):
            raise ValueError("interview stage and workflow stage are inconsistent")
        for field_name in (
            "missing_fields",
            "contradictions",
            "questions_asked",
            "similar_case_ids",
            "evidence_refs",
        ):
            _require_unique(getattr(self, field_name), field_name)
        _require_unique(
            [question.field for question in self.clarifying_questions],
            "clarifying question fields",
        )
        _require_unique(
            [question.question for question in self.clarifying_questions],
            "clarifying question text",
        )
        if (
            self.workflow_stage
            in {
                ProjectStatus.ASSESSED,
                ProjectStatus.PROPOSAL_GENERATED,
                ProjectStatus.COMPLETE,
            }
            and self.assessment_id is None
        ):
            raise ValueError("assessed workflow state requires assessment_id")
        if (
            self.workflow_stage
            in {
                ProjectStatus.PROPOSAL_GENERATED,
                ProjectStatus.COMPLETE,
            }
            and self.proposal_id is None
        ):
            raise ValueError("proposal workflow state requires proposal_id")
        if self.proposal is not None and self.proposal_id is None:
            raise ValueError("proposal payload requires proposal_id")
        return self
