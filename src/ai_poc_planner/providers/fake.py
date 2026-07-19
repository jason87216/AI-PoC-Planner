"""Deterministic provider used by offline tests and smoke checks."""

from ai_poc_planner.domain.enums import (
    GateDisposition,
    Recommendation,
    ScoreDimension,
)
from ai_poc_planner.domain.models import (
    ArchitectureOption,
    ClarifyingQuestion,
    HardGateResult,
    PocProposal,
    ScoreDimensionResult,
    SimilarCase,
)
from ai_poc_planner.providers.base import ProviderRequest


class FakeProviderError(RuntimeError):
    """Intentional fake failure used to exercise provider error handling."""


class FakeModelProvider:
    """Return reproducible structured data without network or credentials."""

    ERROR_TRIGGER_TITLE = "[simulate-provider-error]"

    def generate(self, request: ProviderRequest) -> PocProposal:
        if request.project.title == self.ERROR_TRIGGER_TITLE:
            raise FakeProviderError("simulated provider failure")

        return PocProposal(
            schema_version="1.0",
            recommendation=Recommendation.CONDITIONAL,
            gate_disposition=GateDisposition.PASS,
            problem_statement=request.project.problem_statement,
            target_users=["客服人員"],
            current_workflow_summary="客服人員手動搜尋已核准的產品文件。",
            known_information={
                "project_id": str(request.project.id),
                **request.known_information,
            },
            missing_information=["需確認代表性問題集與答案擁有者"],
            clarifying_questions=[
                ClarifyingQuestion(
                    field="evaluation_dataset",
                    question="是否已有代表性問題與核准答案？",
                    reason="需要離線評估檢索品質。",
                    priority=1,
                )
            ],
            similar_cases=[
                SimilarCase(
                    case_id="fake-case-001",
                    title="本機知識檢索輔助案例",
                    similarity=0.8,
                    fit_summary="適合有人工覆核與核准知識來源的查找流程。",
                    source_ref="synthetic:fake-case-001",
                )
            ],
            scores=_fixed_scores(),
            weighted_score=73,
            hard_gates=[
                HardGateResult(
                    rule_id="HG-BASELINE",
                    disposition=GateDisposition.PASS,
                    reason="合成案例未觸發已知 hard gate。",
                    required_controls=[],
                    human_review_required=False,
                )
            ],
            architecture_options=[
                ArchitectureOption(
                    name="本機 fake-model baseline",
                    summary="只驗證 contracts 與 provider seam，不連接真實模型。",
                    deployment="local",
                    components=[
                        "Python package",
                        "Pydantic contracts",
                        "fake provider",
                    ],
                    assumptions=["正式檢索與 Agent workflow 尚未實作"],
                )
            ],
            required_data=["代表性問題", "已核准答案"],
            integrations=[],
            risks=["尚未以真實案例驗證"],
            human_review_points=["核准資料來源與成功指標"],
            roi_assumptions=["尚未取得正式 baseline，僅作測試資料"],
            success_metrics=["proposal schema validation passes"],
            estimated_weeks=2,
            estimated_team=["AI／Solution Engineer", "業務流程負責人"],
            next_actions=["建立可驗證的需求訪談資料"],
        )


def _fixed_scores() -> list[ScoreDimensionResult]:
    ratings = {
        ScoreDimension.BUSINESS_VALUE: (4, 25, 20.0),
        ScoreDimension.DATA_READINESS: (3, 20, 12.0),
        ScoreDimension.TECHNICAL_FIT: (4, 15, 12.0),
        ScoreDimension.ARCHITECTURE_CONTROLLABILITY: (4, 15, 12.0),
        ScoreDimension.GOVERNANCE_READINESS: (3, 15, 9.0),
        ScoreDimension.USER_ADOPTION: (4, 10, 8.0),
    }
    return [
        ScoreDimensionResult(
            dimension=dimension,
            rating=rating,
            weight=weight,
            weighted_points=points,
            rationale="固定的 fake-provider 測試評估。",
            evidence_refs=["synthetic:baseline"],
        )
        for dimension, (rating, weight, points) in ratings.items()
    ]
