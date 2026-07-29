"""Compose the canonical, reader-oriented assessment report."""

# ruff: noqa: E501

from __future__ import annotations

import json
import re
from collections.abc import Sequence

from ai_poc_planner.domain.analysis import ValidatedAnalysisResult
from ai_poc_planner.domain.catalog_relationships import (
    ReviewedImplementationReference,
    SolutionCaseLink,
)
from ai_poc_planner.domain.discovery import InterviewQuestion
from ai_poc_planner.domain.enums import FactStatus
from ai_poc_planner.domain.planning_report import (
    CaseSupportSummary,
    CurrentTargetComparison,
    GateAppendixRow,
    ImplementationReferenceContent,
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
    "approval_process_detail": "核准流程與例外",
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
    "audit_trail_requirements": "用來確保核准人、時間、備註與例外紀錄可供查詢與稽核。",
    "validation_sample": "提醒驗證樣本仍待確認，不能視為已具備。",
    "fault_labels": "提醒標籤定義仍待確認，不能直接承諾模型成果。",
}

_INTERVIEW_TOPIC_ALIASES = {
    "manager_approval": "主管核准責任",
    "manager_approval_responsibility": "主管核准責任",
    "it_provisioning": "IT 開通責任",
    "it_provisioning_responsibility": "IT 開通責任",
    "rules_conflict_check": "規則與衝突檢查",
    "policy_rule_validation": "固定規則檢查",
    "required_field_validation": "必填欄位檢查",
    "exception_handling": "例外處理",
    "audit_trail": "稽核紀錄",
    "access_review": "存取檢視",
}
_INTERVIEW_IMPACT_ALIASES = {
    "manager_approval": "用來保留主管的最終核准責任。",
    "manager_approval_responsibility": "用來保留主管的最終核准責任。",
    "it_provisioning": "用來分開主管核准與 IT 實際開通。",
    "it_provisioning_responsibility": "用來分開主管核准與 IT 實際開通。",
    "rules_conflict_check": "用來決定固定規則、衝突提示與例外交由誰處理。",
    "policy_rule_validation": "用來決定固定規則與衝突提示的驗收範圍。",
    "required_field_validation": "用來檢查申請資料是否完整。",
    "exception_handling": "用來界定例外如何回到人工判斷。",
    "audit_trail": "用來保留申請、核准人與處理時間的稽核紀錄。",
    "access_review": "用來安排後續存取檢視與撤銷追蹤。",
}
_PRACTICE_LABELS = {
    "structured_request_intake": "集中申請入口與標準欄位",
    "required_field_validation": "必填欄位檢查",
    "policy_rule_validation": "固定規則與衝突檢查",
    "manager_approval": "主管核准",
    "resource_owner_approval": "資源負責人核准",
    "provisioning_separation": "核准與 IT 開通分離",
    "exception_handling": "例外處理",
    "audit_trail": "稽核紀錄",
    "access_review": "存取檢視",
    "temporary_access": "臨時存取",
    "access_expiration": "期限管理",
}
_SIMPLIFIED_REPLACEMENTS = {
    "申请": "申請",
    "规则": "規則",
    "审批": "核准",
    "审核": "審核",
    "记录": "紀錄",
    "查询": "查詢",
    "数据": "資料",
    "权限": "權限",
    "审计": "稽核",
    "时间": "時間",
    "自动": "自動",
    "实际": "實際",
    "确认": "確認",
    "问题": "問題",
    "复核": "覆核",
    "范围": "範圍",
    "处理": "處理",
    "开发": "開發",
    "系统": "系統",
    "用户": "使用者",
    "负责": "負責",
    "人员": "人員",
    "资料": "資料",
}
_BANNED_VISIBLE_TERMS = (
    "Fxxx",
    "SC-xxx",
    "success_conditions",
    "required controls",
    "go/no-go",
    "安全化原始問答",
    "證據依據",
    "訪談補充重點",
    "其他已確認事項",
)


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
        "autonomous_action": "自主執行高風險動作",
        "High": "高",
        "Low": "低",
        "Medium": "中",
        "審批": "核准",
    }.items():
        text = text.replace(source, target)
    for source, target in _SIMPLIFIED_REPLACEMENTS.items():
        text = text.replace(source, target)
    for term in _BANNED_VISIBLE_TERMS:
        text = text.replace(term, "")
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
    cleaned = [_phrase(item) for item in _unique(values, empty=empty)]
    return "；".join(cleaned)


