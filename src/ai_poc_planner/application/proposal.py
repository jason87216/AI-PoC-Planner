"""Deterministic assembly of a validated PoC proposal from assessment outputs."""

from __future__ import annotations

from ai_poc_planner.domain.enums import GateDisposition
from ai_poc_planner.domain.models import (
    AnalysisProject,
    EvidenceReference,
    JSONValue,
    PocProposal,
)
from ai_poc_planner.domain.tools import AssessmentToolOutputs
from ai_poc_planner.domain.workflow import Assessment


class ProposalGenerationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _string_list(value: JSONValue | None, fallback: list[str]) -> list[str]:
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        result = [item.strip() for item in value if item.strip()]
        return result or fallback
    return fallback


def generate_proposal(
    *,
    project: AnalysisProject,
    interview_answers: dict[str, JSONValue],
    assessment: Assessment,
    tool_outputs: AssessmentToolOutputs,
    evidence: list[EvidenceReference],
) -> PocProposal:
    """Assemble proposal fields without recalculating any assessment decision."""
    retrieval = tool_outputs.retrieve_similar_cases
    technical = tool_outputs.assess_technical_fit_and_architecture
    business = tool_outputs.assess_business_value_roi_and_kpis
    scope = tool_outputs.estimate_poc_scope
    if any(item is None for item in (retrieval, technical, business, scope)):
        raise ProposalGenerationError(
            "incomplete_proposal_inputs", "proposal inputs are incomplete"
        )
    assert retrieval is not None
    assert technical is not None
    assert business is not None
    assert scope is not None
    if any(item.error is not None for item in (retrieval, technical, business, scope)):
        raise ProposalGenerationError(
            "invalid_proposal_inputs", "proposal inputs contain tool errors"
        )
    assert retrieval.cases is not None
    assert retrieval.evidence is not None
    assert technical.architecture_options is not None
    assert business.roi_assumptions is not None
    assert business.kpi_proposals is not None
    assert scope.estimated_weeks is not None
    assert scope.roles is not None
    assert scope.assumptions is not None

    controls = _unique(
        [
            control
            for gate in assessment.hard_gates
            for control in gate.required_controls
        ]
    )
    blocked = assessment.gate_disposition is GateDisposition.BLOCKED
    assistive = assessment.gate_disposition is GateDisposition.ASSISTIVE_ONLY
    requires_controls = (
        assessment.gate_disposition is GateDisposition.REQUIRES_CONTROLS
    )

    if blocked:
        summary = (
            f"暫停直接 PoC 執行。雖然加權分數為 {assessment.weighted_score}，"
            "hard gate 要求先重新設計用途、權限與人工責任邊界。"
        )
        boundary = "僅進行需求重新設計、授權確認與治理審查，不建置執行能力。"
        in_scope = ["確認合法授權與 accountable owner", "重新設計非自主用途"]
        milestones = ["完成重新設計與 qualified reviewer 核准"]
        next_actions = ["暫停直接 PoC 執行", *controls]
        architecture_options = []
        estimated_weeks = 1
        estimated_team = ["治理／領域 Reviewer"]
    else:
        summary = (
            f"評估分數 {assessment.weighted_score}，結論為"
            f"「{assessment.recommendation.value}」。"
        )
        if assistive:
            boundary = "系統只提供摘要與建議；保留人工最終決策及覆核／申訴路徑。"
        elif requires_controls:
            boundary = "完成所有 hard-gate controls 後，才可進入受限 PoC。"
        else:
            boundary = "在本機、合成／已核准資料與人工抽樣覆核範圍內驗證。"
        in_scope = ["固定訪談資料", "六維 deterministic 評估", "Markdown 報告"]
        milestones = [
            "確認 evaluation dataset 與 baseline",
            "執行離線 PoC 與錯誤分析",
            "由流程負責人審查 KPI 與 go／no-go 結論",
        ]
        next_actions = [*controls, "確認 evaluation dataset 與 KPI baseline"]
        architecture_options = technical.architecture_options
        estimated_weeks = scope.estimated_weeks
        estimated_team = scope.roles

    human_review = [
        "PoC 輸出與成效由流程負責人抽樣覆核",
        *(
            ["保留人工最終決策與可申訴／覆核路徑"]
            if assistive
            else []
        ),
        *(controls if requires_controls or blocked else []),
    ]
    all_evidence = [*evidence, *retrieval.evidence]
    risks = _unique(
        [gate.reason for gate in assessment.hard_gates]
        or ["固定 fixture 結果不可直接外推至 production"]
    )
    target_users = _string_list(
        interview_answers.get("target_users"), ["流程使用者"]
    )
    workflow_summary = str(
        interview_answers.get("current_workflow", "目前流程尚未完整描述")
    )
    success_metrics = [
        f"{item.name}: target {item.target} {item.unit}"
        for item in business.kpi_proposals
    ]

    return PocProposal(
        schema_version="1.0",
        executive_summary=summary,
        recommendation=assessment.recommendation,
        gate_disposition=assessment.gate_disposition,
        problem_statement=project.problem_statement,
        suggested_use_case_boundary=boundary,
        target_users=target_users,
        current_workflow_summary=workflow_summary,
        known_information=interview_answers,
        missing_information=[],
        clarifying_questions=[],
        similar_cases=retrieval.cases,
        scores=assessment.scores,
        weighted_score=assessment.weighted_score,
        hard_gates=assessment.hard_gates,
        architecture_options=architecture_options,
        required_data=_string_list(interview_answers.get("data_sources"), []),
        integrations=[],
        risks=risks,
        human_review_points=_unique(human_review),
        roi_assumptions=business.roi_assumptions,
        success_metrics=success_metrics,
        estimated_weeks=estimated_weeks,
        estimated_team=estimated_team,
        in_scope=in_scope,
        out_of_scope=[
            "自主最終決策或企業系統操作",
            "production deployment",
            "真實 provider、semantic retrieval 與持久化",
        ],
        poc_milestones=milestones,
        evidence_refs=sorted(str(item.id) for item in all_evidence),
        next_actions=_unique(next_actions),
    )
