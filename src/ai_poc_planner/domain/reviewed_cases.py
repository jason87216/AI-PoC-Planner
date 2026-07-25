"""Contracts for manually reviewed, local success cases only."""

from __future__ import annotations

from enum import StrEnum

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


class ReviewedCase(ContractModel):
    """A source-backed case approved for deterministic local matching."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: CaseId = Field(pattern=r"^case-[0-9]{2}$")
    organization: NonEmptyStr
    title: NonEmptyStr
    opportunity_types: list[OpportunityType] = Field(min_length=1)
    business_problem: NonEmptyStr
    implementation_method: NonEmptyStr
    reported_outcomes: list[NonEmptyStr] = Field(default_factory=list)
    applicability_tags: list[NonEmptyStr] = Field(default_factory=list)
    non_applicability_tags: list[NonEmptyStr] = Field(default_factory=list)
    human_oversight: list[NonEmptyStr] = Field(default_factory=list)
    risks_or_limitations: list[NonEmptyStr] = Field(default_factory=list)
    evidence_type: EvidenceType
    evidence_grade: ReviewedEvidenceGrade
    source_name: NonEmptyStr
    source_url: HttpUrl
    review_status: ReviewStatus
    review_notes: NonEmptyStr | None = None

    @model_validator(mode="after")
    def approved_case_has_source(self) -> ReviewedCase:
        if self.review_status is ReviewStatus.APPROVED and (
            not self.source_name or not self.source_url
        ):
            raise ValueError("approved cases require a source")
        return self
