from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from ai_poc_planner.application.assessment_policy import (
    derive_decision_authority,
    derive_processing_boundary,
)
from ai_poc_planner.domain.enums import (
    DecisionAuthority,
    FactStatus,
    ProcessingBoundary,
)
from ai_poc_planner.domain.project_history import FactRevision


def _fact(
    value: str | None,
    *,
    status: FactStatus = FactStatus.CONFIRMED,
) -> FactRevision:
    return FactRevision(
        id=uuid4(),
        version_id=uuid4(),
        fact_key="processing_boundary",
        value=value,
        status=status,
        reference_message_ids=[uuid4()],
        created_at=datetime.now(UTC),
    )


@pytest.mark.parametrize(
    ("facts", "expected"),
    [
        (
            (_fact("僅限本機處理，資料不得離開內部網路。"),),
            ProcessingBoundary.LOCAL_ONLY,
        ),
        (
            (_fact("只能使用脫敏或核准環境，外部模型尚未獲准。"),),
            ProcessingBoundary.PRIVATE_ENDPOINT,
        ),
        (
            (_fact("此 PoC 已核准外部處理與外部模型。"),),
            ProcessingBoundary.EXTERNAL_ENDPOINT,
        ),
        (
            (_fact(None, status=FactStatus.UNKNOWN),),
            ProcessingBoundary.LOCAL_ONLY,
        ),
        (
            (
                _fact("僅限本機處理。", status=FactStatus.CONFIRMED),
                _fact("已核准外部處理。", status=FactStatus.CONFIRMED),
            ),
            ProcessingBoundary.LOCAL_ONLY,
        ),
        (
            (
                _fact("只能使用核准環境，外部模型尚未獲准。"),
                _fact("已核准外部處理。"),
            ),
            ProcessingBoundary.PRIVATE_ENDPOINT,
        ),
    ],
)
def test_processing_boundary_uses_confirmed_facts_with_conservative_precedence(
    facts: tuple[FactRevision, ...], expected: ProcessingBoundary
) -> None:
    assert derive_processing_boundary(facts) is expected


def test_processing_boundary_ignores_nonconfirmed_external_permission() -> None:
    assert (
        derive_processing_boundary(
            (_fact("已核准外部處理。", status=FactStatus.ASSUMPTION),)
        )
        is ProcessingBoundary.LOCAL_ONLY
    )


def test_decision_authority_never_grants_autonomy_from_provider_content() -> None:
    facts = (_fact("主管保留最終核准，系統僅提供輔助。"),)

    assert derive_decision_authority(facts) is DecisionAuthority.HUMAN_FINAL_DECISION
