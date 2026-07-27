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
    """A safe, report-oriented explanation of one persisted interview turn."""

    topic: NonEmptyStr
    initial_understanding: NonEmptyStr
    clarification: NonEmptyStr
    assessment_impact: NonEmptyStr
    source_question: NonEmptyStr
    answer_summary: NonEmptyStr


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
    suitable_reason: NonEmptyStr
    benefits: list[NonEmptyStr] = Field(default_factory=list)
    limitations_risks: list[NonEmptyStr] = Field(default_factory=list)
    prerequisites: list[NonEmptyStr] = Field(default_factory=list)
    conclusion: NonEmptyStr
    recommended: bool = False


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
    safe_interview_qa: list[SafeInterviewQuestionAnswer] = Field(default_factory=list)
    evidence_basis: list[NonEmptyStr] = Field(default_factory=list)


class ReportSynthesis(ContractModel):
    """Canonical article view model shared by the API response and Markdown export."""

    schema_version: Literal["2.0"] = "2.0"
    executive_narrative: NonEmptyStr
    project_context_narrative: NonEmptyStr
    interview_findings: list[InterviewFinding] = Field(default_factory=list)
    current_target_comparison: list[CurrentTargetComparison] = Field(min_length=1)
    option_comparison: list[OptionComparison] = Field(min_length=1)
    case_comparison: list[CaseComparison] = Field(default_factory=list)
    recommendation_narrative: NonEmptyStr
    implementation_roadmap: list[RoadmapPhase] = Field(min_length=1)
    hard_gate_summary: list[GateBoundarySummary] = Field(default_factory=list)
    risk_and_boundary_summary: NonEmptyStr
    next_actions: list[NonEmptyStr] = Field(min_length=1)
    appendix: ReportAppendix


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
