"""Pure, user-facing presentation helpers for persisted assessment results."""

from __future__ import annotations

import re
from typing import Any

_STATUS_VIEWS = {
    "ready_for_assessment": "ready",
    "assessed": "assessed",
    "complete": "complete",
}

_REPORT_LABELS = {
    "executive_summary": "執行摘要",
    "requirement_understanding": "需求理解",
    "current_process_and_pain_points": "目前流程與痛點",
    "goals_and_proposed_success_criteria": "目標與建議成功標準",
    "ai_suitability_explanation": "AI 適用性說明",
    "recommended_direction_explanation": "建議方向說明",
    "alternatives_explanation": "替代方向說明",
    "target_workflow": "目標工作流程",
    "data_needs_and_gaps": "資料需求與缺口",
    "deployment_comparison": "部署方式比較",
    "poc_scope": "PoC 範圍",
    "in_scope": "納入範圍",
    "out_of_scope": "不納入範圍",
    "kpi_and_acceptance_method": "KPI 與驗收方式",
    "cost_assumptions": "成本假設",
    "implementation_stages_and_roles": "實作階段與角色",
    "risks_governance_and_human_review": "風險、治理與人工覆核",
    "open_issues_and_next_actions": "待釐清事項與下一步",
}

_VALUE_LABELS = {
    "suitable_for_ai": "適合採用 AI",
    "better_suited_to_non_ai": "較適合非 AI 方案",
    "establish_non_ai_foundations_before_ai": "先建立非 AI 基礎，再評估 AI",
    "hybrid_ai_and_non_ai": "AI 與非 AI 的混合方案",
    "proceed": "建議進行",
    "conditional_proceed": "符合條件後可進行",
    "do_not_proceed": "暫不建議進行",
    "pass": "通過",
    "fail": "未通過",
    "review_required": "需要人工覆核",
    "yes": "是",
    "no": "否",
    "unknown": "尚不清楚",
    "human_final_decision": "由人員做最終決策",
    "assistive_only": "僅提供輔助",
    "autonomous_action": "可自主執行",
    "local_only": "僅限本機環境",
    "private_endpoint": "受控私有端點",
    "external_endpoint": "外部受控端點",
    "requires_controls": "需要控制措施",
    "blocked": "不建議進入下一步",
    "required": "需要人工覆核",
    "not_required": "不需要額外人工覆核",
    "business_value": "商業價值",
    "data_readiness": "資料就緒度",
    "technical_fit": "技術適配性",
    "architecture_controllability": "架構可控性",
    "governance_readiness": "治理就緒度",
    "user_adoption": "使用者採用度",
    "matched": "已匹配",
    "no_suitable_reviewed_case": "沒有足夠成熟案例",
    "ai_hybrid": "AI 與人工輔助混合路線",
    "rules_first": "規則與流程標準化優先",
    "governed_assistive": "治理限制下的人工輔助",
    "readiness_first": "資料基礎建設優先",
}

_TEXT_REPLACEMENTS = {
    "autonomous_action": "不得自主執行高風險動作",
    "assistive_only": "僅限人工輔助",
    (
        "required authorization, lawful basis, or accountable ownership "
        "is absent, or the use is prohibited."
    ): ("授權、合法依據或可追責負責人尚未確認，或目前用途受到禁止。"),
    (
        "Required authorization, lawful basis, or accountable ownership "
        "is absent, or the use is prohibited."
    ): ("授權、合法依據或可追責負責人尚未確認，或目前用途受到禁止。"),
    (
        "A high-impact final decision cannot be autonomous or lack "
        "meaningful human review."
    ): ("高影響決策不得自主執行，也不得缺少有實質意義的人工覆核。"),
    (
        "One or more mandatory data, security, governance, or audit "
        "controls are missing."
    ): ("必要的資料、安全、治理或稽核控制措施仍有缺口。"),
    "Data is unavailable, mostly non-digital, or lacks a validation sample.": (
        "資料尚未提供、主要仍是非數位格式，或缺少驗證樣本。"
    ),
    "obtain documented authorization and lawful basis": "取得書面授權與合法依據",
    "assign an accountable owner": "指定可追責的負責人",
    "remove autonomous final decisions and enterprise actions": (
        "移除自主最終決策與企業系統執行"
    ),
    "complete qualified professional review": "完成合格專業人工覆核",
    "remove autonomous final-decision authority": "移除自主最終決策權限",
    "require a qualified human final decision": "要求合格人員做最終決策",
    "use an approved local or private endpoint": "使用核准的本機或私有端點",
    "define data minimization": "定義資料最小化措施",
    "define retention and deletion controls": "定義保存與刪除控制措施",
    "enforce least-privilege access control": "強制執行最小權限存取控制",
    "approve required security controls": "核准必要的安全控制措施",
    "approve required governance controls": "核准必要的治理控制措施",
    "enable required audit controls": "啟用必要的稽核控制措施",
    "make required data available": "提供必要資料",
    "digitize or OCR source material": "將來源資料數位化或進行 OCR 擷取",
    "create a representative validation sample": "建立具代表性的驗證樣本",
    "required controls": "必要控制措施",
    "opportunity": "機會類型",
}


