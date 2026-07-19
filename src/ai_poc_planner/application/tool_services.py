"""Deterministic implementations of the six bounded assessment tools."""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID, uuid5

from ai_poc_planner.assessment.gates import evaluate_hard_gates
from ai_poc_planner.assessment.scoring import (
    score_architecture_controllability,
    score_business_value,
    score_data_readiness,
    score_governance_readiness,
    score_technical_fit,
    score_user_adoption,
)
from ai_poc_planner.domain.enums import EvidenceSourceType
from ai_poc_planner.domain.facts import AssessmentFacts
from ai_poc_planner.domain.models import (
    ArchitectureOption,
    EvidenceReference,
    SimilarCase,
)
from ai_poc_planner.domain.tools import (
    AssessBusinessValueRoiAndKpisInput,
    AssessBusinessValueRoiAndKpisOutput,
    AssessDataReadinessInput,
    AssessDataReadinessOutput,
    AssessmentToolOutputs,
    AssessTechnicalFitAndArchitectureInput,
    AssessTechnicalFitAndArchitectureOutput,
    EstimatePocScopeInput,
    EstimatePocScopeOutput,
    EvaluateRiskAndHardGatesInput,
    EvaluateRiskAndHardGatesOutput,
    KpiProposal,
    RetrieveSimilarCasesInput,
    RetrieveSimilarCasesOutput,
    ToolContract,
    ToolError,
    ToolOutputContract,
)
from ai_poc_planner.providers.base import AssessmentToolInputs

TOOL_NAMES = (
    "retrieve_similar_cases",
    "assess_data_readiness",
    "assess_technical_fit_and_architecture",
    "evaluate_risk_and_hard_gates",
    "assess_business_value_roi_and_kpis",
    "estimate_poc_scope",
)
_CASE_NAMESPACE = UUID("70000000-0000-0000-0000-000000000001")
_FIXTURE_CASES = (
    (
        frozenset({"customer-service", "retail"}),
        SimilarCase(
            case_id="fixture-customer-support",
            title="客服核准知識查找",
            similarity=0.92,
            fit_summary="適合有核准知識來源、代表性問題與人工覆核的查找流程。",
            source_ref="fixture:customer-support",
        ),
    ),
    (
        frozenset({"legal", "professional-services"}),
        SimilarCase(
            case_id="fixture-contract-review",
            title="合約條款輔助審查",
            similarity=0.78,
            fit_summary="僅適合保留法律專業人員最終判斷的輔助流程。",
            source_ref="fixture:contract-review",
        ),
    ),
    (
        frozenset({"operations"}),
        SimilarCase(
            case_id="fixture-document-intake",
            title="文件收件與欄位檢查",
            similarity=0.64,
            fit_summary="適合規則明確且可人工處理例外的文件前處理。",
            source_ref="fixture:document-intake",
        ),
    ),
)


def _context(request: ToolContract) -> dict[str, object]:
    return {
        "schema_version": request.schema_version,
        "correlation_id": request.correlation_id,
        "project_id": request.project_id,
        "session_id": request.session_id,
    }


def retrieve_similar_cases(
    request: RetrieveSimilarCasesInput,
) -> RetrieveSimilarCasesOutput:
    """Perform a transparent fixture filter; this is not semantic retrieval."""
    requested = set(request.industries)
    matches = [
        case
        for industries, case in _FIXTURE_CASES
        if not requested or industries.intersection(requested)
    ][: request.top_k]
    evidence = [
        EvidenceReference(
            id=uuid5(_CASE_NAMESPACE, case.case_id),
            project_id=request.project_id,
            session_id=request.session_id,
            source_type=EvidenceSourceType.CASE,
            source_ref=case.source_ref,
            label=case.title,
            metadata={"lookup": "deterministic_fixture"},
        )
        for case in matches
    ]
    return RetrieveSimilarCasesOutput(
        **_context(request),
        cases=matches,
        evidence=evidence,
    )


def assess_data_readiness(
    request: AssessDataReadinessInput,
    facts: AssessmentFacts,
) -> AssessDataReadinessOutput:
    gaps: list[str] = []
    prerequisites: list[str] = []
    if not request.access_confirmed:
        gaps.append("資料存取尚未核准")
        prerequisites.append("取得資料擁有者與合法使用核准")
    if not request.validation_sample_available:
        gaps.append("缺少代表性 validation sample")
        prerequisites.append("建立可重現的離線驗證資料集")
    return AssessDataReadinessOutput(
        **_context(request),
        score=score_data_readiness(facts.data_readiness),
        gaps=gaps,
        prerequisites=prerequisites,
        rationale="依資料存取、數位化、品質與驗證樣本 facts 評估。",
    )


def assess_technical_fit_and_architecture(
    request: AssessTechnicalFitAndArchitectureInput,
    facts: AssessmentFacts,
) -> AssessTechnicalFitAndArchitectureOutput:
    option = ArchitectureOption(
        name="本機 deterministic planning pipeline",
        summary="以 typed services、固定規則與人工覆核邊界完成 PoC。",
        deployment="local",
        components=[
            "structured interview fixture",
            "deterministic assessment tools",
            "Pydantic contracts",
            "Markdown exporter",
        ],
        assumptions=["目前不含真實模型、資料庫或 semantic retrieval"],
    )
    return AssessTechnicalFitAndArchitectureOutput(
        **_context(request),
        technical_fit=score_technical_fit(facts.technical_fit),
        architecture_controllability=score_architecture_controllability(
            facts.architecture_controllability
        ),
        architecture_options=[option],
        rationale="依 AI 必要性、技術路徑、依賴與可測試性 facts 評估。",
    )


