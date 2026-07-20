"""Public SQLite persistence boundary."""

from ai_poc_planner.persistence.connection import database_connection
from ai_poc_planner.persistence.errors import (
    DatabaseOperationError,
    InvalidPlanningRunInputError,
    InvalidPlanningRunTransitionError,
    InvalidProjectInputError,
    InvalidStoredPlanningRunError,
    InvalidStoredProjectError,
    PersistenceError,
    PlanningRunAlreadyExistsError,
    PlanningRunNotFoundError,
    ProjectAlreadyExistsError,
    ProjectNotFoundError,
    SchemaMismatchError,
    UnsupportedSchemaVersionError,
)
from ai_poc_planner.persistence.planning_runs import SQLitePlanningRunRepository
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
    "InvalidPlanningRunInputError",
    "InvalidPlanningRunTransitionError",
    "InvalidStoredPlanningRunError",
    "InvalidStoredProjectError",
    "PersistenceError",
    "ProjectAlreadyExistsError",
    "PlanningRunAlreadyExistsError",
    "PlanningRunNotFoundError",
    "ProjectNotFoundError",
    "SQLiteProjectRepository",
    "SQLitePlanningRunRepository",
    "SchemaMismatchError",
    "UnsupportedSchemaVersionError",
    "database_connection",
    "initialize_database",
    "read_schema_version",
]
