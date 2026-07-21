"""Reviewed, offline AI opportunity catalog fixture."""

from ai_poc_planner.domain.catalog import (
    CaseReference,
    ConditionalGuidance,
    EvidenceGrade,
    EvidenceType,
    OpportunityCatalogEntry,
    OpportunityType,
)


def _case(case_id: str, organization: str, url: str) -> CaseReference:
    return CaseReference(
        case_id=case_id,
        organization=organization,
        case_title=f"{organization} reviewed case",
        source_url=url,
        evidence_type=EvidenceType.VENDOR_REPORTED,
        evidence_grade=EvidenceGrade.C,
        source_label="AI Adoption Case Review",
    )


def _entry(
    opportunity_type: OpportunityType,
    display_name: str,
    case: CaseReference,
    *,
    guidance: list[ConditionalGuidance] | None = None,
) -> OpportunityCatalogEntry:
    return OpportunityCatalogEntry(
        opportunity_type=opportunity_type,
        display_name=display_name,
        description=f"Reviewed planning guidance for {display_name}.",
        business_problem_signals=["repeated business work"],
        suitable_conditions=["a bounded PoC can be defined"],
        unsuitable_conditions=["the workflow requires autonomous final decisions"],
        minimum_information_needed=["business owner and available data"],
        clarification_questions=["What outcome should the PoC validate?"],
        candidate_solution_directions=["reviewed candidate direction"],
        human_oversight_guidance=[
            "Keep meaningful human review at consequential steps."
        ],
        candidate_poc_kpis=["adoption and workflow-quality metric"],
        pause_or_stop_signals=["critical information or review ownership is missing"],
        case_references=[case],
        search_keywords=[opportunity_type.value],
        conditional_guidance=guidance or [],
    )


_CATALOG: tuple[OpportunityCatalogEntry, ...] = (
    _entry(
        OpportunityType.ENTERPRISE_KNOWLEDGE_AND_PROFESSIONAL_DOCUMENT_ASSIST,
        "Enterprise knowledge and professional document assist",
        _case("CASE-01", "Morgan Stanley", "https://openai.com/index/morgan-stanley/"),
        guidance=[
            ConditionalGuidance(
                condition_field="data_modality",
                condition_value="general_knowledge",
                guidance="Ground answers in maintained internal sources.",
                kpi_or_risk_guidance="Track sourced-answer coverage.",
            ),
            ConditionalGuidance(
                condition_field="professional_domain",
                condition_value="professional_document",
                guidance=(
                    "Require qualified professional final review and traceable "
                    "citations."
                ),
                kpi_or_risk_guidance=(
                    "Watch material omissions and confirm jurisdiction or "
                    "professional scope."
                ),
            ),
        ],
    ),
    _entry(
        OpportunityType.CUSTOMER_SERVICE_ASSIST,
        "Customer service assist",
        _case("CASE-03", "Klarna", "https://openai.com/index/klarna/"),
    ),
    _entry(
        OpportunityType.DOCUMENT_CLASSIFICATION_AND_EXTRACTION,
        "Document classification and extraction",
        _case(
            "CASE-06",
            "Affinda",
            "https://aws.amazon.com/solutions/case-studies/affinda-case-study/",
        ),
    ),
    _entry(
        OpportunityType.MEETING_SUMMARY_AND_ACTION_ITEMS,
        "Meeting summary and action items",
        _case(
            "CASE-10",
            "Finastra",
            "https://www.microsoft.com/en/customers/story/18732-finastra-microsoft-viva-engage",
        ),
    ),
    _entry(
        OpportunityType.MARKETING_CONTENT_ASSIST,
        "Marketing content assist",
        _case(
            "CASE-11",
            "Reckitt",
            "https://www.microsoft.com/en/customers/story/23761-reckitt-power-bi",
        ),
    ),
    _entry(
        OpportunityType.DEMAND_FORECASTING,
        "Demand forecasting",
        _case(
            "CASE-16",
            "Amazon Pharmacy",
            "https://aws.amazon.com/solutions/case-studies/amazon-pharmacy-case-study/",
        ),
    ),
    _entry(
        OpportunityType.PREDICTIVE_MAINTENANCE,
        "Predictive maintenance",
        _case("CASE-20", "CrossTech", "https://cloud.google.com/customers/crosstech"),
    ),
    _entry(
        OpportunityType.ANOMALY_AND_RISK_DETECTION,
        "Anomaly and risk detection",
        _case("CASE-22", "Hitachi", "https://cloud.google.com/customers/hitachi"),
        guidance=[
            ConditionalGuidance(
                condition_field="data_modality",
                condition_value="image",
                guidance="Use visual inspection review workflows.",
                kpi_or_risk_guidance=(
                    "Track defect recall, false positives, and human "
                    "reinspection volume."
                ),
            ),
            ConditionalGuidance(
                condition_field="data_modality",
                condition_value="transactional",
                guidance="Keep investigation and appeal paths with human review.",
                kpi_or_risk_guidance=(
                    "Track anomaly recall, false-positive harm, appeals, and "
                    "investigation workload."
                ),
            ),
            ConditionalGuidance(
                condition_field="data_modality",
                condition_value="sensor",
                guidance="Use operational anomaly review before maintenance action.",
                kpi_or_risk_guidance=(
                    "Track warning lead time, missed events, and unplanned "
                    "downtime risk."
                ),
            ),
        ],
    ),
    _entry(
        OpportunityType.RECRUITING_PROCESS_ASSIST,
        "Recruiting process assist",
        _case(
            "CASE-26",
            "Gojob",
            "https://www.microsoft.com/en/customers/story/20838-gojob-azure-open-ai-service",
        ),
    ),
)


def get_opportunity_catalog() -> tuple[OpportunityCatalogEntry, ...]:
    """Return stable catalog copies that callers cannot mutate globally."""

    return tuple(entry.model_copy(deep=True) for entry in _CATALOG)
