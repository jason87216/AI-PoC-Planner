"""Contracts owned by the LangChain planning orchestration boundary."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from ai_poc_planner.domain.catalog import (
    DeploymentPostureAssessment,
    DeploymentPostureInput,
    OpportunityMatchInput,
    OpportunityMatchResult,
)
from ai_poc_planner.domain.models import ClarifyingQuestion, ContractModel, NonEmptyStr


class PlanningIntent(ContractModel):
    """Validated model-supplied inputs for the one bounded planning tool."""

    opportunity_input: OpportunityMatchInput
    deployment_input: DeploymentPostureInput
    request_summary: NonEmptyStr | None = None


class PlanningEvaluation(ContractModel):
    """The planning tool's actual deterministic output."""

    intent: PlanningIntent
    opportunity_match: OpportunityMatchResult
    deployment_posture: DeploymentPostureAssessment


class PlanningResult(PlanningEvaluation):
    """HTTP-ready planning state derived only from deterministic outputs."""

    status: Literal["clarification_required", "ready"]
    clarifying_questions: list[ClarifyingQuestion] = Field(default_factory=list)
