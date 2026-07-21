"""SQLite repository for durable PlanningRun records."""

from __future__ import annotations

import json
import sqlite3
from uuid import UUID

from pydantic import ValidationError

from ai_poc_planner.domain.workflow import PlanningRun
from ai_poc_planner.persistence.errors import (
    DatabaseOperationError,
    InvalidPlanningRunInputError,
    InvalidStoredPlanningRunError,
    PlanningRunAlreadyExistsError,
    PlanningRunNotFoundError,
    ProjectNotFoundError,
)

_COLUMNS = """
id, project_id, status, original_request, intent_json,
known_information_json, missing_information_json, clarifying_questions_json,
clarification_answers_json, assessment_json, proposal_json, markdown_report,
error_code, error_message, created_at, updated_at, completed_at
"""
_INSERT = f"INSERT INTO planning_runs ({_COLUMNS}) VALUES ({', '.join(['?'] * 17)})"
_SELECT_ONE = f"SELECT {_COLUMNS} FROM planning_runs WHERE id = ?"
_SELECT_PROJECT = f"""
SELECT {_COLUMNS}
FROM planning_runs
WHERE project_id = ?
ORDER BY created_at DESC, id DESC
"""
_UPDATE = """
UPDATE planning_runs SET
    status = ?, original_request = ?, intent_json = ?, known_information_json = ?,
    missing_information_json = ?, clarifying_questions_json = ?,
    clarification_answers_json = ?, assessment_json = ?, proposal_json = ?,
    markdown_report = ?, error_code = ?, error_message = ?, updated_at = ?,
    completed_at = ?
WHERE id = ? AND project_id = ?
"""
_DUPLICATE_CODES = {
    sqlite3.SQLITE_CONSTRAINT_PRIMARYKEY,
    sqlite3.SQLITE_CONSTRAINT_UNIQUE,
}


def _rollback_quietly(connection: sqlite3.Connection) -> None:
    try:
        connection.rollback()
    except sqlite3.Error:
        pass


def _json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _validated_input(run: PlanningRun) -> PlanningRun:
    if not isinstance(run, PlanningRun):
        raise InvalidPlanningRunInputError("input does not match PlanningRun")
    try:
        return PlanningRun.model_validate(run.model_dump())
    except ValidationError as error:
        raise InvalidPlanningRunInputError(
            "planning run input does not satisfy its contract"
        ) from error


def _values(run: PlanningRun) -> tuple[object, ...]:
    return (
        str(run.id),
        str(run.project_id),
        run.status.value,
        run.original_request,
        _json(run.intent),
        _json(run.known_information),
        _json(run.missing_information),
        _json(
            [question.model_dump(mode="json") for question in run.clarifying_questions]
        ),
        _json(run.clarification_answers),
        _json(run.assessment.model_dump(mode="json")) if run.assessment else None,
        _json(run.proposal.model_dump(mode="json")) if run.proposal else None,
        run.markdown_report,
        run.error_code,
        run.error_message,
        run.created_at.isoformat(),
        run.updated_at.isoformat(),
        run.completed_at.isoformat() if run.completed_at else None,
    )


def _from_row(row: sqlite3.Row) -> PlanningRun:
    try:
        payload = {
            "id": row["id"],
            "project_id": row["project_id"],
            "status": row["status"],
            "original_request": row["original_request"],
            "intent": json.loads(row["intent_json"]),
            "known_information": json.loads(row["known_information_json"]),
            "missing_information": json.loads(row["missing_information_json"]),
            "clarifying_questions": json.loads(row["clarifying_questions_json"]),
            "clarification_answers": json.loads(row["clarification_answers_json"]),
            "assessment": (
                json.loads(row["assessment_json"])
                if row["assessment_json"] is not None
                else None
            ),
            "proposal": (
                json.loads(row["proposal_json"])
                if row["proposal_json"] is not None
                else None
            ),
            "markdown_report": row["markdown_report"],
            "error_code": row["error_code"],
            "error_message": row["error_message"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "completed_at": row["completed_at"],
        }
        return PlanningRun.model_validate(payload)
    except (json.JSONDecodeError, TypeError, ValidationError, ValueError) as error:
        raise InvalidStoredPlanningRunError(
            "stored planning run does not satisfy its contract"
        ) from error


class SQLitePlanningRunRepository:
    """Create, load, replace and list runs on one caller-owned connection."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def create(self, run: PlanningRun) -> PlanningRun:
        validated = _validated_input(run)
        try:
            self._connection.execute("BEGIN")
            self._connection.execute(_INSERT, _values(validated))
            self._connection.commit()
        except sqlite3.IntegrityError as error:
            _rollback_quietly(self._connection)
            code = getattr(error, "sqlite_errorcode", None)
            if code in _DUPLICATE_CODES:
                raise PlanningRunAlreadyExistsError(
                    "planning run already exists"
                ) from error
            if code == sqlite3.SQLITE_CONSTRAINT_FOREIGNKEY:
                raise ProjectNotFoundError(
                    "analysis project for planning run was not found"
                ) from error
            raise DatabaseOperationError("unable to create planning run") from error
        except sqlite3.Error as error:
            _rollback_quietly(self._connection)
            raise DatabaseOperationError("unable to create planning run") from error
        return self.get(validated.id)

    def get(self, run_id: UUID) -> PlanningRun:
        if not isinstance(run_id, UUID):
            raise InvalidPlanningRunInputError("planning run ID must be a UUID")
        try:
            row = self._connection.execute(_SELECT_ONE, (str(run_id),)).fetchone()
        except sqlite3.Error as error:
            raise DatabaseOperationError("unable to load planning run") from error
        if row is None:
            raise PlanningRunNotFoundError("planning run was not found")
        return _from_row(row)

    def update(self, run: PlanningRun) -> PlanningRun:
        validated = _validated_input(run)
        all_values = _values(validated)
        update_values = (
            all_values[2],
            all_values[3],
            *all_values[4:14],
            all_values[15],
            all_values[16],
            all_values[0],
            all_values[1],
        )
        try:
            self._connection.execute("BEGIN")
            cursor = self._connection.execute(_UPDATE, update_values)
            if cursor.rowcount == 0:
                exists = self._connection.execute(
                    "SELECT project_id FROM planning_runs WHERE id = ?",
                    (str(validated.id),),
                ).fetchone()
                _rollback_quietly(self._connection)
                if exists is None:
                    raise PlanningRunNotFoundError("planning run was not found")
                raise InvalidPlanningRunInputError(
                    "planning run project ownership cannot change"
                )
            self._connection.commit()
        except (PlanningRunNotFoundError, InvalidPlanningRunInputError):
            raise
        except sqlite3.Error as error:
            _rollback_quietly(self._connection)
            raise DatabaseOperationError("unable to update planning run") from error
        return self.get(validated.id)

    def list_for_project(self, project_id: UUID) -> list[PlanningRun]:
        if not isinstance(project_id, UUID):
            raise InvalidPlanningRunInputError("project ID must be a UUID")
        try:
            rows = self._connection.execute(
                _SELECT_PROJECT,
                (str(project_id),),
            ).fetchall()
        except sqlite3.Error as error:
            raise DatabaseOperationError("unable to list planning runs") from error
        return [_from_row(row) for row in rows]
