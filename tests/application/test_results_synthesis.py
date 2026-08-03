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
from ai_poc_planner.domain.enums import FactStatus, InterviewRole, VisibleMessageKind
from ai_poc_planner.domain.project_history import (
    FactRevision,
    VisibleConversationMessage,
)
from ai_poc_planner.domain.solution_catalog import SolutionPattern
from ai_poc_planner.persistence.catalog_seed import (
    implementation_references,
    reviewed_cases,
    reviewed_solution_patterns,
)
from tests.application.test_product_acceptance_baselines import (
    _facts,
    _formal_result,
    _scenario,
)


def _synthesis(scenario_id: str, extra_facts: tuple[FactRevision, ...] = ()):
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
        facts=[*_facts(scenario), *extra_facts],
        solution=solution,
        reviewed_cases=tuple(
            item for item in reviewed_cases() if item.case_id in match_ids
        ),
        candidate_solutions=reviewed_solution_patterns(),
        implementation_references=implementation_references(),
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

    finding = next(
        item for item in synthesis.interview_findings if item.topic == "主管與 IT 責任"
    )
    assert answer.content in finding.confirmed_content
    assert finding.assessment_impact == "明確保留人工最終決策與例外處理責任。"
    assert "誰保留對外回覆" not in markdown
    assert "初始理解" not in markdown
    assert "追問後澄清" not in markdown
    assert "| 主題 | 已確認內容 | 對方案的影響 |" in markdown

    scope_finding = next(
        item
        for item in build_interview_findings(
            questions=[question.model_copy(update={"fact_key": "process_scope"})],
            messages=[answer],
            facts=list(_facts(scenario)),
        )
        if item.topic == "第一階段範圍"
    )
    assert scope_finding.topic == "第一階段範圍"
    assert scope_finding.assessment_impact == "用來限制第一階段範圍、責任與部署方式。"

    for fact_key, topic in (
        ("approval_process_detail", "主管與 IT 責任"),
        ("audit_trail_requirements", "規則、例外與稽核"),
    ):
        finding = next(
            item
            for item in build_interview_findings(
                questions=[question.model_copy(update={"fact_key": fact_key})],
                messages=[answer],
                facts=list(_facts(scenario)),
            )
            if item.topic == topic
        )
        assert finding.topic == topic
        assert finding.topic != "其他已確認事項"


def test_interview_findings_include_all_confirmed_facts_without_new_questions() -> None:
    now = datetime.now(UTC)
    version_id = uuid4()
    facts = list(_facts(_scenario("governed_access")))
    for fact_key, value in (
        ("first_phase_scope", "第一階段只整理電子郵件與試算表申請，先不自動核准。"),
        ("manager_approval_responsibility", "主管保留每一筆權限申請的最終核准權。"),
        (
            "it_provisioning_responsibility",
            "IT 人員依核准結果實際開通，不由 AI 直接寫入權限系統。",
        ),
        ("rules_conflict_check", "提交時檢查必填欄位、固定規則與權限衝突。"),
        (
            "audit_trail_requirements",
            "系統保留申請、規則結果、核准人與時間的稽核紀錄。",
        ),
        ("validation_metric", "驗收檢查格式完整率、規則提示正確率與例外紀錄完整性。"),
    ):
        facts.append(
            FactRevision(
                id=uuid4(),
                version_id=version_id,
                fact_key=fact_key,
                value=value,
                status=FactStatus.CONFIRMED,
                reference_message_ids=[uuid4()],
                created_at=now,
            )
        )

    findings = build_interview_findings(questions=[], messages=[], facts=facts)
    topics = {item.topic for item in findings}

    assert topics == {
        "現況與預期成果",
        "第一階段範圍",
        "主管與 IT 責任",
        "資料與處理環境",
        "規則、例外與稽核",
        "驗收指標",
    }
    assert any(
        "主管保留每一筆權限申請的最終核准權。" in item.confirmed_content
        for item in findings
    )


