"""Compose the canonical, article-oriented report view model."""

# ruff: noqa: E501

from __future__ import annotations

import json
from collections.abc import Sequence

from ai_poc_planner.domain.analysis import ValidatedAnalysisResult
from ai_poc_planner.domain.discovery import InterviewQuestion
from ai_poc_planner.domain.enums import FactStatus
from ai_poc_planner.domain.planning_report import (
    CaseComparison,
    CurrentTargetComparison,
    GateAppendixRow,
    GateBoundarySummary,
    InterviewFinding,
    OptionComparison,
    ReportAppendix,
    ReportSynthesis,
    RoadmapPhase,
    SafeInterviewQuestionAnswer,
    ScoreAppendixRow,
)
from ai_poc_planner.domain.project_history import (
    FactRevision,
    VisibleConversationMessage,
)

_FACT_LABELS = {
    "current_workflow_problem": "目前流程",
    "desired_outcome": "期望成果",
    "available_data": "可用資料",
    "users_and_owners": "使用者與負責人",
    "known_constraints": "已知限制",
    "human_final_decision": "人工最終決策",
    "processing_boundary": "資料處理邊界",
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
_REFERENCE_LABELS = {
    "high": "高參考價值，但專案環境差異大",
    "medium": "中度適配，可移植部分流程",
    "low": "低適配，只能作為方向性參考",
    "unknown": "證據不足，不作正式案例依據",
}
_CATEGORY_COPY = {
    "ai_hybrid": "可採用 AI 輔助，但以檢索、草稿或建議為主，保留人工最終決策。",
    "rules_first": "規則與表單驗證是推薦方案，生成式 AI 不是主要方案。",
    "governed_assistive": "先在治理限制下提供人工輔助，不自動核准或執行高風險動作。",
    "readiness_first": "先建立資料、標籤與驗證基礎，不承諾模型準確率或 PoC 成功。",
}


def _display_value(value: object) -> str:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def _unique(values: Sequence[str], *, empty: str = "目前未記錄。") -> list[str]:
    result = list(dict.fromkeys(item.strip() for item in values if item.strip()))
    return result or [empty]


def _fact_display(fact: FactRevision | None) -> str:
    if fact is None:
        return "尚未記錄。"
    if fact.status is FactStatus.CONFIRMED:
        return _display_value(fact.value)
    if fact.status is FactStatus.UNKNOWN:
        return "尚未確認。"
    if fact.status is FactStatus.MISSING:
        return "尚未提供。"
    return f"待核實假設：{_display_value(fact.value)}"


def _fact_map(facts: Sequence[FactRevision]) -> dict[str, FactRevision]:
    return {fact.fact_key.strip().casefold(): fact for fact in facts}


def build_interview_findings(
    *,
    questions: Sequence[InterviewQuestion],
    messages: Sequence[VisibleConversationMessage],
    facts: Sequence[FactRevision],
) -> tuple[list[InterviewFinding], list[SafeInterviewQuestionAnswer]]:
    """Build safe findings from durable question and visible answer records."""

    answers = {str(message.id): message.content for message in messages}
    fact_by_key = _fact_map(facts)
    findings: list[InterviewFinding] = []
    appendix: list[SafeInterviewQuestionAnswer] = []
    for question in sorted(
        questions, key=lambda item: (item.round_number, item.position)
    ):
        answer = answers.get(str(question.answer_message_id), "尚未提供回答。")
        topic = _FACT_LABELS.get(
            question.fact_key.strip().casefold(),
            question.fact_key.replace("_", " ").strip().capitalize(),
        )
        findings.append(
            InterviewFinding(
                topic=topic,
                initial_understanding=_fact_display(
                    fact_by_key.get(question.fact_key.strip().casefold())
                ),
                clarification=answer,
                assessment_impact=question.affected_judgement,
                source_question=question.question,
                answer_summary=answer,
            )
        )
        appendix.append(
            SafeInterviewQuestionAnswer(
                question=question.question,
                why_it_matters=question.why_it_matters,
                user_answer=answer,
                assessment_impact=question.affected_judgement,
            )
        )
    return findings, appendix


def _formal_route(analysis: ValidatedAnalysisResult) -> tuple[str, str]:
    if analysis.case_centered is not None:
        result = analysis.case_centered
        return result.recommendation_category.value, result.recommendation_title
    option = next(
        item
        for item in analysis.options
        if item.option_key == analysis.recommended_option_key
    )
    return analysis.conclusion.value, option.title


def _formal_option(category: str, title: str) -> OptionComparison:
    details = {
        "ai_hybrid": (
            title,
            "需求涉及知識整理或建議，但仍需用人工覆核控制對外或高影響動作。",
            ["縮短查找或整理時間", "保留人工確認與例外處理"],
            ["案例與本專案環境有差異", "需要代表性資料與驗收設計"],
            ["確認人工責任邊界", "建立可追溯的驗證資料"],
        ),
        "rules_first": (
            "規則與表單驗證",
            "規則明確、輸入結構固定，先用 deterministic 規則處理最直接。",
            ["規則命中結果容易驗證", "降低漏填與超限檢查負擔"],
            ["複雜例外仍需人工判斷", "非結構化附件可留待後續探索"],
            ["整理規則與例外", "確認表單欄位與財務責任"],
        ),
        "governed_assistive": (
            "治理下人工輔助",
            "存在高影響權限或個資處理邊界，先標準化流程並由主管最終核准。",
            ["減少漏項與格式差異", "保留人工核准與 audit trail"],
            ["不得自動核准或開通高風險權限", "未核准資料不得送外部模型"],
            ["建立職位—權限範本", "完成治理、資安與資料處理審查"],
        ),
        "readiness_first": (
            "資料與驗證基礎建設",
            "目前資料、標籤或驗證集不足，先建立資料與判定基準才可評估模型。",
            ["讓後續 PoC 有可驗證的資料基礎", "先確認問題是否可被可靠評估"],
            ["不能承諾準確率或 PoC 成功", "目前不進入生產部署"],
            ["建立標籤規則", "收集代表性樣本並留出驗證集"],
        ),
    }
    option, reason, benefits, risks, prerequisites = details.get(
        category,
        (title, "依正式評估結果保留保守實施範圍。", [], [], []),
    )
    return OptionComparison(
        option=option,
        suitable_reason=reason,
        benefits=benefits,
        limitations_risks=risks,
        prerequisites=prerequisites,
        conclusion="正式推薦方案",
        recommended=True,
    )


def _option_comparison(
    analysis: ValidatedAnalysisResult, category: str, title: str
) -> list[OptionComparison]:
    rows = [_formal_option(category, title)]
    for option in analysis.options:
        if option.option_key == analysis.recommended_option_key:
            continue
        rows.append(
            OptionComparison(
                option=option.title,
                suitable_reason=option.summary,
                benefits=list(option.expected_benefits),
                limitations_risks=[*option.limitations, *option.risks],
                prerequisites=list(option.prerequisites),
                conclusion="候選方向，須符合正式路徑與人工邊界。",
            )
        )
    return rows


def _case_comparison(analysis: ValidatedAnalysisResult) -> list[CaseComparison]:
    result = analysis.case_centered
    if result is None:
        return []
    practices = {
        case_id: practice
        for practice in result.transferable_practices
        for case_id in practice.source_case_ids
    }
    rows: list[CaseComparison] = []
    for match in result.matched_cases:
        case = match.case
        practice = practices.get(case.case_id)
        rows.append(
            CaseComparison(
                display_title_zh=case.display_title_zh or f"{case.organization} 案例",
                original_title=case.title,
                organization=case.organization,
                why_relevant=(
                    case.summary_zh
                    or "；".join(match.project_fit.similarities)
                    or case.business_problem
                ),
                transferable_practice=(
                    practice.transferable_part
                    if practice is not None
                    else case.solution_pattern or case.implementation_method
                ),
                cannot_copy=_unique(
                    [
                        *match.project_fit.key_differences,
                        *match.gaps.not_directly_transferable,
                    ]
                ),
                adaptation_conclusion=_REFERENCE_LABELS.get(
                    match.reference_value.level.value,
                    "證據不足，不作正式案例依據",
                ),
            )
        )
    return rows


def _current_target_comparison(
    analysis: ValidatedAnalysisResult, facts: Sequence[FactRevision]
) -> list[CurrentTargetComparison]:
    fact_by_key = _fact_map(facts)
    result = analysis.case_centered
    phases = result.phased_path if result is not None else ()
    first = phases[0] if phases else None
    second = phases[1] if len(phases) > 1 else first
    gates = result.gate_impacts if result is not None else ()
    limits = [item for gate in gates for item in gate.limits]
    releases = [item for gate in gates for item in gate.release_conditions]
    unknowns = [
        _FACT_LABELS.get(fact.fact_key, "資料")
        for fact in facts
        if fact.status in {FactStatus.UNKNOWN, FactStatus.MISSING}
    ]
    rows = [
        (
            "流程",
            _fact_display(fact_by_key.get("current_workflow_problem")),
            "；".join(first.actions) if first else analysis.requirement_summary,
            "；".join(analysis.unresolved_gaps) or "需要轉成可驗收的有限範圍。",
            "先確認責任邊界，再依第一階段路線驗證。",
        ),
        (
            "人工責任",
            _fact_display(fact_by_key.get("users_and_owners")),
            first.human_decision_boundary if first else "人工保留最終決策。",
            "；".join(limits) or "例外與最終決策責任需要明確記錄。",
            "把人工覆核點列入流程與驗收紀錄。",
        ),
        (
            "資料",
            _fact_display(fact_by_key.get("available_data")),
            "；".join(first.inputs) if first else "建立可驗證的資料輸入。",
            "；".join(unknowns) or "仍需確認資料代表性與驗證方式。",
            "先整理資料樣本、標籤與驗證集。",
        ),
        (
            "系統／部署",
            _fact_display(fact_by_key.get("processing_boundary"))
            + "；"
            + _fact_display(fact_by_key.get("known_constraints")),
            "；".join(second.not_doing) if second else "只在核准環境內進行。",
            "；".join(limits) or "部署邊界與系統依賴尚需確認。",
            "先限於脫敏或核准環境，不直接寫入真實企業系統。",
        ),
        (
            "治理",
            _fact_display(fact_by_key.get("known_constraints")),
            "；".join(releases) or "由人工 reviewer 依條件審查。",
            "；".join(limits) or "治理控制與 audit trail 仍需落實。",
            "完成必要的資安、治理與資料處理審查。",
        ),
        (
            "驗收方式",
            _fact_display(fact_by_key.get("desired_outcome")),
            "；".join(first.acceptance_criteria) if first else "建立代表性驗證條件。",
            "；".join(unknowns) or "驗收條件需要與人工責任和資料品質連結。",
            "以流程指標、人工覆核結果與可追溯紀錄驗收。",
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


def _roadmap(analysis: ValidatedAnalysisResult) -> list[RoadmapPhase]:
    if analysis.case_centered is not None:
        return [
            RoadmapPhase(
                phase=phase.phase_name,
                description=phase.description,
                actions=list(phase.actions),
                inputs=list(phase.inputs),
                outputs=list(phase.outputs),
                human_decision_boundary=phase.human_decision_boundary,
                not_doing=list(phase.not_doing),
                remaining_gaps=list(phase.remaining_gaps),
                acceptance_criteria=list(phase.acceptance_criteria),
            )
            for phase in analysis.case_centered.phased_path
        ]
    return [
        RoadmapPhase(
            phase="第一階段 PoC",
            description="以有限範圍驗證需求、資料與人工責任。",
            actions=["確認流程範圍", "建立驗證資料"],
            inputs=["已確認需求", "核准資料"],
            outputs=["可追蹤的輔助結果"],
            human_decision_boundary="人工保留最終決策。",
            not_doing=["不自主執行高風險動作"],
            remaining_gaps=list(analysis.unresolved_gaps),
            acceptance_criteria=["所有例外可回到人工處理。"],
        )
    ]


def _appendix(
    analysis: ValidatedAnalysisResult,
    facts: Sequence[FactRevision],
    interview_qa: list[SafeInterviewQuestionAnswer],
) -> ReportAppendix:
    scores = [
        ScoreAppendixRow(
            dimension=_SCORE_LABELS.get(score.dimension.value, score.dimension.value),
            judgement=f"{score.rating}/5；加權點數 {score.weighted_points}",
            main_basis=score.rationale,
            improvement_condition="；".join(score.improvement_conditions)
            or "依後續驗證結果更新。",
        )
        for score in analysis.scores
    ]
    if analysis.case_centered is not None:
        gates = [
            GateAppendixRow(
                gate_id=gate.rule_id,
                limit_content="；".join(gate.limits),
                affected_stage=gate.affected_stage,
                currently_possible="；".join(gate.does_not_limit),
                release_condition="；".join(gate.release_conditions)
                or "重新完成 gate 審查。",
            )
            for gate in analysis.case_centered.gate_impacts
        ]
    else:
        gates = [
            GateAppendixRow(
                gate_id=gate.rule_id,
                limit_content=gate.reason,
                affected_stage=gate.affected_stage,
                currently_possible="；".join(gate.does_not_limit),
                release_condition="；".join(gate.release_conditions)
                or "重新完成 gate 審查。",
            )
            for gate in analysis.gate_results
        ]
    evidence = [
        f"{_FACT_LABELS.get(fact.fact_key, '需求資料')}：{_fact_display(fact)}"
        for fact in facts
    ]
    return ReportAppendix(
        scores=scores,
        hard_gates=gates,
        safe_interview_qa=interview_qa,
        evidence_basis=evidence,
    )


def _hard_gate_summary(analysis: ValidatedAnalysisResult) -> list[GateBoundarySummary]:
    """Project deterministic gate impacts into the report's human-facing layer."""

    if analysis.case_centered is not None:
        return [
            GateBoundarySummary(
                limit_content="；".join(gate.limits),
                affected_stage=gate.affected_stage,
                currently_possible="；".join(gate.does_not_limit),
                release_condition="；".join(gate.release_conditions)
                or "重新完成 gate 審查。",
            )
            for gate in analysis.case_centered.gate_impacts
        ]
    return [
        GateBoundarySummary(
            limit_content=gate.reason,
            affected_stage=gate.affected_stage,
            currently_possible="；".join(gate.does_not_limit),
            release_condition="；".join(gate.release_conditions)
            or "重新完成 gate 審查。",
        )
        for gate in analysis.gate_results
    ]


def build_report_synthesis(
    *,
    analysis: ValidatedAnalysisResult,
    facts: Sequence[FactRevision],
    report=None,
    interview_questions: Sequence[InterviewQuestion] = (),
    messages: Sequence[VisibleConversationMessage] = (),
) -> ReportSynthesis:
    """Build one deterministic, readable result model for UI and Markdown."""

    category, title = _formal_route(analysis)
    findings, interview_qa = build_interview_findings(
        questions=interview_questions,
        messages=messages,
        facts=facts,
    )
    route_copy = _CATEGORY_COPY.get(category, "依正式評估結果保留保守實施範圍。")
    confirmed = [
        f"{_FACT_LABELS.get(fact.fact_key, '需求資料')}：{_fact_display(fact)}"
        for fact in facts
        if fact.status is FactStatus.CONFIRMED
    ]
    uncertain = [
        _FACT_LABELS.get(fact.fact_key, "資料")
        for fact in facts
        if fact.status in {FactStatus.UNKNOWN, FactStatus.MISSING}
    ]
    provider_section = getattr(report, "executive_summary", None)
    provider_summary = getattr(provider_section, "content", "")
    if "模型文字說明暫時不可用" in provider_summary:
        provider_summary = ""
    context = "目前已確認：" + "；".join(confirmed or ["尚未記錄足夠需求資料。"])
    if uncertain:
        context += "。仍有未確認資訊：" + "、".join(dict.fromkeys(uncertain)) + "。"
    executive = f"本次評估結論是「{title}」。{route_copy}"
    if provider_summary:
        executive += f"補充說明：{provider_summary}"
    recommendation = f"正式推薦「{title}」。{route_copy}"
    if analysis.case_centered is not None and analysis.case_centered.gate_impacts:
        recommendation += (
            "目前 gate 只限制受控範圍與自動化程度，不代表所有準備工作都不能進行。"
        )
    if analysis.case_centered is not None:
        risk_summary = "；".join(
            f"{gate.affected_stage}：{'；'.join(gate.limits)}"
            for gate in analysis.case_centered.gate_impacts
        )
    else:
        risk_summary = ""
    risk_summary = risk_summary or "目前沒有額外 hard gate；仍保留人工最終決策。"
    if uncertain:
        risk_summary += "尚未確認的資料不視為已通過，需在後續階段補足。"
    roadmap = _roadmap(analysis)
    next_actions = _unique(
        [*roadmap[0].actions, *roadmap[0].remaining_gaps, *analysis.unresolved_gaps],
        empty="依第一階段驗收結果重新判定下一步。",
    )
    return ReportSynthesis(
        executive_narrative=executive,
        project_context_narrative=context,
        interview_findings=findings,
        current_target_comparison=_current_target_comparison(analysis, facts),
        option_comparison=_option_comparison(analysis, category, title),
        case_comparison=_case_comparison(analysis),
        recommendation_narrative=recommendation,
        implementation_roadmap=roadmap,
        hard_gate_summary=_hard_gate_summary(analysis),
        risk_and_boundary_summary=risk_summary,
        next_actions=next_actions,
        appendix=_appendix(analysis, facts, interview_qa),
    )


def _cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ").strip()


def _joined(values: Sequence[str], *, empty: str = "目前未記錄。") -> str:
    return "；".join(values) if values else empty


def render_synthesis_markdown(synthesis: ReportSynthesis) -> str:
    """Render the exact synthesis object used by the API response."""

    lines = [
        "# 專案評估報告",
        "",
        "## 1. 專案評估摘要",
        "",
        synthesis.executive_narrative,
        "",
        "## 2. 需求與訪談發現",
        "",
        synthesis.project_context_narrative,
    ]
    if synthesis.interview_findings:
        lines.extend(
            ["", "| 主題 | 初始理解 | 追問後澄清 | 對評估的影響 |", "|---|---|---|---|"]
        )
        lines.extend(
            "| "
            + " | ".join(
                _cell(getattr(item, field))
                for field in (
                    "topic",
                    "initial_understanding",
                    "clarification",
                    "assessment_impact",
                )
            )
            + " |"
            for item in synthesis.interview_findings
        )
    else:
        lines.extend(["", "目前沒有可安全呈現的追問紀錄。"])
    lines.extend(
        [
            "",
            "## 3. 目前狀態與目標狀態",
            "",
            "| 面向 | 目前狀態 | 目標狀態 | 主要差距 | 處理方式 |",
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
            "## 4. 候選方案比較",
            "",
            "| 方案 | 適合原因 | 效益 | 限制／風險 | 前置條件 | 結論 |",
            "|---|---|---|---|---|---|",
        ]
    )
    lines.extend(
        "| "
        + " | ".join(
            _cell(value)
            for value in (
                ("正式推薦：" if item.recommended else "") + item.option,
                item.suitable_reason,
                _joined(item.benefits),
                _joined(item.limitations_risks),
                _joined(item.prerequisites),
                item.conclusion,
            )
        )
        + " |"
        for item in synthesis.option_comparison
    )
    lines.extend(["", "## 5. 成熟案例橫向比較", ""])
    if synthesis.case_comparison:
        lines.extend(
            [
                "| 中文案例名稱 | 原始英文名稱 | 組織 | 為什麼相關 | 可移植做法 | 不能直接複製 | 專案適配結論 |",
                "|---|---|---|---|---|---|---|",
            ]
        )
        lines.extend(
            "| "
            + " | ".join(
                _cell(value)
                for value in (
                    item.display_title_zh,
                    item.original_title,
                    item.organization,
                    item.why_relevant,
                    item.transferable_practice,
                    _joined(item.cannot_copy),
                    item.adaptation_conclusion,
                )
            )
            + " |"
            for item in synthesis.case_comparison
        )
    else:
        lines.append("目前沒有足夠成熟案例作為正式案例依據。")
    lines.extend(
        [
            "",
            "## 6. 推薦方案與理由",
            "",
            synthesis.recommendation_narrative,
            "",
            "## 7. 分階段實施路線",
            "",
        ]
    )
    for phase in synthesis.implementation_roadmap:
        lines.extend(
            [
                f"### {phase.phase}",
                "",
                phase.description,
                f"- 行動：{_joined(phase.actions)}",
                f"- 輸入：{_joined(phase.inputs)}",
                f"- 輸出：{_joined(phase.outputs)}",
                f"- 人工決策邊界：{phase.human_decision_boundary}",
                f"- 不做：{_joined(phase.not_doing)}",
                f"- 尚存差距：{_joined(phase.remaining_gaps)}",
                f"- 驗收條件：{_joined(phase.acceptance_criteria)}",
                "",
            ]
        )
    lines.extend(
        [
            "## 8. 風險、人工邊界與暫不實施事項",
            "",
            synthesis.risk_and_boundary_summary,
            "",
        ]
    )
    if synthesis.hard_gate_summary:
        lines.extend(
            [
                "| 限制內容 | 影響階段 | 目前可做事項 | 解除條件 |",
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
            for item in synthesis.hard_gate_summary
        )
        lines.append("")
    lines.extend(["## 9. 下一步", ""])
    lines.extend(f"- {item}" for item in synthesis.next_actions)
    lines.extend(["", "## 10. 評估依據附錄", "", "### 六維評分"])
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
    lines.extend(["", "### Hard gate 明細"])
    if synthesis.appendix.hard_gates:
        lines.extend(
            [
                "",
                "| 編號 | 限制內容 | 影響階段 | 目前可做事項 | 解除條件 |",
                "|---|---|---|---|---|",
            ]
        )
        lines.extend(
            "| "
            + " | ".join(
                _cell(getattr(item, field))
                for field in (
                    "gate_id",
                    "limit_content",
                    "affected_stage",
                    "currently_possible",
                    "release_condition",
                )
            )
            + " |"
            for item in synthesis.appendix.hard_gates
        )
    lines.extend(["", "### 安全化原始問答"])
    if synthesis.appendix.safe_interview_qa:
        lines.extend(
            [
                "",
                "| 問題 | 為什麼重要 | 使用者回答 | 影響的評估判斷 |",
                "|---|---|---|---|",
            ]
        )
        lines.extend(
            "| "
            + " | ".join(
                _cell(getattr(item, field))
                for field in (
                    "question",
                    "why_it_matters",
                    "user_answer",
                    "assessment_impact",
                )
            )
            + " |"
            for item in synthesis.appendix.safe_interview_qa
        )
    lines.extend(["", "### 證據依據"])
    lines.extend(f"- {item}" for item in synthesis.appendix.evidence_basis)
    return "\n".join(lines).rstrip() + "\n"
