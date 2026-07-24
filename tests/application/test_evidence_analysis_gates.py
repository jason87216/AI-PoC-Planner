from __future__ import annotations

from ai_poc_planner.application.evidence_analysis import EvidenceAnalysisService
from ai_poc_planner.domain.analysis import AIAnalysisDraft
from ai_poc_planner.domain.enums import GateDisposition
from tests.domain.test_analysis_contracts import _payload


def test_unknown_critical_gate_inputs_do_not_default_to_pass() -> None:
    draft = AIAnalysisDraft.model_validate(_payload())
    option = draft.options[0]

    result = EvidenceAnalysisService._gate_facts(option, draft)

    assert result.lawful_basis_confirmed is False
    assert result.data_available is False


def test_external_option_conflicts_with_local_boundary() -> None:
    payload = _payload()
    payload["options"][0]["processing_boundary"] = "external_endpoint"  # type: ignore[index]
    payload["gate_signals"] = [
        {
            "signal_name": name,
            "value": (
                "complete"
                if name == "digitization"
                else "local_only"
                if name == "data_boundary"
                else "confirmed"
            ),
            "fact_refs": ["F001"],
            "rationale": "A confirmed signal is supplied for this test.",
        }
        for name in (
            "authorization",
            "lawful_basis",
            "accountable_owner",
            "minimization",
            "retention",
            "access_control",
            "security_controls",
            "governance_controls",
            "audit_controls",
            "data_availability",
            "digitization",
            "validation_sample",
            "data_boundary",
        )
    ]
    draft = AIAnalysisDraft.model_validate(payload)
    option = draft.options[0]

    facts = EvidenceAnalysisService._gate_facts(option, draft)
    from ai_poc_planner.assessment.gates import evaluate_hard_gates

    evaluation = evaluate_hard_gates(facts)
    assert evaluation.disposition is GateDisposition.REQUIRES_CONTROLS
    assert {item.rule_id for item in evaluation.triggered} == {"HG-04"}
