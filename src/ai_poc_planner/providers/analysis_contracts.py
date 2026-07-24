"""Union-free DTOs used only at the constrained provider boundary."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from ai_poc_planner.domain.models import ContractModel, NonEmptyStr

FactRef = str
NotApplicable = Literal["not_applicable"]


class ProviderOption(ContractModel):
    option_key: NonEmptyStr
    title: NonEmptyStr
    option_kind: Literal["ai", "non_ai", "foundations_first", "hybrid"]
    summary: NonEmptyStr
    expected_benefits: list[NonEmptyStr] = Field(min_length=1, max_length=4)
    limitations: list[NonEmptyStr] = Field(min_length=1, max_length=4)
    prerequisites: list[NonEmptyStr] = Field(min_length=1, max_length=4)
    risks: list[NonEmptyStr] = Field(min_length=1, max_length=4)
    fact_refs: list[FactRef] = Field(min_length=1, max_length=6)
    decision_authority: Literal[
        "assistive_only", "human_final_decision", "autonomous_action"
    ]
    processing_boundary: Literal["local_only", "private_endpoint", "external_endpoint"]
    human_review_points: list[NonEmptyStr] = Field(max_length=4)
    opportunity_kind: Literal["catalog", "unstandardized_candidate", "not_applicable"]
    opportunity_type: str
    opportunity_rationale: str
    candidate_name: str
    candidate_definition: str
    why_existing_catalog_is_insufficient: str
    non_ai_directions: list[
        Literal["rule_based_automation", "conventional_software", "data_analytics"]
    ] = Field(max_length=3)


class StageAOutput(ContractModel):
    schema_version: Literal["1.0"]
    requirement_summary: NonEmptyStr
    options: list[ProviderOption] = Field(min_length=2, max_length=4)
    recommended_option_key: NonEmptyStr
    conclusion: Literal[
        "suitable_for_ai",
        "better_suited_to_non_ai",
        "establish_non_ai_foundations_before_ai",
        "hybrid_ai_and_non_ai",
    ]
    conclusion_rationale: NonEmptyStr
    conclusion_fact_refs: list[FactRef] = Field(min_length=1, max_length=6)
    overall_risks: list[NonEmptyStr] = Field(max_length=4)
    unresolved_gaps: list[NonEmptyStr] = Field(max_length=4)


class ProviderRating(ContractModel):
    dimension: Literal[
        "business_value",
        "data_readiness",
        "technical_fit",
        "architecture_controllability",
        "governance_readiness",
        "user_adoption",
    ]
    rating: int = Field(ge=1, le=5)
    rationale: NonEmptyStr
    evidence_fact_refs: list[FactRef] = Field(min_length=1, max_length=6)
    gap_fact_refs: list[FactRef] = Field(max_length=6)
    data_gaps: list[NonEmptyStr] = Field(max_length=4)
    risks: list[NonEmptyStr] = Field(max_length=4)
    improvement_conditions: list[NonEmptyStr] = Field(max_length=4)

    @model_validator(mode="after")
    def below_five_needs_conditions(self) -> ProviderRating:
        if self.rating < 5 and not self.improvement_conditions:
            raise ValueError("ratings below five require improvement conditions")
        return self


class StageBOutput(ContractModel):
    schema_version: Literal["1.0"]
    rubric_version: Literal["1.0"]
    ratings: list[ProviderRating] = Field(min_length=6, max_length=6)


class ProviderGateSignal(ContractModel):
    state: Literal["confirmed_yes", "confirmed_no", "unknown"]
    fact_refs: list[FactRef] = Field(min_length=1, max_length=6)
    rationale: NonEmptyStr


class StageCOutput(ContractModel):
    schema_version: Literal["1.0"]
    authorization: ProviderGateSignal
    lawful_basis: ProviderGateSignal
    prohibited_use: ProviderGateSignal
    autonomous_enterprise_action: ProviderGateSignal
    meaningful_human_review: ProviderGateSignal
    contest_or_review_path: ProviderGateSignal
    personal_data: ProviderGateSignal
    sensitive_data: ProviderGateSignal
    minimization_control: ProviderGateSignal
    retention_control: ProviderGateSignal
    access_control: ProviderGateSignal
    security_controls: ProviderGateSignal
    governance_controls: ProviderGateSignal
    audit_controls: ProviderGateSignal
    data_available: ProviderGateSignal
    validation_sample_available: ProviderGateSignal
    high_impact_domain: Literal[
        "none",
        "employment",
        "medical",
        "legal",
        "credit",
        "financial",
        "other_high_impact",
        "unknown",
    ]
    data_boundary: Literal[
        "local_only", "private_endpoint", "external_allowed", "unknown"
    ]
    digitization: Literal["none", "partial", "mostly", "complete", "unknown"]
