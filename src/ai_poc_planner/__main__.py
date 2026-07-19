"""Minimal offline smoke command; this is intentionally not a product CLI."""

from datetime import UTC, datetime
from uuid import UUID

from ai_poc_planner.domain.enums import ProjectStatus
from ai_poc_planner.domain.models import AnalysisProject
from ai_poc_planner.providers.base import ProviderRequest
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
    proposal = FakeModelProvider().generate(ProviderRequest(project=project))
    print(
        "fake-provider: ok "
        f"schema={proposal.schema_version} score={proposal.weighted_score}"
    )


if __name__ == "__main__":
    main()
