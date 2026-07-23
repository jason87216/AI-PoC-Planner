from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from ai_poc_planner.domain.enums import (
    FactStatus,
    InterviewRole,
    ProjectStatus,
    VisibleMessageKind,
)
from ai_poc_planner.domain.project_history import (
    FactRevision,
    PlanningProject,
    ProjectVersion,
    SelectedModelSnapshot,
    VisibleConversationMessage,
)

NOW = datetime(2026, 7, 24, tzinfo=UTC)


def test_project_version_and_safe_model_snapshot_contracts() -> None:
    snapshot = SelectedModelSnapshot(
        profile_id=uuid4(), profile_name="Local model", model_name="qwen"
    )
    project = PlanningProject(
        id=uuid4(), project_name="  Customer support  ", created_at=NOW, updated_at=NOW
    )
    version = ProjectVersion(
        id=uuid4(),
        project_id=project.id,
        version_number=1,
        status=ProjectStatus.DRAFT,
        selected_model=snapshot,
        created_at=NOW,
        updated_at=NOW,
    )

    assert project.project_name == "Customer support"
    assert version.selected_model is not None
    assert "api_key" not in version.model_dump()


@pytest.mark.parametrize(
    ("status", "completed_at"),
    [
        (ProjectStatus.COMPLETE, None),
        (ProjectStatus.DRAFT, NOW),
    ],
)
def test_version_completion_timestamp_invariants(
    status: ProjectStatus, completed_at: datetime | None
) -> None:
    with pytest.raises(ValidationError):
        ProjectVersion(
            id=uuid4(),
            project_id=uuid4(),
            version_number=1,
            status=status,
            created_at=NOW,
            updated_at=NOW,
            completed_at=completed_at,
        )


def test_version_rejects_naive_or_reversed_timestamps() -> None:
    with pytest.raises(ValidationError):
        ProjectVersion(
            id=uuid4(),
            project_id=uuid4(),
            version_number=1,
            status=ProjectStatus.DRAFT,
            created_at=datetime(2026, 7, 24),
            updated_at=NOW,
        )
    with pytest.raises(ValidationError):
        ProjectVersion(
            id=uuid4(),
            project_id=uuid4(),
            version_number=1,
            status=ProjectStatus.COMPLETE,
            created_at=NOW,
            updated_at=NOW,
            completed_at=NOW - timedelta(seconds=1),
        )


def test_visible_message_only_allows_safe_role_kind_pairs() -> None:
    message = VisibleConversationMessage(
        id=uuid4(),
        version_id=uuid4(),
        sequence=1,
        role=InterviewRole.ASSISTANT,
        message_kind=VisibleMessageKind.AI_UNDERSTANDING,
        content="  A visible summary.  ",
        created_at=NOW,
    )
    assert message.content == "A visible summary."

    with pytest.raises(ValidationError):
        VisibleConversationMessage(
            id=uuid4(),
            version_id=uuid4(),
            sequence=1,
            role=InterviewRole.USER,
            message_kind=VisibleMessageKind.QUESTION,
            content="Not allowed",
            created_at=NOW,
        )


@pytest.mark.parametrize(
    ("status", "value"),
    [
        (FactStatus.ASSUMPTION, None),
        (FactStatus.CONFIRMED, None),
        (FactStatus.UNKNOWN, {"not": "allowed"}),
        (FactStatus.MISSING, ["not", "allowed"]),
    ],
)
def test_fact_status_and_value_invariants(status: FactStatus, value: object) -> None:
    with pytest.raises(ValidationError):
        FactRevision(
            id=uuid4(),
            version_id=uuid4(),
            fact_key="owner",
            value=value,
            status=status,
            reference_message_ids=[uuid4()],
            created_at=NOW,
        )


def test_fact_requires_references_and_rejects_internal_provider_fields() -> None:
    with pytest.raises(ValidationError):
        FactRevision(
            id=uuid4(),
            version_id=uuid4(),
            fact_key="owner",
            value="Operations",
            status=FactStatus.ASSUMPTION,
            reference_message_ids=[],
            created_at=NOW,
        )
    with pytest.raises(ValidationError):
        PlanningProject.model_validate(
            {
                "id": str(uuid4()),
                "project_name": "Safe",
                "created_at": NOW.isoformat(),
                "updated_at": NOW.isoformat(),
                "system_prompt": "not durable",
            }
        )
