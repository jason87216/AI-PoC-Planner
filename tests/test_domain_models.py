from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from ai_poc_planner.domain.enums import (
    GateDisposition,
    InterviewRole,
    ProjectStatus,
    Recommendation,
    ScoreDimension,
)
from ai_poc_planner.domain.models import (
    AnalysisProject,
    HardGateResult,
    InterviewTurn,
    ScoreDimensionResult,
)


def test_valid_domain_models_can_be_created() -> None:
    now = datetime.now(UTC)
    project = AnalysisProject(
        id=uuid4(),
        title="客服知識檢索 PoC",
        problem_statement="客服需要更快找到已核准的產品答案。",
        status=ProjectStatus.DRAFT,
        created_at=now,
        updated_at=now,
    )
    turn = InterviewTurn(
        id=uuid4(),
        session_id=uuid4(),
        sequence=1,
        role=InterviewRole.USER,
        content="目前平均查找時間為十分鐘。",
        normalized_answers={"baseline_minutes": 10},
        created_at=now,
    )

    assert project.title == "客服知識檢索 PoC"
    assert turn.normalized_answers["baseline_minutes"] == 10


def test_missing_required_project_field_has_clear_validation_error() -> None:
    now = datetime.now(UTC)

    with pytest.raises(ValidationError) as error:
        AnalysisProject.model_validate(
            {
                "id": str(uuid4()),
                "title": "缺少問題描述",
                "status": "draft",
                "created_at": now,
                "updated_at": now,
            }
        )

    assert error.value.errors()[0]["loc"] == ("problem_statement",)


def test_score_rating_outside_one_to_five_is_rejected() -> None:
    with pytest.raises(ValidationError) as error:
        ScoreDimensionResult(
            dimension=ScoreDimension.BUSINESS_VALUE,
            rating=6,
            weight=25,
            weighted_points=25,
            rationale="分數超出合法範圍。",
            evidence_refs=[],
        )

    assert error.value.errors()[0]["loc"] == ("rating",)


def test_hard_gate_disposition_rejects_unknown_value() -> None:
    with pytest.raises(ValidationError) as error:
        HardGateResult.model_validate(
            {
                "rule_id": "HG-TEST",
                "disposition": "ignored",
                "reason": "未知狀態不可進入 domain。",
                "required_controls": [],
                "human_review_required": True,
            }
        )

    assert error.value.errors()[0]["loc"] == ("disposition",)


def test_gate_and_weighted_score_remain_separate_contracts() -> None:
    score = ScoreDimensionResult(
        dimension=ScoreDimension.TECHNICAL_FIT,
        rating=5,
        weight=15,
        weighted_points=15,
        rationale="技術模式清楚。",
        evidence_refs=["interview:data-flow"],
    )
    gate = HardGateResult(
        rule_id="HG-01",
        disposition=GateDisposition.BLOCKED,
        reason="必要資料尚未取得授權。",
        required_controls=["取得資料擁有者核准"],
        human_review_required=True,
    )

    assert score.rating == 5
    assert gate.disposition is GateDisposition.BLOCKED
    assert Recommendation.NOT_RECOMMENDED.value == "暫不建議"
