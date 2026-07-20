"""Small, explicit SQLite schema initialization and v1-to-v2 migration."""

from __future__ import annotations

import sqlite3

from ai_poc_planner.persistence.errors import (
    DatabaseOperationError,
    SchemaMismatchError,
    UnsupportedSchemaVersionError,
)

CURRENT_SCHEMA_VERSION = 2
_PROJECT_COLUMNS = frozenset(
    {
        "id",
        "title",
        "problem_statement",
        "status",
        "created_at",
        "updated_at",
    }
)
_CREATE_PROJECTS_TABLE = """
CREATE TABLE IF NOT EXISTS analysis_projects (
    id TEXT PRIMARY KEY NOT NULL,
    title TEXT NOT NULL,
    problem_statement TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""
_PLANNING_RUN_COLUMNS = frozenset(
    {
        "id",
        "project_id",
        "status",
        "original_request",
        "intent_json",
        "known_information_json",
        "missing_information_json",
        "clarifying_questions_json",
        "clarification_answers_json",
        "assessment_json",
        "proposal_json",
        "markdown_report",
        "error_code",
        "error_message",
        "created_at",
        "updated_at",
        "completed_at",
    }
)
_CREATE_PLANNING_RUNS_TABLE = """
CREATE TABLE IF NOT EXISTS planning_runs (
    id TEXT PRIMARY KEY NOT NULL,
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
_CREATE_PLANNING_RUNS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_planning_runs_project_created
ON planning_runs (project_id, created_at DESC, id DESC)
"""


def read_schema_version(connection: sqlite3.Connection) -> int:
    """Return SQLite's application-controlled schema version."""
    try:
        row = connection.execute("PRAGMA user_version").fetchone()
    except sqlite3.Error as error:
        raise DatabaseOperationError(
            "unable to read database schema version"
        ) from error
    if row is None:
        raise SchemaMismatchError("database schema version is unavailable")
    return int(row[0])


def _validate_project_table(connection: sqlite3.Connection) -> None:
    columns = {
        row[1] for row in connection.execute("PRAGMA table_info(analysis_projects)")
    }
    if not _PROJECT_COLUMNS <= columns:
        raise SchemaMismatchError(
            "analysis project table is missing required schema fields"
        )


def _validate_planning_run_table(connection: sqlite3.Connection) -> None:
    columns = {row[1] for row in connection.execute("PRAGMA table_info(planning_runs)")}
    if not _PLANNING_RUN_COLUMNS <= columns:
        raise SchemaMismatchError(
            "planning run table is missing required schema fields"
        )
    foreign_keys = connection.execute(
        "PRAGMA foreign_key_list(planning_runs)"
    ).fetchall()
    project_key_exists = any(
        row[2] == "analysis_projects" and row[3] == "project_id" and row[4] == "id"
        for row in foreign_keys
    )
    if not project_key_exists:
        raise SchemaMismatchError(
            "planning run table is missing the analysis project foreign key"
        )


def _validate_current_schema(connection: sqlite3.Connection) -> None:
    _validate_project_table(connection)
    _validate_planning_run_table(connection)


def _rollback_quietly(connection: sqlite3.Connection) -> None:
    try:
        connection.rollback()
    except sqlite3.Error:
        pass


def initialize_database(connection: sqlite3.Connection) -> None:
    """Create schema v2 or upgrade the sole supported prior version, v1."""
    version = read_schema_version(connection)
    if version not in {0, 1, CURRENT_SCHEMA_VERSION}:
        raise UnsupportedSchemaVersionError(
            "database schema version is not supported by this application"
        )

    if version == CURRENT_SCHEMA_VERSION:
        try:
            _validate_current_schema(connection)
        except SchemaMismatchError:
            raise
        except sqlite3.Error as error:
            raise DatabaseOperationError(
                "unable to validate database schema"
            ) from error
        return

    try:
        connection.execute("BEGIN")
        if version == 0:
            connection.execute(_CREATE_PROJECTS_TABLE)
        _validate_project_table(connection)
        connection.execute(_CREATE_PLANNING_RUNS_TABLE)
        connection.execute(_CREATE_PLANNING_RUNS_INDEX)
        _validate_planning_run_table(connection)
        connection.execute(f"PRAGMA user_version = {CURRENT_SCHEMA_VERSION}")
        connection.commit()
    except SchemaMismatchError:
        _rollback_quietly(connection)
        raise
    except sqlite3.Error as error:
        _rollback_quietly(connection)
        raise DatabaseOperationError("unable to initialize database schema") from error