def test_permission_report_filters_unrelated_digitization_gate_conditions() -> None:
    markdown = render_synthesis_markdown(_synthesis("governed_access"))

    assert "OCR" not in markdown
    assert "數位化" not in markdown


def test_permission_report_uses_taiwan_approval_terms() -> None:
    markdown = render_synthesis_markdown(_synthesis("governed_access"))

    assert "人工審批" not in markdown
    assert "審批" not in markdown


def test_permission_interview_impact_uses_manager_and_it_responsibilities() -> None:
    fact = FactRevision(
        id=uuid4(),
        version_id=uuid4(),
        fact_key="human_final_decision",
        value="主管保留最終核准，IT 人員負責實際開通。",
        status=FactStatus.CONFIRMED,
        reference_message_ids=[uuid4()],
        created_at=datetime.now(UTC),
    )

    findings = build_interview_findings(
        questions=[],
        messages=[],
        facts=[fact],
        recommendation_category="rules_first",
    )

    assert findings[0].topic == "主管與 IT 責任"
    assert findings[0].assessment_impact == "明確保留主管最終核准與 IT 實際開通責任。"


def test_permission_report_excludes_cross_scenario_copy_and_merges_topics() -> None:
    extra_facts = tuple(
        FactRevision(
            id=uuid4(),
            version_id=uuid4(),
            fact_key=fact_key,
            value=value,
            status=FactStatus.CONFIRMED,
            reference_message_ids=[uuid4()],
            created_at=datetime.now(UTC),
        )
        for fact_key, value in (
            ("first_phase_scope", "第一階段不自動核准，也不直接寫入權限系統。"),
            ("manager_approval_responsibility", "主管保留每筆申請的最終核准權。"),
            ("it_provisioning_responsibility", "IT 依核准結果實際開通。"),
            ("rules_conflict_check", "提交時檢查必填資料與規則衝突。"),
            ("audit_trail_requirements", "保留申請、規則結果、核准人與時間紀錄。"),
            ("validation_metric", "驗收檢查格式完整率與規則提示正確率。"),
        )
    )
    synthesis = _synthesis("governed_access", extra_facts=extra_facts)
    markdown = render_synthesis_markdown(synthesis)
    main_report = _main_report(markdown)
    interview_section = main_report.split("## 3. 需求與訪談發現", 1)[1].split(
        "## 4. 方案、成熟案例與專案差距比較", 1
    )[0]
    topics = [
        line.split("|")[1].strip()
        for line in interview_section.splitlines()
        if line.startswith("|") and "主題" not in line and "---" not in line
    ]

    assert set(topics) <= {
        "現況與預期成果",
        "第一階段範圍",
        "主管與 IT 責任",
        "資料與處理環境",
        "規則、例外與稽核",
        "驗收指標",
    }
    assert len(topics) <= 8
    assert {
        item.topic: item.assessment_impact for item in synthesis.interview_findings
    } == {
        "現況與預期成果": "用來界定電子郵件與試算表流程的改善目標與驗收方向。",
        "第一階段範圍": "用來限制第一階段僅標準化、規則檢查與人工核准，不自動開通。",
        "主管與 IT 責任": "明確保留主管最終核准與 IT 實際開通責任。",
        "資料與處理環境": "用來決定申請資料、權限資料及受控處理環境的整理範圍。",
        "規則、例外與稽核": "用來定義必填欄位、固定規則、例外處理與稽核紀錄。",
        "驗收指標": "用來設定格式完整率、規則提示正確率、核准時間與例外紀錄完整性。",
    }
    for term in ("對外回覆", "客服", "客戶回覆", "回覆草稿"):
        assert term not in main_report


