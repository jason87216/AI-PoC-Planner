"""Contracts for the reviewed solution catalogue used at runtime."""

from __future__ import annotations

from typing import Literal

from pydantic import ConfigDict

from ai_poc_planner.domain.models import ContractModel, NonEmptyStr
from ai_poc_planner.domain.reviewed_cases import ReviewStatus


class SolutionPattern(ContractModel):
    """Human-authored solution content; providers never create these values."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    solution_key: NonEmptyStr
    recommendation_category: Literal[
        "ai_hybrid", "rules_first", "governed_assistive", "readiness_first"
    ]
    display_name_zh: NonEmptyStr
    short_description_zh: NonEmptyStr
    detailed_description_zh: NonEmptyStr
    suitable_when_zh: NonEmptyStr
    not_suitable_when_zh: NonEmptyStr
    typical_scope_zh: NonEmptyStr
    human_boundary_zh: NonEmptyStr
    expected_outputs_zh: NonEmptyStr
    acceptance_focus_zh: NonEmptyStr
    review_status: ReviewStatus
    content_version: NonEmptyStr
    created_at: NonEmptyStr
    updated_at: NonEmptyStr
