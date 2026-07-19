from uuid import UUID

import pytest
from pydantic import ValidationError

from ai_poc_planner.assessment.gates import (
    GATE_PRECEDENCE,
    evaluate_hard_gates,
)
from ai_poc_planner.domain.enums import (
    DataBoundary,
    DigitizationLevel,
    GateDisposition,
    HighImpactDomain,
)
from ai_poc_planner.domain.facts import GateFacts

EVIDENCE_ID = UUID("00000000-0000-0000-0000-000000001101")


def _facts(**overrides: object) -> GateFacts:
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


def test_gate_precedence_is_normative_and_complete() -> None:
    assert GATE_PRECEDENCE == {
        GateDisposition.PASS: 0,
        GateDisposition.REQUIRES_CONTROLS: 1,
        GateDisposition.ASSISTIVE_ONLY: 2,
        GateDisposition.BLOCKED: 3,
    }


def test_gate_facts_do_not_assume_authorization_or_controls() -> None:
    with pytest.raises(ValidationError):
        GateFacts(evidence_ids=[EVIDENCE_ID])


def test_no_trigger_returns_pass_and_no_fabricated_gate() -> None:
    evaluation = evaluate_hard_gates(_facts())

    assert evaluation.disposition is GateDisposition.PASS
    assert evaluation.triggered == ()


@pytest.mark.parametrize(
    "override",
    [
        {"authorization_confirmed": False},
        {"lawful_basis_confirmed": False},
        {"accountable_owner_confirmed": False},
        {"prohibited_use": True},
    ],
)
def test_hg01_blocks_unauthorized_or_prohibited_use(
    override: dict[str, object],
) -> None:
    evaluation = evaluate_hard_gates(_facts(**override))

    assert evaluation.disposition is GateDisposition.BLOCKED
    assert [gate.rule_id for gate in evaluation.triggered] == ["HG-01"]


@pytest.mark.parametrize(
    "override",
    [
        {"autonomous_final_decision": True},
        {"autonomous_enterprise_action": True},
    ],
)
def test_hg01_blocks_general_autonomous_decision_or_enterprise_action(
    override: dict[str, object],
) -> None:
    evaluation = evaluate_hard_gates(_facts(**override))

    assert evaluation.disposition is GateDisposition.BLOCKED
    assert "HG-01" in {gate.rule_id for gate in evaluation.triggered}


@pytest.mark.parametrize(
    "domain",
    [
        HighImpactDomain.EMPLOYMENT,
        HighImpactDomain.MEDICAL,
        HighImpactDomain.LEGAL,
        HighImpactDomain.CREDIT,
        HighImpactDomain.OTHER_HIGH_IMPACT,
    ],
)
def test_hg02_blocks_high_impact_autonomous_final_decision(
    domain: HighImpactDomain,
) -> None:
    evaluation = evaluate_hard_gates(
        _facts(
            high_impact_domain=domain,
            autonomous_final_decision=True,
            meaningful_human_review=False,
        )
    )

    assert evaluation.disposition is GateDisposition.BLOCKED
    assert "HG-02" in {gate.rule_id for gate in evaluation.triggered}


def test_hg03_caps_high_impact_assistive_workflow() -> None:
    evaluation = evaluate_hard_gates(
        _facts(
            high_impact_domain=HighImpactDomain.MEDICAL,
            autonomous_final_decision=False,
            meaningful_human_review=True,
            contest_or_review_path=True,
        )
    )

    gate = evaluation.triggered[0]
    assert gate.rule_id == "HG-03"
    assert evaluation.disposition is GateDisposition.ASSISTIVE_ONLY
    assert gate.human_review_required is True
    assert "human final decision" in " ".join(gate.required_controls)


def test_hg03_records_missing_governance_and_audit_controls() -> None:
    evaluation = evaluate_hard_gates(
        _facts(
            high_impact_domain=HighImpactDomain.LEGAL,
            governance_controls_confirmed=False,
            audit_controls_confirmed=False,
        )
    )

    controls = evaluation.triggered[0].required_controls
    assert any("governance" in control for control in controls)
    assert any("audit" in control for control in controls)


@pytest.mark.parametrize(
    "boundary", [DataBoundary.LOCAL_ONLY, DataBoundary.PRIVATE_ENDPOINT]
)
def test_hg04_requires_control_when_external_endpoint_conflicts_with_boundary(
    boundary: DataBoundary,
) -> None:
    evaluation = evaluate_hard_gates(
        _facts(data_boundary=boundary, external_endpoint_requested=True)
    )

    assert evaluation.disposition is GateDisposition.REQUIRES_CONTROLS
    assert [gate.rule_id for gate in evaluation.triggered] == ["HG-04"]


