"""Public deterministic assessment composition entry point."""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from ai_poc_planner.assessment.gates import evaluate_hard_gates
from ai_poc_planner.assessment.scoring import (
    calculate_weighted_score,
    score_dimensions,
)
from ai_poc_planner.domain.enums import GateDisposition, Recommendation
from ai_poc_planner.domain.facts import AssessmentFacts, EvidenceBackedFacts
from ai_poc_planner.domain.models import EvidenceReference
from ai_poc_planner.domain.tools import AssessmentToolOutputs, ToolOutputContract
from ai_poc_planner.domain.workflow import Assessment, AssessmentInput

RULE_VERSION = "1.0"
RECOMMENDED_SCORE_THRESHOLD = 75
CONDITIONAL_SCORE_THRESHOLD = 55
TOOL_OUTPUT_FIELDS = (
    "retrieve_similar_cases",
    "assess_data_readiness",
    "assess_technical_fit_and_architecture",
    "evaluate_risk_and_hard_gates",
    "assess_business_value_roi_and_kpis",
    "estimate_poc_scope",
)


class AssessmentError(ValueError):
    """Stable domain error raised when a formal assessment cannot be produced."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def decide_recommendation(
    weighted_score: int, disposition: GateDisposition
) -> Recommendation:
    """Apply hard-gate caps before the approved 75/55 score thresholds."""
    if not 0 <= weighted_score <= 100:
        raise AssessmentError("invalid_weighted_score", "weighted score is invalid")
    if disposition is GateDisposition.BLOCKED:
        return Recommendation.NOT_RECOMMENDED
    if weighted_score < CONDITIONAL_SCORE_THRESHOLD:
        return Recommendation.NOT_RECOMMENDED
    if disposition in {
        GateDisposition.ASSISTIVE_ONLY,
        GateDisposition.REQUIRES_CONTROLS,
    }:
        return Recommendation.CONDITIONAL
    if weighted_score >= RECOMMENDED_SCORE_THRESHOLD:
        return Recommendation.RECOMMENDED
    return Recommendation.CONDITIONAL


def _require_complete_input(
    assessment_input: AssessmentInput,
) -> tuple[AssessmentFacts, AssessmentToolOutputs, UUID, object]:
    if (
        assessment_input.facts is None
        or assessment_input.tool_outputs is None
        or assessment_input.assessment_id is None
        or assessment_input.evaluated_at is None
    ):
        raise AssessmentError(
            "incomplete_assessment_input",
            "assessment input is incomplete for formal evaluation",
        )
    return (
        assessment_input.facts,
        assessment_input.tool_outputs,
        assessment_input.assessment_id,
        assessment_input.evaluated_at,
    )


def _validated_tool_outputs(
    outputs: AssessmentToolOutputs,
    *,
    project_id: UUID,
    session_id: UUID,
) -> dict[str, ToolOutputContract]:
    validated: dict[str, ToolOutputContract] = {}
    for field_name in TOOL_OUTPUT_FIELDS:
        output = getattr(outputs, field_name)
        if output is None:
            raise AssessmentError(
                "missing_tool_output",
                f"missing required tool output: {field_name}",
            )
        if output.project_id != project_id or output.session_id != session_id:
            raise AssessmentError(
                "invalid_tool_reference",
                f"tool reference does not match assessment: {field_name}",
            )
        if output.error is not None:
            raise AssessmentError(
                "assessment_tool_error",
                f"assessment tool failed: {field_name} ({output.error.code})",
            )
        validated[field_name] = output
    return validated


def _validate_evidence_ownership(
    evidence: EvidenceReference,
    *,
    project_id: UUID,
    session_id: UUID,
) -> None:
    if (
        evidence.project_id is not None
        and evidence.project_id != project_id
        or evidence.session_id is not None
        and evidence.session_id != session_id
    ):
        raise AssessmentError(
            "invalid_evidence_ownership",
            f"evidence ownership does not match assessment: {evidence.id}",
        )


def _evidence_registry(
    assessment_input: AssessmentInput,
    outputs: dict[str, ToolOutputContract],
) -> dict[UUID, EvidenceReference]:
    registry: dict[UUID, EvidenceReference] = {}
    candidates = list(assessment_input.evidence)
    retrieval = outputs["retrieve_similar_cases"]
    retrieval_evidence = getattr(retrieval, "evidence", None) or []
    candidates.extend(retrieval_evidence)
    for evidence in candidates:
        _validate_evidence_ownership(
            evidence,
            project_id=assessment_input.project_id,
            session_id=assessment_input.session_id,
        )
        existing = registry.get(evidence.id)
        if existing is not None and existing != evidence:
            raise AssessmentError(
                "contradictory_evidence",
                f"evidence ID has contradictory records: {evidence.id}",
            )
        registry[evidence.id] = evidence
    return registry


def _fact_groups(facts: AssessmentFacts) -> Iterable[EvidenceBackedFacts]:
    return (
        facts.business_value,
        facts.data_readiness,
        facts.technical_fit,
        facts.architecture_controllability,
        facts.governance_readiness,
        facts.user_adoption,
        facts.gates,
    )


def _validate_fact_evidence(
    facts: AssessmentFacts, registry: dict[UUID, EvidenceReference]
) -> set[UUID]:
    referenced = {
        evidence_id
        for group in _fact_groups(facts)
        for evidence_id in group.evidence_ids
    }
    unknown = sorted(referenced - registry.keys(), key=str)
    if unknown:
        raise AssessmentError(
            "invalid_evidence_reference",
            "unknown evidence reference: " + ", ".join(map(str, unknown)),
        )
    return referenced


def _tool_evidence_ids(
    outputs: dict[str, ToolOutputContract],
    registry: dict[UUID, EvidenceReference],
) -> set[UUID]:
    referenced: set[UUID] = set()
    for output in outputs.values():
        score_values = (
            getattr(output, field_name, None)
            for field_name in (
                "score",
                "technical_fit",
                "architecture_controllability",
                "governance_readiness",
                "business_value",
                "user_adoption",
            )
        )
        gate_values = getattr(output, "hard_gates", None) or []
        refs = [
            ref
            for value in score_values
            if value is not None
            for ref in value.evidence_refs
        ]
        refs.extend(ref for gate in gate_values for ref in gate.evidence_refs)
        for ref in refs:
            try:
                evidence_id = UUID(ref)
            except ValueError as error:
                raise AssessmentError(
                    "invalid_evidence_reference",
                    f"invalid tool evidence reference: {ref}",
                ) from error
            referenced.add(evidence_id)
    unknown = sorted(referenced - registry.keys(), key=str)
    if unknown:
        raise AssessmentError(
            "invalid_evidence_reference",
            "unknown evidence reference: " + ", ".join(map(str, unknown)),
        )
    return referenced


def _validate_consistent_facts(facts: AssessmentFacts) -> None:
    comparisons = (
        (
            "data_available",
            facts.data_readiness.data_available,
            facts.gates.data_available,
        ),
        (
            "digitization",
            facts.data_readiness.digitization,
            facts.gates.digitization,
        ),
        (
            "validation_sample_available",
            facts.data_readiness.validation_sample_available,
            facts.gates.validation_sample_available,
        ),
        (
            "lawful_basis_confirmed",
            facts.governance_readiness.lawful_basis_confirmed,
            facts.gates.lawful_basis_confirmed,
        ),
        (
            "accountable_owner_confirmed",
            facts.governance_readiness.accountable_owner_confirmed,
            facts.gates.accountable_owner_confirmed,
        ),
    )
    contradictory = [name for name, left, right in comparisons if left != right]
    if contradictory:
        raise AssessmentError(
            "contradictory_assessment_facts",
            "contradictory assessment facts: " + ", ".join(contradictory),
        )


def _validate_declared_gate_result(
    declared_output: ToolOutputContract,
    *,
    disposition: GateDisposition,
    rule_ids: set[str],
) -> None:
    declared_disposition = getattr(declared_output, "gate_disposition", None)
    declared_gates = getattr(declared_output, "hard_gates", None)
    declared_rule_ids = {gate.rule_id for gate in declared_gates or []}
    if declared_disposition is not disposition or declared_rule_ids != rule_ids:
        raise AssessmentError(
            "contradictory_tool_result",
            "contradictory gate result from structured tool output",
        )


def _recommendation_trace(weighted_score: int, disposition: GateDisposition) -> str:
    if disposition is GateDisposition.BLOCKED:
        return "REC-GATE-BLOCKED"
    if weighted_score < CONDITIONAL_SCORE_THRESHOLD:
        return "REC-SCORE-LOW"
    if disposition is GateDisposition.ASSISTIVE_ONLY:
        return "REC-GATE-ASSISTIVE"
    if disposition is GateDisposition.REQUIRES_CONTROLS:
        return "REC-GATE-CONTROLS"
    if weighted_score >= RECOMMENDED_SCORE_THRESHOLD:
        return "REC-SCORE-HIGH"
    return "REC-SCORE-CONDITIONAL"


def assess_project(assessment_input: AssessmentInput) -> Assessment:
    """Evaluate one fully structured input without I/O, models, or current time."""
    facts, output_bundle, assessment_id, evaluated_at = _require_complete_input(
        assessment_input
    )
    outputs = _validated_tool_outputs(
        output_bundle,
        project_id=assessment_input.project_id,
        session_id=assessment_input.session_id,
    )
    _validate_consistent_facts(facts)
    evidence_registry = _evidence_registry(assessment_input, outputs)
    referenced_evidence = _validate_fact_evidence(facts, evidence_registry)
    referenced_evidence |= _tool_evidence_ids(outputs, evidence_registry)

    scores = score_dimensions(facts)
    weighted_score = calculate_weighted_score(scores)
    gate_evaluation = evaluate_hard_gates(facts.gates)
    _validate_declared_gate_result(
        outputs["evaluate_risk_and_hard_gates"],
        disposition=gate_evaluation.disposition,
        rule_ids={gate.rule_id for gate in gate_evaluation.triggered},
    )
    recommendation = decide_recommendation(weighted_score, gate_evaluation.disposition)

    retrieval = outputs["retrieve_similar_cases"]
    cases = getattr(retrieval, "cases", None) or []
    retrieval_evidence = getattr(retrieval, "evidence", None) or []
    all_evidence = referenced_evidence | {item.id for item in retrieval_evidence}
    trace = _recommendation_trace(weighted_score, gate_evaluation.disposition)

    return Assessment(
        schema_version=assessment_input.schema_version,
        id=assessment_id,
        project_id=assessment_input.project_id,
        session_id=assessment_input.session_id,
        rule_version=RULE_VERSION,
        scores=scores,
        weighted_score=weighted_score,
        hard_gates=list(gate_evaluation.triggered),
        gate_disposition=gate_evaluation.disposition,
        recommendation=recommendation,
        matched_case_ids=sorted(case.case_id for case in cases),
        evidence_refs=sorted(str(item) for item in all_evidence),
        rationale=(
            f"[{trace}] Deterministic score {weighted_score}; "
            f"gate disposition {gate_evaluation.disposition.value}."
        ),
        created_at=evaluated_at,
    )
