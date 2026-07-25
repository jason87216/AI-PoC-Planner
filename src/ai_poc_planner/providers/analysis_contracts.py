"""Small, union-free DTOs for the staged Phase 4 provider boundary.

The provider never receives the product-domain option union.  A0 chooses only
option kinds; a separate, kind-specific A1 request fills each option.  The
program then maps the validated DTOs into the stricter domain contracts.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import Field, create_model, model_validator

from ai_poc_planner.domain.models import ContractModel, NonEmptyStr

FactRef = str
OptionKind = Literal["ai", "non_ai", "foundations_first", "hybrid"]
CatalogOpportunityType = Literal[
    "enterprise_knowledge_and_professional_document_assist",
    "customer_service_assist",
    "document_classification_and_extraction",
    "meeting_summary_and_action_items",
    "marketing_content_assist",
    "demand_forecasting",
    "predictive_maintenance",
    "anomaly_and_risk_detection",
    "recruiting_process_assist",
]
NonAiDirection = Literal[
    "rule_based_automation", "conventional_software", "data_analytics"
]


def _token_enum(name: str, tokens: tuple[str, ...]) -> type[Enum]:
    """Build a closed string enum for this request's fact-token catalog."""

    if not tokens:
        # Readiness already requires confirmed evidence.  This defensive enum
        # makes an accidental empty catalog impossible to satisfy.
        tokens = ("__no_valid_fact_token__",)
    return Enum(name, {token: token for token in tokens}, type=str)


class StageA0Option(ContractModel):
    # Provider-facing spelling avoids the JSON Schema annotation collision
    # exhibited by the constrained NVIDIA model; it maps to domain ``title``.
    option_title: NonEmptyStr
    option_kind: OptionKind
    summary: NonEmptyStr
    fact_refs: list[FactRef] = Field(min_length=1, max_length=6)


class StageA0Output(ContractModel):
    """A0 is deliberately incapable of expressing opportunity details."""

    recommended_option_index: int = Field(ge=1, le=4)
    recommendation_rationale: NonEmptyStr
    recommendation_fact_refs: list[FactRef] = Field(min_length=1, max_length=6)
    options: list[StageA0Option] = Field(min_length=2, max_length=4)

    @model_validator(mode="after")
    def recommended_index_and_alternative_are_valid(self) -> StageA0Output:
        if self.recommended_option_index > len(self.options):
            raise ValueError("recommended_option_index must select a listed option")
        if len({item.option_kind for item in self.options}) == 1:
            raise ValueError("options must include a meaningful alternative direction")
        return self


class _OptionDetailBase(ContractModel):
    expected_benefits: list[NonEmptyStr] = Field(min_length=1, max_length=4)
    limitations: list[NonEmptyStr] = Field(min_length=1, max_length=4)
    prerequisites: list[NonEmptyStr] = Field(min_length=1, max_length=4)
    risks: list[NonEmptyStr] = Field(min_length=1, max_length=4)
    human_review_points: list[NonEmptyStr] = Field(min_length=1, max_length=4)
    fact_refs: list[FactRef] = Field(min_length=1, max_length=6)
    decision_authority: Literal[
        "assistive_only", "human_final_decision", "autonomous_action"
    ]
    processing_boundary: Literal["local_only", "private_endpoint", "external_endpoint"]


