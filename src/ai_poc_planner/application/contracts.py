"""Typed input and output contracts for the offline planning application."""

from __future__ import annotations

from uuid import UUID

from pydantic import Field, model_validator

from ai_poc_planner.domain.models import (
    AnalysisProject,
    ContractModel,
    EvidenceReference,
    JSONValue,
    NonEmptyStr,
    PocProposal,
    UtcDateTime,
)
from ai_poc_planner.domain.workflow import Assessment


class OfflinePlanningRequest(ContractModel):
    project: AnalysisProject
    session_id: UUID
    assessment_id: UUID
    evaluated_at: UtcDateTime
    interview_answers: dict[str, JSONValue] = Field(default_factory=dict)
    evidence: list[EvidenceReference] = Field(default_factory=list)
    output_path: NonEmptyStr | None = None
    fail_tool: NonEmptyStr | None = None

    @model_validator(mode="after")
    def evidence_ids_are_unique(self) -> OfflinePlanningRequest:
        ids = [item.id for item in self.evidence]
        if len(ids) != len(set(ids)):
            raise ValueError("evidence IDs must not contain duplicates")
        return self


class OfflinePlanningResult(ContractModel):
    project: AnalysisProject
    assessment: Assessment
    proposal: PocProposal
    markdown: NonEmptyStr
    report_path: NonEmptyStr | None = None
