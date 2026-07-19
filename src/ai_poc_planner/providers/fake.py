"""Deterministic model and embedding providers for offline workflows."""

from __future__ import annotations

from collections.abc import Sequence
from hashlib import sha256
from uuid import UUID, uuid5

from ai_poc_planner.domain.enums import (
    DataBoundary,
    DecisionImpact,
    DigitizationLevel,
    HighImpactDomain,
)
from ai_poc_planner.domain.facts import (
    ArchitectureControllabilityFacts,
    AssessmentFacts,
    BusinessValueFacts,
    DataReadinessFacts,
    GateFacts,
    GovernanceReadinessFacts,
    TechnicalFitFacts,
    UserAdoptionFacts,
)
from ai_poc_planner.domain.models import ClarifyingQuestion
from ai_poc_planner.domain.tools import (
    AssessBusinessValueRoiAndKpisInput,
    AssessDataReadinessInput,
    AssessTechnicalFitAndArchitectureInput,
    EstimatePocScopeInput,
    EvaluateRiskAndHardGatesInput,
    RetrieveSimilarCasesInput,
)
from ai_poc_planner.providers.base import (
    AssessmentToolInputs,
    PreparationStatus,
    ProviderCapabilities,
    ProviderPreparation,
    ProviderRequest,
)


class FakeProviderError(RuntimeError):
    """Intentional fake failure used to exercise provider error handling."""


class FakeModelProvider:
    """Extract reproducible facts and tool inputs without making decisions."""

    _capabilities = ProviderCapabilities(
        structured_output=True,
        tool_calling=False,
        streaming=False,
        model_identifier="fake/offline-v1",
    )

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    def prepare_assessment(self, request: ProviderRequest) -> ProviderPreparation:
        if request.interview_answers.get("simulate_provider_error") is True:
            raise FakeProviderError("simulated provider failure")

        missing = _missing_fields(request)
        if missing:
            return ProviderPreparation(
                status=PreparationStatus.CLARIFICATION_REQUIRED,
                clarifying_questions=[_question(field) for field in missing[:5]],
            )

        scenario = str(request.interview_answers["scenario"])
        if scenario not in {
            "high_value_low_risk",
            "high_score_but_blocked",
            "assistive_only",
            "requires_controls",
        }:
            return ProviderPreparation(
                status=PreparationStatus.CLARIFICATION_REQUIRED,
                clarifying_questions=[_question("scenario")],
            )

        evidence_ids = [item.id for item in request.evidence]
        facts = _facts_for(scenario, evidence_ids)
        return ProviderPreparation(
            status=PreparationStatus.READY,
            facts=facts,
            tool_inputs=_tool_inputs(request, scenario, facts),
        )


class FakeEmbeddingProvider:
    """Stable local vectors for interface tests; not semantic embeddings."""

    dimensions = 8

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for value in texts:
            digest = sha256(value.encode("utf-8")).digest()
            vectors.append(
                [round((byte / 255.0) * 2.0 - 1.0, 6) for byte in digest[:8]]
            )
        return vectors


_REQUIRED_ANSWERS = (
    "scenario",
    "target_users",
    "current_workflow",
    "data_sources",
    "owner",
)


def _missing_fields(request: ProviderRequest) -> list[str]:
    missing = [
        name for name in _REQUIRED_ANSWERS if not request.interview_answers.get(name)
    ]
    if not request.evidence:
        missing.append("interview_evidence")
    return missing


def _question(field: str) -> ClarifyingQuestion:
    prompts = {
        "scenario": "這個固定離線案例屬於哪一種評估情境？",
        "target_users": "主要使用者是誰？",
        "current_workflow": "目前流程如何運作？",
        "data_sources": "PoC 可使用哪些已核准資料來源？",
        "owner": "誰是流程與成果的負責人？",
        "interview_evidence": "哪一筆訪談 evidence 支持這些結構化答案？",
    }
    return ClarifyingQuestion(
        field=field,
        question=prompts[field],
        reason="完整且可追蹤的輸入是正式評估的前置條件。",
        priority=1,
    )


