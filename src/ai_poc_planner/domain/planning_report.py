"""Phase 5.2 report contracts; all source facts stay explicit and auditable."""

# ruff: noqa: E501

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from ai_poc_planner.domain.analysis import FactToken
from ai_poc_planner.domain.case_centered import CaseCenteredNarrative
from ai_poc_planner.domain.models import ContractModel, NonEmptyStr, UtcDateTime

REPORT_SECTION_KEYS = (
    "executive_summary",
    "requirement_understanding",
    "current_process_and_pain_points",
    "goals_and_proposed_success_criteria",
    "ai_suitability_explanation",
    "recommended_direction_explanation",
    "alternatives_explanation",
    "target_workflow",
    "data_needs_and_gaps",
    "deployment_comparison",
    "poc_scope",
    "in_scope",
    "out_of_scope",
    "kpi_and_acceptance_method",
    "cost_assumptions",
    "implementation_stages_and_roles",
    "risks_governance_and_human_review",
    "open_issues_and_next_actions",
)


class ReportSectionDraft(ContractModel):
    content: NonEmptyStr
    fact_refs: list[FactToken] = Field(min_length=1)


class InterviewFinding(ContractModel):
    """A compact, report-oriented interview finding without the raw prompt."""

    topic: NonEmptyStr
    confirmed_content: NonEmptyStr = "尚待確認。"
    assessment_impact: NonEmptyStr
    # Retain these legacy fields only so an already persisted 2.0 report stays
    # readable. New 2.1 synthesis payloads deliberately omit them.
    initial_understanding: str = Field(default="", exclude=True)
    clarification: str = Field(default="", exclude=True)
    source_question: str = Field(default="", exclude=True)
    answer_summary: str = Field(default="", exclude=True)


class SafeInterviewQuestionAnswer(ContractModel):
    """Visible interview content without persistence identifiers or provider data."""

    question: NonEmptyStr
    why_it_matters: NonEmptyStr
    user_answer: NonEmptyStr
    assessment_impact: NonEmptyStr


class CurrentTargetComparison(ContractModel):
    aspect: NonEmptyStr
    current_state: NonEmptyStr
    target_state: NonEmptyStr
    main_gap: NonEmptyStr
    treatment: NonEmptyStr


class OptionComparison(ContractModel):
    option: NonEmptyStr
    conclusion: NonEmptyStr
    recommended: bool = False
    positioning: NonEmptyStr = "尚待比較。"
    supporting_cases: list[NonEmptyStr] = Field(default_factory=list)
    case_evidence: NonEmptyStr = "目前沒有直接案例支持。"
    transferable_practice: NonEmptyStr = "尚待確認可移植做法。"
    cannot_copy: list[NonEmptyStr] = Field(default_factory=list)
    # Legacy columns are accepted for old persisted reports but are not part of
    # the redesigned report payload.
    suitable_reason: str = Field(default="", exclude=True)
    benefits: list[NonEmptyStr] = Field(default_factory=list, exclude=True)
    limitations_risks: list[NonEmptyStr] = Field(default_factory=list, exclude=True)
    prerequisites: list[NonEmptyStr] = Field(default_factory=list, exclude=True)


class CaseComparison(ContractModel):
    display_title_zh: NonEmptyStr
    original_title: NonEmptyStr
    organization: NonEmptyStr
    why_relevant: NonEmptyStr
    transferable_practice: NonEmptyStr
    cannot_copy: list[NonEmptyStr] = Field(default_factory=list)
    adaptation_conclusion: NonEmptyStr


class RoadmapPhase(ContractModel):
    phase: NonEmptyStr
    description: NonEmptyStr
    actions: list[NonEmptyStr] = Field(min_length=1)
    inputs: list[NonEmptyStr] = Field(min_length=1)
    outputs: list[NonEmptyStr] = Field(min_length=1)
    human_decision_boundary: NonEmptyStr
    not_doing: list[NonEmptyStr] = Field(default_factory=list)
    remaining_gaps: list[NonEmptyStr] = Field(default_factory=list)
    acceptance_criteria: list[NonEmptyStr] = Field(min_length=1)


class ScoreAppendixRow(ContractModel):
    dimension: NonEmptyStr
    judgement: NonEmptyStr
    main_basis: NonEmptyStr
    improvement_condition: NonEmptyStr


class GateAppendixRow(ContractModel):
    gate_id: NonEmptyStr
    limit_content: NonEmptyStr
    affected_stage: NonEmptyStr
    currently_possible: NonEmptyStr
    release_condition: NonEmptyStr


class GateBoundarySummary(ContractModel):
    """Human-readable gate impact shown before the technical appendix."""

    limit_content: NonEmptyStr
    affected_stage: NonEmptyStr
    currently_possible: NonEmptyStr
    release_condition: NonEmptyStr


