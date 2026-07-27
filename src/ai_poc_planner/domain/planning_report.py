"""Phase 5.2 report contracts; all source facts stay explicit and auditable."""

# ruff: noqa: E501

from __future__ import annotations

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
