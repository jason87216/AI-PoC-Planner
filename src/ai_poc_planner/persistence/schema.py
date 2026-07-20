"""Versioned SQLite schema initialization for the M2.1 project aggregate."""

from __future__ import annotations

import sqlite3

from ai_poc_planner.persistence.errors import (
    DatabaseOperationError,
    SchemaMismatchError,
    UnsupportedSchemaVersionError,
)

CURRENT_SCHEMA_VERSION = 1
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


def _rollback_quietly(connection: sqlite3.Connection) -> None:
    try:
        connection.rollback()
    except sqlite3.Error:
        pass


def initialize_database(connection: sqlite3.Connection) -> None:
    """Create the current M2.1 schema once or verify an initialized database."""
    version = read_schema_version(connection)
    if version not in {0, CURRENT_SCHEMA_VERSION}:
        raise UnsupportedSchemaVersionError(
            "database schema version is not supported by this application"
        )

    if version == CURRENT_SCHEMA_VERSION:
        try:
            _validate_project_table(connection)
        except SchemaMismatchError:
            raise
        except sqlite3.Error as error:
            raise DatabaseOperationError(
                "unable to validate database schema"
            ) from error
        return

    try:
        connection.execute("BEGIN")
        connection.execute(_CREATE_PROJECTS_TABLE)
        _validate_project_table(connection)
        connection.execute(f"PRAGMA user_version = {CURRENT_SCHEMA_VERSION}")
        connection.commit()
    except SchemaMismatchError:
        _rollback_quietly(connection)
        raise
    except sqlite3.Error as error:
        _rollback_quietly(connection)
        raise DatabaseOperationError("unable to initialize database schema") from error
