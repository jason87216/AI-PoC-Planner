from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from ai_poc_planner.assessment import AssessmentError, assess_project
from ai_poc_planner.assessment.engine import decide_recommendation
from ai_poc_planner.assessment.gates import evaluate_hard_gates
from ai_poc_planner.domain.enums import (
    DataBoundary,
    DigitizationLevel,
    EvidenceSourceType,
    GateDisposition,
    HighImpactDomain,
    Recommendation,
    ScoreDimension,
)
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
from ai_poc_planner.domain.models import (
    SCORE_WEIGHTS,
    ArchitectureOption,
    ScoreDimensionResult,
    SimilarCase,
)
from ai_poc_planner.domain.tools import (
    AssessBusinessValueRoiAndKpisOutput,
    AssessDataReadinessOutput,
    AssessmentToolOutputs,
    AssessTechnicalFitAndArchitectureOutput,
    EstimatePocScopeOutput,
    EvaluateRiskAndHardGatesOutput,
    KpiProposal,
    RetrieveSimilarCasesOutput,
    ToolError,
)
from ai_poc_planner.domain.workflow import (
    Assessment,
    AssessmentInput,
    EvidenceReference,
)

PROJECT_ID = UUID("00000000-0000-0000-0000-000000002001")
SESSION_ID = UUID("00000000-0000-0000-0000-000000002002")
ASSESSMENT_ID = UUID("00000000-0000-0000-0000-000000002003")
CORRELATION_ID = UUID("00000000-0000-0000-0000-000000002004")
EVIDENCE_ID = UUID("00000000-0000-0000-0000-000000002005")
EVALUATED_AT = datetime(2026, 7, 19, 14, 0, tzinfo=UTC)


def _evidence(
    *, project_id: UUID = PROJECT_ID, session_id: UUID = SESSION_ID
) -> EvidenceReference:
    return EvidenceReference(
        id=EVIDENCE_ID,
        project_id=project_id,
        session_id=session_id,
        source_type=EvidenceSourceType.INTERVIEW,
        source_ref="turn:1",
        label="Approved structured assessment facts",
        metadata={
            "project_id": str(project_id),
            "session_id": str(session_id),
        },
    )


def _high_facts(*, gates: GateFacts | None = None) -> AssessmentFacts:
    evidence = [EVIDENCE_ID]
    return AssessmentFacts(
        business_value=BusinessValueFacts(
            evidence_ids=evidence,
            pain_defined=True,
            beneficiary_defined=True,
            owner_identified=True,
            owner_approved=True,
            quantitative_baseline=True,
            target_kpi_defined=True,
            benefit_assumptions_documented=True,
            cost_baseline_available=True,
            roi_formula_available=True,
        ),
        data_readiness=DataReadinessFacts(
            evidence_ids=evidence,
            data_available=True,
            lawful_access=True,
            digitization=DigitizationLevel.COMPLETE,
            quality_known=True,
            quality_sampled=True,
            quality_measured=True,
            validation_sample_available=True,
            representative_validation_sample=True,
            gaps_resolvable_in_poc=True,
        ),
        technical_fit=TechnicalFitFacts(
            evidence_ids=evidence,
            ai_needed=True,
            technically_feasible=True,
            technical_path_defined=True,
            retrieval_required=True,
            boundaries_defined=True,
            key_assumptions_testable=True,
        ),
        architecture_controllability=ArchitectureControllabilityFacts(
            evidence_ids=evidence,
            integration_count=1,
            interfaces_known=True,
            test_environment_available=True,
            data_boundary_defined=True,
            dependencies_replaceable=True,
            observability_available=True,
            reproducible_environment=True,
        ),
        governance_readiness=GovernanceReadinessFacts(
            evidence_ids=evidence,
            lawful_basis_confirmed=True,
            accountable_owner_confirmed=True,
            data_boundary_defined=True,
            data_types_identified=True,
            risks_identified=True,
            controls_identified=True,
            policy_defined=True,
            reviewer_identified=True,
            minimization_defined=True,
            retention_defined=True,
            approved_policy=True,
            formal_risk_assessment=True,
            audit_records_available=True,
            incident_process_defined=True,
        ),
        user_adoption=UserAdoptionFacts(
            evidence_ids=evidence,
            process_owner_confirmed=True,
            affected_roles_involved=True,
            value_proposition_clear=True,
            representative_users_committed=True,
            workflow_adjusted=True,
            training_plan_defined=True,
            feedback_process_defined=True,
            users_co_designed=True,
            adoption_metrics_defined=True,
            support_owner_confirmed=True,
            iteration_owner_confirmed=True,
        ),
        gates=gates or _pass_gate_facts(),
    )


