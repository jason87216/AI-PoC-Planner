"""Application rules for linear project versions and append-only visible facts."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from uuid import UUID, uuid4

from ai_poc_planner.domain.enums import FactStatus, InterviewRole, ProjectStatus
from ai_poc_planner.domain.project_history import (
    FactRevision,
    PlanningProject,
    ProjectVersion,
    SelectedModelSnapshot,
    VisibleConversationMessage,
)
from ai_poc_planner.persistence.errors import (
    CompletedVersionImmutableError,
    CurrentVersionRequiredError,
    FactConfirmationInvalidError,
    FactConflictError,
    FactCorrectionInvalidError,
    FactCorrectionRequiredError,
    FactNotCurrentError,
    FactReferenceInvalidError,
    InvalidProjectVersionTransitionError,
    InvalidVisibleMessageError,
)
from ai_poc_planner.persistence.project_history import (
    SQLiteProjectHistoryRepository,
    normalize_fact_key,
)
from ai_poc_planner.providers.profiles import ModelProfile


def _utc_now() -> datetime:
    return datetime.now(UTC)


class ProjectHistoryService:
    """Apply product rules before delegating durable writes to SQLite."""

    def __init__(
        self,
        repository: SQLiteProjectHistoryRepository,
        *,
        selected_profile_getter: Callable[[], ModelProfile | None] | None = None,
        uuid_factory: Callable[[], UUID] = uuid4,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._repository = repository
        self._selected_profile_getter = selected_profile_getter
        self._uuid_factory = uuid_factory
        self._clock = clock

    def create_project(
        self, project_name: str
    ) -> tuple[PlanningProject, ProjectVersion]:
        timestamp = self._clock()
        project = PlanningProject(
            id=self._uuid_factory(),
            project_name=project_name,
            created_at=timestamp,
            updated_at=timestamp,
        )
        version = ProjectVersion(
            id=self._uuid_factory(),
            project_id=project.id,
            version_number=1,
            status=ProjectStatus.DRAFT,
            selected_model=self._selected_snapshot(),
            created_at=timestamp,
            updated_at=timestamp,
        )
        return self._repository.create_project_with_version(project, version)

    def list_projects(self):
        """Return human-readable latest-version summaries without provider secrets."""

        return self._repository.list_summaries()

    def get_project(self, project_id: UUID) -> PlanningProject:
        return self._repository.get_project(project_id)

    def list_versions(self, project_id: UUID) -> list[ProjectVersion]:
        return self._repository.list_versions(project_id)

    def get_version(self, project_id: UUID, version_number: int) -> ProjectVersion:
        return self._repository.get_version(project_id, version_number)

    def complete_version(self, project_id: UUID, version_number: int) -> ProjectVersion:
        version = self._require_latest(project_id, version_number)
        if version.status is ProjectStatus.COMPLETE:
            raise CompletedVersionImmutableError("completed versions cannot be changed")
        timestamp = self._clock()
        completed_payload = version.model_dump()
        completed_payload.update(
            status=ProjectStatus.COMPLETE,
            updated_at=timestamp,
            completed_at=timestamp,
        )
        completed = ProjectVersion(
            **completed_payload,
        )
        return self._repository.complete_version(completed, timestamp)

    def create_next_version(
        self, project_id: UUID, version_number: int
    ) -> ProjectVersion:
        source = self._require_latest(project_id, version_number)
        if source.status is not ProjectStatus.COMPLETE:
            raise InvalidProjectVersionTransitionError(
                "only a completed latest version can create a successor"
            )
        timestamp = self._clock()
        successor = ProjectVersion(
            id=self._uuid_factory(),
            project_id=project_id,
            version_number=source.version_number + 1,
            status=ProjectStatus.DRAFT,
            based_on_version_id=source.id,
            selected_model=self._selected_snapshot() or source.selected_model,
            created_at=timestamp,
            updated_at=timestamp,
        )
        return self._repository.create_successor(source, successor, timestamp)

    def append_message(
        self,
        project_id: UUID,
        version_number: int,
        *,
        role: InterviewRole,
        message_kind: str,
        content: str,
    ) -> VisibleConversationMessage:
        version = self._require_mutable_latest(project_id, version_number)
        timestamp = self._clock()
        message_id = self._uuid_factory()
        try:
            VisibleConversationMessage(
                id=message_id,
                version_id=version.id,
                sequence=1,
                role=role,
                message_kind=message_kind,
                content=content,
                created_at=timestamp,
            )
        except Exception as error:
            raise InvalidVisibleMessageError(
                "visible message input is invalid"
            ) from error
        return self._repository.append_message(
            version_id=version.id,
            role=role,
            message_kind=message_kind,
            content=content,
            created_at=timestamp,
            message_id=message_id,
            project_updated_at=timestamp,
        )

    def list_messages(
        self, project_id: UUID, version_number: int
    ) -> list[VisibleConversationMessage]:
        return self._repository.list_messages(
            self._repository.get_version(project_id, version_number).id
        )

    def propose_assumption(
        self,
        project_id: UUID,
        version_number: int,
        *,
        fact_key: str,
        value: object,
        reference_message_ids: Sequence[UUID],
    ) -> FactRevision:
        version = self._require_mutable_latest(project_id, version_number)
        self._ensure_new_fact_key(version.id, fact_key)
        self._validate_references(
            version.id,
            reference_message_ids,
            required_role=InterviewRole.ASSISTANT,
        )
        return self._write_fact(
            version.id,
            fact_key=fact_key,
            value=value,
            status=FactStatus.ASSUMPTION,
            reference_message_ids=reference_message_ids,
        )

    def record_unknown_or_missing(
        self,
        project_id: UUID,
        version_number: int,
        *,
        fact_key: str,
        status: FactStatus,
        reference_message_ids: Sequence[UUID],
    ) -> FactRevision:
        if status not in {FactStatus.UNKNOWN, FactStatus.MISSING}:
            raise FactCorrectionInvalidError("only unknown or missing can be recorded")
        version = self._require_mutable_latest(project_id, version_number)
        self._ensure_new_fact_key(version.id, fact_key)
        self._validate_references(version.id, reference_message_ids)
        return self._write_fact(
            version.id,
            fact_key=fact_key,
            value=None,
            status=status,
            reference_message_ids=reference_message_ids,
        )

    def confirm_assumption(
        self,
        project_id: UUID,
        version_number: int,
        fact_id: UUID,
        *,
        reference_message_ids: Sequence[UUID],
    ) -> FactRevision:
        version = self._require_mutable_latest(project_id, version_number)
        target = self._require_current_fact(version.id, fact_id)
        if target.status is not FactStatus.ASSUMPTION:
            raise FactConfirmationInvalidError(
                "only a current assumption can be confirmed"
            )
        self._validate_references(
            version.id,
            reference_message_ids,
            required_role=InterviewRole.USER,
            allowed_kinds={"confirmation", "answer", "user_input"},
        )
        return self._write_fact(
            version.id,
            fact_key=target.fact_key,
            value=target.value,
            status=FactStatus.CONFIRMED,
            reference_message_ids=reference_message_ids,
            supersedes_fact_id=target.id,
        )

    def correct_fact(
        self,
        project_id: UUID,
        version_number: int,
        fact_id: UUID,
        *,
        status: FactStatus,
        value: object,
        correction_reason: str,
        reference_message_ids: Sequence[UUID],
    ) -> FactRevision:
        if status is FactStatus.ASSUMPTION:
            raise FactCorrectionInvalidError("correction cannot create an assumption")
        if not correction_reason or not correction_reason.strip():
            raise FactCorrectionInvalidError("correction requires a reason")
        version = self._require_mutable_latest(project_id, version_number)
        target = self._require_current_fact(version.id, fact_id)
        self._validate_references(
            version.id,
            reference_message_ids,
            required_role=InterviewRole.USER,
            allowed_kinds={"correction"},
        )
        return self._write_fact(
            version.id,
            fact_key=target.fact_key,
            value=value,
            status=status,
            reference_message_ids=reference_message_ids,
            supersedes_fact_id=target.id,
            correction_reason=correction_reason,
        )

    def list_current_facts(
        self, project_id: UUID, version_number: int
    ) -> list[FactRevision]:
        version = self._repository.get_version(project_id, version_number)
        return self._repository.list_current_facts(version.id)

    def list_fact_history(
        self, project_id: UUID, version_number: int
    ) -> list[FactRevision]:
        version = self._repository.get_version(project_id, version_number)
        return self._repository.list_fact_history(version.id)

    def _write_fact(
        self,
        version_id: UUID,
        *,
        fact_key: str,
        value: object,
        status: FactStatus,
        reference_message_ids: Sequence[UUID],
        supersedes_fact_id: UUID | None = None,
        correction_reason: str | None = None,
    ) -> FactRevision:
        timestamp = self._clock()
        try:
            fact = FactRevision(
                id=self._uuid_factory(),
                version_id=version_id,
                fact_key=fact_key,
                value=value,
                status=status,
                reference_message_ids=list(reference_message_ids),
                supersedes_fact_id=supersedes_fact_id,
                correction_reason=correction_reason,
                created_at=timestamp,
            )
        except Exception as error:
            raise FactCorrectionInvalidError("fact input is invalid") from error
        return self._repository.create_fact(fact, project_updated_at=timestamp)

    def _require_latest(self, project_id: UUID, version_number: int) -> ProjectVersion:
        version = self._repository.get_version(project_id, version_number)
        latest = self._repository.get_latest_version(project_id)
        if version.id != latest.id:
            raise CurrentVersionRequiredError(
                "only the latest version may change state"
            )
        return version

    def _require_mutable_latest(
        self, project_id: UUID, version_number: int
    ) -> ProjectVersion:
        version = self._require_latest(project_id, version_number)
        if version.status is ProjectStatus.COMPLETE:
            raise CompletedVersionImmutableError(
                "completed versions cannot be modified"
            )
        return version

    def _ensure_new_fact_key(self, version_id: UUID, fact_key: str) -> None:
        normalized = normalize_fact_key(fact_key)
        for fact in self._repository.list_current_facts(version_id):
            if normalize_fact_key(fact.fact_key) == normalized:
                if fact.status is FactStatus.CONFIRMED:
                    raise FactCorrectionRequiredError(
                        "confirmed facts require an explicit correction"
                    )
                raise FactConflictError("a current fact already uses this key")

    def _require_current_fact(self, version_id: UUID, fact_id: UUID) -> FactRevision:
        target = self._repository.get_fact(fact_id)
        if target.version_id != version_id:
            raise FactNotCurrentError("fact is not current for this version")
        current_ids = {
            fact.id for fact in self._repository.list_current_facts(version_id)
        }
        if target.id not in current_ids:
            raise FactNotCurrentError("fact revision is superseded")
        return target

    def _validate_references(
        self,
        version_id: UUID,
        reference_message_ids: Sequence[UUID],
        *,
        required_role: InterviewRole | None = None,
        allowed_kinds: set[str] | None = None,
    ) -> None:
        if not reference_message_ids:
            raise FactReferenceInvalidError("facts require visible message references")
        messages: list[VisibleConversationMessage] = []
        try:
            messages = [
                self._repository.get_message(item) for item in reference_message_ids
            ]
        except Exception as error:
            raise FactReferenceInvalidError("fact reference is not visible") from error
        if any(message.version_id != version_id for message in messages):
            raise FactReferenceInvalidError(
                "fact references must belong to this version"
            )
        if required_role is not None and not any(
            message.role is required_role for message in messages
        ):
            if required_role is InterviewRole.USER:
                raise FactConfirmationInvalidError("user evidence is required")
            raise FactReferenceInvalidError("assistant evidence is required")
        if allowed_kinds is not None and not any(
            message.message_kind.value in allowed_kinds
            and (required_role is None or message.role is required_role)
            for message in messages
        ):
            if "correction" in allowed_kinds:
                raise FactCorrectionInvalidError(
                    "a user correction message is required"
                )
            raise FactConfirmationInvalidError(
                "valid user confirmation evidence is required"
            )

    def _selected_snapshot(self) -> SelectedModelSnapshot | None:
        if self._selected_profile_getter is None:
            return None
        profile = self._selected_profile_getter()
        if profile is None:
            return None
        return SelectedModelSnapshot(
            profile_id=profile.id,
            profile_name=profile.profile_name,
            model_name=profile.model_name,
        )
