"""Explicit SQLite schema initialization with additive legacy-safe migrations."""

from __future__ import annotations

import sqlite3

from ai_poc_planner.persistence.errors import (
    DatabaseOperationError,
    SchemaMismatchError,
    UnsupportedSchemaVersionError,
)

CURRENT_SCHEMA_VERSION = 3
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
_PLANNING_PROJECT_COLUMNS = frozenset(
    {"id", "project_name", "created_at", "updated_at"}
)
_PROJECT_VERSION_COLUMNS = frozenset(
    {
        "id",
        "project_id",
        "version_number",
        "status",
        "based_on_version_id",
        "profile_id",
        "profile_name",
        "model_name",
        "created_at",
        "updated_at",
        "completed_at",
    }
)
_MESSAGE_COLUMNS = frozenset(
    {
        "id",
        "version_id",
        "sequence",
        "role",
        "message_kind",
        "content",
        "created_at",
        "copied_from_message_id",
    }
)
_FACT_COLUMNS = frozenset(
    {
        "id",
        "version_id",
        "fact_key",
        "normalized_fact_key",
        "value_json",
        "status",
        "supersedes_fact_id",
        "copied_from_fact_id",
        "correction_reason",
        "created_at",
    }
)
_FACT_REFERENCE_COLUMNS = frozenset({"fact_id", "message_id"})
_CREATE_PLANNING_PROJECTS_TABLE = """
CREATE TABLE IF NOT EXISTS planning_projects (
    id TEXT PRIMARY KEY NOT NULL,
    project_name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""
_CREATE_PROJECT_VERSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS planning_project_versions (
    id TEXT PRIMARY KEY NOT NULL,
    project_id TEXT NOT NULL REFERENCES planning_projects(id),
    version_number INTEGER NOT NULL CHECK (version_number >= 1),
    status TEXT NOT NULL,
    based_on_version_id TEXT REFERENCES planning_project_versions(id),
    profile_id TEXT,
    profile_name TEXT,
    model_name TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT,
    UNIQUE (project_id, version_number),
    CHECK (
        (profile_id IS NULL AND profile_name IS NULL AND model_name IS NULL)
        OR (
            profile_id IS NOT NULL
            AND profile_name IS NOT NULL
            AND model_name IS NOT NULL
        )
    )
)
"""
_CREATE_VISIBLE_MESSAGES_TABLE = """
CREATE TABLE IF NOT EXISTS visible_conversation_messages (
    id TEXT PRIMARY KEY NOT NULL,
    version_id TEXT NOT NULL REFERENCES planning_project_versions(id),
    sequence INTEGER NOT NULL CHECK (sequence >= 1),
    role TEXT NOT NULL,
    message_kind TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    copied_from_message_id TEXT REFERENCES visible_conversation_messages(id),
    UNIQUE (version_id, sequence)
)
"""
_CREATE_FACT_REVISIONS_TABLE = """
CREATE TABLE IF NOT EXISTS project_fact_revisions (
    id TEXT PRIMARY KEY NOT NULL,
    version_id TEXT NOT NULL REFERENCES planning_project_versions(id),
    fact_key TEXT NOT NULL,
    normalized_fact_key TEXT NOT NULL,
    value_json TEXT,
    status TEXT NOT NULL,
    supersedes_fact_id TEXT REFERENCES project_fact_revisions(id),
    copied_from_fact_id TEXT REFERENCES project_fact_revisions(id),
    correction_reason TEXT,
    created_at TEXT NOT NULL
)
"""
_CREATE_FACT_REFERENCES_TABLE = """
CREATE TABLE IF NOT EXISTS fact_message_references (
    fact_id TEXT NOT NULL REFERENCES project_fact_revisions(id) ON DELETE CASCADE,
    message_id TEXT NOT NULL REFERENCES visible_conversation_messages(id),
    PRIMARY KEY (fact_id, message_id)
)
"""
_CREATE_PROJECT_HISTORY_INDEX = """
CREATE INDEX IF NOT EXISTS idx_planning_projects_updated
ON planning_projects (updated_at DESC, id DESC)
"""
_CREATE_VERSION_HISTORY_INDEX = """
CREATE INDEX IF NOT EXISTS idx_project_versions_history
ON planning_project_versions (project_id, version_number DESC)
"""
_CREATE_MESSAGE_ORDER_INDEX = """
CREATE INDEX IF NOT EXISTS idx_visible_messages_order
ON visible_conversation_messages (version_id, sequence)
"""
_CREATE_FACT_CURRENT_INDEX = """
CREATE INDEX IF NOT EXISTS idx_fact_revisions_current
ON project_fact_revisions (version_id, normalized_fact_key, supersedes_fact_id)
"""
_CREATE_FACT_REFERENCE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_fact_references_message
ON fact_message_references (message_id, fact_id)
"""
_CREATE_COMPLETED_VERSION_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS prevent_completed_version_update
BEFORE UPDATE ON planning_project_versions
WHEN OLD.status = 'complete'
BEGIN
    SELECT RAISE(ABORT, 'completed version is immutable');
END
"""
_CREATE_COMPLETED_VERSION_DELETE_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS prevent_completed_version_delete
BEFORE DELETE ON planning_project_versions
WHEN OLD.status = 'complete'
BEGIN
    SELECT RAISE(ABORT, 'completed version is immutable');