def _pass_gate_facts(**overrides: object) -> GateFacts:
    values: dict[str, object] = {
        "evidence_ids": [EVIDENCE_ID],
        "authorization_confirmed": True,
        "lawful_basis_confirmed": True,
        "accountable_owner_confirmed": True,
        "prohibited_use": False,
        "high_impact_domain": HighImpactDomain.NONE,
        "autonomous_final_decision": False,
        "autonomous_enterprise_action": False,
        "meaningful_human_review": True,
        "contest_or_review_path": True,
        "personal_data": False,
        "sensitive_data": False,
        "minimization_control": True,
        "retention_control": True,
        "access_control": True,
        "security_controls_confirmed": True,
        "security_controls_required": False,
        "governance_controls_confirmed": True,
        "governance_controls_required": False,
        "audit_controls_confirmed": True,
        "audit_controls_required": False,
        "data_boundary": DataBoundary.EXTERNAL_ALLOWED,
        "external_endpoint_requested": False,
        "data_available": True,
        "digitization": DigitizationLevel.COMPLETE,
        "validation_sample_available": True,
    }
    values.update(overrides)
    return GateFacts.model_validate(values)


def _declared_score(dimension: ScoreDimension, rating: int = 1) -> ScoreDimensionResult:
    weight = SCORE_WEIGHTS[dimension]
    return ScoreDimensionResult(
        dimension=dimension,
        rating=rating,
        weight=weight,
        weighted_points=rating / 5 * weight,
        rationale="Non-authoritative tool declaration.",
        evidence_refs=[str(EVIDENCE_ID)],
    )


def _context(
    *, project_id: UUID = PROJECT_ID, session_id: UUID = SESSION_ID
) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "correlation_id": CORRELATION_ID,
        "project_id": project_id,
        "session_id": session_id,
    }


def _tool_outputs(
    facts: AssessmentFacts,
    *,
    project_id: UUID = PROJECT_ID,
    session_id: UUID = SESSION_ID,
) -> AssessmentToolOutputs:
    context = _context(project_id=project_id, session_id=session_id)
    gate_evaluation = evaluate_hard_gates(facts.gates)
    return AssessmentToolOutputs(
        retrieve_similar_cases=RetrieveSimilarCasesOutput(
            **context,
            cases=[
                SimilarCase(
                    case_id="case-001",
                    title="Synthetic support case",
                    similarity=0.8,
                    fit_summary="A bounded retrieval workflow with human review.",
                    source_ref="case_library/case-001.md",
                )
            ],
            evidence=[],
        ),
        assess_data_readiness=AssessDataReadinessOutput(
            **context,
            score=_declared_score(ScoreDimension.DATA_READINESS),
            gaps=[],
            prerequisites=[],
            rationale="Tool facts collected.",
        ),
        assess_technical_fit_and_architecture=(
            AssessTechnicalFitAndArchitectureOutput(
                **context,
                technical_fit=_declared_score(ScoreDimension.TECHNICAL_FIT),
                architecture_controllability=_declared_score(
                    ScoreDimension.ARCHITECTURE_CONTROLLABILITY
                ),
                architecture_options=[
                    ArchitectureOption(
                        name="local retrieval",
                        summary="Local deterministic test option.",
                        deployment="local",
                        components=["retrieval", "review"],
                        assumptions=[],
                    )
                ],
                rationale="Tool facts collected.",
            )
        ),
        evaluate_risk_and_hard_gates=EvaluateRiskAndHardGatesOutput(
            **context,
            rule_version="1.0",
            hard_gates=list(gate_evaluation.triggered),
            gate_disposition=gate_evaluation.disposition,
            governance_readiness=_declared_score(ScoreDimension.GOVERNANCE_READINESS),
        ),
        assess_business_value_roi_and_kpis=(
            AssessBusinessValueRoiAndKpisOutput(
                **context,
                business_value=_declared_score(ScoreDimension.BUSINESS_VALUE),
                user_adoption=_declared_score(ScoreDimension.USER_ADOPTION),
                roi_assumptions=["Synthetic fixed assumption"],
                kpi_proposals=[
                    KpiProposal(
                        name="cycle time",
                        unit="minutes",
                        baseline=10,
                        target=5,
                        direction="decrease",
                    )
                ],
                rationale="Tool facts collected.",
            )
        ),
        estimate_poc_scope=EstimatePocScopeOutput(
            **context,
            estimated_weeks=2,
            roles=["AI engineer", "process owner"],
            complexity_points=3,
            assumptions=["No enterprise write integration"],
        ),
    )


