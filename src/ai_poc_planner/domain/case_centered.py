"""Typed contracts for case-centred assessment results.

These contracts deliberately keep case evidence, project fit, gaps, gates, and
implementation phases separate. They are deterministic result data, not a
provider response and not a second scoring rubric.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import Field

from ai_poc_planner.domain.models import ContractModel, NonEmptyStr
from ai_poc_planner.domain.reviewed_cases import ReviewedCase


class CaseReferenceValueLevel(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class FitLevel(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class FitDimensionStatus(StrEnum):
    SIMILAR = "similar"
    DIFFERENT = "different"
    UNKNOWN = "unknown"


class GapCategory(StrEnum):
    READY = "ready"
    MISSING = "missing"
    NOT_DIRECTLY_TRANSFERABLE = "not_directly_transferable"
    NEEDS_CONFIRMATION = "needs_confirmation"


class CaseReferenceValue(ContractModel):
    level: CaseReferenceValueLevel
    score: int = Field(ge=0, le=100)
    basis: list[NonEmptyStr] = Field(default_factory=list)
    unknown_items: list[NonEmptyStr] = Field(default_factory=list)


class FitDimension(ContractModel):
    name: NonEmptyStr
    status: FitDimensionStatus
    score: int = Field(ge=0, le=100)
    basis: list[NonEmptyStr] = Field(default_factory=list)


class ProjectCaseFit(ContractModel):
    level: FitLevel
    score: int = Field(ge=0, le=100)
    dimensions: list[FitDimension] = Field(min_length=1)
    similarities: list[NonEmptyStr] = Field(default_factory=list)
    key_differences: list[NonEmptyStr] = Field(default_factory=list)
    needs_confirmation: list[NonEmptyStr] = Field(default_factory=list)


class CaseGapAnalysis(ContractModel):
    ready_conditions: list[NonEmptyStr] = Field(default_factory=list)
    missing_conditions: list[NonEmptyStr] = Field(default_factory=list)
    not_directly_transferable: list[NonEmptyStr] = Field(default_factory=list)
    needs_confirmation: list[NonEmptyStr] = Field(default_factory=list)


class MatchedCaseAssessment(ContractModel):
    case: ReviewedCase
    reference_value: CaseReferenceValue
    project_fit: ProjectCaseFit
    gaps: CaseGapAnalysis
    ranking_reasons: list[NonEmptyStr] = Field(min_length=1)


class TransferablePractice(ContractModel):
    name: NonEmptyStr
    source_case_ids: list[NonEmptyStr] = Field(min_length=1)
    source_case_titles: list[NonEmptyStr] = Field(min_length=1)
    case_evidence: NonEmptyStr
    transferable_part: NonEmptyStr
    required_adjustments: list[NonEmptyStr] = Field(default_factory=list)
    current_stage: NonEmptyStr
    prerequisites: list[NonEmptyStr] = Field(default_factory=list)
    not_applicable_scope: list[NonEmptyStr] = Field(default_factory=list)


class HardGateImpact(ContractModel):
    rule_id: NonEmptyStr
    disposition: NonEmptyStr
    affected_stage: NonEmptyStr
    limits: list[NonEmptyStr] = Field(min_length=1)
    does_not_limit: list[NonEmptyStr] = Field(min_length=1)
    release_conditions: list[NonEmptyStr] = Field(default_factory=list)


class ImplementationPhase(ContractModel):
    phase_name: NonEmptyStr
    description: NonEmptyStr
    actions: list[NonEmptyStr] = Field(min_length=1)
    inputs: list[NonEmptyStr] = Field(min_length=1)
    outputs: list[NonEmptyStr] = Field(min_length=1)
    users: list[NonEmptyStr] = Field(min_length=1)
    human_decision_boundary: NonEmptyStr
    not_doing: list[NonEmptyStr] = Field(default_factory=list)
    source_case_ids: list[NonEmptyStr] = Field(default_factory=list)
    remaining_gaps: list[NonEmptyStr] = Field(default_factory=list)
    gate_impacts: list[NonEmptyStr] = Field(default_factory=list)
    acceptance_criteria: list[NonEmptyStr] = Field(min_length=1)


class CaseCenteredNarrative(ContractModel):
    """Typed, non-authoritative narrative derived from deterministic results."""

    executive_summary: NonEmptyStr
    why_these_cases: NonEmptyStr
    transferable_practices_summary: NonEmptyStr
    current_constraints_summary: NonEmptyStr
    phased_path_summary: NonEmptyStr


class CaseCenteredAssessment(ContractModel):
    """The single deterministic result shared by API, UI, and report."""

    schema_version: Literal["1.0"] = "1.0"
    matching_status: Literal["matched", "no_suitable_reviewed_case"]
    matched_cases: list[MatchedCaseAssessment] = Field(default_factory=list)
    no_case_reason: NonEmptyStr | None = None
    transferable_practices: list[TransferablePractice] = Field(default_factory=list)
    gate_impacts: list[HardGateImpact] = Field(default_factory=list)
    phased_path: list[ImplementationPhase] = Field(min_length=1)
    recommendation_title: NonEmptyStr
    recommendation_basis: list[NonEmptyStr] = Field(min_length=1)