def test_hg04_does_not_trigger_when_external_use_is_allowed() -> None:
    evaluation = evaluate_hard_gates(
        _facts(
            data_boundary=DataBoundary.EXTERNAL_ALLOWED,
            external_endpoint_requested=True,
        )
    )

    assert evaluation.disposition is GateDisposition.PASS


@pytest.mark.parametrize(
    "missing_control",
    [
        "minimization_control",
        "retention_control",
        "access_control",
        "security_controls_confirmed",
    ],
)
def test_hg05_requires_each_sensitive_data_control(
    missing_control: str,
) -> None:
    evaluation = evaluate_hard_gates(
        _facts(sensitive_data=True, **{missing_control: False})
    )

    gate = evaluation.triggered[0]
    assert gate.rule_id == "HG-05"
    assert gate.disposition is GateDisposition.REQUIRES_CONTROLS
    assert gate.required_controls


@pytest.mark.parametrize(
    ("required_field", "confirmed_field"),
    [
        ("security_controls_required", "security_controls_confirmed"),
        ("governance_controls_required", "governance_controls_confirmed"),
        ("audit_controls_required", "audit_controls_confirmed"),
    ],
)
def test_hg05_requires_explicitly_necessary_controls_outside_sensitive_data(
    required_field: str, confirmed_field: str
) -> None:
    evaluation = evaluate_hard_gates(
        _facts(**{required_field: True, confirmed_field: False})
    )

    assert evaluation.disposition is GateDisposition.REQUIRES_CONTROLS
    assert [gate.rule_id for gate in evaluation.triggered] == ["HG-05"]


@pytest.mark.parametrize(
    "override",
    [
        {"data_available": False},
        {"digitization": DigitizationLevel.NONE},
        {"digitization": DigitizationLevel.PARTIAL},
        {"validation_sample_available": False},
    ],
)
def test_hg06_requires_data_prerequisites(override: dict[str, object]) -> None:
    evaluation = evaluate_hard_gates(_facts(**override))

    assert evaluation.disposition is GateDisposition.REQUIRES_CONTROLS
    assert [gate.rule_id for gate in evaluation.triggered] == ["HG-06"]


def test_hg07_blocks_autonomous_financial_final_decision() -> None:
    evaluation = evaluate_hard_gates(
        _facts(
            high_impact_domain=HighImpactDomain.FINANCIAL,
            autonomous_final_decision=True,
            meaningful_human_review=False,
        )
    )

    assert evaluation.disposition is GateDisposition.BLOCKED
    assert "HG-07" in {gate.rule_id for gate in evaluation.triggered}


def test_all_triggered_rules_are_preserved_in_stable_rule_order() -> None:
    evaluation = evaluate_hard_gates(
        _facts(
            authorization_confirmed=False,
            high_impact_domain=HighImpactDomain.FINANCIAL,
            autonomous_final_decision=True,
            meaningful_human_review=False,
            sensitive_data=True,
            minimization_control=False,
            data_available=False,
        )
    )

    assert [gate.rule_id for gate in evaluation.triggered] == [
        "HG-01",
        "HG-02",
        "HG-05",
        "HG-06",
        "HG-07",
    ]
    assert evaluation.disposition is GateDisposition.BLOCKED


def test_stronger_gate_wins_independently_of_trigger_count() -> None:
    evaluation = evaluate_hard_gates(
        _facts(
            high_impact_domain=HighImpactDomain.MEDICAL,
            meaningful_human_review=True,
            sensitive_data=True,
            retention_control=False,
            data_available=False,
        )
    )

    assert {gate.disposition for gate in evaluation.triggered} == {
        GateDisposition.ASSISTIVE_ONLY,
        GateDisposition.REQUIRES_CONTROLS,
    }
    assert evaluation.disposition is GateDisposition.ASSISTIVE_ONLY


def test_triggered_gate_preserves_reason_controls_and_evidence() -> None:
    evaluation = evaluate_hard_gates(_facts(authorization_confirmed=False))

    gate = evaluation.triggered[0]
    assert gate.rule_id == "HG-01"
    assert gate.reason
    assert gate.required_controls
    assert gate.evidence_refs == [str(EVIDENCE_ID)]