def _assessment_input(
    *,
    facts: AssessmentFacts | None = None,
    tool_outputs: AssessmentToolOutputs | None = None,
    evidence: list[EvidenceReference] | None = None,
) -> AssessmentInput:
    normalized_facts = facts or _high_facts()
    return AssessmentInput(
        schema_version="1.0",
        project_id=PROJECT_ID,
        session_id=SESSION_ID,
        assessment_id=ASSESSMENT_ID,
        evaluated_at=EVALUATED_AT,
        known_information={"problem": "Synthetic deterministic assessment"},
        facts=normalized_facts,
        tool_outputs=tool_outputs or _tool_outputs(normalized_facts),
        evidence=evidence if evidence is not None else [_evidence()],
    )


def _error_output(output_type: type, *, code: str = "tool_failed") -> object:
    return output_type(
        **_context(),
        error=ToolError(
            code=code,
            message="Synthetic tool failure.",
            retryable=False,
            details={},
        ),
    )


@pytest.fixture
def high_value_low_risk_case() -> AssessmentInput:
    return _assessment_input()


@pytest.fixture
def high_score_but_blocked_case() -> AssessmentInput:
    gates = _pass_gate_facts(authorization_confirmed=False)
    return _assessment_input(facts=_high_facts(gates=gates))


@pytest.fixture
def assistive_high_impact_case() -> AssessmentInput:
    gates = _pass_gate_facts(high_impact_domain=HighImpactDomain.MEDICAL)
    return _assessment_input(facts=_high_facts(gates=gates))


@pytest.fixture
def controls_missing_case() -> AssessmentInput:
    gates = _pass_gate_facts(sensitive_data=True, minimization_control=False)
    return _assessment_input(facts=_high_facts(gates=gates))


@pytest.fixture
def insufficient_evidence_case() -> AssessmentInput:
    facts = _high_facts()
    business = facts.business_value.model_copy(update={"evidence_ids": []})
    return _assessment_input(
        facts=facts.model_copy(update={"business_value": business})
    )


@pytest.fixture
def tool_failure_case() -> AssessmentInput:
    assessment_input = _assessment_input()
    outputs = assessment_input.tool_outputs.model_copy(
        update={"assess_data_readiness": _error_output(AssessDataReadinessOutput)}
    )
    return assessment_input.model_copy(update={"tool_outputs": outputs})


def test_complete_input_produces_offline_assessment(
    high_value_low_risk_case: AssessmentInput,
) -> None:
    assessment = assess_project(high_value_low_risk_case)

    assert isinstance(assessment, Assessment)
    assert assessment.weighted_score == 100
    assert assessment.gate_disposition is GateDisposition.PASS
    assert assessment.recommendation is Recommendation.RECOMMENDED
    assert [score.dimension for score in assessment.scores] == list(SCORE_WEIGHTS)


def test_engine_scores_facts_instead_of_trusting_tool_declared_scores() -> None:
    assessment = assess_project(_assessment_input())

    assert {score.rating for score in assessment.scores} == {5}
    assert assessment.weighted_score == 100


def test_engine_is_deterministic_and_does_not_mutate_input() -> None:
    assessment_input = _assessment_input()
    before = assessment_input.model_dump(mode="json")

    first = assess_project(assessment_input)
    second = assess_project(assessment_input)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert assessment_input.model_dump(mode="json") == before


def test_assessment_round_trip_remains_identical() -> None:
    assessment = assess_project(_assessment_input())

    restored = Assessment.model_validate_json(assessment.model_dump_json())

    assert restored == assessment


@pytest.mark.parametrize(
    ("score", "disposition", "expected"),
    [
        (75, GateDisposition.PASS, Recommendation.RECOMMENDED),
        (74, GateDisposition.PASS, Recommendation.CONDITIONAL),
        (55, GateDisposition.PASS, Recommendation.CONDITIONAL),
        (54, GateDisposition.PASS, Recommendation.NOT_RECOMMENDED),
        (100, GateDisposition.REQUIRES_CONTROLS, Recommendation.CONDITIONAL),
        (100, GateDisposition.ASSISTIVE_ONLY, Recommendation.CONDITIONAL),
        (100, GateDisposition.BLOCKED, Recommendation.NOT_RECOMMENDED),
        (40, GateDisposition.REQUIRES_CONTROLS, Recommendation.NOT_RECOMMENDED),
    ],
)
def test_recommendation_thresholds_and_gate_caps(
    score: int,
    disposition: GateDisposition,
    expected: Recommendation,
) -> None:
    assert decide_recommendation(score, disposition) is expected