def test_permission_route_table_separates_benefits_from_case_practices() -> None:
    synthesis = _synthesis("governed_access")
    rows = {item.option: item for item in synthesis.option_comparison}
    route_table = render_synthesis_markdown(synthesis).split("### 路線比較", 1)[1]
    route_table = route_table.split("### 成熟案例介紹", 1)[0]

    assert rows["電子郵件與試算表人工標準化"].transferable_practice == (
        "改動小，導入成本最低。"
    )
    assert rows["權限申請標準化、規則檢查與人工核准"].transferable_practice == (
        "直接改善漏填、規則衝突、責任分工與稽核追蹤。"
    )
    assert rows["自由文字與附件的 AI 輔助"].transferable_practice == (
        "未來可協助整理非結構化申請與複雜例外。"
    )
    assert rows["自動核准與直接開通"].transferable_practice == (
        "理論上可減少人工處理時間。"
    )
    assert len({item.transferable_practice for item in rows.values()}) == 4
    assert all("可移植的是" not in item.transferable_practice for item in rows.values())
    assert len({"；".join(item.cannot_copy) for item in rows.values()}) == 4
    assert "可移植的是" not in route_table


def test_permission_case_support_summaries_have_case_specific_adoption() -> None:
    summaries = _synthesis("governed_access").case_support_summaries
    adoptions = {item.case_title: item.project_adoption for item in summaries}

    assert len(adoptions) == 3
    assert len(set(adoptions.values())) == 3
    for title, expected in (
        ("Demandbase", "集中申請入口、角色與權限對照、撤銷追蹤"),
        ("Cenibra", "分階段導入、規則與風險檢查、跨系統稽核"),
        ("Varo", "臨時權限、期限管理、存取檢視"),
    ):
        adoption = next(value for key, value in adoptions.items() if title in key)
        assert expected in adoption


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
        display_name_zh="權限申請標準化、規則檢查與人工核准",
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


def test_empty_reviewed_cases_do_not_render_empty_case_sections() -> None:
    synthesis = _synthesis("governed_access").model_copy(
        update={"reviewed_cases": (), "case_support_summaries": ()}
    )

    markdown = render_synthesis_markdown(synthesis)

    assert "本次沒有匹配的已審核成熟案例。" in markdown
    assert "### 成熟案例介紹" not in markdown
    assert "### 案例支持關係摘要" not in markdown


def test_generic_roadmap_has_distinct_pre_scale_review() -> None:
    synthesis = _synthesis("knowledge_assist")
    phases = synthesis.implementation_roadmap

    assert len(phases) >= 3
    assert phases[-1].phase == "擴大前檢視"
    assert phases[-1].actions != phases[1].actions
    assert any("停止" in item or "擴大" in item for item in phases[-1].outputs)
    assert any("hard gates" in item for item in phases[-1].acceptance_criteria)
    assert "若若" not in render_synthesis_markdown(synthesis)


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
        item.supporting_cases
        or "本次未找到可直接參照的已審核案例" in item.case_evidence
        for item in synthesis.option_comparison
    )
    assert ("| 方案 | 主要做法 | 優點 | 限制 | 判斷 |") in markdown
    assert (
        "| 面向 | 目前狀態 | 採用推薦方案後的目標狀態 | 主要差距 | 方案如何處理 |"
    ) in markdown
    assert (
        markdown.index(synthesis.comparison_narrative)
        < markdown.index("| 方案 | 主要做法 | 優點 | 限制 | 判斷 |")
        < markdown.index("| 面向 | 目前狀態 |")
    )
    assert "成熟案例橫向比較" not in markdown
    assert "目前狀態與目標狀態" not in markdown


