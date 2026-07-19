"""Versioned HG-01 through HG-07 hard-gate rules and precedence."""

from __future__ import annotations

from dataclasses import dataclass

from ai_poc_planner.domain.enums import (
    DataBoundary,
    DigitizationLevel,
    GateDisposition,
    HighImpactDomain,
)
from ai_poc_planner.domain.facts import GateFacts
from ai_poc_planner.domain.models import HardGateResult

GATE_PRECEDENCE: dict[GateDisposition, int] = {
    GateDisposition.PASS: 0,
    GateDisposition.REQUIRES_CONTROLS: 1,
    GateDisposition.ASSISTIVE_ONLY: 2,
    GateDisposition.BLOCKED: 3,
}


@dataclass(frozen=True, slots=True)
class GateEvaluation:
    triggered: tuple[HardGateResult, ...]
    disposition: GateDisposition


def _evidence(facts: GateFacts) -> list[str]:
    return sorted(str(item) for item in facts.evidence_ids)


def _gate(
    *,
    rule_id: str,
    disposition: GateDisposition,
    reason: str,
    controls: list[str],
    human_review: bool,
    facts: GateFacts,
) -> HardGateResult:
    return HardGateResult(
        rule_id=rule_id,
        disposition=disposition,
        reason=reason,
        required_controls=controls,
        human_review_required=human_review,
        evidence_refs=_evidence(facts),
    )


def _hg01(facts: GateFacts) -> HardGateResult | None:
    if all(
        (
            facts.authorization_confirmed,
            facts.lawful_basis_confirmed,
            facts.accountable_owner_confirmed,
            not facts.prohibited_use,
            not facts.autonomous_final_decision,
            not facts.autonomous_enterprise_action,
        )
    ):
        return None
    return _gate(
        rule_id="HG-01",
        disposition=GateDisposition.BLOCKED,
        reason=(
            "Required authorization, lawful basis, or accountable ownership is "
            "absent, or the use is prohibited."
        ),
        controls=[
            "obtain documented authorization and lawful basis",
            "assign an accountable owner",
            "remove autonomous final decisions and enterprise actions",
            "complete qualified professional review",
        ],
        human_review=True,
        facts=facts,
    )


def _hg02(facts: GateFacts) -> HardGateResult | None:
    high_impact = facts.high_impact_domain is not HighImpactDomain.NONE
    if not high_impact or (
        not facts.autonomous_final_decision and facts.meaningful_human_review
    ):
        return None
    return _gate(
        rule_id="HG-02",
        disposition=GateDisposition.BLOCKED,
        reason=(
            "A high-impact final decision cannot be autonomous or lack meaningful "
            "human review."
        ),
        controls=[
            "remove autonomous final-decision authority",
            "require a qualified human final decision",
        ],
        human_review=True,
        facts=facts,
    )


def _hg03(facts: GateFacts) -> HardGateResult | None:
    if (
        facts.high_impact_domain is HighImpactDomain.NONE
        or facts.autonomous_final_decision
        or not facts.meaningful_human_review
    ):
        return None
    controls = ["preserve a meaningful human final decision"]
    if not facts.contest_or_review_path:
        controls.append("provide a contest or review path")
    if not facts.governance_controls_confirmed:
        controls.append("approve governance controls")
    if not facts.audit_controls_confirmed:
        controls.append("enable audit controls")
    return _gate(
        rule_id="HG-03",
        disposition=GateDisposition.ASSISTIVE_ONLY,
        reason=(
            "The high-impact workflow is limited to advice, summary, or decision "
            "support."
        ),
        controls=controls,
        human_review=True,
        facts=facts,
    )


def _hg04(facts: GateFacts) -> HardGateResult | None:
    boundary_conflict = facts.external_endpoint_requested and facts.data_boundary in {
        DataBoundary.LOCAL_ONLY,
        DataBoundary.PRIVATE_ENDPOINT,
    }
    if not boundary_conflict:
        return None
    return _gate(
        rule_id="HG-04",
        disposition=GateDisposition.REQUIRES_CONTROLS,
        reason=(
            "The requested external endpoint conflicts with the approved data boundary."
        ),
        controls=["use an approved local or private endpoint"],
        human_review=True,
        facts=facts,
    )


def _hg05(facts: GateFacts) -> HardGateResult | None:
    controls = []
    if facts.personal_data or facts.sensitive_data:
        for present, label in (
            (facts.minimization_control, "define data minimization"),
            (facts.retention_control, "define retention and deletion controls"),
            (facts.access_control, "enforce least-privilege access control"),
        ):
            if not present:
                controls.append(label)
    if (
        facts.personal_data or facts.sensitive_data or facts.security_controls_required
    ) and not facts.security_controls_confirmed:
        controls.append("approve required security controls")
    if facts.governance_controls_required and not facts.governance_controls_confirmed:
        controls.append("approve required governance controls")
    if facts.audit_controls_required and not facts.audit_controls_confirmed:
        controls.append("enable required audit controls")
    if not controls:
        return None
    return _gate(
        rule_id="HG-05",
        disposition=GateDisposition.REQUIRES_CONTROLS,
        reason=(
            "One or more mandatory data, security, governance, or audit controls "
            "are missing."
        ),
        controls=controls,
        human_review=True,
        facts=facts,
    )


def _hg06(facts: GateFacts) -> HardGateResult | None:
    low_maturity = (
        not facts.data_available
        or facts.digitization in {DigitizationLevel.NONE, DigitizationLevel.PARTIAL}
        or not facts.validation_sample_available
    )
    if not low_maturity:
        return None
    return _gate(
        rule_id="HG-06",
        disposition=GateDisposition.REQUIRES_CONTROLS,
        reason="Data is unavailable, mostly non-digital, or lacks a validation sample.",
        controls=[
            "make required data available",
            "digitize or OCR source material",
            "create a representative validation sample",
        ],
        human_review=False,
        facts=facts,
    )


def _hg07(facts: GateFacts) -> HardGateResult | None:
    if not (
        facts.high_impact_domain is HighImpactDomain.FINANCIAL
        and facts.autonomous_final_decision
    ):
        return None
    return _gate(
        rule_id="HG-07",
        disposition=GateDisposition.BLOCKED,
        reason="The MVP cannot autonomously approve, price, lend, or invest.",
        controls=[
            "remove autonomous financial decision authority",
            "require qualified human approval",
        ],
        human_review=True,
        facts=facts,
    )


GATE_RULES = (_hg01, _hg02, _hg03, _hg04, _hg05, _hg06, _hg07)


def evaluate_hard_gates(facts: GateFacts) -> GateEvaluation:
    """Evaluate every rule, preserve all triggers, and apply fixed precedence."""
    triggered = tuple(
        result for rule in GATE_RULES if (result := rule(facts)) is not None
    )
    disposition = max(
        (gate.disposition for gate in triggered),
        key=GATE_PRECEDENCE.__getitem__,
        default=GateDisposition.PASS,
    )
    return GateEvaluation(triggered=triggered, disposition=disposition)
