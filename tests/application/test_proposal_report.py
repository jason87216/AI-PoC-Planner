from pathlib import Path

import pytest

from ai_poc_planner.application.demo import build_demo_request
from ai_poc_planner.application.report import (
    REPORT_SECTIONS,
    ReportExportError,
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


def test_blocked_proposal_stops_execution_and_has_no_architecture_plan() -> None:
    result = run_offline_planning(
        build_demo_request(scenario="high_score_but_blocked")
    )

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


def test_markdown_is_identical_for_identical_input() -> None:
    request = build_demo_request()

    assert run_offline_planning(request).markdown == run_offline_planning(
        request
    ).markdown


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
