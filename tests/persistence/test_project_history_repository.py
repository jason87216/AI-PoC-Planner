import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from ai_poc_planner.application.project_history import ProjectHistoryService
from ai_poc_planner.domain.enums import ProjectStatus
from ai_poc_planner.persistence.connection import database_connection
from ai_poc_planner.persistence.errors import CompletedVersionImmutableError
from ai_poc_planner.persistence.project_history import SQLiteProjectHistoryRepository
from ai_poc_planner.persistence.schema import (
    CURRENT_SCHEMA_VERSION,
    initialize_database,
    read_schema_version,
)


def _service(
    path: Path,
) -> tuple[object, SQLiteProjectHistoryRepository, ProjectHistoryService]:
    connection = database_connection(path)
    initialize_database(connection)
    repository = SQLiteProjectHistoryRepository(connection)
    return connection, repository, ProjectHistoryService(repository)


def test_fresh_schema_contains_phase_two_tables_and_preserves_foreign_keys(
    tmp_path: Path,
) -> None:
    connection = database_connection(tmp_path / "history.sqlite3")
    try:
        initialize_database(connection)
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert read_schema_version(connection) == CURRENT_SCHEMA_VERSION == 3
        assert {
            "analysis_projects",
            "planning_runs",
            "planning_projects",
            "planning_project_versions",
            "visible_conversation_messages",
            "project_fact_revisions",
            "fact_message_references",
        } <= tables
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    finally:
        connection.close()


def test_v1_and_v2_legacy_data_survive_additive_upgrade(tmp_path: Path) -> None:
    for version in (1, 2):
        connection = database_connection(tmp_path / f"legacy-{version}.sqlite3")
        try:
            connection.execute(
                """
                CREATE TABLE analysis_projects (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    problem_statement TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            now = datetime(2026, 7, 24, tzinfo=UTC).isoformat()
            legacy_project_id = str(uuid4())
            connection.execute(
                "INSERT INTO analysis_projects VALUES (?, ?, ?, ?, ?, ?)",
                (legacy_project_id, "legacy", "legacy problem", "draft", now, now),
            )
            if version == 2:
                connection.execute(
                    """
                    CREATE TABLE planning_runs (
                        id TEXT PRIMARY KEY,
                        project_id TEXT NOT NULL REFERENCES analysis_projects(id),
                        status TEXT NOT NULL,
                        original_request TEXT NOT NULL,
                        intent_json TEXT NOT NULL,
                        known_information_json TEXT NOT NULL,
                        missing_information_json TEXT NOT NULL,
                        clarifying_questions_json TEXT NOT NULL,
                        clarification_answers_json TEXT NOT NULL,
                        assessment_json TEXT,
                        proposal_json TEXT,
                        markdown_report TEXT,
                        error_code TEXT,
                        error_message TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        completed_at TEXT
                    )
                    """
                )
                connection.execute(
                    "INSERT INTO planning_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
                    "?, ?, ?, ?, ?, ?, ?)",
                    (
                        str(uuid4()),
                        legacy_project_id,
                        "created",
                        "legacy request",
                        "{}",
                        "{}",
                        "[]",
                        "[]",
                        "{}",
                        None,
                        None,
                        None,
                        None,
                        None,
                        now,
                        now,
                        None,
                    ),
                )
            connection.execute(f"PRAGMA user_version = {version}")
            connection.commit()

            initialize_database(connection)

            assert (
                connection.execute("SELECT COUNT(*) FROM analysis_projects").fetchone()[
                    0
                ]
                == 1
            )
            if version == 2:
                assert (
                    connection.execute("SELECT COUNT(*) FROM planning_runs").fetchone()[
                        0
                    ]
                    == 1
                )
            assert read_schema_version(connection) == 3
        finally:
            connection.close()


def test_project_creation_completion_and_successor_are_durable_and_immutable(
    tmp_path: Path,
) -> None:
    connection, repository, service = _service(tmp_path / "history.sqlite3")
    try:
        project, version = service.create_project("客服流程改善評估")
        completed = service.complete_version(project.id, version.version_number)

        assert completed.status is ProjectStatus.COMPLETE
        assert completed.completed_at is not None
        with pytest.raises(CompletedVersionImmutableError):
            repository.append_message(
                version_id=version.id,
                role="user",
                message_kind="user_input",
                content="must not be stored",
                created_at=datetime.now(UTC),
                message_id=uuid4(),
            )

        successor = service.create_next_version(project.id, 1)
        assert successor.version_number == 2
        assert successor.based_on_version_id == version.id
        assert successor.status is ProjectStatus.DRAFT
        assert repository.get_version(project.id, 1).status is ProjectStatus.COMPLETE
    finally:
        connection.close()


def test_current_schema_incomplete_and_future_versions_are_rejected(
    tmp_path: Path,
) -> None:
    connection = database_connection(tmp_path / "invalid.sqlite3")
    try:
        initialize_database(connection)
        connection.execute("DROP TABLE fact_message_references")
        connection.execute("PRAGMA user_version = 3")
        connection.commit()

        with pytest.raises(Exception) as incomplete:
            initialize_database(connection)
        assert getattr(incomplete.value, "code", None) == "schema_mismatch"

        connection.execute("PRAGMA user_version = 99")
        connection.commit()
        with pytest.raises(Exception) as future:
            initialize_database(connection)
        assert getattr(future.value, "code", None) == "unsupported_schema_version"
    finally:
        connection.close()


def test_failed_v2_upgrade_rolls_back_without_losing_legacy_project(
    tmp_path: Path,
) -> None:
    connection = database_connection(tmp_path / "rollback.sqlite3")
    try:
        connection.execute(
            """
            CREATE TABLE analysis_projects (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                problem_statement TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        now = datetime(2026, 7, 24, tzinfo=UTC).isoformat()
        legacy_id = str(uuid4())
        connection.execute(
            "INSERT INTO analysis_projects VALUES (?, ?, ?, ?, ?, ?)",
            (legacy_id, "legacy", "problem", "draft", now, now),
        )
        connection.execute("CREATE TABLE planning_projects (id TEXT PRIMARY KEY)")
        connection.execute("PRAGMA user_version = 2")
        connection.commit()

        with pytest.raises(Exception) as migration:
            initialize_database(connection)

        assert getattr(migration.value, "code", None) == "schema_mismatch"
        assert read_schema_version(connection) == 2
        assert (
            connection.execute(
                "SELECT id FROM analysis_projects WHERE id = ?", (legacy_id,)
            ).fetchone()[0]
            == legacy_id
        )
    finally:
        connection.close()


def test_completed_version_sqlite_triggers_block_direct_message_and_fact_writes(
    tmp_path: Path,
) -> None:
    connection, _, service = _service(tmp_path / "trigger.sqlite3")
    try:
        project, version = service.create_project("Immutable")
        message = service.append_message(
            project.id,
            version.version_number,
            role="user",
            message_kind="user_input",
            content="Visible only.",
        )
        fact = service.record_unknown_or_missing(
            project.id,
            version.version_number,
            fact_key="retention",
            status="unknown",
            reference_message_ids=[message.id],
        )
        service.complete_version(project.id, version.version_number)

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE visible_conversation_messages SET content = ? WHERE id = ?",
                ("changed", str(message.id)),
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "DELETE FROM project_fact_revisions WHERE id = ?", (str(fact.id),)
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE planning_project_versions SET status = 'draft' WHERE id = ?",
                (str(version.id),),
            )
    finally:
        connection.close()
