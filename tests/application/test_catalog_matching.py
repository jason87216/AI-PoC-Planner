from __future__ import annotations

import pytest

from ai_poc_planner.application import match_opportunities
from ai_poc_planner.domain import OpportunityMatchInput, OpportunityType


@pytest.mark.parametrize(
    ("signal", "expected"),
    [
        (
            "internal knowledge documents",
            OpportunityType.ENTERPRISE_KNOWLEDGE_AND_PROFESSIONAL_DOCUMENT_ASSIST,
        ),
        ("customer support FAQ", OpportunityType.CUSTOMER_SERVICE_ASSIST),
        (
            "invoice OCR extraction",
            OpportunityType.DOCUMENT_CLASSIFICATION_AND_EXTRACTION,
        ),
        (
            "meeting minutes action items",
            OpportunityType.MEETING_SUMMARY_AND_ACTION_ITEMS,
        ),
        ("marketing campaign content", OpportunityType.MARKETING_CONTENT_ASSIST),
        ("inventory demand forecast", OpportunityType.DEMAND_FORECASTING),
        ("equipment maintenance failure", OpportunityType.PREDICTIVE_MAINTENANCE),
        ("transaction fraud anomaly", OpportunityType.ANOMALY_AND_RISK_DETECTION),
        ("recruiting resume candidate", OpportunityType.RECRUITING_PROCESS_ASSIST),
    ],
)
def test_matching_returns_the_expected_reviewed_opportunity(
    signal: str, expected: OpportunityType
) -> None:
    result = match_opportunities(
        OpportunityMatchInput(business_problem_signals=[signal])
    )

    assert result.candidates[0].opportunity_type is expected
    assert result.candidates[0].match_strength >= 1
    assert len(result.candidates[0].reasons) <= 3
    assert len(result.candidates[0].case_references) <= 2


def test_matching_is_stable_limited_and_preserves_contextual_guidance() -> None:
    request = OpportunityMatchInput(
        business_problem_signals=[
            "documents",
            "customer support",
            "invoice",
            "meeting",
        ],
        professional_domain="professional_document",
    )

    result = match_opportunities(request)

    assert len(result.candidates) == 3
    assert [candidate.opportunity_type for candidate in result.candidates] == [
        OpportunityType.ENTERPRISE_KNOWLEDGE_AND_PROFESSIONAL_DOCUMENT_ASSIST,
        OpportunityType.CUSTOMER_SERVICE_ASSIST,
        OpportunityType.DOCUMENT_CLASSIFICATION_AND_EXTRACTION,
    ]
    assert (
        result.candidates[0].conditional_guidance[0].condition_value
        == "professional_document"
    )


def test_matching_requests_clarification_when_signals_are_insufficient() -> None:
    result = match_opportunities(
        OpportunityMatchInput(business_problem_signals=["improve work"])
    )

    assert result.candidates == []
    assert result.clarifying_questions


def test_matching_adds_non_ai_alternatives_without_turning_them_into_candidates() -> (
    None
):
    result = match_opportunities(
        OpportunityMatchInput(
            business_problem_signals=[
                "fixed rules",
                "form workflow database",
                "dashboard trend",
            ],
        )
    )

    assert [item.value for item in result.non_ai_alternatives] == [
        "rule_based_automation",
        "conventional_software",
    ]
    assert all(
        candidate.opportunity_type.value != "software_development_assist"
        for candidate in result.candidates
    )


@pytest.mark.parametrize(
    ("data_modality", "expected_kpi"),
    [
        ("image", "defect recall"),
        ("transactional", "anomaly recall"),
        ("sensor", "warning lead time"),
    ],
)
def test_anomaly_guidance_keeps_kpis_specific_to_the_data_modality(
    data_modality: str, expected_kpi: str
) -> None:
    result = match_opportunities(
        OpportunityMatchInput(
            business_problem_signals=["defect anomaly inspection"],
            data_modality=data_modality,
        )
    )

    guidance = result.candidates[0].conditional_guidance

    assert guidance[0].condition_value == data_modality
    assert expected_kpi in guidance[0].kpi_or_risk_guidance.lower()
