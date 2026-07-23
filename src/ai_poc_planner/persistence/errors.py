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


class PlanningRunAlreadyExistsError(PersistenceError):
    code = "planning_run_already_exists"


class PlanningRunNotFoundError(PersistenceError):
    code = "planning_run_not_found"


class InvalidPlanningRunInputError(PersistenceError):
    code = "invalid_planning_run_input"


class InvalidStoredPlanningRunError(PersistenceError):
    code = "invalid_stored_planning_run"


class InvalidPlanningRunTransitionError(PersistenceError):
    code = "invalid_planning_run_transition"


class DatabaseOperationError(PersistenceError):
    code = "database_operation_failed"


class SchemaMismatchError(PersistenceError):
    code = "schema_mismatch"


class UnsupportedSchemaVersionError(PersistenceError):
    code = "unsupported_schema_version"


class ProjectVersionNotFoundError(PersistenceError):
    code = "project_version_not_found"


class InvalidProjectVersionTransitionError(PersistenceError):
    code = "invalid_project_version_transition"


class CompletedVersionImmutableError(PersistenceError):
    code = "completed_version_immutable"


class CurrentVersionRequiredError(PersistenceError):
    code = "current_version_required"


class FactNotFoundError(PersistenceError):
    code = "fact_not_found"


class FactNotCurrentError(PersistenceError):
    code = "fact_not_current"


class FactConflictError(PersistenceError):
    code = "fact_conflict"


class FactReferenceInvalidError(PersistenceError):
    code = "fact_reference_invalid"


class FactConfirmationInvalidError(PersistenceError):
    code = "fact_confirmation_invalid"


class FactCorrectionRequiredError(PersistenceError):
    code = "fact_correction_required"


class FactCorrectionInvalidError(PersistenceError):
    code = "fact_correction_invalid"
