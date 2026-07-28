"""P6.6 golden invariants for the four synthetic product acceptance scenarios."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from ai_poc_planner.application.case_centered_assessment import (
    build_deterministic_assessment_facts,
    build_deterministic_gate_evaluation,
    infer_opportunity_types,
)
from ai_poc_planner.application.evidence_analysis import EvidenceAnalysisService
from ai_poc_planner.application.planning_report import render_markdown
from ai_poc_planner.domain.analysis import (
    AIAnalysisDraft,
    AnalysisOptionDraft,
    CatalogOpportunity,
    ProgramGateResult,
    RubricRatingDraft,
)
from ai_poc_planner.domain.catalog import NonAiAlternativeDirection, OpportunityType
from ai_poc_planner.domain.enums import (
    AnalysisConclusion,
    AnalysisOptionKind,
    DecisionAuthority,
    FactStatus,
    HighImpactDomain,
    ProcessingBoundary,
    ScoreDimension,
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
_DEFAULT_OPPORTUNITY = (
    OpportunityType.ENTERPRISE_KNOWLEDGE_AND_PROFESSIONAL_DOCUMENT_ASSIST
)


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


def _fact(
    fact_key: str,
    value: object,
    *,
    status: FactStatus = FactStatus.CONFIRMED,
) -> FactRevision:
    now = datetime.now(UTC)
    return FactRevision(
        id=uuid4(),
        version_id=uuid4(),
        fact_key=fact_key,
        value=value,
        status=status,
        reference_message_ids=[uuid4()],
        created_at=now,
    )


def _category_option_kind(category: str) -> AnalysisOptionKind:
    return {
        "ai_hybrid": AnalysisOptionKind.HYBRID,
        "rules_first": AnalysisOptionKind.NON_AI,
        "governed_assistive": AnalysisOptionKind.HYBRID,
        "readiness_first": AnalysisOptionKind.FOUNDATIONS_FIRST,
    }[category]


def _category_conclusion(category: str) -> AnalysisConclusion:
    return {
        "ai_hybrid": AnalysisConclusion.HYBRID_AI_AND_NON_AI,
        "rules_first": AnalysisConclusion.BETTER_SUITED_TO_NON_AI,
        "governed_assistive": AnalysisConclusion.HYBRID_AI_AND_NON_AI,
        "readiness_first": AnalysisConclusion.ESTABLISH_NON_AI_FOUNDATIONS_BEFORE_AI,
    }[category]


def _draft_option(
    *,
    key: str,
    kind: AnalysisOptionKind,
    fact_ref: str,
    opportunity_type: OpportunityType,
    human_boundary: str = "由負責人依政策覆核後再執行。",
    deployment_constraint: str = "依目前資料與治理條件限制範圍。",
) -> AnalysisOptionDraft:
    opportunity = CatalogOpportunity(
        kind="catalog",
        opportunity_type=opportunity_type,
        display_rationale="以確認的流程與資料事實作為機會類型依據。",
        fact_refs=[fact_ref],
    )
    return AnalysisOptionDraft(
        option_key=key,
        title=f"測試路線 {key}",
        option_kind=kind,
        summary="以確認事實、人工邊界與部署條件形成正式路線。",
        expected_benefits=["縮短驗收與決策時間"],
        limitations=[deployment_constraint],
        prerequisites=["完成必要的資料與治理確認"],
        risks=["未確認條件不可視為已通過"],
        fact_refs=[fact_ref],
        decision_authority=DecisionAuthority.HUMAN_FINAL_DECISION,
        processing_boundary=ProcessingBoundary.LOCAL_ONLY,
        human_review_points=[human_boundary],
        ai_opportunity=opportunity
        if kind in {AnalysisOptionKind.AI, AnalysisOptionKind.HYBRID}
        else None,
        non_ai_directions=(
            [NonAiAlternativeDirection.RULE_BASED_AUTOMATION]
            if kind
            in {
                AnalysisOptionKind.NON_AI,
                AnalysisOptionKind.HYBRID,
                AnalysisOptionKind.FOUNDATIONS_FIRST,
            }
            else []
        ),
    )


def _formal_result(
    scenario: AcceptanceScenario,
    selected_kind_override: AnalysisOptionKind | None = None,
):
    facts = _facts(scenario)
    ordered_facts = sorted(facts, key=lambda item: item.fact_key.casefold())
    tokens = {
        f"F{index:03d}": fact.id for index, fact in enumerate(ordered_facts, start=1)
    }
    fact_ref = next(iter(tokens))
    category = scenario.expected.recommendation_category
    selected_kind = selected_kind_override or _category_option_kind(category)
    selected_conclusion = (
        {
            AnalysisOptionKind.HYBRID: AnalysisConclusion.HYBRID_AI_AND_NON_AI,
            AnalysisOptionKind.NON_AI: AnalysisConclusion.BETTER_SUITED_TO_NON_AI,
            AnalysisOptionKind.FOUNDATIONS_FIRST: (
                AnalysisConclusion.ESTABLISH_NON_AI_FOUNDATIONS_BEFORE_AI
            ),
            AnalysisOptionKind.AI: AnalysisConclusion.SUITABLE_FOR_AI,
        }[selected_kind]
        if selected_kind_override is not None
        else _category_conclusion(category)
    )
    alternative_kind = (
        AnalysisOptionKind.NON_AI
        if selected_kind is not AnalysisOptionKind.NON_AI
        else AnalysisOptionKind.HYBRID
    )
    draft = AIAnalysisDraft(
        schema_version="1.0",
        requirement_summary="以確認事實組合正式驗收結果。",
        options=[
            _draft_option(
                key="o1",
                kind=selected_kind,
                fact_ref=fact_ref,
                opportunity_type=(
                    OpportunityType(scenario.expected.opportunity_types[0])
                    if scenario.expected.opportunity_types
                    else _DEFAULT_OPPORTUNITY
                ),
                human_boundary=scenario.expected.human_decision_boundary,
                deployment_constraint=scenario.expected.deployment_constraint,
            ),
            _draft_option(
                key="o2",
                kind=alternative_kind,
                fact_ref=fact_ref,
                opportunity_type=OpportunityType.ENTERPRISE_KNOWLEDGE_AND_PROFESSIONAL_DOCUMENT_ASSIST,
            ),
        ],
        recommended_option_key="o1",
        conclusion=selected_conclusion,
        conclusion_rationale=(
            "正式 recommendation 由 option kind、confirmed facts 與 "
            "deterministic gates 組合。"
        ),
        conclusion_fact_refs=[fact_ref],
        rubric_ratings=[
            RubricRatingDraft(
                dimension=dimension,
                rating=3,
                rationale="由 deterministic assessment engine 依確認事實評估。",
                evidence_fact_refs=[fact_ref],
                improvement_conditions=["補充驗收證據"],
            )
            for dimension in ScoreDimension
        ],
    )
    service = object.__new__(EvidenceAnalysisService)
    service._cases_path = _ROOT / "data" / "reviewed_cases.json"
    service._clock = lambda: datetime.now(UTC)
    service._uuid_factory = uuid4
    return service._validated_result(
        SimpleNamespace(id=uuid4()), draft, ordered_facts, tokens
    )


def _formal_recommendation_category(result) -> str:
    return result.case_centered.recommendation_category.value


def _flatten_text(value: object) -> str:
    if isinstance(value, dict):
        return " ".join(_flatten_text(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return " ".join(_flatten_text(item) for item in value)
    return str(value)


def _formal_outputs(result, facts: tuple[FactRevision, ...]) -> tuple[str, str, str]:
    formal = _flatten_text(result.model_dump(mode="json"))
    ui_view = case_centered_overview(
        {"case_centered": result.case_centered.model_dump(mode="json")}
    )
    ui = _flatten_text(ui_view)
    markdown = render_markdown(
        SimpleNamespace(section_items=lambda: ()), result, list(facts)
    )
    return formal, ui, markdown


def _claim_fragments(value: str) -> set[str]:
    fragments: set[str] = set(re.findall(r"[A-Za-z]{2,}", value))
    for run in re.findall(r"[\u4e00-\u9fff]+", value):
        fragments.update(run[index : index + 2] for index in range(len(run) - 1))
    return fragments


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


@pytest.mark.parametrize(
    "scenario_id",
    [item.scenario_id for item in load_acceptance_scenarios()],
)
def test_golden_expectations_are_consumed_by_formal_result_composition(
    scenario_id: str,
) -> None:
    scenario = _scenario(scenario_id)
    result = _formal_result(scenario)
    facts = _facts(scenario)
    inferred = tuple(item.value for item in infer_opportunity_types(facts))
    formal, ui, markdown = _formal_outputs(result, facts)
    structured = " ".join((formal, ui, markdown)).casefold()

    assert set(inferred) == set(scenario.expected.opportunity_types)
    assert _formal_recommendation_category(result) == (
        scenario.expected.recommendation_category
    )
    for term in scenario.expected.must_have_gap_terms:
        assert term.casefold() in structured
    phase_names = {item.phase_name for item in result.case_centered.phased_path}
    assert set(scenario.expected.must_have_phase_names) <= phase_names
    for forbidden in scenario.expected.must_not_have_conclusions:
        assert forbidden.casefold() not in structured
    result_text = _flatten_text(result.model_dump(mode="json"))
    assert (
        scenario.expected.human_decision_boundary.casefold() in result_text.casefold()
    )
    assert scenario.expected.deployment_constraint.casefold() in result_text.casefold()
    basis_and_phases = " ".join(
        [
            *result.case_centered.recommendation_basis,
            *[item.description for item in result.case_centered.phased_path],
            *[
                action
                for item in result.case_centered.phased_path
                for action in item.actions
            ],
        ]
    )
    for conclusion in scenario.expected.key_conclusions:
        assert any(
            fragment.casefold() in basis_and_phases.casefold()
            for fragment in _claim_fragments(conclusion)
        )


def test_formal_category_overrides_provider_hybrid_for_rules_first_case() -> None:
    result = _formal_result(
        _scenario("expense_rules"),
        selected_kind_override=AnalysisOptionKind.HYBRID,
    )

    assert result.case_centered.recommendation_category.value == "rules_first"
    assert result.case_centered.recommendation_title == "流程標準化與規則檢查路線"
    assert (
        "hybrid" not in " ".join(result.case_centered.recommendation_basis).casefold()
    )
    assert result.case_centered.recommendation_title in " ".join(
        result.case_centered.recommendation_basis
    )


def test_rules_first_signals_suppress_generic_ai_opportunity_matches() -> None:
    facts = (
        _fact("current_workflow_problem", "員工費用報銷大多是固定條件判斷。"),
        _fact("available_data", "資料來自結構化表單，欄位與附件狀態明確。"),
        _fact(
            "known_constraints",
            "優先使用規則引擎、表單驗證與傳統自動化，不需要複雜自然語言理解。",
        ),
    )

    assessed = build_deterministic_assessment_facts(facts)

    assert assessed.technical_fit.traditional_solution_preferred is True
    assert assessed.technical_fit.ai_needed is False
    assert infer_opportunity_types(facts) == ()


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("已有驗證集可供測試。", True),
        ("沒有驗證集。", False),
        ("有設備照片，但沒有驗證集。", False),
        ("計畫未來建立驗證集。", False),
        ("no validation set is available", False),
        ("validation sample not available", False),
        ("without a validation sample", False),
        ("not available: validation sample", False),
    ],
)
def test_validation_signal_is_scoped_to_one_fact_and_handles_negation(
    value: str, expected: bool
) -> None:
    facts = (_fact("available_data", value),)
    assessment_facts = build_deterministic_assessment_facts(facts)

    assert assessment_facts.data_readiness.validation_sample_available is expected
    if "照片" in value:
        assert assessment_facts.data_readiness.data_available


@pytest.mark.parametrize(
    ("value", "expected_domain"),
    [
        ("員工費用報銷規則檢查，財務人員最終審核。", HighImpactDomain.NONE),
        ("員工 FAQ 與內部培訓內容整理。", HighImpactDomain.NONE),
        ("主管進行高風險系統權限核准。", HighImpactDomain.EMPLOYMENT),
        ("招募與錄用決策由主管作成。", HighImpactDomain.EMPLOYMENT),
    ],
)
def test_high_impact_employment_requires_explicit_signal(
    value: str, expected_domain: HighImpactDomain
) -> None:
    facts = (_fact("current_workflow_problem", value),)
    assessment_facts = build_deterministic_assessment_facts(facts)
    gates = build_deterministic_gate_evaluation(
        facts,
        selected_authority=DecisionAuthority.HUMAN_FINAL_DECISION,
        selected_boundary=ProcessingBoundary.LOCAL_ONLY,
    )

    assert assessment_facts.gates.high_impact_domain is expected_domain
    assert ("HG-03" in {item.rule_id for item in gates.triggered}) is (
        expected_domain is HighImpactDomain.EMPLOYMENT
    )


@pytest.mark.parametrize(
    ("value", "included", "excluded"),
    [
        (
            "高風險權限申請由主管核准。",
            (),
            (OpportunityType.ANOMALY_AND_RISK_DETECTION,),
        ),
        (
            "交易風險識別與異常交易檢測。",
            (OpportunityType.ANOMALY_AND_RISK_DETECTION,),
            (),
        ),
        (
            "預測設備故障，使用設備照片。",
            (OpportunityType.PREDICTIVE_MAINTENANCE,),
            (OpportunityType.DEMAND_FORECASTING,),
        ),
        (
            "庫存需求預測與補貨預測。",
            (OpportunityType.DEMAND_FORECASTING,),
            (),
        ),
    ],
)
def test_opportunity_matching_keeps_positive_and_negative_signals_separate(
    value: str,
    included: tuple[OpportunityType, ...],
    excluded: tuple[OpportunityType, ...],
) -> None:
    inferred = infer_opportunity_types((_fact("current_workflow_problem", value),))

    assert all(item in inferred for item in included)
    assert all(item not in inferred for item in excluded)


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
    result = _formal_result(scenario)

    assert OpportunityType.CUSTOMER_SERVICE_ASSIST in opportunities
    assert (
        OpportunityType.ENTERPRISE_KNOWLEDGE_AND_PROFESSIONAL_DOCUMENT_ASSIST
        in opportunities
    )
    assert assessment_facts.technical_fit.retrieval_required
    assert not assessment_facts.gates.autonomous_final_decision
    assert all(
        "自主" not in item
        for phase in result.case_centered.phased_path
        for item in phase.actions + phase.not_doing
        if "允許" in item
    )
    assert result.case_centered.matched_cases
    assert all(
        match.case.source_references for match in result.case_centered.matched_cases
    )


def test_expense_rules_prefers_deterministic_rules_and_does_not_force_cases() -> None:
    scenario = _scenario("expense_rules")
    facts = _facts(scenario)
    assessment_facts = build_deterministic_assessment_facts(facts)
    opportunities = infer_opportunity_types(facts)
    result = _formal_result(scenario)

    assert opportunities == ()
    assert assessment_facts.technical_fit.traditional_solution_preferred
    assert not assessment_facts.technical_fit.ai_needed
    assert result.case_centered.matching_status == "no_suitable_reviewed_case"
    assert not result.case_centered.matched_cases
    assert result.case_centered.no_case_reason


def test_governed_access_keeps_human_authority_and_exposes_gate_impacts() -> None:
    scenario = _scenario("governed_access")
    facts = _facts(scenario)
    evaluation = build_deterministic_gate_evaluation(
        facts,
        selected_authority=DecisionAuthority.HUMAN_FINAL_DECISION,
        selected_boundary=ProcessingBoundary.LOCAL_ONLY,
    )
    result = _formal_result(scenario)
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
    assert result.case_centered.gate_impacts
    assert all(item.affected_stage for item in result.case_centered.gate_impacts)
    assert any(
        "hard gate" in item for item in result.case_centered.recommendation_basis
    )
    assert len(result.case_centered.phased_path) >= 3


def test_coverage_gap_never_invents_a_case_and_keeps_unknowns_conservative() -> None:
    scenario = _scenario("maintenance_coverage_gap")
    facts = _facts(scenario)
    assessment_facts = build_deterministic_assessment_facts(facts)
    result = _formal_result(scenario)
    approved_ids = {
        item.case_id for item in _CASES if item.review_status.value == "approved"
    }

    assert OpportunityType.PREDICTIVE_MAINTENANCE in infer_opportunity_types(facts)
    assert OpportunityType.DEMAND_FORECASTING not in infer_opportunity_types(facts)
    assert not assessment_facts.data_readiness.validation_sample_available
    assert any(item.unknown_impact for item in _score_unknowns(facts))
    assert {
        match.case.case_id for match in result.case_centered.matched_cases
    } <= approved_ids
    assert all(
        match.reference_value.level.value != "high"
        for match in result.case_centered.matched_cases
    )
    assert all(
        practice.source_case_ids
        and set(practice.source_case_ids)
        <= {match.case.case_id for match in result.case_centered.matched_cases}
        for practice in result.case_centered.transferable_practices
    )
    assert "成熟案例驗證" not in " ".join(result.case_centered.recommendation_basis)


def _score_unknowns(facts: tuple[FactRevision, ...]):
    from ai_poc_planner.application.case_centered_assessment import (
        build_deterministic_scores,
    )

    tokens = {f"F{index:03d}": item.id for index, item in enumerate(facts, start=1)}
    scores, _ = build_deterministic_scores(facts, tokens)
    return scores


def test_api_ui_and_markdown_share_the_same_case_centered_result() -> None:
    result = _formal_result(_scenario("knowledge_assist"))
    api_payload = {"case_centered": result.case_centered.model_dump(mode="json")}
    ui_view = case_centered_overview(api_payload)
    markdown = render_markdown(
        SimpleNamespace(section_items=lambda: ()),
        result,
        _facts(_scenario("knowledge_assist")),
    )

    assert ui_view["recommendation_title"] == result.case_centered.recommendation_title
    assert [item["title"] for item in ui_view["cases"]] == [
        item.case.title for item in result.case_centered.matched_cases
    ]
    assert result.case_centered.recommendation_title in markdown
    assert all(
        item.case.organization in markdown
        for item in result.case_centered.matched_cases
    )
    assert "準備階段（立即行動）" in markdown
    assert "第一階段 PoC" in markdown
