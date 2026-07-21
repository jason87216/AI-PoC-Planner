from __future__ import annotations

from ai_poc_planner.catalog import get_opportunity_catalog
from ai_poc_planner.domain import (
    DeploymentAssessmentStatus,
    DeploymentCandidateStatus,
    DeploymentPosture,
    DeploymentPostureAssessment,
    DeploymentPostureCandidate,
    DeploymentPostureInput,
    EvidenceGrade,
    EvidenceType,
    NonAiAlternativeDirection,
    OpportunityMatchInput,
    OpportunityType,
)


def test_catalog_contains_exactly_the_nine_approved_opportunities() -> None:
    catalog = get_opportunity_catalog()

    assert len(catalog) == 9
    assert {entry.opportunity_type for entry in catalog} == set(OpportunityType)
    assert "software_development_assist" not in {
        entry.opportunity_type.value for entry in catalog
    }
    assert "knowledge_query" not in {entry.opportunity_type.value for entry in catalog}
    assert "contract_risk_assist" not in {
        entry.opportunity_type.value for entry in catalog
    }


def test_non_ai_directions_are_not_catalog_entries() -> None:
    catalog = get_opportunity_catalog()

    assert set(NonAiAlternativeDirection) == {
        NonAiAlternativeDirection.RULE_BASED_AUTOMATION,
        NonAiAlternativeDirection.CONVENTIONAL_SOFTWARE,
        NonAiAlternativeDirection.DATA_ANALYTICS,
    }
    assert not (
        {item.value for item in NonAiAlternativeDirection}
        & {entry.opportunity_type.value for entry in catalog}
    )


def test_catalog_callers_cannot_mutate_the_fixed_fixture() -> None:
    first = get_opportunity_catalog()
    first[0].display_name = "caller mutation"

    assert get_opportunity_catalog()[0].display_name != "caller mutation"


def test_catalog_entries_have_required_references_and_grade_e_is_supplemental() -> None:
    for entry in get_opportunity_catalog():
        assert entry.business_problem_signals
        assert entry.minimum_information_needed
        assert entry.case_references
        assert all(reference.source_url for reference in entry.case_references)
        assert all(reference.source_label for reference in entry.case_references)
        assert all(
            reference.evidence_grade is not EvidenceGrade.E
            for reference in entry.case_references
        )
        assert all(
            reference.evidence_grade is EvidenceGrade.E
            for reference in entry.supplemental_case_references
        )
        assert all(reference.evidence_type for reference in entry.case_references)


def test_merged_opportunities_preserve_conditional_guidance_by_context() -> None:
    catalog = {entry.opportunity_type: entry for entry in get_opportunity_catalog()}

    professional = catalog[
        OpportunityType.ENTERPRISE_KNOWLEDGE_AND_PROFESSIONAL_DOCUMENT_ASSIST
    ]
    anomaly = catalog[OpportunityType.ANOMALY_AND_RISK_DETECTION]

    assert {item.condition_value for item in professional.conditional_guidance} >= {
        "general_knowledge",
        "professional_document",
    }
    assert {item.condition_value for item in anomaly.conditional_guidance} >= {
        "image",
        "transactional",
        "sensor",
    }
    transactional = next(
        item
        for item in anomaly.conditional_guidance
        if item.condition_value == "transactional"
    )
    image = next(
        item for item in anomaly.conditional_guidance if item.condition_value == "image"
    )
    sensor = next(
        item
        for item in anomaly.conditional_guidance
        if item.condition_value == "sensor"
    )
    assert "appeal" in transactional.kpi_or_risk_guidance
    assert "defect" in image.kpi_or_risk_guidance
    assert "downtime" in sensor.kpi_or_risk_guidance


def test_catalog_contracts_round_trip_and_do_not_expose_formal_decisions() -> None:
    entry = get_opportunity_catalog()[0]
    restored = type(entry).model_validate_json(entry.model_dump_json())

    assert restored == entry
    assert "recommendation" not in type(entry).model_fields
    assert "gate_disposition" not in type(entry).model_fields
    assert "assistive_only" not in type(entry).model_fields
    assert "blocked" not in type(entry).model_fields
    assert OpportunityMatchInput(
        business_problem_signals=["documents"]
    ).business_problem_signals


def test_deployment_contract_skeleton_keeps_disallowed_local_to_a_posture() -> None:
    request = DeploymentPostureInput(data_classification="confidential")
    candidate = DeploymentPostureCandidate(
        posture=DeploymentPosture.PUBLIC_CLOUD_MANAGED,
        status=DeploymentCandidateStatus.DISALLOWED,
        reasons=["external processing is not allowed"],
    )
    assessment = DeploymentPostureAssessment(
        status=DeploymentAssessmentStatus.CLARIFICATION_REQUIRED,
        recommended_posture=None,
        candidates=[candidate],
        missing_deployment_information=["external_processing_allowed"],
    )

    assert request.data_classification.value == "confidential"
    assert assessment.recommended_posture is None
    assert assessment.candidates[0].status is DeploymentCandidateStatus.DISALLOWED
    assert EvidenceType.VENDOR_REPORTED.value == "vendor_reported"
