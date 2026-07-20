"""Application service for the M2.1 analysis-project lifecycle."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from pydantic import ValidationError

from ai_poc_planner.domain.enums import ProjectStatus
from ai_poc_planner.domain.models import AnalysisProject
from ai_poc_planner.persistence.errors import InvalidProjectInputError


class ProjectRepository(Protocol):
    def create(self, project: AnalysisProject) -> AnalysisProject: ...

    def get(self, project_id: UUID) -> AnalysisProject: ...


def _utc_now() -> datetime:
    return datetime.now(UTC)


class AnalysisProjectService:
    """Assign business identity/time, then delegate durable storage."""

    def __init__(
        self,
        repository: ProjectRepository,
        *,
        uuid_factory: Callable[[], UUID] = uuid4,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._repository = repository
        self._uuid_factory = uuid_factory
        self._clock = clock

    def create(
        self,
        *,
        title: str,
        problem_statement: str,
    ) -> AnalysisProject:
        timestamp = self._clock()
        try:
            project = AnalysisProject(
                id=self._uuid_factory(),
                title=title,
                problem_statement=problem_statement,
                status=ProjectStatus.DRAFT,
                created_at=timestamp,
                updated_at=timestamp,
            )
        except ValidationError as error:
            raise InvalidProjectInputError(
                "project creation input does not satisfy its contract"
            ) from error
        return self._repository.create(project)

    def load(self, project_id: UUID) -> AnalysisProject:
        return self._repository.get(project_id)
