"""Persisted coordinator around the existing deterministic offline workflow."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID, uuid5

from ai_poc_planner.application.contracts import OfflinePlanningRequest
from ai_poc_planner.application.planning_runs import PlanningRunService
from ai_poc_planner.application.workflow import (
    ClarificationRequiredError,
    PlanningError,
    run_offline_planning,
)
from ai_poc_planner.domain.enums import EvidenceSourceType, PlanningRunStatus
from ai_poc_planner.domain.models import AnalysisProject, EvidenceReference
from ai_poc_planner.domain.workflow import PlanningRun
from ai_poc_planner.persistence.errors import InvalidPlanningRunTransitionError
from ai_poc_planner.providers.base import ModelProvider


class ProjectReader(Protocol):
    def get(self, project_id: UUID) -> AnalysisProject: ...


def run_and_persist_offline_planning(
    run_id: UUID,
    *,
    service: PlanningRunService,
    project_reader: ProjectReader,
    provider: ModelProvider | None = None,
) -> PlanningRun:
    """Execute one deterministic attempt and persist its terminal step."""
    run = service.load(run_id)
    if run.status is not PlanningRunStatus.CREATED:
        raise InvalidPlanningRunTransitionError(
            f"planning run cannot execute from {run.status.value}"
        )
    project = project_reader.get(run.project_id)
    session_id = uuid5(run.id, "planning-session")
    answers = {
        "scenario": "high_value_low_risk",
        **run.known_information,
        **run.clarification_answers,
    }
    evidence = EvidenceReference(
        id=uuid5(run.id, "interview-evidence"),
        project_id=run.project_id,
        session_id=session_id,
        source_type=EvidenceSourceType.USER_INPUT,
        source_ref=f"planning-run:{run.id}",
        label="Structured planning-run input",
        metadata={"run_id": str(run.id)},
    )
    request = OfflinePlanningRequest(
        project=project,
        session_id=session_id,
        assessment_id=uuid5(run.id, "assessment"),
        evaluated_at=run.updated_at,
        interview_answers=answers,
        evidence=[evidence],
    )
    try:
        result = run_offline_planning(request, provider=provider)
    except ClarificationRequiredError as error:
        return service.require_clarification(
            run.id,
            intent=run.intent,
            known_information=answers,
            questions=list(error.questions[:4]),
        )
    except PlanningError as error:
        return service.fail(
            run.id,
            error_code=error.code,
            error_message="Offline planning could not complete.",
        )
    return service.complete(
        run.id,
        assessment=result.assessment,
        proposal=result.proposal,
        markdown_report=result.markdown,
    )
