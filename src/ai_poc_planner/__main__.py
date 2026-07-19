"""Minimal offline provider smoke command; product CLI arrives later."""

from datetime import UTC, datetime
from uuid import UUID

from ai_poc_planner.domain.enums import EvidenceSourceType, ProjectStatus
from ai_poc_planner.domain.models import AnalysisProject, EvidenceReference
from ai_poc_planner.providers.base import PreparationStatus, ProviderRequest
from ai_poc_planner.providers.fake import FakeModelProvider


def main() -> None:
    timestamp = datetime(2026, 7, 19, tzinfo=UTC)
    project = AnalysisProject(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        title="Offline smoke project",
        problem_statement="Verify package import and structured fake output.",
        status=ProjectStatus.DRAFT,
        created_at=timestamp,
        updated_at=timestamp,
    )
    session_id = UUID("00000000-0000-0000-0000-000000000002")
    preparation = FakeModelProvider().prepare_assessment(
        ProviderRequest(
            project=project,
            session_id=session_id,
            interview_answers={
                "scenario": "high_value_low_risk",
                "target_users": ["客服人員"],
                "current_workflow": "人工搜尋已核准的產品文件。",
                "data_sources": ["核准產品文件", "代表性問題集"],
                "owner": "客服流程負責人",
            },
            evidence=[
                EvidenceReference(
                    id=UUID("00000000-0000-0000-0000-000000000003"),
                    project_id=project.id,
                    session_id=session_id,
                    source_type=EvidenceSourceType.INTERVIEW,
                    source_ref="interview:smoke:1",
                    label="固定 smoke 訪談",
                )
            ],
        )
    )
    assert preparation.status is PreparationStatus.READY
    print(f"fake-provider: ready schema={preparation.schema_version}")


if __name__ == "__main__":
    main()
