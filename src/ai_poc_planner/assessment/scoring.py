"""Pure 1–5 rubric rules and stable Decimal-based weighting."""

from __future__ import annotations

from collections.abc import Iterable
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from ai_poc_planner.domain.enums import DigitizationLevel, ScoreDimension
from ai_poc_planner.domain.facts import (
    ArchitectureControllabilityFacts,
    AssessmentFacts,
    BusinessValueFacts,
    DataReadinessFacts,
    EvidenceBackedFacts,
    GovernanceReadinessFacts,
    TechnicalFitFacts,
    UserAdoptionFacts,
)
from ai_poc_planner.domain.models import SCORE_WEIGHTS, ScoreDimensionResult

CONTRIBUTION_QUANTUM = Decimal("0.01")
TOTAL_QUANTUM = Decimal("1")


class AssessmentScoringError(ValueError):
    """Raised when score collections violate the normative six-dimension set."""


def calculate_weighted_points(rating: int, weight: int) -> Decimal:
    """Return ``rating / 5 * weight``, rounded half-up to 0.01 points."""
    if not 1 <= rating <= 5:
        raise AssessmentScoringError("rating must be between 1 and 5")
    if not 1 <= weight <= 100:
        raise AssessmentScoringError("weight must be between 1 and 100")
    return (Decimal(rating) * Decimal(weight) / Decimal(5)).quantize(
        CONTRIBUTION_QUANTUM, rounding=ROUND_HALF_UP
    )


def round_score(value: Decimal) -> int:
    """Round a total to a whole point using decimal ROUND_HALF_UP."""
    return int(value.quantize(TOTAL_QUANTUM, rounding=ROUND_HALF_UP))


def calculate_weighted_score(scores: Iterable[ScoreDimensionResult]) -> int:
    """Recompute, never trust, each contribution and return the 0–100 total."""
    materialized = list(scores)
    dimensions = [score.dimension for score in materialized]
    if len(dimensions) != len(SCORE_WEIGHTS) or set(dimensions) != set(SCORE_WEIGHTS):
        raise AssessmentScoringError(
            "scores must contain each normative dimension exactly once"
        )
    by_dimension = {score.dimension: score for score in materialized}
    total = sum(
        (
            calculate_weighted_points(
                by_dimension[dimension].rating, SCORE_WEIGHTS[dimension]
            )
            for dimension in SCORE_WEIGHTS
        ),
        start=Decimal("0"),
    )
    return round_score(total)


def _evidence_refs(evidence_ids: list[UUID]) -> list[str]:
    return sorted(str(item) for item in evidence_ids)


def _build_result(
    dimension: ScoreDimension,
    rating: int,
    rule_id: str,
    rationale: str,
    facts: EvidenceBackedFacts,
) -> ScoreDimensionResult:
    if not facts.evidence_ids and rating > 2:
        rating = 2
        rule_id = "SC-EVIDENCE-CAP"
        rationale = "Required evidence is missing; the rating is conservatively capped."
    weight = SCORE_WEIGHTS[dimension]
    return ScoreDimensionResult(
        dimension=dimension,
        rating=rating,
        weight=weight,
        weighted_points=float(calculate_weighted_points(rating, weight)),
        rationale=f"[{rule_id}] {rationale}",
        evidence_refs=_evidence_refs(facts.evidence_ids),
    )


def score_business_value(facts: BusinessValueFacts) -> ScoreDimensionResult:
    if all(
        (
            facts.pain_defined,
            facts.beneficiary_defined,
            facts.owner_identified,
            facts.owner_approved,
            facts.quantitative_baseline,
            facts.target_kpi_defined,
            facts.benefit_assumptions_documented,
            facts.cost_baseline_available,
            facts.roi_formula_available,
        )
    ):
        rating = 5
    elif all(
        (
            facts.pain_defined,
            facts.beneficiary_defined,
            facts.owner_identified,
            facts.quantitative_baseline,
            facts.target_kpi_defined,
            facts.benefit_assumptions_documented,
        )
    ):
        rating = 4
    elif facts.owner_identified and facts.quantitative_baseline:
        rating = 3
    elif facts.pain_defined:
        rating = 2
    else:
        rating = 1
    return _build_result(
        ScoreDimension.BUSINESS_VALUE,
        rating,
        f"SC-BV-0{rating}",
        "Business value and ROI facts match the approved rubric anchor.",
        facts,
    )


def score_data_readiness(facts: DataReadinessFacts) -> ScoreDimensionResult:
    if not facts.data_available or not facts.lawful_access:
        rating = 1
    elif all(
        (
            facts.digitization is DigitizationLevel.COMPLETE,
            facts.quality_measured,
            facts.validation_sample_available,
            facts.representative_validation_sample,
        )
    ):
        rating = 5
    elif all(
        (
            facts.digitization
            in {DigitizationLevel.MOSTLY, DigitizationLevel.COMPLETE},
            facts.quality_sampled,
            facts.gaps_resolvable_in_poc,
        )
    ):
        rating = 4
    elif facts.digitization in {
        DigitizationLevel.PARTIAL,
        DigitizationLevel.MOSTLY,
        DigitizationLevel.COMPLETE,
    }:
        rating = 3
    else:
        rating = 2
    return _build_result(
        ScoreDimension.DATA_READINESS,
        rating,
        f"SC-DATA-0{rating}",
        "Availability, access, digitization, quality, and validation facts were "
        "evaluated.",
        facts,
    )


