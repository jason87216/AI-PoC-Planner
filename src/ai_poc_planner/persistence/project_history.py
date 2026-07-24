"""SQLite persistence for the Phase 2 planning-project version aggregate."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from uuid import UUID, uuid4

from pydantic import ValidationError

from ai_poc_planner.domain.enums import InterviewRole
from ai_poc_planner.domain.project_history import (
    FactRevision,
    PlanningProject,
    ProjectHistorySummary,
    ProjectVersion,
    VisibleConversationMessage,
)
from ai_poc_planner.persistence.errors import (
    CompletedVersionImmutableError,
    DatabaseOperationError,
    FactNotFoundError,
    FactReferenceInvalidError,
    ProjectNotFoundError,
    ProjectVersionNotFoundError,
)


def normalize_fact_key(value: str) -> str:
    """Use one stable comparison form without changing the user-visible key."""

    return value.strip().casefold()


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class SQLiteProjectHistoryRepository:
    """Persist Phase 2 records through one explicit caller-owned connection."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    @contextmanager
    def _transaction(self) -> Iterator[None]:
        try:
            self._connection.execute("BEGIN")
            yield
            self._connection.commit()
        except sqlite3.Error as error:
            self._rollback_quietly()
            if "completed version is immutable" in str(error):
                raise CompletedVersionImmutableError(
                    "completed versions cannot be modified"
                ) from error
            raise DatabaseOperationError("unable to persist project history") from error
        except Exception:
            self._rollback_quietly()
            raise

    def _rollback_quietly(self) -> None:
        try:
            self._connection.rollback()
        except sqlite3.Error:
            pass

    def create_project_with_version(
        self,
        project: PlanningProject,
        version: ProjectVersion,
    ) -> tuple[PlanningProject, ProjectVersion]:
        with self._transaction():
            self._connection.execute(
                "INSERT INTO planning_projects "
                "(id, project_name, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (
                    str(project.id),
                    project.project_name,
                    project.created_at.isoformat(),
                    project.updated_at.isoformat(),
                ),
            )
            self._insert_version(version)
        return self.get_project(project.id), self.get_version(project.id, 1)

    def list_projects(self) -> list[PlanningProject]:
        try:
            rows = self._connection.execute(
                "SELECT id, project_name, created_at, updated_at "
                "FROM planning_projects ORDER BY updated_at DESC, id DESC"
            ).fetchall()
        except sqlite3.Error as error:
            raise DatabaseOperationError("unable to list planning projects") from error
        return [self._project_from_row(row) for row in rows]

    def get_project(self, project_id: UUID) -> PlanningProject:
        try:
            row = self._connection.execute(
                "SELECT id, project_name, created_at, updated_at "
                "FROM planning_projects WHERE id = ?",
                (str(project_id),),
            ).fetchone()
        except sqlite3.Error as error:
            raise DatabaseOperationError("unable to load planning project") from error
        if row is None:
            raise ProjectNotFoundError("planning project was not found")
        return self._project_from_row(row)

    def list_versions(self, project_id: UUID) -> list[ProjectVersion]:
        self.get_project(project_id)
        try:
            rows = self._connection.execute(
                "SELECT * FROM planning_project_versions WHERE project_id = ? "
                "ORDER BY version_number ASC",
                (str(project_id),),
            ).fetchall()
        except sqlite3.Error as error:
            raise DatabaseOperationError("unable to list project versions") from error
        return [self._version_from_row(row) for row in rows]

    def get_version(self, project_id: UUID, version_number: int) -> ProjectVersion:
        try:
            row = self._connection.execute(
                "SELECT * FROM planning_project_versions WHERE project_id = ? "
                "AND version_number = ?",
                (str(project_id), version_number),
            ).fetchone()
        except sqlite3.Error as error:
            raise DatabaseOperationError("unable to load project version") from error
        if row is None:
            raise ProjectVersionNotFoundError("project version was not found")
        return self._version_from_row(row)

    def get_latest_version(self, project_id: UUID) -> ProjectVersion:
        try:
            row = self._connection.execute(
                "SELECT * FROM planning_project_versions WHERE project_id = ? "
                "ORDER BY version_number DESC LIMIT 1",
                (str(project_id),),
            ).fetchone()
        except sqlite3.Error as error:
            raise DatabaseOperationError(
                "unable to load latest project version"
            ) from error
        if row is None:
            self.get_project(project_id)
            raise ProjectVersionNotFoundError("project version was not found")
        return self._version_from_row(row)

    def list_summaries(self) -> list[ProjectHistorySummary]:
        try:
            rows = self._connection.execute(
                "SELECT p.id AS project_id, p.project_name, v.version_number, "
                "v.status, v.created_at, v.updated_at, v.completed_at, "
                "v.profile_name, v.model_name "
                "FROM planning_projects p JOIN planning_project_versions v "
                "ON v.project_id = p.id "
                "WHERE v.version_number = (SELECT MAX(v2.version_number) "
                "FROM planning_project_versions v2 WHERE v2.project_id = p.id) "
                "ORDER BY p.updated_at DESC, p.id DESC"
            ).fetchall()
        except sqlite3.Error as error:
            raise DatabaseOperationError("unable to list project history") from error
        try:
            return [ProjectHistorySummary.model_validate(dict(row)) for row in rows]
        except ValidationError as error:
            raise DatabaseOperationError("stored project history is invalid") from error

    def complete_version(
        self, version: ProjectVersion, project_updated_at: datetime
    ) -> ProjectVersion:
        with self._transaction():
            cursor = self._connection.execute(
                "UPDATE planning_project_versions SET status = ?, updated_at = ?, "
                "completed_at = ? WHERE id = ? AND project_id = ?",
                (
                    version.status.value,
                    version.updated_at.isoformat(),
                    version.completed_at.isoformat() if version.completed_at else None,
                    str(version.id),
                    str(version.project_id),
                ),
            )
            if cursor.rowcount != 1:
                raise ProjectVersionNotFoundError("project version was not found")
            self._touch_project(version.project_id, project_updated_at)
        return self.get_version(version.project_id, version.version_number)

    def create_successor(
        self,
        source: ProjectVersion,
        successor: ProjectVersion,
        project_updated_at: datetime,
    ) -> ProjectVersion:
        with self._transaction():
            self._insert_version(successor)
            message_map = self._clone_messages(source.id, successor.id)
            self._clone_current_facts(source.id, successor.id, message_map)
            self._touch_project(successor.project_id, project_updated_at)
        return self.get_version(successor.project_id, successor.version_number)

    def append_message(
        self,
        *,
        version_id: UUID,
        role: InterviewRole | str,
        message_kind: str,
        content: str,
        created_at: datetime,
        message_id: UUID,
        project_updated_at: datetime | None = None,
        copied_from_message_id: UUID | None = None,
    ) -> VisibleConversationMessage:
        version = self.get_version_by_id(version_id)
        with self._transaction():
            next_sequence = self._connection.execute(
                "SELECT COALESCE(MAX(sequence), 0) + 1 FROM "
                "visible_conversation_messages WHERE version_id = ?",
                (str(version_id),),
            ).fetchone()[0]
            self._connection.execute(
                "INSERT INTO visible_conversation_messages "
                "(id, version_id, sequence, role, message_kind, content, created_at, "
                "copied_from_message_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    str(message_id),
                    str(version_id),
                    next_sequence,
                    str(role),
                    str(message_kind),
                    content,
                    created_at.isoformat(),
                    str(copied_from_message_id) if copied_from_message_id else None,
                ),
            )
            self._touch_project(version.project_id, project_updated_at or created_at)
        return self.get_message(message_id)

    def list_messages(self, version_id: UUID) -> list[VisibleConversationMessage]:
        try:
            rows = self._connection.execute(
                "SELECT * FROM visible_conversation_messages WHERE version_id = ? "
                "ORDER BY sequence ASC",
                (str(version_id),),
            ).fetchall()
        except sqlite3.Error as error:
            raise DatabaseOperationError("unable to list visible messages") from error
        return [self._message_from_row(row) for row in rows]

    def get_message(self, message_id: UUID) -> VisibleConversationMessage:
        try:
            row = self._connection.execute(
                "SELECT * FROM visible_conversation_messages WHERE id = ?",
                (str(message_id),),
            ).fetchone()
        except sqlite3.Error as error:
            raise DatabaseOperationError("unable to load visible message") from error
        if row is None:
            raise DatabaseOperationError("visible message was not found")
        return self._message_from_row(row)

    def create_fact(
        self,
        fact: FactRevision,
        *,
        project_updated_at: datetime,
    ) -> FactRevision:
        version = self.get_version_by_id(fact.version_id)
        with self._transaction():
            self._insert_fact(fact)
            self._touch_project(version.project_id, project_updated_at)
        return self.get_fact(fact.id)

    def get_fact(self, fact_id: UUID) -> FactRevision:
        try:
            row = self._connection.execute(
                "SELECT * FROM project_fact_revisions WHERE id = ?", (str(fact_id),)
            ).fetchone()
        except sqlite3.Error as error:
            raise DatabaseOperationError("unable to load fact revision") from error
        if row is None:
            raise FactNotFoundError("fact revision was not found")
        return self._fact_from_row(row)

    def list_current_facts(self, version_id: UUID) -> list[FactRevision]:
        return self._facts_for_version(version_id, current_only=True)

    def list_fact_history(self, version_id: UUID) -> list[FactRevision]:
        return self._facts_for_version(version_id, current_only=False)

    def get_version_by_id(self, version_id: UUID) -> ProjectVersion:
        try:
            row = self._connection.execute(
                "SELECT * FROM planning_project_versions WHERE id = ?",
                (str(version_id),),
            ).fetchone()
        except sqlite3.Error as error:
            raise DatabaseOperationError("unable to load project version") from error
        if row is None:
            raise ProjectVersionNotFoundError("project version was not found")
        return self._version_from_row(row)

    def _insert_version(self, version: ProjectVersion) -> None:
        snapshot = version.selected_model
        self._connection.execute(
            "INSERT INTO planning_project_versions "
            "(id, project_id, version_number, status, based_on_version_id, profile_id, "
            "profile_name, model_name, created_at, updated_at, completed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(version.id),
                str(version.project_id),
                version.version_number,
                version.status.value,
                str(version.based_on_version_id)
                if version.based_on_version_id
                else None,
                str(snapshot.profile_id) if snapshot else None,
                snapshot.profile_name if snapshot else None,
                snapshot.model_name if snapshot else None,
                version.created_at.isoformat(),
                version.updated_at.isoformat(),
                version.completed_at.isoformat() if version.completed_at else None,
            ),
        )

    def _clone_messages(self, source_id: UUID, successor_id: UUID) -> dict[UUID, UUID]:
        source_messages = self.list_messages(source_id)
        mapping: dict[UUID, UUID] = {}
        for source in source_messages:
            cloned_id = uuid4()
            mapping[source.id] = cloned_id
            self._connection.execute(
                "INSERT INTO visible_conversation_messages "
                "(id, version_id, sequence, role, message_kind, content, created_at, "
                "copied_from_message_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    str(cloned_id),
                    str(successor_id),
                    source.sequence,
                    source.role.value,
                    source.message_kind.value,
                    source.content,
                    source.created_at.isoformat(),
                    str(source.id),
                ),
            )
        return mapping

    def _clone_current_facts(
        self,
        source_id: UUID,
        successor_id: UUID,
        message_map: dict[UUID, UUID],
    ) -> None:
        for source in self.list_current_facts(source_id):
            cloned = FactRevision(
                id=uuid4(),
                version_id=successor_id,
                fact_key=source.fact_key,
                value=source.value,
                status=source.status,
                reference_message_ids=[
                    message_map[item] for item in source.reference_message_ids
                ],
                copied_from_fact_id=source.id,
                created_at=source.created_at,
            )
            self._insert_fact(cloned)

    def _insert_fact(self, fact: FactRevision) -> None:
        self._validate_fact_references(fact)
        self._connection.execute(
            "INSERT INTO project_fact_revisions "
            "(id, version_id, fact_key, normalized_fact_key, value_json, status, "
            "supersedes_fact_id, copied_from_fact_id, correction_reason, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(fact.id),
                str(fact.version_id),
                fact.fact_key,
                normalize_fact_key(fact.fact_key),
                _json(fact.value) if fact.value is not None else None,
                fact.status.value,
                str(fact.supersedes_fact_id) if fact.supersedes_fact_id else None,
                str(fact.copied_from_fact_id) if fact.copied_from_fact_id else None,
                fact.correction_reason,
                fact.created_at.isoformat(),
            ),
        )
        self._connection.executemany(
            "INSERT INTO fact_message_references (fact_id, message_id) VALUES (?, ?)",
            [
                (str(fact.id), str(message_id))
                for message_id in fact.reference_message_ids
            ],
        )

    def _validate_fact_references(self, fact: FactRevision) -> None:
        placeholders = ", ".join("?" for _ in fact.reference_message_ids)
        rows = self._connection.execute(
            "SELECT id FROM visible_conversation_messages "
            f"WHERE version_id = ? AND id IN ({placeholders})",
            (str(fact.version_id), *(str(item) for item in fact.reference_message_ids)),
        ).fetchall()
        if len(rows) != len(fact.reference_message_ids):
            raise FactReferenceInvalidError(
                "fact references must be visible messages in the same version"
            )

    def _facts_for_version(
        self, version_id: UUID, *, current_only: bool
    ) -> list[FactRevision]:
        query = "SELECT f.* FROM project_fact_revisions f WHERE f.version_id = ?"
        if current_only:
            query += (
                " AND NOT EXISTS (SELECT 1 FROM project_fact_revisions successor "
                "WHERE successor.supersedes_fact_id = f.id)"
            )
        query += " ORDER BY f.rowid ASC"
        try:
            rows = self._connection.execute(query, (str(version_id),)).fetchall()
        except sqlite3.Error as error:
            raise DatabaseOperationError("unable to list fact revisions") from error
        return [self._fact_from_row(row) for row in rows]

    def _touch_project(self, project_id: UUID, updated_at: datetime) -> None:
        self._connection.execute(
            "UPDATE planning_projects SET updated_at = ? WHERE id = ?",
            (updated_at.isoformat(), str(project_id)),
        )

    @staticmethod
    def _project_from_row(row: sqlite3.Row) -> PlanningProject:
        try:
            return PlanningProject.model_validate(dict(row))
        except ValidationError as error:
            raise DatabaseOperationError(
                "stored planning project is invalid"
            ) from error

    @staticmethod
    def _version_from_row(row: sqlite3.Row) -> ProjectVersion:
        try:
            payload = dict(row)
            if payload["profile_id"] is not None:
                payload["selected_model"] = {
                    "profile_id": payload.pop("profile_id"),
                    "profile_name": payload.pop("profile_name"),
                    "model_name": payload.pop("model_name"),
                }
            else:
                payload.pop("profile_id")
                payload.pop("profile_name")
                payload.pop("model_name")
            return ProjectVersion.model_validate(payload)
        except ValidationError as error:
            raise DatabaseOperationError("stored project version is invalid") from error

    def _message_from_row(self, row: sqlite3.Row) -> VisibleConversationMessage:
        try:
            return VisibleConversationMessage.model_validate(dict(row))
        except ValidationError as error:
            raise DatabaseOperationError("stored visible message is invalid") from error

    def _fact_from_row(self, row: sqlite3.Row) -> FactRevision:
        try:
            refs = self._connection.execute(
                "SELECT message_id FROM fact_message_references WHERE fact_id = ? "
                "ORDER BY message_id",
                (row["id"],),
            ).fetchall()
            payload = dict(row)
            value_json = payload.pop("value_json")
            payload["value"] = (
                json.loads(value_json) if value_json is not None else None
            )
            payload.pop("normalized_fact_key")
            payload["reference_message_ids"] = [item["message_id"] for item in refs]
            return FactRevision.model_validate(payload)
        except (json.JSONDecodeError, ValidationError) as error:
            raise DatabaseOperationError("stored fact revision is invalid") from error
