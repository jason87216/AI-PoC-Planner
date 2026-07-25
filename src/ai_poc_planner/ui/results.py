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
}


def result_view_for_status(status: object) -> str:
    """Select a result page state only from the durable API status."""

    return _STATUS_VIEWS.get(str(status), "unavailable")


def readable_value(value: object) -> str:
    return _VALUE_LABELS.get(str(value), str(value).replace("_", " ").title())


def _readable_text(value: object) -> str:
    """Hide evidence tokens, which are internal audit references rather than UI text."""

    return re.sub(r"\s*\(?F\d{3}\)?", "", str(value)).strip()


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