def _joined_verbatim(values: Sequence[str], *, empty: str = "目前尚待確認。") -> str:
    """Join reviewed catalogue text without changing its terminal punctuation."""

    return " ".join(_unique(values, empty=empty))


def _practice_labels(keys: Sequence[str], *, fallback: str) -> str:
    labels = _unique(
        [_PRACTICE_LABELS.get(key, "") for key in keys],
        empty=fallback,
    )
    return "、".join(labels)


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
        short_description_zh=_natural_text(
            solution.short_description_zh, fallback="推薦方向待補充。"
        ),
        detailed_description_zh=_natural_text(
            solution.detailed_description_zh, fallback="推薦方向待補充。"
        ),
        suitable_when_zh=_natural_text(
            solution.suitable_when_zh, fallback="適用條件待補充。"
        ),
        not_suitable_when_zh=_natural_text(
            solution.not_suitable_when_zh, fallback="限制條件待補充。"
        ),
        typical_scope_zh=_natural_text(
            solution.typical_scope_zh, fallback="第一階段範圍待補充。"
        ),
        human_boundary_zh=_natural_text(
            solution.human_boundary_zh, fallback="人工責任邊界待補充。"
        ),
        expected_outputs_zh=_natural_text(
            solution.expected_outputs_zh, fallback="預期交付成果待補充。"
        ),
        acceptance_focus_zh=_natural_text(
            solution.acceptance_focus_zh, fallback="驗收方式待補充。"
        ),
    )


def _reviewed_case_content(
    case: ReviewedCase,
    link: SolutionCaseLink | None = None,
) -> ReviewedCaseContent:
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
        support_type=link.support_type if link is not None else "supporting",
        supported_practice_keys=(
            list(link.supported_practice_keys) if link is not None else []
        ),
        applicability_note_zh=link.applicability_note_zh if link is not None else "",
        limitation_note_zh=link.limitation_note_zh if link is not None else "",
    )


def _case_support_summaries(
    cases: Sequence[ReviewedCaseContent], solution_key: str
) -> list[CaseSupportSummary]:
    summaries: list[CaseSupportSummary] = []
    for case in cases:
        supported = case.applicability_note_zh or case.transferable_practices_zh
        if solution_key == "permission_request_rules_and_human_approval":
            adoption = (
                "本專案先採用標準欄位、固定規則檢查、主管核准、"
                "IT 依核准結果開通與完整稽核紀錄。"
            )
        else:
            adoption = (
                f"本專案只採用{_phrase(case.transferable_practices_zh)}，"
                "再依自身資料與人工責任重新驗證。"
            )
        summaries.append(
            CaseSupportSummary(
                case_title=case.display_title_zh,
                supported_practices=_natural_text(
                    supported, fallback="可移植做法待確認。"
                ),
                project_adoption=adoption,
            )
        )
    return summaries


def _implementation_reference_contents(
    references: Sequence[ReviewedImplementationReference],
) -> list[ImplementationReferenceContent]:
    return [
        ImplementationReferenceContent(
            topic=_practice_labels(
                reference.supported_practice_keys,
                fallback="流程實施",
            ),
            display_title_zh=reference.display_title_zh,
            purpose_zh=reference.summary_zh,
            source_name=reference.source_name,
            source_url=str(reference.source_url),
        )
        for reference in references
    ]


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
    ordered_questions = sorted(
        questions, key=lambda item: (item.round_number, item.position)
    )
    answer_by_key: dict[str, str] = {}
    for question in ordered_questions:
        key = question.fact_key.strip().casefold()
        answer = answers.get(str(question.answer_message_id), "").strip()
        if answer:
            answer_by_key[key] = answer

    confirmed_facts = {
        fact.fact_key.strip().casefold(): fact
        for fact in facts
        if fact.status is FactStatus.CONFIRMED
    }
    seen_keys: set[str] = set()

    def add_finding(key: str, fact: FactRevision | None) -> None:
        topic = _INTERVIEW_TOPIC_ALIASES.get(key) or _FACT_LABELS.get(key)
        impact = _INTERVIEW_IMPACT_ALIASES.get(key) or _TOPIC_IMPACTS.get(key)
        if topic is None or impact is None:
            return
        seen_keys.add(key)
        findings.append(
            InterviewFinding(
                topic=topic,
                confirmed_content=_natural_text(
                    answer_by_key.get(key) or _fact_display(fact),
                    fallback="待確認。",
                ),
                assessment_impact=impact,
            )
        )

    # Keep the current round's answer-backed findings first, then append every
    # confirmed persisted fact so refresh/history cannot erase earlier findings.
    for question in ordered_questions:
        key = question.fact_key.strip().casefold()
        if key in seen_keys:
            continue
        if key not in confirmed_facts and key not in answer_by_key:
            continue
        add_finding(key, confirmed_facts.get(key) or fact_by_key.get(key))
    for fact in facts:
        key = fact.fact_key.strip().casefold()
        if key in seen_keys or key not in confirmed_facts:
            continue
        add_finding(key, confirmed_facts[key])
    return findings