END
"""
_CREATE_COMPLETED_MESSAGE_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS prevent_completed_version_message_write
BEFORE INSERT ON visible_conversation_messages
WHEN (
    SELECT status FROM planning_project_versions WHERE id = NEW.version_id
) = 'complete'
BEGIN
    SELECT RAISE(ABORT, 'completed version is immutable');
END
"""
_CREATE_COMPLETED_MESSAGE_UPDATE_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS prevent_completed_version_message_update
BEFORE UPDATE ON visible_conversation_messages
WHEN (
    SELECT status FROM planning_project_versions WHERE id = OLD.version_id
) = 'complete'
BEGIN
    SELECT RAISE(ABORT, 'completed version is immutable');
END
"""
_CREATE_COMPLETED_MESSAGE_DELETE_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS prevent_completed_version_message_delete
BEFORE DELETE ON visible_conversation_messages
WHEN (
    SELECT status FROM planning_project_versions WHERE id = OLD.version_id
) = 'complete'
BEGIN
    SELECT RAISE(ABORT, 'completed version is immutable');
END
"""
_CREATE_COMPLETED_FACT_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS prevent_completed_version_fact_write
BEFORE INSERT ON project_fact_revisions
WHEN (
    SELECT status FROM planning_project_versions WHERE id = NEW.version_id
) = 'complete'
BEGIN
    SELECT RAISE(ABORT, 'completed version is immutable');
END
"""
_CREATE_COMPLETED_FACT_UPDATE_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS prevent_completed_version_fact_update
BEFORE UPDATE ON project_fact_revisions
WHEN (
    SELECT status FROM planning_project_versions WHERE id = OLD.version_id
) = 'complete'
BEGIN
    SELECT RAISE(ABORT, 'completed version is immutable');
END
"""
_CREATE_COMPLETED_FACT_DELETE_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS prevent_completed_version_fact_delete
BEFORE DELETE ON project_fact_revisions
WHEN (
    SELECT status FROM planning_project_versions WHERE id = OLD.version_id
) = 'complete'
BEGIN
    SELECT RAISE(ABORT, 'completed version is immutable');
END
"""
_CREATE_COMPLETED_FACT_REFERENCE_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS prevent_completed_version_fact_reference_write
BEFORE INSERT ON fact_message_references
WHEN (
    SELECT v.status
    FROM project_fact_revisions f
    JOIN planning_project_versions v ON v.id = f.version_id
    WHERE f.id = NEW.fact_id
) = 'complete'
BEGIN
    SELECT RAISE(ABORT, 'completed version is immutable');
END
"""
_CREATE_COMPLETED_FACT_REFERENCE_UPDATE_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS prevent_completed_version_fact_reference_update
BEFORE UPDATE ON fact_message_references
WHEN (
    SELECT v.status
    FROM project_fact_revisions f
    JOIN planning_project_versions v ON v.id = f.version_id
    WHERE f.id = OLD.fact_id
) = 'complete'
BEGIN
    SELECT RAISE(ABORT, 'completed version is immutable');