def evaluate_risk_and_hard_gates(
    request: EvaluateRiskAndHardGatesInput,
    facts: AssessmentFacts,
) -> EvaluateRiskAndHardGatesOutput:
    evaluation = evaluate_hard_gates(facts.gates)
    return EvaluateRiskAndHardGatesOutput(
        **_context(request),
        rule_version="1.0",
        hard_gates=list(evaluation.triggered),
        gate_disposition=evaluation.disposition,
        governance_readiness=score_governance_readiness(
            facts.governance_readiness
        ),
    )


def assess_business_value_roi_and_kpis(
    request: AssessBusinessValueRoiAndKpisInput,
    facts: AssessmentFacts,
) -> AssessBusinessValueRoiAndKpisOutput:
    return AssessBusinessValueRoiAndKpisOutput(
        **_context(request),
        business_value=score_business_value(facts.business_value),
        user_adoption=score_user_adoption(facts.user_adoption),
        roi_assumptions=[
            request.baseline_description,
            request.expected_change,
            "PoC 不做自動財務決策，效益需由流程負責人驗證。",
        ],
        kpi_proposals=[
            KpiProposal(
                name="中位查找時間",
                unit="minutes",
                baseline=request.current_time_minutes,
                target=3.0,
                direction="decrease",
            ),
            KpiProposal(
                name="核准答案命中率",
                unit="percent",
                baseline=None,
                target=90.0,
                direction="increase",
            ),
        ],
        rationale="以固定 baseline、目標與 adoption evidence 產生可驗證 KPI。",
    )


def estimate_poc_scope(request: EstimatePocScopeInput) -> EstimatePocScopeOutput:
    points = (
        (2 if request.requires_ocr else 0)
        + request.integration_count * 2
        + (1 if request.requires_review_ui else 0)
        + (0 if request.evaluation_data_available else 2)
        + (2 if request.handles_sensitive_data else 0)
        + max(0, request.department_count - 1)
    )
    roles = ["AI／Solution Engineer", "業務流程負責人"]
    if request.requires_review_ui:
        roles.append("代表性使用者／Reviewer")
    if request.handles_sensitive_data:
        roles.append("資安／隱私 Reviewer")
    assumptions = ["使用單一標準訪談與固定評估框架"]
    if not request.evaluation_data_available:
        assumptions.append("開始建置前需建立 evaluation dataset")
    return EstimatePocScopeOutput(
        **_context(request),
        estimated_weeks=max(2, 2 + (points + 2) // 3),
        roles=roles,
        complexity_points=points,
        assumptions=assumptions,
    )


def _error_output(
    output_type: type[ToolOutputContract],
    request: ToolContract,
) -> ToolOutputContract:
    return output_type(
        **_context(request),
        error=ToolError(
            code="simulated_tool_error",
            message="Deterministic tool failure requested by the test input.",
            retryable=False,
            details={},
        ),
    )


def run_assessment_tools(
    inputs: AssessmentToolInputs,
    facts: AssessmentFacts,
    *,
    fail_tool: str | None = None,
) -> AssessmentToolOutputs:
    """Run all six tools in a stable order without I/O or mutable state."""
    if fail_tool is not None and fail_tool not in TOOL_NAMES:
        raise ValueError(f"unknown tool: {fail_tool}")

    calls: dict[str, tuple[ToolContract, Callable[[], ToolOutputContract]]] = {
        "retrieve_similar_cases": (
            inputs.retrieve_similar_cases,
            lambda: retrieve_similar_cases(inputs.retrieve_similar_cases),
        ),
        "assess_data_readiness": (
            inputs.assess_data_readiness,
            lambda: assess_data_readiness(inputs.assess_data_readiness, facts),
        ),
        "assess_technical_fit_and_architecture": (
            inputs.assess_technical_fit_and_architecture,
            lambda: assess_technical_fit_and_architecture(
                inputs.assess_technical_fit_and_architecture, facts
            ),
        ),
        "evaluate_risk_and_hard_gates": (
            inputs.evaluate_risk_and_hard_gates,
            lambda: evaluate_risk_and_hard_gates(
                inputs.evaluate_risk_and_hard_gates, facts
            ),
        ),
        "assess_business_value_roi_and_kpis": (
            inputs.assess_business_value_roi_and_kpis,
            lambda: assess_business_value_roi_and_kpis(
                inputs.assess_business_value_roi_and_kpis, facts
            ),
        ),
        "estimate_poc_scope": (
            inputs.estimate_poc_scope,
            lambda: estimate_poc_scope(inputs.estimate_poc_scope),
        ),
    }
    output_types: dict[str, type[ToolOutputContract]] = {
        "retrieve_similar_cases": RetrieveSimilarCasesOutput,
        "assess_data_readiness": AssessDataReadinessOutput,
        "assess_technical_fit_and_architecture": (
            AssessTechnicalFitAndArchitectureOutput
        ),
        "evaluate_risk_and_hard_gates": EvaluateRiskAndHardGatesOutput,
        "assess_business_value_roi_and_kpis": AssessBusinessValueRoiAndKpisOutput,
        "estimate_poc_scope": EstimatePocScopeOutput,
    }
    outputs = {
        name: (
            _error_output(output_types[name], request)
            if name == fail_tool
            else call()
        )
        for name, (request, call) in calls.items()
    }
    return AssessmentToolOutputs(**outputs)