def _case_support(
    cases: Sequence[ReviewedCaseContent],
    references: Sequence[ReviewedImplementationReference] = (),
) -> tuple[list[str], str, str, list[str], list[str]]:
    if not cases:
        return (
            [],
            "未有已審核案例可提供直接佐證。",
            "先以專案內部資料與人工確認流程驗證，不主張直接套用外部案例。",
            ["案例的使用者、資料與責任邊界不同，不能直接複製。"],
            [],
        )
    reference_names = [
        f"[{item.display_title_zh}]({item.source_url})" for item in references
    ]
    return (
        [case.display_title_zh for case in cases],
        " ".join(
            " ".join(
                (
                    f"{case.display_title_zh}：{case.case_summary_zh}",
                    f"案例背景：{case.problem_context_zh}",
                    f"實際做法：{case.implemented_approach_zh}",
                    f"已記錄成果：{case.documented_outcomes_zh}",
                )
            )
            for case in cases
        )
        + " 來源："
        + "、".join(f"[{case.source_name}]({case.source_url})" for case in cases),
        " ".join(
            item
            for case in cases
            for item in (
                case.transferable_practices_zh,
                case.applicability_note_zh,
            )
            if item
        ),
        _unique(
            [
                item
                for case in cases
                for item in (case.limitations_zh, case.limitation_note_zh)
                if item
            ]
        ),
        reference_names,
    )


def _case_table_support(
    cases: Sequence[ReviewedCaseContent],
) -> tuple[str, str, list[str]]:
    """Keep the integrated comparison table concise; detail belongs in rationale."""

    if not cases:
        return (
            "未有已審核案例可提供直接佐證。",
            "先以專案內部資料與人工確認流程驗證。",
            ["案例的使用者、資料與責任邊界不同，不能直接複製。"],
        )
    evidence = "；".join(
        f"{case.display_title_zh}：{case.applicability_note_zh or case.case_summary_zh}"
        for case in cases
    )
    transferable = "；".join(
        _unique([case.transferable_practices_zh for case in cases])
    )
    cannot_copy = [
        "案例已有成熟產品與較大規模整合；本專案先不直接開通，也不複製案例量化成效。"
    ]
    return evidence, transferable, cannot_copy