def test_comparison_chapter_separates_routes_cases_references_and_gaps() -> None:
    synthesis = _synthesis("governed_access")
    markdown = render_synthesis_markdown(synthesis)
    recommendation = synthesis.recommendation_narrative
    chapter = markdown.split("## 4. 方案、成熟案例與專案差距比較", 1)[1]
    chapter = chapter.split("## 5. 實施路線、風險與驗收", 1)[0]

    assert 5 <= recommendation.count("\n\n") + 1 <= 6
    assert all(
        case.problem_context_zh not in recommendation
        for case in synthesis.reviewed_cases
    )
    assert all(
        case.implemented_approach_zh not in recommendation
        for case in synthesis.reviewed_cases
    )
    assert all(
        case.documented_outcomes_zh not in recommendation
        for case in synthesis.reviewed_cases
    )
    assert all(
        f"[{case.source_name}]" not in recommendation
        for case in synthesis.reviewed_cases
    )

    route_header = "| 方案 | 主要做法 | 優點 | 限制 | 判斷 |"
    case_summary_header = "| 案例 | 主要支持做法 | 本專案採用方式 |"
    reference_header = "| 主題 | 參考文件 | 用途 |"
    assert route_header in chapter
    assert "案例能證明什麼" not in chapter
    assert "persisted matched cases" not in chapter
    assert case_summary_header in chapter
    assert "### 官方實施參考" in chapter
    assert (
        "| 面向 | 目前狀態 | 採用推薦方案後的目標狀態 | 主要差距 | 方案如何處理 |"
        in chapter
    )
    assert chapter.index("### 路線比較") < chapter.index(route_header)
    assert chapter.index(route_header) < chapter.index("### 成熟案例介紹")
    assert chapter.index("### 成熟案例介紹") < chapter.index("### 案例支持關係摘要")
    assert chapter.index("### 官方實施參考") < chapter.index(reference_header)
    assert chapter.index(reference_header) < chapter.index("| 面向 |")

    matched_titles = {case.display_title_zh for case in synthesis.reviewed_cases}
    non_case_headers = {
        "### 路線比較",
        "### 成熟案例介紹",
        "### 案例支持關係摘要",
        "### 官方實施參考",
        "### 目前狀態、目標狀態與主要差距",
    }
    detail_titles = {
        line.removeprefix("### ").strip()
        for line in chapter.splitlines()
        if line.startswith("### ") and line not in non_case_headers
    }
    assert detail_titles == matched_titles
    assert "cellcentric" not in chapter
    assert len(synthesis.case_support_summaries) == len(synthesis.reviewed_cases)
    assert len(synthesis.implementation_references) == 6
    assert reference_header in chapter
    assert "[Microsoft Learn：存取套件申請流程]" in chapter

    visible_gate_rows = [
        (
            row.limit_content,
            row.affected_stage,
            row.currently_possible,
            row.release_condition,
        )
        for row in synthesis.appendix.hard_gates
    ]
    assert len(visible_gate_rows) == len(set(visible_gate_rows))


def test_governed_access_report_excludes_unrelated_retrieval_content() -> None:
    markdown = render_synthesis_markdown(_synthesis("governed_access"))
    main_report = _main_report(markdown)

    for required in (
        "權限申請標準化、規則檢查與人工核准",
        "主管保留最終核准",
        "IT 依已核准結果開通",
        "不處理自動開通",
        "申請格式完整率",
        "規則提示正確率",
        "主管核准處理時間",
        "例外紀錄完整性",
        "Demandbase",
        "Cenibra",
        "Varo",
    ):
        assert required in main_report

    for prohibited in (
        "文件知識檢索與人工審核輔助",
        "Morgan Stanley",
        "Klarna",
        "Ironclad",
        "CrossTech",
        "autonomous_action",
        "盤點核准文件與 FAQ",
        "內容檢索",
        "來源引用",
        "客服回覆",
    ):
        assert prohibited not in main_report

    assert "目前沒有直接案例支持" not in main_report
    assert "目前沒有足夠相關的已審核成熟案例" not in main_report
    assert "本次未找到可直接參照的已審核案例" not in main_report
    assert len(_synthesis("governed_access").recommendation_narrative) > len(
        _synthesis("governed_access").comparison_narrative
    )
    assert len(_synthesis("governed_access").option_comparison) == 4


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
