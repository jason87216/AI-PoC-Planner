"""Compose the canonical, reader-oriented assessment report."""

# ruff: noqa: E501

from __future__ import annotations

import json
import re
from collections.abc import Sequence

from ai_poc_planner.domain.analysis import ValidatedAnalysisResult
from ai_poc_planner.domain.discovery import InterviewQuestion
from ai_poc_planner.domain.enums import FactStatus
from ai_poc_planner.domain.planning_report import (
    CurrentTargetComparison,
    GateAppendixRow,
    InterviewFinding,
    OptionComparison,
    ReportAppendix,
    ReportSynthesis,
    ReviewedCaseContent,
    ReviewedSolutionContent,
    RoadmapPhase,
    ScoreAppendixRow,
)
from ai_poc_planner.domain.project_history import (
    FactRevision,
    VisibleConversationMessage,
)
from ai_poc_planner.domain.reviewed_cases import ReviewedCase, ReviewStatus
from ai_poc_planner.domain.solution_catalog import SolutionPattern


class ReportSynthesisError(RuntimeError):
    """Raised when persisted analysis cannot be tied to approved report content."""


_FACT_LABELS = {
    "current_workflow_problem": "目前流程",
    "desired_outcome": "預期成果",
    "available_data": "可用資料",
    "users_and_owners": "使用者與負責人",
    "known_constraints": "已知限制",
    "human_final_decision": "人工最終決策",
    "approval_process_detail": "審批流程與例外",
    "processing_boundary": "資料處理邊界",
    "first_phase_scope": "第一階段範圍",
    "auditability_requirements": "追溯與稽核",
    "governance_and_risk": "治理與風險",
    "validation_metric": "驗收指標",
    "success_conditions": "驗收條件",
    "process_scope": "第一階段範圍",
    "audit_trail_detail": "追溯與稽核",
    "audit_trail_requirements": "稽核紀錄要求",
    "validation_sample": "驗證樣本",
    "fault_labels": "故障標籤",
}
_SCORE_LABELS = {
    "business_value": "商業價值",
    "data_readiness": "資料就緒度",
    "technical_fit": "技術適配性",
    "architecture_controllability": "架構可控性",
    "governance_readiness": "治理就緒度",
    "user_adoption": "使用者採用度",
}
_TOPIC_IMPACTS = {
    "current_workflow_problem": "用來確認第一階段要優先改善的流程痛點。",
    "desired_outcome": "用來設定 PoC 的可觀察效益與驗收方式。",
    "available_data": "決定可納入的資料範圍與驗證樣本準備方式。",
    "users_and_owners": "用來界定使用者、品質責任與例外交接。",
    "known_constraints": "用來限制第一階段範圍與部署方式。",
    "human_final_decision": "明確保留人工確認與對外回覆責任。",
    "approval_process_detail": "用來界定主管核准、拒絕與例外處理的流程。",
    "processing_boundary": "用來限定資料可在何種受控環境中處理。",
    "first_phase_scope": "用來限制第一階段的工作範圍。",
    "auditability_requirements": "用來保留追溯、覆核與例外處理紀錄。",
    "governance_and_risk": "用來確認資料、權限與人工責任的限制。",
    "validation_metric": "用來設定可觀察的驗收指標。",
    "success_conditions": "用來定義第一階段的通過條件。",
    "process_scope": "用來限制第一階段的工作範圍。",
    "audit_trail_detail": "用來保留追溯、覆核與例外處理紀錄。",
    "audit_trail_requirements": "用來確保審批人、時間、備註與例外紀錄可供查詢與稽核。",
    "validation_sample": "提醒驗證樣本仍待確認，不能視為已具備。",
    "fault_labels": "提醒標籤定義仍待確認，不能直接承諾模型成果。",
}


def _display_value(value: object) -> str:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def _unique(values: Sequence[str], *, empty: str = "目前尚待確認。") -> list[str]:
    result = list(dict.fromkeys(item.strip() for item in values if item.strip()))
    return result or [empty]


def _has_english_sentence(value: str) -> bool:
    return bool(re.search(r"[A-Za-z]{4,}(?:\s+[A-Za-z]{2,}){2,}", value))


