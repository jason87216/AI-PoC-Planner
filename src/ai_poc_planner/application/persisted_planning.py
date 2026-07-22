"""Compose the bounded planning Agent with the existing persisted workflow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from ai_poc_planner.agent.contracts import PlanningEvaluation, PlanningIntent
from ai_poc_planner.agent.planning import (
    PlanningAgent,
    build_planning_result,
    evaluate_planning_intent,
)
from ai_poc_planner.application.planning_runs import PlanningRunService
from ai_poc_planner.application.planning_workflow import (
    run_and_persist_offline_planning,
)
from ai_poc_planner.application.projects import AnalysisProjectService
from ai_poc_planner.domain.enums import PlanningRunStatus
from ai_poc_planner.domain.models import AnalysisProject, JSONValue
from ai_poc_planner.domain.workflow import PlanningRun
from ai_poc_planner.persistence.errors import InvalidPlanningRunTransitionError
from ai_poc_planner.providers.base import ModelProvider


class ProjectReader(Protocol):
    def get(self, project_id: UUID) -> AnalysisProject: ...


@dataclass(frozen=True)
class PersistedPlanningOutcome:
    """One run state paired with the tool evaluation that produced it."""

    run: PlanningRun
    evaluation: PlanningEvaluation


class PersistedPlanningFlow:
    """A small application-specific bridge; it owns no durable mutable state."""

    def __init__(
        self,
        *,
        planning_agent: PlanningAgent,
        projects: AnalysisProjectService,
        planning_runs: PlanningRunService,
        project_reader: ProjectReader,
        assessment_provider: ModelProvider,
    ) -> None:
        self._planning_agent = planning_agent
        self._projects = projects
        self._planning_runs = planning_runs
        self._project_reader = project_reader
        self._assessment_provider = assessment_provider

    def start(
        self,
        natural_language_request: str,
        clarification_answers: dict[str, JSONValue],
    ) -> PersistedPlanningOutcome:
        evaluation = self._interpret(natural_language_request, clarification_answers)
        project = self._projects.create(
            title=evaluation.intent.request_summary or "AI PoC planning request",
            problem_statement=natural_language_request,
        )
        run = self._planning_runs.create(
            project_id=project.id,
            original_request=natural_language_request,
            intent=evaluation.intent.model_dump(mode="json"),
            known_information=clarification_answers,
        )
        return self._advance(run, evaluation)

    def submit_clarification(
        self,
        run_id: UUID,
        answers: dict[str, JSONValue],
    ) -> PersistedPlanningOutcome:
        run = self._planning_runs.load(run_id)
        if run.status is not PlanningRunStatus.CLARIFICATION_REQUIRED:
            raise InvalidPlanningRunTransitionError(
                f"planning run cannot transition from {run.status.value}"
            )
        accumulated_answers = {**run.clarification_answers, **answers}
        evaluation = self._interpret(run.original_request, accumulated_answers)
        refreshed = self._planning_runs.submit_clarification(
            run_id,
            answers,
            intent=evaluation.intent.model_dump(mode="json"),
        )
        return self._advance(refreshed, evaluation)

    def load(self, run_id: UUID) -> PersistedPlanningOutcome:
        run = self._planning_runs.load(run_id)
        intent = PlanningIntent.model_validate(run.intent)
        return PersistedPlanningOutcome(
            run=run,
            evaluation=evaluate_planning_intent(intent),
        )

    def _interpret(
        self,
        natural_language_request: str,
        clarification_answers: dict[str, JSONValue],
    ) -> PlanningEvaluation:
        return self._planning_agent.interpret(
            natural_language_request=natural_language_request,
            clarification_answers=clarification_answers,
        )

    def _advance(
        self,
        run: PlanningRun,
        evaluation: PlanningEvaluation,
    ) -> PersistedPlanningOutcome:
        planning_result = build_planning_result(evaluation)
        if planning_result.status == "clarification_required":
            return PersistedPlanningOutcome(
                run=self._planning_runs.require_clarification(
                    run.id,
                    intent=evaluation.intent.model_dump(mode="json"),
                    known_information=run.known_information,
                    questions=planning_result.clarifying_questions,
                ),
                evaluation=evaluation,
            )
        return PersistedPlanningOutcome(
            run=run_and_persist_offline_planning(
                run.id,
                service=self._planning_runs,
                project_reader=self._project_reader,
                provider=self._assessment_provider,
            ),
            evaluation=evaluation,
        )
