from pathlib import Path

import pytest

from ai_poc_planner.application.demo import build_demo_request
from ai_poc_planner.application.report import (
    REPORT_SECTIONS,
    ReportExportError,
    render_markdown_report,
    write_markdown_report,
)
from ai_poc_planner.application.workflow import run_offline_planning
from ai_poc_planner.domain.enums import GateDisposition


def test_generated_proposal_contains_required_planning_fields() -> None:
    result = run_offline_planning(build_demo_request())
    proposal = result.proposal

    assert proposal.executive_summary
    assert proposal.suggested_use_case_boundary
    assert proposal.in_scope
    assert proposal.out_of_scope
    assert proposal.poc_milestones
    assert proposal.evidence_refs
    assert proposal.success_metrics
    assert proposal.scope_assumptions


def test_blocked_proposal_stops_execution_and_has_no_architecture_plan() -> None:
    result = run_offline_planning(build_demo_request(scenario="high_score_but_blocked"))

    assert result.proposal.gate_disposition is GateDisposition.BLOCKED
    assert result.proposal.architecture_options == []
    assert "暫停" in result.proposal.executive_summary
    assert "暫停直接 PoC 執行" in result.proposal.next_actions


def test_assistive_report_preserves_human_final_decision() -> None:
    result = run_offline_planning(build_demo_request(scenario="assistive_only"))

    assert any("人工最終決策" in item for item in result.proposal.human_review_points)
    assert "人工最終決策" in result.markdown


def test_requires_controls_report_lists_gate_controls() -> None:
    result = run_offline_planning(build_demo_request(scenario="requires_controls"))

    controls = {
        control
        for gate in result.assessment.hard_gates
        for control in gate.required_controls
    }
    assert controls
    assert all(control in result.markdown for control in controls)


def test_markdown_sections_are_complete_and_in_fixed_order() -> None:
    markdown = run_offline_planning(build_demo_request()).markdown

    positions = [markdown.index(section) for section in REPORT_SECTIONS]

    assert positions == sorted(positions)
    assert "HG-" in markdown or "No hard gates triggered" in markdown
    assert "fixture:" in markdown
    assert "Estimated duration:" in markdown
    assert "Estimated team:" in markdown
    assert "使用單一標準訪談與固定評估框架" in markdown


def test_markdown_is_identical_for_identical_input() -> None:
    request = build_demo_request()

    assert (
        run_offline_planning(request).markdown == run_offline_planning(request).markdown
    )


def test_markdown_file_can_be_written(tmp_path: Path) -> None:
    output = tmp_path / "demo-report.md"
    request = build_demo_request(output_path=str(output))

    result = run_offline_planning(request)

    assert result.report_path == str(output.resolve())
    assert output.read_text(encoding="utf-8") == result.markdown


def test_report_write_failure_has_stable_error(tmp_path: Path) -> None:
    with pytest.raises(ReportExportError) as error:
        write_markdown_report("# report\n", tmp_path)

    assert error.value.code == "report_write_failed"


def test_markdown_neutralizes_markup_and_redacts_sensitive_answers() -> None:
    request = build_demo_request()
    project = request.project.model_copy(
        update={"title": "<script>alert(1)</script> [click](https://evil.invalid)"}
    )
    answers = {
        **request.interview_answers,
        "api_key": "synthetic-api-key-that-must-not-appear",
        "context": {
            "api_key": "synthetic-nested-key-that-must-not-appear",
            "note": "safe",
        },
    }

    markdown = run_offline_planning(
        request.model_copy(update={"project": project, "interview_answers": answers})
    ).markdown

    assert "<script>" not in markdown
    assert "[click](" not in markdown
    assert "synthetic-api-key-that-must-not-appear" not in markdown
    assert "synthetic-nested-key-that-must-not-appear" not in markdown
    assert "&lt;script&gt;" in markdown
    assert "REDACTED" in markdown


def test_markdown_neutralizes_typed_team_case_and_rule_identifiers() -> None:
    request = build_demo_request(scenario="high_score_but_blocked")
    result = run_offline_planning(request)
    gate = result.assessment.hard_gates[0].model_copy(
        update={
            "rule_id": "<b>HG-X</b>",
            "evidence_refs": ["<svg onload=alert(1)>"],
        }
    )
    assessment = result.assessment.model_copy(update={"hard_gates": [gate]})
    case = result.proposal.similar_cases[0].model_copy(
        update={"case_id": "[case](https://evil.invalid)"}
    )
    proposal = result.proposal.model_copy(
        update={
            "hard_gates": [gate],
            "similar_cases": [case],
            "estimated_team": ["<img src=x onerror=alert(1)>"],
        }
    )

    markdown = render_markdown_report(
        project=request.project,
        interview_answers=request.interview_answers,
        assessment=assessment,
        proposal=proposal,
        evidence=request.evidence,
    )

    assert "<b>HG-X</b>" not in markdown
    assert "[case](" not in markdown
    assert "<img" not in markdown
    assert "<svg" not in markdown
    assert "&lt;b&gt;HG-X&lt;/b&gt;" in markdown