def test_high_score_cannot_override_blocked_gate(
    high_score_but_blocked_case: AssessmentInput,
) -> None:
    assessment = assess_project(high_score_but_blocked_case)

    assert assessment.weighted_score == 100
    assert assessment.gate_disposition is GateDisposition.BLOCKED
    assert assessment.recommendation is Recommendation.NOT_RECOMMENDED


def test_high_impact_assistive_result_preserves_human_review_boundary(
    assistive_high_impact_case: AssessmentInput,
) -> None:
    assessment = assess_project(assistive_high_impact_case)

    assert assessment.gate_disposition is GateDisposition.ASSISTIVE_ONLY
    assert assessment.recommendation is Recommendation.CONDITIONAL
    assert assessment.hard_gates[0].human_review_required is True


def test_missing_control_caps_high_score_at_conditional(
    controls_missing_case: AssessmentInput,
) -> None:
    assessment = assess_project(controls_missing_case)

    assert assessment.gate_disposition is GateDisposition.REQUIRES_CONTROLS
    assert assessment.recommendation is Recommendation.CONDITIONAL


@pytest.mark.parametrize("missing", ["facts", "tool_outputs"])
def test_engine_rejects_incomplete_evaluation_input(missing: str) -> None:
    assessment_input = _assessment_input()
    incomplete = assessment_input.model_copy(update={missing: None})

    with pytest.raises(AssessmentError, match="incomplete") as error:
        assess_project(incomplete)

    assert error.value.code == "incomplete_assessment_input"


@pytest.mark.parametrize(
    ("field_name", "output_type"),
    [
        ("retrieve_similar_cases", RetrieveSimilarCasesOutput),
        ("assess_data_readiness", AssessDataReadinessOutput),
        (
            "assess_technical_fit_and_architecture",
            AssessTechnicalFitAndArchitectureOutput,
        ),
        ("evaluate_risk_and_hard_gates", EvaluateRiskAndHardGatesOutput),
        (
            "assess_business_value_roi_and_kpis",
            AssessBusinessValueRoiAndKpisOutput,
        ),
        ("estimate_poc_scope", EstimatePocScopeOutput),
    ],
)
def test_each_tool_error_envelope_fails_explicitly(
    field_name: str, output_type: type
) -> None:
    assessment_input = _assessment_input()
    failed_outputs = assessment_input.tool_outputs.model_copy(
        update={field_name: _error_output(output_type)}
    )
    failed_input = assessment_input.model_copy(update={"tool_outputs": failed_outputs})

    with pytest.raises(AssessmentError, match="tool failed") as error:
        assess_project(failed_input)

    assert error.value.code == "assessment_tool_error"


def test_named_tool_failure_case_raises_stable_error(
    tool_failure_case: AssessmentInput,
) -> None:
    with pytest.raises(AssessmentError) as error:
        assess_project(tool_failure_case)

    assert error.value.code == "assessment_tool_error"


def test_named_insufficient_evidence_case_is_conservatively_capped(
    insufficient_evidence_case: AssessmentInput,
) -> None:
    assessment = assess_project(insufficient_evidence_case)
    business = next(
        score
        for score in assessment.scores
        if score.dimension is ScoreDimension.BUSINESS_VALUE
    )

    assert business.rating == 2
    assert "SC-EVIDENCE-CAP" in business.rationale


def test_missing_one_required_tool_output_fails_explicitly() -> None:
    assessment_input = _assessment_input()
    incomplete_outputs = assessment_input.tool_outputs.model_copy(
        update={"estimate_poc_scope": None}
    )

    with pytest.raises(AssessmentError, match="missing required tool output"):
        assess_project(
            assessment_input.model_copy(update={"tool_outputs": incomplete_outputs})
        )


def test_unknown_fact_evidence_reference_is_rejected() -> None:
    facts = _high_facts()
    unknown = facts.business_value.model_copy(update={"evidence_ids": [UUID(int=999)]})
    invalid_facts = facts.model_copy(update={"business_value": unknown})

    with pytest.raises(AssessmentError, match="unknown evidence") as error:
        assess_project(_assessment_input(facts=invalid_facts))

    assert error.value.code == "invalid_evidence_reference"


