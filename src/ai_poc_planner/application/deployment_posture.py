"""Small deterministic deployment-posture assessment for planning only."""

from ai_poc_planner.domain.catalog import (
    DataClassification,
    DeploymentAssessmentStatus,
    DeploymentCandidateStatus,
    DeploymentPosture,
    DeploymentPostureAssessment,
    DeploymentPostureCandidate,
    DeploymentPostureInput,
)


def _candidate(
    posture: DeploymentPosture,
    status: DeploymentCandidateStatus,
    reason: str,
    cost_shape: str,
    operations_requirement: str,
) -> DeploymentPostureCandidate:
    return DeploymentPostureCandidate(
        posture=posture,
        status=status,
        reasons=[reason],
        cost_shape=cost_shape,
        operations_requirements=[operations_requirement],
    )


def assess_deployment_posture(
    request: DeploymentPostureInput,
) -> DeploymentPostureAssessment:
    """Return a small deterministic posture recommendation or clarification request."""

    missing = []
    if request.data_classification is DataClassification.UNKNOWN:
        missing.append("data_classification")
    if request.external_processing_allowed is None:
        missing.append("external_processing_allowed")
    if request.offline_operation_required is None:
        missing.append("offline_operation_required")
    if request.data_classification is DataClassification.HIGHLY_CONFIDENTIAL and not (
        request.existing_on_prem_infrastructure or request.existing_cloud_environment
    ):
        missing.append("approved_isolated_environment")
    if missing:
        return DeploymentPostureAssessment(
            status=DeploymentAssessmentStatus.CLARIFICATION_REQUIRED,
            recommended_posture=None,
            missing_deployment_information=missing,
        )
    if request.offline_operation_required or not request.external_processing_allowed:
        return DeploymentPostureAssessment(
            status=DeploymentAssessmentStatus.RECOMMENDATION_AVAILABLE,
            recommended_posture=DeploymentPosture.ON_PREMISES,
            candidates=[
                _candidate(
                    DeploymentPosture.ON_PREMISES,
                    DeploymentCandidateStatus.ELIGIBLE,
                    "Offline or no external processing requires local control.",
                    "Higher initial investment and operations burden.",
                    "Maintain local infrastructure and access controls.",
                ),
                _candidate(
                    DeploymentPosture.HYBRID,
                    DeploymentCandidateStatus.CONDITIONAL,
                    "Use only if a safely separated workload exists.",
                    "Mixed fixed and variable cost with integration burden.",
                    "Define a reviewed separation boundary for any external workload.",
                ),
                _candidate(
                    DeploymentPosture.PUBLIC_CLOUD_MANAGED,
                    DeploymentCandidateStatus.DISALLOWED,
                    "External processing is not permitted.",
                    "Not applicable.",
                    "No public-cloud operation is permitted for this workload.",
                ),
            ],
        )
    if request.data_classification is DataClassification.HIGHLY_CONFIDENTIAL:
        preferred = (
            DeploymentPosture.ON_PREMISES
            if request.existing_on_prem_infrastructure
            else DeploymentPosture.PRIVATE_CLOUD_OR_ISOLATED_ENVIRONMENT
        )
        return DeploymentPostureAssessment(
            status=DeploymentAssessmentStatus.RECOMMENDATION_AVAILABLE,
            recommended_posture=preferred,
            candidates=[
                _candidate(
                    preferred,
                    DeploymentCandidateStatus.ELIGIBLE,
                    (
                        "Highly confidential data requires an approved isolated "
                        "environment."
                    ),
                    "Higher fixed investment and operations burden.",
                    (
                        "Operate within the approved isolated environment and its "
                        "controls."
                    ),
                ),
                _candidate(
                    DeploymentPosture.HYBRID,
                    DeploymentCandidateStatus.CONDITIONAL,
                    "Use only for reviewed, safely separated lower-sensitivity work.",
                    "Mixed fixed and variable cost with integration burden.",
                    "Maintain a verified boundary between isolated and external work.",
                ),
                _candidate(
                    DeploymentPosture.PUBLIC_CLOUD_MANAGED,
                    DeploymentCandidateStatus.DISALLOWED,
                    (
                        "General public cloud is not appropriate for highly "
                        "confidential data."
                    ),
                    "Not applicable.",
                    "Do not process the highly confidential workload in public cloud.",
                ),
            ],
        )
    if (
        request.data_classification is DataClassification.CONFIDENTIAL
        and request.existing_cloud_environment
    ):
        return DeploymentPostureAssessment(
            status=DeploymentAssessmentStatus.RECOMMENDATION_AVAILABLE,
            recommended_posture=DeploymentPosture.PRIVATE_CLOUD_OR_ISOLATED_ENVIRONMENT,
            candidates=[
                _candidate(
                    DeploymentPosture.PRIVATE_CLOUD_OR_ISOLATED_ENVIRONMENT,
                    DeploymentCandidateStatus.ELIGIBLE,
                    (
                        "Confidential data can use the existing governed cloud "
                        "environment."
                    ),
                    "Moderate fixed and variable cost with managed operations.",
                    "Apply the existing cloud governance and access controls.",
                ),
                _candidate(
                    DeploymentPosture.HYBRID,
                    DeploymentCandidateStatus.CONDITIONAL,
                    "Use if sensitive source data remains separated.",
                    "Mixed cost with additional integration burden.",
                    "Define and operate the data-separation boundary.",
                ),
            ],
        )
    if request.contains_personal_data or request.contains_trade_secrets:
        return DeploymentPostureAssessment(
            status=DeploymentAssessmentStatus.RECOMMENDATION_AVAILABLE,
            recommended_posture=DeploymentPosture.HYBRID,
            candidates=[
                _candidate(
                    DeploymentPosture.HYBRID,
                    DeploymentCandidateStatus.ELIGIBLE,
                    "Sensitive and less-sensitive processing can be separated.",
                    "Mixed cost and higher integration operations burden.",
                    "Maintain the data classification and separation process.",
                ),
            ],
        )
    return DeploymentPostureAssessment(
        status=DeploymentAssessmentStatus.RECOMMENDATION_AVAILABLE,
        recommended_posture=DeploymentPosture.PUBLIC_CLOUD_MANAGED,
        candidates=[
            _candidate(
                DeploymentPosture.PUBLIC_CLOUD_MANAGED,
                DeploymentCandidateStatus.ELIGIBLE,
                "External processing is allowed for a fast PoC.",
                "Low initial investment with variable operating cost.",
                "Use managed service operations and confirm data controls.",
            ),
            _candidate(
                DeploymentPosture.PRIVATE_CLOUD_OR_ISOLATED_ENVIRONMENT,
                DeploymentCandidateStatus.CONDITIONAL,
                "Use when stronger enterprise controls are needed.",
                "Moderate fixed and variable cost with more operations.",
                "Provide the required cloud governance and operations ownership.",
            ),
        ],
    )