def score_technical_fit(facts: TechnicalFitFacts) -> ScoreDimensionResult:
    capability_needed = any(
        (
            facts.retrieval_required,
            facts.reasoning_required,
            facts.tool_collaboration_required,
        )
    )
    if not facts.ai_needed or not facts.technically_feasible:
        rating = 1
    elif facts.traditional_solution_preferred:
        rating = 2
    elif all(
        (
            facts.technical_path_defined,
            capability_needed,
            facts.boundaries_defined,
            facts.key_assumptions_testable,
        )
    ):
        rating = 5
    elif facts.technical_path_defined and capability_needed:
        rating = 4
    else:
        rating = 3
    return _build_result(
        ScoreDimension.TECHNICAL_FIT,
        rating,
        f"SC-TECH-0{rating}",
        "AI necessity, simpler alternatives, path clarity, and testability were "
        "evaluated.",
        facts,
    )


def score_architecture_controllability(
    facts: ArchitectureControllabilityFacts,
) -> ScoreDimensionResult:
    if facts.unknown_dependency_count >= 3 or (
        facts.high_risk_integration_count >= 3 and not facts.test_environment_available
    ):
        rating = 1
    elif facts.high_risk_integration_count >= 2 and not facts.interfaces_known:
        rating = 2
    elif all(
        (
            facts.integration_count <= 1,
            facts.interfaces_known,
            facts.test_environment_available,
            facts.data_boundary_defined,
            facts.dependencies_replaceable,
            facts.observability_available,
            facts.reproducible_environment,
        )
    ):
        rating = 5
    elif all(
        (
            facts.integration_count <= 2,
            facts.interfaces_known,
            facts.test_environment_available,
            facts.data_boundary_defined,
        )
    ):
        rating = 4
    else:
        rating = 3
    return _build_result(
        ScoreDimension.ARCHITECTURE_CONTROLLABILITY,
        rating,
        f"SC-ARCH-0{rating}",
        "Integration risk, testability, boundaries, and operability were evaluated.",
        facts,
    )


def score_governance_readiness(
    facts: GovernanceReadinessFacts,
) -> ScoreDimensionResult:
    if not all(
        (
            facts.lawful_basis_confirmed,
            facts.accountable_owner_confirmed,
            facts.data_boundary_defined,
        )
    ):
        rating = 1
    elif all(
        (
            facts.policy_defined,
            facts.reviewer_identified,
            facts.minimization_defined,
            facts.retention_defined,
            facts.approved_policy,
            facts.formal_risk_assessment,
            facts.audit_records_available,
            facts.incident_process_defined,
        )
    ):
        rating = 5
    elif all(
        (
            facts.policy_defined,
            facts.reviewer_identified,
            facts.minimization_defined,
            facts.retention_defined,
        )
    ):
        rating = 4
    elif all(
        (
            facts.data_types_identified,
            facts.risks_identified,
            facts.controls_identified,
        )
    ):
        rating = 3
    else:
        rating = 2
    return _build_result(
        ScoreDimension.GOVERNANCE_READINESS,
        rating,
        f"SC-GOV-0{rating}",
        "Authority, ownership, controls, policy, audit, and incident readiness "
        "were evaluated.",
        facts,
    )


def score_user_adoption(facts: UserAdoptionFacts) -> ScoreDimensionResult:
    if facts.users_opposed or not facts.process_owner_confirmed:
        rating = 1
    elif all(
        (
            facts.affected_roles_involved,
            facts.value_proposition_clear,
            facts.representative_users_committed,
            facts.workflow_adjusted,
            facts.training_plan_defined,
            facts.feedback_process_defined,
            facts.users_co_designed,
            facts.adoption_metrics_defined,
            facts.support_owner_confirmed,
            facts.iteration_owner_confirmed,
        )
    ):
        rating = 5
    elif all(
        (
            facts.affected_roles_involved,
            facts.representative_users_committed,
            facts.workflow_adjusted,
            facts.training_plan_defined,
            facts.feedback_process_defined,
        )
    ):
        rating = 4
    elif all(
        (
            facts.affected_roles_involved,
            facts.value_proposition_clear,
            facts.representative_users_committed,
        )
    ):
        rating = 3
    else:
        rating = 2
    return _build_result(
        ScoreDimension.USER_ADOPTION,
        rating,
        f"SC-ADOPT-0{rating}",
        "Ownership, participation, training, feedback, and adoption "
        "accountability were evaluated.",
        facts,
    )


def score_dimensions(facts: AssessmentFacts) -> list[ScoreDimensionResult]:
    """Score all dimensions in the single canonical weight-table order."""
    scores = {
        ScoreDimension.BUSINESS_VALUE: score_business_value(facts.business_value),
        ScoreDimension.DATA_READINESS: score_data_readiness(facts.data_readiness),
        ScoreDimension.TECHNICAL_FIT: score_technical_fit(facts.technical_fit),
        ScoreDimension.ARCHITECTURE_CONTROLLABILITY: (
            score_architecture_controllability(facts.architecture_controllability)
        ),
        ScoreDimension.GOVERNANCE_READINESS: score_governance_readiness(
            facts.governance_readiness
        ),
        ScoreDimension.USER_ADOPTION: score_user_adoption(facts.user_adoption),
    }
    return [scores[dimension] for dimension in SCORE_WEIGHTS]