def _natural_text(value: object, *, fallback: str) -> str:
    """Keep the report Chinese even when an internal rationale is English."""

    text = "" if value is None else _display_value(value)
    text = re.sub(r"\bF\d{3}\b|\bSC-\d+\b", "", text).strip()
    text = re.sub(r"\s+", " ", text)
    for source, target in {
        "Email": "電子郵件",
        "Excel": "試算表",
        "audit trail": "稽核紀錄",
        "Manual Knowledge Base Consolidation": "傳統知識庫整合",
        "Foundations-First Knowledge Graph": "先建立資料基礎的知識關係整理",
        "Customer-service assistance": "客服輔助",
        "Generative AI assistance": "生成式 AI 輔助",
        "Governance and risk": "治理與風險",
        "success_conditions": "驗收條件",
        "required controls": "必要控制措施",
    }.items():
        text = text.replace(source, target)
    text = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", text)
    return fallback if not text or _has_english_sentence(text) else text


def _phrase(value: str) -> str:
    return value.rstrip("。；;. ")


def _fact_display(fact: FactRevision | None) -> str:
    if fact is None:
        return "待確認。"
    if fact.status is FactStatus.CONFIRMED:
        return _natural_text(fact.value, fallback="已確認內容需以中文補充說明。")
    if fact.status in {FactStatus.UNKNOWN, FactStatus.MISSING}:
        return "待確認。"
    return "待核實。"


def _fact_map(facts: Sequence[FactRevision]) -> dict[str, FactRevision]:
    return {fact.fact_key.strip().casefold(): fact for fact in facts}


def _fact(facts: dict[str, FactRevision], key: str) -> str:
    return _fact_display(facts.get(key))


def _joined(values: Sequence[str], *, empty: str = "目前尚待確認。") -> str:
    return "；".join(_unique(values, empty=empty))


def _formal_category(analysis: ValidatedAnalysisResult) -> str:
    if analysis.case_centered is not None:
        return analysis.case_centered.recommendation_category.value
    return {
        "hybrid_ai_and_non_ai": "ai_hybrid",
        "better_suited_to_non_ai": "rules_first",
        "establish_non_ai_foundations_before_ai": "readiness_first",
    }.get(analysis.conclusion.value, "governed_assistive")


def _reviewed_solution_content(solution: SolutionPattern) -> ReviewedSolutionContent:
    if solution.review_status is not ReviewStatus.APPROVED:
        raise ReportSynthesisError("solution_not_approved")
    return ReviewedSolutionContent(
        display_name_zh=solution.display_name_zh,
        short_description_zh=solution.short_description_zh,
        detailed_description_zh=solution.detailed_description_zh,
        suitable_when_zh=solution.suitable_when_zh,
        not_suitable_when_zh=solution.not_suitable_when_zh,
        typical_scope_zh=solution.typical_scope_zh,
        human_boundary_zh=solution.human_boundary_zh,
        expected_outputs_zh=solution.expected_outputs_zh,
        acceptance_focus_zh=solution.acceptance_focus_zh,
    )


def _reviewed_case_content(case: ReviewedCase) -> ReviewedCaseContent:
    if case.review_status is not ReviewStatus.APPROVED or not case.source_url:
        raise ReportSynthesisError("case_not_approved_or_missing_source")
    fields = (
        "display_title_zh",
        "case_summary_zh",
        "problem_context_zh",
        "implemented_approach_zh",
        "documented_outcomes_zh",
        "transferable_practices_zh",
        "limitations_zh",
    )
    if any(getattr(case, field) is None for field in fields):
        raise ReportSynthesisError("case_content_incomplete")
    return ReviewedCaseContent(
        display_title_zh=case.display_title_zh,
        organization=case.organization,
        case_summary_zh=case.case_summary_zh,
        problem_context_zh=case.problem_context_zh,
        implemented_approach_zh=case.implemented_approach_zh,
        documented_outcomes_zh=case.documented_outcomes_zh,
        transferable_practices_zh=case.transferable_practices_zh,
        limitations_zh=case.limitations_zh,
        source_name=case.source_name,
        source_url=str(case.source_url),
    )


