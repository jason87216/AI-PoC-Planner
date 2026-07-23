"""Phase 2 contracts for durable project versions and visible evidence."""

from __future__ import annotations

from uuid import UUID

from pydantic import Field, model_validator

from ai_poc_planner.domain.enums import (
    FactStatus,
    InterviewRole,
    ProjectStatus,
    VisibleMessageKind,
)
from ai_poc_planner.domain.models import (
    ContractModel,
    JSONValue,
    NonEmptyStr,
    UtcDateTime,
)


class SelectedModelSnapshot(ContractModel):
    """Safe model identity retained with a version, never provider configuration."""

    profile_id: UUID
    profile_name: NonEmptyStr
    model_name: NonEmptyStr


class PlanningProject(ContractModel):
    """Stable project identity, separate from any mutable planning version."""

    id: UUID
    project_name: NonEmptyStr
    created_at: UtcDateTime
    updated_at: UtcDateTime

    @model_validator(mode="after")
    def timestamps_are_ordered(self) -> PlanningProject:
        if self.updated_at < self.created_at:
            raise ValueError("updated_at must not be earlier than created_at")
        return self


class ProjectVersion(ContractModel):
    """One linear planning version; completed records are immutable in persistence."""

    id: UUID
    project_id: UUID
    version_number: int = Field(ge=1)
    status: ProjectStatus
    based_on_version_id: UUID | None = None
    selected_model: SelectedModelSnapshot | None = None
    created_at: UtcDateTime
    updated_at: UtcDateTime
    completed_at: UtcDateTime | None = None

    @model_validator(mode="after")
    def completion_and_timestamps_are_consistent(self) -> ProjectVersion:
        if self.updated_at < self.created_at:
            raise ValueError("updated_at must not be earlier than created_at")
        if self.status is ProjectStatus.COMPLETE and self.completed_at is None:
            raise ValueError("complete versions require completed_at")
        if self.status is not ProjectStatus.COMPLETE and self.completed_at is not None:
            raise ValueError("only complete versions may have completed_at")
        if self.completed_at is not None and self.completed_at < self.created_at:
            raise ValueError("completed_at must not be earlier than created_at")
        return self


class VisibleConversationMessage(ContractModel):
    """Only content deliberately visible to the user, without hidden model traces."""

    id: UUID
    version_id: UUID
    sequence: int = Field(ge=1)
    role: InterviewRole
    message_kind: VisibleMessageKind
    content: NonEmptyStr
    created_at: UtcDateTime
    copied_from_message_id: UUID | None = None

    @model_validator(mode="after")
    def role_matches_visible_message_kind(self) -> VisibleConversationMessage:
        assistant_kinds = {
            VisibleMessageKind.AI_UNDERSTANDING,
            VisibleMessageKind.QUESTION,
        }
        user_kinds = {
            VisibleMessageKind.USER_INPUT,
            VisibleMessageKind.CONFIRMATION,
            VisibleMessageKind.CORRECTION,
            VisibleMessageKind.ANSWER,
        }
        if (
            self.message_kind in assistant_kinds
            and self.role is not InterviewRole.ASSISTANT
        ):
            raise ValueError("assistant message kinds require the assistant role")
        if self.message_kind in user_kinds and self.role is not InterviewRole.USER:
            raise ValueError("user message kinds require the user role")
        return self


class FactRevision(ContractModel):
    """Append-only fact revision with explicit, visible message evidence."""

    id: UUID
    version_id: UUID
    fact_key: NonEmptyStr
    value: JSONValue
    status: FactStatus
    reference_message_ids: list[UUID] = Field(min_length=1)
    supersedes_fact_id: UUID | None = None
    copied_from_fact_id: UUID | None = None
    correction_reason: NonEmptyStr | None = None
    created_at: UtcDateTime

    @model_validator(mode="after")
    def value_and_reference_invariants(self) -> FactRevision:
        if len(self.reference_message_ids) != len(set(self.reference_message_ids)):
            raise ValueError("reference_message_ids must not contain duplicates")
        if self.status in {FactStatus.ASSUMPTION, FactStatus.CONFIRMED}:
            if self.value is None:
                raise ValueError("assumption and confirmed facts require a value")
        elif self.value is not None:
            raise ValueError("unknown and missing facts require a null value")
        return self


class ProjectHistorySummary(ContractModel):
    """Human-readable project history row for future UI/API consumers."""

    project_id: UUID
    project_name: NonEmptyStr
    version_number: int = Field(ge=1)
    status: ProjectStatus
    created_at: UtcDateTime
    updated_at: UtcDateTime
    completed_at: UtcDateTime | None = None
    profile_name: NonEmptyStr | None = None
    model_name: NonEmptyStr | None = None
