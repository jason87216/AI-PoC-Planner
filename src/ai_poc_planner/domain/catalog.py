"""Contracts for reviewed AI opportunity catalog entries and future matching."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from ai_poc_planner.domain.models import ContractModel, NonEmptyStr


class OpportunityType(StrEnum):
    ENTERPRISE_KNOWLEDGE_AND_PROFESSIONAL_DOCUMENT_ASSIST = (
        "enterprise_knowledge_and_professional_document_assist"
    )
    CUSTOMER_SERVICE_ASSIST = "customer_service_assist"
    DOCUMENT_CLASSIFICATION_AND_EXTRACTION = "document_classification_and_extraction"
    MEETING_SUMMARY_AND_ACTION_ITEMS = "meeting_summary_and_action_items"
    MARKETING_CONTENT_ASSIST = "marketing_content_assist"
    DEMAND_FORECASTING = "demand_forecasting"
    PREDICTIVE_MAINTENANCE = "predictive_maintenance"
    ANOMALY_AND_RISK_DETECTION = "anomaly_and_risk_detection"
    RECRUITING_PROCESS_ASSIST = "recruiting_process_assist"


class NonAiAlternativeDirection(StrEnum):
    RULE_BASED_AUTOMATION = "rule_based_automation"
    CONVENTIONAL_SOFTWARE = "conventional_software"
    DATA_ANALYTICS = "data_analytics"


class EvidenceGrade(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"


class EvidenceType(StrEnum):
    REGULATOR_FINDING = "regulator_finding"
    OFFICIAL_COMPANY_DISCLOSURE = "official_company_disclosure"
    COMPANY_REPORTED = "company_reported"
    VENDOR_REPORTED = "vendor_reported"
    VENDOR_PARTICIPATED_RESEARCH = "vendor_participated_research"
    MEDIA_REPORTED = "media_reported"
    OTHER_NON_INDEPENDENT = "other_non_independent"


class CaseReference(ContractModel):
    case_id: NonEmptyStr
    organization: NonEmptyStr
    case_title: NonEmptyStr
    source_url: NonEmptyStr
    evidence_type: EvidenceType
    evidence_grade: EvidenceGrade
    source_label: NonEmptyStr
    relevance_note: NonEmptyStr | None = None
    reported_claim_summary: NonEmptyStr | None = None


class ConditionalGuidance(ContractModel):
    condition_field: NonEmptyStr
    condition_value: NonEmptyStr
    guidance: NonEmptyStr
    kpi_or_risk_guidance: NonEmptyStr


class OpportunityCatalogEntry(ContractModel):
    opportunity_type: OpportunityType
    display_name: NonEmptyStr
    description: NonEmptyStr
    business_problem_signals: list[NonEmptyStr] = Field(min_length=1)
    suitable_conditions: list[NonEmptyStr] = Field(min_length=1)
    unsuitable_conditions: list[NonEmptyStr] = Field(min_length=1)
    minimum_information_needed: list[NonEmptyStr] = Field(min_length=1)
    clarification_questions: list[NonEmptyStr] = Field(min_length=1)
    candidate_solution_directions: list[NonEmptyStr] = Field(min_length=1)
    human_oversight_guidance: list[NonEmptyStr] = Field(min_length=1)
    candidate_poc_kpis: list[NonEmptyStr] = Field(min_length=1)
    pause_or_stop_signals: list[NonEmptyStr] = Field(min_length=1)
    case_references: list[CaseReference] = Field(min_length=1)
    supplemental_case_references: list[CaseReference] = Field(default_factory=list)
    search_keywords: list[NonEmptyStr] = Field(min_length=1)
    conditional_guidance: list[ConditionalGuidance] = Field(default_factory=list)

    @model_validator(mode="after")
    def grade_e_references_are_supplemental_only(self) -> OpportunityCatalogEntry:
        if any(
            reference.evidence_grade is EvidenceGrade.E
            for reference in self.case_references
        ):
            raise ValueError("Grade E references must be supplemental")
        if any(
            reference.evidence_grade is not EvidenceGrade.E
            for reference in self.supplemental_case_references
        ):
            raise ValueError("supplemental references must have Grade E")
        return self


class OpportunityMatchInput(ContractModel):
    business_problem_signals: list[NonEmptyStr] = Field(min_length=1)
    data_modality: NonEmptyStr | None = None
    professional_domain: NonEmptyStr | None = None
    decision_impact: NonEmptyStr | None = None
    historical_data_available: bool | None = None


class OpportunityCandidate(ContractModel):
    opportunity_type: OpportunityType
    match_strength: int = Field(ge=0, le=100)
    reasons: list[NonEmptyStr] = Field(min_length=1)
    missing_information: list[NonEmptyStr] = Field(default_factory=list)
    clarification_questions: list[NonEmptyStr] = Field(default_factory=list)
    conditional_guidance: list[ConditionalGuidance] = Field(default_factory=list)
    case_references: list[CaseReference] = Field(default_factory=list, max_length=2)


class OpportunityMatchResult(ContractModel):
    candidates: list[OpportunityCandidate] = Field(max_length=3)
    clarifying_questions: list[NonEmptyStr] = Field(default_factory=list)
    non_ai_alternatives: list[NonAiAlternativeDirection] = Field(default_factory=list)


class DataClassification(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    HIGHLY_CONFIDENTIAL = "highly_confidential"
    UNKNOWN = "unknown"


class DeploymentPosture(StrEnum):
    PUBLIC_CLOUD_MANAGED = "public_cloud_managed"
    PRIVATE_CLOUD_OR_ISOLATED_ENVIRONMENT = "private_cloud_or_isolated_environment"
    ON_PREMISES = "on_premises"
    HYBRID = "hybrid"


class DeploymentAssessmentStatus(StrEnum):
    CLARIFICATION_REQUIRED = "clarification_required"
    RECOMMENDATION_AVAILABLE = "recommendation_available"


class DeploymentCandidateStatus(StrEnum):
    ELIGIBLE = "eligible"
    CONDITIONAL = "conditional"
    DISALLOWED = "disallowed"


class DeploymentPostureInput(ContractModel):
    data_classification: DataClassification = DataClassification.UNKNOWN
    contains_personal_data: bool | None = None
    contains_trade_secrets: bool | None = None
    contains_regulated_data: bool | None = None
    data_residency_required: bool | None = None
    external_processing_allowed: bool | None = None
    provider_data_retention_allowed: bool | None = None
    provider_training_on_data_allowed: bool | None = None
    internet_access_allowed: bool | None = None
    expected_request_volume: NonEmptyStr | None = None
    expected_concurrency: NonEmptyStr | None = None
    workload_variability: NonEmptyStr | None = None
    expected_context_or_file_volume: NonEmptyStr | None = None
    latency_requirement: NonEmptyStr | None = None
    availability_requirement: NonEmptyStr | None = None
    budget_preference: NonEmptyStr | None = None
    existing_gpu_or_server_capacity: NonEmptyStr | None = None
    existing_cloud_environment: NonEmptyStr | None = None
    existing_on_prem_infrastructure: NonEmptyStr | None = None
    internal_ai_operations_capability: NonEmptyStr | None = None
    model_update_requirement: NonEmptyStr | None = None
    integration_constraints: NonEmptyStr | None = None
    vendor_lock_in_tolerance: NonEmptyStr | None = None
    offline_operation_required: bool | None = None


class DeploymentPostureCandidate(ContractModel):
    posture: DeploymentPosture
    status: DeploymentCandidateStatus
    reasons: list[NonEmptyStr] = Field(min_length=1)
    cost_shape: NonEmptyStr | None = None
    operations_requirements: list[NonEmptyStr] = Field(default_factory=list)
    critical_assumptions: list[NonEmptyStr] = Field(default_factory=list)


class DeploymentPostureAssessment(ContractModel):
    status: DeploymentAssessmentStatus
    recommended_posture: DeploymentPosture | None
    candidates: list[DeploymentPostureCandidate] = Field(default_factory=list)
    missing_deployment_information: list[NonEmptyStr] = Field(default_factory=list)

    @model_validator(mode="after")
    def available_recommendation_has_a_posture(self) -> DeploymentPostureAssessment:
        if (
            self.status is DeploymentAssessmentStatus.RECOMMENDATION_AVAILABLE
            and self.recommended_posture is None
        ):
            raise ValueError("recommendation_available requires recommended_posture")
        return self