def build_interview_findings(
    *,
    questions: Sequence[InterviewQuestion],
    messages: Sequence[VisibleConversationMessage],
    facts: Sequence[FactRevision],
) -> list[InterviewFinding]:
    """Summarise confirmed interview content without emitting the raw question."""

    answers = {str(message.id): message.content for message in messages}
    fact_by_key = _fact_map(facts)
    findings: list[InterviewFinding] = []
    for question in sorted(
        questions, key=lambda item: (item.round_number, item.position)
    ):
        key = question.fact_key.strip().casefold()
        answer = answers.get(str(question.answer_message_id))
        findings.append(
            InterviewFinding(
                topic=_FACT_LABELS.get(key, "訪談補充重點"),
                confirmed_content=_natural_text(
                    answer or _fact_display(fact_by_key.get(key)),
                    fallback="待確認。",
                ),
                assessment_impact=_TOPIC_IMPACTS.get(
                    key, "用來調整第一階段範圍與驗收方式。"
                ),
            )
        )
    return findings


def _case_support(
    cases: Sequence[ReviewedCaseContent],
) -> tuple[list[str], str, str, list[str]]:
    if not cases:
        return (
            [],
            "目前沒有足夠相關的已審核成熟案例，因此本方案主要依據專案需求、流程規則與目前條件形成，案例只待後續補充。",
            "先以專案內部資料與人工確認流程驗證，不主張直接套用外部案例。",
            ["案例的使用者、資料與責任邊界不同，不能直接複製。"],
        )
    return (
        [case.display_title_zh for case in cases],
        _joined([case.case_summary_zh for case in cases]),
        _joined([case.transferable_practices_zh for case in cases]),
        _unique([case.limitations_zh for case in cases]),
    )


def _option_comparison(
    analysis: ValidatedAnalysisResult,
    solution: SolutionPattern,
    reviewed_cases: Sequence[ReviewedCaseContent],
    candidate_solutions: Sequence[SolutionPattern],
) -> list[OptionComparison]:
    category = solution.recommendation_category
    case_names, case_evidence, transferable, cannot_copy = _case_support(reviewed_cases)
    rows = [
        OptionComparison(
            option=solution.display_name_zh,
            positioning=solution.short_description_zh,
            supporting_cases=case_names,
            case_evidence=case_evidence,
            transferable_practice=transferable,
            cannot_copy=cannot_copy,
            conclusion="正式推薦；適合以有限範圍 PoC 驗證。",
            recommended=True,
        )
    ]
    solutions_by_category = {
        item.recommendation_category: item
        for item in candidate_solutions
        if item.review_status is ReviewStatus.APPROVED
    }
    relevant_alternative_categories = {
        "governed_assistive": {"rules_first", "readiness_first"},
    }.get(category)
    alternative_categories: list[str] = []
    for option in analysis.options:
        if option.option_key == analysis.recommended_option_key:
            continue
        alternative_category = {
            "non_ai": "rules_first",
            "foundations_first": "readiness_first",
            "hybrid": "ai_hybrid",
            "ai": "ai_hybrid",
        }.get(getattr(option.option_kind, "value", ""))
        if (
            alternative_category is None
            or alternative_category == category
            or alternative_category in alternative_categories
            or (
                relevant_alternative_categories is not None
                and alternative_category not in relevant_alternative_categories
            )
        ):
            continue
        alternative = solutions_by_category.get(alternative_category)
        if alternative is None:
            continue
        alternative_categories.append(alternative_category)
        rows.append(
            OptionComparison(
                option=alternative.display_name_zh,
                positioning=alternative.short_description_zh,
                case_evidence="本次未找到可直接參照的已審核案例；此方向僅作為比較參考。",
                transferable_practice=alternative.typical_scope_zh,
                cannot_copy=["目前沒有可直接套用的外部做法，仍需依本專案條件驗證。"],
                conclusion="可作為比較基線，暫不列為正式推薦。",
            )
        )
    return rows