def _facts_for(scenario: str, evidence_ids: list[UUID]) -> AssessmentFacts:
    gates = GateFacts(
        evidence_ids=evidence_ids,
        authorization_confirmed=True,
        lawful_basis_confirmed=True,
        accountable_owner_confirmed=True,
        prohibited_use=False,
        high_impact_domain=HighImpactDomain.NONE,
        autonomous_final_decision=False,
        autonomous_enterprise_action=False,
        meaningful_human_review=True,
        contest_or_review_path=True,
        personal_data=False,
        sensitive_data=False,
        minimization_control=True,
        retention_control=True,
        access_control=True,
        security_controls_confirmed=True,
        security_controls_required=False,
        governance_controls_confirmed=True,
        governance_controls_required=False,
        audit_controls_confirmed=True,
        audit_controls_required=False,
        data_boundary=DataBoundary.LOCAL_ONLY,
        external_endpoint_requested=False,
        data_available=True,
        digitization=DigitizationLevel.COMPLETE,
        validation_sample_available=True,
    )
    if scenario == "high_score_but_blocked":
        gates = gates.model_copy(update={"autonomous_enterprise_action": True})
    elif scenario == "assistive_only":
        gates = gates.model_copy(update={"high_impact_domain": HighImpactDomain.LEGAL})
    elif scenario == "requires_controls":
        gates = gates.model_copy(
            update={
                "personal_data": True,
                "minimization_control": False,
                "retention_control": False,
                "access_control": False,
                "security_controls_required": True,
                "security_controls_confirmed": False,
            }
        )

    evidence = {"evidence_ids": evidence_ids}
    return AssessmentFacts(
        business_value=BusinessValueFacts(
            **evidence,
            pain_defined=True,
            beneficiary_defined=True,
            owner_identified=True,
            owner_approved=True,
            quantitative_baseline=True,
            target_kpi_defined=True,
            benefit_assumptions_documented=True,
            cost_baseline_available=True,
            roi_formula_available=True,
        ),
        data_readiness=DataReadinessFacts(
            **evidence,
            data_available=True,
            lawful_access=True,
            digitization=DigitizationLevel.COMPLETE,
            quality_known=True,
            quality_sampled=True,
            quality_measured=True,
            validation_sample_available=True,
            representative_validation_sample=True,
            gaps_resolvable_in_poc=True,
        ),
        technical_fit=TechnicalFitFacts(
            **evidence,
            ai_needed=True,
            technically_feasible=True,
            technical_path_defined=True,
            retrieval_required=True,
            boundaries_defined=True,
            key_assumptions_testable=True,
        ),
        architecture_controllability=ArchitectureControllabilityFacts(
            **evidence,
            integration_count=0,
            interfaces_known=True,
            test_environment_available=True,
            mocks_available=True,
            data_boundary_defined=True,
            dependencies_replaceable=True,
            observability_available=True,
            reproducible_environment=True,
        ),
        governance_readiness=GovernanceReadinessFacts(
            **evidence,
            lawful_basis_confirmed=True,
            accountable_owner_confirmed=True,
            data_boundary_defined=True,
            data_types_identified=True,
            risks_identified=True,
            controls_identified=True,
            policy_defined=True,
            reviewer_identified=True,
            minimization_defined=True,
            retention_defined=True,
            approved_policy=True,
            formal_risk_assessment=True,
            audit_records_available=True,
            incident_process_defined=True,
        ),
        user_adoption=UserAdoptionFacts(
            **evidence,
            process_owner_confirmed=True,
            affected_roles_involved=True,
            value_proposition_clear=True,
            representative_users_committed=True,
            workflow_adjusted=True,
            training_plan_defined=True,
            feedback_process_defined=True,
            users_co_designed=True,
            adoption_metrics_defined=True,
            support_owner_confirmed=True,
            iteration_owner_confirmed=True,
        ),
        gates=gates,
    )


def _tool_inputs(
    request: ProviderRequest,
    scenario: str,
    facts: AssessmentFacts,
) -> AssessmentToolInputs:
    correlation_id = uuid5(request.session_id, f"fake-provider:{scenario}")
    context = {
        "schema_version": "1.0",
        "correlation_id": correlation_id,
        "project_id": request.project.id,
        "session_id": request.session_id,
    }
    answers = request.interview_answers
    data_sources = [str(item) for item in answers["data_sources"]]
    return AssessmentToolInputs(
        retrieve_similar_cases=RetrieveSimilarCasesInput(
            **context,
            normalized_problem=request.project.problem_statement,
            industries=["customer-service"],
            top_k=3,
        ),
        assess_data_readiness=AssessDataReadinessInput(
            **context,
            data_sources=data_sources,
            access_confirmed=facts.data_readiness.lawful_access,
            digitization=facts.data_readiness.digitization,
            quality_notes=["固定案例已完成品質抽樣"],
            labels_available=True,
            validation_sample_available=(
                facts.data_readiness.validation_sample_available
            ),
        ),
        assess_technical_fit_and_architecture=(
            AssessTechnicalFitAndArchitectureInput(
                **context,
                task_pattern="bounded knowledge assistance",
                required_reasoning=["source-grounded answer selection"],
                required_tools=["fixture case lookup"],
                integrations=[],
                deployment_constraints=["offline", "local-only"],
            )
        ),
        evaluate_risk_and_hard_gates=EvaluateRiskAndHardGatesInput(
            **context,
            domain=facts.gates.high_impact_domain.value,
            decision_impact=(
                DecisionImpact.HIGH
                if facts.gates.high_impact_domain is not HighImpactDomain.NONE
                else DecisionImpact.LOW
            ),
            personal_data=facts.gates.personal_data,
            sensitive_data=facts.gates.sensitive_data,
            data_boundary=facts.gates.data_boundary,
            human_review_available=facts.gates.meaningful_human_review,
            authorization_confirmed=facts.gates.authorization_confirmed,
        ),
        assess_business_value_roi_and_kpis=(
            AssessBusinessValueRoiAndKpisInput(
                **context,
                owner=str(answers["owner"]),
                baseline_description="平均每次搜尋需要十分鐘",
                monthly_volume=1000,
                current_time_minutes=10,
                expected_change="將中位搜尋時間降至三分鐘",
                adoption_evidence=["代表性客服人員承諾參與 PoC"],
            )
        ),
        estimate_poc_scope=EstimatePocScopeInput(
            **context,
            requires_ocr=False,
            integration_count=0,
            requires_review_ui=True,
            evaluation_data_available=True,
            handles_sensitive_data=facts.gates.sensitive_data,
            department_count=1,
        ),
    )
