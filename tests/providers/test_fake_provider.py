from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import TypeAdapter

from ai_poc_planner.domain.enums import EvidenceSourceType, ProjectStatus
from ai_poc_planner.domain.models import AnalysisProject, EvidenceReference
from ai_poc_planner.providers.base import (
    ModelProvider,
    PreparationStatus,
    ProviderPreparation,
    ProviderRequest,
)
from ai_poc_planner.providers.fake import (
    FakeEmbeddingProvider,
    FakeModelProvider,
    FakeProviderError,
)

PROJECT_ID = UUID("10000000-0000-0000-0000-000000000001")
SESSION_ID = UUID("20000000-0000-0000-0000-000000000001")
EVIDENCE_ID = UUID("30000000-0000-0000-0000-000000000001")


def _request(*, answers: dict[str, object] | None = None) -> ProviderRequest:
    timestamp = datetime(2026, 7, 19, tzinfo=UTC)
    project = AnalysisProject(
        id=PROJECT_ID,
        title="客服知識檢索 PoC",
        problem_statement="客服需要更快找到已核准的產品答案。",
        status=ProjectStatus.INTERVIEWING,
        created_at=timestamp,
        updated_at=timestamp,
    )
    evidence = EvidenceReference(
        id=EVIDENCE_ID,
        project_id=PROJECT_ID,
        session_id=SESSION_ID,
        source_type=EvidenceSourceType.INTERVIEW,
        source_ref="interview:demo:1",
        label="固定訪談資料",
    )
    return ProviderRequest(
        project=project,
        session_id=SESSION_ID,
        interview_answers=(
            {
                "scenario": "high_value_low_risk",
                "target_users": ["客服人員"],
                "current_workflow": "人工搜尋已核准的產品文件。",
                "data_sources": ["核准產品文件", "代表性問題集"],
                "owner": "客服流程負責人",
            }
            if answers is None
            else answers
        ),
        evidence=[evidence],
    )


def test_fake_provider_satisfies_small_protocol() -> None:
    provider: ModelProvider = FakeModelProvider()

    assert provider.capabilities.structured_output is True
    assert provider.capabilities.tool_calling is False
    assert provider.capabilities.model_identifier == "fake/offline-v1"


def test_fake_provider_is_deterministic_and_structured() -> None:
    provider = FakeModelProvider()
    request = _request()

    first = provider.prepare_assessment(request)
    second = provider.prepare_assessment(request)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.status is PreparationStatus.READY
    assert ProviderPreparation.model_validate(first.model_dump()) == first


def test_provider_response_has_no_final_assessment_decisions() -> None:
    payload = FakeModelProvider().prepare_assessment(_request()).model_dump(mode="json")

    forbidden = {"weighted_score", "recommendation", "gate_disposition", "scores"}
    assert forbidden.isdisjoint(payload)
    assert "facts" in payload
    assert "tool_inputs" in payload


def test_fake_provider_requests_clarification_for_incomplete_interview() -> None:
    result = FakeModelProvider().prepare_assessment(_request(answers={}))

    assert result.status is PreparationStatus.CLARIFICATION_REQUIRED
    assert result.facts is None
    assert result.tool_inputs is None
    assert 1 <= len(result.clarifying_questions) <= 5


def test_fake_provider_supports_fixed_error_scenario() -> None:
    request = _request(answers={"simulate_provider_error": True})

    with pytest.raises(FakeProviderError, match="simulated provider failure"):
        FakeModelProvider().prepare_assessment(request)


def test_fake_provider_reuses_only_supplied_evidence() -> None:
    result = FakeModelProvider().prepare_assessment(_request())

    assert result.facts is not None
    fact_ids = {
        evidence_id
        for value in result.facts.__dict__.values()
        if hasattr(value, "evidence_ids")
        for evidence_id in value.evidence_ids
    }
    assert fact_ids == {EVIDENCE_ID}


def test_fake_embeddings_are_deterministic_and_typed() -> None:
    provider = FakeEmbeddingProvider()

    first = provider.embed(["alpha", "beta"])
    second = provider.embed(["alpha", "beta"])

    assert first == second
    assert len(first) == 2
    assert all(len(vector) == provider.dimensions for vector in first)
    TypeAdapter(list[list[float]]).validate_python(first)


def test_fake_providers_do_not_need_network_or_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    monkeypatch.delenv("EMBEDDING_API_KEY", raising=False)

    def fail_network(*args: object, **kwargs: object) -> None:
        raise AssertionError("fake providers must remain offline")

    monkeypatch.setattr("socket.create_connection", fail_network)

    assert FakeModelProvider().prepare_assessment(_request()).facts is not None
    assert FakeEmbeddingProvider().embed(["offline"])