def _comparison_narrative(
    analysis: ValidatedAnalysisResult,
    facts: Sequence[FactRevision],
    options: Sequence[OptionComparison],
    title: str,
) -> str:
    names = "、".join(item.option for item in options)
    recommended = next(item for item in options if item.recommended)
    unknowns = [
        _FACT_LABELS.get(fact.fact_key, "重要資訊")
        for fact in facts
        if fact.status in {FactStatus.UNKNOWN, FactStatus.MISSING}
    ]
    case_narrative = (
        f"成熟案例方面，本次以{'、'.join(recommended.supporting_cases)}作為{title}中特定做法的參考。它們支持受控的資料使用、內容檢索或人工確認，但不代表本專案可以照搬相同的自動化程度。"
        if recommended.supporting_cases
        else f"本次沒有找到可支持「{title}」的已審核成熟案例，因此不把其他領域案例當成證據。正式判斷以已確認的流程規則、人工責任、資料條件與驗收範圍為準。"
    )
    gap_sentence = (
        "、".join(dict.fromkeys(unknowns)) or "實際資料版本、責任分工與驗證樣本"
    )
    return "\n\n".join(
        [
            f"本次主要比較{names}等方向；比較的目的不是重新排名，而是確認哪一種做法最能回應已確認的專案問題與限制。",
            case_narrative,
            f"本專案與案例之間最大的差距在於{gap_sentence}仍須逐項確認。因此，案例只用來說明可移植的流程做法，不能取代本專案的資料、權限與驗收判斷。",
            f"綜合已確認需求、人工責任與可驗證範圍後，仍選擇「{title}」作為正式推薦；下表先呈現方案與案例的關係，再說明推薦方案會如何改變目前狀態。",
        ]
    )


def _target_copy(category: str) -> tuple[str, str, str, str, str, str]:
    values = {
        "ai_hybrid": (
            "透過單一入口檢索核准內容、顯示來源並產生回覆草稿。",
            "AI 提供候選內容；人員確認、修改並決定是否使用。",
            "建立可追溯的知識來源與代表性驗證集。",
            "只在核准環境與明確資料範圍內提供內部輔助。",
            "依明確權限使用核准資料，保留人工覆核與修改紀錄。",
            "以代表性問題比較搜尋時間、來源正確性與人工修改情形。",
        ),
        "rules_first": (
            "在固定流程中檢查欄位、金額、附件與已定義規則。",
            "系統提示規則結果；人員處理例外與最終審核。",
            "將核准規則與例外整理成可追溯的規則集。",
            "先在既有內部流程中運作，不擴大到未確認的整合。",
            "由規則負責人維護變更紀錄，保留人工例外判斷。",
            "以規則命中、漏檢情形與人工檢查時間驗收。",
        ),
        "governed_assistive": (
            "在受控流程中整理申請內容、提示缺項並交由具責任人員核准。",
            "AI 僅整理與提示；主管保留核准、拒絕與高風險操作權限。",
            "使用經核准的資料與權限範本，建立可追溯的申請紀錄。",
            "只在核准或脫敏環境中試行，不直接寫入高風險系統。",
            "以最小權限、保存規則與人工覆核紀錄限制使用範圍。",
            "以申請格式完整率、規則提示正確率、主管審批處理時間與例外紀錄完整性驗收。",
        ),
        "readiness_first": (
            "先盤點資料、定義標籤與建立可驗證的工作流程。",
            "領域人員確認標籤、判定基準與後續是否進入模型評估。",
            "形成可追溯的資料清單、標註規則與保留驗證集。",
            "只進行受控的資料準備與驗證設計，不進入生產部署。",
            "由領域與工程負責人共同確認資料用途、版本與驗收紀錄。",
            "以樣本代表性、標註一致性與驗證設計完整度驗收。",
        ),
    }
    return values[category]


def _current_target_comparison(
    analysis: ValidatedAnalysisResult,
    facts: Sequence[FactRevision],
    category: str,
) -> list[CurrentTargetComparison]:
    fact_by_key = _fact_map(facts)
    targets = _target_copy(category)
    current_human = _fact(fact_by_key, "human_final_decision")
    if current_human == "待確認。":
        current_human = _fact(fact_by_key, "users_and_owners")
    current_system = _fact(fact_by_key, "processing_boundary")
    if current_system == "待確認。":
        current_system = _fact(fact_by_key, "known_constraints")
    rows = [
        (
            "流程",
            _fact(fact_by_key, "current_workflow_problem"),
            targets[0],
            "流程步驟、資料入口或版本尚未統一。",
            "先整理可用範圍，再依推薦方案建立受控的第一階段流程。",
        ),
        (
            "人工責任",
            current_human,
            targets[1],
            "覆核順序、例外交接或最終責任仍待確認。",
            "把人工確認設為必要步驟，並保留修改與例外紀錄。",
        ),
        (
            "資料",
            _fact(fact_by_key, "available_data"),
            targets[2],
            "資料代表性、版本與品質仍待確認。",
            "先整理核准樣本、資料版本與驗證集，再納入推薦方案。",
        ),
        (
            "系統與部署",
            current_system,
            targets[3],
            "可用環境、串接範圍與資料流向仍待確認。",
            "第一階段只在受控環境中提供輔助，不直接擴大系統整合。",
        ),
        (
            "治理",
            _fact(fact_by_key, "known_constraints"),
            targets[4],
            "權限、保存、稽核與責任安排仍待確認。",
            "以核准資料、明確權限與人工覆核紀錄限制 PoC 範圍。",
        ),
        (
            "驗收方式",
            _fact(fact_by_key, "desired_outcome"),
            targets[5],
            "驗證樣本、通過門檻與錯誤分類仍待確認。",
            "先建立代表性測試，再以推薦方案的實際結果與人工覆核紀錄驗收。",
        ),
    ]
    return [
        CurrentTargetComparison(
            aspect=aspect,
            current_state=current,
            target_state=target,
            main_gap=gap,
            treatment=treatment,
        )
        for aspect, current, target, gap, treatment in rows
    ]


