"""Public SQLite persistence boundary."""

from ai_poc_planner.persistence.connection import database_connection
from ai_poc_planner.persistence.errors import (
    DatabaseOperationError,
    InvalidProjectInputError,
    InvalidStoredProjectError,
    PersistenceError,
    ProjectAlreadyExistsError,
    ProjectNotFoundError,
    SchemaMismatchError,
    UnsupportedSchemaVersionError,
)
from ai_poc_planner.persistence.projects import SQLiteProjectRepository
from ai_poc_planner.persistence.schema import (
    CURRENT_SCHEMA_VERSION,
    initialize_database,
    read_schema_version,
)

__all__ = [
    "CURRENT_SCHEMA_VERSION",
    "DatabaseOperationError",
    "InvalidProjectInputError",
    "InvalidStoredProjectError",
    "PersistenceError",
    "ProjectAlreadyExistsError",
    "ProjectNotFoundError",
    "SQLiteProjectRepository",
    "SchemaMismatchError",
    "UnsupportedSchemaVersionError",
    "database_connection",
    "initialize_database",
    "read_schema_version",
]