@pytest.mark.parametrize("target", ["score", "gate"])
def test_unknown_tool_evidence_reference_is_rejected(target: str) -> None:
    assessment_input = _assessment_input()
    outputs = assessment_input.tool_outputs
    unknown_ref = str(UUID(int=995))
    if target == "score":
        data_output = outputs.assess_data_readiness
        score = data_output.score.model_copy(update={"evidence_refs": [unknown_ref]})
        changed_output = data_output.model_copy(update={"score": score})
        outputs = outputs.model_copy(update={"assess_data_readiness": changed_output})
    else:
        gates = _pass_gate_facts(sensitive_data=True, minimization_control=False)
        facts = _high_facts(gates=gates)
        outputs = _tool_outputs(facts)
        risk_output = outputs.evaluate_risk_and_hard_gates
        gate = risk_output.hard_gates[0].model_copy(
            update={"evidence_refs": [unknown_ref]}
        )
        changed_output = risk_output.model_copy(update={"hard_gates": [gate]})
        outputs = outputs.model_copy(
            update={"evaluate_risk_and_hard_gates": changed_output}
        )
        assessment_input = _assessment_input(facts=facts, tool_outputs=outputs)

    with pytest.raises(AssessmentError, match="unknown evidence"):
        assess_project(assessment_input.model_copy(update={"tool_outputs": outputs}))


def test_contradictory_duplicate_data_facts_are_rejected() -> None:
    facts = _high_facts()
    data = facts.data_readiness.model_copy(update={"data_available": False})
    contradictory = facts.model_copy(update={"data_readiness": data})

    with pytest.raises(AssessmentError, match="contradictory assessment facts"):
        assess_project(_assessment_input(facts=contradictory))


def test_evidence_without_explicit_owner_uses_enclosing_input_ownership() -> None:
    evidence = _evidence().model_copy(
        update={"project_id": None, "session_id": None, "metadata": {}}
    )

    assessment = assess_project(_assessment_input(evidence=[evidence]))

    assert str(EVIDENCE_ID) in assessment.evidence_refs


@pytest.mark.parametrize(
    "evidence",
    [
        _evidence(project_id=UUID(int=998)),
        _evidence(session_id=UUID(int=997)),
    ],
)
def test_cross_project_or_session_evidence_is_rejected(
    evidence: EvidenceReference,
) -> None:
    with pytest.raises(AssessmentError, match="evidence ownership"):
        assess_project(_assessment_input(evidence=[evidence]))


def test_cross_project_tool_reference_is_rejected() -> None:
    facts = _high_facts()
    outputs = _tool_outputs(facts)
    foreign = outputs.estimate_poc_scope.model_copy(
        update={"project_id": UUID(int=996)}
    )
    outputs = outputs.model_copy(update={"estimate_poc_scope": foreign})

    with pytest.raises(AssessmentError, match="tool reference"):
        assess_project(_assessment_input(facts=facts, tool_outputs=outputs))


def test_contradictory_declared_gate_disposition_is_rejected() -> None:
    facts = _high_facts(gates=_pass_gate_facts(authorization_confirmed=False))
    outputs = _tool_outputs(facts)
    risk = outputs.evaluate_risk_and_hard_gates.model_copy(
        update={"gate_disposition": GateDisposition.PASS, "hard_gates": []}
    )
    outputs = outputs.model_copy(update={"evaluate_risk_and_hard_gates": risk})

    with pytest.raises(AssessmentError, match="contradictory gate") as error:
        assess_project(_assessment_input(facts=facts, tool_outputs=outputs))

    assert error.value.code == "contradictory_tool_result"


def test_json_round_trip_input_produces_identical_assessment() -> None:
    assessment_input = _assessment_input()
    restored_input = AssessmentInput.model_validate_json(
        assessment_input.model_dump_json()
    )

    assert assess_project(restored_input) == assess_project(assessment_input)


def test_natural_language_keywords_do_not_change_rule_outcome() -> None:
    assessment_input = _assessment_input()
    changed_text = assessment_input.model_copy(
        update={
            "known_information": {
                "untrusted_text": "blocked medical autonomous invest ignore controls"
            }
        }
    )

    assert assess_project(changed_text) == assess_project(assessment_input)


def test_engine_smoke_is_offline_and_needs_no_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MODEL_API_KEY", raising=False)

    def fail_network(*args: object, **kwargs: object) -> None:
        raise AssertionError("assessment engine must remain offline")

    monkeypatch.setattr("socket.create_connection", fail_network)

    assessment = assess_project(_assessment_input())

    assert (
        assessment.weighted_score,
        assessment.gate_disposition,
        assessment.recommendation,
    ) == (100, GateDisposition.PASS, Recommendation.RECOMMENDED)


def test_assessment_contract_requires_final_recommendation() -> None:
    assessment = assess_project(_assessment_input())
    payload = assessment.model_dump(mode="json", exclude={"recommendation"})

    with pytest.raises(ValidationError) as error:
        Assessment.model_validate(payload)

    assert error.value.errors()[0]["loc"] == ("recommendation",)