def _phase_defaults(
    category: str, index: int
) -> tuple[list[str], list[str], str, list[str]]:
    common = {
        "ai_hybrid": (
            ["盤點核准文件與 FAQ", "建立代表性問題與標準答案的測試樣本"],
            ["可追溯的知識清單與測試樣本"],
            "人員確認納入範圍、內容版本與例外處理方式。",
            ["資料來源可追溯，測試問題可由人員覆核。"],
        ),
        "rules_first": (
            ["整理規則、例外與表單欄位", "確認規則負責人與覆核流程"],
            ["可檢查的規則清單與例外處理方式"],
            "人員確認規則變更與所有例外判斷。",
            ["主要規則與例外可由人員逐項覆核。"],
        ),
        "governed_assistive": (
            ["整理申請流程與權限範本", "確認核准資料與受控環境"],
            ["可追溯的流程範本與試行資料範圍"],
            "主管保留核准與高風險操作的最終權限。",
            ["流程範本、權限範圍與人工覆核方式已確認。"],
        ),
        "readiness_first": (
            ["盤點資料來源與樣本", "定義標籤與驗證規則"],
            ["資料清單、標註規則與保留驗證集"],
            "領域人員確認標籤與驗收結論。",
            ["樣本、標籤與驗證設計可由領域人員覆核。"],
        ),
    }[category]
    if index == 0:
        return common
    return (
        ["在有限範圍內執行 PoC", "記錄人工修改、例外與驗證結果"],
        ["可檢視的 PoC 結果與改善清單"],
        common[2],
        ["結果可回溯到資料、人工確認與驗證紀錄。"],
    )


def _roadmap(analysis: ValidatedAnalysisResult, category: str) -> list[RoadmapPhase]:
    phases = analysis.case_centered.phased_path if analysis.case_centered else ()
    count = max(2, len(phases))
    names = ["準備階段（立即行動）", "第一階段 PoC"]
    rows: list[RoadmapPhase] = []
    for index in range(count):
        actions, outputs, boundary, acceptance = _phase_defaults(category, index)
        phase = phases[index] if index < len(phases) else None
        rows.append(
            RoadmapPhase(
                phase=names[index] if index < len(names) else "擴大前檢視",
                description="以有限範圍完成可驗證的準備與試行。",
                actions=actions,
                inputs=["已確認需求與核准資料"],
                outputs=outputs,
                human_decision_boundary=boundary,
                not_doing=["不在驗證前擴大自動化或直接執行高影響動作。"],
                remaining_gaps=(
                    ["依第一階段結果確認是否具備擴大條件。"]
                    if phase is None
                    else ["依 PoC 紀錄確認資料、流程與驗收差距。"]
                ),
                acceptance_criteria=acceptance,
            )
        )
    return rows


def _major_risks(category: str) -> list[str]:
    common = [
        "資料代表性、版本與驗證樣本未確認前，不把試行結果視為正式成效。",
        "第一階段不擴大到未核准資料、未確認串接或自主執行。",
    ]
    specific = {
        "ai_hybrid": [
            "AI 只提供檢索與草稿；人員仍負責確認內容與對外使用。",
            "來源不清楚或版本過期時，結果必須回到人工查核。",
        ],
        "rules_first": [
            "規則未定義或出現例外時，系統只提示，不取代人員審核。",
            "第一階段不把固定規則延伸為未驗證的 AI 判斷。",
        ],
        "governed_assistive": [
            "主管保留核准與高風險操作權限；系統不得直接執行。",
            "未核准資料或權限範圍不納入試行。",
        ],
        "readiness_first": [
            "資料與標籤不足時，不承諾模型準確率或進入生產部署。",
            "領域人員未確認判定基準前，不擴大資料收集結論。",
        ],
    }
    return _unique([*specific[category], *common])[:5]


