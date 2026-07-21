"""Application service for the durable planning-run lifecycle."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from pydantic import ValidationError

from ai_poc_planner.application.projects import ProjectRepository
from ai_poc_planner.domain.enums import PlanningRunStatus
from ai_poc_planner.domain.models import (
    ClarifyingQuestion,
    JSONValue,
    PocProposal,
)
from ai_poc_planner.domain.workflow import Assessment, PlanningRun
from ai_poc_planner.persistence.errors import (
    InvalidPlanningRunInputError,
    InvalidPlanningRunTransitionError,
)


class PlanningRunRepository(Protocol):
    def create(self, run: PlanningRun) -> PlanningRun: ...

    def get(self, run_id: UUID) -> PlanningRun: ...

    def update(self, run: PlanningRun) -> PlanningRun: ...

    def list_for_project(self, project_id: UUID) -> list[PlanningRun]: ...


def _utc_now() -> datetime:
    return datetime.now(UTC)


class PlanningRunService:
    """Apply lifecycle rules while keeping persistence and planning separate."""

    def __init__(
        self,
        repository: PlanningRunRepository,
        project_repository: ProjectRepository,
        *,
        uuid_factory: Callable[[], UUID] = uuid4,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._repository = repository
        self._project_repository = project_repository
        self._uuid_factory = uuid_factory
        self._clock = clock

    def create(
        self,
        *,
        project_id: UUID,
        original_request: str,
        intent: dict[str, JSONValue] | None = None,
        known_information: dict[str, JSONValue] | None = None,
    ) -> PlanningRun:
        self._project_repository.get(project_id)
        timestamp = self._clock()
        try:
            run = PlanningRun(
                id=self._uuid_factory(),
                project_id=project_id,
                status=PlanningRunStatus.CREATED,
                original_request=original_request,
                intent=intent or {"summary": original_request},
                known_information=known_information or {},
                created_at=timestamp,
                updated_at=timestamp,
            )
        except ValidationError as error:
            raise InvalidPlanningRunInputError(
                "planning run creation input does not satisfy its contract"
            ) from error
        return self._repository.create(run)

    def require_clarification(
        self,
        run_id: UUID,
        *,
        intent: dict[str, JSONValue],
        known_information: dict[str, JSONValue],
        questions: list[ClarifyingQuestion],
    ) -> PlanningRun:
        run = self.load(run_id)
        self._require_status(run, PlanningRunStatus.CREATED)
        if not questions:
            raise InvalidPlanningRunInputError(
                "clarification requires at least one question"
            )
        return self._replace(
            run,
            status=PlanningRunStatus.CLARIFICATION_REQUIRED,
            intent=intent,
            known_information=known_information,
            missing_information=[question.field for question in questions],
            clarifying_questions=questions,
            updated_at=self._clock(),
        )

    def submit_clarification(
        self,
        run_id: UUID,
        answers: dict[str, JSONValue],
    ) -> PlanningRun:
        run = self.load(run_id)
        self._require_status(run, PlanningRunStatus.CLARIFICATION_REQUIRED)
        if not answers:
            raise InvalidPlanningRunInputError(
                "clarification answers must not be empty"
            )
        return self._replace(
            run,
            status=PlanningRunStatus.CREATED,
            known_information={**run.known_information, **answers},
            missing_information=[],
            clarification_answers={**run.clarification_answers, **answers},
            updated_at=self._clock(),
        )

    def complete(
        self,
        run_id: UUID,
        *,
        assessment: Assessment,
        proposal: PocProposal,
        markdown_report: str,
    ) -> PlanningRun:
        run = self.load(run_id)
        self._require_status(run, PlanningRunStatus.CREATED)
        timestamp = self._clock()
        return self._replace(
            run,
            status=PlanningRunStatus.COMPLETED,
            assessment=assessment,
            proposal=proposal,
            markdown_report=markdown_report,
            error_code=None,
            error_message=None,
            updated_at=timestamp,
            completed_at=timestamp,
        )

    def fail(
        self,
        run_id: UUID,
        *,
        error_code: str,
        error_message: str,
    ) -> PlanningRun:
        run = self.load(run_id)
        if run.status not in {
            PlanningRunStatus.CREATED,
            PlanningRunStatus.CLARIFICATION_REQUIRED,
        }:
            self._raise_transition(run)
        return self._replace(
            run,
            status=PlanningRunStatus.FAILED,
            missing_information=[],
            error_code=error_code,
            error_message=error_message,
            updated_at=self._clock(),
        )

    def load(self, run_id: UUID) -> PlanningRun:
        return self._repository.get(run_id)

    def list_for_project(self, project_id: UUID) -> list[PlanningRun]:
        self._project_repository.get(project_id)
        return self._repository.list_for_project(project_id)

    def _replace(self, run: PlanningRun, **changes: object) -> PlanningRun:
        try:
            updated = PlanningRun.model_validate({**run.model_dump(), **changes})
        except ValidationError as error:
            raise InvalidPlanningRunInputError(
                "planning run update does not satisfy its contract"
            ) from error
        return self._repository.update(updated)

    @staticmethod
    def _require_status(
        run: PlanningRun,
        expected: PlanningRunStatus,
    ) -> None:
        if run.status is not expected:
            PlanningRunService._raise_transition(run)

    @staticmethod
    def _raise_transition(run: PlanningRun) -> None:
        raise InvalidPlanningRunTransitionError(
            f"planning run cannot transition from {run.status.value}"
        )
