"""Versioned relations between approved solutions, cases, and references."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, HttpUrl

from ai_poc_planner.domain.models import ContractModel, NonEmptyStr
from ai_poc_planner.domain.reviewed_cases import ReviewStatus

PracticeKey = NonEmptyStr


class SolutionCaseLink(ContractModel):
    """Editorial relation; a case is never implicitly relevant to all routes."""

    solution_key: NonEmptyStr
    case_id: NonEmptyStr
    support_type: Literal["primary", "supporting", "contra"]
    supported_practice_keys: list[PracticeKey] = Field(default_factory=list)
    applicability_note_zh: NonEmptyStr
    limitation_note_zh: NonEmptyStr
    review_status: ReviewStatus
    content_version: NonEmptyStr


class ReviewedImplementationReference(ContractModel):
    """Official process or product documentation, not an enterprise case."""

    reference_key: NonEmptyStr
    display_title_zh: NonEmptyStr
    publisher: NonEmptyStr
    summary_zh: NonEmptyStr
    supported_practice_keys: list[PracticeKey] = Field(default_factory=list)
    source_name: NonEmptyStr
    source_url: HttpUrl
    review_status: ReviewStatus
    content_version: NonEmptyStr


class GoldenScenarioCoverage(ContractModel):
    """Minimum reviewed evidence required before a formal scenario can report."""

    scenario_id: NonEmptyStr
    expected_solution_key: NonEmptyStr
    required_practice_keys: list[PracticeKey] = Field(default_factory=list)
    minimum_primary_cases: int = Field(ge=0)
    minimum_supporting_cases: int = Field(ge=0)
    minimum_implementation_references: int = Field(ge=0)
    content_version: NonEmptyStr
