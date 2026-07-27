"""P6.6 golden invariants for the four synthetic product acceptance scenarios."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from ai_poc_planner.application.case_centered_assessment import (
    build_case_centered_assessment,
    build_deterministic_assessment_facts,
    build_deterministic_gate_evaluation,
    infer_opportunity_types,
)
from ai_poc_planner.application.planning_report import render_markdown
from ai_poc_planner.domain.analysis import ProgramGateResult
from ai_poc_planner.domain.catalog import OpportunityType
from ai_poc_planner.domain.enums import (
    DecisionAuthority,
    FactStatus,
    ProcessingBoundary,
)
from ai_poc_planner.domain.project_history import FactRevision
from ai_poc_planner.infrastructure.local_case_repository import LocalCaseRepository
from ai_poc_planner.ui.results import case_centered_overview
from tests.fixtures.product_acceptance.schema import (
    ACCEPTANCE_RUBRIC,
    AcceptanceScenario,
    load_acceptance_scenarios,
)

_ROOT = Path(__file__).parents[2]
_CASES = LocalCaseRepository(_ROOT / "data" / "reviewed_cases.json").load()
_SCENARIOS = {item.scenario_id: item for item in load_acceptance_scenarios()}


def _scenario(scenario_id: str) -> AcceptanceScenario:
    return _SCENARIOS[scenario_id]


def _facts(scenario: AcceptanceScenario) -> tuple[FactRevision, ...]:
    now = datetime.now(UTC)
    return tuple(
        FactRevision(
            id=uuid4(),
            version_id=uuid4(),
            fact_key=item.fact_key,
            value=item.value,
            status=item.status,
            reference_message_ids=[uuid4()],
            created_at=now,
        )
        for item in scenario.facts
    )


def _gate_results(scenario: AcceptanceScenario) -> tuple[ProgramGateResult, ...]:
    evaluation = build_deterministic_gate_evaluation(
        _facts(scenario),
        selected_authority=DecisionAuthority.HUMAN_FINAL_DECISION,
        selected_boundary=ProcessingBoundary.LOCAL_ONLY,
    )
    return tuple(
        ProgramGateResult(
            rule_id=item.rule_id,
            disposition=item.disposition,
            reason=item.reason,
            required_controls=item.required_controls,
            human_review_required=item.human_review_required,
            affected_stage="目前階段與第一階段 PoC",
            release_conditions=item.required_controls,
        )
        for item in evaluation.triggered
    )


def _assessment(scenario: AcceptanceScenario):
    facts = _facts(scenario)
    return build_case_centered_assessment(
        cases=_CASES,
        facts=facts,
        opportunity_types=infer_opportunity_types(facts),
        recommendation_title="P6.6 基準驗收路線",
        gate_results=_gate_results(scenario),
        option_kind="hybrid",
    )


def test_all_product_acceptance_scenarios_and_rubric_are_schema_valid() -> None:
    scenarios = load_acceptance_scenarios()

    assert {item.scenario_id for item in scenarios} == {
        "knowledge_assist",
        "expense_rules",
        "governed_access",
        "maintenance_coverage_gap",
    }
    assert len(scenarios) == 4
    assert ACCEPTANCE_RUBRIC.maximum_score == 20
    assert ACCEPTANCE_RUBRIC.minimum_passing_score == 16
    assert len(ACCEPTANCE_RUBRIC.dimensions) == 10
    assert set(ACCEPTANCE_RUBRIC.critical_dimension_keys) == {
        "requirement_understanding",
        "case_relevance",
        "hard_gate_explanation",
    }


def test_fixture_facts_preserve_confirmed_and_unknown_states() -> None:
    assert all(
        item.status is FactStatus.CONFIRMED
        for scenario in (_scenario("knowledge_assist"), _scenario("expense_rules"))
        for item in scenario.facts
    )
    governed = {item.fact_key: item for item in _scenario("governed_access").facts}
    assert governed["processing_boundary"].status is FactStatus.CONFIRMED
    maintenance = {
        item.fact_key: item for item in _scenario("maintenance_coverage_gap").facts
    }
    assert maintenance["validation_sample"].status is FactStatus.UNKNOWN
    assert maintenance["fault_labels"].status is FactStatus.UNKNOWN


def test_knowledge_assist_is_retrieval_first_and_human_final() -> None:
    scenario = _scenario("knowledge_assist")
    facts = _facts(scenario)
    opportunities = infer_opportunity_types(facts)
    assessment_facts = build_deterministic_assessment_facts(facts)
    result = _assessment(scenario)

    assert OpportunityType.CUSTOMER_SERVICE_ASSIST in opportunities
    assert (
        OpportunityType.ENTERPRISE_KNOWLEDGE_AND_PROFESSIONAL_DOCUMENT_ASSIST
        in opportunities
    )
    assert assessment_facts.technical_fit.retrieval_required
    assert not assessment_facts.gates.autonomous_final_decision
    assert all(
        "自主" not in item
        for phase in result.phased_path
        for item in phase.actions + phase.not_doing
        if "允許" in item
    )
    assert result.matched_cases
    assert all(match.case.source_references for match in result.matched_cases)


def test_expense_rules_prefers_deterministic_rules_and_does_not_force_cases() -> None:
    scenario = _scenario("expense_rules")
    facts = _facts(scenario)
    assessment_facts = build_deterministic_assessment_facts(facts)
    opportunities = infer_opportunity_types(facts)
    result = _assessment(scenario)

    assert opportunities == ()
    assert assessment_facts.technical_fit.traditional_solution_preferred
    assert not assessment_facts.technical_fit.ai_needed
    assert result.matching_status == "no_suitable_reviewed_case"
    assert not result.matched_cases
    assert result.no_case_reason


def test_governed_access_keeps_human_authority_and_exposes_gate_impacts() -> None:
    scenario = _scenario("governed_access")
    facts = _facts(scenario)
    evaluation = build_deterministic_gate_evaluation(
        facts,
        selected_authority=DecisionAuthority.HUMAN_FINAL_DECISION,
        selected_boundary=ProcessingBoundary.LOCAL_ONLY,
    )
    result = _assessment(scenario)
    gate_ids = {item.rule_id for item in evaluation.triggered}

    assert OpportunityType.ENTERPRISE_KNOWLEDGE_AND_PROFESSIONAL_DOCUMENT_ASSIST in (
        infer_opportunity_types(facts)
    )
    assert OpportunityType.ANOMALY_AND_RISK_DETECTION not in infer_opportunity_types(
        facts
    )
    assert {"HG-01", "HG-03", "HG-05", "HG-06"}.issubset(gate_ids)
    assert not build_deterministic_assessment_facts(
        facts,
        selected_authority=DecisionAuthority.HUMAN_FINAL_DECISION,
        selected_boundary=ProcessingBoundary.LOCAL_ONLY,
    ).gates.autonomous_final_decision
    assert result.gate_impacts
    assert all(item.affected_stage for item in result.gate_impacts)
    assert any("hard gate" in item for item in result.recommendation_basis)
    assert len(result.phased_path) >= 3


def test_coverage_gap_never_invents_a_case_and_keeps_unknowns_conservative() -> None:
    scenario = _scenario("maintenance_coverage_gap")
    facts = _facts(scenario)
    assessment_facts = build_deterministic_assessment_facts(facts)
    result = _assessment(scenario)
    approved_ids = {
        item.case_id for item in _CASES if item.review_status.value == "approved"
    }

    assert OpportunityType.PREDICTIVE_MAINTENANCE in infer_opportunity_types(facts)
    assert OpportunityType.DEMAND_FORECASTING not in infer_opportunity_types(facts)
    assert not assessment_facts.data_readiness.validation_sample_available
    assert any(item.unknown_impact for item in _score_unknowns(facts))
    assert {match.case.case_id for match in result.matched_cases} <= approved_ids
    assert all(
        match.reference_value.level.value != "high" for match in result.matched_cases
    )
    assert all(
        practice.source_case_ids
        and set(practice.source_case_ids)
        <= {match.case.case_id for match in result.matched_cases}
        for practice in result.transferable_practices
    )
    assert "成熟案例驗證" not in " ".join(result.recommendation_basis)


def _score_unknowns(facts: tuple[FactRevision, ...]):
    from ai_poc_planner.application.case_centered_assessment import (
        build_deterministic_scores,
    )

    tokens = {f"F{index:03d}": item.id for index, item in enumerate(facts, start=1)}
    scores, _ = build_deterministic_scores(facts, tokens)
    return scores


def test_api_ui_and_markdown_share_the_same_case_centered_result() -> None:
    result = _assessment(_scenario("knowledge_assist"))
    api_payload = {"case_centered": result.model_dump(mode="json")}
    ui_view = case_centered_overview(api_payload)
    markdown = render_markdown(
        SimpleNamespace(section_items=lambda: ()),
        SimpleNamespace(case_centered=result, scores=()),
        _facts(_scenario("knowledge_assist")),
    )

    assert ui_view["recommendation_title"] == result.recommendation_title
    assert [item["title"] for item in ui_view["cases"]] == [
        item.case.title for item in result.matched_cases
    ]
    assert result.recommendation_title in markdown
    assert all(item.case.title in markdown for item in result.matched_cases)
    assert all(phase.phase_name in markdown for phase in result.phased_path)
