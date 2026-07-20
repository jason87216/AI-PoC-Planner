"""Stable errors exposed by the SQLite persistence boundary."""


class PersistenceError(RuntimeError):
    """Base class for persistence failures safe for application code to handle."""

    code = "persistence_error"


class ProjectAlreadyExistsError(PersistenceError):
    code = "project_already_exists"


class ProjectNotFoundError(PersistenceError):
    code = "project_not_found"


class InvalidProjectInputError(PersistenceError):
    code = "invalid_project_input"


class InvalidStoredProjectError(PersistenceError):
    code = "invalid_stored_project"


class DatabaseOperationError(PersistenceError):
    code = "database_operation_failed"


class SchemaMismatchError(PersistenceError):
    code = "schema_mismatch"


class UnsupportedSchemaVersionError(PersistenceError):
    code = "unsupported_schema_version"