def _option_comparison(
    analysis: ValidatedAnalysisResult,
    solution: SolutionPattern,
    reviewed_cases: Sequence[ReviewedCaseContent],
    candidate_solutions: Sequence[SolutionPattern],
    implementation_references: Sequence[ReviewedImplementationReference] = (),
) -> list[OptionComparison]:
    category = solution.recommendation_category
    case_names, case_evidence, transferable, cannot_copy, reference_names = (
        _case_support(reviewed_cases, implementation_references)
    )
    if solution.solution_key == "permission_request_rules_and_human_approval":
        table_case_evidence, table_transferable, table_cannot_copy = (
            _case_table_support(reviewed_cases)
        )
        route_order = {
            "baseline": 0,
            "recommended": 1,
            "future_extension": 2,
            "rejected": 3,
        }
        routes = sorted(
            {
                item.solution_key: item
                for item in candidate_solutions
                if item.review_status is ReviewStatus.APPROVED
                and item.alternative_type is not None
                and item.solution_key.startswith("permission_request_")
            }.values(),
            key=lambda item: route_order.get(item.alternative_type or "", 99),
        )
        if solution.solution_key not in {item.solution_key for item in routes}:
            routes.append(solution)
        rows: list[OptionComparison] = []
        for route in routes:
            recommended = route.solution_key == solution.solution_key
            if recommended:
                rows.append(
                    OptionComparison(
                        option=route.display_name_zh,
                        positioning=_natural_text(
                            route.short_description_zh, fallback="主要做法待補充。"
                        ),
                        supporting_cases=case_names,
                        case_evidence=table_case_evidence,
                        transferable_practice=table_transferable,
                        cannot_copy=table_cannot_copy,
                        supporting_references=reference_names,
                        conclusion="正式推薦；適合以有限範圍 PoC 驗證。",
                        recommended=True,
                    )
                )
                continue
            conclusion = {
                "baseline": "可作為最低成本基線，暫不列為正式推薦。",
                "future_extension": "列為後續延伸，第一階段不作為主要方案。",
                "rejected": "明確拒絕；不得繞過主管核准或 IT 開通責任。",
            }.get(route.alternative_type or "", "作為比較參考，暫不列為正式推薦。")
            rows.append(
                OptionComparison(
                    option=route.display_name_zh,
                    positioning=_natural_text(
                        route.short_description_zh, fallback="主要做法待補充。"
                    ),
                    case_evidence="此方向沒有本次推薦案例直接支持，只用來說明取捨。",
                    transferable_practice=route.typical_scope_zh,
                    cannot_copy=[route.human_boundary_zh],
                    conclusion=conclusion,
                )
            )
        return rows
    rows = [
        OptionComparison(
            option=solution.display_name_zh,
            positioning=_natural_text(
                solution.short_description_zh, fallback="主要做法待補充。"
            ),
            supporting_cases=case_names,
            case_evidence=case_evidence,
            transferable_practice=transferable,
            cannot_copy=cannot_copy,
            supporting_references=reference_names,
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
                positioning=_natural_text(
                    alternative.short_description_zh, fallback="主要做法待補充。"
                ),
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
    if title == "權限申請標準化、規則檢查與人工核准":
        case_names = "、".join(recommended.supporting_cases) or "本次沒有匹配案例"
        return "\n\n".join(
            [
                "本次主要比較電子郵件與試算表人工標準化、標準化申請搭配固定規則與人工核准，以及未來處理自由文字與附件的 AI 輔助；另列出自動核准與直接開通作為明確拒絕的方向。這些方向的差異在於申請入口、規則檢查、人工責任與是否直接執行開通。",
                f"本次實際匹配的成熟案例為{case_names}。這些案例分別支持集中申請、核准、期限或稽核等做法；案例的產品環境、組織規模與既有整合不同，因此只能作為成熟做法的參考，不能直接複製自動化程度或案例成效。",
                "本專案最大的差距是目前仍以電子郵件與試算表收件，申請欄位、衝突規則、例外處理、主管核准與 IT 開通紀錄尚未形成單一流程；這與案例已具備的身分治理平台和整合能力不同。綜合比較後仍選擇「權限申請標準化、規則檢查與人工核准」，因為它先處理已確認的流程問題，又保留主管與 IT 的責任邊界，並能在第一階段以可驗收資料驗證。",
            ]
        )
    unknowns = [
        _FACT_LABELS.get(fact.fact_key, "重要資訊")
        for fact in facts
        if fact.status in {FactStatus.UNKNOWN, FactStatus.MISSING}
    ]
    case_narrative = (
        f"成熟案例方面，本次以{'、'.join(recommended.supporting_cases)}作為{title}中特定做法的參考。它們支持受控的資料使用、人工確認與可追溯流程，但不代表本專案可以照搬相同的自動化程度。"
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
            "以申請格式完整率、規則提示正確率、主管核准處理時間與例外紀錄完整性驗收。",
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
    solution_key: str = "",
) -> list[CurrentTargetComparison]:
    fact_by_key = _fact_map(facts)
    if solution_key == "permission_request_rules_and_human_approval":
        rows = [
            (
                "流程",
                "員工以電子郵件與試算表提出權限申請，欄位與格式不一致，人工往返確認漏項。",
                "員工使用統一申請入口提交標準欄位，提交時立即看到必填資料與固定規則衝突。",
                "申請入口、欄位定義與狀態追蹤尚未統一。",
                "先建立標準欄位、申請狀態與職位—權限範本，再加入規則提示。",
            ),
            (
                "人工責任",
                "主管負責最後判斷，IT 依個案處理開通，但核准與執行紀錄分散。",
                "主管保留最終核准或退回權，IT 只依核准結果實際開通，兩者紀錄分開保存。",
                "覆核順序、退回原因與例外交接尚未固定。",
                "把主管核准設為必要步驟，並把 IT 開通結果記錄為後續人工作業。",
            ),
            (
                "資料",
                "已有員工資料、權限清單、電子郵件與試算表，但格式、版本與代表性尚未統一。",
                "申請資料、規則結果、核准與開通紀錄形成同一筆可追溯測試資料。",
                "職位—權限範本、必填欄位與測試樣本仍待確認。",
                "第一階段先整理核准欄位與代表性申請，並建立錯誤分類。",
            ),
            (
                "系統與部署",
                "目前沒有單一申請入口，電子郵件與試算表也沒有直接連到權限系統的受控流程。",
                "在受控環境中提供標準申請、規則結果與待辦狀態，不直接寫入正式權限系統。",
                "申請入口、紀錄保存與 IT 開通介面尚未定義。",
                "PoC 先以模擬或人工確認的開通結果驗證流程，再決定是否整合。",
            ),
            (
                "治理",
                "已知個人資料不得送到未核准外部模型，也不得自動核准或開通高風險權限。",
                "只在核准環境處理申請，主管核准與 IT 開通責任不可被系統取代，所有例外留下紀錄。",
                "權限範本、保存方式、稽核責任與例外規則仍待確認。",
                "以固定規則、人工核准、最小權限與稽核紀錄限制 PoC 範圍。",
            ),
            (
                "驗收方式",
                "目前尚未有同一組樣本可同時檢查格式完整性、規則提示、核准時間與例外紀錄。",
                "以代表性申請驗收格式完整率、規則提示正確率、主管核准處理時間、例外紀錄完整性與稽核紀錄完整性。",
                "驗證集、錯誤分類與通過門檻仍待確認。",
                "先建立可重複的申請樣本與人工對照結果，再依五項指標判斷是否進入擴大評估。",
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
    if (
        analysis.case_centered is not None
        and analysis.case_centered.solution_key
        == "permission_request_rules_and_human_approval"
    ):
        return [
            RoadmapPhase(
                phase="準備階段（立即行動）",
                description="把申請欄位、權限範本、規則與責任整理成可驗證的基線。",
                actions=[
                    "統一電子郵件與試算表申請為標準欄位",
                    "建立職位—權限範本與申請狀態",
                    "列出必填欄位、規則衝突與例外處理方式",
                    "確認主管核准與 IT 開通的責任邊界",
                ],
                inputs=["現有申請樣本", "權限清單", "主管與 IT 的流程確認"],
                outputs=["標準申請欄位", "規則與例外清單", "責任分工表"],
                human_decision_boundary="主管確認核准規則與例外；IT 確認開通作業，不由系統代為決定。",
                not_doing=["不自動核准", "不直接寫入正式權限系統"],
                remaining_gaps=["權限範本與代表性測試樣本待確認。"],
                acceptance_criteria=["欄位、規則、例外與責任可由主管和 IT 逐項確認。"],
            ),
            RoadmapPhase(
                phase="第一階段 PoC",
                description="在受控資料與有限範圍內驗證表單、規則提示、人工核准與紀錄。",
                actions=[
                    "檢查必填欄位與規則衝突",
                    "把規則結果交由主管核准或退回",
                    "由 IT 依核准結果完成模擬或人工開通",
                    "記錄申請、規則結果、核准人、時間與 IT 處理結果",
                ],
                inputs=["代表性申請樣本", "已確認規則", "核准環境"],
                outputs=["規則檢查結果", "核准與開通紀錄", "例外清單"],
                human_decision_boundary="主管作最終核准；IT 作實際開通；系統不得取代兩者。",
                not_doing=[
                    "不自動核准",
                    "不直接寫入正式權限系統",
                    "不以 AI 取代固定規則",
                ],
                remaining_gaps=["依驗收結果確認是否需要系統整合。"],
                acceptance_criteria=[
                    "格式完整率、規則提示正確率、主管核准處理時間、例外紀錄完整性與稽核紀錄完整性可被量測。"
                ],
            ),
            RoadmapPhase(
                phase="擴大前檢視",
                description="依 PoC 證據決定是否進入權限系統整合或評估非結構化資料輔助。",
                actions=[
                    "檢視五項驗收指標與未解例外",
                    "決定是否規劃權限系統整合",
                    "只有在自由文字或附件成為瓶頸時，才評估 AI 輔助",
                ],
                inputs=["PoC 紀錄", "主管與 IT 回饋", "例外與稽核結果"],
                outputs=["擴大或暫停決定", "後續整合範圍", "AI 評估前提"],
                human_decision_boundary="業務主管、資訊安全與 IT 共同決定是否擴大；AI 不取得核准或開通權限。",
                not_doing=["不把案例成效當成本專案承諾", "不跳過人工核准"],
                remaining_gaps=["正式整合、存取檢視週期與 AI 使用授權待決定。"],
                acceptance_criteria=["每項擴大決定都有對應的 PoC 紀錄與責任人。"],
            ),
        ]
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


def _appendix(
    analysis: ValidatedAnalysisResult, *, solution_key: str = ""
) -> ReportAppendix:
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
    gates_by_limit: dict[str, GateAppendixRow] = {}
    for gate in gate_source:
        release_conditions = list(getattr(gate, "release_conditions", []) or [])
        if solution_key == "permission_request_rules_and_human_approval":
            release_conditions = [
                item
                for item in release_conditions
                if not any(term in item for term in ("OCR", "數位化"))
            ]
        row = GateAppendixRow(
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
                "；".join(release_conditions),
                fallback="待相關條件確認後再重新評估。",
            ),
        )
        existing = gates_by_limit.get(row.limit_content)
        if existing is None:
            gates_by_limit[row.limit_content] = row
            continue
        gates_by_limit[row.limit_content] = existing.model_copy(
            update={
                "affected_stage": _joined(
                    [existing.affected_stage, row.affected_stage]
                ),
                "currently_possible": _joined(
                    [existing.currently_possible, row.currently_possible]
                ),
                "release_condition": _joined(
                    [existing.release_condition, row.release_condition]
                ),
            }
        )
    gates = list(gates_by_limit.values())
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
    if solution.solution_key == "permission_request_rules_and_human_approval":
        case_names = "、".join(case.organization for case in reviewed_cases)
        case_conclusion = (
            f"本次匹配的成熟案例為{case_names}；它們共同支持集中申請、主管核准、"
            "期限或稽核追蹤等流程做法。案例的產品環境、組織規模與自動化程度不同，"
            "本專案只採用可移植的流程原則，不直接複製產品整合或案例成效。"
            if reviewed_cases
            else "本次沒有匹配的已審核成熟案例（目前沒有足夠相關的已審核成熟案例），"
            "因此推薦主要依據專案流程、固定規則與人工責任形成，不把其他領域案例當成直接證據。"
        )
        return "\n\n".join(
            [
                f"本專案目前以電子郵件與試算表處理員工權限申請，申請欄位不一致，容易漏填，主管與 IT 也缺少同一份可追溯的處理紀錄。推薦方向是「{solution.display_name_zh}」，先把員工、申請系統、權限範圍、申請理由、期限與附件等內容整理成標準欄位，再讓系統在提交時檢查必填資料與固定規則衝突。",
                f"正式推薦是「{solution.display_name_zh}」，因為它先處理申請入口、欄位與規則的一致性，再把主管核准和 IT 開通分成可追蹤的責任步驟。{case_conclusion}",
                "生成式 AI 不是第一階段核心：目前最需要驗證的是必填資料、固定規則與例外處理，而不是生成文字。第一階段可以先把 AI 限制在整理或提示，不能取得核准權，也不能直接執行開通。",
                "主管保留最終核准、退回與要求補件的權限；IT 依已核准結果開通。系統負責收集標準欄位、檢查規則、提示缺項並保存申請、規則結果、核准人、時間、開通結果與例外紀錄。",
                "PoC 前置條件是確認申請欄位、職位與權限範本、固定規則、衝突定義與交接責任。第一階段不處理自動開通；驗收檢查申請格式完整率、規則提示正確率、主管核准處理時間、例外紀錄完整性與稽核可追溯性，預期效益是減少漏項、提升檢查一致性並縮短人工往返。",
                "未來只有在標準欄位、規則與人工流程穩定後，才評估以 AI 整理自由文字或附件；若要串接權限系統，也必須先完成權限範本、最小權限、稽核與回復流程設計。任何 AI 或系統串接都不能取代主管核准與 IT 的實際責任。",
            ]
        )
    case_names = "、".join(case.organization for case in reviewed_cases)
    case_conclusion = (
        f"本次匹配的成熟案例為{case_names}；它們只支持可移植的流程做法，"
        "不代表本專案可以複製相同的產品環境、規模或案例成效。"
        if reviewed_cases
        else "本次沒有匹配的已審核成熟案例，因此不把其他領域案例當成直接證據。"
    )
    return "\n\n".join(
        [
            f"專案問題在於{_phrase(_fact(fact_by_key, 'current_workflow_problem'))}；期待達成的成果是{_phrase(_fact(fact_by_key, 'desired_outcome'))}。目前可用資料為{_phrase(_fact(fact_by_key, 'available_data'))}，因此第一階段不應從抽象的技術選型開始，而應先把可驗證的資料、流程與責任範圍固定下來。",
            f"正式推薦方向是「{solution.display_name_zh}」。{solution.detailed_description_zh}本次理由聚焦於{_phrase(recommended.transferable_practice)}，而不是把案例詳情當成方案本身。",
            f"生成式 AI 不是第一階段核心；先完成資料、流程與責任的可驗證定義，再評估 AI 是否能降低整理成本。{case_conclusion}",
            f"人工責任必須維持清楚：{solution.human_boundary_zh}系統只在受控範圍內提供輔助，不把未確認條件寫成既有能力。",
            f"第一階段範圍為{solution.typical_scope_zh}，PoC 驗收聚焦於{solution.acceptance_focus_zh}預期交付成果是{solution.expected_outputs_zh}，並以人工覆核與可追溯紀錄確認結果。",
            f"未來若資料、流程與驗收條件穩定，再評估生成式 AI 或系統串接；若{solution.not_suitable_when_zh}，就不應擴大自動化。",
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
    case_links: Sequence[SolutionCaseLink] = (),
    implementation_references: Sequence[ReviewedImplementationReference] = (),
) -> ReportSynthesis:
    """Build one deterministic synthesis shared verbatim by UI and Markdown."""

    del report  # Provider prose is not a source of truth for the final report.
    category = _formal_category(analysis)
    if solution.review_status is not ReviewStatus.APPROVED:
        raise ReportSynthesisError("solution_not_approved")
    if solution.recommendation_category != category and not (
        solution.solution_key == "permission_request_rules_and_human_approval"
        and solution.recommendation_category == "governed_assistive"
    ):
        raise ReportSynthesisError("solution_category_mismatch")
    result = analysis.case_centered
    if result is not None and (
        result.solution_key != solution.solution_key
        or result.recommendation_title != solution.display_name_zh
    ):
        raise ReportSynthesisError("project_solution_mismatch")
    matched_ids = [item.case.case_id for item in result.matched_cases] if result else []
    if (
        solution.solution_key == "permission_request_rules_and_human_approval"
        and not matched_ids
    ):
        raise ReportSynthesisError(
            "CATALOG_COVERAGE_ERROR: formal permission route has no reviewed cases"
        )
    case_by_id = {case.case_id: case for case in reviewed_cases}
    link_by_case = {
        link.case_id: link
        for link in case_links
        if link.solution_key == solution.solution_key
        and link.support_type in {"primary", "supporting"}
    }
    legacy_empty_case_compat = (
        not reviewed_cases
        and solution.solution_key == "permission_request_rules_and_human_approval"
        and solution.recommendation_category == "governed_assistive"
    )
    if legacy_empty_case_compat:
        matched_ids = []
    if set(case_by_id) != set(matched_ids):
        raise ReportSynthesisError("reviewed_case_set_mismatch")
    selected_cases: list[ReviewedCase] = []
    matches = (
        () if legacy_empty_case_compat else (result.matched_cases if result else ())
    )
    for match in matches:
        case = case_by_id[match.case.case_id]
        if (
            case.review_status is not ReviewStatus.APPROVED
            or (case_links and case.case_id not in link_by_case)
            or case.model_dump(mode="json") != match.case.model_dump(mode="json")
        ):
            raise ReportSynthesisError("reviewed_case_mismatch")
        selected_cases.append(case)
    case_content = [
        _reviewed_case_content(case, link_by_case.get(case.case_id))
        for case in selected_cases
    ]
    options = _option_comparison(
        analysis,
        solution,
        case_content,
        candidate_solutions or (solution,),
        implementation_references,
    )
    return ReportSynthesis(
        executive_narrative=(
            f"本次評估建議採用「{solution.display_name_zh}」。{_natural_text(solution.short_description_zh, fallback='推薦方向待補充。')}"
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
        case_support_summaries=_case_support_summaries(
            case_content, solution.solution_key
        ),
        implementation_references=_implementation_reference_contents(
            implementation_references
        ),
        interview_findings=build_interview_findings(
            questions=interview_questions, messages=messages, facts=facts
        ),
        current_target_comparison=_current_target_comparison(
            analysis, facts, category, solution.solution_key
        ),
        option_comparison=options,
        comparison_narrative=_comparison_narrative(
            analysis, facts, options, solution.display_name_zh
        ),
        implementation_roadmap=_roadmap(analysis, category),
        major_risks_and_boundaries=_major_risks(category),
        appendix=_appendix(analysis, solution_key=solution.solution_key),
    )


def _cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ").strip()


def validate_report_quality(synthesis: ReportSynthesis, markdown: str) -> None:
    """Fail closed before persistence when reader-facing content regresses."""

    errors: list[str] = []
    for term in _BANNED_VISIBLE_TERMS:
        if term in markdown:
            errors.append(f"banned_visible_term:{term}")
    if re.search(r"\bF\d{3}\b|\bSC-\d+\b", markdown):
        errors.append("internal_reference_token")
    if re.search(r"。；|；。|。，|。。", markdown):
        errors.append("malformed_punctuation")
    if re.search(
        r"[A-Za-z]{4,}(?:\s+[A-Za-z]{2,}){3,}[.!?]",
        markdown,
    ):
        errors.append("english_sentence")
    if any(term in markdown for term in _SIMPLIFIED_REPLACEMENTS):
        errors.append("simplified_chinese")
    if len(synthesis.recommendation_narrative) <= len(synthesis.executive_narrative):
        errors.append("recommendation_not_longer_than_summary")
    paragraphs = [
        re.sub(r"\s+", "", item) for item in markdown.split("\n\n") if item.strip()
    ]
    if len(paragraphs) != len(set(paragraphs)):
        errors.append("adjacent_duplicate_paragraph")
    if synthesis.recommended_solution is not None and (
        synthesis.recommended_solution.display_name_zh
        == "權限申請標準化、規則檢查與人工核准"
    ):
        if len(synthesis.option_comparison) != 4 and synthesis.reviewed_cases:
            errors.append("permission_route_count")
        if not any(
            phrase in synthesis.recommendation_narrative
            for phrase in ("生成式 AI 不是第一階段核心", "生成式 AI 不是目前方案的核心")
        ):
            errors.append("rules_first_ai_first_narrative")
    if errors:
        raise ReportSynthesisError("REPORT_QUALITY_ERROR: " + ", ".join(errors))


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
        lines.append("目前沒有已確認的訪談結論。")
    lines.extend(
        [
            "",
            "## 4. 方案、成熟案例與專案差距比較",
            "",
            synthesis.comparison_narrative,
            "",
        ]
    )
    lines.extend(
        [
            "### 路線比較",
            "",
            "| 方案 | 主要做法 | 優點 | 限制 | 判斷 |",
            "|---|---|---|---|---|",
        ]
    )
    lines.extend(
        "| "
        + " | ".join(
            _cell(value)
            for value in (
                ("正式推薦：" if item.recommended else "") + item.option,
                item.positioning,
                item.transferable_practice,
                _joined_verbatim(item.cannot_copy),
                item.conclusion,
            )
        )
        + " |"
        for item in synthesis.option_comparison
    )
    lines.extend(["", "### 成熟案例介紹", ""])
    for case in synthesis.reviewed_cases:
        lines.extend(
            [
                f"### {case.display_title_zh}",
                "",
                f"- 背景：{case.problem_context_zh}",
                f"- 實際做法：{case.implemented_approach_zh}",
                f"- 已記錄成果：{case.documented_outcomes_zh}",
                f"- 可借鑑做法：{case.transferable_practices_zh}",
                f"- 不直接複製部分：{case.limitations_zh}",
                f"- 可點擊來源：[{case.source_name}]({case.source_url})",
                "",
            ]
        )
    lines.extend(
        [
            "### 案例支持關係摘要",
            "",
            "| 案例 | 主要支持做法 | 本專案採用方式 |",
            "|---|---|---|",
        ]
    )
    lines.extend(
        "| "
        + " | ".join(
            _cell(getattr(item, field))
            for field in ("case_title", "supported_practices", "project_adoption")
        )
        + " |"
        for item in synthesis.case_support_summaries
    )
    lines.extend(["", "### 官方實施參考", ""])
    if synthesis.implementation_references:
        lines.extend(["| 主題 | 參考文件 | 用途 |", "|---|---|---|"])
        lines.extend(
            "| "
            + " | ".join(
                (
                    _cell(reference.topic),
                    _cell(
                        f"{reference.display_title_zh}"
                        f"（[{reference.source_name}]({reference.source_url})）"
                    ),
                    _cell(reference.purpose_zh),
                )
            )
            + " |"
            for reference in synthesis.implementation_references
        )
    else:
        lines.append("目前沒有另外列出的官方實施參考。")
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
    markdown = "\n".join(lines).rstrip() + "\n"
    markdown = re.sub(r"。；", "；", markdown)
    markdown = re.sub(r"；。", "。", markdown)
    markdown = re.sub(r"。，", "，", markdown)
    markdown = re.sub(r"。{2,}", "。", markdown)
    validate_report_quality(synthesis, markdown)
    return markdown
