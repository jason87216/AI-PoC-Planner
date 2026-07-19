from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import ValidationError

from ai_poc_planner.assessment.scoring import (
    AssessmentScoringError,
    calculate_weighted_points,
    calculate_weighted_score,
    round_score,
    score_architecture_controllability,
    score_business_value,
    score_data_readiness,
    score_dimensions,
    score_governance_readiness,
    score_technical_fit,
    score_user_adoption,
)
from ai_poc_planner.domain.enums import DigitizationLevel, ScoreDimension
from ai_poc_planner.domain.facts import (
    ArchitectureControllabilityFacts,
    AssessmentFacts,
    BusinessValueFacts,
    DataReadinessFacts,
    GateFacts,
    GovernanceReadinessFacts,
    TechnicalFitFacts,
    UserAdoptionFacts,
)
from ai_poc_planner.domain.models import SCORE_WEIGHTS, ScoreDimensionResult

EVIDENCE_ID = UUID("00000000-0000-0000-0000-000000001001")


def _business(rating: int) -> BusinessValueFacts:
    values: dict[int, dict[str, object]] = {
        1: {},
        2: {"pain_defined": True},
        3: {
            "pain_defined": True,
            "owner_identified": True,
            "quantitative_baseline": True,
        },
        4: {
            "pain_defined": True,
            "beneficiary_defined": True,
            "owner_identified": True,
            "quantitative_baseline": True,
            "target_kpi_defined": True,
            "benefit_assumptions_documented": True,
        },
        5: {
            "pain_defined": True,
            "beneficiary_defined": True,
            "owner_identified": True,
            "owner_approved": True,
            "quantitative_baseline": True,
            "target_kpi_defined": True,
            "benefit_assumptions_documented": True,
            "cost_baseline_available": True,
            "roi_formula_available": True,
        },
    }
    return BusinessValueFacts(evidence_ids=[EVIDENCE_ID], **values[rating])


def _data(rating: int) -> DataReadinessFacts:
    values: dict[int, dict[str, object]] = {
        1: {},
        2: {
            "data_available": True,
            "lawful_access": True,
            "digitization": DigitizationLevel.NONE,
        },
        3: {
            "data_available": True,
            "lawful_access": True,
            "digitization": DigitizationLevel.PARTIAL,
        },
        4: {
            "data_available": True,
            "lawful_access": True,
            "digitization": DigitizationLevel.MOSTLY,
            "quality_known": True,
            "quality_sampled": True,
            "gaps_resolvable_in_poc": True,
        },
        5: {
            "data_available": True,
            "lawful_access": True,
            "digitization": DigitizationLevel.COMPLETE,
            "quality_known": True,
            "quality_sampled": True,
            "quality_measured": True,
            "validation_sample_available": True,
            "representative_validation_sample": True,
            "gaps_resolvable_in_poc": True,
        },
    }
    return DataReadinessFacts(evidence_ids=[EVIDENCE_ID], **values[rating])


def _technical(rating: int) -> TechnicalFitFacts:
    values: dict[int, dict[str, object]] = {
        1: {},
        2: {
            "ai_needed": True,
            "technically_feasible": True,
            "traditional_solution_preferred": True,
        },
        3: {"ai_needed": True, "technically_feasible": True},
        4: {
            "ai_needed": True,
            "technically_feasible": True,
            "technical_path_defined": True,
            "retrieval_required": True,
        },
        5: {
            "ai_needed": True,
            "technically_feasible": True,
            "technical_path_defined": True,
            "retrieval_required": True,
            "boundaries_defined": True,
            "key_assumptions_testable": True,
        },
    }
    return TechnicalFitFacts(evidence_ids=[EVIDENCE_ID], **values[rating])


def _architecture(rating: int) -> ArchitectureControllabilityFacts:
    values: dict[int, dict[str, object]] = {
        1: {
            "integration_count": 4,
            "high_risk_integration_count": 3,
            "unknown_dependency_count": 3,
        },
        2: {
            "integration_count": 3,
            "high_risk_integration_count": 2,
            "unknown_dependency_count": 1,
        },
        3: {
            "integration_count": 2,
            "high_risk_integration_count": 1,
            "unknown_dependency_count": 1,
            "mocks_available": True,
        },
        4: {
            "integration_count": 2,
            "interfaces_known": True,
            "test_environment_available": True,
            "data_boundary_defined": True,
        },
        5: {
            "integration_count": 1,
            "interfaces_known": True,
            "test_environment_available": True,
            "data_boundary_defined": True,
            "dependencies_replaceable": True,
            "observability_available": True,
            "reproducible_environment": True,
        },
    }
    return ArchitectureControllabilityFacts(
        evidence_ids=[EVIDENCE_ID], **values[rating]
    )


