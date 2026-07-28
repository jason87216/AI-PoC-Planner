# ruff: noqa: E501

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from ai_poc_planner.domain.analysis import (
    AnalysisOptionDraft,
    ProgramGateResult,
    ProgramScore,
    ValidatedAnalysisResult,
)
from ai_poc_planner.domain.case_centered import (
    CaseCenteredAssessment,
    ImplementationPhase,
    RecommendationCategory,
)
from ai_poc_planner.domain.catalog import NonAiAlternativeDirection, OpportunityType
from ai_poc_planner.domain.enums import (
    AnalysisConclusion,
    AnalysisOptionKind,
    DecisionAuthority,
    FactStatus,
    GateDisposition,
    InterviewRole,
    ProcessingBoundary,
    ProjectStatus,
    ScoreDimension,
    VisibleMessageKind,
)
from ai_poc_planner.domain.models import SCORE_WEIGHTS
from ai_poc_planner.domain.project_history import (
    FactRevision,
    PlanningProject,
    ProjectVersion,
    SelectedModelSnapshot,
)
from ai_poc_planner.persistence.analysis import SQLiteAnalysisRepository
from ai_poc_planner.persistence.project_history import SQLiteProjectHistoryRepository


class AssessedSnapshotFixture:
    def __init__(
        self, project_id: UUID, version_id: UUID, analysis: ValidatedAnalysisResult
    ) -> None:
        (
            self.project_id,
            self.version_id,
            self.version_number,
            self.expected_analysis,
        ) = project_id, version_id, 1, analysis


def build_assessed_snapshot(
    connection,
    selected_model_snapshot: SelectedModelSnapshot,
    *,
    case_centered: CaseCenteredAssessment | None = None,
) -> AssessedSnapshotFixture:
    now = datetime.now(UTC)
    history = SQLiteProjectHistoryRepository(connection)
    analyses = SQLiteAnalysisRepository(connection)
    project = PlanningProject(
        id=uuid4(), project_name="客服请求分流 PoC", created_at=now, updated_at=now
    )
    ready = ProjectVersion(
        id=uuid4(),
        project_id=project.id,
        version_number=1,
        status=ProjectStatus.READY_FOR_ASSESSMENT,
        selected_model=selected_model_snapshot,
        created_at=now,
        updated_at=now,
    )
    history.create_project_with_version(project, ready)
    message = history.append_message(
        version_id=ready.id,
        role=InterviewRole.USER,
        message_kind=VisibleMessageKind.USER_INPUT.value,
        content="客服人员确认当前流程与人工最终决定边界。",
        created_at=now,
        message_id=uuid4(),
    )
    facts = []
    for key, value in (
        ("current_workflow", "Email 与 LINE 请求由客服人工分流。"),
        ("desired_outcome", "缩短分类与转派时间。"),
        ("human_final_decision", "客服人员确认每项建议。"),
        ("approved_external_api", "经核准的外部模型 API 可用于 PoC。"),
    ):
        fact = FactRevision(
            id=uuid4(),
            version_id=ready.id,
            fact_key=key,
            value=value,
            status=FactStatus.CONFIRMED,
            reference_message_ids=[message.id],
            created_at=now,
        )
        facts.append(history.create_fact(fact, project_updated_at=now))
    tokens = {f"F{i:03d}": fact.id for i, fact in enumerate(facts, 1)}
    refs = list(tokens)
    options = [
        AnalysisOptionDraft(
            option_key="o1",
            title="规则优先",
            option_kind=AnalysisOptionKind.NON_AI,
            summary="以规则协助基础分流。",
            expected_benefits=["一致性"],
            limitations=["复杂例外仍需人工"],
            prerequisites=["定义类别"],
            risks=["规则过期"],
            fact_refs=[refs[0]],
            decision_authority=DecisionAuthority.HUMAN_FINAL_DECISION,
            processing_boundary=ProcessingBoundary.EXTERNAL_ENDPOINT,
            non_ai_directions=[NonAiAlternativeDirection.RULE_BASED_AUTOMATION],
        ),
        AnalysisOptionDraft(
            option_key="o2",
            title="混合辅助分流",
            option_kind=AnalysisOptionKind.HYBRID,
            summary="AI 建议配合规则与人工确认。",
            expected_benefits=["辅助分类"],
            limitations=["标签仍不完整"],
            prerequisites=["验证样本"],
            risks=["建议错误"],
            fact_refs=[refs[0]],
            decision_authority=DecisionAuthority.HUMAN_FINAL_DECISION,
            processing_boundary=ProcessingBoundary.EXTERNAL_ENDPOINT,
            human_review_points=["客服确认"],
            ai_opportunity={
                "kind": "catalog",
                "opportunity_type": OpportunityType.CUSTOMER_SERVICE_ASSIST,
                "display_rationale": "客服分流场景。",
                "fact_refs": [refs[0]],
            },
            non_ai_directions=[NonAiAlternativeDirection.RULE_BASED_AUTOMATION],
        ),
    ]
    scores = [
        ProgramScore(
            dimension=d,
            rating=3,
            weight=SCORE_WEIGHTS[d],
            weighted_points=SCORE_WEIGHTS[d] * 3 // 5,
            rationale="受控 PoC 证据。",
            evidence_fact_refs=[refs[0]],
            gap_fact_refs=[],
            improvement_conditions=["待确认"],
            data_gaps=[],
            risks=[],
        )
        for d in ScoreDimension
    ]
    analysis = ValidatedAnalysisResult(
        id=uuid4(),
        version_id=ready.id,
        rubric_version="1.0",
        hard_gate_version="legacy-1",
        requirement_summary="客服分流的受控 PoC。",
        options=options,
        recommended_option_key="o2",
        conclusion=AnalysisConclusion.HYBRID_AI_AND_NON_AI,
        conclusion_rationale="保留人工最终决定。",
        conclusion_fact_refs=[refs[0]],
        scores=scores,
        weighted_total=sum(item.weighted_points for item in scores),
        gate_results=[
            ProgramGateResult(
                rule_id="HG-01",
                disposition=GateDisposition.ASSISTIVE_ONLY,
                reason="人工最终决定。",
                required_controls=["人工确认"],
                human_review_required=True,
            )
        ],
        gate_disposition=GateDisposition.ASSISTIVE_ONLY,
        created_at=now,
        case_centered=case_centered
        or CaseCenteredAssessment(
            matching_status="no_suitable_reviewed_case",
            no_case_reason="目前沒有足夠相關的已審核成熟案例。",
            phased_path=[
                ImplementationPhase(
                    phase_name="目前階段",
                    description="先整理資料與驗證條件。",
                    actions=["盤點資料"],
                    inputs=["已確認需求"],
                    outputs=["資料清單"],
                    users=["流程負責人"],
                    human_decision_boundary="人員確認資料與驗收範圍。",
                    acceptance_criteria=["資料與驗證條件可供覆核。"],
                )
            ],
            solution_key="data_readiness_validation",
            recommendation_title="資料與驗證基礎建設",
            recommendation_category=RecommendationCategory.READINESS_FIRST,
            recommendation_basis=["已確認資料與驗證條件仍待補足。"],
        ),
    )
    with history.transaction():
        analyses.create(analysis, tokens)
        assessed = ready.model_copy(
            update={"status": ProjectStatus.ASSESSED, "updated_at": now}
        )
        history.update_version(assessed, now)
    assert history.get_version(project.id, 1).status is ProjectStatus.ASSESSED
    assert analyses.get_by_version(ready.id) == analysis
    return AssessedSnapshotFixture(project.id, ready.id, analysis)
