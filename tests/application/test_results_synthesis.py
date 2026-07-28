from __future__ import annotations

import re
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from ai_poc_planner.application.planning_report import (
    build_report_synthesis,
    render_synthesis_markdown,
)
from ai_poc_planner.application.report_synthesis import (
    ReportSynthesisError,
    build_interview_findings,
)
from ai_poc_planner.domain.discovery import InterviewQuestion
from ai_poc_planner.domain.enums import InterviewRole, VisibleMessageKind
from ai_poc_planner.domain.project_history import VisibleConversationMessage
from ai_poc_planner.domain.solution_catalog import SolutionPattern
from ai_poc_planner.persistence.catalog_seed import (
    reviewed_cases,
    reviewed_solution_patterns,
)
from tests.application.test_product_acceptance_baselines import (
    _facts,
    _formal_result,
    _scenario,
)


def _synthesis(scenario_id: str):
    scenario = _scenario(scenario_id)
    analysis = _formal_result(scenario)
    solution = next(
        item
        for item in reviewed_solution_patterns()
        if item.solution_key == analysis.case_centered.solution_key
    )
    match_ids = {item.case.case_id for item in analysis.case_centered.matched_cases}
    return build_report_synthesis(
        analysis=analysis,
        facts=list(_facts(scenario)),
        solution=solution,
        reviewed_cases=tuple(
            item for item in reviewed_cases() if item.case_id in match_ids
        ),
        candidate_solutions=reviewed_solution_patterns(),
    )


def _main_report(markdown: str) -> str:
    return markdown.split("## 6. 技術附錄", 1)[0]


def test_interview_findings_are_compact_and_never_expose_raw_questions() -> None:
    scenario = _scenario("knowledge_assist")
    result = _formal_result(scenario)
    now = datetime.now(UTC)
    answer_id = uuid4()
    question = InterviewQuestion(
        id=uuid4(),
        session_id=uuid4(),
        version_id=result.version_id,
        round_number=1,
        position=1,
        visible_message_id=uuid4(),
        fact_key="human_final_decision",
        question="誰保留對外回覆的最終確認權？",
        why_it_matters="這會決定是否能進入自動回覆範圍。",
        affected_judgement="影響人工決策邊界與部署限制。",
        example="例如由客服人員確認後才回覆。",
        answer_message_id=answer_id,
        created_at=now,
        answered_at=now,
    )
    answer = VisibleConversationMessage(
        id=answer_id,
        version_id=result.version_id,
        sequence=2,
        role=InterviewRole.USER,
        message_kind=VisibleMessageKind.ANSWER,
        content="客服人員確認內容後才可回覆客戶。",
        created_at=now,
    )

    synthesis = build_report_synthesis(
        analysis=result,
        facts=list(_facts(scenario)),
        solution=next(
            item
            for item in reviewed_solution_patterns()
            if item.solution_key == result.case_centered.solution_key
        ),
        reviewed_cases=tuple(
            item
            for item in reviewed_cases()
            if item.case_id
            in {case.case.case_id for case in result.case_centered.matched_cases}
        ),
        candidate_solutions=reviewed_solution_patterns(),
        interview_questions=[question],
        messages=[answer],
    )
    markdown = render_synthesis_markdown(synthesis)

    finding = synthesis.interview_findings[0]
    assert finding.topic == "人工最終決策"
    assert finding.confirmed_content == answer.content
    assert finding.assessment_impact == "明確保留人工確認與對外回覆責任。"
    assert "誰保留對外回覆" not in markdown
    assert "初始理解" not in markdown
    assert "追問後澄清" not in markdown
    assert "| 主題 | 已確認內容 | 對方案的影響 |" in markdown

    scope_finding = build_interview_findings(
        questions=[question.model_copy(update={"fact_key": "process_scope"})],
        messages=[answer],
        facts=list(_facts(scenario)),
    )[0]
    assert scope_finding.topic == "第一階段範圍"
    assert scope_finding.assessment_impact == "用來限制第一階段的工作範圍。"


def test_fallback_writes_a_complete_recommendation_article() -> None:
    synthesis = _synthesis("maintenance_coverage_gap")
    markdown = render_synthesis_markdown(synthesis)

    assert len(synthesis.recommendation_narrative) > (
        len(synthesis.executive_narrative) * 3
    )
    assert synthesis.recommendation_narrative.count("\n\n") >= 3
    for phrase in (
        "專案問題",
        "推薦方向",
        "人工責任",
        "第一階段",
        "驗收",
    ):
        assert phrase in synthesis.recommendation_narrative
    assert "## 2. 推薦方案與理由" in markdown


