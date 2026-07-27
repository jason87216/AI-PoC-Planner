from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from ai_poc_planner.domain.case_centered import (
    CaseCenteredAssessment,
    CaseGapAnalysis,
    CaseReferenceValue,
    CaseReferenceValueLevel,
    FitDimension,
    FitDimensionStatus,
    FitLevel,
    ImplementationPhase,
    MatchedCaseAssessment,
    ProjectCaseFit,
    TransferablePractice,
)
from ai_poc_planner.domain.catalog import EvidenceType
from ai_poc_planner.domain.enums import FactStatus
from ai_poc_planner.domain.project_history import FactRevision
from ai_poc_planner.domain.reviewed_cases import ReviewedCase


def _case(**updates: object) -> ReviewedCase:
    payload: dict[str, object] = {
        "case_id": "case-01",
        "organization": "Example organisation",
        "title": "Permission request review assistance",
        "organization_type": "large enterprise",
        "applicable_context": ["manager approval", "permission workflow"],
        "opportunity_types": ["enterprise_knowledge_and_professional_document_assist"],
        "business_problem": "Standardise permission request review.",
        "workflow_scope": "Request, review, and approve access",
        "solution_pattern": "Role-based permission templates with human review",
        "required_inputs": ["employee role", "requested access"],
        "system_dependencies": ["role catalogue"],
        "governance_conditions": ["audit trail", "least privilege"],
        "decision_authority": "human_final_decision",
        "processing_boundary": "private_endpoint",
        "implementation_stage": "production assistive workflow",
        "implementation_method": "Role-based templates and review assistance.",
        "reported_outcomes": ["Fewer free-form requests."],
        "measurable_outcomes": ["Fewer free-form requests."],
        "applicability_tags": ["human_review"],
        "non_applicability_tags": ["autonomous_action"],
        "human_oversight": ["Manager makes the final decision."],
        "risks_or_limitations": ["Requires a role catalogue."],
        "evidence_type": EvidenceType.OFFICIAL_COMPANY_DISCLOSURE.value,
        "evidence_grade": "A",
        "source_name": "Example source",
        "source_url": "https://example.test/case",
        "review_status": "approved",
    }
    payload.update(updates)
    return ReviewedCase.model_validate(payload)


def _fact(
    key: str, value: object, status: FactStatus = FactStatus.CONFIRMED
) -> FactRevision:
    return FactRevision(
        id=uuid4(),
        version_id=uuid4(),
        fact_key=key,
        value=value,
        status=status,
        reference_message_ids=[uuid4()],
        created_at=datetime.now(UTC),
    )


def test_case_contract_exposes_context_without_inventing_legacy_fields() -> None:
    case = _case().model_copy(update={"workflow_scope": None, "required_inputs": []})

    assert case.title == "Permission request review assistance"
    assert case.workflow_scope is None
    assert case.required_inputs == []


def test_case_centered_result_keeps_reference_value_and_project_fit_separate() -> None:
    case = _case()
    matched = MatchedCaseAssessment(
        case=case,
        reference_value=CaseReferenceValue(
            level=CaseReferenceValueLevel.HIGH,
            score=90,
            basis=["已审核且来源清楚"],
        ),
        project_fit=ProjectCaseFit(
            level=FitLevel.MEDIUM,
            score=60,
            dimensions=[
                FitDimension(
                    name="流程相似度",
                    status=FitDimensionStatus.SIMILAR,
                    score=80,
                    basis=["流程都包含主管审核"],
                )
            ],
            similarities=["流程都包含主管审核"],
            key_differences=["系统依赖不同"],
        ),
        gaps=CaseGapAnalysis(
            ready_conditions=["人工最终决定"],
            missing_conditions=["统一角色目录"],
            not_directly_transferable=["案例的自动写入能力"],
            needs_confirmation=["是否已有角色目录"],
        ),
        ranking_reasons=["适用 opportunity 与需求相符"],
    )
    result = CaseCenteredAssessment(
        matching_status="matched",
        matched_cases=[matched],
        transferable_practices=[
            TransferablePractice(
                name="权限范本标准化",
                source_case_ids=[case.case_id],
                source_case_titles=[case.title],
                case_evidence="案例记录角色目录与主管审核。",
                transferable_part="先建立职位—权限范本。",
                required_adjustments=["第一阶段不接入写入权限。"],
                current_stage="第一阶段 PoC",
            )
        ],
        phased_path=[
            ImplementationPhase(
                phase_name="第一階段 PoC",
                description="以人工審核輔助驗證流程。",
                actions=["建立角色—權限範本"],
                inputs=["既有職位資料"],
                outputs=["可追蹤的申請建議"],
                users=["申請人", "主管"],
                human_decision_boundary="主管保留最終核准。",
                acceptance_criteria=["每筆申請都有人工決策紀錄。"],
            )
        ],
        recommendation_title="权限申请标准化与人工审核辅助",
        recommendation_basis=["来源案例与人工审核边界一致"],
    )

    assert result.matched_cases[0].reference_value.score == 90
    assert result.matched_cases[0].project_fit.score == 60
    assert result.transferable_practices[0].source_case_ids == [case.case_id]
