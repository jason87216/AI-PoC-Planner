from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from ai_poc_planner.application.case_centered_assessment import (
    build_case_centered_assessment,
    build_deterministic_gate_evaluation,
    build_deterministic_scores,
    calculate_case_reference_value,
    calculate_project_case_fit,
    derive_recommendation_category,
    infer_opportunity_types,
    rank_case_matches,
)
from ai_poc_planner.domain.case_centered import RecommendationCategory
from ai_poc_planner.domain.catalog import OpportunityType
from ai_poc_planner.domain.enums import (
    DecisionAuthority,
    FactStatus,
    ProcessingBoundary,
)
from ai_poc_planner.domain.project_history import FactRevision
from ai_poc_planner.domain.reviewed_cases import ReviewedCase


def _case(case_id: str = "case-01", **updates: object) -> ReviewedCase:
    payload: dict[str, object] = {
        "case_id": case_id,
        "organization": "Example organisation",
        "title": "Permission request review assistance",
        "organization_type": "large enterprise",
        "applicable_context": ["manager approval", "permission workflow"],
        "opportunity_types": [
            OpportunityType.ENTERPRISE_KNOWLEDGE_AND_PROFESSIONAL_DOCUMENT_ASSIST.value
        ],
        "business_problem": "Standardise permission request review.",
        "workflow_scope": "Request, review, and approve access",
        "solution_pattern": "Role-based permission templates with human review",
        "required_inputs": ["employee role", "requested access"],
        "system_dependencies": ["role catalogue"],
        "governance_conditions": ["audit trail", "least privilege"],
        "decision_authority": "human_final_decision",
        "processing_boundary": "private_endpoint",
        "implementation_stage": "production assistive workflow",
        "implementation_method": "Role-based templates and review assistance.",
        "reported_outcomes": ["Fewer free-form requests."],
        "measurable_outcomes": ["Fewer free-form requests."],
        "applicability_tags": ["human_review"],
        "non_applicability_tags": ["autonomous_action"],
        "applicable_solution_keys": ["test-solution"],
        "human_oversight": ["Manager makes the final decision."],
        "risks_or_limitations": ["Requires a role catalogue."],
        "evidence_type": "official_company_disclosure",
        "evidence_grade": "A",
        "source_name": "Example source",
        "source_url": "https://example.test/case",
        "review_status": "approved",
    }
    payload.update(updates)
    return ReviewedCase.model_validate(payload)


def _fact(
    key: str, value: object, status: FactStatus = FactStatus.CONFIRMED
) -> FactRevision:
    return FactRevision(
        id=uuid4(),
        version_id=uuid4(),
        fact_key=key,
        value=value,
        status=status,
        reference_message_ids=[uuid4()],
        created_at=datetime.now(UTC),
    )


def _facts(
    *, different: bool = False, unknown_boundary: bool = False
) -> tuple[FactRevision, ...]:
    return (
        _fact("current_workflow_problem", "主管審核權限申請"),
        _fact("available_data", "員工職位與申請權限"),
        _fact("users_and_owners", "申請人與主管"),
        _fact(
            "known_constraints",
            "需要 audit trail 與 least privilege"
            if not different
            else "依賴集中式 IAM 與自動寫入",
        ),
        _fact(
            "human_final_decision",
            None if unknown_boundary else "主管保留最終核准",
            FactStatus.UNKNOWN if unknown_boundary else FactStatus.CONFIRMED,
        ),
    )


def test_reference_value_rewards_review_and_outcome_evidence() -> None:
    approved = calculate_case_reference_value(_case())
    incomplete = calculate_case_reference_value(
        _case(
            "case-02",
            reported_outcomes=[],
            measurable_outcomes=[],
            risks_or_limitations=[],
            evidence_grade="D",
        )
    )

    assert approved.score > incomplete.score
    assert approved.level.value in {"high", "medium"}
    assert incomplete.unknown_items


def test_project_case_fit_separates_differences_and_unknowns() -> None:
    close = calculate_project_case_fit(_facts(), _case())
    different = calculate_project_case_fit(_facts(different=True), _case())
    unknown = calculate_project_case_fit(
        _facts(unknown_boundary=True), _case(processing_boundary=None)
    )

    assert close.score > different.score
    assert any("系統" in item or "依賴" in item for item in different.key_differences)
    assert unknown.needs_confirmation
    assert any(item.status.value == "unknown" for item in unknown.dimensions)