def _score_improvement(dimension: str) -> str:
    return {
        "business_value": "以第一階段實際節省時間與一致性結果補強。",
        "data_readiness": "補足資料版本、代表性與驗證樣本。",
        "technical_fit": "以有限範圍試行確認技術可行性。",
        "architecture_controllability": "確認受控環境、權限與可追溯紀錄。",
        "governance_readiness": "補足責任、保存與稽核安排。",
        "user_adoption": "以使用者試行回饋與人工修改紀錄確認。",
    }.get(dimension, "依第一階段驗證結果更新。")


def _appendix(analysis: ValidatedAnalysisResult) -> ReportAppendix:
    scores = [
        ScoreAppendixRow(
            dimension=_SCORE_LABELS.get(score.dimension.value, "評估面向"),
            judgement=f"{score.rating}/5 分；加權點數 {score.weighted_points}",
            main_basis="依已確認的專案資訊與固定評估規則判斷。",
            improvement_condition=_score_improvement(score.dimension.value),
        )
        for score in analysis.scores
    ]
    gate_source = (
        analysis.case_centered.gate_impacts
        if analysis.case_centered is not None
        else analysis.gate_results
    )
    gates = [
        GateAppendixRow(
            gate_id="內部檢核項目",
            limit_content=_natural_text(
                "；".join(getattr(gate, "limits", []) or [getattr(gate, "reason", "")]),
                fallback="此項限制要求維持受控範圍。",
            ),
            affected_stage=_natural_text(
                getattr(gate, "affected_stage", ""), fallback="目前階段與第一階段 PoC"
            ),
            currently_possible=_natural_text(
                "；".join(getattr(gate, "does_not_limit", [])),
                fallback="可先在受控範圍內完成資料、流程與人工確認準備。",
            ),
            release_condition=_natural_text(
                "；".join(getattr(gate, "release_conditions", [])),
                fallback="待相關條件確認後再重新評估。",
            ),
        )
        for gate in gate_source
    ]
    return ReportAppendix(scores=scores, hard_gates=gates)


def _recommendation_narrative(
    *,
    facts: Sequence[FactRevision],
    solution: SolutionPattern,
    reviewed_cases: Sequence[ReviewedCaseContent],
    options: Sequence[OptionComparison],
) -> str:
    fact_by_key = _fact_map(facts)
    recommended = next(item for item in options if item.recommended)
    case_support = (
        "；".join(recommended.supporting_cases)
        if recommended.supporting_cases
        else "目前沒有足夠相關的已審核成熟案例"
    )
    case_basis = (
        _phrase(recommended.case_evidence)
        if reviewed_cases
        else "目前沒有足夠相關的已審核成熟案例，因此本方案主要依據專案需求、流程規則與目前條件形成，案例只待後續補充"
    )
    return "\n\n".join(
        [
            f"專案問題在於{_phrase(_fact(fact_by_key, 'current_workflow_problem'))}；期待達成的成果是{_phrase(_fact(fact_by_key, 'desired_outcome'))}。目前可用資料為{_phrase(_fact(fact_by_key, 'available_data'))}，因此第一階段不應從抽象的技術選型開始，而應先把可驗證的資料、流程與責任範圍固定下來。",
            f"正式推薦方向是「{solution.display_name_zh}」。{solution.detailed_description_zh}適用時機是{solution.suitable_when_zh}；若{solution.not_suitable_when_zh}，就不應把它當成可直接擴大的答案。",
            f"第一階段範圍為{solution.typical_scope_zh}。預期交付成果是{solution.expected_outputs_zh}，因此推薦理由不只在於處理眼前痛點，也在於把後續判斷建立在可回溯的流程與資料上。",
            f"人工責任必須維持清楚：{solution.human_boundary_zh}成熟案例支持的是其中可移植的做法，而不是另一套排名。{case_support}提供的正式案例依據是{case_basis}。本專案可借鑑{_phrase(recommended.transferable_practice)}；但{_joined(recommended.cannot_copy)}。",
            f"PoC 驗收不以通用宣稱代替實測，而是聚焦於{solution.acceptance_focus_zh}若資料、責任或驗證條件仍待確認，結果只用來決定下一階段是否補足準備，不把未知內容寫成既有能力。",
        ]
    )


