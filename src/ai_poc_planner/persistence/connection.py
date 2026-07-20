"""Small SQLite connection factory with project-wide safety defaults."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from ai_poc_planner.persistence.errors import DatabaseOperationError


def database_connection(database_path: str | Path) -> sqlite3.Connection:
    """Open one caller-owned SQLite connection.

    The caller controls its lifetime and must close it. Schema initialization is
    deliberately separate, so importing this module never creates a database.
    """
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection
    except sqlite3.Error as error:
        if connection is not None:
            connection.close()
        raise DatabaseOperationError("unable to open the project database") from error