def test_ranking_filters_review_status_and_is_repeatable() -> None:
    pending = _case("case-02", review_status="pending")
    cases = (_case("case-03"), pending, _case("case-01", evidence_grade="B"))
    first = rank_case_matches(
        cases,
        _facts(),
        opportunity_types=(
            OpportunityType.ENTERPRISE_KNOWLEDGE_AND_PROFESSIONAL_DOCUMENT_ASSIST,
        ),
        solution_key="test-solution",
        gate_results=(),
    )
    second = rank_case_matches(
        tuple(reversed(cases)),
        _facts(),
        opportunity_types=(
            OpportunityType.ENTERPRISE_KNOWLEDGE_AND_PROFESSIONAL_DOCUMENT_ASSIST,
        ),
        solution_key="test-solution",
        gate_results=(),
    )

    assert [item.case.case_id for item in first] == [
        item.case.case_id for item in second
    ]
    assert "case-02" not in {item.case.case_id for item in first}


def test_composition_has_source_bound_practices_and_no_case_is_honest() -> None:
    result = build_case_centered_assessment(
        cases=(_case(),),
        facts=_facts(),
        opportunity_types=(
            OpportunityType.ENTERPRISE_KNOWLEDGE_AND_PROFESSIONAL_DOCUMENT_ASSIST,
        ),
        solution_key="test-solution",
        recommendation_title="權限申請標準化與人工審核輔助",
        gate_results=(),
        option_kind="hybrid",
    )
    empty = build_case_centered_assessment(
        cases=(_case(),),
        facts=_facts(),
        opportunity_types=(OpportunityType.CUSTOMER_SERVICE_ASSIST,),
        solution_key="test-solution",
        recommendation_title="資料基礎建設優先路線",
        gate_results=(),
        option_kind="foundations_first",
    )

    assert result.matched_cases
    assert result.transferable_practices
    assert result.transferable_practices[0].source_case_ids == ["case-01"]
    assert empty.matching_status == "no_suitable_reviewed_case"
    assert empty.matched_cases == []
    assert "沒有足夠" in (empty.no_case_reason or "")


def test_scores_and_gates_are_deterministic_and_explain_unknowns() -> None:
    facts = _facts(unknown_boundary=True)
    tokens = {f"F{index:03d}": fact.id for index, fact in enumerate(facts, 1)}
    first_scores, first_total = build_deterministic_scores(facts, tokens)
    second_scores, second_total = build_deterministic_scores(facts, tokens)
    assert first_scores == second_scores
    assert first_total == second_total
    assert len(first_scores) == 6
    assert all(item.evaluation_subject for item in first_scores)
    assert any(item.unknown_fact_refs for item in first_scores)

    first_gates = build_deterministic_gate_evaluation(
        facts,
        selected_authority=DecisionAuthority.HUMAN_FINAL_DECISION,
        selected_boundary=ProcessingBoundary.LOCAL_ONLY,
    )
    second_gates = build_deterministic_gate_evaluation(
        facts,
        selected_authority=DecisionAuthority.HUMAN_FINAL_DECISION,
        selected_boundary=ProcessingBoundary.LOCAL_ONLY,
    )
    assert first_gates == second_gates


def test_opportunity_inference_uses_confirmed_facts_not_model_options() -> None:
    inferred = infer_opportunity_types(_facts())

    assert inferred == (
        OpportunityType.ENTERPRISE_KNOWLEDGE_AND_PROFESSIONAL_DOCUMENT_ASSIST,
    )
    assert OpportunityType.PREDICTIVE_MAINTENANCE not in inferred


def test_permission_request_rules_with_human_approval_prefer_governed_route() -> None:
    """A missing validation set must not hide a controlled access workflow."""

    facts = (
        _fact(
            "current_workflow_problem",
            "員工以 Email 與 Excel 提出權限申請，主管逐案審核。",
        ),
        _fact(
            "desired_outcome",
            "建立權限申請標準化、固定規則檢查與可追蹤的人工核准流程。",
        ),
        _fact("available_data", "員工職位資料、既有權限清單與申請紀錄。"),
        _fact("users_and_owners", "員工申請，主管最終核准，IT 人員實際開通。"),
        _fact(
            "known_constraints",
            "第一階段不得 AI 自動核准或直接開通，必須保留人工複核與稽核紀錄。",
        ),
    )

    assert derive_recommendation_category(facts, ()) is (
        RecommendationCategory.GOVERNED_ASSISTIVE
    )