class ReportAppendix(ContractModel):
    scores: list[ScoreAppendixRow] = Field(default_factory=list)
    hard_gates: list[GateAppendixRow] = Field(default_factory=list)
    # These two fields are legacy-only. Raw Q&A and evidence traces are no
    # longer retained in a user-facing ReportSynthesis payload.
    safe_interview_qa: list[SafeInterviewQuestionAnswer] = Field(
        default_factory=list, exclude=True
    )
    evidence_basis: list[NonEmptyStr] = Field(default_factory=list, exclude=True)


class ReportSynthesis(ContractModel):
    """Canonical article view model shared by the API response and Markdown export."""

    schema_version: Literal["2.0", "2.1"] = "2.1"
    executive_narrative: NonEmptyStr
    recommendation_narrative: NonEmptyStr
    interview_findings: list[InterviewFinding] = Field(default_factory=list)
    current_target_comparison: list[CurrentTargetComparison] = Field(min_length=1)
    option_comparison: list[OptionComparison] = Field(min_length=1)
    comparison_narrative: NonEmptyStr = "本章整合比較候選方案、案例與專案差距。"
    implementation_roadmap: list[RoadmapPhase] = Field(min_length=1)
    major_risks_and_boundaries: list[NonEmptyStr] = Field(default_factory=list)
    appendix: ReportAppendix
    # Legacy fields preserve backwards-compatible parsing for saved 2.0
    # reports. New reports do not serialise or render these fields.
    project_context_narrative: str = Field(default="", exclude=True)
    case_comparison: list[CaseComparison] = Field(default_factory=list, exclude=True)
    hard_gate_summary: list[GateBoundarySummary] = Field(
        default_factory=list, exclude=True
    )
    risk_and_boundary_summary: str = Field(default="", exclude=True)
    next_actions: list[NonEmptyStr] = Field(default_factory=list, exclude=True)


class PlanningReportDraft(ContractModel):
    """Provider-owned explanations only; program-owned analysis values are rendered separately."""

    schema_version: str = Field(pattern=r"^1\.0$")
    executive_summary: ReportSectionDraft
    requirement_understanding: ReportSectionDraft
    current_process_and_pain_points: ReportSectionDraft
    goals_and_proposed_success_criteria: ReportSectionDraft
    ai_suitability_explanation: ReportSectionDraft
    recommended_direction_explanation: ReportSectionDraft
    alternatives_explanation: ReportSectionDraft
    target_workflow: ReportSectionDraft
    data_needs_and_gaps: ReportSectionDraft
    deployment_comparison: ReportSectionDraft
    poc_scope: ReportSectionDraft
    in_scope: ReportSectionDraft
    out_of_scope: ReportSectionDraft
    kpi_and_acceptance_method: ReportSectionDraft
    cost_assumptions: ReportSectionDraft
    implementation_stages_and_roles: ReportSectionDraft
    risks_governance_and_human_review: ReportSectionDraft
    open_issues_and_next_actions: ReportSectionDraft
    case_centered_narrative: CaseCenteredNarrative | None = None

    @model_validator(mode="after")
    def contains_every_required_section(self) -> PlanningReportDraft:
        return self

    def section_items(self) -> tuple[tuple[str, ReportSectionDraft], ...]:
        return tuple((key, getattr(self, key)) for key in REPORT_SECTION_KEYS)


class PlanningReportPartA(ContractModel):
    executive_summary: ReportSectionDraft
    requirement_understanding: ReportSectionDraft
    current_process_and_pain_points: ReportSectionDraft
    goals_and_proposed_success_criteria: ReportSectionDraft
    ai_suitability_explanation: ReportSectionDraft
    recommended_direction_explanation: ReportSectionDraft
    alternatives_explanation: ReportSectionDraft
    target_workflow: ReportSectionDraft
    data_needs_and_gaps: ReportSectionDraft


class PlanningReportPartB(ContractModel):
    deployment_comparison: ReportSectionDraft
    poc_scope: ReportSectionDraft
    in_scope: ReportSectionDraft
    out_of_scope: ReportSectionDraft
    kpi_and_acceptance_method: ReportSectionDraft
    cost_assumptions: ReportSectionDraft
    implementation_stages_and_roles: ReportSectionDraft
    risks_governance_and_human_review: ReportSectionDraft
    open_issues_and_next_actions: ReportSectionDraft


class PersistedPlanningReport(ContractModel):
    id: UUID
    version_id: UUID
    analysis_id: UUID
    report: PlanningReportDraft
    markdown: NonEmptyStr
    created_at: UtcDateTime
    synthesis: ReportSynthesis | None = None
