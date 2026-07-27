from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from ai_poc_planner.application.planning_report import (
    build_report_synthesis,
    render_synthesis_markdown,
)
from ai_poc_planner.domain.discovery import InterviewQuestion
from ai_poc_planner.domain.enums import InterviewRole, VisibleMessageKind
from ai_poc_planner.domain.project_history import VisibleConversationMessage
from tests.application.test_product_acceptance_baselines import (
    _facts,
    _formal_result,
    _scenario,
)


def test_report_synthesis_is_an_article_with_safe_interview_findings() -> None:
    scenario = _scenario("knowledge_assist")
    result = _formal_result(scenario)
    question_id = uuid4()
    answer_id = uuid4()
    now = datetime.now(UTC)
    question = InterviewQuestion(
        id=question_id,
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
        interview_questions=[question],
        messages=[answer],
    )

    assert synthesis.executive_narrative
    assert synthesis.project_context_narrative
    assert synthesis.recommendation_narrative
    assert synthesis.current_target_comparison
    assert synthesis.option_comparison
    assert synthesis.case_comparison
    assert synthesis.implementation_roadmap
    assert synthesis.next_actions
    finding = synthesis.interview_findings[0]
    assert finding.source_question == question.question
    assert finding.answer_summary == answer.content
    assert str(question_id) not in repr(synthesis)
    assert str(answer_id) not in repr(synthesis)
    assert "human_final_decision" not in repr(synthesis)


def test_fallback_synthesis_is_complete_and_scores_are_appendix_only() -> None:
    scenario = _scenario("maintenance_coverage_gap")
    result = _formal_result(scenario)

    synthesis = build_report_synthesis(
        analysis=result,
        facts=list(_facts(scenario)),
        report=None,
    )
    markdown = render_synthesis_markdown(synthesis)
    main_report = markdown.split("## 10. 評估依據附錄", 1)[0]

    assert synthesis.executive_narrative
    assert synthesis.risk_and_boundary_summary
    assert synthesis.hard_gate_summary
    assert synthesis.appendix.scores
    assert synthesis.appendix.hard_gates
    assert "加權" not in main_report
    assert "HG-" not in main_report
    assert "限制內容 | 影響階段 | 目前可做事項 | 解除條件" in main_report
    assert "## 10. 評估依據附錄" in markdown
    assert "HG-" in markdown


def test_multiple_cases_render_as_one_comparison_table() -> None:
    scenario = _scenario("knowledge_assist")
    synthesis = build_report_synthesis(
        analysis=_formal_result(scenario),
        facts=list(_facts(scenario)),
    )

    markdown = render_synthesis_markdown(synthesis)

    assert markdown.count("| 中文案例名稱 | 原始英文名稱 | 組織 |") == 1
    assert "可移植做法" in markdown
    assert "不能直接複製" in markdown


@pytest.mark.parametrize(
    "scenario_id",
    [
        "knowledge_assist",
        "expense_rules",
        "governed_access",
        "maintenance_coverage_gap",
    ],
)
def test_all_golden_scenarios_have_the_complete_article_structure(
    scenario_id: str,
) -> None:
    scenario = _scenario(scenario_id)
    synthesis = build_report_synthesis(
        analysis=_formal_result(scenario),
        facts=list(_facts(scenario)),
    )
    markdown = render_synthesis_markdown(synthesis)

    assert synthesis.executive_narrative
    assert len(synthesis.current_target_comparison) >= 6
    assert synthesis.option_comparison
    assert sum(item.recommended for item in synthesis.option_comparison) == 1
    assert len({item.option for item in synthesis.option_comparison}) == len(
        synthesis.option_comparison
    )
    assert synthesis.implementation_roadmap
    assert synthesis.next_actions
    assert "## 10. 評估依據附錄" in markdown
    assert "## 1. 專案評估摘要" in markdown
    assert "## 3. 目前狀態與目標狀態" in markdown
    assert "## 4. 候選方案比較" in markdown
    assert "## 8. 風險、人工邊界與暫不實施事項" in markdown


def test_human_gate_summary_excludes_internal_gate_ids() -> None:
    synthesis = build_report_synthesis(
        analysis=_formal_result(_scenario("governed_access")),
        facts=list(_facts(_scenario("governed_access"))),
    )

    assert synthesis.hard_gate_summary
    assert all("HG-" not in repr(item) for item in synthesis.hard_gate_summary)
    assert all(item.currently_possible for item in synthesis.hard_gate_summary)
    assert all(item.release_condition for item in synthesis.hard_gate_summary)