def _governance(rating: int) -> GovernanceReadinessFacts:
    values: dict[int, dict[str, object]] = {
        1: {},
        2: {
            "lawful_basis_confirmed": True,
            "accountable_owner_confirmed": True,
            "data_boundary_defined": True,
            "data_types_identified": True,
            "risks_identified": True,
        },
        3: {
            "lawful_basis_confirmed": True,
            "accountable_owner_confirmed": True,
            "data_boundary_defined": True,
            "data_types_identified": True,
            "risks_identified": True,
            "controls_identified": True,
        },
        4: {
            "lawful_basis_confirmed": True,
            "accountable_owner_confirmed": True,
            "data_boundary_defined": True,
            "data_types_identified": True,
            "risks_identified": True,
            "controls_identified": True,
            "policy_defined": True,
            "reviewer_identified": True,
            "minimization_defined": True,
            "retention_defined": True,
        },
        5: {
            "lawful_basis_confirmed": True,
            "accountable_owner_confirmed": True,
            "data_boundary_defined": True,
            "data_types_identified": True,
            "risks_identified": True,
            "controls_identified": True,
            "policy_defined": True,
            "reviewer_identified": True,
            "minimization_defined": True,
            "retention_defined": True,
            "approved_policy": True,
            "formal_risk_assessment": True,
            "audit_records_available": True,
            "incident_process_defined": True,
        },
    }
    return GovernanceReadinessFacts(evidence_ids=[EVIDENCE_ID], **values[rating])


def _adoption(rating: int) -> UserAdoptionFacts:
    values: dict[int, dict[str, object]] = {
        1: {"users_opposed": True},
        2: {"process_owner_confirmed": True},
        3: {
            "process_owner_confirmed": True,
            "affected_roles_involved": True,
            "value_proposition_clear": True,
            "representative_users_committed": True,
        },
        4: {
            "process_owner_confirmed": True,
            "affected_roles_involved": True,
            "value_proposition_clear": True,
            "representative_users_committed": True,
            "workflow_adjusted": True,
            "training_plan_defined": True,
            "feedback_process_defined": True,
        },
        5: {
            "process_owner_confirmed": True,
            "affected_roles_involved": True,
            "value_proposition_clear": True,
            "representative_users_committed": True,
            "workflow_adjusted": True,
            "training_plan_defined": True,
            "feedback_process_defined": True,
            "users_co_designed": True,
            "adoption_metrics_defined": True,
            "support_owner_confirmed": True,
            "iteration_owner_confirmed": True,
        },
    }
    return UserAdoptionFacts(evidence_ids=[EVIDENCE_ID], **values[rating])


SCORERS = {
    ScoreDimension.BUSINESS_VALUE: (score_business_value, _business),
    ScoreDimension.DATA_READINESS: (score_data_readiness, _data),
    ScoreDimension.TECHNICAL_FIT: (score_technical_fit, _technical),
    ScoreDimension.ARCHITECTURE_CONTROLLABILITY: (
        score_architecture_controllability,
        _architecture,
    ),
    ScoreDimension.GOVERNANCE_READINESS: (score_governance_readiness, _governance),
    ScoreDimension.USER_ADOPTION: (score_user_adoption, _adoption),
}


def _score_result(dimension: ScoreDimension, rating: int) -> ScoreDimensionResult:
    return ScoreDimensionResult(
        dimension=dimension,
        rating=rating,
        weight=SCORE_WEIGHTS[dimension],
        weighted_points=float(
            calculate_weighted_points(rating, SCORE_WEIGHTS[dimension])
        ),
        rationale="Known deterministic score.",
        evidence_refs=[str(EVIDENCE_ID)],
    )


def _assessment_facts(rating: int) -> AssessmentFacts:
    return AssessmentFacts(
        business_value=_business(rating),
        data_readiness=_data(rating),
        technical_fit=_technical(rating),
        architecture_controllability=_architecture(rating),
        governance_readiness=_governance(rating),
        user_adoption=_adoption(rating),
        gates=GateFacts(
            evidence_ids=[EVIDENCE_ID],
            authorization_confirmed=True,
            lawful_basis_confirmed=True,
            accountable_owner_confirmed=True,
            prohibited_use=False,
            high_impact_domain="none",
            autonomous_final_decision=False,
            autonomous_enterprise_action=False,
            meaningful_human_review=True,
            contest_or_review_path=True,
            personal_data=False,
            sensitive_data=False,
            minimization_control=True,
            retention_control=True,
            access_control=True,
            security_controls_confirmed=True,
            security_controls_required=False,
            governance_controls_confirmed=True,
            governance_controls_required=False,
            audit_controls_confirmed=True,
            audit_controls_required=False,
            data_boundary="external_allowed",
            external_endpoint_requested=False,
            data_available=True,
            digitization="complete",
            validation_sample_available=True,
        ),
    )