END
"""
_CREATE_COMPLETED_FACT_REFERENCE_DELETE_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS prevent_completed_version_fact_reference_delete
BEFORE DELETE ON fact_message_references
WHEN (
    SELECT v.status
    FROM project_fact_revisions f
    JOIN planning_project_versions v ON v.id = f.version_id
    WHERE f.id = OLD.fact_id
) = 'complete'
BEGIN
    SELECT RAISE(ABORT, 'completed version is immutable');
END
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
    _validate_phase_two_tables(connection)


def _validate_columns(
    connection: sqlite3.Connection,
    table: str,
    required_columns: frozenset[str],
) -> None:
    columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
    if not required_columns <= columns:
        raise SchemaMismatchError(f"{table} is missing required schema fields")


def _validate_phase_two_tables(connection: sqlite3.Connection) -> None:
    _validate_columns(connection, "planning_projects", _PLANNING_PROJECT_COLUMNS)
    _validate_columns(
        connection,
        "planning_project_versions",
        _PROJECT_VERSION_COLUMNS,
    )
    _validate_columns(connection, "visible_conversation_messages", _MESSAGE_COLUMNS)
    _validate_columns(connection, "project_fact_revisions", _FACT_COLUMNS)
    _validate_columns(connection, "fact_message_references", _FACT_REFERENCE_COLUMNS)


def _create_phase_two_schema(connection: sqlite3.Connection) -> None:
    for statement in (
        _CREATE_PLANNING_PROJECTS_TABLE,
        _CREATE_PROJECT_VERSIONS_TABLE,
        _CREATE_VISIBLE_MESSAGES_TABLE,
        _CREATE_FACT_REVISIONS_TABLE,
        _CREATE_FACT_REFERENCES_TABLE,
        _CREATE_PROJECT_HISTORY_INDEX,
        _CREATE_VERSION_HISTORY_INDEX,
        _CREATE_MESSAGE_ORDER_INDEX,
        _CREATE_FACT_CURRENT_INDEX,
        _CREATE_FACT_REFERENCE_INDEX,
        _CREATE_COMPLETED_VERSION_TRIGGER,
        _CREATE_COMPLETED_VERSION_DELETE_TRIGGER,
        _CREATE_COMPLETED_MESSAGE_TRIGGER,
        _CREATE_COMPLETED_MESSAGE_UPDATE_TRIGGER,
        _CREATE_COMPLETED_MESSAGE_DELETE_TRIGGER,
        _CREATE_COMPLETED_FACT_TRIGGER,
        _CREATE_COMPLETED_FACT_UPDATE_TRIGGER,
        _CREATE_COMPLETED_FACT_DELETE_TRIGGER,
        _CREATE_COMPLETED_FACT_REFERENCE_TRIGGER,
        _CREATE_COMPLETED_FACT_REFERENCE_UPDATE_TRIGGER,
        _CREATE_COMPLETED_FACT_REFERENCE_DELETE_TRIGGER,
    ):
        connection.execute(statement)


def _phase_two_table_count(connection: sqlite3.Connection) -> int:
    names = {
        "planning_projects",
        "planning_project_versions",
        "visible_conversation_messages",
        "project_fact_revisions",
        "fact_message_references",
    }
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    return sum(row[0] in names for row in rows)


def _rollback_quietly(connection: sqlite3.Connection) -> None:
    try:
        connection.rollback()
    except sqlite3.Error:
        pass


def initialize_database(connection: sqlite3.Connection) -> None:
    """Create schema v3 or additively upgrade supported v1/v2 legacy databases."""
    version = read_schema_version(connection)
    if version not in {0, 1, 2, CURRENT_SCHEMA_VERSION}:
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
        if _phase_two_table_count(connection):
            _validate_phase_two_tables(connection)
        _create_phase_two_schema(connection)
        _validate_phase_two_tables(connection)
        connection.execute(f"PRAGMA user_version = {CURRENT_SCHEMA_VERSION}")
        connection.commit()
    except SchemaMismatchError:
        _rollback_quietly(connection)
        raise
    except sqlite3.Error as error:
        _rollback_quietly(connection)
        raise DatabaseOperationError("unable to initialize database schema") from error
