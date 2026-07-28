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
    RoadmapPhase,
    ScoreAppendixRow,
)
from ai_poc_planner.domain.project_history import (
    FactRevision,
    VisibleConversationMessage,
)

_FACT_LABELS = {
    "current_workflow_problem": "目前流程",
    "desired_outcome": "預期成果",
    "available_data": "可用資料",
    "users_and_owners": "使用者與負責人",
    "known_constraints": "已知限制",
    "human_final_decision": "人工最終決策",
    "processing_boundary": "資料處理邊界",
    "first_phase_scope": "第一階段範圍",
    "auditability_requirements": "追溯與稽核",
    "governance_and_risk": "治理與風險",
    "validation_metric": "驗收指標",
    "success_conditions": "驗收條件",
    "process_scope": "第一階段範圍",
    "audit_trail_detail": "追溯與稽核",
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
_CATEGORY_TITLES = {
    "ai_hybrid": "AI 輔助與人工確認",
    "rules_first": "規則與流程標準化",
    "governed_assistive": "治理下的人工輔助",
    "readiness_first": "資料與驗證基礎建設",
}
_CATEGORY_POSITIONING = {
    "ai_hybrid": "以核准內容的自然語言檢索、來源引用與回覆草稿協助人員，最終由人員確認。",
    "rules_first": "將明確規則與例外轉成可檢查流程，先提升一致性，再評估是否需要 AI。",
    "governed_assistive": "在受控資料與權限內提供整理、提醒與檢查，不取代高影響決策。",
    "readiness_first": "先建立資料、標籤與驗證基礎，再決定後續模型或系統方案。",
}
_CATEGORY_BENEFITS = {
    "ai_hybrid": "縮短資訊查找時間、提高回覆一致性，並讓每次草稿保留可追溯的來源。",
    "rules_first": "降低漏填與規則漏檢，讓例外情形回到可被人員判斷的流程。",
    "governed_assistive": "減少格式與流程遺漏，同時維持主管與專責人員的決策責任。",
    "readiness_first": "把後續投資建立在可驗證的資料與標註基礎上，避免過早承諾模型成果。",
}
_CATEGORY_PREREQUISITES = {
    "ai_hybrid": "先確認可使用的文件範圍、版本責任與代表性驗證問題，並指定人工確認與例外交接方式。",
    "rules_first": "先整理規則、例外、表單欄位與財務責任，讓規則結果可以由人員覆核。",
    "governed_assistive": "先確認核准資料、權限範圍、保存方式與人工核准流程，再擴大任何系統整合。",
    "readiness_first": "先由領域人員定義標籤與判定基準，收集代表性樣本並保留獨立驗證集。",
}
_CATEGORY_HUMAN_BOUNDARIES = {
    "ai_hybrid": "AI 只提出檢索結果與草稿；負責人確認內容、修改例外並決定是否對外使用。",
    "rules_first": "系統只執行已核准的規則；例外、最終審核與責任判斷仍由人員負責。",
    "governed_assistive": "AI 只整理與提示；主管或具責任的人員保留核准、拒絕與高風險操作的最終權限。",
    "readiness_first": "領域人員與工程負責人保留資料標註、故障判定與驗收結論的責任。",
}
_TOPIC_IMPACTS = {
    "current_workflow_problem": "用來確認第一階段要優先改善的流程痛點。",
    "desired_outcome": "用來設定 PoC 的可觀察效益與驗收方式。",
    "available_data": "決定可納入的資料範圍與驗證樣本準備方式。",
    "users_and_owners": "用來界定使用者、品質責任與例外交接。",
    "known_constraints": "用來限制第一階段範圍與部署方式。",
    "human_final_decision": "明確保留人工確認與對外回覆責任。",
    "processing_boundary": "用來限定資料可在何種受控環境中處理。",
    "first_phase_scope": "用來限制第一階段的工作範圍。",
    "auditability_requirements": "用來保留追溯、覆核與例外處理紀錄。",
    "governance_and_risk": "用來確認資料、權限與人工責任的限制。",
    "validation_metric": "用來設定可觀察的驗收指標。",
    "success_conditions": "用來定義第一階段的通過條件。",
    "process_scope": "用來限制第一階段的工作範圍。",
    "audit_trail_detail": "用來保留追溯、覆核與例外處理紀錄。",
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


def _formal_route(analysis: ValidatedAnalysisResult) -> tuple[str, str]:
    if analysis.case_centered is not None:
        result = analysis.case_centered
        category = result.recommendation_category.value
        return category, _natural_text(
            result.recommendation_title,
            fallback=_CATEGORY_TITLES.get(category, "建議先採有限範圍方案"),
        )
    category = {
        "hybrid_ai_and_non_ai": "ai_hybrid",
        "better_suited_to_non_ai": "rules_first",
        "establish_non_ai_foundations_before_ai": "readiness_first",
    }.get(analysis.conclusion.value, "governed_assistive")
    return category, _CATEGORY_TITLES[category]


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
                topic=_FACT_LABELS.get(key, "其他已確認事項"),
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


def _option_title(option: object, *, index: int) -> str:
    kind = getattr(getattr(option, "option_kind", None), "value", "")
    formal_title = str(getattr(option, "title", "")).casefold()
    for fragment, label in (
        ("manual review workflow", "規則檢查與人工核准流程"),
        ("standardized email", "標準化申請格式與預處理"),
        ("excel", "試算表追蹤與條件檢查"),
        ("knowledge graph", "知識關係整理優先"),
        ("knowledge base", "傳統知識庫整合"),
        ("retrieval", "AI 檢索與人工確認"),
    ):
        if fragment in formal_title:
            return label
    titles = {
        "hybrid": "AI 輔助與人工確認",
        "non_ai": "規則與流程標準化",
        "foundations_first": "資料與驗證基礎建設",
        "ai": "AI 輔助分析",
    }
    return titles.get(kind, f"候選方向 {index}")


def _case_support(
    analysis: ValidatedAnalysisResult,
) -> tuple[list[str], str, str, list[str]]:
    result = analysis.case_centered
    if result is None or not result.matched_cases:
        return (
            [],
            "目前沒有直接案例支持；此方向以專案自身已確認需求與有限範圍驗證為主。",
            "先以專案內部資料與人工確認流程驗證，不主張直接套用外部案例。",
            ["案例的使用者、資料與責任邊界不同，不能直接複製。"],
        )

    practices = {
        case_id: practice
        for practice in result.transferable_practices
        for case_id in practice.source_case_ids
    }
    names: list[str] = []
    evidence: list[str] = []
    transferable: list[str] = []
    cannot_copy: list[str] = []
    for match in result.matched_cases:
        case = match.case
        case_title = case.display_title_zh or "受控 AI 輔助案例"
        names.append(f"{case.organization}：{case_title}")
        evidence.append(
            f"{case.organization} 顯示{_natural_text(case.summary_zh or '', fallback='受控的 AI 輔助與人工確認可作為方向性參考。')}"
        )
        practice = practices.get(case.case_id)
        transferable.append(
            _phrase(
                _natural_text(
                    practice.transferable_part if practice is not None else "",
                    fallback="採用受控資料、來源保留與人工確認的工作方式。",
                )
            )
        )
        cannot_copy.extend(
            _natural_text(
                item,
                fallback="案例的使用者、資料與責任邊界不同，不能直接複製。",
            )
            for item in [
                *match.project_fit.key_differences,
                *match.gaps.not_directly_transferable,
            ]
        )
    return (
        _unique(names),
        _joined(evidence),
        _joined(transferable, empty="採用受控資料、來源保留與人工確認的工作方式。"),
        _unique(
            cannot_copy,
            empty="案例的使用者、資料與責任邊界不同，不能直接複製。",
        ),
    )


def _option_comparison(
    analysis: ValidatedAnalysisResult, category: str, title: str
) -> list[OptionComparison]:
    case_names, case_evidence, transferable, cannot_copy = _case_support(analysis)
    rows = [
        OptionComparison(
            option=title,
            positioning=_CATEGORY_POSITIONING[category],
            supporting_cases=case_names,
            case_evidence=case_evidence,
            transferable_practice=transferable,
            cannot_copy=cannot_copy,
            conclusion="正式推薦；適合以有限範圍 PoC 驗證。",
            recommended=True,
        )
    ]
    for index, option in enumerate(analysis.options, start=1):
        if option.option_key == analysis.recommended_option_key:
            continue
        option_title = _option_title(option, index=index)
        if any(item.option == option_title for item in rows):
            option_title = f"{option_title}（替代做法 {index}）"
        rows.append(
            OptionComparison(
                option=option_title,
                positioning={
                    "規則與流程標準化": "先用明確規則處理固定輸入與例外提醒。",
                    "資料與驗證基礎建設": "先補足資料與驗證條件，再判斷是否進入系統實作。",
                    "AI 輔助與人工確認": "以 AI 協助整理或草稿，但仍要設定資料範圍與人工確認。",
                    "AI 輔助分析": "以有限資料進行分析輔助，不取代正式決策。",
                }.get(option_title, "作為比較基線，檢視是否能以更小範圍處理需求。"),
                case_evidence="目前沒有直接案例支持；此方向僅作為比較基線。",
                transferable_practice="可先保留資料整理、人工確認與驗證紀錄，但不足以支持直接採用。",
                cannot_copy=["沒有直接對應的成熟案例，不應推定外部做法可直接套用。"],
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
    case_sentence = (
        "、".join(recommended.supporting_cases)
        if recommended.supporting_cases
        else "目前沒有直接對應的成熟案例"
    )
    gap_sentence = (
        "、".join(dict.fromkeys(unknowns)) or "實際資料版本、責任分工與驗證樣本"
    )
    return "\n\n".join(
        [
            f"本次主要比較{names}等方向；比較的目的不是重新排名，而是確認哪一種做法最能回應已確認的專案問題與限制。",
            f"成熟案例方面，本次以{case_sentence}作為{title}中特定做法的參考。它們支持受控的資料使用、內容檢索或人工確認，但不代表本專案可以照搬相同的自動化程度。",
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
            "以漏項減少、人工覆核可追溯性與例外處理品質驗收。",
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
    category: str,
    title: str,
    options: Sequence[OptionComparison],
) -> str:
    fact_by_key = _fact_map(facts)
    recommended = next(item for item in options if item.recommended)
    case_support = (
        "；".join(recommended.supporting_cases)
        if recommended.supporting_cases
        else "目前沒有直接對應的成熟案例"
    )
    return "\n\n".join(
        [
            f"專案問題在於{_phrase(_fact(fact_by_key, 'current_workflow_problem'))}；期待達成的成果是{_phrase(_fact(fact_by_key, 'desired_outcome'))}。目前可用資料為{_phrase(_fact(fact_by_key, 'available_data'))}，因此第一階段不應從抽象的技術選型開始，而應先把可驗證的資料、流程與責任範圍固定下來。",
            f"推薦方向是「{title}」。這是正式評估結果所指定的方向：{_CATEGORY_POSITIONING[category]}其主要效益是{_phrase(_CATEGORY_BENEFITS[category])}；相較於只堆疊文件或直接追求高度自動化，這個方向能先回應已確認的問題，同時把不確定性留在可控制的 PoC 範圍內。",
            f"成熟案例支持的是其中可移植的做法，而不是另一套排名。{case_support}提供的參考是{_phrase(recommended.case_evidence)}。本專案可採用{_phrase(recommended.transferable_practice)}；但案例的使用者、資料、部署環境與責任邊界並不相同，{_joined(recommended.cannot_copy)}，所以不能直接複製其自動化程度或對外使用權限。",
            f"人工責任必須維持清楚：{_CATEGORY_HUMAN_BOUNDARIES[category]}第一階段範圍聚焦於受控資料、有限流程與可回溯的試行，不包含未確認的系統整合、自主核准或直接對外執行。前置條件是{_CATEGORY_PREREQUISITES[category]}",
            f"PoC 驗收不以通用宣稱代替實測，而是依推薦方案檢查流程是否可追溯、人工覆核是否確實發生，以及{_target_copy(category)[5]}若資料、責任或驗證條件仍待確認，結果只用來決定下一階段是否補足準備，不把未知內容寫成既有能力。",
        ]
    )


def build_report_synthesis(
    *,
    analysis: ValidatedAnalysisResult,
    facts: Sequence[FactRevision],
    report=None,
    interview_questions: Sequence[InterviewQuestion] = (),
    messages: Sequence[VisibleConversationMessage] = (),
) -> ReportSynthesis:
    """Build one deterministic synthesis shared verbatim by UI and Markdown."""

    del report  # Provider prose is not a source of truth for the final report.
    category, title = _formal_route(analysis)
    options = _option_comparison(analysis, category, title)
    return ReportSynthesis(
        executive_narrative=(
            f"本次評估建議採用「{title}」。{_CATEGORY_BENEFITS[category]}"
            "第一階段將以受控範圍驗證，不把未確認事項視為既有條件。"
        ),
        recommendation_narrative=_recommendation_narrative(
            facts=facts, category=category, title=title, options=options
        ),
        interview_findings=build_interview_findings(
            questions=interview_questions, messages=messages, facts=facts
        ),
        current_target_comparison=_current_target_comparison(analysis, facts, category),
        option_comparison=options,
        comparison_narrative=_comparison_narrative(analysis, facts, options, title),
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
                _joined(item.supporting_cases, empty="目前沒有直接案例支持。"),
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