def test_weight_source_contains_exactly_six_normative_dimensions() -> None:
    assert SCORE_WEIGHTS == {
        ScoreDimension.BUSINESS_VALUE: 25,
        ScoreDimension.DATA_READINESS: 20,
        ScoreDimension.TECHNICAL_FIT: 15,
        ScoreDimension.ARCHITECTURE_CONTROLLABILITY: 15,
        ScoreDimension.GOVERNANCE_READINESS: 15,
        ScoreDimension.USER_ADOPTION: 10,
    }
    assert sum(SCORE_WEIGHTS.values()) == 100


@pytest.mark.parametrize("dimension", list(SCORERS))
@pytest.mark.parametrize("rating", [1, 2, 3, 4, 5])
def test_each_rubric_has_explicit_one_to_five_boundaries(
    dimension: ScoreDimension, rating: int
) -> None:
    scorer, facts_factory = SCORERS[dimension]

    result = scorer(facts_factory(rating))

    assert result.dimension is dimension
    assert result.rating == rating
    assert result.weight == SCORE_WEIGHTS[dimension]
    assert result.rationale


@pytest.mark.parametrize("dimension", list(SCORERS))
def test_missing_evidence_caps_each_rubric_at_two(
    dimension: ScoreDimension,
) -> None:
    scorer, facts_factory = SCORERS[dimension]
    high_facts = facts_factory(5).model_copy(update={"evidence_ids": []})

    result = scorer(high_facts)

    assert result.rating == 2
    assert "SC-EVIDENCE-CAP" in result.rationale


def test_all_fives_total_one_hundred() -> None:
    scores = [_score_result(dimension, 5) for dimension in SCORE_WEIGHTS]

    assert calculate_weighted_score(scores) == 100


def test_all_ones_total_twenty() -> None:
    scores = [_score_result(dimension, 1) for dimension in SCORE_WEIGHTS]

    assert calculate_weighted_score(scores) == 20


def test_known_score_set_totals_seventy_three() -> None:
    ratings = [4, 3, 4, 4, 3, 4]
    scores = [
        _score_result(dimension, rating)
        for dimension, rating in zip(SCORE_WEIGHTS, ratings, strict=True)
    ]

    assert calculate_weighted_score(scores) == 73
    assert Decimal(str(sum(item.weighted_points for item in scores))) == Decimal("73.0")


def test_rounding_uses_decimal_half_up() -> None:
    assert round_score(Decimal("54.49")) == 54
    assert round_score(Decimal("54.50")) == 55


def test_weighted_calculation_is_independent_of_input_order() -> None:
    scores = [_score_result(dimension, 4) for dimension in SCORE_WEIGHTS]

    assert calculate_weighted_score(scores) == calculate_weighted_score(
        list(reversed(scores))
    )


def test_weighted_calculation_rejects_missing_dimension() -> None:
    scores = [_score_result(dimension, 4) for dimension in SCORE_WEIGHTS][:-1]

    with pytest.raises(AssessmentScoringError, match="exactly once"):
        calculate_weighted_score(scores)


def test_weighted_calculation_rejects_duplicate_dimension() -> None:
    scores = [_score_result(dimension, 4) for dimension in SCORE_WEIGHTS]
    scores[-1] = scores[0]

    with pytest.raises(AssessmentScoringError, match="exactly once"):
        calculate_weighted_score(scores)


def test_unknown_dimension_is_rejected_by_contract() -> None:
    with pytest.raises(ValidationError):
        ScoreDimensionResult.model_validate(
            {
                "dimension": "invented_dimension",
                "rating": 3,
                "weight": 10,
                "weighted_points": 6,
                "rationale": "Unknown dimensions are not allowed.",
                "evidence_refs": [],
            }
        )


def test_score_dimensions_returns_canonical_order_and_exact_total() -> None:
    scores = score_dimensions(_assessment_facts(4))

    assert [score.dimension for score in scores] == list(SCORE_WEIGHTS)
    assert calculate_weighted_score(scores) == 80