def build_report_synthesis(
    *,
    analysis: ValidatedAnalysisResult,
    facts: Sequence[FactRevision],
    solution: SolutionPattern,
    reviewed_cases: Sequence[ReviewedCase],
    candidate_solutions: Sequence[SolutionPattern] = (),
    report=None,
    interview_questions: Sequence[InterviewQuestion] = (),
    messages: Sequence[VisibleConversationMessage] = (),
) -> ReportSynthesis:
    """Build one deterministic synthesis shared verbatim by UI and Markdown."""

    del report  # Provider prose is not a source of truth for the final report.
    category = _formal_category(analysis)
    if solution.review_status is not ReviewStatus.APPROVED:
        raise ReportSynthesisError("solution_not_approved")
    if solution.recommendation_category != category:
        raise ReportSynthesisError("solution_category_mismatch")
    result = analysis.case_centered
    if result is not None and (
        result.solution_key != solution.solution_key
        or result.recommendation_title != solution.display_name_zh
    ):
        raise ReportSynthesisError("project_solution_mismatch")
    matched_ids = [item.case.case_id for item in result.matched_cases] if result else []
    case_by_id = {case.case_id: case for case in reviewed_cases}
    if set(case_by_id) != set(matched_ids):
        raise ReportSynthesisError("reviewed_case_set_mismatch")
    selected_cases: list[ReviewedCase] = []
    for match in result.matched_cases if result else ():
        case = case_by_id[match.case.case_id]
        if (
            case.review_status is not ReviewStatus.APPROVED
            or solution.solution_key not in case.applicable_solution_keys
            or case.model_dump(mode="json") != match.case.model_dump(mode="json")
        ):
            raise ReportSynthesisError("reviewed_case_mismatch")
        selected_cases.append(case)
    case_content = [_reviewed_case_content(case) for case in selected_cases]
    options = _option_comparison(
        analysis,
        solution,
        case_content,
        candidate_solutions or (solution,),
    )
    return ReportSynthesis(
        executive_narrative=(
            f"本次評估建議採用「{solution.display_name_zh}」。{solution.short_description_zh}"
            "第一階段將以受控範圍驗證，不把未確認事項視為既有條件。"
        ),
        recommendation_narrative=_recommendation_narrative(
            facts=facts,
            solution=solution,
            reviewed_cases=case_content,
            options=options,
        ),
        recommended_solution=_reviewed_solution_content(solution),
        reviewed_cases=case_content,
        interview_findings=build_interview_findings(
            questions=interview_questions, messages=messages, facts=facts
        ),
        current_target_comparison=_current_target_comparison(analysis, facts, category),
        option_comparison=options,
        comparison_narrative=_comparison_narrative(
            analysis, facts, options, solution.display_name_zh
        ),
        implementation_roadmap=_roadmap(analysis, category),
        major_risks_and_boundaries=_major_risks(category),
        appendix=_appendix(analysis),
    )


def _cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ").strip()