def test_synthesis_uses_reviewed_catalogue_content() -> None:
    result = _formal_result(_scenario("governed_access"))
    solution = SolutionPattern(
        solution_key="permission_request_rules_and_human_approval",
        recommendation_category="governed_assistive",
        display_name_zh="權限申請標準化、規則檢查與人工審批",
        short_description_zh="將申請格式、規則檢查與人工核准串成可追溯流程。",
        detailed_description_zh=(
            "先標準化申請欄位與權限範本，再執行固定規則檢查；"
            "主管保留最終核准，IT 依核准結果開通。"
        ),
        suitable_when_zh="申請格式、核准規則與人工責任可以明確界定時適用。",
        not_suitable_when_zh="規則、權限範本或責任人尚未釐清時，不應直接擴大自動化。",
        typical_scope_zh="先驗證申請表、規則清單、人工核准與稽核紀錄。",
        human_boundary_zh="主管最終核准，IT 依已核准結果開通；系統不得自行核准或開通。",
        expected_outputs_zh="完整申請資料、規則檢查結果、人工核准與可追溯紀錄。",
        acceptance_focus_zh="檢查漏項、規則命中、例外處理與人工覆核紀錄。",
        review_status="approved",
        content_version="test-1",
        created_at="2026-07-28T00:00:00+00:00",
        updated_at="2026-07-28T00:00:00+00:00",
    )

    synthesis = build_report_synthesis(
        analysis=result,
        facts=list(_facts(_scenario("governed_access"))),
        solution=solution,
        reviewed_cases=(),
    )
    markdown = render_synthesis_markdown(synthesis)

    assert synthesis.recommended_solution.display_name_zh == solution.display_name_zh
    assert solution.display_name_zh in markdown
    assert "測試路線 o1" not in markdown
    assert "文件知識檢索與人工審核輔助" not in markdown
    assert "目前沒有足夠相關的已審核成熟案例" in markdown


def test_synthesis_fails_closed_for_solution_mismatch() -> None:
    result = _formal_result(_scenario("governed_access"))
    wrong_solution = next(
        item
        for item in reviewed_solution_patterns()
        if item.recommendation_category == "ai_hybrid"
    )

    with pytest.raises(ReportSynthesisError, match="solution_category_mismatch"):
        build_report_synthesis(
            analysis=result,
            facts=list(_facts(_scenario("governed_access"))),
            solution=wrong_solution,
            reviewed_cases=(),
        )


def test_case_facts_and_source_links_are_verbatim_from_reviewed_catalogue() -> None:
    synthesis = _synthesis("knowledge_assist")
    markdown = render_synthesis_markdown(synthesis)

    assert synthesis.reviewed_cases
    for case in synthesis.reviewed_cases:
        assert case.problem_context_zh in markdown
        assert case.implemented_approach_zh in markdown
        assert case.documented_outcomes_zh in markdown
        assert case.transferable_practices_zh in markdown
        assert case.limitations_zh in markdown
        assert f"[{case.source_name}]({case.source_url})" in markdown


def test_provider_values_cannot_enter_synthesis() -> None:
    result = _formal_result(_scenario("knowledge_assist"))
    mutated_option = result.options[0].model_copy(
        update={"title": "Manual Knowledge Base Consolidation"}
    )
    altered_analysis = result.model_copy(
        update={"options": [mutated_option, *result.options[1:]]}
    )
    solution = next(
        item
        for item in reviewed_solution_patterns()
        if item.solution_key == result.case_centered.solution_key
    )
    cases = tuple(
        item
        for item in reviewed_cases()
        if item.case_id
        in {match.case.case_id for match in result.case_centered.matched_cases}
    )

    markdown = render_synthesis_markdown(
        build_report_synthesis(
            analysis=altered_analysis,
            facts=list(_facts(_scenario("knowledge_assist"))),
            solution=solution,
            reviewed_cases=cases,
            candidate_solutions=reviewed_solution_patterns(),
        )
    )
    assert "Manual Knowledge Base Consolidation" not in markdown

    altered_case = result.case_centered.matched_cases[0].case.model_copy(
        update={"case_summary_zh": "provider 覆寫的案例成果"}
    )
    altered_match = result.case_centered.matched_cases[0].model_copy(
        update={"case": altered_case}
    )
    inconsistent_analysis = result.model_copy(
        update={
            "case_centered": result.case_centered.model_copy(
                update={
                    "matched_cases": [
                        altered_match,
                        *result.case_centered.matched_cases[1:],
                    ]
                }
            )
        }
    )
    with pytest.raises(ReportSynthesisError, match="reviewed_case_mismatch"):
        build_report_synthesis(
            analysis=inconsistent_analysis,
            facts=list(_facts(_scenario("knowledge_assist"))),
            solution=solution,
            reviewed_cases=cases,
        )


