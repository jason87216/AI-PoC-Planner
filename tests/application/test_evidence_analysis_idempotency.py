from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from ai_poc_planner.application.evidence_analysis import (
    EvidenceAnalysisError,
    EvidenceAnalysisService,
)
from ai_poc_planner.application.project_history import ProjectHistoryService
from ai_poc_planner.domain.case_centered import RecommendationCategory
from ai_poc_planner.domain.project_history import SelectedModelSnapshot
from ai_poc_planner.persistence.analysis import SQLiteAnalysisRepository
from ai_poc_planner.persistence.connection import database_connection
from ai_poc_planner.persistence.discovery import SQLiteDiscoveryRepository
from ai_poc_planner.persistence.project_history import SQLiteProjectHistoryRepository
from ai_poc_planner.persistence.schema import initialize_database
from ai_poc_planner.persistence.solution_catalog import SQLiteSolutionCatalogRepository
from tests.support.assessed_snapshot import build_assessed_snapshot


def test_existing_assessment_is_returned_without_provider_or_duplicate_run(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "idempotency.sqlite3"
    connection = database_connection(database_path)
    try:
        initialize_database(connection)
        fixture = build_assessed_snapshot(
            connection,
            SelectedModelSnapshot(
                profile_id=uuid4(),
                profile_name="Test profile",
                model_name="test-model",
            ),
        )
        history = ProjectHistoryService(
            SQLiteProjectHistoryRepository(connection),
            selected_profile_getter=lambda: None,
        )
        provider_calls: list[object] = []

        def fail_if_called(_: object) -> object:
            provider_calls.append(object())
            raise AssertionError("provider must not be called")

        service = EvidenceAnalysisService(
            history=history,
            sessions=SQLiteDiscoveryRepository(connection),
            analyses=SQLiteAnalysisRepository(connection),
            readiness=object(),
            selected_profile_getter=lambda: None,
            adapter_factory=fail_if_called,
            catalog=SQLiteSolutionCatalogRepository(connection),
        )
        assert service.create(fixture.project_id, 1) == fixture.expected_analysis
        assert provider_calls == []
    finally:
        connection.close()


def test_domain_validation_failure_is_contained_before_persistence() -> None:
    version = SimpleNamespace(id=uuid4())
    service = object.__new__(EvidenceAnalysisService)
    service._history = SimpleNamespace(
        get_version=lambda _project_id, _version_number: version
    )
    service._analyses = SimpleNamespace(get_by_version=lambda _version_id: None)
    service._require_ready = lambda _project_id, _version_number: (version, [], {})
    service._require_profile = lambda _version: object()
    service._analysis_prompt = lambda *_args: {}
    service._token_groups = lambda *_args: ((), ())
    service._call_stage = lambda *_args: SimpleNamespace(options=[])
    service._call_option_detail = lambda *_args: object()
    service._to_domain_draft = lambda *_args, **_kwargs: object()
    service._validate_references = lambda *_args: None

    def fail_deterministic_assembly(*_args, **_kwargs):
        raise ValueError("synthetic domain validation detail")

    service._validated_result = fail_deterministic_assembly

    with pytest.raises(EvidenceAnalysisError) as caught:
        service.create(uuid4(), 1)

    assert caught.value.code == "analysis_result_invalid"
    assert service._analyses.get_by_version(version.id) is None


def test_governed_assistive_accepts_reviewed_permission_solution_alias() -> None:
    service = object.__new__(EvidenceAnalysisService)
    solution = SimpleNamespace(
        solution_key="permission_request_rules_and_human_approval",
        recommendation_category="rules_first",
    )

    assert service._solution_matches_formal_category(
        solution, RecommendationCategory.GOVERNED_ASSISTIVE
    )
    assert not service._solution_matches_formal_category(
        SimpleNamespace(
            solution_key="unreviewed-solution",
            recommendation_category="rules_first",
        ),
        RecommendationCategory.GOVERNED_ASSISTIVE,
    )
    assert not service._solution_matches_formal_category(
        solution, RecommendationCategory.AI_HYBRID
    )