def render_synthesis_markdown(synthesis: ReportSynthesis) -> str:
    """Render the exact canonical synthesis supplied to the UI response."""

    lines = [
        "# 專案評估報告",
        "",
        "## 1. 專案評估摘要",
        "",
        synthesis.executive_narrative,
        "",
        "## 2. 推薦方案與理由",
        "",
        f"### {synthesis.recommended_solution.display_name_zh}",
        "",
        synthesis.recommended_solution.short_description_zh,
        "",
        synthesis.recommendation_narrative,
        "",
        "## 3. 需求與訪談發現",
        "",
    ]
    if synthesis.interview_findings:
        lines.extend(["| 主題 | 已確認內容 | 對方案的影響 |", "|---|---|---|"])
        lines.extend(
            "| "
            + " | ".join(
                _cell(getattr(item, field))
                for field in ("topic", "confirmed_content", "assessment_impact")
            )
            + " |"
            for item in synthesis.interview_findings
        )
    else:
        lines.append("目前沒有新增的訪談發現；後續確認事項會直接更新此表。")
    lines.extend(
        [
            "",
            "## 4. 方案、成熟案例與專案差距比較",
            "",
            synthesis.comparison_narrative,
            "",
            "### 正式推薦方案",
            "",
            f"**方案說明：** {synthesis.recommended_solution.detailed_description_zh}",
            "",
            f"**適用時機：** {synthesis.recommended_solution.suitable_when_zh}",
            "",
            f"**人工責任：** {synthesis.recommended_solution.human_boundary_zh}",
            "",
        ]
    )
    if synthesis.reviewed_cases:
        for case in synthesis.reviewed_cases:
            lines.extend(
                [
                    f"### {case.display_title_zh}",
                    "",
                    f"- 案例背景：{case.problem_context_zh}",
                    f"- 實際做法：{case.implemented_approach_zh}",
                    f"- 已記錄成果：{case.documented_outcomes_zh}",
                    f"- 可借鑑做法：{case.transferable_practices_zh}",
                    f"- 不可直接複製：{case.limitations_zh}",
                    f"- 來源：[{case.source_name}]({case.source_url})",
                    "",
                ]
            )
    else:
        lines.extend(
            [
                "目前沒有足夠相關的已審核成熟案例，因此本方案主要依據專案需求、流程規則與目前條件形成，案例只待後續補充。",
                "",
            ]
        )
    lines.extend(
        [
            "| 方案 | 方案定位 | 支持此方案的成熟案例 | 案例能證明什麼 | 可移植到本專案的做法 | 本專案不可直接複製的部分 | 綜合判斷 |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    lines.extend(
        "| "
        + " | ".join(
            _cell(value)
            for value in (
                ("正式推薦：" if item.recommended else "") + item.option,
                item.positioning,
                _joined(
                    item.supporting_cases, empty="本次未找到可直接參照的已審核案例。"
                ),
                item.case_evidence,
                item.transferable_practice,
                _joined(item.cannot_copy),
                item.conclusion,
            )
        )
        + " |"
        for item in synthesis.option_comparison
    )
    lines.extend(
        [
            "",
            "### 目前狀態、目標狀態與主要差距",
            "",
            "| 面向 | 目前狀態 | 採用推薦方案後的目標狀態 | 主要差距 | 方案如何處理 |",
            "|---|---|---|---|---|",
        ]
    )
    lines.extend(
        "| "
        + " | ".join(
            _cell(getattr(item, field))
            for field in (
                "aspect",
                "current_state",
                "target_state",
                "main_gap",
                "treatment",
            )
        )
        + " |"
        for item in synthesis.current_target_comparison
    )
    lines.extend(
        [
            "",
            "## 5. 實施路線、風險與驗收",
            "",
            "| 階段 | 主要工作 | 交付成果 | 人工邊界 | 通過條件 |",
            "|---|---|---|---|---|",
        ]
    )
    lines.extend(
        "| "
        + " | ".join(
            _cell(value)
            for value in (
                phase.phase,
                _joined(phase.actions),
                _joined(phase.outputs),
                phase.human_decision_boundary,
                _joined(phase.acceptance_criteria),
            )
        )
        + " |"
        for phase in synthesis.implementation_roadmap
    )
    lines.extend(["", "最重要風險與暫不實施事項："])
    lines.extend(f"- {item}" for item in synthesis.major_risks_and_boundaries)
    lines.extend(["", "## 6. 技術附錄", "", "### 六維評分"])
    if synthesis.appendix.scores:
        lines.extend(["", "| 維度 | 判斷 | 主要依據 | 改善條件 |", "|---|---|---|---|"])
        lines.extend(
            "| "
            + " | ".join(
                _cell(getattr(item, field))
                for field in (
                    "dimension",
                    "judgement",
                    "main_basis",
                    "improvement_condition",
                )
            )
            + " |"
            for item in synthesis.appendix.scores
        )
    lines.extend(["", "### 硬性限制明細"])
    if synthesis.appendix.hard_gates:
        lines.extend(
            [
                "",
                "| 限制內容 | 影響階段 | 目前可做事項 | 重新評估條件 |",
                "|---|---|---|---|",
            ]
        )
        lines.extend(
            "| "
            + " | ".join(
                _cell(getattr(item, field))
                for field in (
                    "limit_content",
                    "affected_stage",
                    "currently_possible",
                    "release_condition",
                )
            )
            + " |"
            for item in synthesis.appendix.hard_gates
        )
    else:
        lines.extend(["", "目前沒有額外硬性限制。"])
    return "\n".join(lines).rstrip() + "\n"