def test_comparison_combines_options_cases_and_project_gap_in_one_section() -> None:
    synthesis = _synthesis("knowledge_assist")
    markdown = render_synthesis_markdown(synthesis)

    assert synthesis.comparison_narrative.count("\n\n") >= 2
    assert sum(item.recommended for item in synthesis.option_comparison) == 1
    recommended = next(item for item in synthesis.option_comparison if item.recommended)
    assert recommended.supporting_cases
    assert "Morgan Stanley" in " ".join(recommended.supporting_cases)
    assert all(
        item.supporting_cases or "目前沒有直接案例支持" in item.case_evidence
        for item in synthesis.option_comparison
    )
    assert (
        "| 方案 | 方案定位 | 支持此方案的成熟案例 | 案例能證明什麼 | "
        "可移植到本專案的做法 | 本專案不可直接複製的部分 | 綜合判斷 |"
    ) in markdown
    assert (
        "| 面向 | 目前狀態 | 採用推薦方案後的目標狀態 | 主要差距 | 方案如何處理 |"
    ) in markdown
    assert (
        markdown.index(synthesis.comparison_narrative)
        < markdown.index("| 方案 | 方案定位 |")
        < markdown.index("| 面向 | 目前狀態 |")
    )
    assert "成熟案例橫向比較" not in markdown
    assert "目前狀態與目標狀態" not in markdown


def test_roadmap_contains_immediate_actions_and_has_no_standalone_next_steps() -> None:
    markdown = render_synthesis_markdown(_synthesis("knowledge_assist"))

    assert "## 5. 實施路線、風險與驗收" in markdown
    assert "| 階段 | 主要工作 | 交付成果 | 人工邊界 | 通過條件 |" in markdown
    assert "立即行動" in markdown
    assert "## 9. 下一步" not in markdown
    assert "## 下一步" not in markdown


@pytest.mark.parametrize(
    "scenario_id",
    [
        "knowledge_assist",
        "expense_rules",
        "governed_access",
        "maintenance_coverage_gap",
    ],
)
def test_all_golden_scenarios_use_the_new_chinese_article_structure(
    scenario_id: str,
) -> None:
    synthesis = _synthesis(scenario_id)
    markdown = render_synthesis_markdown(synthesis)
    main_report = _main_report(markdown)

    assert synthesis.schema_version == "2.2"
    assert len(synthesis.current_target_comparison) == 6
    assert synthesis.implementation_roadmap
    assert "## 1. 專案評估摘要" in markdown
    assert "## 2. 推薦方案與理由" in markdown
    assert "## 3. 需求與訪談發現" in markdown
    assert "## 4. 方案、成熟案例與專案差距比較" in markdown
    assert "## 5. 實施路線、風險與驗收" in markdown
    assert "## 6. 技術附錄" in markdown
    assert "## 10. 評估依據附錄" not in markdown
    for forbidden in (
        "安全化原始問答",
        "證據依據",
        "success_conditions",
        "required controls",
        "go/no-go",
        "Fxxx",
        "SC-xxx",
    ):
        assert forbidden not in markdown
    assert re.search(r"\bF\d{3}\b|\bSC-\d+\b", markdown) is None
    assert re.search(r"[A-Z][a-z]+(?:\s+[A-Za-z]+){3,}[.!?]", main_report) is None


def test_appendix_keeps_only_chinese_scores_and_hard_gate_details() -> None:
    markdown = render_synthesis_markdown(_synthesis("governed_access"))
    appendix = markdown.split("## 6. 技術附錄", 1)[1]

    assert "### 六維評分" in appendix
    assert "### 硬性限制明細" in appendix
    assert "| 編號 |" not in appendix
    assert "安全化原始問答" not in appendix
    assert "證據依據" not in appendix
