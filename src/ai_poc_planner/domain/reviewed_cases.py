"""Contracts for manually reviewed, local success cases only."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import ConfigDict, Field, HttpUrl, model_validator

from ai_poc_planner.domain.catalog import EvidenceType, OpportunityType
from ai_poc_planner.domain.models import ContractModel, NonEmptyStr

CaseId = str


class ReviewedEvidenceGrade(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class ReviewStatus(StrEnum):
    APPROVED = "approved"
    PENDING = "pending"
    REJECTED = "rejected"


class CaseSourceReference(ContractModel):
    """A user-readable source attached to a reviewed case."""

    label: NonEmptyStr
    url: HttpUrl


class ReviewedCase(ContractModel):
    """A source-backed case approved for deterministic local matching."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="before")
    @classmethod
    def keep_older_records_readable(cls, value: Any) -> Any:
        """Additive defaults keep the P5.1 JSON library backward compatible.

        Missing facts are intentionally represented as empty/None values. The
        presentation layer turns those values into ``未記錄``; they are never
        upgraded to confirmed facts here.
        """

        if not isinstance(value, dict):
            return value
        payload = dict(value)
        payload.setdefault("source_references", [])
        if (
            not payload["source_references"]
            and payload.get("source_name")
            and payload.get("source_url")
        ):
            payload["source_references"] = [
                {"label": payload["source_name"], "url": payload["source_url"]}
            ]
        return payload

    case_id: CaseId = Field(pattern=r"^case-[0-9]{2}$")
    organization: NonEmptyStr
    title: NonEmptyStr
    display_title_zh: NonEmptyStr | None = None
    summary_zh: NonEmptyStr | None = None
    organization_type: NonEmptyStr | None = None
    applicable_context: list[NonEmptyStr] = Field(default_factory=list)
    opportunity_types: list[OpportunityType] = Field(min_length=1)
    business_problem: NonEmptyStr
    workflow_scope: NonEmptyStr | None = None
    solution_pattern: NonEmptyStr | None = None
    required_inputs: list[NonEmptyStr] = Field(default_factory=list)
    system_dependencies: list[NonEmptyStr] = Field(default_factory=list)
    governance_conditions: list[NonEmptyStr] = Field(default_factory=list)
    decision_authority: NonEmptyStr | None = None
    processing_boundary: NonEmptyStr | None = None
    implementation_stage: NonEmptyStr | None = None
    implementation_method: NonEmptyStr
    reported_outcomes: list[NonEmptyStr] = Field(default_factory=list)
    measurable_outcomes: list[NonEmptyStr] = Field(default_factory=list)
    applicability_tags: list[NonEmptyStr] = Field(default_factory=list)
    non_applicability_tags: list[NonEmptyStr] = Field(default_factory=list)
    human_oversight: list[NonEmptyStr] = Field(default_factory=list)
    risks_or_limitations: list[NonEmptyStr] = Field(default_factory=list)
    evidence_type: EvidenceType
    evidence_grade: ReviewedEvidenceGrade
    source_name: NonEmptyStr
    source_url: HttpUrl
    source_references: list[CaseSourceReference] = Field(default_factory=list)
    review_status: ReviewStatus
    review_notes: NonEmptyStr | None = None

    @model_validator(mode="after")
    def approved_case_has_source(self) -> ReviewedCase:
        if self.review_status is ReviewStatus.APPROVED and (
            not self.source_name or not self.source_url
        ):
            raise ValueError("approved cases require a source")
        return self