def result_view_for_status(status: object) -> str:
    """Select a result page state only from the durable API status."""

    return _STATUS_VIEWS.get(str(status), "unavailable")


def readable_value(value: object) -> str:
    return _VALUE_LABELS.get(str(value), str(value).replace("_", " ").title())


def _readable_text(value: object) -> str:
    """Hide evidence tokens, which are internal audit references rather than UI text."""

    text = re.sub(r"\s*\(?F\d{3}\)?", "", str(value)).strip()
    for source, target in _TEXT_REPLACEMENTS.items():
        text = text.replace(source, target)
    return text


def _readable_items(value: object) -> list[str]:
    return [_readable_text(item) for item in value] if isinstance(value, list) else []


def report_sections(report: dict[str, Any]) -> list[dict[str, str]]:
    """Return persisted report narration in its contract-defined order."""

    draft = report.get("report")
    if not isinstance(draft, dict):
        return []
    return [
        {"title": label, "content": _readable_text(section.get("content", ""))}
        for key, label in _REPORT_LABELS.items()
        if isinstance(section := draft.get(key), dict)
    ]


def report_synthesis_view(report: dict[str, Any]) -> dict[str, Any]:
    """Project the persisted canonical synthesis into safe UI fields only."""

    synthesis = report.get("synthesis")
    if not isinstance(synthesis, dict) or synthesis.get("schema_version") != "2.1":
        return {}

    def rows(
        key: str, fields: tuple[str, ...], source: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        values = (source or synthesis).get(key)
        if not isinstance(values, list):
            return []
        result: list[dict[str, Any]] = []
        for value in values:
            if not isinstance(value, dict):
                continue
            result.append(
                {
                    field: (
                        bool(value.get(field, False))
                        if field == "recommended"
                        else (
                            _readable_items(value.get(field, []))
                            if field
                            in {
                                "supporting_cases",
                                "cannot_copy",
                                "actions",
                                "outputs",
                                "acceptance_criteria",
                            }
                            else _readable_text(value.get(field, ""))
                        )
                    )
                    for field in fields
                }
            )
        return result

    appendix = synthesis.get("appendix")
    if not isinstance(appendix, dict):
        appendix = {}
    return {
        "executive_narrative": _readable_text(synthesis.get("executive_narrative", "")),
        "recommendation_narrative": _readable_text(
            synthesis.get("recommendation_narrative", "")
        ),
        "interview_findings": rows(
            "interview_findings",
            (
                "topic",
                "confirmed_content",
                "assessment_impact",
            ),
        ),
        "comparison_narrative": _readable_text(
            synthesis.get("comparison_narrative", "")
        ),
        "current_target_comparison": rows(
            "current_target_comparison",
            ("aspect", "current_state", "target_state", "main_gap", "treatment"),
        ),
        "option_comparison": rows(
            "option_comparison",
            (
                "option",
                "positioning",
                "supporting_cases",
                "case_evidence",
                "transferable_practice",
                "cannot_copy",
                "conclusion",
                "recommended",
            ),
        ),
        "implementation_roadmap": rows(
            "implementation_roadmap",
            (
                "phase",
                "actions",
                "outputs",
                "human_decision_boundary",
                "acceptance_criteria",
            ),
        ),
        "major_risks_and_boundaries": _readable_items(
            synthesis.get("major_risks_and_boundaries", [])
        ),
        "appendix": {
            "scores": rows(
                "scores",
                ("dimension", "judgement", "main_basis", "improvement_condition"),
                appendix,
            )
            if isinstance(appendix.get("scores"), list)
            else [],
            "hard_gates": rows(
                "hard_gates",
                (
                    "limit_content",
                    "affected_stage",
                    "currently_possible",
                    "release_condition",
                ),
                appendix,
            )
            if isinstance(appendix.get("hard_gates"), list)
            else [],
        },
    }


def analysis_overview(analysis: dict[str, Any]) -> dict[str, Any]:
    """Keep only the business-readable assessment data for rendering."""

    return {
        "requirement_summary": _readable_text(analysis.get("requirement_summary", "")),
        "conclusion": readable_value(analysis.get("conclusion", "")),
        "conclusion_rationale": _readable_text(
            analysis.get("conclusion_rationale", "")
        ),
        "weighted_total": analysis.get("weighted_total", "—"),
        "gate_disposition": readable_value(analysis.get("gate_disposition", "")),
        "options": [
            {
                "title": option.get("title", "未命名方向"),
                "summary": _readable_text(option.get("summary", "")),
                "benefits": _readable_items(option.get("expected_benefits", [])),
                "limitations": _readable_items(option.get("limitations", [])),
                "prerequisites": _readable_items(option.get("prerequisites", [])),
                "risks": _readable_items(option.get("risks", [])),
                "decision_authority": readable_value(
                    option.get("decision_authority", "")
                ),
                "processing_boundary": readable_value(
                    option.get("processing_boundary", "")
                ),
                "human_review": _readable_items(option.get("human_review_points", [])),
                "recommended": option.get("option_key")
                == analysis.get("recommended_option_key"),
            }
            for option in analysis.get("options", [])
            if isinstance(option, dict)
        ],
        "scores": [
            {
                "dimension": readable_value(score.get("dimension", "")),
                "rating": score.get("rating", "—"),
                "weight": score.get("weight", "—"),
                "weighted_points": score.get("weighted_points", "—"),
                "rationale": _readable_text(score.get("rationale", "")),
                "data_gaps": _readable_items(score.get("data_gaps", [])),
                "risks": _readable_items(score.get("risks", [])),
                "improvement_conditions": _readable_items(
                    score.get("improvement_conditions", [])
                ),
            }
            for score in analysis.get("scores", [])
            if isinstance(score, dict)
        ],
        "gates": [
            {
                "disposition": readable_value(gate.get("disposition", "")),
                "reason": _readable_text(gate.get("reason", "")),
                "required_controls": _readable_items(gate.get("required_controls", [])),
                "human_review_required": readable_value(
                    gate.get("human_review_required", "")
                ),
            }
            for gate in analysis.get("gate_results", [])
            if isinstance(gate, dict)
        ],
        "overall_risks": _readable_items(analysis.get("overall_risks", [])),
        "unresolved_gaps": _readable_items(analysis.get("unresolved_gaps", [])),
        "case_centered": case_centered_overview(analysis),
    }


def case_centered_overview(analysis: dict[str, Any]) -> dict[str, Any]:
    """Expose only business-readable fields from the canonical result."""

    result = analysis.get("case_centered")
    if not isinstance(result, dict):
        return {}
    cases: list[dict[str, Any]] = []
    for match in result.get("matched_cases", []):
        if not isinstance(match, dict) or not isinstance(match.get("case"), dict):
            continue
        case = match["case"]
        reference = match.get("reference_value", {})
        fit = match.get("project_fit", {})
        gaps = match.get("gaps", {})
        cases.append(
            {
                "title": case.get("title", "未命名案例"),
                "organization": case.get("organization", "未記錄"),
                "reference_level": readable_value(reference.get("level", "")),
                "reference_score": reference.get("score"),
                "reference_basis": _readable_items(reference.get("basis", [])),
                "reference_unknown": _readable_items(
                    reference.get("unknown_items", [])
                ),
                "fit_level": readable_value(fit.get("level", "")),
                "fit_score": fit.get("score"),
                "similarities": _readable_items(fit.get("similarities", [])),
                "differences": _readable_items(fit.get("key_differences", [])),
                "needs_confirmation": _readable_items(
                    fit.get("needs_confirmation", [])
                ),
                "ready_conditions": _readable_items(gaps.get("ready_conditions", [])),
                "missing_conditions": _readable_items(
                    gaps.get("missing_conditions", [])
                ),
                "not_directly_transferable": _readable_items(
                    gaps.get("not_directly_transferable", [])
                ),
                "gap_confirmation": _readable_items(gaps.get("needs_confirmation", [])),
                "sources": [
                    {
                        "label": source.get("label", "來源"),
                        "url": source.get("url", ""),
                    }
                    for source in case.get("source_references", [])
                    if isinstance(source, dict)
                ],
            }
        )
    practices = [
        {
            "name": item.get("name", "未命名做法"),
            "source_case_titles": _readable_items(item.get("source_case_titles", [])),
            "case_evidence": _readable_text(item.get("case_evidence", "")),
            "transferable_part": _readable_text(item.get("transferable_part", "")),
            "required_adjustments": _readable_items(
                item.get("required_adjustments", [])
            ),
            "current_stage": _readable_text(item.get("current_stage", "")),
            "prerequisites": _readable_items(item.get("prerequisites", [])),
            "not_applicable_scope": _readable_items(
                item.get("not_applicable_scope", [])
            ),
        }
        for item in result.get("transferable_practices", [])
        if isinstance(item, dict)
    ]
    gates = [
        {
            "disposition": readable_value(item.get("disposition", "")),
            "affected_stage": _readable_text(item.get("affected_stage", "")),
            "limits": _readable_items(item.get("limits", [])),
            "does_not_limit": _readable_items(item.get("does_not_limit", [])),
            "release_conditions": _readable_items(item.get("release_conditions", [])),
        }
        for item in result.get("gate_impacts", [])
        if isinstance(item, dict)
    ]
    phases = [
        {
            key: _readable_items(item.get(key, []))
            if key
            in {
                "actions",
                "inputs",
                "outputs",
                "users",
                "not_doing",
                "remaining_gaps",
                "acceptance_criteria",
            }
            else _readable_text(item.get(key, ""))
            for key in (
                "phase_name",
                "description",
                "actions",
                "inputs",
                "outputs",
                "users",
                "human_decision_boundary",
                "not_doing",
                "remaining_gaps",
                "acceptance_criteria",
            )
        }
        for item in result.get("phased_path", [])
        if isinstance(item, dict)
    ]
    return {
        "matching_status": readable_value(result.get("matching_status", "")),
        "no_case_reason": _readable_text(result.get("no_case_reason", "")),
        "recommendation_title": _readable_text(result.get("recommendation_title", "")),
        "recommendation_category": readable_value(
            result.get("recommendation_category", "")
        ),
        "recommendation_basis": _readable_items(result.get("recommendation_basis", [])),
        "cases": cases,
        "practices": practices,
        "gates": gates,
        "phases": phases,
    }


def reviewed_case_sources(markdown: str) -> list[dict[str, str]]:
    """Read only the source details persisted in the report Markdown.

    The report contract does not expose a case library separately, so this never
    infers a title, summary, or relevance that is absent from the saved report.
    """

    match = re.search(
        r"^## Relevant Reviewed Cases\s*$\n(?P<cases>.*?)(?=^## |\Z)",
        markdown,
        flags=re.MULTILINE | re.DOTALL,
    )
    if match is None:
        return []
    rows: list[dict[str, str]] = []
    pattern = re.compile(
        r"^- (?P<organization>.+?) \((?P<evidence_grade>[^)]+)\): "
        r"(?P<source_name>.+?) — (?P<source_url>https?://\S+)\s*$"
    )
    for line in match.group("cases").splitlines():
        item = pattern.match(line)
        if item:
            rows.append(item.groupdict())
    return rows


def markdown_download_name(project_name: object, version_number: object) -> str:
    """Create a readable, filesystem-safe name without internal identifiers."""

    words = re.findall(r"[\w-]+", str(project_name), flags=re.UNICODE)
    project_part = "-".join(words) or "plan"
    return f"AI-PoC-Plan-{project_part}-v{version_number}.md"
