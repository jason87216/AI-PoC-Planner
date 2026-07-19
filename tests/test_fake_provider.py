from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from ai_poc_planner.domain.enums import ProjectStatus
from ai_poc_planner.domain.models import AnalysisProject, PocProposal
from ai_poc_planner.providers.base import ProviderRequest
from ai_poc_planner.providers.fake import FakeModelProvider, FakeProviderError


def _project(title: str = "客服知識檢索 PoC") -> AnalysisProject:
    now = datetime.now(UTC)
    return AnalysisProject(
        id=uuid4(),
        title=title,
        problem_statement="客服需要更快找到已核准的產品答案。",
        status=ProjectStatus.DRAFT,
        created_at=now,
        updated_at=now,
    )


def test_fake_provider_needs_no_network_or_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MODEL_API_KEY", raising=False)

    def fail_if_network_is_used(*args: object, **kwargs: object) -> None:
        raise AssertionError("fake provider must not access the network")

    monkeypatch.setattr("socket.create_connection", fail_if_network_is_used)

    proposal = FakeModelProvider().generate(ProviderRequest(project=_project()))

    assert proposal.schema_version == "1.0"


def test_fake_provider_returns_same_result_for_same_input() -> None:
    request = ProviderRequest(project=_project())
    provider = FakeModelProvider()

    first = provider.generate(request)
    second = provider.generate(request)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_fake_provider_output_passes_pydantic_contract() -> None:
    output = FakeModelProvider().generate(ProviderRequest(project=_project()))

    validated = PocProposal.model_validate(output.model_dump())

    assert validated.weighted_score == 73
    assert len(validated.scores) == 6


def test_fake_provider_can_simulate_provider_error() -> None:
    request = ProviderRequest(
        project=_project(title=FakeModelProvider.ERROR_TRIGGER_TITLE)
    )

    with pytest.raises(FakeProviderError, match="simulated provider failure"):
        FakeModelProvider().generate(request)


def test_assistive_only_proposal_requires_human_review_point() -> None:
    proposal = FakeModelProvider().generate(ProviderRequest(project=_project()))
    payload = proposal.model_dump(mode="json")
    payload["recommendation"] = "條件式建議"
    payload["gate_disposition"] = "assistive_only"
    payload["hard_gates"] = [
        {
            "rule_id": "HG-03",
            "disposition": "assistive_only",
            "reason": "高影響用途必須保留人工最終決策。",
            "required_controls": ["人工覆核"],
            "human_review_required": True,
        }
    ]
    payload["human_review_points"] = []

    with pytest.raises(ValidationError, match="at least one human review point"):
        PocProposal.model_validate(payload)