class AiOptionDetail(_OptionDetailBase):
    opportunity_source_kind: Literal["catalog", "unstandardized_candidate"]
    opportunity_type: Literal[
        "enterprise_knowledge_and_professional_document_assist",
        "customer_service_assist",
        "document_classification_and_extraction",
        "meeting_summary_and_action_items",
        "marketing_content_assist",
        "demand_forecasting",
        "predictive_maintenance",
        "anomaly_and_risk_detection",
        "recruiting_process_assist",
        "unstandardized_candidate",
    ]
    candidate_name: NonEmptyStr
    opportunity_rationale: NonEmptyStr
    candidate_definition: NonEmptyStr
    why_existing_catalog_is_insufficient: NonEmptyStr

    @model_validator(mode="after")
    def source_and_type_match(self) -> AiOptionDetail:
        if (
            self.opportunity_source_kind == "catalog"
            and self.opportunity_type == "unstandardized_candidate"
        ):
            raise ValueError("catalog opportunities require a catalog opportunity_type")
        if (
            self.opportunity_source_kind == "unstandardized_candidate"
            and self.opportunity_type != "unstandardized_candidate"
        ):
            raise ValueError(
                "unstandardized candidates require their fixed opportunity_type"
            )
        return self


class NonAiOptionDetail(_OptionDetailBase):
    non_ai_directions: list[NonAiDirection] = Field(min_length=1, max_length=3)


class HybridOptionDetail(AiOptionDetail):
    non_ai_directions: list[NonAiDirection] = Field(min_length=1, max_length=3)


class FoundationsFirstOptionDetail(HybridOptionDetail):
    foundation_prerequisites: list[NonEmptyStr] = Field(min_length=1, max_length=4)


def stage_a0_contract(confirmed_tokens: tuple[str, ...]) -> type[StageA0Output]:
    """Return an A0 contract closed over only confirmed fact tokens."""

    token = _token_enum("ConfirmedFactRef", confirmed_tokens)
    option = create_model(
        "ConstrainedStageA0Option",
        __base__=StageA0Option,
        fact_refs=(list[token], Field(min_length=1, max_length=6)),
    )
    return create_model(
        "ConstrainedStageA0Output",
        __base__=StageA0Output,
        recommendation_fact_refs=(list[token], Field(min_length=1, max_length=6)),
        options=(list[option], Field(min_length=2, max_length=4)),
    )


def option_detail_contract(
    option_kind: str, confirmed_tokens: tuple[str, ...]
) -> type[_OptionDetailBase]:
    """Return the single A1 schema appropriate for the A0-selected kind."""

    bases: dict[str, type[_OptionDetailBase]] = {
        "ai": AiOptionDetail,
        "non_ai": NonAiOptionDetail,
        "hybrid": HybridOptionDetail,
        "foundations_first": FoundationsFirstOptionDetail,
    }
    try:
        base = bases[option_kind]
    except KeyError as error:
        raise ValueError("unsupported analysis option kind") from error
    token = _token_enum("ConfirmedFactRef", confirmed_tokens)
    return create_model(
        f"Constrained{option_kind.title().replace('_', '')}OptionDetail",
        __base__=base,
        fact_refs=(list[token], Field(min_length=1, max_length=6)),
    )


class ProviderRating(ContractModel):
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
    """Fixed keys make duplicate or missing rubric dimensions unrepresentable."""

    business_value: ProviderRating
    data_readiness: ProviderRating
    technical_fit: ProviderRating
    architecture_controllability: ProviderRating
    governance_readiness: ProviderRating
    user_adoption: ProviderRating


def stage_b_contract(
    confirmed_tokens: tuple[str, ...], gap_tokens: tuple[str, ...]
) -> type[StageBOutput]:
    confirmed = _token_enum("ConfirmedEvidenceFactRef", confirmed_tokens)
    gaps = _token_enum("GapFactRef", gap_tokens)
    rating = create_model(
        "ConstrainedProviderRating",
        __base__=ProviderRating,
        evidence_fact_refs=(list[confirmed], Field(min_length=1, max_length=6)),
        gap_fact_refs=(list[gaps], Field(max_length=6)),
    )
    return create_model(
        "ConstrainedStageBOutput",
        __base__=StageBOutput,
        business_value=(rating, ...),
        data_readiness=(rating, ...),
        technical_fit=(rating, ...),
        architecture_controllability=(rating, ...),
        governance_readiness=(rating, ...),
        user_adoption=(rating, ...),
    )


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
