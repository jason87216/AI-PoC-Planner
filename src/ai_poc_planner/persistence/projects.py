"""SQLite repository for the AnalysisProject aggregate."""

from __future__ import annotations

import sqlite3
from uuid import UUID

from pydantic import ValidationError

from ai_poc_planner.domain.models import AnalysisProject
from ai_poc_planner.persistence.errors import (
    DatabaseOperationError,
    InvalidProjectInputError,
    InvalidStoredProjectError,
    ProjectAlreadyExistsError,
    ProjectNotFoundError,
)

_INSERT_PROJECT = """
INSERT INTO analysis_projects (
    id, title, problem_statement, status, created_at, updated_at
) VALUES (?, ?, ?, ?, ?, ?)
"""
_SELECT_PROJECT = """
SELECT id, title, problem_statement, status, created_at, updated_at
FROM analysis_projects
WHERE id = ?
"""
_DUPLICATE_CONSTRAINT_CODES = {
    sqlite3.SQLITE_CONSTRAINT_PRIMARYKEY,
    sqlite3.SQLITE_CONSTRAINT_UNIQUE,
}


def _rollback_quietly(connection: sqlite3.Connection) -> None:
    try:
        connection.rollback()
    except sqlite3.Error:
        pass


def _validate_input(project: AnalysisProject) -> AnalysisProject:
    if not isinstance(project, AnalysisProject):
        raise InvalidProjectInputError("project input does not match AnalysisProject")
    try:
        return AnalysisProject.model_validate(project.model_dump())
    except ValidationError as error:
        raise InvalidProjectInputError(
            "project input does not satisfy the AnalysisProject contract"
        ) from error


class SQLiteProjectRepository:
    """Create and load projects through one explicit caller-owned connection."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def create(self, project: AnalysisProject) -> AnalysisProject:
        validated = _validate_input(project)
        values = (
            str(validated.id),
            validated.title,
            validated.problem_statement,
            validated.status.value,
            validated.created_at.isoformat(),
            validated.updated_at.isoformat(),
        )
        try:
            self._connection.execute("BEGIN")
            self._connection.execute(_INSERT_PROJECT, values)
            self._connection.commit()
        except sqlite3.IntegrityError as error:
            _rollback_quietly(self._connection)
            if getattr(error, "sqlite_errorcode", None) in _DUPLICATE_CONSTRAINT_CODES:
                raise ProjectAlreadyExistsError(
                    "analysis project already exists"
                ) from error
            raise DatabaseOperationError("unable to create analysis project") from error
        except sqlite3.Error as error:
            _rollback_quietly(self._connection)
            raise DatabaseOperationError("unable to create analysis project") from error
        return self.get(validated.id)

    def get(self, project_id: UUID) -> AnalysisProject:
        if not isinstance(project_id, UUID):
            raise InvalidProjectInputError("project ID must be a UUID")
        try:
            row = self._connection.execute(
                _SELECT_PROJECT,
                (str(project_id),),
            ).fetchone()
        except sqlite3.Error as error:
            raise DatabaseOperationError("unable to load analysis project") from error
        if row is None:
            raise ProjectNotFoundError("analysis project was not found")
        try:
            return AnalysisProject.model_validate(dict(row))
        except ValidationError as error:
            raise InvalidStoredProjectError(
                "stored analysis project does not satisfy its contract"
            ) from error
