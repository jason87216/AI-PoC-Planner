"""Structured, non-model facts consumed by the deterministic assessment engine."""

from __future__ import annotations

from uuid import UUID

from pydantic import Field, model_validator

from ai_poc_planner.domain.enums import (
    DataBoundary,
    DigitizationLevel,
    HighImpactDomain,
)
from ai_poc_planner.domain.models import ContractModel


class EvidenceBackedFacts(ContractModel):
    evidence_ids: list[UUID] = Field(default_factory=list)

    @model_validator(mode="after")
    def evidence_is_unique(self) -> EvidenceBackedFacts:
        if len(self.evidence_ids) != len(set(self.evidence_ids)):
            raise ValueError("evidence_ids must not contain duplicates")
        return self


class BusinessValueFacts(EvidenceBackedFacts):
    pain_defined: bool = False
    beneficiary_defined: bool = False
    owner_identified: bool = False
    owner_approved: bool = False
    quantitative_baseline: bool = False
    target_kpi_defined: bool = False
    benefit_assumptions_documented: bool = False
    cost_baseline_available: bool = False
    roi_formula_available: bool = False


class DataReadinessFacts(EvidenceBackedFacts):
    data_available: bool = False
    lawful_access: bool = False
    digitization: DigitizationLevel = DigitizationLevel.NONE
    quality_known: bool = False
    quality_sampled: bool = False
    quality_measured: bool = False
    validation_sample_available: bool = False
    representative_validation_sample: bool = False
    gaps_resolvable_in_poc: bool = False


class TechnicalFitFacts(EvidenceBackedFacts):
    ai_needed: bool = False
    technically_feasible: bool = False
    traditional_solution_preferred: bool = False
    technical_path_defined: bool = False
    retrieval_required: bool = False
    reasoning_required: bool = False
    tool_collaboration_required: bool = False
    boundaries_defined: bool = False
    key_assumptions_testable: bool = False


class ArchitectureControllabilityFacts(EvidenceBackedFacts):
    integration_count: int = Field(default=0, ge=0)
    high_risk_integration_count: int = Field(default=0, ge=0)
    unknown_dependency_count: int = Field(default=0, ge=0)
    interfaces_known: bool = False
    test_environment_available: bool = False
    mocks_available: bool = False
    data_boundary_defined: bool = False
    dependencies_replaceable: bool = False
    observability_available: bool = False
    reproducible_environment: bool = False

    @model_validator(mode="after")
    def risk_count_does_not_exceed_integrations(
        self,
    ) -> ArchitectureControllabilityFacts:
        if self.high_risk_integration_count > self.integration_count:
            raise ValueError(
                "high_risk_integration_count cannot exceed integration_count"
            )
        return self


class GovernanceReadinessFacts(EvidenceBackedFacts):
    lawful_basis_confirmed: bool = False
    accountable_owner_confirmed: bool = False
    data_boundary_defined: bool = False
    data_types_identified: bool = False
    risks_identified: bool = False
    controls_identified: bool = False
    policy_defined: bool = False
    reviewer_identified: bool = False
    minimization_defined: bool = False
    retention_defined: bool = False
    approved_policy: bool = False
    formal_risk_assessment: bool = False
    audit_records_available: bool = False
    incident_process_defined: bool = False


class UserAdoptionFacts(EvidenceBackedFacts):
    users_opposed: bool = False
    process_owner_confirmed: bool = False
    affected_roles_involved: bool = False
    value_proposition_clear: bool = False
    representative_users_committed: bool = False
    workflow_adjusted: bool = False
    training_plan_defined: bool = False
    feedback_process_defined: bool = False
    users_co_designed: bool = False
    adoption_metrics_defined: bool = False
    support_owner_confirmed: bool = False
    iteration_owner_confirmed: bool = False


class GateFacts(EvidenceBackedFacts):
    authorization_confirmed: bool
    lawful_basis_confirmed: bool
    accountable_owner_confirmed: bool
    prohibited_use: bool
    high_impact_domain: HighImpactDomain
    autonomous_final_decision: bool
    autonomous_enterprise_action: bool
    meaningful_human_review: bool
    contest_or_review_path: bool
    personal_data: bool
    sensitive_data: bool
    minimization_control: bool
    retention_control: bool
    access_control: bool
    security_controls_confirmed: bool
    security_controls_required: bool
    governance_controls_confirmed: bool
    governance_controls_required: bool
    audit_controls_confirmed: bool
    audit_controls_required: bool
    data_boundary: DataBoundary
    external_endpoint_requested: bool
    data_available: bool
    digitization: DigitizationLevel
    validation_sample_available: bool


class AssessmentFacts(ContractModel):
    business_value: BusinessValueFacts
    data_readiness: DataReadinessFacts
    technical_fit: TechnicalFitFacts
    architecture_controllability: ArchitectureControllabilityFacts
    governance_readiness: GovernanceReadinessFacts
    user_adoption: UserAdoptionFacts
    gates: GateFacts
