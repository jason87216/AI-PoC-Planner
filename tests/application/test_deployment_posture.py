from __future__ import annotations

from ai_poc_planner.application import assess_deployment_posture
from ai_poc_planner.domain import (
    DataClassification,
    DeploymentAssessmentStatus,
    DeploymentCandidateStatus,
    DeploymentPosture,
    DeploymentPostureInput,
)


def test_deployment_requests_clarification_for_required_unknowns() -> None:
    result = assess_deployment_posture(DeploymentPostureInput())

    assert result.status is DeploymentAssessmentStatus.CLARIFICATION_REQUIRED
    assert result.recommended_posture is None
    assert set(result.missing_deployment_information) >= {
        "data_classification",
        "external_processing_allowed",
        "offline_operation_required",
    }


def test_deployment_prefers_public_cloud_for_low_sensitivity_fast_poc() -> None:
    result = assess_deployment_posture(
        DeploymentPostureInput(
            data_classification=DataClassification.INTERNAL,
            external_processing_allowed=True,
            offline_operation_required=False,
            budget_preference="fast PoC",
            internal_ai_operations_capability="limited",
        )
    )

    assert result.recommended_posture is DeploymentPosture.PUBLIC_CLOUD_MANAGED


def test_deployment_prefers_private_environment_for_confidential_governed_cloud() -> (
    None
):
    result = assess_deployment_posture(
        DeploymentPostureInput(
            data_classification=DataClassification.CONFIDENTIAL,
            external_processing_allowed=True,
            offline_operation_required=False,
            existing_cloud_environment="governed cloud",
        )
    )

    assert (
        result.recommended_posture
        is DeploymentPosture.PRIVATE_CLOUD_OR_ISOLATED_ENVIRONMENT
    )


def test_deployment_prefers_hybrid_for_separable_sensitive_work() -> None:
    result = assess_deployment_posture(
        DeploymentPostureInput(
            data_classification=DataClassification.INTERNAL,
            contains_personal_data=True,
            external_processing_allowed=True,
            offline_operation_required=False,
        )
    )

    assert result.recommended_posture is DeploymentPosture.HYBRID


def test_offline_or_disallowed_external_processing_does_not_block_the_whole_poc() -> (
    None
):
    result = assess_deployment_posture(
        DeploymentPostureInput(
            data_classification=DataClassification.CONFIDENTIAL,
            external_processing_allowed=False,
            offline_operation_required=True,
            existing_on_prem_infrastructure="available",
        )
    )

    assert result.recommended_posture is DeploymentPosture.ON_PREMISES
    assert any(
        candidate.status is DeploymentCandidateStatus.DISALLOWED
        for candidate in result.candidates
    )


def test_highly_confidential_data_without_environment_requires_clarification() -> None:
    result = assess_deployment_posture(
        DeploymentPostureInput(
            data_classification=DataClassification.HIGHLY_CONFIDENTIAL,
            external_processing_allowed=False,
            offline_operation_required=False,
        )
    )

    assert result.status is DeploymentAssessmentStatus.CLARIFICATION_REQUIRED
    assert result.recommended_posture is None


def test_highly_confidential_data_never_selects_general_public_cloud() -> None:
    result = assess_deployment_posture(
        DeploymentPostureInput(
            data_classification=DataClassification.HIGHLY_CONFIDENTIAL,
            external_processing_allowed=True,
            offline_operation_required=False,
            existing_cloud_environment="isolated environment",
        )
    )

    assert result.recommended_posture is (
        DeploymentPosture.PRIVATE_CLOUD_OR_ISOLATED_ENVIRONMENT
    )
    assert any(
        candidate.posture is DeploymentPosture.PUBLIC_CLOUD_MANAGED
        and candidate.status is DeploymentCandidateStatus.DISALLOWED
        for candidate in result.candidates
    )
